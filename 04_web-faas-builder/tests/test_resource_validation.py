"""Property-based tests for resource format validation.

**Feature: spin-k8s-deployment, Property 8: Invalid Resource Format Rejection**
**Validates: Requirements 9.5**

For any resource value that does not conform to Kubernetes resource format
(e.g., negative values, invalid units), the system should reject the input
with a validation error.
"""

import pytest
from hypothesis import given, settings, strategies as st, assume

from src.models.manifest import (
    ResourceLimits,
    ResourceValidationError,
    validate_resource_format,
)


# Strategy for generating valid Kubernetes resource values
@st.composite
def valid_resource_value(draw):
    """Generate valid Kubernetes resource format values.
    
    Valid formats:
    - Plain integers: 100, 200
    - Millicores: 100m, 500m
    - Binary units: 128Ki, 256Mi, 1Gi, 2Ti, 1Pi, 1Ei
    - Decimal units: 1k, 1M, 1G, 1T, 1P, 1E
    """
    number = draw(st.integers(min_value=1, max_value=10000))
    unit = draw(st.sampled_from([
        "",      # plain integer
        "m",     # millicores
        "Ki",    # kibibytes
        "Mi",    # mebibytes
        "Gi",    # gibibytes
        "Ti",    # tebibytes
        "Pi",    # pebibytes
        "Ei",    # exbibytes
        "k",     # kilobytes (decimal)
        "M",     # megabytes (decimal)
        "G",     # gigabytes (decimal)
        "T",     # terabytes (decimal)
        "P",     # petabytes (decimal)
        "E",     # exabytes (decimal)
    ]))
    return f"{number}{unit}"


# Strategy for generating invalid resource values
@st.composite
def invalid_resource_value(draw):
    """Generate invalid Kubernetes resource format values.
    
    Invalid formats include:
    - Negative values
    - Invalid units
    - Random text
    - Empty strings
    - Values with spaces
    """
    strategy = draw(st.sampled_from([
        "negative",
        "invalid_unit",
        "random_text",
        "with_spaces",
        "special_chars",
    ]))
    
    if strategy == "negative":
        # Negative values are invalid
        number = draw(st.integers(min_value=-10000, max_value=-1))
        unit = draw(st.sampled_from(["", "m", "Mi", "Gi"]))
        return f"{number}{unit}"
    
    elif strategy == "invalid_unit":
        # Invalid unit suffixes
        number = draw(st.integers(min_value=1, max_value=10000))
        invalid_unit = draw(st.sampled_from([
            "mb", "MB", "gb", "GB", "kb", "KB",  # Common mistakes
            "mib", "MiB", "gib", "GiB",          # Wrong case
            "bytes", "B", "b",                    # Not valid K8s units
            "mm", "gg", "tt",                     # Doubled letters
            "x", "y", "z",                        # Random letters
        ]))
        return f"{number}{invalid_unit}"
    
    elif strategy == "random_text":
        # Random text that doesn't match resource format
        text = draw(st.text(
            min_size=1, 
            max_size=10,
            alphabet=st.characters(whitelist_categories=('L',))
        ))
        # Ensure it doesn't accidentally match valid format
        assume(not text.isdigit())
        return text
    
    elif strategy == "with_spaces":
        # Values with spaces are invalid
        number = draw(st.integers(min_value=1, max_value=10000))
        unit = draw(st.sampled_from(["m", "Mi", "Gi"]))
        return f"{number} {unit}"
    
    else:  # special_chars
        # Values with special characters
        number = draw(st.integers(min_value=1, max_value=10000))
        special = draw(st.sampled_from(["!", "@", "#", "$", "%"]))
        return f"{number}{special}Mi"


