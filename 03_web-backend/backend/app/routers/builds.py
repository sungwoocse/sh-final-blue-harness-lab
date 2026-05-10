"""빌드/배포 API 라우터"""
from fastapi import APIRouter, HTTPException, UploadFile, File, Form, BackgroundTasks
from typing import Optional
from app.models import (
    BuildResponse,
    TaskStatusResponse,
    BuildTaskResult,
    PushRequest,
    ScaffoldRequest,
    ScaffoldResponse,
    DeployRequest,
    DeployResponse,
    BuildAndPushRequest,
    WorkspaceTaskItem,
    WorkspaceTasksResponse,
)
from app.database import db_client, s3_client
from app.config import settings
from app.utils.timezone import to_kst
import logging
import httpx
import asyncio
from datetime import datetime

logger = logging.getLogger(__name__)

router = APIRouter()


# ===== Helper Functions =====
def _to_kst_iso_string(value: Optional[str]) -> str:
    """ISO 문자열을 KST(+09:00) 기준 문자열로 변환. 실패 시 원본 반환."""
    if not value:
        return value or ""
    try:
        return to_kst(datetime.fromisoformat(value)).isoformat()
    except Exception:
        return value


def _get_workspace_id_from_task(task_id: str) -> Optional[str]:
    """task_id로부터 workspace_id 조회"""
    task = db_client.get_build_task_by_id(task_id)
    if task:
        return task.get("workspace_id")
    return None


async def _real_build_process(
    workspace_id: str, task_id: str, file_content: bytes, filename: str, app_name: str
):
    """실제 Builder Service 호출 및 폴링"""
    try:
        # DynamoDB 상태 갱신은 빌더 서비스 측에서 처리 (중복 업데이트 방지)

        # 1. Builder Service의 /api/v1/build 호출
        async with httpx.AsyncClient(timeout=30.0) as client:
            files = {"file": (filename, file_content)}
            data = {
                "workspace_id": workspace_id,
                "app_name": app_name,
            }

            response = await client.post(
                f"{settings.builder_service_url}/api/v1/build",
                files=files,
                data=data,
            )
            response.raise_for_status()
            build_response = response.json()
            builder_task_id = build_response.get("task_id")

            logger.info(f"Build task {task_id} submitted to Builder Service: {builder_task_id}")

        # 2. 폴링으로 Builder Service의 작업 상태 확인 (최대 10분)
        max_attempts = 120  # 5초 * 120 = 600초 = 10분
        for attempt in range(max_attempts):
            await asyncio.sleep(5)

            async with httpx.AsyncClient(timeout=10.0) as client:
                status_response = await client.get(
                    f"{settings.builder_service_url}/api/v1/tasks/{builder_task_id}",
                    params={"workspace_id": workspace_id}
                )
                status_response.raise_for_status()
                status_data = status_response.json()

                status = status_data.get("status")
                logger.info(f"Build task {task_id} status: {status} (attempt {attempt + 1}/{max_attempts})")

                # 상태 업데이트
                if status in ["completed", "done"]:
                    result = status_data.get("result", {})
                    wasm_path = result.get("wasm_path")

                    logger.info(f"Build task {task_id} completed: {wasm_path}")
                    break

                elif status == "failed":
                    error_msg = status_data.get("error", "Build failed")
                    logger.error(f"Build task {task_id} failed: {error_msg}")
                    break

                else:
                    # running 또는 pending 상태는 로그만 남김
                    logger.debug(f"Build task {task_id} status (no-op update): {status}")

        else:
            # 타임아웃 (10분 초과)
            error_msg = "Build timeout (10 minutes exceeded)"
            logger.error(f"Build task {task_id} timed out")

    except httpx.HTTPError as e:
        logger.error(f"Build task {task_id} HTTP error: {str(e)}")
    except Exception as e:
        logger.error(f"Build task {task_id} failed: {str(e)}")


