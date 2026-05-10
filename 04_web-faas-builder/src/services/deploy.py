"""DeployService for Kubernetes SpinApp deployment and Service query.

This module provides the DeployService class for deploying SpinApp manifests
to Kubernetes and querying automatically created Services.

Requirements: 10.3, 10.4, 10.5, 10.6, 10.7, 11.1, 11.2, 11.4
"""

import subprocess
from dataclasses import dataclass
from typing import Literal

from faker import Faker


ServiceStatus = Literal["found", "pending", "not_found"]


@dataclass
class ServiceQueryResult:
    """Result of querying a Service for a SpinApp.
    
    Attributes:
        service_status: Status of the Service (found, pending, not_found)
        endpoint: Service endpoint if found, None otherwise
    """
    service_status: ServiceStatus
    endpoint: str | None = None


@dataclass
class DeployResult:
    """Result of deploying a SpinApp to Kubernetes.
    
    Attributes:
        success: Whether the deployment was successful
        app_name: Name of the deployed SpinApp
        namespace: Kubernetes namespace where the SpinApp is deployed
        service_name: Name of the automatically created Service (same as app_name)
        service_status: Status of the Service (found, pending, not_found)
        endpoint: Service endpoint if found, None otherwise
        enable_autoscaling: Whether autoscaling is enabled
        use_spot: Whether Spot instance configuration is used
        error: Error message if deployment failed
        
    Requirements: 11.2, 11.4
    """
    success: bool
    app_name: str | None
    namespace: str | None
    service_name: str | None
    service_status: ServiceStatus
    endpoint: str | None
    enable_autoscaling: bool
    use_spot: bool
    error: str | None


