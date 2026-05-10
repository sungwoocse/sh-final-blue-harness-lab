"""
Configuration module for Python WASM Deploy Platform.
Reads Docker Hub credentials and Kubernetes configuration from files.
"""
import os
from pathlib import Path
from dataclasses import dataclass
from typing import Optional


@dataclass
class DockerConfig:
    """Docker Hub authentication configuration."""
    username: str
    password: str
    registry: str = "docker.io"


@dataclass
class KubernetesConfig:
    """Kubernetes cluster configuration."""
    config_path: str
    server: str = "https://192.168.50.235:6443"
    context: str = "default"


@dataclass
class RegistryConfig:
    """OCI Registry configuration for WASM artifacts."""
    builder_image: str = "docker.io/galaxyeunha0530/wasm-spin-builder"
    wasm_registry: str = "docker.io/galaxyeunha0530/wasm-test"


def _find_project_root() -> Path:
    """Find the project root directory by looking for marker files."""
    current = Path(__file__).resolve().parent
    while current != current.parent:
        if (current / "kube-config").exists() or (current.parent / "kube-config").exists():
            if (current / "kube-config").exists():
                return current
            return current.parent
        current = current.parent
    # Default to two levels up from this file (app/config.py -> project root)
    return Path(__file__).resolve().parent.parent.parent


def load_docker_config(secret_file: Optional[str] = None) -> DockerConfig:
    """
    Load Docker Hub credentials from secret file.
    
    Args:
        secret_file: Path to the dockerhub-secret.txt file.
                    If None, searches in project root.
    
    Returns:
        DockerConfig with credentials.
    
    Raises:
        FileNotFoundError: If secret file doesn't exist.
        ValueError: If required fields are missing.
    """
    if secret_file is None:
        project_root = _find_project_root()
        # Check multiple possible locations
        possible_paths = [
            project_root / "dockerhub-secret.txt",
            project_root / "dockerub-seccret.txt",  # Handle typo in filename
            project_root.parent / "dockerhub-secret.txt",
            project_root.parent / "dockerub-seccret.txt",
        ]
        for path in possible_paths:
            if path.exists():
                secret_file = str(path)
                break
        else:
            raise FileNotFoundError(
                f"Docker secret file not found. Searched: {[str(p) for p in possible_paths]}"
            )
    
    config = {}
    with open(secret_file, "r") as f:
        for line in f:
            line = line.strip()
            if line and "=" in line and not line.startswith("#"):
                key, value = line.split("=", 1)
                config[key.strip()] = value.strip()
    
    required_fields = ["DOCKER_USERNAME", "DOCKER_PASSWORD"]
    missing = [f for f in required_fields if f not in config]
    if missing:
        raise ValueError(f"Missing required fields in Docker secret: {missing}")
    
    return DockerConfig(
        username=config["DOCKER_USERNAME"],
        password=config["DOCKER_PASSWORD"],
        registry=config.get("DOCKER_REGISTRY", "docker.io"),
    )


def load_kubernetes_config(config_file: Optional[str] = None) -> KubernetesConfig:
    """
    Load Kubernetes configuration file path.
    
    Args:
        config_file: Path to the kube-config file.
                    If None, searches in project root.
    
    Returns:
        KubernetesConfig with file path and server info.
    
    Raises:
        FileNotFoundError: If config file doesn't exist.
    """
    if config_file is None:
        project_root = _find_project_root()
        possible_paths = [
            project_root / "kube-config",
            project_root.parent / "kube-config",
        ]
        for path in possible_paths:
            if path.exists():
                config_file = str(path)
                break
        else:
            raise FileNotFoundError(
                f"Kubernetes config file not found. Searched: {[str(p) for p in possible_paths]}"
            )
    
    return KubernetesConfig(
        config_path=config_file,
        server="https://192.168.50.235:6443",
        context="default",
    )


def get_registry_config() -> RegistryConfig:
    """Get OCI registry configuration."""
    return RegistryConfig()


# Singleton instances for easy access
_docker_config: Optional[DockerConfig] = None
_kubernetes_config: Optional[KubernetesConfig] = None
_registry_config: Optional[RegistryConfig] = None


def get_docker_config() -> DockerConfig:
    """Get cached Docker configuration."""
    global _docker_config
    if _docker_config is None:
        _docker_config = load_docker_config()
    return _docker_config


def get_kubernetes_config() -> KubernetesConfig:
    """Get cached Kubernetes configuration."""
    global _kubernetes_config
    if _kubernetes_config is None:
        _kubernetes_config = load_kubernetes_config()
    return _kubernetes_config
