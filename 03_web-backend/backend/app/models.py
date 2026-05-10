"""Pydantic 데이터 모델"""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime


# ===== Workspace 모델 =====
class WorkspaceCreate(BaseModel):
    """워크스페이스 생성 요청"""

    name: str = Field(..., min_length=1, description="워크스페이스 이름")
    description: Optional[str] = Field(None, description="워크스페이스 설명")


class WorkspaceUpdate(BaseModel):
    """워크스페이스 수정 요청"""

    name: Optional[str] = Field(None, min_length=1, description="워크스페이스 이름")
    description: Optional[str] = Field(None, description="워크스페이스 설명")


class Workspace(BaseModel):
    """워크스페이스 응답"""

    id: str
    name: str
    description: Optional[str] = None
    createdAt: datetime
    functionCount: int = 0
    invocations24h: int = 0
    errorRate: float = 0.0


# ===== Function 모델 =====
class FunctionCreate(BaseModel):
    """함수 생성 요청"""

    name: str = Field(..., min_length=1, description="함수 이름")
    description: Optional[str] = Field(None, description="함수 설명")
    runtime: str = Field(default="Python 3.12", description="런타임")
    memory: int = Field(default=256, ge=128, le=1024, description="메모리 (MB)")
    timeout: int = Field(default=30, ge=1, le=900, description="타임아웃 (초)")
    httpMethods: List[str] = Field(
        default=["GET"], description="허용 HTTP 메서드"
    )
    environmentVariables: Dict[str, str] = Field(
        default_factory=dict, description="환경 변수"
    )
    code: str = Field(..., description="Base64 인코딩된 Python 코드")


class FunctionUpdate(BaseModel):
    """함수 수정 요청"""

    name: Optional[str] = Field(None, min_length=1)
    description: Optional[str] = None
    runtime: Optional[str] = None
    memory: Optional[int] = Field(None, ge=128, le=1024)
    timeout: Optional[int] = Field(None, ge=1, le=900)
    httpMethods: Optional[List[str]] = None
    environmentVariables: Optional[Dict[str, str]] = None
    code: Optional[str] = None
    invocationUrl: Optional[str] = None
    lastDeployed: Optional[datetime] = None
    # 배포 상태 확장 대비: 제한 없는 문자열 허용
    status: Optional[str] = None


class FunctionConfig(BaseModel):
    """함수 설정 응답"""

    id: str
    workspaceId: str
    name: str
    description: Optional[str] = None
    runtime: str
    memory: int
    timeout: int
    httpMethods: List[str]
    environmentVariables: Dict[str, str]
    code: str
    invocationUrl: Optional[str] = None
    status: str = "active"
    lastModified: datetime
    lastDeployed: Optional[datetime] = None
    invocations24h: int = 0
    errors24h: int = 0
    avgDuration: float = 0.0


# ===== ExecutionLog 모델 =====
class ExecutionLog(BaseModel):
    """실행 로그"""

    id: str
    functionId: str
    timestamp: datetime
    status: str  # "success" | "error"
    duration: float  # ms
    statusCode: int
    requestBody: Optional[Any] = None
    responseBody: Optional[Any] = None
    logs: List[str] = Field(default_factory=list)
    level: str = "info"  # "info" | "warn" | "error"


class LogsResponse(BaseModel):
    """로그 조회 응답"""

    logs: List[ExecutionLog]
    total: int


# ===== Loki Log 모델 =====
class LokiLogEntry(BaseModel):
    """Loki 로그 엔트리"""

    timestamp: str = Field(..., description="로그 타임스탬프 (나노초)")
    line: str = Field(..., description="로그 메시지")


class LokiLogsResponse(BaseModel):
    """Loki 로그 조회 응답"""

    logs: List[LokiLogEntry] = Field(default_factory=list, description="로그 목록")
    total: int = Field(..., description="전체 로그 수")
    function_id: str = Field(..., description="함수 ID")


