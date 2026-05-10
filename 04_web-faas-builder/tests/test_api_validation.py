"""Property-based tests for API request validation.

**Feature: spin-k8s-deployment, Property 16: API Request Validation**
**Validates: Requirements 1.3**

For any invalid API request (missing required fields, wrong types), the system
should return HTTP 400 with validation details describing the specific validation failures.
"""

import pytest
from hypothesis import given, settings, strategies as st
from fastapi.testclient import TestClient

from main import app
from src.models.api_models import PushRequest, ScaffoldRequest, DeployRequest


client = TestClient(app)


# Strategy for generating invalid push requests (missing required fields)
@st.composite
def invalid_push_request_missing_fields(draw):
    """Generate push request data with at least one required field missing."""
    # Required fields: registry_url, username, password, app_dir
    include_registry_url = draw(st.booleans())
    include_username = draw(st.booleans())
    include_password = draw(st.booleans())
    include_app_dir = draw(st.booleans())
    
    # Ensure at least one required field is missing
    if include_registry_url and include_username and include_password and include_app_dir:
        # Randomly remove one field
        field_to_remove = draw(st.sampled_from(["registry_url", "username", "password", "app_dir"]))
        if field_to_remove == "registry_url":
            include_registry_url = False
        elif field_to_remove == "username":
            include_username = False
        elif field_to_remove == "password":
            include_password = False
        else:
            include_app_dir = False
    
    data = {}
    if include_registry_url:
        data["registry_url"] = draw(st.text(min_size=1, max_size=100))
    if include_username:
        data["username"] = draw(st.text(min_size=1, max_size=50))
    if include_password:
        data["password"] = draw(st.text(min_size=1, max_size=50))
    if include_app_dir:
        data["app_dir"] = draw(st.text(min_size=1, max_size=100))
    
    return data


# Strategy for generating invalid scaffold requests (missing required fields)
@st.composite
def invalid_scaffold_request_missing_fields(draw):
    """Generate scaffold request data with required field missing."""
    # Required field: image_ref
    # Return empty dict or dict without image_ref
    include_optional = draw(st.booleans())
    
    data = {}
    if include_optional:
        data["component"] = draw(st.text(min_size=1, max_size=50))
        data["replicas"] = draw(st.integers(min_value=1, max_value=10))
    
    # Never include image_ref to make it invalid
    return data


# Strategy for generating invalid deploy requests (missing required fields)
@st.composite
def invalid_deploy_request_missing_fields(draw):
    """Generate deploy request data with at least one required field missing."""
    # Required fields: namespace, image_ref
    include_namespace = draw(st.booleans())
    include_image_ref = draw(st.booleans())
    
    # Ensure at least one required field is missing
    if include_namespace and include_image_ref:
        field_to_remove = draw(st.sampled_from(["namespace", "image_ref"]))
        if field_to_remove == "namespace":
            include_namespace = False
        else:
            include_image_ref = False
    
    data = {}
    if include_namespace:
        data["namespace"] = draw(st.text(min_size=1, max_size=63))
    if include_image_ref:
        data["image_ref"] = draw(st.text(min_size=1, max_size=200))
    
    # Add some optional fields
    if draw(st.booleans()):
        data["app_name"] = draw(st.text(min_size=1, max_size=63))
    
    return data


# Strategy for generating requests with wrong types
@st.composite
def scaffold_request_wrong_types(draw):
    """Generate scaffold request with wrong field types."""
    # replicas should be int, but we'll send wrong type
    wrong_type = draw(st.sampled_from(["string", "list", "dict", "float"]))
    
    data = {
        "image_ref": draw(st.text(min_size=1, max_size=100)),
    }
    
    if wrong_type == "string":
        data["replicas"] = "not_a_number"
    elif wrong_type == "list":
        data["replicas"] = [1, 2, 3]
    elif wrong_type == "dict":
        data["replicas"] = {"value": 1}
    elif wrong_type == "float":
        # Pydantic may coerce float to int, so use a string that looks like float
        data["replicas"] = "1.5"
    
    return data


@st.composite
def deploy_request_wrong_types(draw):
    """Generate deploy request with wrong field types."""
    # replicas should be int, enable_autoscaling should be bool
    wrong_type = draw(st.sampled_from(["string_replicas", "list_replicas", "dict_replicas", "string_autoscaling"]))
    
    data = {
        "namespace": draw(st.text(min_size=1, max_size=63)),
        "image_ref": draw(st.text(min_size=1, max_size=200)),
    }
    
    if wrong_type == "string_replicas":
        data["replicas"] = "not_a_number"
    elif wrong_type == "list_replicas":
        data["replicas"] = [1, 2, 3]
    elif wrong_type == "dict_replicas":
        data["replicas"] = {"value": 1}
    elif wrong_type == "string_autoscaling":
        data["enable_autoscaling"] = "not_a_bool"
    
    return data


