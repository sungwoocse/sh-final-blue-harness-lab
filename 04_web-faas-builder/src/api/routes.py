"""FastAPI routes for Spin K8s Deployment Tool."""

import uuid
import tempfile
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, File, Form, HTTPException, UploadFile

from src.models.api_models import (
    BuildResponse,
    DeployRequest,
    DeployResponse,
    PushRequest,
    ScaffoldRequest,
    ScaffoldResponse,
    TaskStatusResponse,
    TaskListItem,
    TaskListResponse,
)
from src.services.task_manager import TaskManager, TaskStatus
from src.services.dynamodb import BuildStatus
from src.services.file_handler import FileHandler
from src.services.validation import ValidationService
from src.services.build import BuildService
from src.services.push import PushService
from src.services.scaffold import ScaffoldService
from src.services.deploy import DeployService
from src.services.manifest import ManifestService
from src.services.s3_storage import S3StorageService
from src.services.core_service import (
    get_core_service_client,
    CoreServiceClientInterface,
)
from src.models.manifest import (
    SpinAppManifest,
    ResourceLimits,
    validate_autoscaling_config,
    Toleration,
)

router = APIRouter()

# Global service instances
task_manager = TaskManager()
file_handler = FileHandler()
validation_service = ValidationService()
build_service = BuildService()
push_service = PushService()
scaffold_service = ScaffoldService()
deploy_service = DeployService()
manifest_service = ManifestService()
s3_storage_service = S3StorageService()
core_service_client: CoreServiceClientInterface = get_core_service_client()


def run_build_task(
    task_id: str,
    file_content: bytes,
    filename: str,
    app_name: str | None,
    workspace_id: str,
) -> None:
    """Background task to run the build process.
    
    This function:
    1. Updates task status to BUILDING (via DynamoDB)
    2. Handles file (zip or single .py)
    3. Uploads source to S3
    4. If Core Service is configured: calls Core Service for build
    5. Otherwise: validates with MyPy and executes local build
    6. Updates task status to DONE or FAILED (via DynamoDB)
    
    Requirements: 6.1, 6.2, 6.3, 6.4, 6.5
    Requirements: 16.1, 16.2, 16.4, 16.5 - Core Service integration
    Requirements: 17.1, 17.2, 17.3 - DynamoDB persistence
    """
    # Update status to BUILDING (Requirement 17.3)
    task_manager.update_build_status(task_id, BuildStatus.BUILDING)
    
    try:
        # Create temporary work directory
        work_dir = file_handler.create_temp_work_dir()
        
        # Handle file based on type
        if filename.endswith(".zip"):
            result = file_handler.handle_zip(file_content, work_dir)
        elif filename.endswith(".py"):
            result = file_handler.handle_single_py(file_content, filename, work_dir)
        else:
            task_manager.update_build_status(
                task_id,
                BuildStatus.FAILED,
                error=f"Unsupported file type: {filename}. Only .py and .zip files are supported."
            )
            return
        
        if not result.success:
            task_manager.update_build_status(
                task_id,
                BuildStatus.FAILED,
                error=result.error
            )
            return
        
        app_dir = result.app_dir
        
        # Upload source to S3 (Requirement 15.1)
        s3_upload_result = s3_storage_service.upload_source_directory(
            workspace_id=workspace_id,
            task_id=task_id,
            directory_path=app_dir,
        )
        
        if not s3_upload_result.success:
            task_manager.update_build_status(
                task_id,
                BuildStatus.FAILED,
                error=f"Failed to upload source to S3: {s3_upload_result.error}"
            )
            return
        
        s3_source_path = s3_upload_result.s3_path
        
        # Check if Core Service is configured (Requirement 16.1)
        from src.services.core_service import CoreServiceClient
        real_client = CoreServiceClient()
        
        if real_client.is_configured():
            # Use Core Service for build (Requirement 16.2)
            core_result = real_client.build(
                workspace_id=workspace_id,
                task_id=task_id,
                s3_source_path=s3_source_path,
                app_name=app_name,
            )
            
            if core_result.success:
                # Requirement 17.4 - Update WasmPath field
                task_manager.update_build_status(
                    task_id,
                    BuildStatus.DONE,
                    wasm_path=core_result.wasm_path,
                )
            else:
                # Requirement 16.5, 17.6 - Set task status to failed with error
                task_manager.update_build_status(
                    task_id,
                    BuildStatus.FAILED,
                    error=core_result.error
                )
        else:
            # Fall back to local build (Mock API behavior - Requirement 16.1)
            # Find Python files to validate
            py_files = list(app_dir.glob("*.py"))
            
            # Validate Python code with MyPy
            if py_files:
                # Validate the main Python file or all Python files
                validation_result = validation_service.validate_python(str(app_dir))
                
                if not validation_result.success:
                    task_manager.update_build_status(
                        task_id,
                        BuildStatus.FAILED,
                        error=f"MyPy validation failed:\n{validation_result.output}"
                    )
                    return
            
            # Execute the full build pipeline
            build_result = build_service.full_build(app_dir)
            
            if build_result.success:
                # Upload artifact to S3 (Requirement 15.2)
                if build_result.wasm_path:
                    artifact_result = s3_storage_service.upload_artifact(
                        task_id=task_id,
                        file_path=Path(build_result.wasm_path),
                    )
                    wasm_s3_path = artifact_result.s3_path if artifact_result.success else build_result.wasm_path
                else:
                    wasm_s3_path = build_result.wasm_path
                
                # Requirement 17.4 - Update WasmPath field
                task_manager.update_build_status(
                    task_id,
                    BuildStatus.DONE,
                    wasm_path=wasm_s3_path,
                )
            else:
                # Requirement 17.6 - Update ErrorMessage field
                task_manager.update_build_status(
                    task_id,
                    BuildStatus.FAILED,
                    error=build_result.error
                )
            
    except Exception as e:
        task_manager.update_build_status(
            task_id,
            BuildStatus.FAILED,
            error=f"Build task failed with unexpected error: {str(e)}"
        )


