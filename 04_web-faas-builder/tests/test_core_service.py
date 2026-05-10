"""Tests for Core Service client.

**Feature: spin-k8s-deployment**
**Validates: Requirements 16.1, 16.2, 16.3, 16.4, 16.5**
"""

import os
import pytest
from unittest.mock import patch, MagicMock

from src.services.core_service import (
    CoreServiceClient,
    CoreServiceClientInterface,
    CoreServiceOperation,
    CoreServiceResult,
    MockCoreServiceClient,
    get_core_service_client,
)


class TestCoreServiceClientInterface:
    """Test Core Service client interface and factory function."""
    
    def test_mock_client_returned_when_endpoint_not_configured(self):
        """When CORE_SERVICE_ENDPOINT is not set, MockCoreServiceClient is returned.
        
        **Feature: spin-k8s-deployment, Property: Core Service fallback**
        **Validates: Requirements 16.1**
        """
        # Ensure environment variable is not set
        with patch.dict(os.environ, {}, clear=True):
            # Remove the env var if it exists
            os.environ.pop("CORE_SERVICE_ENDPOINT", None)
            client = get_core_service_client()
            assert isinstance(client, MockCoreServiceClient)
    
    def test_real_client_returned_when_endpoint_configured(self):
        """When CORE_SERVICE_ENDPOINT is set, CoreServiceClient is returned.
        
        **Feature: spin-k8s-deployment, Property: Core Service configuration**
        **Validates: Requirements 16.2, 16.3**
        """
        with patch.dict(os.environ, {"CORE_SERVICE_ENDPOINT": "http://core-service:8080"}):
            client = get_core_service_client()
            assert isinstance(client, CoreServiceClient)
    
    def test_client_interface_has_required_methods(self):
        """CoreServiceClientInterface defines build, push, and is_configured methods."""
        # Check that the interface has the required abstract methods
        assert hasattr(CoreServiceClientInterface, "build")
        assert hasattr(CoreServiceClientInterface, "push")
        assert hasattr(CoreServiceClientInterface, "is_configured")


class TestMockCoreServiceClient:
    """Test Mock Core Service client implementation.
    
    **Validates: Requirements 16.1**
    """
    
    def test_mock_build_returns_success(self):
        """Mock build operation returns successful result with WASM path.
        
        **Feature: spin-k8s-deployment, Property: Mock API build**
        **Validates: Requirements 16.1**
        """
        client = MockCoreServiceClient(s3_bucket="test-bucket")
        result = client.build(
            workspace_id="ws-123",
            task_id="task-456",
            s3_source_path="s3://test-bucket/build-sources/ws-123/task-456/",
        )
        
        assert result.success is True
        assert result.operation == CoreServiceOperation.BUILD
        assert result.wasm_path is not None
        assert "task-456" in result.wasm_path
        assert result.error is None
    
    def test_mock_push_returns_success(self):
        """Mock push operation returns successful result with image URL.
        
        **Feature: spin-k8s-deployment, Property: Mock API push**
        **Validates: Requirements 16.1**
        """
        client = MockCoreServiceClient(s3_bucket="test-bucket")
        result = client.push(
            workspace_id="ws-123",
            task_id="task-456",
            s3_source_path="s3://test-bucket/build-sources/ws-123/task-456/",
            registry_url="123456789.dkr.ecr.ap-northeast-2.amazonaws.com/spin-apps",
        )
        
        assert result.success is True
        assert result.operation == CoreServiceOperation.PUSH
        assert result.image_url is not None
        assert "123456789.dkr.ecr.ap-northeast-2.amazonaws.com/spin-apps" in result.image_url
        assert result.error is None
    
    def test_mock_push_with_custom_tag(self):
        """Mock push operation preserves custom tag in image URL.
        
        **Feature: spin-k8s-deployment, Property: Mock API custom tag**
        **Validates: Requirements 16.1**
        """
        client = MockCoreServiceClient()
        result = client.push(
            workspace_id="ws-123",
            task_id="task-456",
            s3_source_path="s3://bucket/path/",
            registry_url="registry.example.com/repo",
            tag="v1.0.0",
        )
        
        assert result.success is True
        assert result.image_url == "registry.example.com/repo:v1.0.0"
    
    def test_mock_is_configured_returns_true(self):
        """Mock client is_configured always returns True."""
        client = MockCoreServiceClient()
        assert client.is_configured() is True


