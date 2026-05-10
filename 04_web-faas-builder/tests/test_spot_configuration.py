"""Property-based tests for SpinApp Spot instance configuration.

This module tests the Spot instance configuration behavior for SpinApp manifests.

**Feature: spin-k8s-deployment, Properties 21-24: Spot Instance Configuration**
**Validates: Requirements 14.1, 14.2, 14.3, 14.4**
"""

import yaml
from hypothesis import given, strategies as st, settings
import pytest

from src.models.manifest import (
    SpinAppManifest,
    ResourceLimits,
    Toleration,
    NodeAffinity,
    PreferredSchedulingTerm,
    NodeSelectorRequirement,
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

# Strategy for custom tolerations (not the default spot toleration)
custom_toleration = st.builds(
    Toleration,
    key=st.text(
        alphabet=st.sampled_from("abcdefghijklmnopqrstuvwxyz0123456789-"),
        min_size=1,
        max_size=30,
    ).filter(lambda s: s != "spot" and s[0].isalnum()),
    operator=st.sampled_from(["Exists", "Equal"]),
    effect=st.sampled_from(["NoSchedule", "PreferNoSchedule", "NoExecute"]),
    value=st.one_of(st.none(), st.text(min_size=1, max_size=20)),
)


class TestDefaultSpotToleration:
    """Property tests for default Spot toleration.
    
    **Feature: spin-k8s-deployment, Property 21: Default Spot Toleration**
    **Validates: Requirements 14.1**
    """

    @given(name=k8s_name, image=image_ref, namespace=k8s_name)
    @settings(max_examples=100)
    def test_default_spot_toleration_included_when_use_spot_true(
        self, name: str, image: str, namespace: str
    ):
        """
        **Feature: spin-k8s-deployment, Property 21: Default Spot Toleration**
        **Validates: Requirements 14.1**
        
        For any SpinApp manifest created without explicit Spot configuration
        (use_spot defaults to true), the generated YAML should include the
        default Spot toleration (key: spot, effect: NoSchedule).
        """
        # Create manifest with default use_spot=True
        manifest = SpinAppManifest(
            name=name,
            image=image,
            namespace=namespace,
        )
        
        # Verify use_spot defaults to True
        assert manifest.use_spot is True, \
            f"use_spot should default to True, got {manifest.use_spot}"
        
        service = ManifestService()
        yaml_content = service.to_yaml(manifest)
        data = yaml.safe_load(yaml_content)
        
        # Verify tolerations are present
        assert "tolerations" in data["spec"], \
            "tolerations should be present when use_spot is true"
        
        tolerations = data["spec"]["tolerations"]
        assert isinstance(tolerations, list), \
            "tolerations should be a list"
        
        # Find the default Spot toleration
        spot_toleration = None
        for t in tolerations:
            if t.get("key") == "spot":
                spot_toleration = t
                break
        
        assert spot_toleration is not None, \
            "Default Spot toleration (key: spot) should be present"
        assert spot_toleration.get("operator") == "Exists", \
            f"Spot toleration operator should be 'Exists', got {spot_toleration.get('operator')}"
        assert spot_toleration.get("effect") == "NoSchedule", \
            f"Spot toleration effect should be 'NoSchedule', got {spot_toleration.get('effect')}"

    @given(name=k8s_name, image=image_ref, namespace=k8s_name)
    @settings(max_examples=100)
    def test_explicit_use_spot_true_includes_toleration(
        self, name: str, image: str, namespace: str
    ):
        """
        **Feature: spin-k8s-deployment, Property 21: Default Spot Toleration**
        **Validates: Requirements 14.1**
        
        For any SpinApp manifest with use_spot explicitly set to true,
        the generated YAML should include the default Spot toleration.
        """
        manifest = SpinAppManifest(
            name=name,
            image=image,
            namespace=namespace,
            use_spot=True,
        )
        
        service = ManifestService()
        yaml_content = service.to_yaml(manifest)
        data = yaml.safe_load(yaml_content)
        
        # Verify tolerations contain the Spot toleration
        tolerations = data["spec"].get("tolerations", [])
        spot_keys = [t.get("key") for t in tolerations]
        
        assert "spot" in spot_keys, \
            "Spot toleration should be present when use_spot is true"


class TestDefaultSpotAffinity:
    """Property tests for default Spot affinity.
    
    **Feature: spin-k8s-deployment, Property 22: Default Spot Affinity**
    **Validates: Requirements 14.2**
    """

    @given(name=k8s_name, image=image_ref, namespace=k8s_name)
    @settings(max_examples=100)
    def test_default_spot_affinity_included_when_use_spot_true(
        self, name: str, image: str, namespace: str
    ):
        """
        **Feature: spin-k8s-deployment, Property 22: Default Spot Affinity**
        **Validates: Requirements 14.2**
        
        For any SpinApp manifest created without explicit Spot configuration
        (use_spot defaults to true), the generated YAML should include node
        affinity preferring nodes with label spot=true.
        """
        manifest = SpinAppManifest(
            name=name,
            image=image,
            namespace=namespace,
        )
        
        service = ManifestService()
        yaml_content = service.to_yaml(manifest)
        data = yaml.safe_load(yaml_content)
        
        # Verify affinity is present
        assert "affinity" in data["spec"], \
            "affinity should be present when use_spot is true"
        
        affinity = data["spec"]["affinity"]
        assert "nodeAffinity" in affinity, \
            "nodeAffinity should be present in affinity"
        
        node_affinity = affinity["nodeAffinity"]
        assert "preferredDuringSchedulingIgnoredDuringExecution" in node_affinity, \
            "preferredDuringSchedulingIgnoredDuringExecution should be present"
        
        preferred = node_affinity["preferredDuringSchedulingIgnoredDuringExecution"]
        assert isinstance(preferred, list) and len(preferred) > 0, \
            "preferredDuringSchedulingIgnoredDuringExecution should be a non-empty list"
        
        # Check for spot=true preference
        found_spot_preference = False
        for term in preferred:
            pref = term.get("preference", {})
            match_exprs = pref.get("matchExpressions", [])
            for expr in match_exprs:
                if expr.get("key") == "spot" and "true" in expr.get("values", []):
                    found_spot_preference = True
                    break
        
        assert found_spot_preference, \
            "Node affinity should prefer nodes with label spot=true"

    @given(name=k8s_name, image=image_ref, namespace=k8s_name)
    @settings(max_examples=100)
    def test_spot_affinity_has_weight(
        self, name: str, image: str, namespace: str
    ):
        """
        **Feature: spin-k8s-deployment, Property 22: Default Spot Affinity**
        **Validates: Requirements 14.2**
        
        For any SpinApp manifest with use_spot=true, the Spot affinity
        should have a weight value for scheduling preference.
        """
        manifest = SpinAppManifest(
            name=name,
            image=image,
            namespace=namespace,
            use_spot=True,
        )
        
        service = ManifestService()
        yaml_content = service.to_yaml(manifest)
        data = yaml.safe_load(yaml_content)
        
        preferred = data["spec"]["affinity"]["nodeAffinity"][
            "preferredDuringSchedulingIgnoredDuringExecution"
        ]
        
        for term in preferred:
            assert "weight" in term, \
                "Each preferred scheduling term should have a weight"
            assert isinstance(term["weight"], int) and term["weight"] > 0, \
                f"Weight should be a positive integer, got {term['weight']}"


class TestSpotConfigurationDisabled:
    """Property tests for Spot configuration disabled.
    
    **Feature: spin-k8s-deployment, Property 23: Spot Configuration Disabled**
    **Validates: Requirements 14.3**
    """

    @given(name=k8s_name, image=image_ref, namespace=k8s_name)
    @settings(max_examples=100)
    def test_spot_toleration_omitted_when_use_spot_false(
        self, name: str, image: str, namespace: str
    ):
        """
        **Feature: spin-k8s-deployment, Property 23: Spot Configuration Disabled**
        **Validates: Requirements 14.3**
        
        For any SpinApp manifest with use_spot explicitly set to false,
        the generated YAML should not include the default Spot toleration.
        """
        manifest = SpinAppManifest(
            name=name,
            image=image,
            namespace=namespace,
            use_spot=False,
        )
        
        service = ManifestService()
        yaml_content = service.to_yaml(manifest)
        data = yaml.safe_load(yaml_content)
        
        # Verify tolerations are not present (or don't contain spot)
        tolerations = data["spec"].get("tolerations", [])
        spot_keys = [t.get("key") for t in tolerations]
        
        assert "spot" not in spot_keys, \
            "Spot toleration should NOT be present when use_spot is false"

    @given(name=k8s_name, image=image_ref, namespace=k8s_name)
    @settings(max_examples=100)
    def test_spot_affinity_omitted_when_use_spot_false(
        self, name: str, image: str, namespace: str
    ):
        """
        **Feature: spin-k8s-deployment, Property 23: Spot Configuration Disabled**
        **Validates: Requirements 14.3**
        
        For any SpinApp manifest with use_spot explicitly set to false,
        the generated YAML should not include the default Spot affinity.
        """
        manifest = SpinAppManifest(
            name=name,
            image=image,
            namespace=namespace,
            use_spot=False,
        )
        
        service = ManifestService()
        yaml_content = service.to_yaml(manifest)
        data = yaml.safe_load(yaml_content)
        
        # Verify affinity is not present
        assert "affinity" not in data["spec"], \
            "affinity should NOT be present when use_spot is false"

    @given(name=k8s_name, image=image_ref, namespace=k8s_name)
    @settings(max_examples=100)
    def test_no_spot_settings_when_disabled(
        self, name: str, image: str, namespace: str
    ):
        """
        **Feature: spin-k8s-deployment, Property 23: Spot Configuration Disabled**
        **Validates: Requirements 14.3**
        
        For any SpinApp manifest with use_spot=false and no custom tolerations,
        the generated YAML should have no tolerations or affinity sections.
        """
        manifest = SpinAppManifest(
            name=name,
            image=image,
            namespace=namespace,
            use_spot=False,
            tolerations=[],
        )
        
        service = ManifestService()
        yaml_content = service.to_yaml(manifest)
        data = yaml.safe_load(yaml_content)
        
        # Verify no tolerations
        assert "tolerations" not in data["spec"] or data["spec"]["tolerations"] == [], \
            "tolerations should be empty or absent when use_spot is false"
        
        # Verify no affinity
        assert "affinity" not in data["spec"], \
            "affinity should NOT be present when use_spot is false"


class TestCustomTolerationsInclusion:
    """Property tests for custom tolerations inclusion.
    
    **Feature: spin-k8s-deployment, Property 24: Custom Tolerations Inclusion**
    **Validates: Requirements 14.4**
    """

    @given(
        name=k8s_name,
        image=image_ref,
        namespace=k8s_name,
        custom_tols=st.lists(custom_toleration, min_size=1, max_size=3),
    )
    @settings(max_examples=100)
    def test_custom_tolerations_included_with_spot_toleration(
        self, name: str, image: str, namespace: str, custom_tols: list[Toleration]
    ):
        """
        **Feature: spin-k8s-deployment, Property 24: Custom Tolerations Inclusion**
        **Validates: Requirements 14.4**
        
        For any deployment request with custom tolerations specified,
        the generated YAML should include all custom tolerations in addition
        to the default Spot toleration (when use_spot is true).
        """
        manifest = SpinAppManifest(
            name=name,
            image=image,
            namespace=namespace,
            use_spot=True,
            tolerations=custom_tols,
        )
        
        service = ManifestService()
        yaml_content = service.to_yaml(manifest)
        data = yaml.safe_load(yaml_content)
        
        tolerations = data["spec"].get("tolerations", [])
        toleration_keys = [t.get("key") for t in tolerations]
        
        # Verify default Spot toleration is present
        assert "spot" in toleration_keys, \
            "Default Spot toleration should be present when use_spot is true"
        
        # Verify all custom tolerations are present
        for custom_tol in custom_tols:
            assert custom_tol.key in toleration_keys, \
                f"Custom toleration with key '{custom_tol.key}' should be present"

    @given(
        name=k8s_name,
        image=image_ref,
        namespace=k8s_name,
        custom_tols=st.lists(custom_toleration, min_size=1, max_size=3),
    )
    @settings(max_examples=100)
    def test_custom_tolerations_without_spot_when_disabled(
        self, name: str, image: str, namespace: str, custom_tols: list[Toleration]
    ):
        """
        **Feature: spin-k8s-deployment, Property 24: Custom Tolerations Inclusion**
        **Validates: Requirements 14.4**
        
        For any deployment request with custom tolerations and use_spot=false,
        the generated YAML should include only the custom tolerations
        (not the default Spot toleration).
        """
        manifest = SpinAppManifest(
            name=name,
            image=image,
            namespace=namespace,
            use_spot=False,
            tolerations=custom_tols,
        )
        
        service = ManifestService()
        yaml_content = service.to_yaml(manifest)
        data = yaml.safe_load(yaml_content)
        
        tolerations = data["spec"].get("tolerations", [])
        toleration_keys = [t.get("key") for t in tolerations]
        
        # Verify default Spot toleration is NOT present
        assert "spot" not in toleration_keys, \
            "Default Spot toleration should NOT be present when use_spot is false"
        
        # Verify all custom tolerations are present
        for custom_tol in custom_tols:
            assert custom_tol.key in toleration_keys, \
                f"Custom toleration with key '{custom_tol.key}' should be present"

    @given(
        name=k8s_name,
        image=image_ref,
        namespace=k8s_name,
        custom_tol=custom_toleration,
    )
    @settings(max_examples=100)
    def test_custom_toleration_values_preserved(
        self, name: str, image: str, namespace: str, custom_tol: Toleration
    ):
        """
        **Feature: spin-k8s-deployment, Property 24: Custom Tolerations Inclusion**
        **Validates: Requirements 14.4**
        
        For any custom toleration, all fields (key, operator, effect, value)
        should be preserved in the generated YAML.
        """
        manifest = SpinAppManifest(
            name=name,
            image=image,
            namespace=namespace,
            use_spot=True,
            tolerations=[custom_tol],
        )
        
        service = ManifestService()
        yaml_content = service.to_yaml(manifest)
        data = yaml.safe_load(yaml_content)
        
        tolerations = data["spec"].get("tolerations", [])
        
        # Find the custom toleration by key
        yaml_tol = None
        for t in tolerations:
            if t.get("key") == custom_tol.key:
                yaml_tol = t
                break
        
        assert yaml_tol is not None, \
            f"Custom toleration with key '{custom_tol.key}' should be present"
        
        assert yaml_tol.get("operator") == custom_tol.operator, \
            f"Operator mismatch for key '{custom_tol.key}'"
        assert yaml_tol.get("effect") == custom_tol.effect, \
            f"Effect mismatch for key '{custom_tol.key}'"
        
        if custom_tol.value is not None:
            assert yaml_tol.get("value") == custom_tol.value, \
                f"Value mismatch for key '{custom_tol.key}'"