@router.post("/build", response_model=BuildResponse, status_code=202)
async def build(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    app_name: str | None = Form(None),
    workspace_id: str = Form(...),
) -> BuildResponse:
    """Build a Spin application from uploaded file.
    
    Accepts a .py file or .zip archive and starts a background build task.
    When Core Service is configured, uploads source to S3 and calls Core Service.
    Otherwise, falls back to local subprocess execution.
    
    Requirements: 6.1 - Start operation as background task and return task ID immediately
    Requirements: 16.1, 16.2 - Use Core Service when configured, Mock API otherwise
    Requirements: 17.1, 17.2 - Store task in DynamoDB with workspace_id
    """
    # Generate S3 source path for response (need task_id first)
    # We'll generate a preliminary task_id to compute the path
    import uuid
    preliminary_task_id = str(uuid.uuid4())
    source_s3_path = s3_storage_service.get_source_prefix(workspace_id, preliminary_task_id)
    
    # Create task with workspace_id and app_name for DynamoDB persistence
    # (Requirement 17.1, 17.2)
    task_id = task_manager.create_task(
        workspace_id=workspace_id,
        app_name=app_name,
        source_code_path=source_s3_path,
    )
    
    # Update source_s3_path with actual task_id
    source_s3_path = s3_storage_service.get_source_prefix(workspace_id, task_id)
    
    # Read file content
    file_content = await file.read()
    filename = file.filename or "app.py"
    
    # Add background task
    background_tasks.add_task(
        run_build_task,
        task_id,
        file_content,
        filename,
        app_name,
        workspace_id,
    )
    
    return BuildResponse(
        task_id=task_id,
        status="pending",
        message="Build task created",
        source_s3_path=source_s3_path,
    )


@router.get("/tasks/{task_id}", response_model=TaskStatusResponse)
async def get_task_status(
    task_id: str,
    workspace_id: str | None = None,
) -> TaskStatusResponse:
    """Get the status of a background task.
    
    Retrieves task data from DynamoDB when workspace_id is provided,
    otherwise falls back to in-memory store.
    
    Requirements: 17.7 - Retrieve task data from DynamoDB using PK and SK
    """
    task = task_manager.get_task(task_id, workspace_id=workspace_id)
    if task is None:
        raise HTTPException(status_code=404, detail=f"Task not found: {task_id}")
    
    return TaskStatusResponse(
        task_id=task.task_id,
        status=task.status.value,
        result=task.result,
        error=task.error,
    )