class TestCoreServiceClient:
    """Test real Core Service client implementation.
    
    **Validates: Requirements 16.2, 16.3, 16.4, 16.5**
    """
    
    def test_is_configured_returns_false_when_no_endpoint(self):
        """is_configured returns False when endpoint is not set."""
        client = CoreServiceClient(endpoint=None)
        assert client.is_configured() is False
    
    def test_is_configured_returns_true_when_endpoint_set(self):
        """is_configured returns True when endpoint is set."""
        client = CoreServiceClient(endpoint="http://core-service:8080")
        assert client.is_configured() is True
    
    def test_build_returns_error_when_not_configured(self):
        """Build returns error when Core Service is not configured.
        
        **Feature: spin-k8s-deployment, Property: Core Service not configured**
        **Validates: Requirements 16.5**
        """
        client = CoreServiceClient(endpoint=None)
        result = client.build(
            workspace_id="ws-123",
            task_id="task-456",
            s3_source_path="s3://bucket/path/",
        )
        
        assert result.success is False
        assert result.operation == CoreServiceOperation.BUILD
        assert "not configured" in result.error.lower()
    
    def test_push_returns_error_when_not_configured(self):
        """Push returns error when Core Service is not configured.
        
        **Feature: spin-k8s-deployment, Property: Core Service not configured**
        **Validates: Requirements 16.5**
        """
        client = CoreServiceClient(endpoint=None)
        result = client.push(
            workspace_id="ws-123",
            task_id="task-456",
            s3_source_path="s3://bucket/path/",
            registry_url="registry.example.com/repo",
        )
        
        assert result.success is False
        assert result.operation == CoreServiceOperation.PUSH
        assert "not configured" in result.error.lower()
    
    @patch("httpx.Client.post")
    def test_build_calls_core_service_with_correct_params(self, mock_post):
        """Build calls Core Service with workspace_id, task_id, and s3_source_path.
        
        **Feature: spin-k8s-deployment, Property: Core Service build params**
        **Validates: Requirements 16.2, 16.4**
        """
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"wasm_path": "s3://bucket/artifacts/app.wasm"}
        mock_post.return_value = mock_response
        
        client = CoreServiceClient(endpoint="http://core-service:8080")
        result = client.build(
            workspace_id="ws-123",
            task_id="task-456",
            s3_source_path="s3://bucket/sources/ws-123/task-456/",
            app_name="my-app",
        )
        
        # Verify the call was made with correct parameters
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        assert call_args[0][0] == "http://core-service:8080/api/v1/build"
        assert call_args[1]["json"]["workspace_id"] == "ws-123"
        assert call_args[1]["json"]["task_id"] == "task-456"
        assert call_args[1]["json"]["s3_source_path"] == "s3://bucket/sources/ws-123/task-456/"
        assert call_args[1]["json"]["app_name"] == "my-app"
        
        assert result.success is True
        assert result.wasm_path == "s3://bucket/artifacts/app.wasm"
    
    @patch("httpx.Client.post")
    def test_push_calls_core_service_with_correct_params(self, mock_post):
        """Push calls Core Service with workspace_id, task_id, s3_source_path, and registry_url.
        
        **Feature: spin-k8s-deployment, Property: Core Service push params**
        **Validates: Requirements 16.3, 16.4**
        """
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"image_url": "registry.example.com/repo:v1.0.0"}
        mock_post.return_value = mock_response
        
        client = CoreServiceClient(endpoint="http://core-service:8080")
        result = client.push(
            workspace_id="ws-123",
            task_id="task-456",
            s3_source_path="s3://bucket/sources/ws-123/task-456/",
            registry_url="registry.example.com/repo",
            tag="v1.0.0",
        )
        
        # Verify the call was made with correct parameters
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        assert call_args[0][0] == "http://core-service:8080/api/v1/push"
        assert call_args[1]["json"]["workspace_id"] == "ws-123"
        assert call_args[1]["json"]["task_id"] == "task-456"
        assert call_args[1]["json"]["s3_source_path"] == "s3://bucket/sources/ws-123/task-456/"
        assert call_args[1]["json"]["registry_url"] == "registry.example.com/repo"
        assert call_args[1]["json"]["tag"] == "v1.0.0"
        
        assert result.success is True
        assert result.image_url == "registry.example.com/repo:v1.0.0"
    
    @patch("httpx.Client.post")
    def test_build_handles_error_response(self, mock_post):
        """Build handles error response from Core Service.
        
        **Feature: spin-k8s-deployment, Property: Core Service error handling**
        **Validates: Requirements 16.5**
        """
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.json.return_value = {"detail": "Internal server error"}
        mock_response.text = "Internal server error"
        mock_post.return_value = mock_response
        
        client = CoreServiceClient(endpoint="http://core-service:8080")
        result = client.build(
            workspace_id="ws-123",
            task_id="task-456",
            s3_source_path="s3://bucket/path/",
        )
        
        assert result.success is False
        assert result.operation == CoreServiceOperation.BUILD
        assert "Internal server error" in result.error
    
    @patch("httpx.Client.post")
    def test_push_handles_error_response(self, mock_post):
        """Push handles error response from Core Service.
        
        **Feature: spin-k8s-deployment, Property: Core Service error handling**
        **Validates: Requirements 16.5**
        """
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.json.return_value = {"error": "Invalid registry URL"}
        mock_response.text = "Invalid registry URL"
        mock_post.return_value = mock_response
        
        client = CoreServiceClient(endpoint="http://core-service:8080")
        result = client.push(
            workspace_id="ws-123",
            task_id="task-456",
            s3_source_path="s3://bucket/path/",
            registry_url="invalid-url",
        )
        
        assert result.success is False
        assert result.operation == CoreServiceOperation.PUSH
        assert "Invalid registry URL" in result.error


