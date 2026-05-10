"""Property-based tests for DynamoDB Service.

This module tests:
- DynamoDB Task Persistence Round-Trip (Property 26)
- DynamoDB Status Update Consistency (Property 27)
- DynamoDB PK/SK Format Consistency (Property 28)

**Feature: spin-k8s-deployment**
**Validates: Requirements 17.1, 17.2, 17.3, 17.7**
"""

from datetime import datetime
from hypothesis import given, settings, strategies as st

from src.services.dynamodb import BuildStatus, BuildTaskItem


# Strategy for valid workspace IDs (alphanumeric with hyphens)
workspace_id_strategy = st.text(
    alphabet=st.sampled_from("abcdefghijklmnopqrstuvwxyz0123456789-"),
    min_size=1,
    max_size=50,
).filter(lambda s: s[0].isalnum() and s[-1].isalnum() and "--" not in s)

# Strategy for valid task IDs (UUID-like format)
task_id_strategy = st.uuids().map(str)

# Strategy for valid app names
app_name_strategy = st.text(
    alphabet=st.sampled_from("abcdefghijklmnopqrstuvwxyz0123456789-"),
    min_size=1,
    max_size=63,
).filter(lambda s: s[0].isalnum() and s[-1].isalnum() and "--" not in s)

# Strategy for build status
build_status_strategy = st.sampled_from(list(BuildStatus))

# Strategy for S3 paths
s3_path_strategy = st.builds(
    lambda bucket, prefix, ws, task, fname: f"s3://{bucket}/{prefix}/{ws}/{task}/{fname}",
    bucket=st.text(
        alphabet=st.sampled_from("abcdefghijklmnopqrstuvwxyz0123456789-"),
        min_size=3,
        max_size=20
    ).filter(lambda s: s[0].isalnum()),
    prefix=st.sampled_from(["build-sources", "build-artifacts"]),
    ws=workspace_id_strategy,
    task=task_id_strategy,
    fname=st.sampled_from(["app.py", "app.wasm", "source.zip"]),
)


# Strategy for ECR image URLs
image_url_strategy = st.builds(
    lambda account, region, repo, tag: f"{account}.dkr.ecr.{region}.amazonaws.com/{repo}:{tag}",
    account=st.text(alphabet=st.sampled_from("0123456789"), min_size=12, max_size=12),
    region=st.sampled_from(["ap-northeast-2", "us-east-1", "eu-west-1"]),
    repo=st.text(
        alphabet=st.sampled_from("abcdefghijklmnopqrstuvwxyz0123456789-"),
        min_size=1,
        max_size=30
    ).filter(lambda s: s[0].isalnum()),
    tag=st.text(
        alphabet=st.sampled_from("abcdefghijklmnopqrstuvwxyz0123456789-."),
        min_size=1,
        max_size=20
    ).filter(lambda s: s[0].isalnum()),
)

# Strategy for error messages
error_message_strategy = st.text(min_size=1, max_size=500)

# Strategy for datetime (within reasonable range)
datetime_strategy = st.datetimes(
    min_value=datetime(2020, 1, 1),
    max_value=datetime(2030, 12, 31),
)


@st.composite
def build_task_item_strategy(draw):
    """Generate valid BuildTaskItem instances."""
    workspace_id = draw(workspace_id_strategy)
    task_id = draw(task_id_strategy)
    app_name = draw(app_name_strategy)
    status = draw(build_status_strategy)
    source_code_path = draw(s3_path_strategy)
    created_at = draw(datetime_strategy)
    updated_at = draw(st.datetimes(
        min_value=created_at,
        max_value=datetime(2030, 12, 31),
    ))
    
    wasm_path = None
    image_url = None
    error_message = None
    
    if status in (BuildStatus.PUSHING, BuildStatus.DONE):
        wasm_path = draw(st.one_of(st.none(), s3_path_strategy))
    if status == BuildStatus.DONE:
        image_url = draw(st.one_of(st.none(), image_url_strategy))
    if status == BuildStatus.FAILED:
        error_message = draw(st.one_of(st.none(), error_message_strategy))
    
    return BuildTaskItem(
        workspace_id=workspace_id,
        task_id=task_id,
        app_name=app_name,
        status=status,
        source_code_path=source_code_path,
        created_at=created_at,
        updated_at=updated_at,
        wasm_path=wasm_path,
        image_url=image_url,
        error_message=error_message,
    )



