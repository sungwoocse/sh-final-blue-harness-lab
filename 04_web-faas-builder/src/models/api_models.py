"""Pydantic models for API requests and responses."""

from pydantic import BaseModel


class BuildRequest(BaseModel):
    """Request model for build endpoint."""
    app_name: str | None = None


class BuildResponse(BaseModel):
    """Response model for build and push operations.
    
    Requirements: 15.1 - Include S3 source path in response
    """
    task_id: str
    status: str
    message: str
    source_s3_path: str | None = None


class PushRequest(BaseModel):
    """Request model for push endpoint.
    
    Requirements: 16.3, 16.4 - Include workspace_id and s3_source_path for Core Service
    """
    registry_url: str
    username: str
    password: str
    tag: str | None = None
    app_dir: str
    workspace_id: str
    s3_source_path: str | None = None


class ScaffoldRequest(BaseModel):
    """Request model for scaffold endpoint."""
    image_ref: str
    component: str | None = None
    replicas: int = 1
    output_path: str | None = None


class ScaffoldResponse(BaseModel):
    """Response model for scaffold endpoint."""
    success: bool
    yaml_content: str | None = None
    file_path: str | None = None
    error: str | None = None


class DeployRequest(BaseModel):
    """Request model for deploy endpoint.

    Requirements: 10.1, 10.2, 10.5, 10.6, 10.7
    """
    app_name: str | None = None
    namespace: str
    service_account: str | None = None
    cpu_limit: str | None = None
    memory_limit: str | None = None
    cpu_request: str | None = None
    memory_request: str | None = None
    image_ref: str
    enable_autoscaling: bool = True
    replicas: int | None = None
    use_spot: bool = True
    custom_tolerations: list[dict] | None = None
    custom_affinity: dict | None = None
    function_id: str | None = None


class DeployResponse(BaseModel):
    """Response model for deploy endpoint.
    
    Requirements: 10.4, 10.5, 11.1, 11.2
    """
    app_name: str
    namespace: str
    service_name: str | None = None
    service_status: str = "pending"
    endpoint: str | None = None
    enable_autoscaling: bool = True
    use_spot: bool = True
    error: str | None = None


class TaskStatusResponse(BaseModel):
    """Response model for task status endpoint."""
    task_id: str
    status: str
    result: dict | None = None
    error: str | None = None


class TaskListItem(BaseModel):
    """Item in task list response.
    
    Requirements: 17.8 - List all build tasks for a workspace
    """
    task_id: str
    status: str
    app_name: str | None = None
    created_at: str
    updated_at: str
    result: dict | None = None
    error: str | None = None


class TaskListResponse(BaseModel):
    """Response model for list tasks endpoint.
    
    Requirements: 17.8 - Query all build tasks for a workspace from DynamoDB
    """
    workspace_id: str
    tasks: list[TaskListItem]
    count: int
