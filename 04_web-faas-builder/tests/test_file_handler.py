"""Property-based tests for file handler service.

**Feature: spin-k8s-deployment, Property 13: Single Python File spin.toml Generation**
**Feature: spin-k8s-deployment, Property 14: Zip File spin.toml Validation**
**Validates: Requirements 3.1, 3.2, 3.3, 3.4**

This module tests:
- Single Python file handling generates valid spin.toml
- Zip file extraction validates spin.toml presence
"""

import io
import zipfile
import tempfile
from pathlib import Path

from hypothesis import given, strategies as st, settings, assume

from src.services.file_handler import FileHandler, SPIN_TOML_TEMPLATE


# Strategy for valid Python module names
# Must be valid Python identifiers: start with letter or underscore,
# followed by letters, digits, or underscores
python_identifier = st.text(
    alphabet=st.sampled_from("abcdefghijklmnopqrstuvwxyz_"),
    min_size=1,
    max_size=30,
).filter(
    lambda s: s[0].isalpha() or s[0] == "_"
).filter(
    lambda s: s.isidentifier()
)

# Strategy for valid Python filenames (identifier + .py)
python_filename = st.builds(
    lambda name: f"{name}.py",
    python_identifier
)

# Strategy for simple Python code content
python_code = st.text(
    alphabet=st.characters(whitelist_categories=('L', 'N', 'P', 'Z')),
    min_size=0,
    max_size=1000,
).map(lambda s: s.encode('utf-8'))


class TestSinglePythonFileSpinTomlGeneration:
    """Property tests for single Python file spin.toml generation.
    
    **Feature: spin-k8s-deployment, Property 13: Single Python File spin.toml Generation**
    **Validates: Requirements 3.3, 3.4**
    """

    @given(
        module_name=python_identifier,
        py_content=python_code,
    )
    @settings(max_examples=100)
    def test_spin_toml_generated_with_http_trigger(
        self,
        module_name: str,
        py_content: bytes,
    ):
        """
        **Feature: spin-k8s-deployment, Property 13: Single Python File spin.toml Generation**
        **Validates: Requirements 3.3, 3.4**
        
        For any single Python file upload, the generated spin.toml should contain
        valid HTTP trigger configuration with component source set to app.wasm
        and build command using componentize-py.
        """
        filename = f"{module_name}.py"
        handler = FileHandler()
        
        with tempfile.TemporaryDirectory() as temp_dir:
            work_dir = Path(temp_dir)
            
            result = handler.handle_single_py(py_content, filename, work_dir)
            
            # Verify success
            assert result.success, f"Expected success but got error: {result.error}"
            assert result.app_dir is not None
            
            # Verify spin.toml was created
            spin_toml_path = work_dir / "spin.toml"
            assert spin_toml_path.exists(), "spin.toml should be created"
            
            # Read and verify spin.toml content
            spin_toml_content = spin_toml_path.read_text()
            
            # Verify HTTP trigger configuration (Requirement 3.3)
            assert '[[trigger.http]]' in spin_toml_content, \
                "spin.toml should contain HTTP trigger configuration"
            assert 'route = "/..."' in spin_toml_content, \
                "spin.toml should contain route configuration"
            
            # Verify component source is app.wasm (Requirement 3.4)
            assert 'source = "app.wasm"' in spin_toml_content, \
                "spin.toml should set component source to app.wasm"
            
            # Verify build command uses componentize-py (Requirement 3.4)
            assert 'componentize-py' in spin_toml_content, \
                "spin.toml should use componentize-py in build command"
            assert f'componentize {module_name}' in spin_toml_content, \
                f"spin.toml should reference module name '{module_name}' in build command"

    @given(
        module_name=python_identifier,
        py_content=python_code,
    )
    @settings(max_examples=100)
    def test_python_file_written_to_work_dir(
        self,
        module_name: str,
        py_content: bytes,
    ):
        """
        **Feature: spin-k8s-deployment, Property 13: Single Python File spin.toml Generation**
        **Validates: Requirements 3.3**
        
        For any single Python file upload, the Python file should be written
        to the work directory with the original filename.
        """
        filename = f"{module_name}.py"
        handler = FileHandler()
        
        with tempfile.TemporaryDirectory() as temp_dir:
            work_dir = Path(temp_dir)
            
            result = handler.handle_single_py(py_content, filename, work_dir)
            
            assert result.success, f"Expected success but got error: {result.error}"
            
            # Verify Python file was written
            py_path = work_dir / filename
            assert py_path.exists(), f"Python file {filename} should be written"
            
            # Verify content matches
            written_content = py_path.read_bytes()
            assert written_content == py_content, \
                "Written Python file content should match original"

    @given(
        prefix=st.text(
            alphabet=st.sampled_from("abcdefghijklmnopqrstuvwxyz"),
            min_size=1,
            max_size=10,
        ),
        suffix=st.text(
            alphabet=st.sampled_from("abcdefghijklmnopqrstuvwxyz"),
            min_size=1,
            max_size=10,
        ),
    )
    @settings(max_examples=100)
    def test_app_name_uses_hyphens_instead_of_underscores(
        self,
        prefix: str,
        suffix: str,
    ):
        """
        **Feature: spin-k8s-deployment, Property 13: Single Python File spin.toml Generation**
        **Validates: Requirements 3.3**
        
        For any module name with underscores, the generated app name should
        replace underscores with hyphens for Kubernetes compatibility.
        """
        # Generate module name with underscore
        module_name = f"{prefix}_{suffix}"
        filename = f"{module_name}.py"
        handler = FileHandler()
        
        with tempfile.TemporaryDirectory() as temp_dir:
            work_dir = Path(temp_dir)
            
            result = handler.handle_single_py(b"# test", filename, work_dir)
            
            assert result.success, f"Expected success but got error: {result.error}"
            
            spin_toml_content = (work_dir / "spin.toml").read_text()
            expected_app_name = module_name.replace("_", "-")
            
            assert f'name = "{expected_app_name}"' in spin_toml_content, \
                f"App name should be '{expected_app_name}' (underscores replaced with hyphens)"


