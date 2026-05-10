"""Task Manager for background task handling.

Implements task state machine with PENDING, RUNNING, COMPLETED, FAILED states.
Uses DynamoDB for persistence when configured, with in-memory fallback.

**Feature: spin-k8s-deployment**
**Validates: Requirements 17.1, 17.3**
"""

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional

from src.services.dynamodb import DynamoDBService, BuildTaskItem, BuildStatus


class TaskStatus(Enum):
    """Task status enum representing the state machine states."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


# Mapping from TaskStatus to BuildStatus for DynamoDB persistence
TASK_STATUS_TO_BUILD_STATUS: dict[TaskStatus, BuildStatus] = {
    TaskStatus.PENDING: BuildStatus.PENDING,
    TaskStatus.RUNNING: BuildStatus.BUILDING,
    TaskStatus.COMPLETED: BuildStatus.DONE,
    TaskStatus.FAILED: BuildStatus.FAILED,
}

# Mapping from BuildStatus to TaskStatus for reading from DynamoDB
BUILD_STATUS_TO_TASK_STATUS: dict[BuildStatus, TaskStatus] = {
    BuildStatus.PENDING: TaskStatus.PENDING,
    BuildStatus.BUILDING: TaskStatus.RUNNING,
    BuildStatus.PUSHING: TaskStatus.RUNNING,
    BuildStatus.DONE: TaskStatus.COMPLETED,
    BuildStatus.FAILED: TaskStatus.FAILED,
}


@dataclass
class Task:
    """Task dataclass representing a background task.
    
    Attributes:
        task_id: Unique identifier for the task
        status: Current status of the task
        created_at: Timestamp when task was created
        updated_at: Timestamp when task was last updated
        result: Result data when task completes successfully
        error: Error message when task fails
        workspace_id: Optional workspace identifier for DynamoDB persistence
        app_name: Optional application name
    """
    task_id: str
    status: TaskStatus
    created_at: datetime
    updated_at: datetime
    result: dict[str, Any] | None = None
    error: str | None = None
    workspace_id: str | None = None
    app_name: str | None = None


class TaskManager:
    """Manages background tasks and their state transitions.
    
    Provides methods to create tasks, update their status, and query task state.
    Uses DynamoDB for persistence when workspace_id is provided, with in-memory
    fallback for backward compatibility.
    
    **Feature: spin-k8s-deployment**
    **Validates: Requirements 17.1, 17.3**
    """
    
    def __init__(self, dynamodb_service: Optional[DynamoDBService] = None) -> None:
        """Initialize the task manager.
        
        Args:
            dynamodb_service: Optional DynamoDB service for persistence.
                             If not provided, a default instance will be created.
        """
        self._tasks: dict[str, Task] = {}
        self._dynamodb = dynamodb_service or DynamoDBService()
        # Map task_id to workspace_id for DynamoDB lookups
        self._task_workspace_map: dict[str, str] = {}
    
    def create_task(
        self,
        workspace_id: Optional[str] = None,
        app_name: Optional[str] = None,
        source_code_path: Optional[str] = None,
    ) -> str:
        """Create a new task with PENDING status.
        
        When workspace_id is provided, the task is persisted to DynamoDB.
        Otherwise, it's stored in-memory only.
        
        Args:
            workspace_id: Optional workspace identifier for DynamoDB persistence.
            app_name: Optional application name.
            source_code_path: Optional S3 path to source code.
        
        Returns:
            The unique task ID for the created task.
            
        **Validates: Requirements 17.1, 17.2**
        """
        task_id = str(uuid.uuid4())
        now = datetime.utcnow()
        
        task = Task(
            task_id=task_id,
            status=TaskStatus.PENDING,
            created_at=now,
            updated_at=now,
            workspace_id=workspace_id,
            app_name=app_name,
        )
        
        # Always store in memory for fast access
        self._tasks[task_id] = task
        
        # If workspace_id is provided, persist to DynamoDB
        if workspace_id:
            self._task_workspace_map[task_id] = workspace_id
            
            # Create DynamoDB item
            db_item = BuildTaskItem(
                workspace_id=workspace_id,
                task_id=task_id,
                app_name=app_name or "unknown",
                status=BuildStatus.PENDING,
                source_code_path=source_code_path or "",
                created_at=now,
                updated_at=now,
            )
            self._dynamodb.create_task(db_item)
        
        return task_id
    
    def update_status(
        self,
        task_id: str,
        status: TaskStatus,
        result: dict[str, Any] | None = None,
        error: str | None = None,
        wasm_path: str | None = None,
        image_url: str | None = None,
    ) -> bool:
        """Update the status of an existing task.
        
        Updates both in-memory store and DynamoDB (if workspace_id was provided
        during task creation).
        
        Args:
            task_id: The ID of the task to update
            status: The new status to set
            result: Optional result data (for COMPLETED status)
            error: Optional error message (for FAILED status)
            wasm_path: Optional S3 path to WASM artifact
            image_url: Optional ECR image URI
            
        Returns:
            True if the task was found and updated, False otherwise.
            
        **Validates: Requirements 17.3, 17.4, 17.5, 17.6**
        """
        # Update in-memory store
        if task_id in self._tasks:
            task = self._tasks[task_id]
            task.status = status
            task.updated_at = datetime.utcnow()
            task.result = result
            task.error = error
        
        # Update DynamoDB if workspace_id is known
        workspace_id = self._task_workspace_map.get(task_id)
        if workspace_id:
            build_status = TASK_STATUS_TO_BUILD_STATUS.get(status, BuildStatus.PENDING)
            
            # Extract wasm_path and image_url from result if not provided directly
            if result and not wasm_path:
                wasm_path = result.get("wasm_path")
            if result and not image_url:
                image_url = result.get("image_uri")
            
            self._dynamodb.update_status(
                workspace_id=workspace_id,
                task_id=task_id,
                status=build_status,
                wasm_path=wasm_path,
                image_url=image_url,
                error_message=error,
            )
        
        return task_id in self._tasks or workspace_id is not None
    
    def get_task(self, task_id: str, workspace_id: Optional[str] = None) -> Task | None:
        """Get a task by its ID.
        
        First checks in-memory store, then falls back to DynamoDB if workspace_id
        is provided or known from task creation.
        
        Args:
            task_id: The ID of the task to retrieve
            workspace_id: Optional workspace identifier for DynamoDB lookup
            
        Returns:
            The Task object if found, None otherwise.
            
        **Validates: Requirements 17.7**
        """
        # Check in-memory store first
        if task_id in self._tasks:
            return self._tasks[task_id]
        
        # Try to get workspace_id from map if not provided
        ws_id = workspace_id or self._task_workspace_map.get(task_id)
        
        # Fall back to DynamoDB if workspace_id is available
        if ws_id:
            db_item = self._dynamodb.get_task(ws_id, task_id)
            if db_item:
                task = self._build_task_item_to_task(db_item)
                # Cache in memory
                self._tasks[task_id] = task
                self._task_workspace_map[task_id] = ws_id
                return task
        
        return None
    
    def list_tasks(self, workspace_id: str) -> list[Task]:
        """List all tasks for a workspace.
        
        Queries DynamoDB for all build tasks in the specified workspace.
        
        Args:
            workspace_id: The workspace identifier.
            
        Returns:
            List of Task objects. Empty list if none found.
            
        **Validates: Requirements 17.8**
        """
        db_items = self._dynamodb.list_tasks(workspace_id)
        tasks = []
        for db_item in db_items:
            task = self._build_task_item_to_task(db_item)
            # Cache in memory
            self._tasks[task.task_id] = task
            self._task_workspace_map[task.task_id] = workspace_id
            tasks.append(task)
        return tasks
    
    def _build_task_item_to_task(self, db_item: BuildTaskItem) -> Task:
        """Convert a BuildTaskItem from DynamoDB to a Task object.
        
        Args:
            db_item: The DynamoDB item to convert.
            
        Returns:
            Task object with data from DynamoDB.
        """
        status = BUILD_STATUS_TO_TASK_STATUS.get(db_item.status, TaskStatus.PENDING)
        
        # Build result dict from DynamoDB fields
        result: dict[str, Any] | None = None
        if db_item.wasm_path or db_item.image_url:
            result = {}
            if db_item.wasm_path:
                result["wasm_path"] = db_item.wasm_path
            if db_item.image_url:
                result["image_uri"] = db_item.image_url
        
        return Task(
            task_id=db_item.task_id,
            status=status,
            created_at=db_item.created_at,
            updated_at=db_item.updated_at,
            result=result,
            error=db_item.error_message,
            workspace_id=db_item.workspace_id,
            app_name=db_item.app_name,
        )
    
    def update_build_status(
        self,
        task_id: str,
        build_status: BuildStatus,
        wasm_path: str | None = None,
        image_url: str | None = None,
        error: str | None = None,
    ) -> bool:
        """Update task with a specific BuildStatus (for finer-grained status tracking).
        
        This method allows setting BUILDING or PUSHING status directly,
        which maps to RUNNING in the TaskStatus enum.
        
        Args:
            task_id: The ID of the task to update
            build_status: The BuildStatus to set (PENDING, BUILDING, PUSHING, DONE, FAILED)
            wasm_path: Optional S3 path to WASM artifact
            image_url: Optional ECR image URI
            error: Optional error message
            
        Returns:
            True if the task was found and updated, False otherwise.
            
        **Validates: Requirements 17.3**
        """
        task_status = BUILD_STATUS_TO_TASK_STATUS.get(build_status, TaskStatus.PENDING)
        
        # Update in-memory store
        if task_id in self._tasks:
            task = self._tasks[task_id]
            task.status = task_status
            task.updated_at = datetime.utcnow()
            if error:
                task.error = error
            if wasm_path or image_url:
                task.result = task.result or {}
                if wasm_path:
                    task.result["wasm_path"] = wasm_path
                if image_url:
                    task.result["image_uri"] = image_url
        
        # Update DynamoDB if workspace_id is known
        workspace_id = self._task_workspace_map.get(task_id)
        if workspace_id:
            self._dynamodb.update_status(
                workspace_id=workspace_id,
                task_id=task_id,
                status=build_status,
                wasm_path=wasm_path,
                image_url=image_url,
                error_message=error,
            )
        
        return task_id in self._tasks or workspace_id is not None
