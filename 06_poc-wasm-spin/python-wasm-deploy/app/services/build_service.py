"""
Build Service 모듈

Python 코드를 WASM으로 빌드하는 서비스입니다.
- 코드 검증
- 빌드 생성 및 ID 생성
- WASM 컴파일 (spin build)
- OCI 레지스트리 푸시 (spin registry push)

Requirements: 1.1, 1.2, 1.4, 2.1, 2.2, 2.3, 2.4, 3.1, 3.2, 3.3, 3.4
"""

import os
import subprocess
import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional, Tuple

from ..api.models import Build, BuildStatus, CodeSubmission
from ..config import get_docker_config, get_registry_config
from ..storage.build_storage import BuildStorage, get_build_storage


# 필수 파일 목록
REQUIRED_FILES = ["app.py", "spin.toml"]


@dataclass
class ValidationResult:
    """코드 검증 결과
    
    Attributes:
        is_valid: 검증 통과 여부
        missing_files: 누락된 필수 파일 목록
    """
    is_valid: bool
    missing_files: List[str]


@dataclass
class CompileResult:
    """WASM 컴파일 결과
    
    Attributes:
        success: 컴파일 성공 여부
        wasm_path: 생성된 WASM 파일 경로 (성공 시)
        error_message: 에러 메시지 (실패 시)
    """
    success: bool
    wasm_path: Optional[str] = None
    error_message: Optional[str] = None


@dataclass
class PushResult:
    """OCI 레지스트리 푸시 결과
    
    Attributes:
        success: 푸시 성공 여부
        oci_reference: OCI 참조 URL (성공 시)
        error_message: 에러 메시지 (실패 시)
    """
    success: bool
    oci_reference: Optional[str] = None
    error_message: Optional[str] = None


