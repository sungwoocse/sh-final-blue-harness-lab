"""Property-based tests for Scaffold Service.

This module tests:
- Scaffold command construction (Property 6)

**Feature: spin-k8s-deployment, Property 6: Scaffold Command Construction**
**Validates: Requirements 8.2, 8.3, 8.4**
"""

from hypothesis import given, strategies as st, settings

from src.services.scaffold import ScaffoldService


# Strategy for valid image references (registry/repo:tag format)
image_ref = st.builds(
    lambda host, repo, tag: f"{host}/{repo}:{tag}",
    host=st.text(
        alphabet=st.sampled_from("abcdefghijklmnopqrstuvwxyz0123456789.-"),
        min_size=3,
        max_size=50,
    ).filter(lambda s: s[0].isalnum() and s[-1].isalnum() and ".." not in s),
    repo=st.text(
        alphabet=st.sampled_from("abcdefghijklmnopqrstuvwxyz0123456789-_/"),
        min_size=1,
        max_size=30,
    ).filter(lambda s: s[0].isalnum()),
    tag=st.text(
        alphabet=st.sampled_from("abcdefghijklmnopqrstuvwxyz0123456789.-_"),
        min_size=1,
        max_size=128,
    ).filter(lambda s: s[0].isalnum()),
)

# Strategy for valid component names (Kubernetes naming convention)
component_name = st.text(
    alphabet=st.sampled_from("abcdefghijklmnopqrstuvwxyz0123456789-"),
    min_size=1,
    max_size=63,
).filter(lambda s: s[0].isalnum() and s[-1].isalnum() and "--" not in s)

# Strategy for valid replica counts
replica_count = st.integers(min_value=1, max_value=100)

# Strategy for valid output paths
output_path = st.builds(
    lambda dir_name, file_name: f"/tmp/{dir_name}/{file_name}.yaml",
    dir_name=st.text(
        alphabet=st.sampled_from("abcdefghijklmnopqrstuvwxyz0123456789_-"),
        min_size=1,
        max_size=20,
    ).filter(lambda s: s[0].isalnum()),
    file_name=st.text(
        alphabet=st.sampled_from("abcdefghijklmnopqrstuvwxyz0123456789_-"),
        min_size=1,
        max_size=20,
    ).filter(lambda s: s[0].isalnum()),
)