class TestCoreServiceResult:
    """Test CoreServiceResult dataclass."""
    
    def test_result_for_successful_build(self):
        """CoreServiceResult correctly represents successful build."""
        result = CoreServiceResult(
            success=True,
            operation=CoreServiceOperation.BUILD,
            wasm_path="s3://bucket/artifacts/app.wasm",
        )
        
        assert result.success is True
        assert result.operation == CoreServiceOperation.BUILD
        assert result.wasm_path == "s3://bucket/artifacts/app.wasm"
        assert result.image_url is None
        assert result.error is None
    
    def test_result_for_successful_push(self):
        """CoreServiceResult correctly represents successful push."""
        result = CoreServiceResult(
            success=True,
            operation=CoreServiceOperation.PUSH,
            image_url="registry.example.com/repo:v1.0.0",
        )
        
        assert result.success is True
        assert result.operation == CoreServiceOperation.PUSH
        assert result.wasm_path is None
        assert result.image_url == "registry.example.com/repo:v1.0.0"
        assert result.error is None
    
    def test_result_for_failed_operation(self):
        """CoreServiceResult correctly represents failed operation."""
        result = CoreServiceResult(
            success=False,
            operation=CoreServiceOperation.BUILD,
            error="Build failed: compilation error",
        )
        
        assert result.success is False
        assert result.operation == CoreServiceOperation.BUILD
        assert result.wasm_path is None
        assert result.image_url is None
        assert result.error == "Build failed: compilation error"