class BuildService:
    """Python 코드를 WASM으로 빌드하는 서비스
    
    Attributes:
        storage: 빌드 스토리지 인스턴스
    """
    
    def __init__(self, storage: Optional[BuildStorage] = None):
        """BuildService 초기화
        
        Args:
            storage: BuildStorage 인스턴스. None이면 싱글톤 사용.
        """
        self.storage = storage or get_build_storage()
    
    def validate_submission(self, files: Dict[str, str]) -> ValidationResult:
        """제출된 코드 검증
        
        필수 파일(app.py, spin.toml)이 존재하는지 확인합니다.
        
        Args:
            files: 파일명 -> 내용 매핑
            
        Returns:
            ValidationResult: 검증 결과 (is_valid, missing_files)
            
        Requirements: 1.2, 1.4
        """
        # 파일명 정규화 (경로 구분자 통일, 소문자 비교 안함 - 대소문자 구분)
        normalized_files = set()
        for filename in files.keys():
            # 경로에서 파일명만 추출 (서브디렉토리 내 파일도 처리)
            normalized = filename.replace('\\', '/')
            # 루트 레벨 파일명 추출
            parts = normalized.split('/')
            if len(parts) == 1:
                normalized_files.add(parts[0])
            else:
                # 서브디렉토리 내 파일도 전체 경로로 추가
                normalized_files.add(normalized)
                # 루트 레벨 파일도 추가 (마지막 부분)
                normalized_files.add(parts[-1])
        
        missing_files = []
        for required_file in REQUIRED_FILES:
            if required_file not in normalized_files:
                missing_files.append(required_file)
        
        return ValidationResult(
            is_valid=len(missing_files) == 0,
            missing_files=missing_files
        )

    def generate_build_id(self) -> str:
        """고유 빌드 ID 생성
        
        UUID4 기반으로 고유한 빌드 ID를 생성합니다.
        
        Returns:
            고유 빌드 ID 문자열
            
        Requirements: 1.1
        """
        return str(uuid.uuid4())
    
    def create_build(self, submission: CodeSubmission) -> Tuple[Build, Optional[ValidationResult]]:
        """새 빌드 생성 및 시작
        
        1. 코드 검증
        2. 빌드 ID 생성
        3. 작업 공간 생성 및 코드 저장
        4. 빌드 상태 초기화 (PENDING)
        
        Args:
            submission: 코드 제출 정보
            
        Returns:
            (Build, ValidationResult): 빌드 객체와 검증 결과
            검증 실패 시 Build.status는 FAILED
            
        Requirements: 1.1, 1.2, 1.4
        """
        # 1. 코드 검증
        validation = self.validate_submission(submission.files)
        
        # 2. 빌드 ID 생성
        build_id = self.generate_build_id()
        
        # 3. 빌드 객체 생성
        now = datetime.utcnow()
        
        if not validation.is_valid:
            # 검증 실패 시 FAILED 상태로 생성
            build = Build(
                id=build_id,
                app_name=submission.app_name,
                status=BuildStatus.FAILED,
                error_message=f"Missing required files: {', '.join(validation.missing_files)}",
                created_at=now,
                updated_at=now
            )
            self.storage.save_build(build)
            return build, validation
        
        # 검증 성공 시 PENDING 상태로 생성
        build = Build(
            id=build_id,
            app_name=submission.app_name,
            status=BuildStatus.PENDING,
            created_at=now,
            updated_at=now
        )
        
        # 4. 작업 공간 생성 및 코드 저장
        self.storage.create_workspace(build_id)
        self.storage.save_code(build_id, submission.files)
        
        # 5. 빌드 상태 저장
        self.storage.save_build(build)
        
        return build, validation
    
    def get_build(self, build_id: str) -> Optional[Build]:
        """빌드 상태 조회
        
        Args:
            build_id: 빌드 ID
            
        Returns:
            빌드 객체 또는 None
            
        Requirements: 2.5
        """
        return self.storage.get_build(build_id)
    
    def _find_spin_toml_dir(self, workspace_path: str) -> Optional[str]:
        """spin.toml 파일이 있는 디렉토리 찾기
        
        ZIP 파일이 서브디렉토리 구조로 압축된 경우를 처리합니다.
        
        Args:
            workspace_path: 작업 공간 경로
            
        Returns:
            spin.toml이 있는 디렉토리 경로 또는 None
        """
        # 먼저 루트에서 찾기
        if os.path.exists(os.path.join(workspace_path, "spin.toml")):
            return workspace_path
        
        # 서브디렉토리에서 찾기
        for root, dirs, files in os.walk(workspace_path):
            if "spin.toml" in files:
                return root
        
        return None

    def _setup_venv_and_install(self, build_dir: str) -> Tuple[bool, Optional[str], dict]:
        """가상환경 생성 및 requirements.txt 설치
        
        Args:
            build_dir: 빌드 디렉토리 (spin.toml이 있는 곳)
            
        Returns:
            (success, error_message, env): 성공 여부, 에러 메시지, 환경 변수
        """
        venv_path = os.path.join(build_dir, ".venv")
        
        try:
            # 1. 가상환경 생성
            result = subprocess.run(
                ["python3", "-m", "venv", venv_path],
                cwd=build_dir,
                capture_output=True,
                text=True,
                timeout=60
            )
            
            if result.returncode != 0:
                return False, f"Failed to create venv: {result.stderr}", {}
            
            # 2. 환경 변수 설정 (가상환경 활성화)
            env = os.environ.copy()
            env["VIRTUAL_ENV"] = venv_path
            env["PATH"] = os.path.join(venv_path, "bin") + ":" + env.get("PATH", "")
            
            # 3. pip 업그레이드
            pip_path = os.path.join(venv_path, "bin", "pip")
            subprocess.run(
                [pip_path, "install", "--upgrade", "pip"],
                cwd=build_dir,
                capture_output=True,
                text=True,
                timeout=120,
                env=env
            )
            
            # 4. requirements.txt가 있으면 설치
            requirements_path = os.path.join(build_dir, "requirements.txt")
            if os.path.exists(requirements_path):
                result = subprocess.run(
                    [pip_path, "install", "-r", "requirements.txt"],
                    cwd=build_dir,
                    capture_output=True,
                    text=True,
                    timeout=300,
                    env=env
                )
                
                if result.returncode != 0:
                    return False, f"Failed to install requirements: {result.stderr}", {}
            
            # 5. componentize-py 설치 (spin build에 필요)
            result = subprocess.run(
                [pip_path, "install", "componentize-py"],
                cwd=build_dir,
                capture_output=True,
                text=True,
                timeout=120,
                env=env
            )
            
            if result.returncode != 0:
                return False, f"Failed to install componentize-py: {result.stderr}", {}
            
            return True, None, env
            
        except subprocess.TimeoutExpired:
            return False, "Timeout during venv setup", {}
        except Exception as e:
            return False, f"Venv setup error: {str(e)}", {}

    def compile_to_wasm(self, build_id: str) -> CompileResult:
        """WASM 컴파일
        
        1. 가상환경 생성 및 requirements.txt 설치
        2. subprocess로 'spin build' 명령어를 실행하여 WASM 빌드
        빌드 상태: PENDING → BUILDING → SUCCESS/FAILED
        
        Args:
            build_id: 빌드 ID
            
        Returns:
            CompileResult: 컴파일 결과
            
        Requirements: 2.1, 2.2, 2.3, 2.4
        """
        build = self.storage.get_build(build_id)
        if build is None:
            return CompileResult(
                success=False,
                error_message=f"Build not found: {build_id}"
            )
        
        # 상태를 BUILDING으로 업데이트
        self.storage.update_build_status(build_id, BuildStatus.BUILDING)
        
        workspace_path = self.storage.get_workspace_path(build_id)
        
        # spin.toml이 있는 디렉토리 찾기 (서브디렉토리 지원)
        build_dir = self._find_spin_toml_dir(workspace_path)
        if build_dir is None:
            error_msg = "spin.toml not found in workspace"
            self.storage.update_build_status(
                build_id, 
                BuildStatus.FAILED, 
                error_message=error_msg
            )
            return CompileResult(
                success=False,
                error_message=error_msg
            )
        
        try:
            # 1. 가상환경 생성 및 의존성 설치
            venv_success, venv_error, env = self._setup_venv_and_install(build_dir)
            if not venv_success:
                self.storage.update_build_status(
                    build_id, 
                    BuildStatus.FAILED, 
                    error_message=venv_error
                )
                return CompileResult(
                    success=False,
                    error_message=venv_error
                )
            
            # 2. spin build 명령어 실행 (가상환경 활성화된 상태에서)
            result = subprocess.run(
                ["spin", "build"],
                cwd=build_dir,
                capture_output=True,
                text=True,
                timeout=300,  # 5분 타임아웃
                env=env
            )
            
            if result.returncode != 0:
                error_msg = result.stderr or result.stdout or "Unknown build error"
                self.storage.update_build_status(
                    build_id, 
                    BuildStatus.FAILED, 
                    error_message=error_msg
                )
                return CompileResult(
                    success=False,
                    error_message=error_msg
                )
            
            # WASM 파일 경로 찾기 (target 디렉토리에서)
            target_dir = os.path.join(build_dir, "target")
            wasm_path = None
            
            if os.path.exists(target_dir):
                for root, dirs, files in os.walk(target_dir):
                    for file in files:
                        if file.endswith(".wasm"):
                            wasm_path = os.path.join(root, file)
                            break
                    if wasm_path:
                        break
            
            if wasm_path is None:
                # target 디렉토리가 없거나 wasm 파일이 없는 경우
                # spin build가 성공했으면 일단 성공으로 처리
                wasm_path = build_dir
            
            return CompileResult(
                success=True,
                wasm_path=wasm_path
            )
            
        except subprocess.TimeoutExpired:
            error_msg = "Build timeout: exceeded 5 minutes"
            self.storage.update_build_status(
                build_id, 
                BuildStatus.FAILED, 
                error_message=error_msg
            )
            return CompileResult(
                success=False,
                error_message=error_msg
            )
        except FileNotFoundError:
            error_msg = "spin CLI not found. Please install Spin."
            self.storage.update_build_status(
                build_id, 
                BuildStatus.FAILED, 
                error_message=error_msg
            )
            return CompileResult(
                success=False,
                error_message=error_msg
            )
        except Exception as e:
            error_msg = f"Build error: {str(e)}"
            self.storage.update_build_status(
                build_id, 
                BuildStatus.FAILED, 
                error_message=error_msg
            )
            return CompileResult(
                success=False,
                error_message=error_msg
            )

    def push_to_registry(self, build_id: str) -> PushResult:
        """OCI 레지스트리에 WASM 푸시
        
        subprocess로 'spin registry push' 명령어를 실행하여
        빌드된 WASM을 OCI 레지스트리에 푸시합니다.
        
        Args:
            build_id: 빌드 ID
            
        Returns:
            PushResult: 푸시 결과
            
        Requirements: 3.1, 3.2, 3.3, 3.4
        """
        build = self.storage.get_build(build_id)
        if build is None:
            return PushResult(
                success=False,
                error_message=f"Build not found: {build_id}"
            )
        
        # 상태를 PUSHING으로 업데이트
        self.storage.update_build_status(build_id, BuildStatus.PUSHING)
        
        workspace_path = self.storage.get_workspace_path(build_id)
        
        # spin.toml이 있는 디렉토리 찾기 (서브디렉토리 지원)
        build_dir = self._find_spin_toml_dir(workspace_path)
        if build_dir is None:
            error_msg = "spin.toml not found in workspace"
            self.storage.update_build_status(
                build_id, 
                BuildStatus.FAILED, 
                error_message=error_msg
            )
            return PushResult(
                success=False,
                error_message=error_msg
            )
        
        # OCI 참조 URL 생성 (build_id를 태그로 사용)
        registry_config = get_registry_config()
        oci_reference = f"{registry_config.wasm_registry}:{build_id}"
        
        try:
            # Docker 인증 정보 로드
            docker_config = get_docker_config()
            
            # 환경 변수 설정 (가상환경 PATH)
            env = os.environ.copy()
            
            # 가상환경 PATH 추가 (빌드 시 생성된 venv 사용)
            venv_path = os.path.join(build_dir, ".venv")
            if os.path.exists(venv_path):
                env["VIRTUAL_ENV"] = venv_path
                env["PATH"] = os.path.join(venv_path, "bin") + ":" + env.get("PATH", "")
            
            # spin registry login으로 먼저 로그인
            login_result = subprocess.run(
                [
                    "spin", "registry", "login",
                    "-u", docker_config.username,
                    "-p", docker_config.password,
                    docker_config.registry
                ],
                capture_output=True,
                text=True,
                timeout=60,
                env=env
            )
            
            if login_result.returncode != 0:
                error_msg = f"Registry login failed: {login_result.stderr or login_result.stdout}"
                self.storage.update_build_status(
                    build_id, 
                    BuildStatus.FAILED, 
                    error_message=error_msg
                )
                return PushResult(
                    success=False,
                    error_message=error_msg
                )
            
            # spin registry push 명령어 실행 (spin.toml이 있는 디렉토리에서)
            # --build 옵션으로 빌드 후 푸시
            result = subprocess.run(
                ["spin", "registry", "push", "--build", oci_reference],
                cwd=build_dir,
                capture_output=True,
                text=True,
                timeout=300,  # 5분 타임아웃
                env=env
            )
            
            if result.returncode != 0:
                error_msg = result.stderr or result.stdout or "Unknown push error"
                self.storage.update_build_status(
                    build_id, 
                    BuildStatus.FAILED, 
                    error_message=error_msg
                )
                return PushResult(
                    success=False,
                    error_message=error_msg
                )
            
            # 성공 시 상태 업데이트
            self.storage.update_build_status(
                build_id, 
                BuildStatus.SUCCESS, 
                oci_reference=oci_reference
            )
            
            return PushResult(
                success=True,
                oci_reference=oci_reference
            )
            
        except subprocess.TimeoutExpired:
            error_msg = "Push timeout: exceeded 5 minutes"
            self.storage.update_build_status(
                build_id, 
                BuildStatus.FAILED, 
                error_message=error_msg
            )
            return PushResult(
                success=False,
                error_message=error_msg
            )
        except FileNotFoundError:
            error_msg = "spin CLI not found. Please install Spin."
            self.storage.update_build_status(
                build_id, 
                BuildStatus.FAILED, 
                error_message=error_msg
            )
            return PushResult(
                success=False,
                error_message=error_msg
            )
        except Exception as e:
            error_msg = f"Push error: {str(e)}"
            self.storage.update_build_status(
                build_id, 
                BuildStatus.FAILED, 
                error_message=error_msg
            )
            return PushResult(
                success=False,
                error_message=error_msg
            )
    
    def build_and_push(self, submission: CodeSubmission) -> Build:
        """전체 빌드 및 푸시 프로세스 실행
        
        1. 빌드 생성
        2. WASM 컴파일
        3. OCI 레지스트리 푸시
        
        Args:
            submission: 코드 제출 정보
            
        Returns:
            최종 빌드 상태
            
        Requirements: 1.1, 2.1, 3.1
        """
        # 1. 빌드 생성
        build, validation = self.create_build(submission)
        
        if not validation.is_valid:
            return build
        
        # 2. WASM 컴파일
        compile_result = self.compile_to_wasm(build.id)
        
        if not compile_result.success:
            return self.storage.get_build(build.id)
        
        # 3. OCI 레지스트리 푸시
        push_result = self.push_to_registry(build.id)
        
        return self.storage.get_build(build.id)


# 싱글톤 인스턴스
_build_service: Optional[BuildService] = None


def get_build_service() -> BuildService:
    """BuildService 싱글톤 인스턴스 반환"""
    global _build_service
    if _build_service is None:
        _build_service = BuildService()
    return _build_service
