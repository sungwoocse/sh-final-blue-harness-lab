"""
REST API 라우트 정의

이 모듈은 Python WASM Deploy 플랫폼의 REST API 엔드포인트를 정의합니다.
- 빌드 API: ZIP 파일 업로드, 빌드 상태 조회
- 배포 API: 앱 배포, 상태 조회, 삭제, 목록 조회

Requirements: 1.1, 1.2, 1.3, 2.5, 4.1, 5.1, 6.1
"""

from typing import List, Optional

from fastapi import APIRouter, File, Form, HTTPException, UploadFile, BackgroundTasks
from pydantic import BaseModel

from .models import AppStatus, Build, BuildStatus, CodeSubmission, DeployRequest
from ..services.build_service import BuildService, get_build_service
from ..services.deploy_service import DeployService, get_deploy_service
from ..storage.build_storage import get_build_storage


# ============================================================================
# 빌드 API 라우터
# ============================================================================

build_router = APIRouter(prefix="/api/v1/builds", tags=["builds"])


class BuildResponse(BaseModel):
    """빌드 응답 모델"""
    id: str
    app_name: str
    status: BuildStatus
    oci_reference: Optional[str] = None
    error_message: Optional[str] = None


class BuildErrorResponse(BaseModel):
    """빌드 에러 응답 모델"""
    error: str
    message: Optional[str] = None
    files: Optional[List[str]] = None


def _run_build_and_push(build_service: BuildService, build_id: str):
    """백그라운드에서 빌드 및 푸시 실행"""
    # WASM 컴파일
    compile_result = build_service.compile_to_wasm(build_id)
    
    if compile_result.success:
        # OCI 레지스트리 푸시
        build_service.push_to_registry(build_id)


@build_router.post(
    "",
    response_model=BuildResponse,
    responses={
        400: {"model": BuildErrorResponse, "description": "Invalid ZIP or missing files"}
    },
    summary="ZIP 파일 업로드 및 빌드 시작",
    description="ZIP 파일을 업로드하여 WASM 빌드를 시작합니다. 빌드는 백그라운드에서 실행됩니다."
)
async def create_build(
    background_tasks: BackgroundTasks,
    app_name: str = Form(..., description="애플리케이션 이름"),
    file: UploadFile = File(..., description="ZIP 파일 (application/zip)")
):
    """
    ZIP 파일 업로드 및 빌드 시작
    
    - **app_name**: 애플리케이션 이름
    - **file**: Python Spin 프로젝트가 포함된 ZIP 파일
    
    ZIP 파일에는 다음 필수 파일이 포함되어야 합니다:
    - app.py: Python 애플리케이션 코드
    - spin.toml: Spin 설정 파일
    
    Requirements: 1.1, 1.2, 1.3
    """
    build_service = get_build_service()
    storage = get_build_storage()
    
    # ZIP 파일 읽기
    try:
        zip_data = await file.read()
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail={"error": "invalid_zip", "message": f"Failed to read file: {str(e)}"}
        )
    
    # 빌드 ID 생성 및 작업 공간 생성
    build_id = build_service.generate_build_id()
    storage.create_workspace(build_id)
    
    # ZIP 파일 압축 해제
    try:
        extracted_files = storage.extract_zip(build_id, zip_data)
    except ValueError as e:
        # 작업 공간 정리
        storage.cleanup_workspace(build_id)
        raise HTTPException(
            status_code=400,
            detail={"error": "invalid_zip", "message": str(e)}
        )
    
    # 코드 제출 객체 생성
    submission = CodeSubmission(app_name=app_name, files=extracted_files)
    
    # 필수 파일 검증
    validation = build_service.validate_submission(extracted_files)
    
    if not validation.is_valid:
        # 작업 공간 정리
        storage.cleanup_workspace(build_id)
        raise HTTPException(
            status_code=400,
            detail={
                "error": "missing_files",
                "message": f"Missing required files: {', '.join(validation.missing_files)}",
                "files": validation.missing_files
            }
        )
    
    # 빌드 생성 (검증 통과)
    build, _ = build_service.create_build(submission)
    
    # 백그라운드에서 빌드 및 푸시 실행
    background_tasks.add_task(_run_build_and_push, build_service, build.id)
    
    return BuildResponse(
        id=build.id,
        app_name=build.app_name,
        status=build.status,
        oci_reference=build.oci_reference,
        error_message=build.error_message
    )


@build_router.get(
    "/{build_id}",
    response_model=BuildResponse,
    responses={
        404: {"description": "Build not found"}
    },
    summary="빌드 상태 조회",
    description="빌드 ID로 빌드 상태를 조회합니다."
)
async def get_build(build_id: str):
    """
    빌드 상태 조회
    
    - **build_id**: 빌드 ID
    
    Requirements: 2.5
    """
    build_service = get_build_service()
    build = build_service.get_build(build_id)
    
    if build is None:
        raise HTTPException(
            status_code=404,
            detail={"error": "build_not_found", "message": f"Build not found: {build_id}"}
        )
    
    return BuildResponse(
        id=build.id,
        app_name=build.app_name,
        status=build.status,
        oci_reference=build.oci_reference,
        error_message=build.error_message
    )


