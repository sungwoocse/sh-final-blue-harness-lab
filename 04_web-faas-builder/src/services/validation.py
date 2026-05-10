"""Validation Service for Python code using MyPy.

This module provides MyPy-based validation for Python source code,
capturing type errors with line numbers and error descriptions.

Requirements: 2.1, 2.2, 2.3, 2.4
"""

import subprocess
from dataclasses import dataclass


@dataclass
class ValidationResult:
    """Result of MyPy validation.
    
    Attributes:
        success: True if validation passed (no type errors)
        errors: List of error messages with line numbers
        output: Complete MyPy output (stdout + stderr)
    """
    success: bool
    errors: list[str]
    output: str


class ValidationService:
    """Service for validating Python code using MyPy.
    
    This service executes MyPy validation on Python source code and
    captures the output including line numbers and error descriptions.
    """

    def validate_python(self, source_path: str) -> ValidationResult:
        """Execute MyPy validation on Python source code.
        
        Args:
            source_path: Path to the Python file or directory to validate
            
        Returns:
            ValidationResult containing success status, errors list, and full output
            
        Requirements:
            - 2.1: Execute MyPy validation on source code first
            - 2.2: Proceed to build step if validation passes
            - 2.3: Return MyPy error output if validation fails
            - 2.4: Include line numbers and error descriptions
        """
        result = subprocess.run(
            ["mypy", source_path, "--ignore-missing-imports", "--show-column-numbers"],
            capture_output=True,
            text=True
        )
        
        success = result.returncode == 0
        
        # Parse errors from stdout when validation fails
        # MyPy outputs errors to stdout in format: file:line:column: error: message
        errors: list[str] = []
        if not success:
            for line in result.stdout.splitlines():
                # Filter out summary lines and keep only error lines
                if line and ": error:" in line:
                    errors.append(line)
        
        return ValidationResult(
            success=success,
            errors=errors,
            output=result.stdout + result.stderr
        )