@router.get("/workspaces/{workspace_id}/tasks", response_model=TaskListResponse)
async def list_workspace_tasks(workspace_id: str) -> TaskListResponse:
    """List all build tasks for a workspace.
    
    Queries DynamoDB for all build tasks in the specified workspace.
    
    Requirements: 17.8 - Query all build tasks for a workspace from DynamoDB
    """
    tasks = task_manager.list_tasks(workspace_id)
    
    task_items = [
        TaskListItem(
            task_id=task.task_id,
            status=task.status.value,
            app_name=task.app_name,
            created_at=task.created_at.isoformat(),
            updated_at=task.updated_at.isoformat(),
            result=task.result,
            error=task.error,
        )
        for task in tasks
    ]
    
    return TaskListResponse(
        workspace_id=workspace_id,
        tasks=task_items,
        count=len(task_items),
    )


def run_push_task(
    task_id: str,
    app_dir: str,
    registry_url: str,
    username: str,
    password: str,
    tag: str | None,
    workspace_id: str,
    s3_source_path: str | None = None,
) -> None:
    """Background task to run the push process.
    
    This function:
    1. Updates task status to PUSHING (via DynamoDB)
    2. If Core Service is configured: calls Core Service for push
    3. Otherwise: logs into registry and pushes locally
    4. Updates task status to DONE or FAILED (via DynamoDB)
    
    Requirements: 6.1, 7.1, 7.2, 7.3, 7.4, 7.5, 7.6
    Requirements: 16.1, 16.3, 16.4, 16.5 - Core Service integration
    Requirements: 17.5, 17.6 - Update ImageUrl/ErrorMessage in DynamoDB
    """
    # Update status to PUSHING (Requirement 17.3)
    task_manager.update_build_status(task_id, BuildStatus.PUSHING)
    
    try:
        # Check if Core Service is configured (Requirement 16.1)
        from src.services.core_service import CoreServiceClient
        real_client = CoreServiceClient()
        
        if real_client.is_configured() and s3_source_path:
            # Use Core Service for push (Requirement 16.3)
            core_result = real_client.push(
                workspace_id=workspace_id,
                task_id=task_id,
                s3_source_path=s3_source_path,
                registry_url=registry_url,
                tag=tag,
            )
            
            if core_result.success:
                # Requirement 17.5 - Update ImageUrl field
                task_manager.update_build_status(
                    task_id,
                    BuildStatus.DONE,
                    image_url=core_result.image_url,
                )
            else:
                # Requirement 16.5, 17.6 - Set task status to failed with error
                task_manager.update_build_status(
                    task_id,
                    BuildStatus.FAILED,
                    error=core_result.error
                )
        else:
            # Fall back to local push (Mock API behavior - Requirement 16.1)
            app_path = Path(app_dir)
            temp_dir_created = False

            # If local app_dir doesn't exist but s3_source_path is provided, download from S3
            if not app_path.exists() and s3_source_path:
                import tempfile
                temp_work_dir = tempfile.mkdtemp(prefix="spin_push_")
                app_path = Path(temp_work_dir)
                temp_dir_created = True

                # Download source from S3
                download_result = s3_storage_service.download_source_directory(
                    s3_source_path,
                    app_path,
                )

                if not download_result.success:
                    task_manager.update_build_status(
                        task_id,
                        BuildStatus.FAILED,
                        error=f"Failed to download from S3: {download_result.error}"
                    )
                    return

            # Verify app directory exists
            if not app_path.exists():
                # Requirement 17.6 - Update ErrorMessage field
                task_manager.update_build_status(
                    task_id,
                    BuildStatus.FAILED,
                    error=f"Application directory not found: {app_dir}"
                )
                return

            try:
                # Execute the full push pipeline (login + push)
                push_result = push_service.full_push(
                    app_dir=app_path,
                    registry_url=registry_url,
                    username=username,
                    password=password,
                    tag=tag,
                )
            finally:
                # Clean up temp directory if created
                if temp_dir_created:
                    import shutil
                    shutil.rmtree(app_path, ignore_errors=True)
            
            if push_result.success:
                # Requirement 17.5 - Update ImageUrl field
                task_manager.update_build_status(
                    task_id,
                    BuildStatus.DONE,
                    image_url=push_result.image_uri,
                )
            else:
                # Requirement 17.6 - Update ErrorMessage field
                task_manager.update_build_status(
                    task_id,
                    BuildStatus.FAILED,
                    error=push_result.error
                )
            
    except Exception as e:
        # Requirement 17.6 - Update ErrorMessage field
        task_manager.update_build_status(
            task_id,
            BuildStatus.FAILED,
            error=f"Push task failed with unexpected error: {str(e)}"
        )