async def _real_push_process(
    workspace_id: str,
    task_id: str,
    registry_url: str,
    username: str,
    password: Optional[str],
    tag: str,
    s3_source_path: str
):
    """실제 Builder Service의 Push API 호출 및 폴링"""
    dummy_password = "dummy-password"
    try:
        # DynamoDB 상태 갱신은 빌더 서비스 측에서 처리 (중복 업데이트 방지)

        # 1. Builder Service의 /api/v1/push 호출
        async with httpx.AsyncClient(timeout=30.0) as client:
            push_data = {
                "registry_url": registry_url,
                "username": username,
                "password": password or dummy_password,
                "tag": tag,
                "workspace_id": workspace_id,
                "s3_source_path": s3_source_path,
            }

            response = await client.post(
                f"{settings.builder_service_url}/api/v1/push",
                json=push_data,
            )
            response.raise_for_status()
            push_response = response.json()
            builder_task_id = push_response.get("task_id")

            logger.info(f"Push task {task_id} submitted to Builder Service: {builder_task_id}")

        # 2. 폴링으로 작업 상태 확인 (최대 10분)
        max_attempts = 120
        for attempt in range(max_attempts):
            await asyncio.sleep(5)

            async with httpx.AsyncClient(timeout=10.0) as client:
                status_response = await client.get(
                    f"{settings.builder_service_url}/api/v1/tasks/{builder_task_id}",
                    params={"workspace_id": workspace_id}
                )
                status_response.raise_for_status()
                status_data = status_response.json()

                status = status_data.get("status")
                logger.info(f"Push task {task_id} status: {status} (attempt {attempt + 1}/{max_attempts})")

                if status in ["completed", "done"]:
                    result = status_data.get("result", {})
                    image_url = result.get("image_url") or result.get("image_uri")

                    logger.info(f"Push task {task_id} completed: {image_url}")
                    break

                elif status == "failed":
                    error_msg = status_data.get("error", "Push failed")
                    logger.error(f"Push task {task_id} failed: {error_msg}")
                    break

                else:
                    logger.debug(f"Push task {task_id} status (no-op update): {status}")

        else:
            # 타임아웃
            error_msg = "Push timeout (10 minutes exceeded)"
            logger.error(f"Push task {task_id} timed out")

    except httpx.HTTPError as e:
        logger.error(f"Push task {task_id} HTTP error: {str(e)}")
    except Exception as e:
        logger.error(f"Push task {task_id} failed: {str(e)}")