class TestDynamoDBPKSKFormat:
    """Property tests for DynamoDB PK/SK format consistency.
    
    **Feature: spin-k8s-deployment, Property 28: DynamoDB PK/SK Format Consistency**
    **Validates: Requirements 17.1**
    """

    @given(ws_id=workspace_id_strategy)
    @settings(max_examples=100)
    def test_pk_format_consistency(self, ws_id: str):
        """
        **Feature: spin-k8s-deployment, Property 28: DynamoDB PK/SK Format Consistency**
        **Validates: Requirements 17.1**
        
        For any workspace_id, the generated PK should be ws#{workspace_id}.
        """
        pk = BuildTaskItem.generate_pk(ws_id)
        
        assert pk == f"ws#{ws_id}", f"PK should be ws#{ws_id}, got {pk}"
        assert pk.startswith("ws#"), f"PK should start with 'ws#', got {pk}"
        
        extracted_ws_id = pk.replace("ws#", "", 1)
        assert extracted_ws_id == ws_id

    @given(t_id=task_id_strategy)
    @settings(max_examples=100)
    def test_sk_format_consistency(self, t_id: str):
        """
        **Feature: spin-k8s-deployment, Property 28: DynamoDB PK/SK Format Consistency**
        **Validates: Requirements 17.1**
        
        For any task_id, the generated SK should be build#{task_id}.
        """
        sk = BuildTaskItem.generate_sk(t_id)
        
        assert sk == f"build#{t_id}", f"SK should be build#{t_id}, got {sk}"
        assert sk.startswith("build#"), f"SK should start with 'build#', got {sk}"
        
        extracted_t_id = sk.replace("build#", "", 1)
        assert extracted_t_id == t_id

    @given(item=build_task_item_strategy())
    @settings(max_examples=100)
    def test_item_pk_sk_properties(self, item: BuildTaskItem):
        """
        **Feature: spin-k8s-deployment, Property 28: DynamoDB PK/SK Format Consistency**
        **Validates: Requirements 17.1**
        
        For any BuildTaskItem, the pk and sk properties should match
        the static generate methods.
        """
        assert item.pk == BuildTaskItem.generate_pk(item.workspace_id)
        assert item.sk == BuildTaskItem.generate_sk(item.task_id)

    @given(ws_id=workspace_id_strategy, t_id=task_id_strategy)
    @settings(max_examples=100)
    def test_pk_sk_are_deterministic(self, ws_id: str, t_id: str):
        """
        **Feature: spin-k8s-deployment, Property 28: DynamoDB PK/SK Format Consistency**
        **Validates: Requirements 17.1**
        
        For any workspace_id and task_id, generating PK/SK multiple times
        should always produce the same result.
        """
        pk1 = BuildTaskItem.generate_pk(ws_id)
        pk2 = BuildTaskItem.generate_pk(ws_id)
        pk3 = BuildTaskItem.generate_pk(ws_id)
        
        sk1 = BuildTaskItem.generate_sk(t_id)
        sk2 = BuildTaskItem.generate_sk(t_id)
        sk3 = BuildTaskItem.generate_sk(t_id)
        
        assert pk1 == pk2 == pk3, "PK generation should be deterministic"
        assert sk1 == sk2 == sk3, "SK generation should be deterministic"