@router.post("/push", response_model=BuildResponse, status_code=202)
async def push(
    background_tasks: BackgroundTasks,
    request: PushRequest,
) -> BuildResponse:
    """Push a built Spin application to a container registry.
    
    When Core Service is configured, calls Core Service for push.
    Otherwise, falls back to local subprocess execution.
    
    Requirements: 6.1 - Start operation as background task and return task ID immediately
    Requirements: 7.1, 7.2, 7.3, 7.4, 7.5, 7.6 - Registry login and push operations
    Requirements: 16.1, 16.3 - Use Core Service when configured, Mock API otherwise
    Requirements: 17.1, 17.5, 17.6 - Store task in DynamoDB, update ImageUrl/ErrorMessage
    """
    # Create task with workspace_id for DynamoDB persistence (Requirement 17.1)
    task_id = task_manager.create_task(
        workspace_id=request.workspace_id,
        source_code_path=request.s3_source_path,
    )
    
    # Add background task
    background_tasks.add_task(
        run_push_task,
        task_id,
        request.app_dir,
        request.registry_url,
        request.username,
        request.password,
        request.tag,
        request.workspace_id,
        request.s3_source_path,
    )
    
    return BuildResponse(
        task_id=task_id,
        status="pending",
        message="Push task created",
    )


@router.post("/scaffold", response_model=ScaffoldResponse)
async def scaffold(request: ScaffoldRequest) -> ScaffoldResponse:
    """Generate SpinApp Kubernetes manifest using spin kube scaffold.
    
    Requirements: 8.1, 8.2, 8.3, 8.4, 8.5, 8.6
    - 8.1: Execute spin kube scaffold --from {image}
    - 8.2: Pass --component {name} when specified
    - 8.3: Pass --replicas {count} when specified
    - 8.4: Pass --out {path} when specified
    - 8.5: Return generated YAML content or file path on success
    - 8.6: Return stderr output on failure
    """
    result = scaffold_service.scaffold(
        image_ref=request.image_ref,
        component=request.component,
        replicas=request.replicas,
        output_path=request.output_path,
    )
    
    return ScaffoldResponse(
        success=result.success,
        yaml_content=result.yaml_content,
        file_path=result.file_path,
        error=result.error,
    )


