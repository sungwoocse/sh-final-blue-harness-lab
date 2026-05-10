"""Configuration and constants for Spin K8s Deployment Tool."""

import os
from pathlib import Path
from dataclasses import dataclass, field


# Default ECR registry URL
DEFAULT_ECR_REGISTRY_URL = "217350599014.dkr.ecr.ap-northeast-2.amazonaws.com/blue-final-faas-app"


@dataclass
class Config:
    """Application configuration settings."""

    # venv template path (pre-configured with componentize-py and spin-sdk)
    venv_template_path: Path = field(
        default_factory=lambda: Path("/opt/spin-python-venv")
    )

    # Default work directory for build operations
    work_dir: Path = field(
        default_factory=lambda: Path("/tmp/spin-builds")
    )

    # Default SpinApp settings
    default_namespace: str = "default"
    default_replicas: int = 1

    # SpinApp CRD settings
    spinapp_api_version: str = "core.spinkube.dev/v1alpha1"
    spinapp_kind: str = "SpinApp"

    # Default resource limits
    default_cpu_limit: str | None = None
    default_memory_limit: str | None = None
    default_cpu_request: str | None = None
    default_memory_request: str | None = None

    # Service defaults
    default_service_type: str = "ClusterIP"
    default_service_port: int = 80
    default_target_port: int = 80

    # ECR registry URL (from environment variable or default)
    ecr_registry_url: str = field(
        default_factory=lambda: os.environ.get("ECR_REGISTRY_URL", DEFAULT_ECR_REGISTRY_URL)
    )


# spin.toml template for single Python file uploads
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

# Kubernetes resource format regex pattern
# Valid formats: 100m (millicores), 128Mi (mebibytes), 1Gi (gibibytes), etc.
RESOURCE_FORMAT_PATTERN = r'^[0-9]+(\.[0-9]+)?(m|Ki|Mi|Gi|Ti|Pi|Ei|k|M|G|T|P|E)?$'


# Global config instance
config = Config()
