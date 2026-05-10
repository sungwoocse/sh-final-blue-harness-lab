"""
Deploy Service 모듈

SpinApp 리소스를 관리하는 서비스입니다.
- SpinApp 매니페스트 생성 (spin kube scaffold)
- Kubernetes 배포 (spin kube deploy)
- 앱 상태 조회
- 앱 삭제

Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 5.1, 5.2, 5.3, 6.1, 6.2, 6.3
"""

import json
import os
import subprocess
from dataclasses import dataclass
from typing import List, Optional

from ..api.models import AppStatus, DeployRequest
from ..config import get_kubernetes_config


@dataclass
class ScaffoldResult:
    """SpinApp 매니페스트 생성 결과
    
    Attributes:
        success: 생성 성공 여부
        manifest: 생성된 YAML 매니페스트 (성공 시)
        error_message: 에러 메시지 (실패 시)
    """
    success: bool
    manifest: Optional[str] = None
    error_message: Optional[str] = None


@dataclass
class DeployResult:
    """배포 결과
    
    Attributes:
        success: 배포 성공 여부
        app_name: 앱 이름
        namespace: 네임스페이스
        endpoint: 외부 엔드포인트 (성공 시)
        error_message: 에러 메시지 (실패 시)
    """
    success: bool
    app_name: Optional[str] = None
    namespace: Optional[str] = None
    endpoint: Optional[str] = None
    error_message: Optional[str] = None


@dataclass
class DeleteResult:
    """앱 삭제 결과
    
    Attributes:
        success: 삭제 성공 여부
        error_message: 에러 메시지 (실패 시)
    """
    success: bool
    error_message: Optional[str] = None


