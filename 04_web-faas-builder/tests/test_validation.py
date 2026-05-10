"""Property-based tests for Validation Service (MyPy).

**Feature: spin-k8s-deployment, Property 15: MyPy Error Output Completeness**
**Validates: Requirements 2.3, 2.4**

This module tests:
- MyPy validation captures type errors with line numbers
- MyPy validation returns error descriptions for detected errors
- Valid Python code passes validation
"""

import tempfile
import re
import keyword
from pathlib import Path

from hypothesis import given, strategies as st, settings, assume

from src.services.validation import ValidationService, ValidationResult


# Python reserved keywords that cannot be used as variable names
PYTHON_KEYWORDS = set(keyword.kwlist)

# Strategy for valid Python variable names (excluding keywords)
python_var_name = st.text(
    alphabet=st.sampled_from("abcdefghijklmnopqrstuvwxyz_"),
    min_size=2,
    max_size=20,
).filter(
    lambda s: s[0].isalpha() or s[0] == "_"
).filter(
    lambda s: s.isidentifier()
).filter(
    lambda s: s not in PYTHON_KEYWORDS
)


# Strategy for Python type names
python_type = st.sampled_from(["int", "str", "float", "bool", "list", "dict"])


# Strategy for values that don't match the type
def mismatched_value_for_type(type_name: str) -> st.SearchStrategy:
    """Generate a value that doesn't match the given type annotation."""
    if type_name == "int":
        return st.sampled_from(['"string"', "3.14", "True", "[]", "{}"])
    elif type_name == "str":
        return st.sampled_from(["42", "3.14", "True", "[]", "{}"])
    elif type_name == "float":
        return st.sampled_from(['"string"', "True", "[]", "{}"])
    elif type_name == "bool":
        return st.sampled_from(['"string"', "42", "3.14", "[]", "{}"])
    elif type_name == "list":
        return st.sampled_from(['"string"', "42", "3.14", "True", "{}"])
    elif type_name == "dict":
        return st.sampled_from(['"string"', "42", "3.14", "True", "[]"])
    return st.sampled_from(['"string"', "42"])