# ===== POST /api/v1/build =====
@router.post("/v1/build", response_model=BuildResponse, status_code=202)
async def build(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(..., description=".py 파일 또는 .zip 아카이브"),
    app_name: Optional[str] = Form(None, description="애플리케이션 이름"),
    workspace_id: str = Form(default="ws-default", description="워크스페이스 ID"),
):
    """
    파일 업로드 및 빌드 시작

    - **file**: .py 파일 또는 .zip 아카이브 (필수)
    - **app_name**: 애플리케이션 이름 (선택, 미지정시 자동 생성)
    - **workspace_id**: 워크스페이스 ID (기본값: ws-default)
    """
    try:
        # 파일 확장자 검증
        if not file.filename:
            raise HTTPException(status_code=400, detail="파일명이 없습니다")

        if not (file.filename.endswith(".py") or file.filename.endswith(".zip")):
            raise HTTPException(
                status_code=400, detail="지원하지 않는 파일 형식입니다 (.py 또는 .zip만 가능)"
            )

        # 파일 읽기
        file_content = await file.read()

        # BuildTask 생성
        task = db_client.create_build_task(
            workspace_id=workspace_id, app_name=app_name, source_path=None
        )
        task_id = task["task_id"]
        final_app_name = task["app_name"]

        # S3에 소스 파일 저장
        s3_path = s3_client.save_build_source(
            workspace_id, task_id, file_content, file.filename
        )

        # Task에 source_path 업데이트
        # 상태 업데이트는 빌더에서 처리

        # 백그라운드에서 빌드 프로세스 실행
        background_tasks.add_task(
            _real_build_process, workspace_id, task_id, file_content, file.filename, final_app_name
        )

        return BuildResponse(
            task_id=task_id, status="pending", message="Build task created", source_s3_path=s3_path
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Build endpoint error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


# ===== GET /api/v1/tasks/{task_id} =====
@router.get("/v1/tasks/{task_id}", response_model=TaskStatusResponse)
async def get_task_status(task_id: str):
    """
    작업 상태 조회

    - **task_id**: 작업 ID
    """
    try:
        # task_id로 작업 조회
        task = db_client.get_build_task_by_id(task_id)

        if not task:
            raise HTTPException(status_code=404, detail="Task not found: uuid=string")

        # 응답 구성
        result = None
        if task["status"] == "completed":
            result = BuildTaskResult(
                wasm_path=task.get("wasm_path"),
                image_url=task.get("image_url"),
                file_path=task.get("source_code_path"),
            )

        return TaskStatusResponse(
            task_id=task["task_id"],
            status=task["status"],
            result=result,
            error=task.get("error_message"),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get task status error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


# ===== GET /api/v1/workspaces/{workspace_id}/tasks =====
@router.get("/v1/workspaces/{workspace_id}/tasks", response_model=WorkspaceTasksResponse)
async def list_workspace_tasks(workspace_id: str):
    """
    워크스페이스의 모든 빌드 작업 조회

    - **workspace_id**: 워크스페이스 ID
    """
    try:
        # DynamoDB에서 workspace_id로 모든 작업 조회
        tasks = db_client.list_build_tasks(workspace_id)

        # 응답 구성
        task_items = []
        for task in tasks:
            result = None
            if task["status"] == "completed":
                result = BuildTaskResult(
                    wasm_path=task.get("wasm_path"),
                    image_url=task.get("image_url"),
                    file_path=task.get("source_code_path"),
                )

            task_items.append(
                WorkspaceTaskItem(
                    task_id=task["task_id"],
                    status=task["status"],
                    app_name=task.get("app_name"),
                    created_at=_to_kst_iso_string(task.get("created_at", "")),
                    updated_at=_to_kst_iso_string(task.get("updated_at", "")),
                    result=result,
                    error=task.get("error_message"),
                )
            )

        return WorkspaceTasksResponse(
            workspace_id=workspace_id,
            tasks=task_items,
            count=len(task_items),
        )

    except Exception as e:
        logger.error(f"List workspace tasks error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


# ===== POST /api/v1/push =====
@router.post("/v1/push", response_model=BuildResponse, status_code=202)
async def push_to_ecr(background_tasks: BackgroundTasks, request: PushRequest):
    """
    ECR에 이미지 푸시

    - **registry_url**: ECR 레지스트리 URL
    - **username**: 레지스트리 사용자명 (기본값: AWS)
    - **password**: 레지스트리 비밀번호 (IRSA 사용 시 더미 값 자동 사용)
    - **tag**: 이미지 태그
    - **app_dir**: 애플리케이션 디렉토리 경로
    """
    try:
        workspace_id = request.workspace_id

        # Task 생성
        task = db_client.create_build_task(workspace_id=workspace_id, app_name=None)
        task_id = task["task_id"]

        # 백그라운드에서 푸시 프로세스 실행 (상태 업데이트는 빌더에서 처리)
        background_tasks.add_task(
            _real_push_process,
            workspace_id,
            task_id,
            request.registry_url,
            request.username,
            request.password,
            request.tag,
            request.s3_source_path or "",
        )

        return BuildResponse(
            task_id=task_id, status="pending", message="Push task created"
        )

    except Exception as e:
        logger.error(f"Push endpoint error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


# ===== POST /api/v1/scaffold =====
@router.post("/v1/scaffold", response_model=ScaffoldResponse)
async def scaffold_spinapp(request: ScaffoldRequest):
    """
    SpinApp 매니페스트 생성

    - **image_ref**: 이미지 참조 (ECR URL:tag)
    - **component**: 컴포넌트 이름 (선택)
    - **replicas**: 레플리카 수 (기본값: 1)
    - **output_path**: 출력 파일 경로 (선택)
    """
    try:
        # Builder Service의 /api/v1/scaffold 호출
        async with httpx.AsyncClient(timeout=30.0) as client:
            scaffold_data = {
                "image_ref": request.image_ref,
                "component": request.component,
                "replicas": request.replicas,
                "output_path": request.output_path,
            }

            response = await client.post(
                f"{settings.builder_service_url}/api/v1/scaffold",
                json=scaffold_data,
            )
            response.raise_for_status()
            scaffold_response = response.json()

            return ScaffoldResponse(
                success=scaffold_response.get("success", True),
                yaml_content=scaffold_response.get("yaml_content"),
                file_path=scaffold_response.get("file_path"),
                error=scaffold_response.get("error"),
            )

    except httpx.HTTPError as e:
        logger.error(f"Scaffold HTTP error: {str(e)}")
        return ScaffoldResponse(
            success=False,
            error=f"HTTP error: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Scaffold endpoint error: {str(e)}")
        return ScaffoldResponse(
            success=False,
            error=str(e)
        )


# ===== POST /api/v1/deploy =====
@router.post("/v1/deploy", response_model=DeployResponse)
async def deploy_to_k8s(request: DeployRequest):
    """
    K8s에 SpinApp 배포

    - **namespace**: Kubernetes 네임스페이스 (필수)
    - **image_ref**: 이미지 참조 (필수)
    - **app_name**: 애플리케이션 이름 (선택, 기본값: Faker 자동 생성)
    - **replicas**: 레플리카 수 (기본값: 1)
    - **enable_autoscaling**: HPA/KEDA 활성화 (기본값: true)
    - **use_spot**: Spot 인스턴스 사용 (기본값: true)
    """
    # Builder Service의 /api/v1/deploy 호출
    async with httpx.AsyncClient(timeout=60.0) as client:
        # app_name을 소문자로 변환 (Spin TOML 규칙 준수)
        app_name_sanitized = request.app_name.lower() if request.app_name else None

        deploy_data = {
            "app_name": app_name_sanitized,
            "namespace": request.namespace,
            "service_account": request.service_account,
            "cpu_limit": request.cpu_limit,
            "memory_limit": request.memory_limit,
            "cpu_request": request.cpu_request,
            "memory_request": request.memory_request,
            "image_ref": request.image_ref,
            "enable_autoscaling": request.enable_autoscaling,
            "replicas": request.replicas,
            "use_spot": request.use_spot,
            "custom_tolerations": request.custom_tolerations,
            "custom_affinity": request.custom_affinity,
            "function_id": request.function_id,  # 로그 구분용 Function ID
        }

        # 오토스케일링이 활성화된 경우, replicas 필드를 반드시 제거
        if deploy_data.get("enable_autoscaling"):
            del deploy_data["replicas"]

        logger.info(f"Final deploy data being sent: {deploy_data}")
        response = await client.post(
            f"{settings.builder_service_url}/api/v1/deploy",
            json=deploy_data,
        )
        
        # --- GUARANTEED LOGGING ---
        logger.info(f"Builder service response received. Status: {response.status_code}, Body: {response.text}")
        # --- END GUARANTEED LOGGING ---

        response.raise_for_status()
        deploy_response = response.json()

        # Service 생성 대기 (5초) 및 재조회
        if not deploy_response.get("endpoint"):
            logger.info("Endpoint not ready, waiting 5 seconds...")
            await asyncio.sleep(5)
            
            generated_app_name = deploy_response.get("app_name")
            if generated_app_name:
                deploy_data["app_name"] = generated_app_name
                
                logger.info(f"Re-sending deploy data: {deploy_data}")
                response = await client.post(
                    f"{settings.builder_service_url}/api/v1/deploy",
                    json=deploy_data,
                )
                
                logger.info(f"Builder service retry response. Status: {response.status_code}, Body: {response.text}")
                response.raise_for_status()
                deploy_response = response.json()

        return DeployResponse(
            app_name=deploy_response.get("app_name"),
            namespace=deploy_response.get("namespace"),
            service_name=deploy_response.get("service_name"),
            service_status=deploy_response.get("service_status", "pending"),
            endpoint=deploy_response.get("endpoint"),
            enable_autoscaling=deploy_response.get("enable_autoscaling"),
            use_spot=deploy_response.get("use_spot"),
            error=deploy_response.get("error"),
        )


# ===== POST /api/v1/build-and-push =====
@router.post("/v1/build-and-push", response_model=BuildResponse, status_code=202)
async def build_and_push(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    registry_url: str = Form(...),
    username: str = Form(default="AWS"),
    password: Optional[str] = Form("dummy-password"),
    tag: str = Form(default="sha256"),
    app_name: Optional[str] = Form(None),
    workspace_id: str = Form(default="ws-default"),
):
    """
    빌드 및 푸시 통합

    - **file**: .py 파일 또는 .zip 아카이브 (필수)
    - **registry_url**: ECR 레지스트리 URL (필수)
    - **username**: 레지스트리 사용자명 (기본값: AWS)
    - **password**: 레지스트리 비밀번호 (선택, Builder Service IRSA 사용 시 불필요)
    - **tag**: 이미지 태그 (기본값: sha256)
    - **app_name**: 애플리케이션 이름 (선택)
    """
    try:
        # 파일 검증
        if not file.filename or not (
            file.filename.endswith(".py") or file.filename.endswith(".zip")
        ):
            raise HTTPException(
                status_code=400, detail="지원하지 않는 파일 형식입니다 (.py 또는 .zip만 가능)"
            )

        # 파일 읽기
        file_content = await file.read()

        # Task 생성
        task = db_client.create_build_task(workspace_id=workspace_id, app_name=app_name)
        task_id = task["task_id"]
        final_app_name = task["app_name"]

        # 태그가 sha256(기본값)인 경우, task_id를 포함한 고유 태그 생성
        effective_tag = tag
        if tag == "sha256":
            effective_tag = f"task-{task_id}"

        # S3에 저장
        s3_path = s3_client.save_build_source(
            workspace_id, task_id, file_content, file.filename
        )

        # Builder Service의 /api/v1/build-and-push 호출 (백그라운드)
        async def _build_and_push_wrapper():
            """Build and Push를 순차적으로 실행하는 래퍼"""
            try:
                # 상태 업데이트는 빌더에서 처리
                dummy_password = "dummy-password"
                # IRSA 사용을 위해 기본 크리덴셜은 비워 보냄
                normalized_username = username
                normalized_password = password
                if (username == "AWS") and (password is None or password == dummy_password):
                    normalized_username = ""
                    normalized_password = ""

                # Builder Service에 build-and-push 요청
                async with httpx.AsyncClient(timeout=30.0) as client:
                    files = {"file": (file.filename, file_content)}
                    data = {
                        "registry_url": registry_url,
                        "username": normalized_username,
                        "workspace_id": workspace_id,
                        "tag": effective_tag,
                        "app_name": final_app_name,
                        "password": normalized_password,
                    }

                    response = await client.post(
                        f"{settings.builder_service_url}/api/v1/build-and-push",
                        files=files,
                        data=data,
                    )
                    response.raise_for_status()
                    build_push_response = response.json()
                    builder_task_id = build_push_response.get("task_id")

                    logger.info(f"Build-and-push task {task_id} submitted: {builder_task_id}")

                # 폴링으로 상태 확인
                max_attempts = 120
                for attempt in range(max_attempts):
                    await asyncio.sleep(5)

                    async with httpx.AsyncClient(timeout=10.0) as client:
                        status_response = await client.get(
                            f"{settings.builder_service_url}/api/v1/tasks/{builder_task_id}",
                            params={"workspace_id": workspace_id}
                        )
                        status_response.raise_for_status()
                        status_data = status_response.json()

                        status = status_data.get("status")
                        logger.info(f"Build-and-push task {task_id} status: {status}")

                        if status in ["completed", "done"]:
                            result = status_data.get("result", {})
                            wasm_path = result.get("wasm_path")
                            
                            # 이미지 URL이 없으면 백엔드에서 조합해서 생성
                            image_url = result.get("image_url") or result.get("image_uri")
                            if not image_url and registry_url and effective_tag:
                                image_url = f"{registry_url}:{effective_tag}"

                            # 상태 업데이트
                            db_client.update_build_task_status(
                                workspace_id,
                                task_id,
                                status="completed",
                                wasm_path=wasm_path,
                                image_url=image_url
                            )

                            logger.info(f"Build-and-push task {task_id} completed: {image_url}")
                            break

                        elif status == "failed":
                            error_msg = status_data.get("error", "Build-and-push failed")
                            
                            db_client.update_build_task_status(
                                workspace_id,
                                task_id,
                                status="failed",
                                error_message=error_msg
                            )
                            logger.error(f"Build-and-push task {task_id} failed: {error_msg}")
                            break

                        else:
                            logger.debug(f"Build-and-push task {task_id} status (no-op update): {status}")

                else:
                    error_msg = "Build-and-push timeout (10 minutes exceeded)"
                    db_client.update_build_task_status(
                        workspace_id,
                        task_id,
                        status="failed",
                        error_message=error_msg
                    )
                    logger.error(f"Build-and-push task {task_id} timed out")

            except httpx.HTTPError as e:
                logger.error(f"Build-and-push task {task_id} HTTP error: {str(e)}")
            except Exception as e:
                logger.error(f"Build-and-push task {task_id} failed: {str(e)}")

        background_tasks.add_task(_build_and_push_wrapper)

        return BuildResponse(
            task_id=task_id, status="pending", message="Build and push task created", source_s3_path=s3_path
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Build-and-push endpoint error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")
