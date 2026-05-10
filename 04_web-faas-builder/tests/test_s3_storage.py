"""Property-based tests for S3 Storage Service.

This module tests:
- S3 path generation consistency (Property 25)

**Feature: spin-k8s-deployment, Property 25: S3 Path Generation Consistency**
**Validates: Requirements 15.1, 15.2**
"""

from hypothesis import given, strategies as st, settings

from src.services.s3_storage import S3StorageService


# Strategy for valid workspace IDs (alphanumeric with hyphens)
workspace_id = st.text(
    alphabet=st.sampled_from("abcdefghijklmnopqrstuvwxyz0123456789-"),
    min_size=1,
    max_size=50,
).filter(lambda s: s[0].isalnum() and s[-1].isalnum() and "--" not in s)

# Strategy for valid task IDs (UUID-like format)
task_id = st.uuids().map(str)

# Strategy for valid file names
filename = st.builds(
    lambda name, ext: f"{name}.{ext}",
    name=st.text(
        alphabet=st.sampled_from("abcdefghijklmnopqrstuvwxyz0123456789_-"),
        min_size=1,
        max_size=30,
    ).filter(lambda s: s[0].isalnum()),
    ext=st.sampled_from(["py", "wasm", "toml", "txt", "zip"]),
)

# Strategy for valid bucket names
bucket_name = st.text(
    alphabet=st.sampled_from("abcdefghijklmnopqrstuvwxyz0123456789-"),
    min_size=3,
    max_size=63,
).filter(lambda s: s[0].isalnum() and s[-1].isalnum() and "--" not in s)


