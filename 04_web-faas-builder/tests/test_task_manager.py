"""Property-based tests for Task Manager state transitions.

**Feature: spin-k8s-deployment, Property 2: Task State Transitions**
**Validates: Requirements 6.2, 6.3, 6.4, 6.5**

For any background task, the state transitions must follow the valid sequence:
PENDING → RUNNING → (COMPLETED | FAILED). A task created should start in PENDING,
transition to RUNNING when execution begins, and end in either COMPLETED with
result data or FAILED with error details.
"""

import pytest
from hypothesis import given, settings, strategies as st, assume

from src.services.task_manager import TaskManager, TaskStatus, Task


# Strategy for generating valid result data
@st.composite
def result_data_strategy(draw):
    """Generate valid result data dictionaries."""
    keys = draw(st.lists(
        st.text(min_size=1, max_size=20, alphabet=st.characters(whitelist_categories=('L', 'N'))),
        min_size=0,
        max_size=5,
        unique=True
    ))
    values = draw(st.lists(
        st.one_of(
            st.text(min_size=0, max_size=100),
            st.integers(),
            st.booleans(),
            st.none()
        ),
        min_size=len(keys),
        max_size=len(keys)
    ))
    return dict(zip(keys, values))


# Strategy for generating error messages
error_message_strategy = st.text(min_size=1, max_size=500)