class TestZipFileSpinTomlValidation:
    """Property tests for zip file spin.toml validation.
    
    **Feature: spin-k8s-deployment, Property 14: Zip File spin.toml Validation**
    **Validates: Requirements 3.1, 3.2**
    """

    @given(
        module_name=python_identifier,
        py_content=python_code,
    )
    @settings(max_examples=100)
    def test_zip_with_spin_toml_succeeds(
        self,
        module_name: str,
        py_content: bytes,
    ):
        """
        **Feature: spin-k8s-deployment, Property 14: Zip File spin.toml Validation**
        **Validates: Requirements 3.1**
        
        For any uploaded zip file containing spin.toml in the root,
        extraction should succeed.
        """
        # Create a zip file with spin.toml
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
            # Add spin.toml
            spin_toml_content = SPIN_TOML_TEMPLATE.format(
                app_name=module_name.replace("_", "-"),
                component_name=module_name.replace("_", "-"),
                module_name=module_name
            )
            zf.writestr("spin.toml", spin_toml_content)
            
            # Add Python file
            zf.writestr(f"{module_name}.py", py_content)
        
        zip_data = zip_buffer.getvalue()
        handler = FileHandler()
        
        with tempfile.TemporaryDirectory() as temp_dir:
            work_dir = Path(temp_dir)
            
            result = handler.handle_zip(zip_data, work_dir)
            
            # Verify success (Requirement 3.1)
            assert result.success, f"Expected success but got error: {result.error}"
            assert result.app_dir is not None
            assert result.error is None
            
            # Verify spin.toml exists
            assert (work_dir / "spin.toml").exists(), "spin.toml should exist after extraction"

    @given(
        module_name=python_identifier,
        py_content=python_code,
    )
    @settings(max_examples=100)
    def test_zip_without_spin_toml_fails(
        self,
        module_name: str,
        py_content: bytes,
    ):
        """
        **Feature: spin-k8s-deployment, Property 14: Zip File spin.toml Validation**
        **Validates: Requirements 3.2**
        
        For any uploaded zip file missing spin.toml from the root,
        the system should return an error indicating spin.toml is required.
        """
        # Create a zip file WITHOUT spin.toml
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
            # Only add Python file, no spin.toml
            zf.writestr(f"{module_name}.py", py_content)
        
        zip_data = zip_buffer.getvalue()
        handler = FileHandler()
        
        with tempfile.TemporaryDirectory() as temp_dir:
            work_dir = Path(temp_dir)
            
            result = handler.handle_zip(zip_data, work_dir)
            
            # Verify failure (Requirement 3.2)
            assert not result.success, "Expected failure when spin.toml is missing"
            assert result.app_dir is None
            assert result.error is not None
            assert "spin.toml" in result.error.lower(), \
                "Error message should mention spin.toml"

    @given(random_bytes=st.binary(min_size=10, max_size=1000))
    @settings(max_examples=100)
    def test_invalid_zip_format_fails(self, random_bytes: bytes):
        """
        **Feature: spin-k8s-deployment, Property 14: Zip File spin.toml Validation**
        **Validates: Requirements 3.1**
        
        For any invalid zip file (random bytes), the system should return
        an error indicating the file is not a valid zip.
        """
        # Skip if random bytes happen to be a valid zip
        assume(not zipfile.is_zipfile(io.BytesIO(random_bytes)))
        
        handler = FileHandler()
        
        with tempfile.TemporaryDirectory() as temp_dir:
            work_dir = Path(temp_dir)
            
            result = handler.handle_zip(random_bytes, work_dir)
            
            # Verify failure for invalid zip
            assert not result.success, "Expected failure for invalid zip format"
            assert result.app_dir is None
            assert result.error is not None

    @given(
        module_name=python_identifier,
        py_content=python_code,
        subdir_name=st.text(
            alphabet=st.sampled_from("abcdefghijklmnopqrstuvwxyz"),
            min_size=1,
            max_size=10,
        ),
    )
    @settings(max_examples=100)
    def test_zip_with_spin_toml_in_subdir_fails(
        self,
        module_name: str,
        py_content: bytes,
        subdir_name: str,
    ):
        """
        **Feature: spin-k8s-deployment, Property 14: Zip File spin.toml Validation**
        **Validates: Requirements 3.1, 3.2**
        
        For any uploaded zip file with spin.toml in a subdirectory (not root),
        the system should return an error indicating spin.toml is required in root.
        """
        # Create a zip file with spin.toml in a subdirectory
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
            # Add spin.toml in subdirectory, not root
            spin_toml_content = SPIN_TOML_TEMPLATE.format(
                app_name=module_name.replace("_", "-"),
                component_name=module_name.replace("_", "-"),
                module_name=module_name
            )
            zf.writestr(f"{subdir_name}/spin.toml", spin_toml_content)
            zf.writestr(f"{subdir_name}/{module_name}.py", py_content)
        
        zip_data = zip_buffer.getvalue()
        handler = FileHandler()
        
        with tempfile.TemporaryDirectory() as temp_dir:
            work_dir = Path(temp_dir)
            
            result = handler.handle_zip(zip_data, work_dir)
            
            # Verify failure - spin.toml must be in root
            assert not result.success, \
                "Expected failure when spin.toml is not in root"
            assert result.error is not None
            assert "spin.toml" in result.error.lower()
