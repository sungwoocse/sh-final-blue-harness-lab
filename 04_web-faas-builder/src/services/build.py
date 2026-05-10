"""Build Service for Spin applications.

This module provides functionality to:
- Copy pre-configured venv template to application directory
- Install dependencies from requirements.txt
- Execute spin build via subprocess

Requirements: 3.5, 4.1, 4.2, 4.3, 5.1, 5.2, 5.3, 5.4
"""

import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

from src.config import config


@dataclass
class BuildResult:
    """Result of a build operation.
    
    Attributes:
        success: True if build completed successfully
        wasm_path: Path to the generated WASM artifact (if successful)
        error: Error message (if failed)
    """
    success: bool
    wasm_path: str | None
    error: str | None


class BuildService:
    """Service for building Spin applications.
    
    This service handles the complete build pipeline:
    1. Copy pre-configured venv template
    2. Install additional dependencies from requirements.txt
    3. Execute spin build to generate WASM artifact
    
    Requirements: 4.1, 4.2, 4.3, 5.1, 5.2, 5.3, 5.4
    """
    
    def __init__(self, venv_template_path: Path | None = None) -> None:
        """Initialize the build service.
        
        Args:
            venv_template_path: Path to the pre-configured venv template.
                               Defaults to config.venv_template_path.
        """
        self.venv_template_path = venv_template_path or config.venv_template_path

    def prepare_environment(self, app_dir: Path) -> tuple[bool, str | None]:
        """Copy venv template to application directory.
        
        Requirements: 4.1, 4.2
        
        Args:
            app_dir: Path to the application directory
            
        Returns:
            Tuple of (success, error_message)
            - success: True if venv was copied successfully
            - error_message: Error details if failed, None otherwise
        """
        target_venv = app_dir / ".venv"
        
        try:
            # Check if venv template exists
            if not self.venv_template_path.exists():
                return False, f"venv template not found at {self.venv_template_path}"
            
            # Remove existing venv if present
            if target_venv.exists():
                shutil.rmtree(target_venv)
            
            # Copy the pre-configured venv template
            # This venv should have componentize-py and spin-sdk pre-installed
            shutil.copytree(
                self.venv_template_path,
                target_venv,
                symlinks=True  # Preserve symlinks in venv
            )
            
            # Verify componentize-py and spin-sdk are available
            # by checking if the venv's bin directory exists
            venv_bin = target_venv / "bin"
            if not venv_bin.exists():
                return False, "Invalid venv template: bin directory not found"
            
            return True, None
            
        except PermissionError as e:
            return False, f"Permission denied while copying venv: {str(e)}"
        except Exception as e:
            return False, f"Failed to copy venv template: {str(e)}"

    def install_requirements(self, app_dir: Path) -> tuple[bool, str | None]:
        """Install dependencies from requirements.txt if it exists.
        
        Requirements: 3.5, 4.3
        
        Args:
            app_dir: Path to the application directory
            
        Returns:
            Tuple of (success, error_message)
            - success: True if installation succeeded or no requirements.txt
            - error_message: Error details if failed, None otherwise
        """
        req_file = app_dir / "requirements.txt"
        
        # If no requirements.txt, nothing to install
        if not req_file.exists():
            return True, None
        
        venv_pip = app_dir / ".venv" / "bin" / "pip"
        
        # Check if pip exists in the venv
        if not venv_pip.exists():
            return False, "pip not found in venv"
        
        try:
            result = subprocess.run(
                [str(venv_pip), "install", "-r", str(req_file)],
                capture_output=True,
                text=True,
                cwd=str(app_dir),
                timeout=300  # 5 minute timeout for pip install
            )
            
            if result.returncode != 0:
                return False, f"pip install failed: {result.stderr}"
            
            return True, None
            
        except subprocess.TimeoutExpired:
            return False, "pip install timed out after 5 minutes"
        except Exception as e:
            return False, f"Failed to install requirements: {str(e)}"

    def build(self, app_dir: Path) -> BuildResult:
        """Execute spin build in the application directory.
        
        Requirements: 5.1, 5.2, 5.3, 5.4
        
        Args:
            app_dir: Path to the application directory containing spin.toml
            
        Returns:
            BuildResult with success status, wasm_path, or error message
        """
        try:
            # Set up environment to use the copied venv
            venv_path = app_dir / ".venv"
            env = {
                "PATH": f"{venv_path}/bin:" + subprocess.os.environ.get("PATH", ""),
                "VIRTUAL_ENV": str(venv_path),
            }
            # Copy other environment variables
            for key, value in subprocess.os.environ.items():
                if key not in env:
                    env[key] = value
            
            result = subprocess.run(
                ["spin", "build"],
                capture_output=True,
                text=True,
                cwd=str(app_dir),
                env=env,
                timeout=600  # 10 minute timeout for build
            )
            
            if result.returncode == 0:
                # Find the generated WASM file
                # Default location is app.wasm in the app directory
                wasm_path = app_dir / "app.wasm"
                
                if wasm_path.exists():
                    return BuildResult(
                        success=True,
                        wasm_path=str(wasm_path),
                        error=None
                    )
                else:
                    # Try to find any .wasm file
                    wasm_files = list(app_dir.glob("*.wasm"))
                    if wasm_files:
                        return BuildResult(
                            success=True,
                            wasm_path=str(wasm_files[0]),
                            error=None
                        )
                    return BuildResult(
                        success=False,
                        wasm_path=None,
                        error="Build succeeded but WASM artifact not found"
                    )
            else:
                # Capture stderr for error reporting
                error_output = result.stderr or result.stdout
                return BuildResult(
                    success=False,
                    wasm_path=None,
                    error=error_output
                )
                
        except subprocess.TimeoutExpired:
            return BuildResult(
                success=False,
                wasm_path=None,
                error="spin build timed out after 10 minutes"
            )
        except FileNotFoundError:
            return BuildResult(
                success=False,
                wasm_path=None,
                error="spin CLI not found. Please ensure spin is installed and in PATH"
            )
        except Exception as e:
            return BuildResult(
                success=False,
                wasm_path=None,
                error=f"Build failed: {str(e)}"
            )

    def full_build(self, app_dir: Path) -> BuildResult:
        """Execute the complete build pipeline.
        
        This method orchestrates the full build process:
        1. Prepare environment (copy venv template)
        2. Install requirements (if requirements.txt exists)
        3. Execute spin build
        
        Args:
            app_dir: Path to the application directory
            
        Returns:
            BuildResult with success status, wasm_path, or error message
        """
        # Step 1: Prepare environment
        success, error = self.prepare_environment(app_dir)
        if not success:
            return BuildResult(
                success=False,
                wasm_path=None,
                error=f"Environment setup failed: {error}"
            )
        
        # Step 2: Install requirements
        success, error = self.install_requirements(app_dir)
        if not success:
            return BuildResult(
                success=False,
                wasm_path=None,
                error=f"Requirements installation failed: {error}"
            )
        
        # Step 3: Execute spin build
        return self.build(app_dir)