# ===== Prometheus Metrics 모델 =====
class PrometheusTimeseriesPoint(BaseModel):
    """Prometheus 타임시리즈 포인트"""

    timestamp: float = Field(..., description="UNIX 타임스탬프 (초)")
    value: float = Field(..., description="메트릭 값")


class PrometheusMetricsData(BaseModel):
    """Prometheus 메트릭 데이터"""

    cpu_total: Optional[float] = Field(
        None,
        description="1분 rate 기준으로 합산된 CPU 사용량 (cores)",
    )
    cpu_series: List[PrometheusTimeseriesPoint] = Field(
        default_factory=list,
        description="조회 윈도우 동안의 CPU 사용률 시계열",
    )
    window_seconds: int = Field(
        default=3600,
        description="조회 기간(초). 기본 1시간.",
    )
    instant_query: str = Field(..., description="사용된 인스턴트 PromQL 쿼리")
    range_query: str = Field(..., description="사용된 구간 PromQL 쿼리")
    raw_instant: Optional[Dict[str, Any]] = Field(
        None, description="원본 인스턴트 쿼리 응답 데이터"
    )
    raw_range: Optional[Dict[str, Any]] = Field(
        None, description="원본 구간 쿼리 응답 데이터"
    )


class PrometheusMetricsResponse(BaseModel):
    """Prometheus 메트릭 조회 응답"""

    status: str = Field(..., description="응답 상태")
    data: PrometheusMetricsData = Field(..., description="메트릭 데이터")
    function_id: str = Field(..., description="함수 ID")


# ===== BuildTask 모델 =====
class BuildTaskResult(BaseModel):
    """빌드 작업 결과"""

    wasm_path: Optional[str] = Field(None, description="WASM 파일 경로")
    image_url: Optional[str] = Field(None, description="ECR 이미지 URL")
    image_uri: Optional[str] = Field(None, description="ECR 이미지 URI (호환 필드)")
    file_path: Optional[str] = Field(None, description="업로드된 파일 경로")


class BuildResponse(BaseModel):
    """빌드 응답"""

    task_id: str = Field(..., description="작업 ID")
    status: str = Field(..., description="작업 상태: pending|running|completed|failed")
    message: str = Field(..., description="상태 메시지")
    source_s3_path: Optional[str] = Field(None, description="S3 소스 파일 경로")


class TaskStatusResponse(BaseModel):
    """작업 상태 조회 응답"""

    task_id: str = Field(..., description="작업 ID")
    status: str = Field(..., description="작업 상태: pending|running|completed|failed")
    result: Optional[BuildTaskResult] = Field(None, description="작업 결과")
    error: Optional[str] = Field(None, description="에러 메시지")


class WorkspaceTaskItem(BaseModel):
    """워크스페이스 작업 목록 항목"""

    task_id: str = Field(..., description="작업 ID")
    status: str = Field(..., description="작업 상태")
    app_name: Optional[str] = Field(None, description="애플리케이션 이름")
    created_at: str = Field(..., description="생성 시간")
    updated_at: str = Field(..., description="수정 시간")
    result: Optional[BuildTaskResult] = Field(None, description="작업 결과")
    error: Optional[str] = Field(None, description="에러 메시지")


class WorkspaceTasksResponse(BaseModel):
    """워크스페이스 작업 목록 응답"""

    workspace_id: str = Field(..., description="워크스페이스 ID")
    tasks: List[WorkspaceTaskItem] = Field(..., description="작업 목록")
    count: int = Field(..., description="작업 개수")


class PushRequest(BaseModel):
    """ECR 푸시 요청"""

    registry_url: str = Field(..., description="ECR 레지스트리 URL")
    username: str = Field(default="AWS", description="레지스트리 사용자명 (IRSA 사용 시 기본값 AWS)")
    password: str = Field(
        default="dummy-password", description="레지스트리 비밀번호 (IRSA 사용 시 더미 값 자동 사용)"
    )
    tag: str = Field(default="sha256", description="이미지 태그")
    app_dir: Optional[str] = Field(None, description="애플리케이션 디렉토리 경로")
    workspace_id: str = Field(..., description="워크스페이스 ID")
    s3_source_path: Optional[str] = Field(None, description="S3 소스 파일 경로")