class TestScaffoldCommandConstruction:
    """Property tests for scaffold command construction.
    
    **Feature: spin-k8s-deployment, Property 6: Scaffold Command Construction**
    **Validates: Requirements 8.2, 8.3, 8.4**
    """

    @given(
        image=image_ref,
        component=component_name,
        replicas=replica_count,
        out_path=output_path,
    )
    @settings(max_examples=100)
    def test_command_includes_all_parameters(
        self,
        image: str,
        component: str,
        replicas: int,
        out_path: str,
    ):
        """
        **Feature: spin-k8s-deployment, Property 6: Scaffold Command Construction**
        **Validates: Requirements 8.2, 8.3, 8.4**
        
        For any scaffold request with component name, replica count, and output path
        specified, the constructed command should include all specified parameters
        in the correct format.
        """
        scaffold_service = ScaffoldService()
        
        # Build command with all parameters
        cmd = scaffold_service.build_command(
            image_ref=image,
            component=component,
            replicas=replicas,
            output_path=out_path,
        )
        
        # Verify base command structure
        assert cmd[0] == "spin", "Command should start with 'spin'"
        assert cmd[1] == "kube", "Second argument should be 'kube'"
        assert cmd[2] == "scaffold", "Third argument should be 'scaffold'"
        
        # Verify image reference (Requirement 8.1)
        assert "--from" in cmd, "Command should include --from flag"
        from_index = cmd.index("--from")
        assert cmd[from_index + 1] == image, f"Image ref should be {image}"
        
        # Verify component name (Requirement 8.2)
        assert "--component" in cmd, "Command should include --component flag"
        component_index = cmd.index("--component")
        assert cmd[component_index + 1] == component, f"Component should be {component}"
        
        # Verify replica count (Requirement 8.3)
        assert "--replicas" in cmd, "Command should include --replicas flag"
        replicas_index = cmd.index("--replicas")
        assert cmd[replicas_index + 1] == str(replicas), f"Replicas should be {replicas}"
        
        # Verify output path (Requirement 8.4)
        assert "--out" in cmd, "Command should include --out flag"
        out_index = cmd.index("--out")
        assert cmd[out_index + 1] == out_path, f"Output path should be {out_path}"

    @given(
        image=image_ref,
        replicas=replica_count,
    )
    @settings(max_examples=100)
    def test_command_without_optional_parameters(
        self,
        image: str,
        replicas: int,
    ):
        """
        **Feature: spin-k8s-deployment, Property 6: Scaffold Command Construction**
        **Validates: Requirements 8.1, 8.3**
        
        For any scaffold request without optional parameters (component, output_path),
        the command should still include the required image reference and replicas.
        """
        scaffold_service = ScaffoldService()
        
        # Build command without optional parameters
        cmd = scaffold_service.build_command(
            image_ref=image,
            component=None,
            replicas=replicas,
            output_path=None,
        )
        
        # Verify base command structure
        assert cmd[:3] == ["spin", "kube", "scaffold"]
        
        # Verify image reference is present
        assert "--from" in cmd
        from_index = cmd.index("--from")
        assert cmd[from_index + 1] == image
        
        # Verify replicas is present
        assert "--replicas" in cmd
        replicas_index = cmd.index("--replicas")
        assert cmd[replicas_index + 1] == str(replicas)
        
        # Verify optional parameters are NOT present
        assert "--component" not in cmd, "Component should not be in command when None"
        assert "--out" not in cmd, "Output path should not be in command when None"

    @given(
        image=image_ref,
        component=component_name,
    )
    @settings(max_examples=100)
    def test_command_with_component_only(
        self,
        image: str,
        component: str,
    ):
        """
        **Feature: spin-k8s-deployment, Property 6: Scaffold Command Construction**
        **Validates: Requirements 8.2**
        
        For any scaffold request with only component specified (no output_path),
        the command should include the component but not the output flag.
        """
        scaffold_service = ScaffoldService()
        
        # Build command with component only
        cmd = scaffold_service.build_command(
            image_ref=image,
            component=component,
            replicas=1,
            output_path=None,
        )
        
        # Verify component is present
        assert "--component" in cmd
        component_index = cmd.index("--component")
        assert cmd[component_index + 1] == component
        
        # Verify output path is NOT present
        assert "--out" not in cmd

    @given(
        image=image_ref,
        out_path=output_path,
    )
    @settings(max_examples=100)
    def test_command_with_output_path_only(
        self,
        image: str,
        out_path: str,
    ):
        """
        **Feature: spin-k8s-deployment, Property 6: Scaffold Command Construction**
        **Validates: Requirements 8.4**
        
        For any scaffold request with only output_path specified (no component),
        the command should include the output flag but not the component.
        """
        scaffold_service = ScaffoldService()
        
        # Build command with output path only
        cmd = scaffold_service.build_command(
            image_ref=image,
            component=None,
            replicas=1,
            output_path=out_path,
        )
        
        # Verify output path is present
        assert "--out" in cmd
        out_index = cmd.index("--out")
        assert cmd[out_index + 1] == out_path
        
        # Verify component is NOT present
        assert "--component" not in cmd

    @given(
        image=image_ref,
        replicas=replica_count,
    )
    @settings(max_examples=100)
    def test_replicas_always_included(
        self,
        image: str,
        replicas: int,
    ):
        """
        **Feature: spin-k8s-deployment, Property 6: Scaffold Command Construction**
        **Validates: Requirements 8.3**
        
        For any scaffold request, the replicas parameter should always be included
        in the command.
        """
        scaffold_service = ScaffoldService()
        
        # Build command
        cmd = scaffold_service.build_command(
            image_ref=image,
            replicas=replicas,
        )
        
        # Verify replicas is always present
        assert "--replicas" in cmd
        replicas_index = cmd.index("--replicas")
        assert cmd[replicas_index + 1] == str(replicas)

    @given(image=image_ref)
    @settings(max_examples=100)
    def test_default_replicas_is_one(self, image: str):
        """
        **Feature: spin-k8s-deployment, Property 6: Scaffold Command Construction**
        **Validates: Requirements 8.3**
        
        When replicas is not specified, the default value of 1 should be used.
        """
        scaffold_service = ScaffoldService()
        
        # Build command with default replicas
        cmd = scaffold_service.build_command(image_ref=image)
        
        # Verify default replicas is 1
        assert "--replicas" in cmd
        replicas_index = cmd.index("--replicas")
        assert cmd[replicas_index + 1] == "1"

    @given(
        image=image_ref,
        component=component_name,
        replicas=replica_count,
        out_path=output_path,
    )
    @settings(max_examples=100)
    def test_command_is_list_of_strings(
        self,
        image: str,
        component: str,
        replicas: int,
        out_path: str,
    ):
        """
        **Feature: spin-k8s-deployment, Property 6: Scaffold Command Construction**
        **Validates: Requirements 8.1, 8.2, 8.3, 8.4**
        
        The constructed command should be a list of strings suitable for subprocess.
        """
        scaffold_service = ScaffoldService()
        
        cmd = scaffold_service.build_command(
            image_ref=image,
            component=component,
            replicas=replicas,
            output_path=out_path,
        )
        
        # Verify it's a list
        assert isinstance(cmd, list), "Command should be a list"
        
        # Verify all elements are strings
        for i, element in enumerate(cmd):
            assert isinstance(element, str), f"Element {i} should be a string, got {type(element)}"