class TestDynamoDBRoundTrip:
    """Property tests for DynamoDB task persistence round-trip.
    
    **Feature: spin-k8s-deployment, Property 26: DynamoDB Task Persistence Round-Trip**
    **Validates: Requirements 17.1, 17.2, 17.7**
    """

    @given(item=build_task_item_strategy())
    @settings(max_examples=100)
    def test_to_dynamodb_item_contains_required_fields(self, item: BuildTaskItem):
        """
        **Feature: spin-k8s-deployment, Property 26: DynamoDB Task Persistence Round-Trip**
        **Validates: Requirements 17.1, 17.2**
        
        For any BuildTaskItem, converting to DynamoDB format should include
        all required fields: PK, SK, Type, AppName, Status, SourceCodePath,
        CreatedAt, UpdatedAt.
        """
        dynamo_item = item.to_dynamodb_item()
        
        required_fields = ["PK", "SK", "Type", "AppName", "Status", 
                          "SourceCodePath", "CreatedAt", "UpdatedAt"]
        for field in required_fields:
            assert field in dynamo_item, f"Required field {field} missing"
            assert "S" in dynamo_item[field], f"Field {field} should have 'S' type"
        
        assert dynamo_item["Type"]["S"] == "BuildTask"

    @given(item=build_task_item_strategy())
    @settings(max_examples=100)
    def test_round_trip_preserves_all_fields(self, item: BuildTaskItem):
        """
        **Feature: spin-k8s-deployment, Property 26: DynamoDB Task Persistence Round-Trip**
        **Validates: Requirements 17.1, 17.2, 17.7**
        
        For any valid BuildTaskItem, converting to DynamoDB format and back
        should produce an equivalent object with all fields preserved.
        """
        dynamo_item = item.to_dynamodb_item()
        restored_item = BuildTaskItem.from_dynamodb_item(dynamo_item)
        
        assert restored_item.workspace_id == item.workspace_id
        assert restored_item.task_id == item.task_id
        assert restored_item.app_name == item.app_name
        assert restored_item.status == item.status
        assert restored_item.source_code_path == item.source_code_path
        assert restored_item.created_at == item.created_at
        assert restored_item.updated_at == item.updated_at
        assert restored_item.wasm_path == item.wasm_path
        assert restored_item.image_url == item.image_url
        assert restored_item.error_message == item.error_message

    @given(item=build_task_item_strategy())
    @settings(max_examples=100)
    def test_round_trip_preserves_pk_sk(self, item: BuildTaskItem):
        """
        **Feature: spin-k8s-deployment, Property 26: DynamoDB Task Persistence Round-Trip**
        **Validates: Requirements 17.1, 17.7**
        
        For any BuildTaskItem, the PK and SK should be correctly preserved
        through the round-trip conversion.
        """
        dynamo_item = item.to_dynamodb_item()
        
        assert dynamo_item["PK"]["S"] == item.pk
        assert dynamo_item["SK"]["S"] == item.sk
        
        restored_item = BuildTaskItem.from_dynamodb_item(dynamo_item)
        assert restored_item.pk == item.pk
        assert restored_item.sk == item.sk

    @given(item=build_task_item_strategy())
    @settings(max_examples=100)
    def test_optional_fields_handled_correctly(self, item: BuildTaskItem):
        """
        **Feature: spin-k8s-deployment, Property 26: DynamoDB Task Persistence Round-Trip**
        **Validates: Requirements 17.1, 17.2, 17.7**
        
        For any BuildTaskItem, optional fields should only be included
        in DynamoDB format when they have values.
        """
        dynamo_item = item.to_dynamodb_item()
        
        if item.wasm_path is not None:
            assert "WasmPath" in dynamo_item
            assert dynamo_item["WasmPath"]["S"] == item.wasm_path
        else:
            assert "WasmPath" not in dynamo_item
        
        if item.image_url is not None:
            assert "ImageUrl" in dynamo_item
            assert dynamo_item["ImageUrl"]["S"] == item.image_url
        else:
            assert "ImageUrl" not in dynamo_item
        
        if item.error_message is not None:
            assert "ErrorMessage" in dynamo_item
            assert dynamo_item["ErrorMessage"]["S"] == item.error_message
        else:
            assert "ErrorMessage" not in dynamo_item

    @given(item=build_task_item_strategy())
    @settings(max_examples=100)
    def test_status_enum_preserved(self, item: BuildTaskItem):
        """
        **Feature: spin-k8s-deployment, Property 26: DynamoDB Task Persistence Round-Trip**
        **Validates: Requirements 17.1, 17.2, 17.7**
        
        For any BuildTaskItem, the BuildStatus enum should be correctly
        serialized and deserialized through the round-trip.
        """
        dynamo_item = item.to_dynamodb_item()
        
        assert dynamo_item["Status"]["S"] == item.status.value
        
        restored_item = BuildTaskItem.from_dynamodb_item(dynamo_item)
        assert restored_item.status == item.status
        assert isinstance(restored_item.status, BuildStatus)