class ScaffoldRequest(BaseModel):
    """SpinApp 매니페스트 생성 요청"""

    image_ref: str = Field(..., description="이미지 참조 (ECR URL:tag)")
    component: Optional[str] = Field(None, description="컴포넌트 이름")
    replicas: int = Field(default=1, ge=1, description="레플리카 수")
    output_path: Optional[str] = Field(None, description="출력 파일 경로")


class ScaffoldResponse(BaseModel):
    """SpinApp 매니페스트 생성 응답"""

    success: bool = Field(..., description="성공 여부")
    yaml_content: Optional[str] = Field(None, description="생성된 YAML 내용")
    file_path: Optional[str] = Field(None, description="저장된 파일 경로")
    error: Optional[str] = Field(None, description="에러 메시지")


class DeployRequest(BaseModel):
    """K8s 배포 요청"""

    app_name: Optional[str] = Field(None, description="애플리케이션 이름")
    namespace: str = Field(..., description="Kubernetes 네임스페이스")
    service_account: Optional[str] = Field(None, description="ServiceAccount 이름")
    cpu_limit: Optional[str] = Field(None, description="CPU 제한 (예: 500m)")
    memory_limit: Optional[str] = Field(None, description="메모리 제한 (예: 128Mi)")
    cpu_request: Optional[str] = Field(None, description="CPU 요청 (예: 100m)")
    memory_request: Optional[str] = Field(None, description="메모리 요청 (예: 64Mi)")
    image_ref: str = Field(..., description="이미지 참조 (ECR URL:tag)")
    enable_autoscaling: bool = Field(default=True, description="HPA/KEDA 오토스케일링 활성화")
    replicas: int = Field(default=1, ge=1, description="레플리카 수")
    use_spot: bool = Field(default=True, description="Spot 인스턴스 사용 스케줄링")
    custom_tolerations: Optional[List[Dict[str, Any]]] = Field(
        None, description="사용자 정의 tolerations"
    )
    custom_affinity: Optional[Dict[str, Any]] = Field(None, description="사용자 정의 affinity")
    function_id: Optional[str] = Field(None, description="Function ID (로그 구분용)")


class DeployResponse(BaseModel):
    """K8s 배포 응답"""

    app_name: Optional[str] = Field(None, description="배포된 SpinApp 이름")
    namespace: Optional[str] = Field(None, description="배포된 네임스페이스")
    service_name: Optional[str] = Field(None, description="SpinApp이 자동 생성한 Service 이름")
    service_status: str = Field(..., description="Service 상태: found|pending|not_found")
    endpoint: Optional[str] = Field(None, description="Service 엔드포인트")
    enable_autoscaling: Optional[bool] = Field(None, description="오토스케일링 활성화 여부")
    use_spot: Optional[bool] = Field(None, description="Spot 인스턴스 사용 여부")
    error: Optional[str] = Field(None, description="에러 메시지")


class BuildAndPushRequest(BaseModel):
    """빌드 및 푸시 통합 요청"""

    registry_url: str = Field(..., description="ECR 레지스트리 URL")
    username: str = Field(default="AWS", description="레지스트리 사용자명 (IRSA 사용 시 기본값 AWS)")
    password: str = Field(
        default="dummy-password", description="레지스트리 비밀번호 (IRSA 사용 시 더미 값 자동 사용)"
    )
    tag: str = Field(default="sha256", description="이미지 태그")
    app_name: Optional[str] = Field(None, description="애플리케이션 이름")


# ===== 에러 응답 모델 =====
class ErrorDetail(BaseModel):
    """에러 상세"""

    field: Optional[str] = None


class ErrorResponse(BaseModel):
    """에러 응답"""

    error: Dict[str, Any]