class TestAPIRequestValidation:
    """Property-based tests for API request validation.
    
    **Feature: spin-k8s-deployment, Property 16: API Request Validation**
    """

    @given(data=invalid_push_request_missing_fields())
    @settings(max_examples=100)
    def test_push_missing_required_fields_returns_400(self, data: dict):
        """
        **Feature: spin-k8s-deployment, Property 16: API Request Validation**
        **Validates: Requirements 1.3**
        
        For any push request with missing required fields, the system should
        return HTTP 400 with validation details.
        """
        response = client.post("/api/v1/push", json=data)
        
        assert response.status_code == 422, f"Expected 422 for invalid request, got {response.status_code}"
        response_json = response.json()
        assert "detail" in response_json, "Response should contain 'detail' field"
        assert isinstance(response_json["detail"], list), "Validation errors should be a list"
        assert len(response_json["detail"]) > 0, "Should have at least one validation error"
        
        # Each error should have location and message info
        for error in response_json["detail"]:
            assert "loc" in error, "Error should have 'loc' field"
            assert "msg" in error, "Error should have 'msg' field"

    @given(data=invalid_scaffold_request_missing_fields())
    @settings(max_examples=100)
    def test_scaffold_missing_required_fields_returns_400(self, data: dict):
        """
        **Feature: spin-k8s-deployment, Property 16: API Request Validation**
        **Validates: Requirements 1.3**
        
        For any scaffold request with missing required fields, the system should
        return HTTP 400 with validation details.
        """
        response = client.post("/api/v1/scaffold", json=data)
        
        assert response.status_code == 422, f"Expected 422 for invalid request, got {response.status_code}"
        response_json = response.json()
        assert "detail" in response_json, "Response should contain 'detail' field"
        assert isinstance(response_json["detail"], list), "Validation errors should be a list"
        assert len(response_json["detail"]) > 0, "Should have at least one validation error"

    @given(data=invalid_deploy_request_missing_fields())
    @settings(max_examples=100)
    def test_deploy_missing_required_fields_returns_400(self, data: dict):
        """
        **Feature: spin-k8s-deployment, Property 16: API Request Validation**
        **Validates: Requirements 1.3**
        
        For any deploy request with missing required fields, the system should
        return HTTP 400 with validation details.
        """
        response = client.post("/api/v1/deploy", json=data)
        
        assert response.status_code == 422, f"Expected 422 for invalid request, got {response.status_code}"
        response_json = response.json()
        assert "detail" in response_json, "Response should contain 'detail' field"
        assert isinstance(response_json["detail"], list), "Validation errors should be a list"
        assert len(response_json["detail"]) > 0, "Should have at least one validation error"

    @given(data=scaffold_request_wrong_types())
    @settings(max_examples=100)
    def test_scaffold_wrong_types_returns_400(self, data: dict):
        """
        **Feature: spin-k8s-deployment, Property 16: API Request Validation**
        **Validates: Requirements 1.3**
        
        For any scaffold request with wrong field types, the system should
        return HTTP 400 with validation details.
        """
        response = client.post("/api/v1/scaffold", json=data)
        
        assert response.status_code == 422, f"Expected 422 for invalid request, got {response.status_code}"
        response_json = response.json()
        assert "detail" in response_json, "Response should contain 'detail' field"

    @given(data=deploy_request_wrong_types())
    @settings(max_examples=100)
    def test_deploy_wrong_types_returns_400(self, data: dict):
        """
        **Feature: spin-k8s-deployment, Property 16: API Request Validation**
        **Validates: Requirements 1.3**
        
        For any deploy request with wrong field types, the system should
        return HTTP 400 with validation details.
        """
        response = client.post("/api/v1/deploy", json=data)
        
        assert response.status_code == 422, f"Expected 422 for invalid request, got {response.status_code}"
        response_json = response.json()
        assert "detail" in response_json, "Response should contain 'detail' field"

    def test_empty_push_request_returns_400(self):
        """
        **Feature: spin-k8s-deployment, Property 16: API Request Validation**
        **Validates: Requirements 1.3**
        
        An empty push request should return HTTP 400 with validation details.
        """
        response = client.post("/api/v1/push", json={})
        
        assert response.status_code == 422
        response_json = response.json()
        assert "detail" in response_json
        assert len(response_json["detail"]) >= 4  # 4 required fields

    def test_empty_deploy_request_returns_400(self):
        """
        **Feature: spin-k8s-deployment, Property 16: API Request Validation**
        **Validates: Requirements 1.3**
        
        An empty deploy request should return HTTP 400 with validation details.
        """
        response = client.post("/api/v1/deploy", json={})
        
        assert response.status_code == 422
        response_json = response.json()
        assert "detail" in response_json
        assert len(response_json["detail"]) >= 2  # 2 required fields (namespace, image_ref)
