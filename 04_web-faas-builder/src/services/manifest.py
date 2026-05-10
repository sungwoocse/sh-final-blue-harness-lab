"""ManifestService for SpinApp YAML serialization and deserialization.

This module provides the ManifestService class for converting SpinAppManifest
objects to/from YAML format.

Requirements: 12.1, 12.2, 12.3, 12.4, 14.1, 14.2, 14.3, 14.4, 14.5
"""

import yaml
from typing import Any

from src.models.manifest import (
    SpinAppManifest,
    ResourceLimits,
    Toleration,
    NodeAffinity,
    PreferredSchedulingTerm,
    NodeSelectorRequirement,
)


class ManifestParseError(ValueError):
    """Raised when YAML parsing fails with line number information."""
    
    def __init__(self, message: str, line: int | None = None):
        self.line = line
        if line is not None:
            super().__init__(f"Line {line}: {message}")
        else:
            super().__init__(message)


class ManifestService:
    """Service for serializing and deserializing SpinApp manifests.
    
    Provides methods to convert SpinAppManifest objects to YAML strings
    and parse YAML strings back to SpinAppManifest objects.
    
    Requirements: 12.1, 12.2, 12.3, 12.4, 14.1, 14.2, 14.3, 14.4, 14.5
    """
    
    # Default Spot toleration (key: spot, effect: NoSchedule)
    # Requirements: 14.1
    DEFAULT_SPOT_TOLERATION = Toleration(
        key="spot",
        operator="Exists",
        effect="NoSchedule",
    )
    
    # Default Spot affinity (preferring nodes with label spot=true)
    # Requirements: 14.2
    DEFAULT_SPOT_AFFINITY = NodeAffinity(
        preferred_during_scheduling=[
            PreferredSchedulingTerm(
                weight=100,
                match_expressions=[
                    NodeSelectorRequirement(
                        key="spot",
                        operator="In",
                        values=["true"],
                    )
                ],
            )
        ]
    )
    
    def to_yaml(self, manifest: SpinAppManifest) -> str:
        """Serialize SpinAppManifest to YAML with proper structure.
        
        Produces valid YAML output conforming to the SpinApp CRD schema.
        
        Args:
            manifest: The SpinAppManifest object to serialize
            
        Returns:
            YAML string representation of the manifest
            
        Requirements: 12.1, 13.3, 13.4, 14.1, 14.2, 14.3
        """
        data: dict[str, Any] = {
            "apiVersion": manifest.api_version,
            "kind": manifest.kind,
            "metadata": {
                "name": manifest.name,
                "namespace": manifest.namespace,
            },
            "spec": {
                "image": manifest.image,
                "enableAutoscaling": manifest.enable_autoscaling,
            },
        }
        
        # Add labels to metadata
        if manifest.labels:
            data["metadata"]["labels"] = manifest.labels
        
        # Add podLabels to spec (labels applied to Pods)
        if manifest.pod_labels:
            data["spec"]["podLabels"] = manifest.pod_labels
        
        # Include replicas only when enableAutoscaling is false (Requirement 13.4)
        # Omit replicas when enableAutoscaling is true (Requirement 13.3)
        if not manifest.enable_autoscaling and manifest.replicas is not None:
            data["spec"]["replicas"] = manifest.replicas
        
        # Add serviceAccountName if specified
        if manifest.service_account:
            data["spec"]["serviceAccountName"] = manifest.service_account
        
        # Add resources if any are specified
        if manifest.resources.has_any():
            resources: dict[str, dict[str, str]] = {}
            
            if manifest.resources.has_limits():
                resources["limits"] = {}
                if manifest.resources.cpu_limit:
                    resources["limits"]["cpu"] = manifest.resources.cpu_limit
                if manifest.resources.memory_limit:
                    resources["limits"]["memory"] = manifest.resources.memory_limit
            
            if manifest.resources.has_requests():
                resources["requests"] = {}
                if manifest.resources.cpu_request:
                    resources["requests"]["cpu"] = manifest.resources.cpu_request
                if manifest.resources.memory_request:
                    resources["requests"]["memory"] = manifest.resources.memory_request
            
            data["spec"]["resources"] = resources
        
        # NOTE: SpinApp CRD v1alpha1 does not support tolerations/affinity fields
        # These fields are ignored for now until SpinKube supports pod scheduling options
        # Spot instance scheduling should be handled at the SpinKube operator level
        
        return yaml.dump(data, default_flow_style=False, sort_keys=False)
    
    def _toleration_to_dict(self, toleration: Toleration) -> dict[str, Any]:
        """Convert a Toleration to a dictionary for YAML serialization."""
        result: dict[str, Any] = {
            "key": toleration.key,
            "operator": toleration.operator,
            "effect": toleration.effect,
        }
        if toleration.value is not None:
            result["value"] = toleration.value
        return result
    
    def _node_affinity_to_dict(self, affinity: NodeAffinity) -> dict[str, Any]:
        """Convert a NodeAffinity to a dictionary for YAML serialization."""
        preferred_terms = []
        for term in affinity.preferred_during_scheduling:
            match_expressions = []
            for expr in term.match_expressions:
                match_expressions.append({
                    "key": expr.key,
                    "operator": expr.operator,
                    "values": expr.values,
                })
            preferred_terms.append({
                "weight": term.weight,
                "preference": {
                    "matchExpressions": match_expressions,
                },
            })
        
        return {
            "nodeAffinity": {
                "preferredDuringSchedulingIgnoredDuringExecution": preferred_terms,
            }
        }

    def from_yaml(self, yaml_content: str) -> SpinAppManifest:
        """Parse YAML to SpinAppManifest object with error handling.
        
        Parses valid YAML and produces an equivalent SpinAppManifest object.
        Returns parsing errors with line number information for invalid YAML.
        
        Args:
            yaml_content: YAML string to parse
            
        Returns:
            SpinAppManifest object parsed from the YAML
            
        Raises:
            ManifestParseError: If YAML is invalid or missing required fields
            
        Requirements: 12.2, 12.3
        """
        try:
            data = yaml.safe_load(yaml_content)
        except yaml.YAMLError as e:
            # Extract line number from YAML error if available
            line = None
            if hasattr(e, 'problem_mark') and e.problem_mark is not None:
                line = e.problem_mark.line + 1  # YAML lines are 0-indexed
            raise ManifestParseError(f"Invalid YAML syntax: {e}", line=line)
        
        if data is None:
            raise ManifestParseError("Empty YAML content")
        
        if not isinstance(data, dict):
            raise ManifestParseError("YAML must be a mapping/dictionary")
        
        # Validate required fields
        if "metadata" not in data:
            raise ManifestParseError("Missing required field: metadata")
        
        metadata = data.get("metadata", {})
        if not isinstance(metadata, dict):
            raise ManifestParseError("metadata must be a mapping")
        
        if "name" not in metadata:
            raise ManifestParseError("Missing required field: metadata.name")
        
        if "spec" not in data:
            raise ManifestParseError("Missing required field: spec")
        
        spec = data.get("spec", {})
        if not isinstance(spec, dict):
            raise ManifestParseError("spec must be a mapping")
        
        if "image" not in spec:
            raise ManifestParseError("Missing required field: spec.image")
        
        # Parse resource limits
        resources = ResourceLimits()
        if "resources" in spec:
            res_data = spec["resources"]
            if not isinstance(res_data, dict):
                raise ManifestParseError("spec.resources must be a mapping")
            
            limits = res_data.get("limits", {})
            requests = res_data.get("requests", {})
            
            try:
                resources = ResourceLimits(
                    cpu_limit=limits.get("cpu") if isinstance(limits, dict) else None,
                    memory_limit=limits.get("memory") if isinstance(limits, dict) else None,
                    cpu_request=requests.get("cpu") if isinstance(requests, dict) else None,
                    memory_request=requests.get("memory") if isinstance(requests, dict) else None,
                )
            except ValueError as e:
                raise ManifestParseError(f"Invalid resource value: {e}")
        
        # Build the manifest object
        # Parse enableAutoscaling with default true (Requirement 13.1)
        enable_autoscaling = spec.get("enableAutoscaling", True)
        # Parse optional replicas field
        replicas = spec.get("replicas")
        
        # Parse tolerations (Requirement 14.1)
        tolerations: list[Toleration] = []
        if "tolerations" in spec:
            tolerations_data = spec["tolerations"]
            if not isinstance(tolerations_data, list):
                raise ManifestParseError("spec.tolerations must be a list")
            for t in tolerations_data:
                if not isinstance(t, dict):
                    raise ManifestParseError("Each toleration must be a mapping")
                tolerations.append(Toleration(
                    key=t.get("key", ""),
                    operator=t.get("operator", "Exists"),
                    effect=t.get("effect", "NoSchedule"),
                    value=t.get("value"),
                ))
        
        # Parse node affinity (Requirement 14.2)
        node_affinity: NodeAffinity | None = None
        if "affinity" in spec:
            affinity_data = spec["affinity"]
            if isinstance(affinity_data, dict) and "nodeAffinity" in affinity_data:
                node_affinity_data = affinity_data["nodeAffinity"]
                if isinstance(node_affinity_data, dict):
                    preferred_terms: list[PreferredSchedulingTerm] = []
                    preferred_data = node_affinity_data.get(
                        "preferredDuringSchedulingIgnoredDuringExecution", []
                    )
                    if isinstance(preferred_data, list):
                        for term_data in preferred_data:
                            if isinstance(term_data, dict):
                                match_expressions: list[NodeSelectorRequirement] = []
                                pref = term_data.get("preference", {})
                                if isinstance(pref, dict):
                                    exprs = pref.get("matchExpressions", [])
                                    if isinstance(exprs, list):
                                        for expr in exprs:
                                            if isinstance(expr, dict):
                                                match_expressions.append(
                                                    NodeSelectorRequirement(
                                                        key=expr.get("key", ""),
                                                        operator=expr.get("operator", "In"),
                                                        values=expr.get("values", []),
                                                    )
                                                )
                                preferred_terms.append(
                                    PreferredSchedulingTerm(
                                        weight=term_data.get("weight", 1),
                                        match_expressions=match_expressions,
                                    )
                                )
                    if preferred_terms:
                        node_affinity = NodeAffinity(
                            preferred_during_scheduling=preferred_terms
                        )
        
        # Determine use_spot based on presence of default Spot toleration
        use_spot = self._has_default_spot_toleration(tolerations)
        
        # Filter out default Spot toleration from custom tolerations
        custom_tolerations = [
            t for t in tolerations
            if not (t.key == "spot" and t.operator == "Exists" and t.effect == "NoSchedule")
        ]
        
        # Parse labels from metadata
        labels = metadata.get("labels", {
            "app.kubernetes.io/managed-by": "blue-faas",
        })
        
        # Parse podLabels from spec
        pod_labels = spec.get("podLabels", {
            "faas": "true",
        })
        
        try:
            return SpinAppManifest(
                api_version=data.get("apiVersion", "core.spinkube.dev/v1alpha1"),
                kind=data.get("kind", "SpinApp"),
                name=metadata["name"],
                namespace=metadata.get("namespace", "default"),
                image=spec["image"],
                replicas=replicas,
                service_account=spec.get("serviceAccountName"),
                resources=resources,
                enable_autoscaling=enable_autoscaling,
                use_spot=use_spot,
                tolerations=custom_tolerations,
                node_affinity=node_affinity if not use_spot else None,
                labels=labels,
                pod_labels=pod_labels,
            )
        except ValueError as e:
            raise ManifestParseError(f"Invalid manifest data: {e}")
    
    def _has_default_spot_toleration(self, tolerations: list[Toleration]) -> bool:
        """Check if the default Spot toleration is present in the list."""
        for t in tolerations:
            if (t.key == "spot" and 
                t.operator == "Exists" and 
                t.effect == "NoSchedule"):
                return True
        return False
