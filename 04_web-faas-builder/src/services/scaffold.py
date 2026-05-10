"""Scaffold Service for generating SpinApp Kubernetes manifests.

This service uses spin kube scaffold to generate SpinApp manifests.
"""

import subprocess
from dataclasses import dataclass


@dataclass
class ScaffoldResult:
    """Result of scaffold operation."""
    success: bool
    yaml_content: str | None = None
    file_path: str | None = None
    error: str | None = None


class ScaffoldService:
    """Service for generating SpinApp Kubernetes manifests using spin kube scaffold."""

    def build_command(
        self,
        image_ref: str,
        component: str | None = None,
        replicas: int = 1,
        output_path: str | None = None,
    ) -> list[str]:
        """Build the spin kube scaffold command with all parameters.
        
        Requirements: 8.1, 8.2, 8.3, 8.4
        
        Args:
            image_ref: Image reference (ECR URI:tag)
            component: Optional component name
            replicas: Replica count (default: 1)
            output_path: Optional output file path
            
        Returns:
            List of command arguments for subprocess
        """
        # Base command with image reference (Requirement 8.1)
        cmd = ["spin", "kube", "scaffold", "--from", image_ref]
        
        # Add component name if specified (Requirement 8.2)
        if component:
            cmd.extend(["--component", component])
        
        # Add replica count (Requirement 8.3)
        cmd.extend(["--replicas", str(replicas)])
        
        # Add output path if specified (Requirement 8.4)
        if output_path:
            cmd.extend(["--out", output_path])
        
        return cmd

    def scaffold(
        self,
        image_ref: str,
        component: str | None = None,
        replicas: int = 1,
        output_path: str | None = None,
    ) -> ScaffoldResult:
        """Generate SpinApp manifest using spin kube scaffold.
        
        Requirements: 8.5, 8.6
        
        Args:
            image_ref: Image reference (ECR URI:tag)
            component: Optional component name
            replicas: Replica count (default: 1)
            output_path: Optional output file path
            
        Returns:
            ScaffoldResult with YAML content or file path on success,
            or error message on failure
        """
        # Build the command
        cmd = self.build_command(image_ref, component, replicas, output_path)
        
        # Execute the command (Requirement 8.5, 8.6)
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            # Success - return YAML content or file path (Requirement 8.5)
            return ScaffoldResult(
                success=True,
                yaml_content=result.stdout if not output_path else None,
                file_path=output_path,
                error=None,
            )
        else:
            # Failure - return stderr output (Requirement 8.6)
            return ScaffoldResult(
                success=False,
                yaml_content=None,
                file_path=None,
                error=result.stderr or result.stdout or "Unknown error occurred",
            )