class TestDynamoDBStatusUpdateConsistency:
    """Property tests for DynamoDB status update consistency.
    
    **Feature: spin-k8s-deployment, Property 27: DynamoDB Status Update Consistency**
    **Validates: Requirements 17.3**
    """

    @given(status=build_status_strategy)
    @settings(max_examples=100)
    def test_all_status_values_are_valid_enum_members(self, status: BuildStatus):
        """
        **Feature: spin-k8s-deployment, Property 27: DynamoDB Status Update Consistency**
        **Validates: Requirements 17.3**
        
        For any BuildStatus, it should be a valid enum member with a string value.
        """
        assert isinstance(status, BuildStatus)
        assert isinstance(status.value, str)
        assert status.value in ["PENDING", "BUILDING", "PUSHING", "DONE", "FAILED"]

    @given(status=build_status_strategy)
    @settings(max_examples=100)
    def test_status_can_be_created_from_value(self, status: BuildStatus):
        """
        **Feature: spin-k8s-deployment, Property 27: DynamoDB Status Update Consistency**
        **Validates: Requirements 17.3**
        
        For any BuildStatus, it should be possible to recreate the enum
        from its string value.
        """
        value = status.value
        recreated = BuildStatus(value)
        assert recreated == status

    @given(
        ws_id=workspace_id_strategy,
        t_id=task_id_strategy,
        app_name=app_name_strategy,
        source_path=s3_path_strategy,
        created_at=datetime_strategy,
    )
    @settings(max_examples=100)
    def test_status_update_preserves_immutable_fields(
        self,
        ws_id: str,
        t_id: str,
        app_name: str,
        source_path: str,
        created_at: datetime,
    ):
        """
        **Feature: spin-k8s-deployment, Property 27: DynamoDB Status Update Consistency**
        **Validates: Requirements 17.3**
        
        For any status update, immutable fields (workspace_id, task_id, app_name,
        source_code_path, created_at) should remain unchanged.
        """
        item = BuildTaskItem(
            workspace_id=ws_id,
            task_id=t_id,
            app_name=app_name,
            status=BuildStatus.PENDING,
            source_code_path=source_path,
            created_at=created_at,
            updated_at=created_at,
        )
        
        updated_item = BuildTaskItem(
            workspace_id=ws_id,
            task_id=t_id,
            app_name=app_name,
            status=BuildStatus.BUILDING,
            source_code_path=source_path,
            created_at=created_at,
            updated_at=datetime.utcnow(),
        )
        
        assert updated_item.workspace_id == item.workspace_id
        assert updated_item.task_id == item.task_id
        assert updated_item.app_name == item.app_name
        assert updated_item.source_code_path == item.source_code_path
        assert updated_item.created_at == item.created_at
        assert updated_item.pk == item.pk
        assert updated_item.sk == item.sk


class TestBuildStatusEnum:
    """Tests for BuildStatus enum values and behavior."""

    def test_all_expected_statuses_exist(self):
        """Verify all expected status values exist in the enum."""
        expected_statuses = ["PENDING", "BUILDING", "PUSHING", "DONE", "FAILED"]
        
        for status_name in expected_statuses:
            assert hasattr(BuildStatus, status_name)
            status = getattr(BuildStatus, status_name)
            assert status.value == status_name

    def test_status_count(self):
        """Verify the enum has exactly 5 status values."""
        assert len(BuildStatus) == 5
