"""
Build Storage 모듈

빌드 작업 공간 및 상태를 관리하는 클래스입니다.
- 빌드 작업 공간 생성/삭제
- 코드 파일 저장/조회
- 빌드 상태 저장/조회/업데이트

Requirements: 1.4, 2.4, 2.5
"""

import io
import os
import shutil
import tempfile
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

from ..api.models import Build, BuildStatus


class BuildStorage:
    """빌드 작업 공간 및 상태를 관리하는 클래스
    
    Attributes:
        base_dir: 빌드 작업 공간의 기본 디렉토리
        _builds: 빌드 상태를 메모리에 저장하는 딕셔너리
    """
    
    def __init__(self, base_dir: Optional[str] = None):
        """BuildStorage 초기화
        
        Args:
            base_dir: 빌드 작업 공간의 기본 디렉토리.
                     None이면 시스템 임시 디렉토리 사용.
        """
        if base_dir is None:
            base_dir = os.path.join(tempfile.gettempdir(), "wasm-builds")
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self._builds: Dict[str, Build] = {}
    
    def create_workspace(self, build_id: str) -> str:
        """빌드 작업 공간 생성
        
        Args:
            build_id: 고유 빌드 ID
            
        Returns:
            생성된 작업 공간의 경로
        """
        workspace_path = self.base_dir / build_id
        workspace_path.mkdir(parents=True, exist_ok=True)
        return str(workspace_path)
    
    def get_workspace_path(self, build_id: str) -> str:
        """빌드 작업 공간 경로 조회
        
        Args:
            build_id: 고유 빌드 ID
            
        Returns:
            작업 공간의 경로
        """
        return str(self.base_dir / build_id)

    def extract_zip(self, build_id: str, zip_data: bytes) -> Dict[str, str]:
        """ZIP 파일을 작업 공간에 압축 해제하고 파일 목록 반환
        
        Args:
            build_id: 빌드 ID
            zip_data: ZIP 파일 바이너리 데이터
            
        Returns:
            추출된 파일명 -> 내용 매핑 (텍스트 파일만)
            
        Raises:
            ValueError: ZIP 파일이 유효하지 않거나 손상된 경우
            
        Requirements: 1.2, 1.3, 1.5
        """
        # ZIP 파일 유효성 검사
        if not zip_data:
            raise ValueError("ZIP extraction failed: empty data")
        
        try:
            zip_buffer = io.BytesIO(zip_data)
            
            # ZIP 파일 형식 검증
            if not zipfile.is_zipfile(zip_buffer):
                raise ValueError("ZIP extraction failed: invalid ZIP format")
            
            zip_buffer.seek(0)
            
            with zipfile.ZipFile(zip_buffer, 'r') as zf:
                # ZIP 파일 무결성 검사
                bad_file = zf.testzip()
                if bad_file is not None:
                    raise ValueError(f"ZIP extraction failed: corrupted file '{bad_file}'")
                
                # 작업 공간 경로 확인/생성
                workspace_path = self.base_dir / build_id
                if not workspace_path.exists():
                    workspace_path.mkdir(parents=True, exist_ok=True)
                
                extracted_files: Dict[str, str] = {}
                
                for member in zf.infolist():
                    # 디렉토리는 건너뛰기
                    if member.is_dir():
                        continue
                    
                    # 파일명 정규화 (경로 구분자 통일)
                    filename = member.filename.replace('\\', '/')
                    
                    # 보안: 경로 탐색 공격 방지
                    if filename.startswith('/') or '..' in filename:
                        continue
                    
                    # 파일 추출
                    target_path = workspace_path / filename
                    target_path.parent.mkdir(parents=True, exist_ok=True)
                    
                    # 파일 내용 읽기
                    file_data = zf.read(member.filename)
                    
                    # 파일 저장
                    target_path.write_bytes(file_data)
                    
                    # 텍스트 파일로 디코딩 시도
                    try:
                        content = file_data.decode('utf-8')
                        extracted_files[filename] = content
                    except UnicodeDecodeError:
                        # 바이너리 파일은 내용을 반환하지 않지만 추출은 됨
                        # 파일 목록에는 빈 문자열로 표시
                        extracted_files[filename] = ""
                
                return extracted_files
                
        except zipfile.BadZipFile as e:
            raise ValueError(f"ZIP extraction failed: {str(e)}")
        except Exception as e:
            if isinstance(e, ValueError):
                raise
            raise ValueError(f"ZIP extraction failed: {str(e)}")

    def workspace_exists(self, build_id: str) -> bool:
        """빌드 작업 공간 존재 여부 확인
        
        Args:
            build_id: 고유 빌드 ID
            
        Returns:
            작업 공간이 존재하면 True, 아니면 False
        """
        workspace_path = self.base_dir / build_id
        return workspace_path.exists() and workspace_path.is_dir()
    
    def save_code(self, build_id: str, files: Dict[str, str]) -> None:
        """코드 파일 저장
        
        Args:
            build_id: 고유 빌드 ID
            files: 파일명 -> 내용 매핑
            
        Raises:
            FileNotFoundError: 작업 공간이 존재하지 않을 때
        """
        workspace_path = self.base_dir / build_id
        if not workspace_path.exists():
            raise FileNotFoundError(f"Workspace not found: {build_id}")
        
        for filename, content in files.items():
            file_path = workspace_path / filename
            # 서브디렉토리가 있는 경우 생성
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(content, encoding="utf-8")
    
    def get_code(self, build_id: str, filename: str) -> str:
        """코드 파일 조회
        
        Args:
            build_id: 고유 빌드 ID
            filename: 파일명
            
        Returns:
            파일 내용
            
        Raises:
            FileNotFoundError: 파일이 존재하지 않을 때
        """
        file_path = self.base_dir / build_id / filename
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {filename} in build {build_id}")
        return file_path.read_text(encoding="utf-8")
    
    def get_all_files(self, build_id: str) -> Dict[str, str]:
        """빌드 작업 공간의 모든 파일 조회
        
        Args:
            build_id: 고유 빌드 ID
            
        Returns:
            파일명 -> 내용 매핑
            
        Raises:
            FileNotFoundError: 작업 공간이 존재하지 않을 때
        """
        workspace_path = self.base_dir / build_id
        if not workspace_path.exists():
            raise FileNotFoundError(f"Workspace not found: {build_id}")
        
        files = {}
        for file_path in workspace_path.rglob("*"):
            if file_path.is_file():
                relative_path = file_path.relative_to(workspace_path)
                files[str(relative_path)] = file_path.read_text(encoding="utf-8")
        return files
    
    def cleanup_workspace(self, build_id: str) -> None:
        """작업 공간 정리 (삭제)
        
        Args:
            build_id: 고유 빌드 ID
        """
        workspace_path = self.base_dir / build_id
        if workspace_path.exists():
            shutil.rmtree(workspace_path)

    def save_build(self, build: Build) -> None:
        """빌드 상태 저장
        
        Args:
            build: 저장할 빌드 객체
        """
        self._builds[build.id] = build
    
    def get_build(self, build_id: str) -> Optional[Build]:
        """빌드 상태 조회
        
        Args:
            build_id: 고유 빌드 ID
            
        Returns:
            빌드 객체 또는 None (존재하지 않을 때)
        """
        return self._builds.get(build_id)
    
    def update_build_status(
        self, 
        build_id: str, 
        status: BuildStatus, 
        error_message: Optional[str] = None,
        oci_reference: Optional[str] = None
    ) -> Optional[Build]:
        """빌드 상태 업데이트
        
        Args:
            build_id: 고유 빌드 ID
            status: 새로운 빌드 상태
            error_message: 에러 메시지 (실패 시)
            oci_reference: OCI 이미지 참조 (성공 시)
            
        Returns:
            업데이트된 빌드 객체 또는 None (존재하지 않을 때)
        """
        build = self._builds.get(build_id)
        if build is None:
            return None
        
        # Pydantic 모델은 불변이므로 새 객체 생성
        updated_build = Build(
            id=build.id,
            app_name=build.app_name,
            status=status,
            oci_reference=oci_reference if oci_reference is not None else build.oci_reference,
            error_message=error_message if error_message is not None else build.error_message,
            created_at=build.created_at,
            updated_at=datetime.utcnow()
        )
        self._builds[build_id] = updated_build
        return updated_build
    
    def delete_build(self, build_id: str) -> bool:
        """빌드 상태 삭제
        
        Args:
            build_id: 고유 빌드 ID
            
        Returns:
            삭제 성공 여부
        """
        if build_id in self._builds:
            del self._builds[build_id]
            return True
        return False
    
    def list_builds(self) -> Dict[str, Build]:
        """모든 빌드 목록 조회
        
        Returns:
            빌드 ID -> 빌드 객체 매핑
        """
        return dict(self._builds)


# 싱글톤 인스턴스
_build_storage: Optional[BuildStorage] = None


def get_build_storage() -> BuildStorage:
    """BuildStorage 싱글톤 인스턴스 반환"""
    global _build_storage
    if _build_storage is None:
        _build_storage = BuildStorage()
    return _build_storage