class TestResourceFormatValidation:
    """Property-based tests for resource format validation.
    
    **Feature: spin-k8s-deployment, Property 8: Invalid Resource Format Rejection**
    """

    @given(value=valid_resource_value())
    @settings(max_examples=100)
    def test_valid_resource_formats_accepted(self, value: str):
        """
        **Feature: spin-k8s-deployment, Property 8: Invalid Resource Format Rejection**
        **Validates: Requirements 9.5**
        
        For any valid Kubernetes resource format value, validation should succeed
        and return the same value.
        """
        result = validate_resource_format(value, "test_field")
        assert result == value, f"Valid value '{value}' should be accepted"

    @given(value=invalid_resource_value())
    @settings(max_examples=100)
    def test_invalid_resource_formats_rejected(self, value: str):
        """
        **Feature: spin-k8s-deployment, Property 8: Invalid Resource Format Rejection**
        **Validates: Requirements 9.5**
        
        For any invalid Kubernetes resource format value, validation should raise
        ResourceValidationError with a descriptive message.
        """
        with pytest.raises(ResourceValidationError) as exc_info:
            validate_resource_format(value, "test_field")
        
        # Verify error message contains useful information
        error_msg = str(exc_info.value)
        assert "test_field" in error_msg, "Error should mention the field name"
        assert value in error_msg, "Error should mention the invalid value"

    @given(
        cpu_limit=st.one_of(st.none(), valid_resource_value()),
        memory_limit=st.one_of(st.none(), valid_resource_value()),
        cpu_request=st.one_of(st.none(), valid_resource_value()),
        memory_request=st.one_of(st.none(), valid_resource_value()),
    )
    @settings(max_examples=100)
    def test_resource_limits_accepts_valid_values(
        self, 
        cpu_limit: str | None,
        memory_limit: str | None,
        cpu_request: str | None,
        memory_request: str | None,
    ):
        """
        **Feature: spin-k8s-deployment, Property 8: Invalid Resource Format Rejection**
        **Validates: Requirements 9.5**
        
        For any combination of valid resource values (or None), ResourceLimits
        should be created successfully.
        """
        limits = ResourceLimits(
            cpu_limit=cpu_limit,
            memory_limit=memory_limit,
            cpu_request=cpu_request,
            memory_request=memory_request,
        )
        
        assert limits.cpu_limit == cpu_limit
        assert limits.memory_limit == memory_limit
        assert limits.cpu_request == cpu_request
        assert limits.memory_request == memory_request

    @given(invalid_value=invalid_resource_value())
    @settings(max_examples=100)
    def test_resource_limits_rejects_invalid_cpu_limit(self, invalid_value: str):
        """
        **Feature: spin-k8s-deployment, Property 8: Invalid Resource Format Rejection**
        **Validates: Requirements 9.5**
        
        For any invalid cpu_limit value, ResourceLimits creation should raise
        ResourceValidationError.
        """
        with pytest.raises(ResourceValidationError):
            ResourceLimits(cpu_limit=invalid_value)

    @given(invalid_value=invalid_resource_value())
    @settings(max_examples=100)
    def test_resource_limits_rejects_invalid_memory_limit(self, invalid_value: str):
        """
        **Feature: spin-k8s-deployment, Property 8: Invalid Resource Format Rejection**
        **Validates: Requirements 9.5**
        
        For any invalid memory_limit value, ResourceLimits creation should raise
        ResourceValidationError.
        """
        with pytest.raises(ResourceValidationError):
            ResourceLimits(memory_limit=invalid_value)

    @given(invalid_value=invalid_resource_value())
    @settings(max_examples=100)
    def test_resource_limits_rejects_invalid_cpu_request(self, invalid_value: str):
        """
        **Feature: spin-k8s-deployment, Property 8: Invalid Resource Format Rejection**
        **Validates: Requirements 9.5**
        
        For any invalid cpu_request value, ResourceLimits creation should raise
        ResourceValidationError.
        """
        with pytest.raises(ResourceValidationError):
            ResourceLimits(cpu_request=invalid_value)

    @given(invalid_value=invalid_resource_value())
    @settings(max_examples=100)
    def test_resource_limits_rejects_invalid_memory_request(self, invalid_value: str):
        """
        **Feature: spin-k8s-deployment, Property 8: Invalid Resource Format Rejection**
        **Validates: Requirements 9.5**
        
        For any invalid memory_request value, ResourceLimits creation should raise
        ResourceValidationError.
        """
        with pytest.raises(ResourceValidationError):
            ResourceLimits(memory_request=invalid_value)
