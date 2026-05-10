"""Property-based tests for SpinApp manifest round-trip consistency.

**Feature: spin-k8s-deployment, Property 1: SpinApp Manifest Round-Trip Consistency**
**Validates: Requirements 12.4**

This module tests that serializing a SpinAppManifest to YAML and then
deserializing it back produces an equivalent object.
"""

from hypothesis import given, strategies as st, settings

from src.models.manifest import SpinAppManifest, ResourceLimits
from src.services.manifest import ManifestService


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

# Strategy for valid Kubernetes resource values
resource_value = st.one_of(
    st.builds(lambda n: f"{n}m", st.integers(min_value=1, max_value=10000)),
    st.builds(lambda n: f"{n}Mi", st.integers(min_value=1, max_value=10000)),
    st.builds(lambda n: f"{n}Gi", st.integers(min_value=1, max_value=100)),
    st.builds(lambda n: f"{n}Ki", st.integers(min_value=1, max_value=100000)),
    st.builds(lambda n: str(n), st.integers(min_value=1, max_value=10000)),
)

# Strategy for optional resource values
optional_resource = st.one_of(st.none(), resource_value)

# Strategy for ResourceLimits
resource_limits_strategy = st.builds(
    ResourceLimits,
    cpu_limit=optional_resource,
    memory_limit=optional_resource,
    cpu_request=optional_resource,
    memory_request=optional_resource,
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

# Strategy for autoscaling configuration
# When enable_autoscaling is True, replicas must be None
# When enable_autoscaling is False, replicas can be set
autoscaling_config = st.one_of(
    # Autoscaling enabled (default) - replicas must be None
    st.tuples(st.just(True), st.none()),
    # Autoscaling disabled - replicas can be set
    st.tuples(st.just(False), st.integers(min_value=1, max_value=100)),
)

# Strategy for SpinAppManifest
spinapp_manifest_strategy = autoscaling_config.flatmap(
    lambda config: st.builds(
        SpinAppManifest,
        name=k8s_name,
        image=image_ref,
        namespace=k8s_name,
        replicas=st.just(config[1]),
        service_account=st.one_of(st.none(), k8s_name),
        resources=resource_limits_strategy,
        enable_autoscaling=st.just(config[0]),
    )
)


class TestManifestRoundTrip:
    """Property tests for manifest round-trip consistency.
    
    **Feature: spin-k8s-deployment, Property 1: SpinApp Manifest Round-Trip Consistency**
    **Validates: Requirements 12.4**
    """

    @given(manifest=spinapp_manifest_strategy)
    @settings(max_examples=100)
    def test_roundtrip_preserves_manifest(self, manifest: SpinAppManifest):
        """
        **Feature: spin-k8s-deployment, Property 1: SpinApp Manifest Round-Trip Consistency**
        **Validates: Requirements 12.4**
        
        For any valid SpinApp configuration object, serializing it to YAML
        and then deserializing the YAML back should produce an object
        equivalent to the original.
        """
        service = ManifestService()
        
        # Serialize to YAML
        yaml_content = service.to_yaml(manifest)
        
        # Deserialize back to object
        restored = service.from_yaml(yaml_content)
        
        # Verify all fields are preserved
        assert restored.name == manifest.name, f"name mismatch: {restored.name} != {manifest.name}"
        assert restored.namespace == manifest.namespace, f"namespace mismatch: {restored.namespace} != {manifest.namespace}"
        assert restored.image == manifest.image, f"image mismatch: {restored.image} != {manifest.image}"
        assert restored.replicas == manifest.replicas, f"replicas mismatch: {restored.replicas} != {manifest.replicas}"
        assert restored.service_account == manifest.service_account, f"service_account mismatch: {restored.service_account} != {manifest.service_account}"
        assert restored.api_version == manifest.api_version, f"api_version mismatch: {restored.api_version} != {manifest.api_version}"
        assert restored.kind == manifest.kind, f"kind mismatch: {restored.kind} != {manifest.kind}"
        assert restored.enable_autoscaling == manifest.enable_autoscaling, f"enable_autoscaling mismatch: {restored.enable_autoscaling} != {manifest.enable_autoscaling}"
        
        # Verify resource limits are preserved
        assert restored.resources.cpu_limit == manifest.resources.cpu_limit, \
            f"cpu_limit mismatch: {restored.resources.cpu_limit} != {manifest.resources.cpu_limit}"
        assert restored.resources.memory_limit == manifest.resources.memory_limit, \
            f"memory_limit mismatch: {restored.resources.memory_limit} != {manifest.resources.memory_limit}"
        assert restored.resources.cpu_request == manifest.resources.cpu_request, \
            f"cpu_request mismatch: {restored.resources.cpu_request} != {manifest.resources.cpu_request}"
        assert restored.resources.memory_request == manifest.resources.memory_request, \
            f"memory_request mismatch: {restored.resources.memory_request} != {manifest.resources.memory_request}"


class TestResourceLimitsInManifest:
    """Property tests for resource limits in manifest.
    
    **Feature: spin-k8s-deployment, Property 7: Resource Limits in Manifest**
    **Validates: Requirements 9.1, 9.2, 9.3, 9.4**
    """

    @given(
        name=k8s_name,
        image=image_ref,
        cpu_limit=resource_value,
        memory_limit=resource_value,
        cpu_request=resource_value,
        memory_request=resource_value,
    )
    @settings(max_examples=100)
    def test_resource_limits_included_in_yaml(
        self,
        name: str,
        image: str,
        cpu_limit: str,
        memory_limit: str,
        cpu_request: str,
        memory_request: str,
    ):
        """
        **Feature: spin-k8s-deployment, Property 7: Resource Limits in Manifest**
        **Validates: Requirements 9.1, 9.2, 9.3, 9.4**
        
        For any SpinApp manifest with resource limits (CPU/memory limits and requests)
        specified, the generated YAML should include all specified resource values
        in the correct structure.
        """
        import yaml
        
        # Create manifest with all resource limits specified
        resources = ResourceLimits(
            cpu_limit=cpu_limit,
            memory_limit=memory_limit,
            cpu_request=cpu_request,
            memory_request=memory_request,
        )
        manifest = SpinAppManifest(
            name=name,
            image=image,
            resources=resources,
        )
        
        service = ManifestService()
        yaml_content = service.to_yaml(manifest)
        
        # Parse the generated YAML to verify structure
        data = yaml.safe_load(yaml_content)
        
        # Verify resources section exists
        assert "spec" in data, "spec section missing from YAML"
        assert "resources" in data["spec"], "resources section missing from spec"
        
        resources_data = data["spec"]["resources"]
        
        # Verify limits section (Requirements 9.1, 9.2)
        assert "limits" in resources_data, "limits section missing from resources"
        assert resources_data["limits"]["cpu"] == cpu_limit, \
            f"CPU limit mismatch: {resources_data['limits'].get('cpu')} != {cpu_limit}"
        assert resources_data["limits"]["memory"] == memory_limit, \
            f"Memory limit mismatch: {resources_data['limits'].get('memory')} != {memory_limit}"
        
        # Verify requests section (Requirements 9.3, 9.4)
        assert "requests" in resources_data, "requests section missing from resources"
        assert resources_data["requests"]["cpu"] == cpu_request, \
            f"CPU request mismatch: {resources_data['requests'].get('cpu')} != {cpu_request}"
        assert resources_data["requests"]["memory"] == memory_request, \
            f"Memory request mismatch: {resources_data['requests'].get('memory')} != {memory_request}"

    @given(
        name=k8s_name,
        image=image_ref,
        cpu_limit=resource_value,
    )
    @settings(max_examples=100)
    def test_cpu_limit_only_included(self, name: str, image: str, cpu_limit: str):
        """
        **Feature: spin-k8s-deployment, Property 7: Resource Limits in Manifest**
        **Validates: Requirements 9.1**
        
        For any SpinApp manifest with only CPU limit specified,
        the generated YAML should include the CPU limit in the correct structure.
        """
        import yaml
        
        resources = ResourceLimits(cpu_limit=cpu_limit)
        manifest = SpinAppManifest(name=name, image=image, resources=resources)
        
        service = ManifestService()
        yaml_content = service.to_yaml(manifest)
        data = yaml.safe_load(yaml_content)
        
        assert "resources" in data["spec"], "resources section missing"
        assert "limits" in data["spec"]["resources"], "limits section missing"
        assert data["spec"]["resources"]["limits"]["cpu"] == cpu_limit

    @given(
        name=k8s_name,
        image=image_ref,
        memory_limit=resource_value,
    )
    @settings(max_examples=100)
    def test_memory_limit_only_included(self, name: str, image: str, memory_limit: str):
        """
        **Feature: spin-k8s-deployment, Property 7: Resource Limits in Manifest**
        **Validates: Requirements 9.2**
        
        For any SpinApp manifest with only memory limit specified,
        the generated YAML should include the memory limit in the correct structure.
        """
        import yaml
        
        resources = ResourceLimits(memory_limit=memory_limit)
        manifest = SpinAppManifest(name=name, image=image, resources=resources)
        
        service = ManifestService()
        yaml_content = service.to_yaml(manifest)
        data = yaml.safe_load(yaml_content)
        
        assert "resources" in data["spec"], "resources section missing"
        assert "limits" in data["spec"]["resources"], "limits section missing"
        assert data["spec"]["resources"]["limits"]["memory"] == memory_limit

    @given(
        name=k8s_name,
        image=image_ref,
        cpu_request=resource_value,
    )
    @settings(max_examples=100)
    def test_cpu_request_only_included(self, name: str, image: str, cpu_request: str):
        """
        **Feature: spin-k8s-deployment, Property 7: Resource Limits in Manifest**
        **Validates: Requirements 9.3**
        
        For any SpinApp manifest with only CPU request specified,
        the generated YAML should include the CPU request in the correct structure.
        """
        import yaml
        
        resources = ResourceLimits(cpu_request=cpu_request)
        manifest = SpinAppManifest(name=name, image=image, resources=resources)
        
        service = ManifestService()
        yaml_content = service.to_yaml(manifest)
        data = yaml.safe_load(yaml_content)
        
        assert "resources" in data["spec"], "resources section missing"
        assert "requests" in data["spec"]["resources"], "requests section missing"
        assert data["spec"]["resources"]["requests"]["cpu"] == cpu_request

    @given(
        name=k8s_name,
        image=image_ref,
        memory_request=resource_value,
    )
    @settings(max_examples=100)
    def test_memory_request_only_included(self, name: str, image: str, memory_request: str):
        """
        **Feature: spin-k8s-deployment, Property 7: Resource Limits in Manifest**
        **Validates: Requirements 9.4**
        
        For any SpinApp manifest with only memory request specified,
        the generated YAML should include the memory request in the correct structure.
        """
        import yaml
        
        resources = ResourceLimits(memory_request=memory_request)
        manifest = SpinAppManifest(name=name, image=image, resources=resources)
        
        service = ManifestService()
        yaml_content = service.to_yaml(manifest)
        data = yaml.safe_load(yaml_content)
        
        assert "resources" in data["spec"], "resources section missing"
        assert "requests" in data["spec"]["resources"], "requests section missing"
        assert data["spec"]["resources"]["requests"]["memory"] == memory_request


class TestNamespaceAndServiceAccountInManifest:
    """Property tests for namespace and ServiceAccount in manifest.
    
    **Feature: spin-k8s-deployment, Property 9: Namespace and ServiceAccount in Manifest**
    **Validates: Requirements 10.1, 10.2**
    """

    @given(
        name=k8s_name,
        image=image_ref,
        namespace=k8s_name,
        service_account=k8s_name,
    )
    @settings(max_examples=100)
    def test_namespace_and_service_account_included_in_yaml(
        self,
        name: str,
        image: str,
        namespace: str,
        service_account: str,
    ):
        """
        **Feature: spin-k8s-deployment, Property 9: Namespace and ServiceAccount in Manifest**
        **Validates: Requirements 10.1, 10.2**
        
        For any SpinApp manifest with namespace and ServiceAccount specified,
        the generated YAML should include the namespace in metadata and
        serviceAccountName in spec.
        """
        import yaml
        
        manifest = SpinAppManifest(
            name=name,
            image=image,
            namespace=namespace,
            service_account=service_account,
        )
        
        service = ManifestService()
        yaml_content = service.to_yaml(manifest)
        
        # Parse the generated YAML to verify structure
        data = yaml.safe_load(yaml_content)
        
        # Verify namespace is in metadata (Requirement 10.1)
        assert "metadata" in data, "metadata section missing from YAML"
        assert "namespace" in data["metadata"], "namespace missing from metadata"
        assert data["metadata"]["namespace"] == namespace, \
            f"Namespace mismatch: {data['metadata']['namespace']} != {namespace}"
        
        # Verify serviceAccountName is in spec (Requirement 10.2)
        assert "spec" in data, "spec section missing from YAML"
        assert "serviceAccountName" in data["spec"], "serviceAccountName missing from spec"
        assert data["spec"]["serviceAccountName"] == service_account, \
            f"ServiceAccount mismatch: {data['spec']['serviceAccountName']} != {service_account}"

    @given(
        name=k8s_name,
        image=image_ref,
        namespace=k8s_name,
    )
    @settings(max_examples=100)
    def test_namespace_only_included_in_yaml(
        self,
        name: str,
        image: str,
        namespace: str,
    ):
        """
        **Feature: spin-k8s-deployment, Property 9: Namespace and ServiceAccount in Manifest**
        **Validates: Requirements 10.1**
        
        For any SpinApp manifest with namespace specified (without ServiceAccount),
        the generated YAML should include the namespace in metadata.
        """
        import yaml
        
        manifest = SpinAppManifest(
            name=name,
            image=image,
            namespace=namespace,
            service_account=None,
        )
        
        service = ManifestService()
        yaml_content = service.to_yaml(manifest)
        
        # Parse the generated YAML to verify structure
        data = yaml.safe_load(yaml_content)
        
        # Verify namespace is in metadata (Requirement 10.1)
        assert "metadata" in data, "metadata section missing from YAML"
        assert "namespace" in data["metadata"], "namespace missing from metadata"
        assert data["metadata"]["namespace"] == namespace, \
            f"Namespace mismatch: {data['metadata']['namespace']} != {namespace}"
        
        # Verify serviceAccountName is NOT in spec when not specified
        assert "serviceAccountName" not in data.get("spec", {}), \
            "serviceAccountName should not be present when not specified"

    @given(
        name=k8s_name,
        image=image_ref,
        service_account=k8s_name,
    )
    @settings(max_examples=100)
    def test_service_account_only_included_in_yaml(
        self,
        name: str,
        image: str,
        service_account: str,
    ):
        """
        **Feature: spin-k8s-deployment, Property 9: Namespace and ServiceAccount in Manifest**
        **Validates: Requirements 10.2**
        
        For any SpinApp manifest with ServiceAccount specified,
        the generated YAML should include serviceAccountName in spec.
        """
        import yaml
        
        manifest = SpinAppManifest(
            name=name,
            image=image,
            service_account=service_account,
        )
        
        service = ManifestService()
        yaml_content = service.to_yaml(manifest)
        
        # Parse the generated YAML to verify structure
        data = yaml.safe_load(yaml_content)
        
        # Verify serviceAccountName is in spec (Requirement 10.2)
        assert "spec" in data, "spec section missing from YAML"
        assert "serviceAccountName" in data["spec"], "serviceAccountName missing from spec"
        assert data["spec"]["serviceAccountName"] == service_account, \
            f"ServiceAccount mismatch: {data['spec']['serviceAccountName']} != {service_account}"
