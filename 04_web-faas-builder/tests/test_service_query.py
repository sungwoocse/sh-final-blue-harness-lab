"""Property-based tests for Service query for SpinApp.

**Feature: spin-k8s-deployment, Property 12: Service Query for SpinApp**
**Validates: Requirements 11.1, 11.2, 11.4**

This module tests that querying the Service for a deployed SpinApp returns
the correct service name (same as SpinApp name) and endpoint information
when the Service is available.
"""

from unittest.mock import patch, MagicMock
from hypothesis import given, strategies as st, settings, assume

from src.services.deploy import DeployService, ServiceQueryResult


# Strategy for valid Kubernetes names (DNS-1123 subdomain)
# Must be lowercase alphanumeric, may contain '-', max 63 chars
# Must start and end with alphanumeric
k8s_name = st.text(
    alphabet=st.sampled_from("abcdefghijklmnopqrstuvwxyz0123456789-"),
    min_size=1,
    max_size=63,
).filter(
    lambda s: s[0].isalnum() and s[-1].isalnum() and "--" not in s
)

# Strategy for valid ClusterIP addresses
cluster_ip = st.builds(
    lambda a, b, c, d: f"{a}.{b}.{c}.{d}",
    st.integers(min_value=10, max_value=10),
    st.integers(min_value=0, max_value=255),
    st.integers(min_value=0, max_value=255),
    st.integers(min_value=1, max_value=254),
)