@router.post("/deploy", response_model=DeployResponse)
async def deploy(request: DeployRequest) -> DeployResponse:
    """Deploy a SpinApp to Kubernetes cluster.
    
    Requirements: 10.1, 10.2, 10.3, 10.4, 10.5, 10.6, 10.7, 13.1, 13.2, 13.3, 13.4, 13.5
    Requirements: 14.1, 14.2, 14.3, 14.4, 14.5
    - 10.1: Set namespace in SpinApp manifest metadata
    - 10.2: Include serviceAccountName in SpinApp manifest spec
    - 10.3: Return error if namespace does not exist
    - 10.4: Return deployed SpinApp name and namespace on success
    - 10.5: Apply SpinApp manifest to Kubernetes cluster
    - 10.6: Use custom application name if provided
    - 10.7: Generate unique name using Faker if not provided
    - 13.1: Default enableAutoscaling to true
    - 13.2: Allow explicit enableAutoscaling=false
    - 13.3: Omit replicas when enableAutoscaling is true
    - 13.4: Include replicas when enableAutoscaling is false
    - 13.5: Validate mutual exclusion of enableAutoscaling and replicas
    - 14.1: Add default Spot toleration when use_spot is true
    - 14.2: Add default Spot affinity when use_spot is true
    - 14.3: Omit Spot settings when use_spot is false
    - 14.4: Include custom tolerations in addition to default Spot toleration
    - 14.5: Include custom affinity rules
    """
    import tempfile
    import os
    
    # Validate autoscaling configuration (Requirement 13.5)
    is_valid, error_msg = validate_autoscaling_config(
        request.enable_autoscaling,
        request.replicas
    )
    if not is_valid:
        raise HTTPException(status_code=400, detail=error_msg)

    # enable_autoscaling takes priority - ignore replicas when autoscaling is enabled
    effective_replicas = None if request.enable_autoscaling else request.replicas

    # Create SpinApp manifest
    # Apply default resource limits if not provided
    resources = ResourceLimits(
        cpu_limit=request.cpu_limit or "500m",
        memory_limit=request.memory_limit or "500Mi",
        cpu_request=request.cpu_request or "100m",
        memory_request=request.memory_request or "400Mi",
    )
    
    # Generate app name if not provided (Requirement 10.7)
    # Sanitize app_name: remove spaces, hyphens, underscores for K8s compatibility
    raw_app_name = request.app_name or deploy_service.generate_app_name()
    app_name = raw_app_name.replace(" ", "").replace("-", "").replace("_", "").strip().lower()
    
    # Parse custom tolerations (Requirement 14.4)
    custom_tolerations: list[Toleration] = []
    if request.custom_tolerations:
        for t in request.custom_tolerations:
            custom_tolerations.append(Toleration(
                key=t.get("key", ""),
                operator=t.get("operator", "Exists"),
                effect=t.get("effect", "NoSchedule"),
                value=t.get("value"),
            ))
    
    # Build pod_labels with function_id if provided
    pod_labels: dict[str, str] = {"faas": "true"}
    if request.function_id:
        pod_labels["function_id"] = request.function_id

    # Create manifest with autoscaling and Spot configuration
    # (Requirements 13.1, 13.2, 13.3, 13.4, 14.1, 14.2, 14.3, 14.4)
    manifest = SpinAppManifest(
        name=app_name,
        namespace=request.namespace,
        image=request.image_ref,
        service_account=request.service_account,
        resources=resources,
        replicas=effective_replicas,
        enable_autoscaling=request.enable_autoscaling,
        use_spot=request.use_spot,
        tolerations=custom_tolerations,
        pod_labels=pod_labels,
    )
    
    # Generate YAML manifest
    yaml_content = manifest_service.to_yaml(manifest)
    
    # Write manifest to temporary file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        f.write(yaml_content)
        manifest_path = f.name
    
    try:
        # Deploy using DeployService
        result = deploy_service.deploy(
            manifest_path=manifest_path,
            namespace=request.namespace,
            app_name=app_name,
            enable_autoscaling=request.enable_autoscaling,
            use_spot=request.use_spot,
        )
        
        if not result.success:
            # Return error response (Requirement 10.3)
            raise HTTPException(
                status_code=400 if "not found" in (result.error or "").lower() else 500,
                detail=result.error or "Deployment failed"
            )
        
        return DeployResponse(
            app_name=result.app_name or app_name,
            namespace=result.namespace or request.namespace,
            service_name=result.service_name,
            service_status=result.service_status,
            endpoint=result.endpoint,
            enable_autoscaling=result.enable_autoscaling,
            use_spot=result.use_spot,
            error=result.error,
        )
    finally:
        # Clean up temporary file
        if os.path.exists(manifest_path):
            os.unlink(manifest_path)