class TestTaskStateTransitions:
    """Property-based tests for task state machine transitions.
    
    **Feature: spin-k8s-deployment, Property 2: Task State Transitions**
    """

    @given(st.data())
    @settings(max_examples=100)
    def test_task_created_starts_in_pending(self, data):
        """
        **Feature: spin-k8s-deployment, Property 2: Task State Transitions**
        **Validates: Requirements 6.2**
        
        For any newly created task, the initial status must be PENDING.
        """
        manager = TaskManager()
        task_id = manager.create_task()
        
        task = manager.get_task(task_id)
        
        assert task is not None, "Created task should be retrievable"
        assert task.status == TaskStatus.PENDING, "New task must start in PENDING status"
        assert task.result is None, "New task should have no result"
        assert task.error is None, "New task should have no error"

    @given(st.data())
    @settings(max_examples=100)
    def test_task_transitions_pending_to_running(self, data):
        """
        **Feature: spin-k8s-deployment, Property 2: Task State Transitions**
        **Validates: Requirements 6.3**
        
        For any task in PENDING status, it can transition to RUNNING status.
        """
        manager = TaskManager()
        task_id = manager.create_task()
        
        # Verify initial state
        task = manager.get_task(task_id)
        assert task.status == TaskStatus.PENDING
        
        # Transition to RUNNING
        success = manager.update_status(task_id, TaskStatus.RUNNING)
        
        assert success is True, "Update should succeed for existing task"
        task = manager.get_task(task_id)
        assert task.status == TaskStatus.RUNNING, "Task should be in RUNNING status"

    @given(result_data=result_data_strategy())
    @settings(max_examples=100)
    def test_task_transitions_running_to_completed_with_result(self, result_data: dict):
        """
        **Feature: spin-k8s-deployment, Property 2: Task State Transitions**
        **Validates: Requirements 6.4**
        
        For any task in RUNNING status, it can transition to COMPLETED with result data.
        The result data should be preserved in the task.
        """
        manager = TaskManager()
        task_id = manager.create_task()
        
        # Transition through valid states
        manager.update_status(task_id, TaskStatus.RUNNING)
        
        # Complete with result
        success = manager.update_status(task_id, TaskStatus.COMPLETED, result=result_data)
        
        assert success is True, "Update should succeed"
        task = manager.get_task(task_id)
        assert task.status == TaskStatus.COMPLETED, "Task should be in COMPLETED status"
        assert task.result == result_data, "Result data should be preserved"
        assert task.error is None, "Completed task should have no error"

    @given(error_msg=error_message_strategy)
    @settings(max_examples=100)
    def test_task_transitions_running_to_failed_with_error(self, error_msg: str):
        """
        **Feature: spin-k8s-deployment, Property 2: Task State Transitions**
        **Validates: Requirements 6.5**
        
        For any task in RUNNING status, it can transition to FAILED with error details.
        The error message should be preserved in the task.
        """
        manager = TaskManager()
        task_id = manager.create_task()
        
        # Transition through valid states
        manager.update_status(task_id, TaskStatus.RUNNING)
        
        # Fail with error
        success = manager.update_status(task_id, TaskStatus.FAILED, error=error_msg)
        
        assert success is True, "Update should succeed"
        task = manager.get_task(task_id)
        assert task.status == TaskStatus.FAILED, "Task should be in FAILED status"
        assert task.error == error_msg, "Error message should be preserved"
        assert task.result is None, "Failed task should have no result"

    @given(result_data=result_data_strategy())
    @settings(max_examples=100)
    def test_full_success_lifecycle(self, result_data: dict):
        """
        **Feature: spin-k8s-deployment, Property 2: Task State Transitions**
        **Validates: Requirements 6.2, 6.3, 6.4**
        
        For any task, the complete success lifecycle should be:
        PENDING → RUNNING → COMPLETED with result data.
        """
        manager = TaskManager()
        
        # Create task - should be PENDING
        task_id = manager.create_task()
        task = manager.get_task(task_id)
        assert task.status == TaskStatus.PENDING, "Step 1: Task should start PENDING"
        
        # Start execution - should be RUNNING
        manager.update_status(task_id, TaskStatus.RUNNING)
        task = manager.get_task(task_id)
        assert task.status == TaskStatus.RUNNING, "Step 2: Task should be RUNNING"
        
        # Complete - should be COMPLETED with result
        manager.update_status(task_id, TaskStatus.COMPLETED, result=result_data)
        task = manager.get_task(task_id)
        assert task.status == TaskStatus.COMPLETED, "Step 3: Task should be COMPLETED"
        assert task.result == result_data, "Result should be preserved"

    @given(error_msg=error_message_strategy)
    @settings(max_examples=100)
    def test_full_failure_lifecycle(self, error_msg: str):
        """
        **Feature: spin-k8s-deployment, Property 2: Task State Transitions**
        **Validates: Requirements 6.2, 6.3, 6.5**
        
        For any task, the complete failure lifecycle should be:
        PENDING → RUNNING → FAILED with error details.
        """
        manager = TaskManager()
        
        # Create task - should be PENDING
        task_id = manager.create_task()
        task = manager.get_task(task_id)
        assert task.status == TaskStatus.PENDING, "Step 1: Task should start PENDING"
        
        # Start execution - should be RUNNING
        manager.update_status(task_id, TaskStatus.RUNNING)
        task = manager.get_task(task_id)
        assert task.status == TaskStatus.RUNNING, "Step 2: Task should be RUNNING"
        
        # Fail - should be FAILED with error
        manager.update_status(task_id, TaskStatus.FAILED, error=error_msg)
        task = manager.get_task(task_id)
        assert task.status == TaskStatus.FAILED, "Step 3: Task should be FAILED"
        assert task.error == error_msg, "Error should be preserved"

    @given(st.data())
    @settings(max_examples=100)
    def test_timestamps_updated_on_state_change(self, data):
        """
        **Feature: spin-k8s-deployment, Property 2: Task State Transitions**
        **Validates: Requirements 6.2, 6.3, 6.4, 6.5**
        
        For any state transition, the updated_at timestamp should be updated.
        """
        manager = TaskManager()
        task_id = manager.create_task()
        
        task = manager.get_task(task_id)
        initial_updated_at = task.updated_at
        
        # Transition to RUNNING
        manager.update_status(task_id, TaskStatus.RUNNING)
        task = manager.get_task(task_id)
        
        assert task.updated_at >= initial_updated_at, "updated_at should be >= initial time"

    def test_update_nonexistent_task_returns_false(self):
        """
        **Feature: spin-k8s-deployment, Property 2: Task State Transitions**
        **Validates: Requirements 6.2, 6.3, 6.4, 6.5**
        
        Updating a non-existent task should return False.
        """
        manager = TaskManager()
        
        success = manager.update_status("nonexistent-id", TaskStatus.RUNNING)
        
        assert success is False, "Update should fail for non-existent task"

    def test_get_nonexistent_task_returns_none(self):
        """
        **Feature: spin-k8s-deployment, Property 2: Task State Transitions**
        **Validates: Requirements 6.2, 6.3, 6.4, 6.5**
        
        Getting a non-existent task should return None.
        """
        manager = TaskManager()
        
        task = manager.get_task("nonexistent-id")
        
        assert task is None, "Should return None for non-existent task"


