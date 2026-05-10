"""File handler service for processing uploaded files.

This module handles:
- Zip file extraction and spin.toml validation
- Single Python file handling with spin.toml generation

Requirements: 3.1, 3.2, 3.3, 3.4
"""

import io
import zipfile
import tempfile
import logging
from pathlib import Path
from dataclasses import dataclass


SPIN_TOML_TEMPLATE = '''spin_manifest_version = 2

[application]
name = "{app_name}"
version = "0.1.0"
authors = ["Auto Generated"]
description = ""

[[trigger.http]]
route = "/..."
component = "{component_name}"

[component.{component_name}]
source = "app.wasm"
[component.{component_name}.build]
command = "componentize-py -w spin-http componentize {module_name} -o app.wasm"
'''


@dataclass
class FileHandlerResult:
    """Result of file handling operation."""
    success: bool
    app_dir: Path | None
    error: str | None


class FileHandler:
    """Service for handling uploaded files."""
    def __init__(self) -> None:
        self.logger = logging.getLogger(__name__)

    def handle_zip(self, zip_data: bytes, work_dir: Path) -> FileHandlerResult:
        """Extract zip and verify spin.toml exists.
        
        Requirements: 3.1, 3.2
        
        Args:
            zip_data: Raw bytes of the zip file
            work_dir: Directory to extract files to
            
        Returns:
            FileHandlerResult with success status and app directory or error
        """
        try:
            # Create BytesIO from bytes for zipfile
            zip_buffer = io.BytesIO(zip_data)
            
            # Validate it's a valid zip file
            if not zipfile.is_zipfile(zip_buffer):
                return FileHandlerResult(
                    success=False,
                    app_dir=None,
                    error="Invalid zip file format"
                )
            
            # Reset buffer position after is_zipfile check
            zip_buffer.seek(0)
            
            # Extract the zip file
            with zipfile.ZipFile(zip_buffer, 'r') as zf:
                zf.extractall(work_dir)
            
            # Check if spin.toml exists in the root
            spin_toml_path = work_dir / "spin.toml"
            if not spin_toml_path.exists():
                return FileHandlerResult(
                    success=False,
                    app_dir=None,
                    error="spin.toml not found in zip archive"
                )
            
            return FileHandlerResult(
                success=True,
                app_dir=work_dir,
                error=None
            )
            
        except zipfile.BadZipFile:
            return FileHandlerResult(
                success=False,
                app_dir=None,
                error="Invalid or corrupted zip file"
            )
        except Exception as e:
            return FileHandlerResult(
                success=False,
                app_dir=None,
                error=f"Failed to extract zip file: {str(e)}"
            )

    def handle_single_py(
        self,
        py_content: bytes,
        filename: str,
        work_dir: Path
    ) -> FileHandlerResult:
        """Create spin.toml for single Python file.
        
        Requirements: 3.3, 3.4
        
        Args:
            py_content: Raw bytes of the Python file
            filename: Original filename of the Python file
            work_dir: Directory to write files to
            
        Returns:
            FileHandlerResult with success status and app directory or error
        """
        try:
            # Strip whitespace from filename to prevent module not found errors
            filename = filename.strip()

            decoded = py_content.decode("utf-8")

            # If users provided init_incoming_handler but not IncomingHandler class,
            # inject a lightweight shim so spin-http can find the expected class.
            if "class IncomingHandler" not in decoded and "init_incoming_handler" in decoded:
                self.logger.info("Auto-injecting IncomingHandler shim for %s", filename)
                shim = """

# Auto-generated shim to expose IncomingHandler for spin-python runtime
from spin_sdk.http import IncomingHandler as _BaseIncomingHandler

try:
    _factory = init_incoming_handler
except NameError:
    _factory = None

if _factory is not None:
    class IncomingHandler(_BaseIncomingHandler):
        def __init__(self):
            self._delegate = _factory()

        def handle_request(self, request):
            return self._delegate.handle_request(request)
"""
                decoded = decoded + shim
                py_content = decoded.encode("utf-8")

            # Extract module name from filename (without .py extension)
            # Remove spaces, hyphens, underscores for valid Python module name
            # This ensures the module name matches the app name used in spin.toml
            module_name = Path(filename).stem.strip().replace(" ", "").replace("-", "").replace("_", "")

            # Generate app name: same as module_name (no separators)
            # spin.toml rules are strict:
            # - hyphen-separated words must start with a letter (test-111 fails)
            # - words must be separated with '-', not '_' (test_111 fails)
            # Solution: remove all separators (test111 works)
            app_name = module_name
            
            # Write Python file to work directory
            # Use sanitized filename (module_name + .py) to match spin.toml
            sanitized_filename = f"{module_name}.py"
            py_path = work_dir / sanitized_filename
            py_path.write_bytes(py_content)
            
            # Generate spin.toml with HTTP trigger configuration
            spin_toml_content = SPIN_TOML_TEMPLATE.format(
                app_name=app_name,
                component_name=app_name,
                module_name=module_name
            )
            
            spin_toml_path = work_dir / "spin.toml"
            spin_toml_path.write_text(spin_toml_content)
            
            return FileHandlerResult(
                success=True,
                app_dir=work_dir,
                error=None
            )
            
        except Exception as e:
            return FileHandlerResult(
                success=False,
                app_dir=None,
                error=f"Failed to handle Python file: {str(e)}"
            )

    def create_temp_work_dir(self) -> Path:
        """Create a temporary working directory.
        
        Returns:
            Path to the created temporary directory
        """
        temp_dir = tempfile.mkdtemp(prefix="spin_build_")
        return Path(temp_dir)