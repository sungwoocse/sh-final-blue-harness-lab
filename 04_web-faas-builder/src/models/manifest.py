"""SpinApp manifest data models with validation.

This module provides dataclasses for SpinApp Kubernetes manifests,
including resource limits validation.

Requirements: 9.1, 9.2, 9.3, 9.4, 12.1, 14.1, 14.2
"""

from dataclasses import dataclass, field
from typing import Optional
import re


# Kubernetes resource format regex pattern
# Valid formats: 100m (millicores), 128Mi (mebibytes), 1Gi (gibibytes), etc.
RESOURCE_FORMAT_PATTERN = re.compile(
    r'^[0-9]+(\.[0-9]+)?(m|Ki|Mi|Gi|Ti|Pi|Ei|k|M|G|T|P|E)?$'
)


class ResourceValidationError(ValueError):
    """Raised when a resource value has invalid format."""
    pass


def validate_resource_format(value: str, field_name: str) -> str:
    """Validate that a resource value conforms to Kubernetes resource format.
    
    Valid formats include:
    - Integer values: 100, 200
    - Millicores: 100m, 500m
    - Binary units: 128Ki, 256Mi, 1Gi, 2Ti, 1Pi, 1Ei
    - Decimal units: 1k, 1M, 1G, 1T, 1P, 1E
    
    Args:
        value: The resource value to validate
        field_name: Name of the field for error messages
        
    Returns:
        The validated value
        
    Raises:
        ResourceValidationError: If the value doesn't match valid format
    """
    if not RESOURCE_FORMAT_PATTERN.match(value):
        raise ResourceValidationError(
            f"Invalid resource format for {field_name}: '{value}'. "
            f"Expected format like '100m', '128Mi', '1Gi', etc."
        )
    return value


@dataclass
class ResourceLimits:
    """Kubernetes resource limits and requests.
    
    Represents CPU and memory limits/requests for a SpinApp deployment.
    All values must conform to Kubernetes resource format.
    
    Requirements: 9.1, 9.2, 9.3, 9.4
    """
    cpu_limit: Optional[str] = None
    memory_limit: Optional[str] = None
    cpu_request: Optional[str] = None
    memory_request: Optional[str] = None
    
    def __post_init__(self):
        """Validate resource formats after initialization."""
        if self.cpu_limit is not None:
            validate_resource_format(self.cpu_limit, "cpu_limit")
        if self.memory_limit is not None:
            validate_resource_format(self.memory_limit, "memory_limit")
        if self.cpu_request is not None:
            validate_resource_format(self.cpu_request, "cpu_request")
        if self.memory_request is not None:
            validate_resource_format(self.memory_request, "memory_request")
    
    def has_limits(self) -> bool:
        """Check if any limits are set."""
        return self.cpu_limit is not None or self.memory_limit is not None
    
    def has_requests(self) -> bool:
        """Check if any requests are set."""
        return self.cpu_request is not None or self.memory_request is not None
    
    def has_any(self) -> bool:
        """Check if any resource values are set."""
        return self.has_limits() or self.has_requests()


class AutoscalingValidationError(ValueError):
    """Raised when autoscaling configuration is invalid."""
    pass


@dataclass
class Toleration:
    """Kubernetes toleration for pod scheduling.
    
    Tolerations allow pods to be scheduled on nodes with matching taints.
    
    Attributes:
        key: The taint key to match
        operator: The operator (Exists or Equal)
        effect: The taint effect (NoSchedule, PreferNoSchedule, NoExecute)
        value: The taint value (optional, used with Equal operator)
        
    Requirements: 14.1
    """
    key: str
    operator: str = "Exists"
    effect: str = "NoSchedule"
    value: Optional[str] = None


@dataclass
class NodeSelectorRequirement:
    """A node selector requirement for node affinity.
    
    Attributes:
        key: The label key to match
        operator: The operator (In, NotIn, Exists, DoesNotExist, Gt, Lt)
        values: List of values to match against
    """
    key: str
    operator: str
    values: list[str] = field(default_factory=list)


@dataclass
class PreferredSchedulingTerm:
    """A preferred scheduling term for node affinity.
    
    Attributes:
        weight: Weight (1-100) for this preference
        match_expressions: List of node selector requirements
    """
    weight: int
    match_expressions: list[NodeSelectorRequirement] = field(default_factory=list)


@dataclass
class NodeAffinity:
    """Kubernetes node affinity for preferred scheduling.
    
    Defines preferred node scheduling based on node labels.
    
    Attributes:
        preferred_during_scheduling: List of preferred scheduling terms
        
    Requirements: 14.2
    """
    preferred_during_scheduling: list[PreferredSchedulingTerm] = field(default_factory=list)


def validate_autoscaling_config(enable_autoscaling: bool, replicas: Optional[int]) -> tuple[bool, Optional[str]]:
    """Validate autoscaling configuration.

    When enableAutoscaling=true, replicas is ignored and autoscaling takes priority.

    Args:
        enable_autoscaling: Whether autoscaling is enabled
        replicas: The replica count (ignored when autoscaling is enabled)

    Returns:
        Tuple of (is_valid, error_message)

    Requirements: 13.5
    """
    # enable_autoscaling takes priority over replicas - no error, just ignore replicas
    return True, None


@dataclass
class SpinAppManifest:
    """SpinApp Kubernetes custom resource manifest.
    
    Represents a SpinApp CRD for deploying Spin applications to Kubernetes.
    
    Requirements: 9.1, 9.2, 9.3, 9.4, 12.1, 13.1, 13.2, 13.5, 14.1, 14.2
    """
    name: str
    image: str
    namespace: str = "default"
    replicas: Optional[int] = None
    service_account: Optional[str] = None
    resources: ResourceLimits = field(default_factory=ResourceLimits)
    api_version: str = "core.spinkube.dev/v1alpha1"
    kind: str = "SpinApp"
    enable_autoscaling: bool = True
    use_spot: bool = True
    tolerations: list[Toleration] = field(default_factory=list)
    node_affinity: Optional[NodeAffinity] = None
    # Labels for the SpinApp metadata
    labels: dict[str, str] = field(default_factory=lambda: {
        "app.kubernetes.io/managed-by": "blue-faas",
    })
    # Pod labels for the deployed Pods (spec.podLabels)
    pod_labels: dict[str, str] = field(default_factory=lambda: {
        "faas": "true",
    })
    
    def __post_init__(self):
        """Validate manifest fields after initialization."""
        if not self.name:
            raise ValueError("SpinApp name cannot be empty")
        if not self.image:
            raise ValueError("SpinApp image cannot be empty")
        # Validate replicas only when autoscaling is disabled
        if not self.enable_autoscaling and self.replicas is not None and self.replicas < 1:
            raise ValueError("Replicas must be at least 1")
        # Validate mutual exclusion: enableAutoscaling=true and replicas are mutually exclusive
        if self.enable_autoscaling and self.replicas is not None:
            raise AutoscalingValidationError(
                "enableAutoscaling and replicas are mutually exclusive. "
                "When enableAutoscaling is true, replicas must not be specified."
            )
