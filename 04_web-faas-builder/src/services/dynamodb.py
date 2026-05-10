"""DynamoDB Service for persisting build task data.

This module provides functionality to:
- Store build tasks in DynamoDB table sfbank-blue-FaaSData
- Update task status as build progresses
- Query tasks by workspace_id and task_id
- List all tasks for a workspace

**Feature: spin-k8s-deployment**
**Validates: Requirements 17.1, 17.2, 17.3, 17.4, 17.5, 17.6, 17.7, 17.8**
"""

import os
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional

import boto3
from botocore.exceptions import ClientError, BotoCoreError


class BuildStatus(Enum):
    """Build task status enum for DynamoDB.
    
    States follow the build lifecycle:
    - PENDING: Task created, waiting to start
    - BUILDING: Build in progress (spin build)
    - PUSHING: Push in progress (spin registry push)
    - DONE: Task completed successfully
    - FAILED: Task failed at any stage
    """
    PENDING = "PENDING"
    BUILDING = "BUILDING"
    PUSHING = "PUSHING"
    DONE = "DONE"
    FAILED = "FAILED"


@dataclass
class BuildTaskItem:
    """DynamoDB item for build task.
    
    Attributes:
        workspace_id: The workspace identifier
        task_id: The task identifier (UUIDv4)
        app_name: Application name
        status: Current build status
        source_code_path: S3 path to source code
        created_at: Task creation timestamp
        updated_at: Last update timestamp
        wasm_path: S3 path to WASM artifact (set after build success)
        image_url: ECR image URI (set after push success)
        error_message: Error details (set on failure)
    """
    workspace_id: str
    task_id: str
    app_name: str
    status: BuildStatus
    source_code_path: str
    created_at: datetime
    updated_at: datetime
    wasm_path: Optional[str] = None
    image_url: Optional[str] = None
    error_message: Optional[str] = None

    @property
    def pk(self) -> str:
        """Generate DynamoDB Partition Key.

        Format: WS#{workspace_id}
        """
        return f"WS#{self.workspace_id}"

    @property
    def sk(self) -> str:
        """Generate DynamoDB Sort Key.

        Format: BUILD#{task_id}
        """
        return f"BUILD#{self.task_id}"
    
    def to_dynamodb_item(self) -> dict:
        """Convert to DynamoDB item format.

        Returns:
            Dictionary with DynamoDB attribute value format.
        """
        item = {
            "PK": {"S": self.pk},
            "SK": {"S": self.sk},
            "Type": {"S": "BuildTask"},
            "task_id": {"S": self.task_id},
            "workspace_id": {"S": self.workspace_id},
            "app_name": {"S": self.app_name},
            "status": {"S": self.status.value},
            "source_code_path": {"S": self.source_code_path},
            "created_at": {"S": self.created_at.isoformat()},
            "updated_at": {"S": self.updated_at.isoformat()},
        }
        if self.wasm_path:
            item["wasm_path"] = {"S": self.wasm_path}
        if self.image_url:
            item["image_url"] = {"S": self.image_url}
        if self.error_message:
            item["error_message"] = {"S": self.error_message}
        return item
    
    @classmethod
    def from_dynamodb_item(cls, item: dict) -> "BuildTaskItem":
        """Create BuildTaskItem from DynamoDB item format.

        Supports both formats:
        - This API's format: ws#, build#, PascalCase fields
        - Core service format: WS#, BUILD#, snake_case fields

        Args:
            item: DynamoDB item with attribute value format.

        Returns:
            BuildTaskItem instance.
        """
        pk = item["PK"]["S"]
        sk = item["SK"]["S"]

        # Support both ws# and WS# prefixes
        workspace_id = pk.replace("ws#", "", 1).replace("WS#", "", 1)
        # Support both build# and BUILD# prefixes
        task_id = sk.replace("build#", "", 1).replace("BUILD#", "", 1)

        # Helper to get field value supporting both PascalCase and snake_case
        def get_field(pascal: str, snake: str) -> Optional[str]:
            if pascal in item:
                return item[pascal].get("S")
            if snake in item:
                return item[snake].get("S")
            return None

        # Get status - support both uppercase and mixed case
        # Map core-service status values to this API's enum
        status_str = get_field("Status", "status") or "PENDING"
        status_mapping = {
            "COMPLETED": "DONE",
            "SUCCESS": "DONE",
            "RUNNING": "BUILDING",
            "IN_PROGRESS": "BUILDING",
        }
        normalized_status = status_str.upper()
        mapped_status = status_mapping.get(normalized_status, normalized_status)
        try:
            status = BuildStatus(mapped_status)
        except ValueError:
            status = BuildStatus.PENDING

        # Parse timestamps
        created_str = get_field("CreatedAt", "created_at") or datetime.utcnow().isoformat()
        updated_str = get_field("UpdatedAt", "updated_at") or datetime.utcnow().isoformat()

        return cls(
            workspace_id=workspace_id,
            task_id=task_id,
            app_name=get_field("AppName", "app_name") or "unknown",
            status=status,
            source_code_path=get_field("SourceCodePath", "source_code_path") or "",
            created_at=datetime.fromisoformat(created_str),
            updated_at=datetime.fromisoformat(updated_str),
            wasm_path=get_field("WasmPath", "wasm_path"),
            image_url=get_field("ImageUrl", "image_url"),
            error_message=get_field("ErrorMessage", "error_message"),
        )
    
    @staticmethod
    def generate_pk(workspace_id: str) -> str:
        """Generate PK from workspace_id.

        Args:
            workspace_id: The workspace identifier.

        Returns:
            PK in format WS#{workspace_id}
        """
        return f"WS#{workspace_id}"

    @staticmethod
    def generate_sk(task_id: str) -> str:
        """Generate SK from task_id.

        Args:
            task_id: The task identifier.

        Returns:
            SK in format BUILD#{task_id}
        """
        return f"BUILD#{task_id}"



