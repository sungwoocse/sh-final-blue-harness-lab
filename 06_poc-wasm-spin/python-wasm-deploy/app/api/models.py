"""
Pydantic 데이터 모델 정의

이 모듈은 Python WASM Deploy 플랫폼에서 사용하는 모든 데이터 모델을 정의합니다.
- CodeSubmission: 사용자 코드 제출
- Build/BuildStatus: 빌드 상태 및 정보
- DeployRequest: 배포 요청
- AppStatus: 앱 상태 정보
"""

from datetime import datetime
from enum import Enum
from typing import Dict, Optional

from pydantic import BaseModel, Field


class BuildStatus(str, Enum):
    """빌드 상태를 나타내는 열거형
    
    상태 전이: PENDING → BUILDING → (PUSHING → SUCCESS | FAILED)
    또는: PENDING → BUILDING → FAILED
    """
    PENDING = "pending"
    BUILDING = "building"
    PUSHING = "pushing"
    SUCCESS = "success"
    FAILED = "failed"


class CodeSubmission(BaseModel):
    """사용자 코드 제출 모델
    
    Attributes:
        app_name: 애플리케이션 이름
        files: 파일명 -> 내용 매핑 (필수: app.py, spin.toml)
    """
    app_name: str = Field(..., description="애플리케이션 이름")
    files: Dict[str, str] = Field(
        ..., 
        description="파일명 -> 내용 매핑 (필수: app.py, spin.toml)"
    )


class Build(BaseModel):
    """빌드 정보 모델
    
    Attributes:
        id: 고유 빌드 ID
        app_name: 애플리케이션 이름
        status: 빌드 상태
        oci_reference: OCI 이미지 참조 (성공 시)
        error_message: 에러 메시지 (실패 시)
        created_at: 생성 시간
        updated_at: 업데이트 시간
    """
    id: str = Field(..., description="고유 빌드 ID")
    app_name: str = Field(..., description="애플리케이션 이름")
    status: BuildStatus = Field(
        default=BuildStatus.PENDING, 
        description="빌드 상태"
    )
    oci_reference: Optional[str] = Field(
        default=None, 
        description="OCI 이미지 참조 (성공 시)"
    )
    error_message: Optional[str] = Field(
        default=None, 
        description="에러 메시지 (실패 시)"
    )
    created_at: datetime = Field(
        default_factory=datetime.utcnow, 
        description="생성 시간"
    )
    updated_at: datetime = Field(
        default_factory=datetime.utcnow, 
        description="업데이트 시간"
    )


class DeployRequest(BaseModel):
    """배포 요청 모델
    
    Attributes:
        build_id: 빌드 ID
        namespace: 배포 네임스페이스 (기본값: default)
        replicas: 레플리카 수 (기본값: 1)
    """
    build_id: str = Field(..., description="빌드 ID")
    namespace: str = Field(default="default", description="배포 네임스페이스")
    replicas: int = Field(default=1, ge=1, description="레플리카 수")


class AppStatus(BaseModel):
    """앱 상태 정보 모델
    
    Attributes:
        name: 앱 이름
        namespace: 네임스페이스
        oci_reference: OCI 이미지 참조
        replicas: 설정된 레플리카 수
        ready_replicas: 준비된 레플리카 수
        endpoint: 외부 엔드포인트
        status: 상태 (Running, Pending, Failed)
    """
    name: str = Field(..., description="앱 이름")
    namespace: str = Field(..., description="네임스페이스")
    oci_reference: str = Field(..., description="OCI 이미지 참조")
    replicas: int = Field(..., ge=0, description="설정된 레플리카 수")
    ready_replicas: int = Field(..., ge=0, description="준비된 레플리카 수")
    endpoint: Optional[str] = Field(default=None, description="외부 엔드포인트")
    status: str = Field(..., description="상태 (Running, Pending, Failed)")
