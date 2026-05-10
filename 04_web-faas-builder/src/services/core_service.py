"""Core Service Client for build and push operations.

This module provides:
- Interface for build and push operations via Core Service
- Mock API implementations when Core Service endpoint is not configured
- Configuration from environment variables

**Feature: spin-k8s-deployment**
**Validates: Requirements 16.1, 16.2, 16.3, 16.4, 16.5**
"""

import os
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional
from enum import Enum

import httpx


class CoreServiceOperation(Enum):
    """Core Service operation types."""
    BUILD = "build"
    PUSH = "push"


@dataclass
class CoreServiceResult:
    """Result of a Core Service operation.
    
    Attributes:
        success: True if operation completed successfully
        operation: The operation type (build or push)
        wasm_path: S3 path to WASM artifact (for build operations)
        image_url: ECR image URL (for push operations)
        error: Error message if operation failed
    """
    success: bool
    operation: CoreServiceOperation
    wasm_path: Optional[str] = None
    image_url: Optional[str] = None
    error: Optional[str] = None


class CoreServiceClientInterface(ABC):
    """Abstract interface for Core Service client.
    
    This interface defines the contract for build and push operations
    that can be implemented by either the real Core Service client
    or a mock implementation.
    """
    
    @abstractmethod
    def build(
        self,
        workspace_id: str,
        task_id: str,
        s3_source_path: str,
        app_name: Optional[str] = None,
    ) -> CoreServiceResult:
        """Execute build operation via Core Service.
        
        Args:
            workspace_id: The workspace identifier
            task_id: The task identifier
            s3_source_path: S3 path to source code
            app_name: Optional application name
            
        Returns:
            CoreServiceResult with build status and WASM path
        """
        pass
    
    @abstractmethod
    def push(
        self,
        workspace_id: str,
        task_id: str,
        s3_source_path: str,
        registry_url: str,
        tag: Optional[str] = None,
    ) -> CoreServiceResult:
        """Execute push operation via Core Service.
        
        Args:
            workspace_id: The workspace identifier
            task_id: The task identifier
            s3_source_path: S3 path to source code
            registry_url: Container registry URL
            tag: Optional image tag
            
        Returns:
            CoreServiceResult with push status and image URL
        """
        pass
    
    @abstractmethod
    def is_configured(self) -> bool:
        """Check if the Core Service is configured.
        
        Returns:
            True if Core Service endpoint is configured, False otherwise
        """
        pass


class MockCoreServiceClient(CoreServiceClientInterface):
    """Mock implementation of Core Service client.
    
    This mock implementation is used when the Core Service endpoint
    is not configured. It simulates successful build and push operations.
    
    **Validates: Requirements 16.1**
    """
    
    def __init__(self, s3_bucket: Optional[str] = None):
        """Initialize Mock Core Service client.
        
        Args:
            s3_bucket: S3 bucket name for generating mock paths
        """
        self.s3_bucket = s3_bucket or os.environ.get(
            "S3_BUCKET_NAME", 
            "sfbank-blue-functions-code-bucket"
        )
    
    def build(
        self,
        workspace_id: str,
        task_id: str,
        s3_source_path: str,
        app_name: Optional[str] = None,
    ) -> CoreServiceResult:
        """Mock build operation - simulates successful build.
        
        Returns a mock WASM path in S3.
        """
        # Generate mock WASM artifact path
        wasm_path = f"s3://{self.s3_bucket}/build-artifacts/{task_id}/app.wasm"
        
        return CoreServiceResult(
            success=True,
            operation=CoreServiceOperation.BUILD,
            wasm_path=wasm_path,
        )
    
    def push(
        self,
        workspace_id: str,
        task_id: str,
        s3_source_path: str,
        registry_url: str,
        tag: Optional[str] = None,
    ) -> CoreServiceResult:
        """Mock push operation - simulates successful push.
        
        Returns a mock image URL.
        """
        # Generate mock image URL
        image_tag = tag or f"mock-{task_id[:12]}"
        image_url = f"{registry_url}:{image_tag}"
        
        return CoreServiceResult(
            success=True,
            operation=CoreServiceOperation.PUSH,
            image_url=image_url,
        )
    
    def is_configured(self) -> bool:
        """Mock client is always 'configured' as a fallback."""
        return True