class TestServiceQueryForSpinApp:
    """Property tests for Service query for SpinApp.
    
    **Feature: spin-k8s-deployment, Property 12: Service Query for SpinApp**
    **Validates: Requirements 11.1, 11.2, 11.4**
    """

    @given(app_name=k8s_name, namespace=k8s_name, ip=cluster_ip)
    @settings(max_examples=100)
    def test_service_found_returns_correct_endpoint(
        self, app_name: str, namespace: str, ip: str
    ):
        """
        **Feature: spin-k8s-deployment, Property 12: Service Query for SpinApp**
        **Validates: Requirements 11.1, 11.2, 11.4**
        
        For any deployed SpinApp where the Service is found with a valid ClusterIP,
        the returned endpoint should be in the format '{app_name}.{namespace}.svc.cluster.local'
        and the service_status should be 'found'.
        
        This validates:
        - Requirement 11.1: Query the automatically created Service for the SpinApp
        - Requirement 11.2: Return the Service name and access endpoint information
        - Requirement 11.4: Use the SpinApp name to locate the corresponding Service
        """
        service = DeployService()
        
        # Mock subprocess.run to simulate kubectl returning a valid ClusterIP
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = ip
        mock_result.stderr = ""
        
        with patch("subprocess.run", return_value=mock_result) as mock_run:
            result = service.get_service(app_name, namespace)
            
            # Verify kubectl was called with correct arguments (Requirement 11.4)
            mock_run.assert_called_once()
            call_args = mock_run.call_args[0][0]
            assert "kubectl" in call_args
            assert "get" in call_args
            assert "service" in call_args
            assert app_name in call_args  # SpinApp name used to locate Service
            assert namespace in call_args or f"-n" in call_args
            
            # Verify result (Requirements 11.1, 11.2)
            assert result.service_status == "found"
            expected_endpoint = f"{app_name}.{namespace}.svc.cluster.local"
            assert result.endpoint == expected_endpoint

    @given(app_name=k8s_name, namespace=k8s_name)
    @settings(max_examples=100)
    def test_service_not_found_returns_correct_status(
        self, app_name: str, namespace: str
    ):
        """
        **Feature: spin-k8s-deployment, Property 12: Service Query for SpinApp**
        **Validates: Requirements 11.1, 11.4**
        
        For any SpinApp where the Service is not found, the service_status
        should be 'not_found' and endpoint should be None.
        """
        service = DeployService()
        
        # Mock subprocess.run to simulate kubectl returning "not found" error
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stdout = ""
        mock_result.stderr = 'Error from server (NotFound): services "test" not found'
        
        with patch("subprocess.run", return_value=mock_result):
            result = service.get_service(app_name, namespace)
            
            assert result.service_status == "not_found"
            assert result.endpoint is None

    @given(app_name=k8s_name, namespace=k8s_name)
    @settings(max_examples=100)
    def test_service_pending_returns_correct_status(
        self, app_name: str, namespace: str
    ):
        """
        **Feature: spin-k8s-deployment, Property 12: Service Query for SpinApp**
        **Validates: Requirements 11.1, 11.4**
        
        For any SpinApp where the Service exists but has no ClusterIP yet,
        the service_status should be 'pending' and endpoint should be None.
        """
        service = DeployService()
        
        # Mock subprocess.run to simulate kubectl returning empty ClusterIP
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = ""  # Empty ClusterIP
        mock_result.stderr = ""
        
        with patch("subprocess.run", return_value=mock_result):
            result = service.get_service(app_name, namespace)
            
            assert result.service_status == "pending"
            assert result.endpoint is None

    @given(app_name=k8s_name, namespace=k8s_name)
    @settings(max_examples=100)
    def test_service_pending_when_cluster_ip_is_none(
        self, app_name: str, namespace: str
    ):
        """
        **Feature: spin-k8s-deployment, Property 12: Service Query for SpinApp**
        **Validates: Requirements 11.1, 11.4**
        
        For any SpinApp where the Service exists but ClusterIP is "None",
        the service_status should be 'pending' and endpoint should be None.
        """
        service = DeployService()
        
        # Mock subprocess.run to simulate kubectl returning "None" as ClusterIP
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "None"  # ClusterIP is None (headless service or pending)
        mock_result.stderr = ""
        
        with patch("subprocess.run", return_value=mock_result):
            result = service.get_service(app_name, namespace)
            
            assert result.service_status == "pending"
            assert result.endpoint is None

    @given(app_name=k8s_name, namespace=k8s_name, ip=cluster_ip)
    @settings(max_examples=100)
    def test_endpoint_format_uses_spinapp_name(
        self, app_name: str, namespace: str, ip: str
    ):
        """
        **Feature: spin-k8s-deployment, Property 12: Service Query for SpinApp**
        **Validates: Requirements 11.2, 11.4**
        
        For any deployed SpinApp, the endpoint should use the SpinApp name
        as the Service name (since SpinApp creates a Service with the same name).
        The endpoint format should be '{app_name}.{namespace}.svc.cluster.local'.
        """
        service = DeployService()
        
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = ip
        mock_result.stderr = ""
        
        with patch("subprocess.run", return_value=mock_result):
            result = service.get_service(app_name, namespace)
            
            # The endpoint should contain the app_name (which is the Service name)
            assert result.endpoint is not None
            assert app_name in result.endpoint
            assert namespace in result.endpoint
            assert result.endpoint.endswith(".svc.cluster.local")

    @given(app_name=k8s_name, namespace=k8s_name)
    @settings(max_examples=100)
    def test_kubectl_timeout_returns_pending(
        self, app_name: str, namespace: str
    ):
        """
        **Feature: spin-k8s-deployment, Property 12: Service Query for SpinApp**
        **Validates: Requirements 11.1**
        
        For any Service query that times out, the service_status should be
        'pending' to indicate the Service might still be creating.
        """
        import subprocess
        
        service = DeployService()
        
        with patch("subprocess.run", side_effect=subprocess.TimeoutExpired("kubectl", 30)):
            result = service.get_service(app_name, namespace)
            
            assert result.service_status == "pending"
            assert result.endpoint is None

    @given(app_name=k8s_name, namespace=k8s_name)
    @settings(max_examples=100)
    def test_kubectl_not_found_returns_not_found(
        self, app_name: str, namespace: str
    ):
        """
        **Feature: spin-k8s-deployment, Property 12: Service Query for SpinApp**
        **Validates: Requirements 11.1**
        
        For any Service query where kubectl is not available,
        the service_status should be 'not_found'.
        """
        service = DeployService()
        
        with patch("subprocess.run", side_effect=FileNotFoundError("kubectl not found")):
            result = service.get_service(app_name, namespace)
            
            assert result.service_status == "not_found"
            assert result.endpoint is None

    @given(app_name=k8s_name, namespace=k8s_name, ip=cluster_ip)
    @settings(max_examples=100)
    def test_service_query_result_type(
        self, app_name: str, namespace: str, ip: str
    ):
        """
        **Feature: spin-k8s-deployment, Property 12: Service Query for SpinApp**
        **Validates: Requirements 11.1, 11.2**
        
        For any Service query, the result should be a ServiceQueryResult
        with valid service_status and endpoint fields.
        """
        service = DeployService()
        
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = ip
        mock_result.stderr = ""
        
        with patch("subprocess.run", return_value=mock_result):
            result = service.get_service(app_name, namespace)
            
            # Verify result is correct type
            assert isinstance(result, ServiceQueryResult)
            
            # Verify service_status is one of valid values
            assert result.service_status in ("found", "pending", "not_found")
            
            # Verify endpoint is string when found, None otherwise
            if result.service_status == "found":
                assert isinstance(result.endpoint, str)
            else:
                assert result.endpoint is None