def run_build_and_push_task(
    task_id: str,
    file_content: bytes,
    filename: str,
    registry_url: str,
    username: str | None,
    password: str | None,
    tag: str | None,
    app_name: str | None,
    workspace_id: str,
) -> None:
    """Background task to run the build and push process.
    
    This function chains build and push services in a single background task:
    1. Updates task status to BUILDING (via DynamoDB)
    2. Handles file (zip or single .py)
    3. Uploads source to S3
    4. If Core Service is configured: calls Core Service for build and push
    5. Otherwise: validates with MyPy, builds locally, and pushes locally (uses IRSA for ECR auth)
    6. Updates task status to PUSHING, then DONE or FAILED (via DynamoDB)
    
    Requirements: 6.1, 6.7
    Requirements: 16.1, 16.2, 16.3, 16.4, 16.5 - Core Service integration
    Requirements: 17.1, 17.3, 17.4, 17.5, 17.6 - DynamoDB persistence
    """
    # Update status to BUILDING (Requirement 17.3)
    task_manager.update_build_status(task_id, BuildStatus.BUILDING)
    
    try:
        # Create temporary work directory
        work_dir = file_handler.create_temp_work_dir()
        
        # Handle file based on type
        if filename.endswith(".zip"):
            result = file_handler.handle_zip(file_content, work_dir)
        elif filename.endswith(".py"):
            result = file_handler.handle_single_py(file_content, filename, work_dir)
        else:
            task_manager.update_build_status(
                task_id,
                BuildStatus.FAILED,
                error=f"Unsupported file type: {filename}. Only .py and .zip files are supported."
            )
            return
        
        if not result.success:
            task_manager.update_build_status(
                task_id,
                BuildStatus.FAILED,
                error=result.error
            )
            return
        
        app_dir = result.app_dir
        
        # Upload source to S3 (Requirement 15.1)
        s3_upload_result = s3_storage_service.upload_source_directory(
            workspace_id=workspace_id,
            task_id=task_id,
            directory_path=app_dir,
        )
        
        if not s3_upload_result.success:
            task_manager.update_build_status(
                task_id,
                BuildStatus.FAILED,
                error=f"Failed to upload source to S3: {s3_upload_result.error}"
            )
            return
        
        s3_source_path = s3_upload_result.s3_path
        
        # Check if Core Service is configured (Requirement 16.1)
        from src.services.core_service import CoreServiceClient
        real_client = CoreServiceClient()
        
        if real_client.is_configured():
            # Use Core Service for build (Requirement 16.2)
            build_core_result = real_client.build(
                workspace_id=workspace_id,
                task_id=task_id,
                s3_source_path=s3_source_path,
                app_name=app_name,
            )
            
            if not build_core_result.success:
                # Requirement 16.5, 17.6 - Set task status to failed with error
                task_manager.update_build_status(
                    task_id,
                    BuildStatus.FAILED,
                    error=f"Build failed: {build_core_result.error}"
                )
                return
            
            # Update status to PUSHING (Requirement 17.3)
            task_manager.update_build_status(
                task_id,
                BuildStatus.PUSHING,
                wasm_path=build_core_result.wasm_path,
            )
            
            # Use Core Service for push (Requirement 16.3)
            push_core_result = real_client.push(
                workspace_id=workspace_id,
                task_id=task_id,
                s3_source_path=s3_source_path,
                registry_url=registry_url,
                tag=tag,
            )
            
            if push_core_result.success:
                # Requirement 17.4, 17.5 - Update WasmPath and ImageUrl fields
                task_manager.update_build_status(
                    task_id,
                    BuildStatus.DONE,
                    wasm_path=build_core_result.wasm_path,
                    image_url=push_core_result.image_url,
                )
            else:
                # Requirement 16.5, 17.6 - Set task status to failed with error
                task_manager.update_build_status(
                    task_id,
                    BuildStatus.FAILED,
                    error=f"Push failed: {push_core_result.error}"
                )
        else:
            # Fall back to local build and push (Mock API behavior - Requirement 16.1)
            # Find Python files to validate
            py_files = list(app_dir.glob("*.py"))
            
            # Validate Python code with MyPy
            if py_files:
                validation_result = validation_service.validate_python(str(app_dir))
                
                if not validation_result.success:
                    task_manager.update_build_status(
                        task_id,
                        BuildStatus.FAILED,
                        error=f"MyPy validation failed:\n{validation_result.output}"
                    )
                    return
            
            # Execute the full build pipeline
            build_result = build_service.full_build(app_dir)
            
            if not build_result.success:
                task_manager.update_build_status(
                    task_id,
                    BuildStatus.FAILED,
                    error=f"Build failed: {build_result.error}"
                )
                return
            
            # Upload artifact to S3 (Requirement 15.2)
            wasm_s3_path = build_result.wasm_path
            if build_result.wasm_path:
                artifact_result = s3_storage_service.upload_artifact(
                    task_id=task_id,
                    file_path=Path(build_result.wasm_path),
                )
                if artifact_result.success:
                    wasm_s3_path = artifact_result.s3_path
            
            # Update status to PUSHING (Requirement 17.3)
            task_manager.update_build_status(
                task_id,
                BuildStatus.PUSHING,
                wasm_path=wasm_s3_path,
            )
            
            # Execute the full push pipeline (login + push)
            push_result = push_service.full_push(
                app_dir=app_dir,
                registry_url=registry_url,
                username=username,
                password=password,
                tag=tag,
            )
            
            if push_result.success:
                # Requirement 17.4, 17.5 - Update WasmPath and ImageUrl fields
                task_manager.update_build_status(
                    task_id,
                    BuildStatus.DONE,
                    wasm_path=wasm_s3_path,
                    image_url=push_result.image_uri,
                )
            else:
                # Requirement 17.6 - Update ErrorMessage field
                task_manager.update_build_status(
                    task_id,
                    BuildStatus.FAILED,
                    error=f"Push failed: {push_result.error}"
                )
            
    except Exception as e:
        # Requirement 17.6 - Update ErrorMessage field
        task_manager.update_build_status(
            task_id,
            BuildStatus.FAILED,
            error=f"Build and push task failed with unexpected error: {str(e)}"
        )