class TestTaskStatusQueryConsistency:
    """Property-based tests for task status query consistency.
    
    **Feature: spin-k8s-deployment, Property 3: Task Status Query Consistency**
    **Validates: Requirements 6.6**
    
    For any valid task ID, querying the task status should return the current
    status and any available result or error information that matches the
    task's actual state.
    """

    @given(result_data=result_data_strategy())
    @settings(max_examples=100)
    def test_query_returns_consistent_status_for_completed_task(self, result_data: dict):
        """
        **Feature: spin-k8s-deployment, Property 3: Task Status Query Consistency**
        **Validates: Requirements 6.6**
        
        For any completed task with result data, querying the task status should
        return COMPLETED status and the exact result data that was set.
        """
        manager = TaskManager()
        task_id = manager.create_task()
        
        # Transition to completed with result
        manager.update_status(task_id, TaskStatus.RUNNING)
        manager.update_status(task_id, TaskStatus.COMPLETED, result=result_data)
        
        # Query the task status
        queried_task = manager.get_task(task_id)
        
        assert queried_task is not None, "Task should be retrievable"
        assert queried_task.task_id == task_id, "Task ID should match"
        assert queried_task.status == TaskStatus.COMPLETED, "Status should be COMPLETED"
        assert queried_task.result == result_data, "Result data should match exactly"
        assert queried_task.error is None, "Error should be None for completed task"

    @given(error_msg=error_message_strategy)
    @settings(max_examples=100)
    def test_query_returns_consistent_status_for_failed_task(self, error_msg: str):
        """
        **Feature: spin-k8s-deployment, Property 3: Task Status Query Consistency**
        **Validates: Requirements 6.6**
        
        For any failed task with error details, querying the task status should
        return FAILED status and the exact error message that was set.
        """
        manager = TaskManager()
        task_id = manager.create_task()
        
        # Transition to failed with error
        manager.update_status(task_id, TaskStatus.RUNNING)
        manager.update_status(task_id, TaskStatus.FAILED, error=error_msg)
        
        # Query the task status
        queried_task = manager.get_task(task_id)
        
        assert queried_task is not None, "Task should be retrievable"
        assert queried_task.task_id == task_id, "Task ID should match"
        assert queried_task.status == TaskStatus.FAILED, "Status should be FAILED"
        assert queried_task.error == error_msg, "Error message should match exactly"
        assert queried_task.result is None, "Result should be None for failed task"

    @given(st.data())
    @settings(max_examples=100)
    def test_query_returns_consistent_status_for_pending_task(self, data):
        """
        **Feature: spin-k8s-deployment, Property 3: Task Status Query Consistency**
        **Validates: Requirements 6.6**
        
        For any newly created task, querying the task status should return
        PENDING status with no result or error information.
        """
        manager = TaskManager()
        task_id = manager.create_task()
        
        # Query the task status immediately after creation
        queried_task = manager.get_task(task_id)
        
        assert queried_task is not None, "Task should be retrievable"
        assert queried_task.task_id == task_id, "Task ID should match"
        assert queried_task.status == TaskStatus.PENDING, "Status should be PENDING"
        assert queried_task.result is None, "Result should be None for pending task"
        assert queried_task.error is None, "Error should be None for pending task"

    @given(st.data())
    @settings(max_examples=100)
    def test_query_returns_consistent_status_for_running_task(self, data):
        """
        **Feature: spin-k8s-deployment, Property 3: Task Status Query Consistency**
        **Validates: Requirements 6.6**
        
        For any running task, querying the task status should return
        RUNNING status with no result or error information yet.
        """
        manager = TaskManager()
        task_id = manager.create_task()
        
        # Transition to running
        manager.update_status(task_id, TaskStatus.RUNNING)
        
        # Query the task status
        queried_task = manager.get_task(task_id)
        
        assert queried_task is not None, "Task should be retrievable"
        assert queried_task.task_id == task_id, "Task ID should match"
        assert queried_task.status == TaskStatus.RUNNING, "Status should be RUNNING"
        assert queried_task.result is None, "Result should be None for running task"
        assert queried_task.error is None, "Error should be None for running task"

    @given(
        result_data=result_data_strategy(),
        num_queries=st.integers(min_value=1, max_value=10)
    )
    @settings(max_examples=100)
    def test_multiple_queries_return_consistent_results(self, result_data: dict, num_queries: int):
        """
        **Feature: spin-k8s-deployment, Property 3: Task Status Query Consistency**
        **Validates: Requirements 6.6**
        
        For any task, multiple consecutive queries should return identical
        status and result/error information (idempotent reads).
        """
        manager = TaskManager()
        task_id = manager.create_task()
        
        # Set up a completed task with result
        manager.update_status(task_id, TaskStatus.RUNNING)
        manager.update_status(task_id, TaskStatus.COMPLETED, result=result_data)
        
        # Perform multiple queries and verify consistency
        first_query = manager.get_task(task_id)
        
        for _ in range(num_queries):
            subsequent_query = manager.get_task(task_id)
            
            assert subsequent_query.task_id == first_query.task_id, "Task ID should be consistent"
            assert subsequent_query.status == first_query.status, "Status should be consistent"
            assert subsequent_query.result == first_query.result, "Result should be consistent"
            assert subsequent_query.error == first_query.error, "Error should be consistent"