class TestMyPyErrorOutputCompleteness:
    """Property tests for MyPy error output completeness.
    
    **Feature: spin-k8s-deployment, Property 15: MyPy Error Output Completeness**
    **Validates: Requirements 2.3, 2.4**
    """

    @given(
        var_name=python_var_name,
        type_name=python_type,
    )
    @settings(max_examples=20, deadline=None)
    def test_type_error_includes_line_number(
        self,
        var_name: str,
        type_name: str,
    ):
        """
        **Feature: spin-k8s-deployment, Property 15: MyPy Error Output Completeness**
        **Validates: Requirements 2.3, 2.4**
        
        For any Python code with a type error, the MyPy validation result
        should include line numbers in the error output.
        """
        # Generate Python code with a type error
        # Assign a string to a variable annotated as int (or vice versa)
        if type_name == "int":
            wrong_value = '"wrong_type"'
        elif type_name == "str":
            wrong_value = "42"
        elif type_name == "float":
            wrong_value = '"wrong_type"'
        elif type_name == "bool":
            wrong_value = '"wrong_type"'
        else:
            wrong_value = "42"
        
        code = f'''{var_name}: {type_name} = {wrong_value}
'''
        
        service = ValidationService()
        
        with tempfile.TemporaryDirectory() as temp_dir:
            py_file = Path(temp_dir) / "test_code.py"
            py_file.write_text(code)
            
            result = service.validate_python(str(py_file))
            
            # Validation should fail for type mismatch
            assert not result.success, f"Expected validation to fail for type mismatch: {code}"
            
            # Errors should contain line numbers (Requirement 2.4)
            # MyPy format: file:line:column: error: message
            assert len(result.errors) > 0, "Should have at least one error"
            
            for error in result.errors:
                # Check that error contains line number pattern
                # Format: filename:line:column: error: message
                assert re.search(r":\d+:\d+:", error), \
                    f"Error should contain line:column numbers: {error}"

    @given(
        var_name=python_var_name,
        type_name=python_type,
    )
    @settings(max_examples=20, deadline=None)
    def test_type_error_includes_error_description(
        self,
        var_name: str,
        type_name: str,
    ):
        """
        **Feature: spin-k8s-deployment, Property 15: MyPy Error Output Completeness**
        **Validates: Requirements 2.3, 2.4**
        
        For any Python code with a type error, the MyPy validation result
        should include error descriptions explaining the type mismatch.
        """
        # Generate Python code with a type error
        if type_name == "int":
            wrong_value = '"wrong_type"'
        elif type_name == "str":
            wrong_value = "42"
        elif type_name == "float":
            wrong_value = '"wrong_type"'
        elif type_name == "bool":
            wrong_value = '"wrong_type"'
        else:
            wrong_value = "42"
        
        code = f'''{var_name}: {type_name} = {wrong_value}
'''
        
        service = ValidationService()
        
        with tempfile.TemporaryDirectory() as temp_dir:
            py_file = Path(temp_dir) / "test_code.py"
            py_file.write_text(code)
            
            result = service.validate_python(str(py_file))
            
            # Validation should fail
            assert not result.success, f"Expected validation to fail: {code}"
            
            # Errors should contain descriptive messages (Requirement 2.4)
            assert len(result.errors) > 0, "Should have at least one error"
            
            for error in result.errors:
                # Error should contain "error:" marker and description
                assert ": error:" in error, \
                    f"Error should contain error description: {error}"
                
                # Error description should not be empty after "error:"
                error_parts = error.split(": error:")
                assert len(error_parts) >= 2, "Error should have description after 'error:'"
                assert len(error_parts[1].strip()) > 0, \
                    f"Error description should not be empty: {error}"

    @given(
        var_name=python_var_name,
        num_errors=st.integers(min_value=2, max_value=5),
    )
    @settings(max_examples=15, deadline=None)
    def test_multiple_errors_all_captured(
        self,
        var_name: str,
        num_errors: int,
    ):
        """
        **Feature: spin-k8s-deployment, Property 15: MyPy Error Output Completeness**
        **Validates: Requirements 2.3, 2.4**
        
        For any Python code with multiple type errors, the MyPy validation
        result should include line numbers and descriptions for all errors.
        """
        # Generate Python code with multiple type errors on different lines
        lines = []
        for i in range(num_errors):
            # Each line has a type error: assigning string to int
            lines.append(f'{var_name}_{i}: int = "error_{i}"')
        
        code = "\n".join(lines) + "\n"
        
        service = ValidationService()
        
        with tempfile.TemporaryDirectory() as temp_dir:
            py_file = Path(temp_dir) / "test_code.py"
            py_file.write_text(code)
            
            result = service.validate_python(str(py_file))
            
            # Validation should fail
            assert not result.success, f"Expected validation to fail: {code}"
            
            # Should capture all errors (one per line)
            assert len(result.errors) >= num_errors, \
                f"Expected at least {num_errors} errors, got {len(result.errors)}"
            
            # Each error should have line number and description
            for error in result.errors:
                assert re.search(r":\d+:\d+:", error), \
                    f"Error should contain line:column numbers: {error}"
                assert ": error:" in error, \
                    f"Error should contain error description: {error}"

    @given(var_name=python_var_name)
    @settings(max_examples=20, deadline=None)
    def test_valid_code_passes_validation(
        self,
        var_name: str,
    ):
        """
        **Feature: spin-k8s-deployment, Property 15: MyPy Error Output Completeness**
        **Validates: Requirements 2.2**
        
        For any valid Python code without type errors, the MyPy validation
        should pass with success=True and empty errors list.
        """
        # Generate valid Python code with correct types
        code = f'''{var_name}: int = 42
{var_name}_str: str = "hello"
{var_name}_float: float = 3.14
{var_name}_bool: bool = True
'''
        
        service = ValidationService()
        
        with tempfile.TemporaryDirectory() as temp_dir:
            py_file = Path(temp_dir) / "test_code.py"
            py_file.write_text(code)
            
            result = service.validate_python(str(py_file))
            
            # Validation should pass
            assert result.success, f"Expected validation to pass for valid code: {result.output}"
            
            # No errors should be present
            assert len(result.errors) == 0, \
                f"Valid code should have no errors: {result.errors}"

    @given(
        var_name=python_var_name,
        line_offset=st.integers(min_value=1, max_value=10),
    )
    @settings(max_examples=15, deadline=None)
    def test_error_line_number_matches_actual_line(
        self,
        var_name: str,
        line_offset: int,
    ):
        """
        **Feature: spin-k8s-deployment, Property 15: MyPy Error Output Completeness**
        **Validates: Requirements 2.4**
        
        For any Python code with a type error on a specific line, the MyPy
        validation result should report the correct line number.
        """
        # Generate code with blank lines before the error
        blank_lines = "\n" * line_offset
        error_line = line_offset + 1  # 1-indexed
        
        code = f'''{blank_lines}{var_name}: int = "type_error"
'''
        
        service = ValidationService()
        
        with tempfile.TemporaryDirectory() as temp_dir:
            py_file = Path(temp_dir) / "test_code.py"
            py_file.write_text(code)
            
            result = service.validate_python(str(py_file))
            
            # Validation should fail
            assert not result.success, f"Expected validation to fail: {code}"
            assert len(result.errors) > 0, "Should have at least one error"
            
            # Check that the reported line number matches the actual error line
            error = result.errors[0]
            match = re.search(r":(\d+):\d+:", error)
            assert match, f"Error should contain line number: {error}"
            
            reported_line = int(match.group(1))
            assert reported_line == error_line, \
                f"Expected error on line {error_line}, got line {reported_line}"

    def test_output_contains_full_mypy_output(self):
        """
        **Feature: spin-k8s-deployment, Property 15: MyPy Error Output Completeness**
        **Validates: Requirements 2.3**
        
        The output field should contain the complete MyPy output for debugging.
        """
        code = '''x: int = "wrong"
y: str = 42
'''
        
        service = ValidationService()
        
        with tempfile.TemporaryDirectory() as temp_dir:
            py_file = Path(temp_dir) / "test_code.py"
            py_file.write_text(code)
            
            result = service.validate_python(str(py_file))
            
            # Output should contain the full MyPy output
            assert len(result.output) > 0, "Output should not be empty"
            
            # Output should contain error information
            assert "error" in result.output.lower(), \
                f"Output should contain error information: {result.output}"