class CoreServiceClient(CoreServiceClientInterface):
    """Real Core Service client implementation.
    
    This client calls the actual Core Service API for build and push operations.
    Configuration is read from environment variables:
    - CORE_SERVICE_ENDPOINT: Base URL of the Core Service API
    - CORE_SERVICE_TIMEOUT: Request timeout in seconds (default: 300)
    
    **Validates: Requirements 16.2, 16.3, 16.4, 16.5**
    """
    
    # Environment variable names
    ENV_ENDPOINT = "CORE_SERVICE_ENDPOINT"
    ENV_TIMEOUT = "CORE_SERVICE_TIMEOUT"
    
    # Default timeout (5 minutes for build/push operations)
    DEFAULT_TIMEOUT = 300
    
    # API endpoints
    BUILD_ENDPOINT = "/api/v1/build"
    PUSH_ENDPOINT = "/api/v1/push"
    
    def __init__(
        self,
        endpoint: Optional[str] = None,
        timeout: Optional[int] = None,
    ):
        """Initialize Core Service client.
        
        Args:
            endpoint: Core Service base URL. If not provided, reads from
                     CORE_SERVICE_ENDPOINT environment variable.
            timeout: Request timeout in seconds. If not provided, reads from
                    CORE_SERVICE_TIMEOUT environment variable or uses default.
        """
        self.endpoint = endpoint or os.environ.get(self.ENV_ENDPOINT)
        self.timeout = timeout or int(
            os.environ.get(self.ENV_TIMEOUT, self.DEFAULT_TIMEOUT)
        )
        self._client: Optional[httpx.Client] = None
    
    @property
    def client(self) -> httpx.Client:
        """Lazy initialization of httpx client."""
        if self._client is None:
            self._client = httpx.Client(timeout=self.timeout)
        return self._client
    
    def is_configured(self) -> bool:
        """Check if Core Service endpoint is configured.
        
        Returns:
            True if CORE_SERVICE_ENDPOINT is set, False otherwise
        """
        return self.endpoint is not None and len(self.endpoint) > 0
    
    def build(
        self,
        workspace_id: str,
        task_id: str,
        s3_source_path: str,
        app_name: Optional[str] = None,
    ) -> CoreServiceResult:
        """Execute build operation via Core Service.
        
        Calls Core Service with workspace_id, task_id, and S3 source path.
        
        **Validates: Requirements 16.2, 16.4, 16.5**
        
        Args:
            workspace_id: The workspace identifier
            task_id: The task identifier
            s3_source_path: S3 path to source code
            app_name: Optional application name
            
        Returns:
            CoreServiceResult with build status and WASM path
        """
        if not self.is_configured():
            return CoreServiceResult(
                success=False,
                operation=CoreServiceOperation.BUILD,
                error="Core Service endpoint not configured",
            )
        
        try:
            url = f"{self.endpoint}{self.BUILD_ENDPOINT}"
            payload = {
                "workspace_id": workspace_id,
                "task_id": task_id,
                "s3_source_path": s3_source_path,
            }
            if app_name:
                payload["app_name"] = app_name
            
            response = self.client.post(url, json=payload)
            
            if response.status_code == 200 or response.status_code == 202:
                data = response.json()
                return CoreServiceResult(
                    success=True,
                    operation=CoreServiceOperation.BUILD,
                    wasm_path=data.get("wasm_path"),
                )
            else:
                error_detail = self._extract_error(response)
                return CoreServiceResult(
                    success=False,
                    operation=CoreServiceOperation.BUILD,
                    error=f"Core Service build failed: {error_detail}",
                )
                
        except httpx.TimeoutException:
            return CoreServiceResult(
                success=False,
                operation=CoreServiceOperation.BUILD,
                error=f"Core Service build timed out after {self.timeout} seconds",
            )
        except httpx.RequestError as e:
            return CoreServiceResult(
                success=False,
                operation=CoreServiceOperation.BUILD,
                error=f"Core Service request error: {str(e)}",
            )
        except Exception as e:
            return CoreServiceResult(
                success=False,
                operation=CoreServiceOperation.BUILD,
                error=f"Unexpected error calling Core Service: {str(e)}",
            )
    
    def push(
        self,
        workspace_id: str,
        task_id: str,
        s3_source_path: str,
        registry_url: str,
        tag: Optional[str] = None,
    ) -> CoreServiceResult:
        """Execute push operation via Core Service.
        
        Calls Core Service with workspace_id, task_id, and S3 source path.
        
        **Validates: Requirements 16.3, 16.4, 16.5**
        
        Args:
            workspace_id: The workspace identifier
            task_id: The task identifier
            s3_source_path: S3 path to source code
            registry_url: Container registry URL
            tag: Optional image tag
            
        Returns:
            CoreServiceResult with push status and image URL
        """
        if not self.is_configured():
            return CoreServiceResult(
                success=False,
                operation=CoreServiceOperation.PUSH,
                error="Core Service endpoint not configured",
            )
        
        try:
            url = f"{self.endpoint}{self.PUSH_ENDPOINT}"
            payload = {
                "workspace_id": workspace_id,
                "task_id": task_id,
                "s3_source_path": s3_source_path,
                "registry_url": registry_url,
            }
            if tag:
                payload["tag"] = tag
            
            response = self.client.post(url, json=payload)
            
            if response.status_code == 200 or response.status_code == 202:
                data = response.json()
                return CoreServiceResult(
                    success=True,
                    operation=CoreServiceOperation.PUSH,
                    image_url=data.get("image_url"),
                )
            else:
                error_detail = self._extract_error(response)
                return CoreServiceResult(
                    success=False,
                    operation=CoreServiceOperation.PUSH,
                    error=f"Core Service push failed: {error_detail}",
                )
                
        except httpx.TimeoutException:
            return CoreServiceResult(
                success=False,
                operation=CoreServiceOperation.PUSH,
                error=f"Core Service push timed out after {self.timeout} seconds",
            )
        except httpx.RequestError as e:
            return CoreServiceResult(
                success=False,
                operation=CoreServiceOperation.PUSH,
                error=f"Core Service request error: {str(e)}",
            )
        except Exception as e:
            return CoreServiceResult(
                success=False,
                operation=CoreServiceOperation.PUSH,
                error=f"Unexpected error calling Core Service: {str(e)}",
            )
    
    def _extract_error(self, response: httpx.Response) -> str:
        """Extract error message from response.
        
        Args:
            response: HTTP response object
            
        Returns:
            Error message string
        """
        try:
            data = response.json()
            if "detail" in data:
                return str(data["detail"])
            if "error" in data:
                return str(data["error"])
            if "message" in data:
                return str(data["message"])
            return f"HTTP {response.status_code}: {response.text}"
        except Exception:
            return f"HTTP {response.status_code}: {response.text}"
    
    def close(self) -> None:
        """Close the HTTP client."""
        if self._client is not None:
            self._client.close()
            self._client = None


def get_core_service_client() -> CoreServiceClientInterface:
    """Factory function to get the appropriate Core Service client.
    
    Returns CoreServiceClient if CORE_SERVICE_ENDPOINT is configured,
    otherwise returns MockCoreServiceClient.
    
    **Validates: Requirements 16.1**
    
    Returns:
        CoreServiceClientInterface implementation
    """
    client = CoreServiceClient()
    if client.is_configured():
        return client
    return MockCoreServiceClient()