class DynamoDBService:
    """Service for persisting build tasks to DynamoDB.
    
    Configuration is read from environment variables:
    - DYNAMODB_TABLE_NAME: The DynamoDB table name (defaults to sfbank-blue-FaaSData)
    - AWS_REGION: AWS region (defaults to ap-northeast-2)
    
    **Feature: spin-k8s-deployment**
    **Validates: Requirements 17.1, 17.2, 17.3, 17.4, 17.5, 17.6, 17.7, 17.8**
    """
    
    # Default table name as specified in requirements
    DEFAULT_TABLE_NAME = "sfbank-blue-FaaSData"
    DEFAULT_REGION = "ap-northeast-2"
    
    def __init__(
        self,
        table_name: Optional[str] = None,
        region: Optional[str] = None,
    ):
        """Initialize DynamoDB Service.
        
        Args:
            table_name: DynamoDB table name. If not provided, reads from
                       DYNAMODB_TABLE_NAME environment variable or uses default.
            region: AWS region. If not provided, reads from AWS_REGION
                   environment variable or uses default.
        """
        self.table_name = (
            table_name
            or os.environ.get("DYNAMODB_TABLE_NAME")
            or self.DEFAULT_TABLE_NAME
        )
        self.region = (
            region
            or os.environ.get("AWS_REGION")
            or self.DEFAULT_REGION
        )
        self._client: Optional[boto3.client] = None
    
    @property
    def client(self):
        """Lazy initialization of boto3 DynamoDB client."""
        if self._client is None:
            self._client = boto3.client("dynamodb", region_name=self.region)
        return self._client

    
    def create_task(self, item: BuildTaskItem) -> bool:
        """Create a new build task in DynamoDB.
        
        Stores the task with PK, SK, Type, AppName, Status, SourceCodePath,
        CreatedAt, and UpdatedAt fields.
        
        Args:
            item: BuildTaskItem to store.
            
        Returns:
            True if successful, False otherwise.
            
        **Validates: Requirements 17.1, 17.2**
        """
        try:
            self.client.put_item(
                TableName=self.table_name,
                Item=item.to_dynamodb_item()
            )
            return True
        except (ClientError, BotoCoreError):
            return False
        except Exception:
            return False

    
    def update_status(
        self,
        workspace_id: str,
        task_id: str,
        status: BuildStatus,
        wasm_path: Optional[str] = None,
        image_url: Optional[str] = None,
        error_message: Optional[str] = None,
    ) -> bool:
        """Update build task status in DynamoDB.

        Updates status and updated_at fields. Optionally updates wasm_path,
        image_url, and error_message fields.

        Args:
            workspace_id: The workspace identifier.
            task_id: The task identifier.
            status: New build status.
            wasm_path: S3 path to WASM artifact (optional).
            image_url: ECR image URI (optional).
            error_message: Error details (optional).

        Returns:
            True if successful, False otherwise.

        **Validates: Requirements 17.3, 17.4, 17.5, 17.6**
        """
        update_expr = "SET #status = :status, updated_at = :updated_at"
        expr_names = {"#status": "status"}
        expr_values = {
            ":status": {"S": status.value},
            ":updated_at": {"S": datetime.utcnow().isoformat()},
        }

        if wasm_path is not None:
            update_expr += ", wasm_path = :wasm_path"
            expr_values[":wasm_path"] = {"S": wasm_path}
        if image_url is not None:
            update_expr += ", image_url = :image_url"
            expr_values[":image_url"] = {"S": image_url}
        if error_message is not None:
            update_expr += ", error_message = :error_message"
            expr_values[":error_message"] = {"S": error_message}

        try:
            self.client.update_item(
                TableName=self.table_name,
                Key={
                    "PK": {"S": BuildTaskItem.generate_pk(workspace_id)},
                    "SK": {"S": BuildTaskItem.generate_sk(task_id)},
                },
                UpdateExpression=update_expr,
                ExpressionAttributeNames=expr_names,
                ExpressionAttributeValues=expr_values,
            )
            return True
        except (ClientError, BotoCoreError):
            return False
        except Exception:
            return False

    
    def get_task(
        self,
        workspace_id: str,
        task_id: str,
    ) -> Optional[BuildTaskItem]:
        """Get a build task from DynamoDB.

        Retrieves task by workspace_id and task_id using PK and SK.
        Supports both lowercase (ws#, build#) and uppercase (WS#, BUILD#) formats.

        Args:
            workspace_id: The workspace identifier.
            task_id: The task identifier.

        Returns:
            BuildTaskItem if found, None otherwise.

        **Validates: Requirements 17.7**
        """
        # Try lowercase format first (this API's format)
        pk_formats = [f"ws#{workspace_id}", f"WS#{workspace_id}"]
        sk_formats = [f"build#{task_id}", f"BUILD#{task_id}"]

        for pk in pk_formats:
            for sk in sk_formats:
                try:
                    response = self.client.get_item(
                        TableName=self.table_name,
                        Key={
                            "PK": {"S": pk},
                            "SK": {"S": sk},
                        }
                    )
                    if "Item" in response:
                        return BuildTaskItem.from_dynamodb_item(response["Item"])
                except (ClientError, BotoCoreError):
                    continue
                except Exception:
                    continue
        return None

    
    def list_tasks(self, workspace_id: str) -> list[BuildTaskItem]:
        """List all build tasks for a workspace.

        Queries DynamoDB using PK and SK prefix to retrieve all build tasks
        for the specified workspace. Supports both lowercase and uppercase formats.

        Args:
            workspace_id: The workspace identifier.

        Returns:
            List of BuildTaskItem objects. Empty list if none found or on error.

        **Validates: Requirements 17.8**
        """
        all_items = []

        # Query both lowercase and uppercase PK/SK formats
        pk_formats = [f"ws#{workspace_id}", f"WS#{workspace_id}"]
        sk_prefixes = ["build#", "BUILD#"]

        for pk in pk_formats:
            for sk_prefix in sk_prefixes:
                try:
                    response = self.client.query(
                        TableName=self.table_name,
                        KeyConditionExpression="PK = :pk AND begins_with(SK, :sk_prefix)",
                        ExpressionAttributeValues={
                            ":pk": {"S": pk},
                            ":sk_prefix": {"S": sk_prefix},
                        }
                    )
                    for item in response.get("Items", []):
                        all_items.append(BuildTaskItem.from_dynamodb_item(item))
                except (ClientError, BotoCoreError):
                    continue
                except Exception:
                    continue

        return all_items