@router.post("/build-and-push", response_model=BuildResponse, status_code=202)
async def build_and_push(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    workspace_id: str = Form(...),
    username: str | None = Form(None),
    password: str | None = Form(None),
    tag: str | None = Form(None),
    app_name: str | None = Form(None),
) -> BuildResponse:
    """Build and push a Spin application in a single operation.
    
    Accepts a .py file or .zip archive, builds it, and pushes to the registry.
    When Core Service is configured, uploads source to S3 and calls Core Service.
    Otherwise, falls back to local subprocess execution.
    
    ECR registry URL is automatically set to: 217350599014.dkr.ecr.ap-northeast-2.amazonaws.com/blue-final-faas-app
    Authentication uses IRSA (IAM Roles for Service Accounts) automatically - username/password are optional.
    
    Requirements: 6.1, 6.7 - Start combined operation as background task
    Requirements: 16.1, 16.2, 16.3 - Use Core Service when configured, Mock API otherwise
    Requirements: 17.1, 17.2 - Store task in DynamoDB with workspace_id
    """
    # Use ECR registry URL from config (automatically set)
    from src.config import config
    registry_url = config.ecr_registry_url
    
    # Generate S3 source path for response
    import uuid
    preliminary_task_id = str(uuid.uuid4())
    source_s3_path = s3_storage_service.get_source_prefix(workspace_id, preliminary_task_id)
    
    # Create task with workspace_id and app_name for DynamoDB persistence
    # (Requirement 17.1, 17.2)
    task_id = task_manager.create_task(
        workspace_id=workspace_id,
        app_name=app_name,
        source_code_path=source_s3_path,
    )
    
    # Update source_s3_path with actual task_id
    source_s3_path = s3_storage_service.get_source_prefix(workspace_id, task_id)
    
    # Read file content
    file_content = await file.read()
    filename = file.filename or "app.py"
    
    # Add background task
    background_tasks.add_task(
        run_build_and_push_task,
        task_id,
        file_content,
        filename,
        registry_url,
        username,
        password,
        tag,
        app_name,
        workspace_id,
    )
    
    # Generate S3 source path for response
    source_s3_path = s3_storage_service.get_source_prefix(workspace_id, task_id)
    
    return BuildResponse(
        task_id=task_id,
        status="pending",
        message="Build and push task created",
        source_s3_path=source_s3_path,
    )
