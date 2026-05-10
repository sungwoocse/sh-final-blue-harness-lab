"""Property-based tests for SpinApp autoscaling configuration.

This module tests the autoscaling configuration behavior for SpinApp manifests.

**Feature: spin-k8s-deployment, Properties 17-20: Autoscaling Configuration**
**Validates: Requirements 13.1, 13.3, 13.4, 13.5**
"""

import yaml
from hypothesis import given, strategies as st, settings
import pytest

from src.models.manifest import (
    SpinAppManifest,
    ResourceLimits,
    AutoscalingValidationError,
    validate_autoscaling_config,
)
from src.services.manifest import ManifestService


# Strategy for valid Kubernetes names (DNS-1123 subdomain)
k8s_name = st.text(
    alphabet=st.sampled_from("abcdefghijklmnopqrstuvwxyz0123456789-"),
    min_size=1,
    max_size=63,
).filter(
    lambda s: s[0].isalnum() and s[-1].isalnum() and "--" not in s
)

# Strategy for container image references
image_ref = st.builds(
    lambda registry, repo, tag: f"{registry}/{repo}:{tag}",
    registry=st.text(
        alphabet=st.sampled_from("abcdefghijklmnopqrstuvwxyz0123456789.-"),
        min_size=1,
        max_size=30,
    ).filter(lambda s: s[0].isalnum() and s[-1].isalnum()),
    repo=k8s_name,
    tag=st.text(
        alphabet=st.sampled_from("abcdefghijklmnopqrstuvwxyz0123456789.-"),
        min_size=1,
        max_size=20,
    ).filter(lambda s: s[0].isalnum()),
)


class TestAutoscalingDefaultValue:
    """Property tests for autoscaling default value.
    
    **Feature: spin-k8s-deployment, Property 17: Autoscaling Default Value**
    **Validates: Requirements 13.1**
    """


    @given(name=k8s_name, image=image_ref, namespace=k8s_name)
    @settings(max_examples=100)
    def test_autoscaling_defaults_to_true(self, name: str, image: str, namespace: str):
        """
        **Feature: spin-k8s-deployment, Property 17: Autoscaling Default Value**
        **Validates: Requirements 13.1**
        
        For any SpinApp manifest created without specifying enableAutoscaling,
        the enableAutoscaling field should default to true.
        """
        # Create manifest without specifying enable_autoscaling
        manifest = SpinAppManifest(
            name=name,
            image=image,
            namespace=namespace,
        )
        
        # Verify default value is True
        assert manifest.enable_autoscaling is True, \
            f"enable_autoscaling should default to True, got {manifest.enable_autoscaling}"

    @given(name=k8s_name, image=image_ref, namespace=k8s_name)
    @settings(max_examples=100)
    def test_autoscaling_default_in_yaml(self, name: str, image: str, namespace: str):
        """
        **Feature: spin-k8s-deployment, Property 17: Autoscaling Default Value**
        **Validates: Requirements 13.1**
        
        For any SpinApp manifest with default autoscaling (true),
        the generated YAML should include enableAutoscaling: true.
        """
        manifest = SpinAppManifest(
            name=name,
            image=image,
            namespace=namespace,
        )
        
        service = ManifestService()
        yaml_content = service.to_yaml(manifest)
        data = yaml.safe_load(yaml_content)
        
        # Verify enableAutoscaling is true in YAML
        assert "enableAutoscaling" in data["spec"], \
            "enableAutoscaling should be present in spec"
        assert data["spec"]["enableAutoscaling"] is True, \
            f"enableAutoscaling should be true, got {data['spec']['enableAutoscaling']}"


class TestAutoscalingDisablesReplicas:
    """Property tests for autoscaling disabling replicas field.
    
    **Feature: spin-k8s-deployment, Property 18: Autoscaling Disables Replicas Field**
    **Validates: Requirements 13.3**
    """

    @given(name=k8s_name, image=image_ref, namespace=k8s_name)
    @settings(max_examples=100)
    def test_autoscaling_enabled_omits_replicas(self, name: str, image: str, namespace: str):
        """
        **Feature: spin-k8s-deployment, Property 18: Autoscaling Disables Replicas Field**
        **Validates: Requirements 13.3**
        
        For any SpinApp manifest with enableAutoscaling=true,
        the generated YAML should NOT include the replicas field.
        """
        manifest = SpinAppManifest(
            name=name,
            image=image,
            namespace=namespace,
            enable_autoscaling=True,
            replicas=None,
        )
        
        service = ManifestService()
        yaml_content = service.to_yaml(manifest)
        data = yaml.safe_load(yaml_content)
        
        # Verify replicas is NOT in YAML when autoscaling is enabled
        assert "replicas" not in data["spec"], \
            f"replicas should not be present when enableAutoscaling is true, but found: {data['spec'].get('replicas')}"
        assert data["spec"]["enableAutoscaling"] is True, \
            "enableAutoscaling should be true"


