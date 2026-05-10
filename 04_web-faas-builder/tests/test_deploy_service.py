"""Property-based tests for Deploy Service.

This module contains property-based tests for the DeployService class,
focusing on app name generation uniqueness and custom app name preservation.
"""

from hypothesis import given, strategies as st, settings

from src.services.deploy import DeployService


# Strategy for generating random seeds to test name generation
seed_strategy = st.integers(min_value=0, max_value=1000000)


class TestGeneratedAppNameUniqueness:
    """Property tests for generated app name uniqueness.
    
    **Feature: spin-k8s-deployment, Property 11: Generated App Name Uniqueness**
    **Validates: Requirements 10.7**
    """

    @given(seed=seed_strategy)
    @settings(max_examples=100)
    def test_generated_names_have_low_collision_probability(self, seed: int):
        """
        **Feature: spin-k8s-deployment, Property 11: Generated App Name Uniqueness**
        **Validates: Requirements 10.7**
        
        For any set of generated application names (when no custom name is provided),
        the names should have low collision probability. Generating 1000 names
        should produce at least 999 unique names.
        """
        service = DeployService()
        
        # Generate 1000 names
        names = [service.generate_app_name() for _ in range(1000)]
        
        # Count unique names
        unique_names = set(names)
        
        # At least 999 out of 1000 should be unique (99.9% uniqueness)
        assert len(unique_names) >= 999, (
            f"Expected at least 999 unique names out of 1000, "
            f"but got {len(unique_names)}"
        )

    @given(seed=seed_strategy)
    @settings(max_examples=100)
    def test_generated_names_follow_kubernetes_naming_convention(self, seed: int):
        """
        **Feature: spin-k8s-deployment, Property 11: Generated App Name Uniqueness**
        **Validates: Requirements 10.7**
        
        For any generated application name, it should follow Kubernetes naming
        conventions: lowercase, alphanumeric with hyphens, starting with 'spin-'.
        """
        service = DeployService()
        
        # Generate multiple names and verify format
        for _ in range(100):
            name = service.generate_app_name()
            
            # Should start with 'spin-'
            assert name.startswith("spin-"), f"Name should start with 'spin-': {name}"
            
            # Should be lowercase
            assert name == name.lower(), f"Name should be lowercase: {name}"
            
            # Should only contain alphanumeric and hyphens
            valid_chars = set("abcdefghijklmnopqrstuvwxyz0123456789-")
            assert all(c in valid_chars for c in name), (
                f"Name should only contain lowercase alphanumeric and hyphens: {name}"
            )
            
            # Should not be empty after prefix
            assert len(name) > 5, f"Name should have content after 'spin-': {name}"

    @given(seed=seed_strategy)
    @settings(max_examples=100)
    def test_generated_names_are_non_empty_strings(self, seed: int):
        """
        **Feature: spin-k8s-deployment, Property 11: Generated App Name Uniqueness**
        **Validates: Requirements 10.7**
        
        For any generated application name, it should be a non-empty string.
        """
        service = DeployService()
        
        for _ in range(100):
            name = service.generate_app_name()
            
            assert isinstance(name, str), f"Name should be a string: {type(name)}"
            assert len(name) > 0, "Name should not be empty"


class TestCustomAppNamePreservation:
    """Property tests for custom app name preservation.
    
    **Feature: spin-k8s-deployment, Property 10: Custom App Name Preservation**
    **Validates: Requirements 10.6**
    """

    @given(custom_name=st.text(
        alphabet=st.sampled_from("abcdefghijklmnopqrstuvwxyz0123456789-"),
        min_size=1,
        max_size=63,
    ).filter(lambda s: s[0].isalnum() and s[-1].isalnum() and "--" not in s))
    @settings(max_examples=100)
    def test_custom_app_name_is_preserved_in_deploy_result(self, custom_name: str):
        """
        **Feature: spin-k8s-deployment, Property 10: Custom App Name Preservation**
        **Validates: Requirements 10.6**
        
        For any deployment request with a custom application name,
        the deployed SpinApp should use exactly that name.
        
        This test verifies that when a custom name is provided to the deploy
        method, the resulting DeployResult contains exactly that name.
        """
        from unittest.mock import patch, MagicMock
        
        service = DeployService()
        
        # Mock check_namespace to return True
        # Mock apply_manifest to return success
        # Mock get_service to return found status
        with patch.object(service, 'check_namespace', return_value=True), \
             patch.object(service, 'apply_manifest', return_value=(True, None)), \
             patch.object(service, 'get_service') as mock_get_service:
            
            mock_get_service.return_value = MagicMock(
                service_status="found",
                endpoint=f"{custom_name}.default.svc.cluster.local"
            )
            
            result = service.deploy(
                manifest_path="/tmp/test.yaml",
                namespace="default",
                app_name=custom_name,
            )
            
            # The app_name in result should be exactly the custom name
            assert result.app_name == custom_name, (
                f"Expected app_name to be '{custom_name}', "
                f"but got '{result.app_name}'"
            )
            
            # The service_name should also be the custom name
            assert result.service_name == custom_name, (
                f"Expected service_name to be '{custom_name}', "
                f"but got '{result.service_name}'"
            )

    @given(custom_name=st.text(
        alphabet=st.sampled_from("abcdefghijklmnopqrstuvwxyz0123456789-"),
        min_size=1,
        max_size=63,
    ).filter(lambda s: s[0].isalnum() and s[-1].isalnum() and "--" not in s))
    @settings(max_examples=100)
    def test_custom_name_not_modified_by_deploy(self, custom_name: str):
        """
        **Feature: spin-k8s-deployment, Property 10: Custom App Name Preservation**
        **Validates: Requirements 10.6**
        
        For any custom application name, the deploy method should not
        modify or transform the name in any way.
        """
        from unittest.mock import patch, MagicMock
        
        service = DeployService()
        
        with patch.object(service, 'check_namespace', return_value=True), \
             patch.object(service, 'apply_manifest', return_value=(True, None)), \
             patch.object(service, 'get_service') as mock_get_service:
            
            mock_get_service.return_value = MagicMock(
                service_status="found",
                endpoint=f"{custom_name}.default.svc.cluster.local"
            )
            
            result = service.deploy(
                manifest_path="/tmp/test.yaml",
                namespace="default",
                app_name=custom_name,
            )
            
            # Verify the name is exactly preserved (no trimming, case changes, etc.)
            assert result.app_name == custom_name
            assert len(result.app_name) == len(custom_name)

    @given(seed=seed_strategy)
    @settings(max_examples=100)
    def test_none_app_name_triggers_generation(self, seed: int):
        """
        **Feature: spin-k8s-deployment, Property 10: Custom App Name Preservation**
        **Validates: Requirements 10.6, 10.7**
        
        When no custom app name is provided (None), the deploy method
        should generate a unique name using Faker.
        """
        from unittest.mock import patch, MagicMock
        
        service = DeployService()
        
        with patch.object(service, 'check_namespace', return_value=True), \
             patch.object(service, 'apply_manifest', return_value=(True, None)), \
             patch.object(service, 'get_service') as mock_get_service:
            
            mock_get_service.return_value = MagicMock(
                service_status="pending",
                endpoint=None
            )
            
            result = service.deploy(
                manifest_path="/tmp/test.yaml",
                namespace="default",
                app_name=None,  # No custom name
            )
            
            # A name should be generated
            assert result.app_name is not None
            assert len(result.app_name) > 0
            
            # Generated name should start with 'spin-'
            assert result.app_name.startswith("spin-")