class DeployService:
    """Service for deploying SpinApp to Kubernetes and querying Services.
    
    Provides methods to deploy SpinApp manifests and query the automatically
    created Services for deployed SpinApps.
    
    Requirements: 10.3, 10.4, 10.5, 10.6, 10.7, 11.1, 11.2
    """
    
    def __init__(self):
        """Initialize DeployService with Faker instance for name generation."""
        self._faker = Faker()
    
    def generate_app_name(self) -> str:
        """Generate a unique application name using Faker.
        
        Generates names in the format 'spin-{word}-{word}-{number}' to ensure
        low collision probability. The words are random words from Faker,
        and the number is a random 4-digit integer. All characters are
        lowercase to comply with Kubernetes naming conventions.
        
        Returns:
            A unique application name string (lowercase, alphanumeric with hyphens).
            
        Requirements: 10.7
        """
        # Use two words + random number for uniqueness
        word1 = self._faker.word().lower()
        word2 = self._faker.word().lower()
        number = self._faker.random_int(min=1000, max=9999)
        return f"spin-{word1}-{word2}-{number}"
    
    def check_namespace(self, namespace: str) -> bool:
        """Check if a Kubernetes namespace exists.
        
        Args:
            namespace: The namespace name to check.
            
        Returns:
            True if the namespace exists, False otherwise.
            
        Requirements: 10.3
        """
        try:
            result = subprocess.run(
                ["kubectl", "get", "namespace", namespace],
                capture_output=True,
                text=True,
                timeout=30
            )
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError, Exception):
            return False
    
    def apply_manifest(self, manifest_path: str) -> tuple[bool, str | None]:
        """Apply a SpinApp manifest to the Kubernetes cluster.

        Args:
            manifest_path: Path to the YAML manifest file.

        Returns:
            A tuple of (success, error_message).

        Requirements: 10.4, 10.5
        """
        try:
            result = subprocess.run(
                ["kubectl", "apply", "-f", manifest_path],
                capture_output=True,
                text=True,
                timeout=60
            )
            if result.returncode == 0:
                return True, None
            return False, result.stderr or "Failed to apply manifest"
        except subprocess.TimeoutExpired:
            return False, "kubectl apply timed out"
        except FileNotFoundError:
            return False, "kubectl not found"
        except Exception as e:
            return False, str(e)

    def create_hpa(
        self,
        app_name: str,
        namespace: str,
        min_replicas: int = 1,
        max_replicas: int = 10,
        cpu_target: int = 50,
    ) -> tuple[bool, str | None]:
        """Create HorizontalPodAutoscaler for a deployment.

        Args:
            app_name: Name of the deployment to scale.
            namespace: Kubernetes namespace.
            min_replicas: Minimum number of replicas.
            max_replicas: Maximum number of replicas.
            cpu_target: Target CPU utilization percentage.

        Returns:
            A tuple of (success, error_message).
        """
        hpa_manifest = f"""apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: {app_name}-hpa
  namespace: {namespace}
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: {app_name}
  minReplicas: {min_replicas}
  maxReplicas: {max_replicas}
  metrics:
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: {cpu_target}
"""
        try:
            result = subprocess.run(
                ["kubectl", "apply", "-f", "-"],
                input=hpa_manifest,
                capture_output=True,
                text=True,
                timeout=60
            )
            if result.returncode == 0:
                return True, None
            return False, result.stderr or "Failed to create HPA"
        except subprocess.TimeoutExpired:
            return False, "kubectl apply timed out"
        except FileNotFoundError:
            return False, "kubectl not found"
        except Exception as e:
            return False, str(e)
    
    def deploy(
        self,
        manifest_path: str,
        namespace: str,
        app_name: str | None = None,
        enable_autoscaling: bool = True,
        use_spot: bool = True,
    ) -> DeployResult:
        """Deploy a SpinApp to the Kubernetes cluster.
        
        Args:
            manifest_path: Path to the SpinApp YAML manifest file.
            namespace: Target Kubernetes namespace.
            app_name: Optional custom application name. If not provided,
                     a unique name will be generated using Faker.
            enable_autoscaling: Whether autoscaling is enabled.
            use_spot: Whether Spot instance configuration is used.
            
        Returns:
            DeployResult with deployment status and details.
            
        Requirements: 10.3, 10.4, 10.5, 10.6, 10.7
        """
        # Check if namespace exists (Requirement 10.3)
        if not self.check_namespace(namespace):
            return DeployResult(
                success=False,
                app_name=app_name,
                namespace=namespace,
                service_name=None,
                service_status="not_found",
                endpoint=None,
                enable_autoscaling=enable_autoscaling,
                use_spot=use_spot,
                error=f"Namespace '{namespace}' not found"
            )
        
        # Use custom name or generate one (Requirements 10.6, 10.7)
        final_app_name = app_name if app_name else self.generate_app_name()
        
        # Apply the manifest (Requirements 10.4, 10.5)
        success, error = self.apply_manifest(manifest_path)

        if not success:
            return DeployResult(
                success=False,
                app_name=final_app_name,
                namespace=namespace,
                service_name=None,
                service_status="not_found",
                endpoint=None,
                enable_autoscaling=enable_autoscaling,
                use_spot=use_spot,
                error=error
            )

        # Create HPA if autoscaling is enabled
        if enable_autoscaling:
            hpa_success, hpa_error = self.create_hpa(
                app_name=final_app_name,
                namespace=namespace,
                min_replicas=1,
                max_replicas=10,
                cpu_target=50,
            )
            # Log HPA creation result but don't fail the deployment
            if not hpa_success:
                # HPA creation failed, but SpinApp deployment succeeded
                pass  # Could log this error if needed

        # Query the automatically created Service
        service_result = self.get_service(final_app_name, namespace)

        return DeployResult(
            success=True,
            app_name=final_app_name,
            namespace=namespace,
            service_name=final_app_name,  # SpinApp creates Service with same name
            service_status=service_result.service_status,
            endpoint=service_result.endpoint,
            enable_autoscaling=enable_autoscaling,
            use_spot=use_spot,
            error=None
        )
    
    def get_service(self, app_name: str, namespace: str) -> ServiceQueryResult:
        """Query the automatically created Service for a SpinApp.
        
        When a SpinApp is deployed, Kubernetes automatically creates a Service
        with the same name as the SpinApp. This method queries that Service
        and returns its status and endpoint information.
        
        Args:
            app_name: Name of the SpinApp (also the Service name)
            namespace: Kubernetes namespace where the SpinApp is deployed
            
        Returns:
            ServiceQueryResult with service_status and endpoint:
            - service_status: 'found' if Service exists and has ClusterIP,
                            'pending' if Service exists but no ClusterIP yet,
                            'not_found' if Service doesn't exist
            - endpoint: Service endpoint in format '{app_name}.{namespace}.svc.cluster.local'
                       if found, None otherwise
                       
        Requirements: 11.1, 11.2
        """
        try:
            # Query the Service using kubectl
            result = subprocess.run(
                [
                    "kubectl", "get", "service", app_name,
                    "-n", namespace,
                    "-o", "jsonpath={.spec.clusterIP}"
                ],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0 and result.stdout.strip():
                # Service found with ClusterIP
                cluster_ip = result.stdout.strip()
                if cluster_ip and cluster_ip != "None":
                    endpoint = f"{app_name}.{namespace}.svc.cluster.local"
                    return ServiceQueryResult(
                        service_status="found",
                        endpoint=endpoint
                    )
                else:
                    # Service exists but no ClusterIP assigned yet
                    return ServiceQueryResult(
                        service_status="pending",
                        endpoint=None
                    )
            elif result.returncode != 0:
                # Check if it's a "not found" error
                if "NotFound" in result.stderr or "not found" in result.stderr.lower():
                    return ServiceQueryResult(
                        service_status="not_found",
                        endpoint=None
                    )
                # Service might be pending creation
                return ServiceQueryResult(
                    service_status="pending",
                    endpoint=None
                )
            else:
                # Empty response - service pending
                return ServiceQueryResult(
                    service_status="pending",
                    endpoint=None
                )
                
        except subprocess.TimeoutExpired:
            # Timeout - treat as pending
            return ServiceQueryResult(
                service_status="pending",
                endpoint=None
            )
        except FileNotFoundError:
            # kubectl not found - treat as not_found
            return ServiceQueryResult(
                service_status="not_found",
                endpoint=None
            )
        except Exception:
            # Any other error - treat as not_found
            return ServiceQueryResult(
                service_status="not_found",
                endpoint=None
            )