class DeployService:
    """SpinApp 리소스를 관리하는 서비스
    
    subprocess를 사용하여 spin kube 명령어를 실행합니다.
    """
    
    def __init__(self):
        """DeployService 초기화"""
        self._kube_config = None
    
    def _get_kube_env(self) -> dict:
        """Kubernetes 환경 변수 설정
        
        Returns:
            환경 변수 딕셔너리
        """
        env = os.environ.copy()
        try:
            kube_config = get_kubernetes_config()
            env["KUBECONFIG"] = kube_config.config_path
        except FileNotFoundError:
            # kube-config 파일이 없으면 기본 설정 사용
            pass
        return env
    
    def scaffold_app(
        self, 
        oci_reference: str, 
        app_name: str, 
        namespace: str = "default",
        replicas: int = 1
    ) -> ScaffoldResult:
        """SpinApp 매니페스트 생성
        
        subprocess로 'spin kube scaffold' 명령어를 실행하여 매니페스트를 생성합니다.
        wasmtime-spin-v2 RuntimeClass를 사용하도록 설정합니다.
        
        Args:
            oci_reference: OCI 이미지 참조 URL
            app_name: 애플리케이션 이름
            namespace: Kubernetes 네임스페이스 (기본값: default)
            replicas: 레플리카 수 (기본값: 1)
            
        Returns:
            ScaffoldResult: 매니페스트 생성 결과
            
        Requirements: 4.1, 4.3
        """
        try:
            env = self._get_kube_env()
            
            # spin kube scaffold 명령어 실행
            # --runtime-class-name: wasmtime-spin-v2 RuntimeClass 설정
            cmd = [
                "spin", "kube", "scaffold",
                "--from", oci_reference,
                "--runtime-class-name", "wasmtime-spin-v2",
                "--replicas", str(replicas),
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=60,
                env=env
            )
            
            if result.returncode != 0:
                error_msg = result.stderr or result.stdout or "Unknown scaffold error"
                return ScaffoldResult(
                    success=False,
                    error_message=error_msg
                )
            
            # 생성된 매니페스트 반환
            manifest = result.stdout
            
            return ScaffoldResult(
                success=True,
                manifest=manifest
            )
            
        except subprocess.TimeoutExpired:
            return ScaffoldResult(
                success=False,
                error_message="Scaffold timeout: exceeded 60 seconds"
            )
        except FileNotFoundError:
            return ScaffoldResult(
                success=False,
                error_message="spin CLI not found. Please install Spin with kube plugin."
            )
        except Exception as e:
            return ScaffoldResult(
                success=False,
                error_message=f"Scaffold error: {str(e)}"
            )


    def deploy_app(self, deploy_request: DeployRequest, oci_reference: str) -> DeployResult:
        """SpinApp 배포
        
        kubectl apply를 사용하여 SpinApp을 배포합니다.
        spin kube deploy는 runtime-class-name 옵션을 지원하지 않으므로
        scaffold로 매니페스트를 생성하고 kubectl로 적용합니다.
        
        Args:
            deploy_request: 배포 요청 정보
            oci_reference: OCI 이미지 참조 URL
            
        Returns:
            DeployResult: 배포 결과
            
        Requirements: 4.2, 4.4, 4.5
        """
        try:
            env = self._get_kube_env()
            
            # OCI 참조에서 앱 이름 추출 (태그 부분)
            app_name = oci_reference.split(":")[-1] if ":" in oci_reference else oci_reference.split("/")[-1]
            
            # SpinApp 매니페스트 생성 (kubectl apply 사용)
            manifest = f"""apiVersion: core.spinkube.dev/v1alpha1
kind: SpinApp
metadata:
  name: {app_name}
  namespace: {deploy_request.namespace}
spec:
  image: "{oci_reference}"
  executor: containerd-shim-spin
  replicas: {deploy_request.replicas}
"""
            
            # kubectl apply로 배포 (stdin으로 매니페스트 전달)
            cmd = ["kubectl", "apply", "-f", "-"]
            
            result = subprocess.run(
                cmd,
                input=manifest,
                capture_output=True,
                text=True,
                timeout=120,  # 배포는 더 오래 걸릴 수 있음
                env=env
            )
            
            if result.returncode != 0:
                error_msg = result.stderr or result.stdout or "Unknown deploy error"
                return DeployResult(
                    success=False,
                    error_message=error_msg
                )
            
            return DeployResult(
                success=True,
                app_name=app_name,
                namespace=deploy_request.namespace,
                endpoint=None  # 엔드포인트는 상태 조회에서 확인
            )
            
        except subprocess.TimeoutExpired:
            return DeployResult(
                success=False,
                error_message="Deploy timeout: exceeded 120 seconds"
            )
        except FileNotFoundError:
            return DeployResult(
                success=False,
                error_message="spin CLI not found. Please install Spin with kube plugin."
            )
        except Exception as e:
            return DeployResult(
                success=False,
                error_message=f"Deploy error: {str(e)}"
            )


    def get_app_status(self, app_name: str, namespace: str = "default") -> Optional[AppStatus]:
        """앱 상태 조회
        
        kubectl을 사용하여 SpinApp 리소스 상태를 조회합니다.
        
        Args:
            app_name: 앱 이름
            namespace: Kubernetes 네임스페이스 (기본값: default)
            
        Returns:
            AppStatus 객체 또는 None (앱이 존재하지 않을 때)
            
        Requirements: 5.1, 5.2, 5.3
        """
        try:
            env = self._get_kube_env()
            
            # kubectl get spinapp 명령어로 SpinApp 리소스 조회
            cmd = [
                "kubectl", "get", "spinapp", app_name,
                "-n", namespace,
                "-o", "json"
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30,
                env=env
            )
            
            if result.returncode != 0:
                # 앱이 존재하지 않는 경우
                if "not found" in result.stderr.lower() or "notfound" in result.stderr.lower():
                    return None
                # 다른 에러의 경우도 None 반환
                return None
            
            # JSON 파싱
            spinapp_data = json.loads(result.stdout)
            
            # SpinApp 리소스에서 정보 추출
            metadata = spinapp_data.get("metadata", {})
            spec = spinapp_data.get("spec", {})
            status = spinapp_data.get("status", {})
            
            # 레플리카 정보
            replicas = spec.get("replicas", 1)
            ready_replicas = status.get("readyReplicas", 0)
            
            # 상태 결정
            conditions = status.get("conditions", [])
            app_status = "Pending"
            for condition in conditions:
                if condition.get("type") == "Ready":
                    if condition.get("status") == "True":
                        app_status = "Running"
                    elif condition.get("reason") == "Failed":
                        app_status = "Failed"
                    break
            
            # ready_replicas가 replicas와 같으면 Running
            if ready_replicas >= replicas and replicas > 0:
                app_status = "Running"
            elif ready_replicas == 0 and replicas > 0:
                # 아직 준비 안됨
                if app_status != "Failed":
                    app_status = "Pending"
            
            # OCI 참조
            oci_reference = spec.get("image", "")
            
            # 엔드포인트 조회 (Service에서)
            endpoint = self._get_app_endpoint(app_name, namespace)
            
            return AppStatus(
                name=metadata.get("name", app_name),
                namespace=metadata.get("namespace", namespace),
                oci_reference=oci_reference,
                replicas=replicas,
                ready_replicas=ready_replicas,
                endpoint=endpoint,
                status=app_status
            )
            
        except subprocess.TimeoutExpired:
            return None
        except FileNotFoundError:
            return None
        except json.JSONDecodeError:
            return None
        except Exception:
            return None
    
    def _get_app_endpoint(self, app_name: str, namespace: str) -> Optional[str]:
        """앱의 외부 엔드포인트 조회
        
        Service 리소스에서 외부 IP 또는 NodePort를 조회합니다.
        
        Args:
            app_name: 앱 이름
            namespace: Kubernetes 네임스페이스
            
        Returns:
            엔드포인트 URL 또는 None
        """
        try:
            env = self._get_kube_env()
            
            # Service 조회
            cmd = [
                "kubectl", "get", "service", app_name,
                "-n", namespace,
                "-o", "json"
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30,
                env=env
            )
            
            if result.returncode != 0:
                return None
            
            svc_data = json.loads(result.stdout)
            spec = svc_data.get("spec", {})
            status = svc_data.get("status", {})
            
            # LoadBalancer 타입인 경우
            if spec.get("type") == "LoadBalancer":
                ingress = status.get("loadBalancer", {}).get("ingress", [])
                if ingress:
                    ip = ingress[0].get("ip") or ingress[0].get("hostname")
                    port = spec.get("ports", [{}])[0].get("port", 80)
                    return f"http://{ip}:{port}"
            
            # NodePort 타입인 경우
            if spec.get("type") == "NodePort":
                node_port = spec.get("ports", [{}])[0].get("nodePort")
                if node_port:
                    return f"http://<node-ip>:{node_port}"
            
            # ClusterIP인 경우
            cluster_ip = spec.get("clusterIP")
            if cluster_ip and cluster_ip != "None":
                port = spec.get("ports", [{}])[0].get("port", 80)
                return f"http://{cluster_ip}:{port}"
            
            return None
            
        except Exception:
            return None


    def delete_app(self, app_name: str, namespace: str = "default") -> DeleteResult:
        """앱 삭제
        
        kubectl을 사용하여 SpinApp 리소스를 삭제합니다.
        
        Args:
            app_name: 앱 이름
            namespace: Kubernetes 네임스페이스 (기본값: default)
            
        Returns:
            DeleteResult: 삭제 결과
            
        Requirements: 6.1, 6.2, 6.3
        """
        try:
            env = self._get_kube_env()
            
            # 먼저 앱이 존재하는지 확인
            existing_app = self.get_app_status(app_name, namespace)
            if existing_app is None:
                return DeleteResult(
                    success=False,
                    error_message=f"App not found: {app_name} in namespace {namespace}"
                )
            
            # kubectl delete spinapp 명령어 실행
            cmd = [
                "kubectl", "delete", "spinapp", app_name,
                "-n", namespace,
                "--wait=true",
                "--timeout=60s"
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=90,
                env=env
            )
            
            if result.returncode != 0:
                error_msg = result.stderr or result.stdout or "Unknown delete error"
                # "not found" 에러는 이미 삭제된 것으로 처리
                if "not found" in error_msg.lower():
                    return DeleteResult(
                        success=False,
                        error_message=f"App not found: {app_name}"
                    )
                return DeleteResult(
                    success=False,
                    error_message=error_msg
                )
            
            return DeleteResult(success=True)
            
        except subprocess.TimeoutExpired:
            return DeleteResult(
                success=False,
                error_message="Delete timeout: exceeded 90 seconds"
            )
        except FileNotFoundError:
            return DeleteResult(
                success=False,
                error_message="kubectl not found. Please install kubectl."
            )
        except Exception as e:
            return DeleteResult(
                success=False,
                error_message=f"Delete error: {str(e)}"
            )

    def list_apps(self, namespace: str = "default") -> List[AppStatus]:
        """앱 목록 조회
        
        kubectl을 사용하여 네임스페이스의 모든 SpinApp 리소스를 조회합니다.
        
        Args:
            namespace: Kubernetes 네임스페이스 (기본값: default)
            
        Returns:
            AppStatus 객체 리스트
        """
        try:
            env = self._get_kube_env()
            
            # kubectl get spinapps 명령어로 모든 SpinApp 조회
            cmd = [
                "kubectl", "get", "spinapps",
                "-n", namespace,
                "-o", "json"
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30,
                env=env
            )
            
            if result.returncode != 0:
                return []
            
            # JSON 파싱
            data = json.loads(result.stdout)
            items = data.get("items", [])
            
            apps = []
            for item in items:
                metadata = item.get("metadata", {})
                spec = item.get("spec", {})
                status = item.get("status", {})
                
                app_name = metadata.get("name", "")
                
                # 레플리카 정보
                replicas = spec.get("replicas", 1)
                ready_replicas = status.get("readyReplicas", 0)
                
                # 상태 결정
                app_status = "Pending"
                if ready_replicas >= replicas and replicas > 0:
                    app_status = "Running"
                
                # 엔드포인트 조회
                endpoint = self._get_app_endpoint(app_name, namespace)
                
                apps.append(AppStatus(
                    name=app_name,
                    namespace=metadata.get("namespace", namespace),
                    oci_reference=spec.get("image", ""),
                    replicas=replicas,
                    ready_replicas=ready_replicas,
                    endpoint=endpoint,
                    status=app_status
                ))
            
            return apps
            
        except subprocess.TimeoutExpired:
            return []
        except FileNotFoundError:
            return []
        except json.JSONDecodeError:
            return []
        except Exception:
            return []


# 싱글톤 인스턴스
_deploy_service: Optional[DeployService] = None


def get_deploy_service() -> DeployService:
    """DeployService 싱글톤 인스턴스 반환"""
    global _deploy_service
    if _deploy_service is None:
        _deploy_service = DeployService()
    return _deploy_service