# ============================================================================
# 배포 API 라우터
# ============================================================================

deploy_router = APIRouter(prefix="/api/v1/apps", tags=["apps"])


class DeployResponse(BaseModel):
    """배포 응답 모델"""
    success: bool
    app_name: Optional[str] = None
    namespace: Optional[str] = None
    endpoint: Optional[str] = None
    message: Optional[str] = None


class DeleteResponse(BaseModel):
    """삭제 응답 모델"""
    success: bool
    message: Optional[str] = None


class ErrorResponse(BaseModel):
    """에러 응답 모델"""
    error: str
    message: Optional[str] = None


@deploy_router.post(
    "",
    response_model=DeployResponse,
    responses={
        400: {"model": ErrorResponse, "description": "Build not ready or invalid request"},
        404: {"model": ErrorResponse, "description": "Build not found"}
    },
    summary="앱 배포",
    description="빌드된 WASM 앱을 Kubernetes 클러스터에 배포합니다."
)
async def deploy_app(deploy_request: DeployRequest):
    """
    앱 배포
    
    - **build_id**: 배포할 빌드 ID
    - **namespace**: Kubernetes 네임스페이스 (기본값: default)
    - **replicas**: 레플리카 수 (기본값: 1)
    
    Requirements: 4.1
    """
    build_service = get_build_service()
    deploy_service = get_deploy_service()
    
    # 빌드 조회
    build = build_service.get_build(deploy_request.build_id)
    
    if build is None:
        raise HTTPException(
            status_code=404,
            detail={"error": "build_not_found", "message": f"Build not found: {deploy_request.build_id}"}
        )
    
    # 빌드 상태 확인
    if build.status != BuildStatus.SUCCESS:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "build_not_ready",
                "message": f"Build is not ready. Current status: {build.status.value}"
            }
        )
    
    # OCI 참조 확인
    if not build.oci_reference:
        raise HTTPException(
            status_code=400,
            detail={"error": "build_not_ready", "message": "Build has no OCI reference"}
        )
    
    # 배포 실행
    result = deploy_service.deploy_app(deploy_request, build.oci_reference)
    
    if not result.success:
        raise HTTPException(
            status_code=500,
            detail={"error": "k8s_error", "message": result.error_message}
        )
    
    return DeployResponse(
        success=True,
        app_name=result.app_name,
        namespace=result.namespace,
        endpoint=result.endpoint,
        message="App deployed successfully"
    )


@deploy_router.get(
    "",
    response_model=List[AppStatus],
    summary="앱 목록 조회",
    description="네임스페이스의 모든 SpinApp 목록을 조회합니다."
)
async def list_apps(namespace: str = "default"):
    """
    앱 목록 조회
    
    - **namespace**: Kubernetes 네임스페이스 (기본값: default)
    
    Requirements: 5.1
    """
    deploy_service = get_deploy_service()
    apps = deploy_service.list_apps(namespace)
    return apps


@deploy_router.get(
    "/{app_name}",
    response_model=AppStatus,
    responses={
        404: {"model": ErrorResponse, "description": "App not found"}
    },
    summary="앱 상태 조회",
    description="앱 이름으로 SpinApp 상태를 조회합니다."
)
async def get_app_status(app_name: str, namespace: str = "default"):
    """
    앱 상태 조회
    
    - **app_name**: 앱 이름
    - **namespace**: Kubernetes 네임스페이스 (기본값: default)
    
    Requirements: 5.1
    """
    deploy_service = get_deploy_service()
    app_status = deploy_service.get_app_status(app_name, namespace)
    
    if app_status is None:
        raise HTTPException(
            status_code=404,
            detail={"error": "app_not_found", "message": f"App not found: {app_name}"}
        )
    
    return app_status


@deploy_router.delete(
    "/{app_name}",
    response_model=DeleteResponse,
    responses={
        404: {"model": ErrorResponse, "description": "App not found"}
    },
    summary="앱 삭제",
    description="SpinApp 리소스를 삭제합니다."
)
async def delete_app(app_name: str, namespace: str = "default"):
    """
    앱 삭제
    
    - **app_name**: 앱 이름
    - **namespace**: Kubernetes 네임스페이스 (기본값: default)
    
    Requirements: 6.1
    """
    deploy_service = get_deploy_service()
    result = deploy_service.delete_app(app_name, namespace)
    
    if not result.success:
        if "not found" in (result.error_message or "").lower():
            raise HTTPException(
                status_code=404,
                detail={"error": "app_not_found", "message": result.error_message}
            )
        raise HTTPException(
            status_code=500,
            detail={"error": "k8s_error", "message": result.error_message}
        )
    
    return DeleteResponse(
        success=True,
        message=f"App '{app_name}' deleted successfully"
    )
