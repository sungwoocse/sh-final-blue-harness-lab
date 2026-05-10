"""S3 Storage Service for storing source code and build artifacts.

This module provides functionality to:
- Upload source code to S3 at path: s3://{bucket}/build-sources/{workspace_id}/{task_id}/
- Upload build artifacts (WASM) to S3 at path: s3://{bucket}/build-artifacts/{task_id}/

**Feature: spin-k8s-deployment**
**Validates: Requirements 15.1, 15.2, 15.3, 15.4**
"""

import os
from pathlib import Path
from dataclasses import dataclass
from typing import Optional

import boto3
from botocore.exceptions import ClientError, BotoCoreError


@dataclass
class S3UploadResult:
    """Result of an S3 upload operation."""
    success: bool
    s3_path: Optional[str] = None
    error: Optional[str] = None


@dataclass
class S3DownloadResult:
    """Result of an S3 download operation."""
    success: bool
    local_path: Optional[Path] = None
    error: Optional[str] = None


class S3StorageService:
    """Service for storing build artifacts in S3.
    
    Configuration is read from environment variables:
    - S3_BUCKET_NAME: The S3 bucket name for storing files
    - AWS_REGION: AWS region (defaults to ap-northeast-2)
    """
    
    # Default bucket name (can be overridden via environment variable)
    DEFAULT_BUCKET_NAME = "sfbank-blue-functions-code-bucket"
    DEFAULT_REGION = "ap-northeast-2"
    
    # Path prefixes for S3 storage
    SOURCE_PREFIX = "build-sources"
    ARTIFACT_PREFIX = "build-artifacts"
    
    def __init__(
        self,
        bucket_name: Optional[str] = None,
        region: Optional[str] = None,
    ):
        """Initialize S3 Storage Service.
        
        Args:
            bucket_name: S3 bucket name. If not provided, reads from
                        S3_BUCKET_NAME environment variable or uses default.
            region: AWS region. If not provided, reads from AWS_REGION
                   environment variable or uses default.
        """
        self.bucket_name = (
            bucket_name
            or os.environ.get("S3_BUCKET_NAME")
            or self.DEFAULT_BUCKET_NAME
        )
        self.region = (
            region
            or os.environ.get("AWS_REGION")
            or self.DEFAULT_REGION
        )
        self._client: Optional[boto3.client] = None

    @property
    def client(self):
        """Lazy initialization of boto3 S3 client."""
        if self._client is None:
            self._client = boto3.client("s3", region_name=self.region)
        return self._client
    
    def get_source_path(
        self,
        workspace_id: str,
        task_id: str,
        filename: str,
    ) -> str:
        """Generate S3 path for source code.
        
        Args:
            workspace_id: The workspace identifier
            task_id: The task identifier
            filename: The source file name
            
        Returns:
            S3 URI in format: s3://{bucket}/build-sources/{workspace_id}/{task_id}/{filename}
        """
        return f"s3://{self.bucket_name}/{self.SOURCE_PREFIX}/{workspace_id}/{task_id}/{filename}"
    
    def get_source_prefix(
        self,
        workspace_id: str,
        task_id: str,
    ) -> str:
        """Generate S3 prefix for source code directory.
        
        Args:
            workspace_id: The workspace identifier
            task_id: The task identifier
            
        Returns:
            S3 URI in format: s3://{bucket}/build-sources/{workspace_id}/{task_id}/
        """
        return f"s3://{self.bucket_name}/{self.SOURCE_PREFIX}/{workspace_id}/{task_id}/"
    
    def get_artifact_path(
        self,
        task_id: str,
        filename: str,
    ) -> str:
        """Generate S3 path for build artifact.
        
        Args:
            task_id: The task identifier
            filename: The artifact file name (e.g., app.wasm)
            
        Returns:
            S3 URI in format: s3://{bucket}/build-artifacts/{task_id}/{filename}
        """
        return f"s3://{self.bucket_name}/{self.ARTIFACT_PREFIX}/{task_id}/{filename}"
    
    def get_artifact_prefix(
        self,
        task_id: str,
    ) -> str:
        """Generate S3 prefix for build artifacts directory.
        
        Args:
            task_id: The task identifier
            
        Returns:
            S3 URI in format: s3://{bucket}/build-artifacts/{task_id}/
        """
        return f"s3://{self.bucket_name}/{self.ARTIFACT_PREFIX}/{task_id}/"
    
    def upload_source(
        self,
        workspace_id: str,
        task_id: str,
        file_path: Path,
    ) -> S3UploadResult:
        """Upload source code file to S3.
        
        Path: s3://{bucket}/build-sources/{workspace_id}/{task_id}/{filename}
        
        Args:
            workspace_id: The workspace identifier
            task_id: The task identifier
            file_path: Local path to the source file
            
        Returns:
            S3UploadResult with success status and S3 path or error message
        """
        s3_key = f"{self.SOURCE_PREFIX}/{workspace_id}/{task_id}/{file_path.name}"
        return self._upload_file(file_path, s3_key)
    
    def upload_source_directory(
        self,
        workspace_id: str,
        task_id: str,
        directory_path: Path,
    ) -> S3UploadResult:
        """Upload all files in a directory to S3.
        
        Path: s3://{bucket}/build-sources/{workspace_id}/{task_id}/
        
        Args:
            workspace_id: The workspace identifier
            task_id: The task identifier
            directory_path: Local path to the source directory
            
        Returns:
            S3UploadResult with success status and S3 prefix or error message
        """
        try:
            if not directory_path.is_dir():
                return S3UploadResult(
                    success=False,
                    error=f"Path is not a directory: {directory_path}"
                )
            
            # Upload all files in the directory
            for file_path in directory_path.rglob("*"):
                if file_path.is_file():
                    # Calculate relative path from directory root
                    relative_path = file_path.relative_to(directory_path)
                    s3_key = f"{self.SOURCE_PREFIX}/{workspace_id}/{task_id}/{relative_path}"
                    
                    result = self._upload_file(file_path, s3_key)
                    if not result.success:
                        return result
            
            s3_prefix = self.get_source_prefix(workspace_id, task_id)
            return S3UploadResult(success=True, s3_path=s3_prefix)
            
        except Exception as e:
            return S3UploadResult(success=False, error=str(e))
    
    def upload_artifact(
        self,
        task_id: str,
        file_path: Path,
    ) -> S3UploadResult:
        """Upload build artifact (WASM) to S3.
        
        Path: s3://{bucket}/build-artifacts/{task_id}/{filename}
        
        Args:
            task_id: The task identifier
            file_path: Local path to the artifact file (e.g., app.wasm)
            
        Returns:
            S3UploadResult with success status and S3 path or error message
        """
        s3_key = f"{self.ARTIFACT_PREFIX}/{task_id}/{file_path.name}"
        return self._upload_file(file_path, s3_key)
    
    def _upload_file(
        self,
        file_path: Path,
        s3_key: str,
    ) -> S3UploadResult:
        """Internal method to upload a file to S3.
        
        Args:
            file_path: Local path to the file
            s3_key: S3 object key
            
        Returns:
            S3UploadResult with success status and S3 path or error message
        """
        try:
            if not file_path.exists():
                return S3UploadResult(
                    success=False,
                    error=f"File not found: {file_path}"
                )
            
            self.client.upload_file(
                str(file_path),
                self.bucket_name,
                s3_key,
            )
            
            s3_path = f"s3://{self.bucket_name}/{s3_key}"
            return S3UploadResult(success=True, s3_path=s3_path)
            
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "Unknown")
            error_msg = e.response.get("Error", {}).get("Message", str(e))
            return S3UploadResult(
                success=False,
                error=f"S3 ClientError ({error_code}): {error_msg}"
            )
        except BotoCoreError as e:
            return S3UploadResult(
                success=False,
                error=f"S3 BotoCoreError: {str(e)}"
            )
        except Exception as e:
            return S3UploadResult(
                success=False,
                error=f"Unexpected error uploading to S3: {str(e)}"
            )

    def download_source_directory(
        self,
        s3_path: str,
        local_dir: Path,
    ) -> S3DownloadResult:
        """Download all files from S3 source path to local directory.

        Args:
            s3_path: S3 URI (e.g., s3://bucket/build-sources/workspace/task/)
            local_dir: Local directory to download files to

        Returns:
            S3DownloadResult with success status and local path or error message
        """
        try:
            # Parse S3 URI
            if not s3_path.startswith("s3://"):
                return S3DownloadResult(
                    success=False,
                    error=f"Invalid S3 path: {s3_path}"
                )

            # Remove s3:// prefix and split bucket/key
            path_without_prefix = s3_path[5:]
            parts = path_without_prefix.split("/", 1)
            bucket = parts[0]
            prefix = parts[1] if len(parts) > 1 else ""

            # Remove trailing slash from prefix
            prefix = prefix.rstrip("/")

            # Create local directory if not exists
            local_dir.mkdir(parents=True, exist_ok=True)

            # List all objects with the prefix
            paginator = self.client.get_paginator("list_objects_v2")
            pages = paginator.paginate(Bucket=bucket, Prefix=prefix)

            downloaded_count = 0
            for page in pages:
                if "Contents" not in page:
                    continue

                for obj in page["Contents"]:
                    s3_key = obj["Key"]
                    # Get relative path from prefix
                    relative_path = s3_key[len(prefix):].lstrip("/")
                    if not relative_path:
                        continue

                    local_file_path = local_dir / relative_path

                    # Create parent directories if needed
                    local_file_path.parent.mkdir(parents=True, exist_ok=True)

                    # Download the file
                    self.client.download_file(bucket, s3_key, str(local_file_path))
                    downloaded_count += 1

            if downloaded_count == 0:
                return S3DownloadResult(
                    success=False,
                    error=f"No files found at S3 path: {s3_path}"
                )

            return S3DownloadResult(success=True, local_path=local_dir)

        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "Unknown")
            error_msg = e.response.get("Error", {}).get("Message", str(e))
            return S3DownloadResult(
                success=False,
                error=f"S3 ClientError ({error_code}): {error_msg}"
            )
        except BotoCoreError as e:
            return S3DownloadResult(
                success=False,
                error=f"S3 BotoCoreError: {str(e)}"
            )
        except Exception as e:
            return S3DownloadResult(
                success=False,
                error=f"Unexpected error downloading from S3: {str(e)}"
            )