class TestS3PathGeneration:
    """Property tests for S3 path generation.
    
    **Feature: spin-k8s-deployment, Property 25: S3 Path Generation Consistency**
    **Validates: Requirements 15.1, 15.2**
    """

    @given(
        bucket=bucket_name,
        ws_id=workspace_id,
        t_id=task_id,
        fname=filename,
    )
    @settings(max_examples=100)
    def test_source_path_format(
        self,
        bucket: str,
        ws_id: str,
        t_id: str,
        fname: str,
    ):
        """
        **Feature: spin-k8s-deployment, Property 25: S3 Path Generation Consistency**
        **Validates: Requirements 15.1**
        
        For any workspace_id and task_id, the generated S3 source path should
        follow the format s3://{bucket}/build-sources/{workspace_id}/{task_id}/{filename}
        """
        service = S3StorageService(bucket_name=bucket)
        
        path = service.get_source_path(ws_id, t_id, fname)
        
        # Verify path format
        expected_path = f"s3://{bucket}/build-sources/{ws_id}/{t_id}/{fname}"
        assert path == expected_path, f"Expected {expected_path}, got {path}"
        
        # Verify path starts with s3://
        assert path.startswith("s3://"), f"Path should start with s3://, got {path}"
        
        # Verify path contains build-sources prefix
        assert "/build-sources/" in path, f"Path should contain /build-sources/, got {path}"
        
        # Verify workspace_id is in path
        assert f"/{ws_id}/" in path, f"Path should contain workspace_id {ws_id}, got {path}"
        
        # Verify task_id is in path
        assert f"/{t_id}/" in path, f"Path should contain task_id {t_id}, got {path}"
        
        # Verify filename is at the end
        assert path.endswith(f"/{fname}"), f"Path should end with filename {fname}, got {path}"


    @given(
        bucket=bucket_name,
        ws_id=workspace_id,
        t_id=task_id,
    )
    @settings(max_examples=100)
    def test_source_prefix_format(
        self,
        bucket: str,
        ws_id: str,
        t_id: str,
    ):
        """
        **Feature: spin-k8s-deployment, Property 25: S3 Path Generation Consistency**
        **Validates: Requirements 15.1**
        
        For any workspace_id and task_id, the generated S3 source prefix should
        follow the format s3://{bucket}/build-sources/{workspace_id}/{task_id}/
        """
        service = S3StorageService(bucket_name=bucket)
        
        prefix = service.get_source_prefix(ws_id, t_id)
        
        # Verify prefix format
        expected_prefix = f"s3://{bucket}/build-sources/{ws_id}/{t_id}/"
        assert prefix == expected_prefix, f"Expected {expected_prefix}, got {prefix}"
        
        # Verify prefix ends with /
        assert prefix.endswith("/"), f"Prefix should end with /, got {prefix}"

    @given(
        bucket=bucket_name,
        t_id=task_id,
        fname=filename,
    )
    @settings(max_examples=100)
    def test_artifact_path_format(
        self,
        bucket: str,
        t_id: str,
        fname: str,
    ):
        """
        **Feature: spin-k8s-deployment, Property 25: S3 Path Generation Consistency**
        **Validates: Requirements 15.2**
        
        For any task_id, the generated S3 artifact path should
        follow the format s3://{bucket}/build-artifacts/{task_id}/{filename}
        """
        service = S3StorageService(bucket_name=bucket)
        
        path = service.get_artifact_path(t_id, fname)
        
        # Verify path format
        expected_path = f"s3://{bucket}/build-artifacts/{t_id}/{fname}"
        assert path == expected_path, f"Expected {expected_path}, got {path}"
        
        # Verify path starts with s3://
        assert path.startswith("s3://"), f"Path should start with s3://, got {path}"
        
        # Verify path contains build-artifacts prefix
        assert "/build-artifacts/" in path, f"Path should contain /build-artifacts/, got {path}"
        
        # Verify task_id is in path
        assert f"/{t_id}/" in path, f"Path should contain task_id {t_id}, got {path}"
        
        # Verify filename is at the end
        assert path.endswith(f"/{fname}"), f"Path should end with filename {fname}, got {path}"

    @given(
        bucket=bucket_name,
        t_id=task_id,
    )
    @settings(max_examples=100)
    def test_artifact_prefix_format(
        self,
        bucket: str,
        t_id: str,
    ):
        """
        **Feature: spin-k8s-deployment, Property 25: S3 Path Generation Consistency**
        **Validates: Requirements 15.2**
        
        For any task_id, the generated S3 artifact prefix should
        follow the format s3://{bucket}/build-artifacts/{task_id}/
        """
        service = S3StorageService(bucket_name=bucket)
        
        prefix = service.get_artifact_prefix(t_id)
        
        # Verify prefix format
        expected_prefix = f"s3://{bucket}/build-artifacts/{t_id}/"
        assert prefix == expected_prefix, f"Expected {expected_prefix}, got {prefix}"
        
        # Verify prefix ends with /
        assert prefix.endswith("/"), f"Prefix should end with /, got {prefix}"

    @given(
        bucket=bucket_name,
        ws_id=workspace_id,
        t_id=task_id,
        fname=filename,
    )
    @settings(max_examples=100)
    def test_source_and_artifact_paths_are_distinct(
        self,
        bucket: str,
        ws_id: str,
        t_id: str,
        fname: str,
    ):
        """
        **Feature: spin-k8s-deployment, Property 25: S3 Path Generation Consistency**
        **Validates: Requirements 15.1, 15.2**
        
        For any workspace_id, task_id, and filename, the source path and
        artifact path should be distinct (different prefixes).
        """
        service = S3StorageService(bucket_name=bucket)
        
        source_path = service.get_source_path(ws_id, t_id, fname)
        artifact_path = service.get_artifact_path(t_id, fname)
        
        # Paths should be different
        assert source_path != artifact_path, \
            f"Source and artifact paths should be different: {source_path}"
        
        # Source path should contain build-sources
        assert "build-sources" in source_path
        assert "build-artifacts" not in source_path
        
        # Artifact path should contain build-artifacts
        assert "build-artifacts" in artifact_path
        assert "build-sources" not in artifact_path

    @given(
        bucket=bucket_name,
        ws_id=workspace_id,
        t_id=task_id,
        fname=filename,
    )
    @settings(max_examples=100)
    def test_path_generation_is_deterministic(
        self,
        bucket: str,
        ws_id: str,
        t_id: str,
        fname: str,
    ):
        """
        **Feature: spin-k8s-deployment, Property 25: S3 Path Generation Consistency**
        **Validates: Requirements 15.1, 15.2**
        
        For any inputs, calling path generation multiple times should
        always produce the same result.
        """
        service = S3StorageService(bucket_name=bucket)
        
        # Generate paths multiple times
        source_path1 = service.get_source_path(ws_id, t_id, fname)
        source_path2 = service.get_source_path(ws_id, t_id, fname)
        source_path3 = service.get_source_path(ws_id, t_id, fname)
        
        artifact_path1 = service.get_artifact_path(t_id, fname)
        artifact_path2 = service.get_artifact_path(t_id, fname)
        artifact_path3 = service.get_artifact_path(t_id, fname)
        
        # All calls should produce identical results
        assert source_path1 == source_path2 == source_path3, \
            f"Source paths should be identical: {source_path1}, {source_path2}, {source_path3}"
        assert artifact_path1 == artifact_path2 == artifact_path3, \
            f"Artifact paths should be identical: {artifact_path1}, {artifact_path2}, {artifact_path3}"

    @given(
        bucket=bucket_name,
        ws_id=workspace_id,
        t_id=task_id,
    )
    @settings(max_examples=100)
    def test_bucket_name_in_path(
        self,
        bucket: str,
        ws_id: str,
        t_id: str,
    ):
        """
        **Feature: spin-k8s-deployment, Property 25: S3 Path Generation Consistency**
        **Validates: Requirements 15.1, 15.2**
        
        For any bucket name, the generated paths should contain the
        correct bucket name.
        """
        service = S3StorageService(bucket_name=bucket)
        
        source_prefix = service.get_source_prefix(ws_id, t_id)
        artifact_prefix = service.get_artifact_prefix(t_id)
        
        # Both paths should contain the bucket name
        assert f"s3://{bucket}/" in source_prefix, \
            f"Source prefix should contain bucket {bucket}: {source_prefix}"
        assert f"s3://{bucket}/" in artifact_prefix, \
            f"Artifact prefix should contain bucket {bucket}: {artifact_prefix}"