class TestDisabledAutoscalingIncludesReplicas:
    """Property tests for disabled autoscaling including replicas.
    
    **Feature: spin-k8s-deployment, Property 19: Disabled Autoscaling Includes Replicas**
    **Validates: Requirements 13.4**
    """

    @given(
        name=k8s_name,
        image=image_ref,
        namespace=k8s_name,
        replicas=st.integers(min_value=1, max_value=100),
    )
    @settings(max_examples=100)
    def test_autoscaling_disabled_includes_replicas(
        self, name: str, image: str, namespace: str, replicas: int
    ):
        """
        **Feature: spin-k8s-deployment, Property 19: Disabled Autoscaling Includes Replicas**
        **Validates: Requirements 13.4**
        
        For any SpinApp manifest with enableAutoscaling=false,
        the generated YAML should include the replicas field.
        """
        manifest = SpinAppManifest(
            name=name,
            image=image,
            namespace=namespace,
            enable_autoscaling=False,
            replicas=replicas,
        )
        
        service = ManifestService()
        yaml_content = service.to_yaml(manifest)
        data = yaml.safe_load(yaml_content)
        
        # Verify replicas IS in YAML when autoscaling is disabled
        assert "replicas" in data["spec"], \
            "replicas should be present when enableAutoscaling is false"
        assert data["spec"]["replicas"] == replicas, \
            f"replicas mismatch: {data['spec']['replicas']} != {replicas}"
        assert data["spec"]["enableAutoscaling"] is False, \
            "enableAutoscaling should be false"


class TestAutoscalingReplicasMutualExclusion:
    """Property tests for autoscaling/replicas mutual exclusion.
    
    **Feature: spin-k8s-deployment, Property 20: Autoscaling and Replicas Mutual Exclusion**
    **Validates: Requirements 13.5**
    """

    @given(
        name=k8s_name,
        image=image_ref,
        namespace=k8s_name,
        replicas=st.integers(min_value=1, max_value=100),
    )
    @settings(max_examples=100)
    def test_autoscaling_true_with_replicas_raises_error(
        self, name: str, image: str, namespace: str, replicas: int
    ):
        """
        **Feature: spin-k8s-deployment, Property 20: Autoscaling and Replicas Mutual Exclusion**
        **Validates: Requirements 13.5**
        
        For any attempt to create a SpinApp manifest with enableAutoscaling=true
        AND replicas specified, the system should raise a validation error.
        """
        with pytest.raises(AutoscalingValidationError) as exc_info:
            SpinAppManifest(
                name=name,
                image=image,
                namespace=namespace,
                enable_autoscaling=True,
                replicas=replicas,
            )
        
        assert "mutually exclusive" in str(exc_info.value).lower(), \
            f"Error message should mention mutual exclusion, got: {exc_info.value}"

    @given(
        replicas=st.integers(min_value=1, max_value=100),
    )
    @settings(max_examples=100)
    def test_validate_autoscaling_config_rejects_invalid(self, replicas: int):
        """
        **Feature: spin-k8s-deployment, Property 20: Autoscaling and Replicas Mutual Exclusion**
        **Validates: Requirements 13.5**
        
        For any call to validate_autoscaling_config with enable_autoscaling=True
        AND replicas specified, the function should return invalid.
        """
        is_valid, error_msg = validate_autoscaling_config(
            enable_autoscaling=True,
            replicas=replicas,
        )
        
        assert is_valid is False, \
            "Should be invalid when autoscaling is true and replicas is specified"
        assert error_msg is not None, \
            "Error message should be provided"
        assert "mutually exclusive" in error_msg.lower(), \
            f"Error message should mention mutual exclusion, got: {error_msg}"

    @given(
        replicas=st.one_of(st.none(), st.integers(min_value=1, max_value=100)),
    )
    @settings(max_examples=100)
    def test_validate_autoscaling_config_accepts_valid(self, replicas: int | None):
        """
        **Feature: spin-k8s-deployment, Property 20: Autoscaling and Replicas Mutual Exclusion**
        **Validates: Requirements 13.5**
        
        For any valid autoscaling configuration (autoscaling=True with no replicas,
        or autoscaling=False with any replicas), validation should pass.
        """
        # Test autoscaling=True with no replicas
        is_valid, error_msg = validate_autoscaling_config(
            enable_autoscaling=True,
            replicas=None,
        )
        assert is_valid is True, "Should be valid when autoscaling is true and replicas is None"
        assert error_msg is None, "No error message for valid config"
        
        # Test autoscaling=False with any replicas
        is_valid, error_msg = validate_autoscaling_config(
            enable_autoscaling=False,
            replicas=replicas,
        )
        assert is_valid is True, "Should be valid when autoscaling is false"
        assert error_msg is None, "No error message for valid config"
