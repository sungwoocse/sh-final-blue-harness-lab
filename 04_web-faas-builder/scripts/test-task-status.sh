#!/bin/bash
# Task Status API 테스트
# Usage: ./scripts/test-task-status.sh <TASK_ID> <WORKSPACE_ID>
#
# BASE_URL 설정 방법:
#   export BLUE_FAAS_URL=https://your-api-url.com
#   ./scripts/test-task-status.sh <task_id> <workspace_id>

BASE_URL="${BLUE_FAAS_URL:?Error: BLUE_FAAS_URL 환경변수를 설정하세요. 예: export BLUE_FAAS_URL=https://builder.eunha.icu}"
TASK_ID="${1:?Error: TASK_ID is required}"
WORKSPACE_ID="${2:?Error: WORKSPACE_ID is required}"

echo "=========================================="
echo "Task Status API"
echo "=========================================="
echo "▶ Request: GET $BASE_URL/api/v1/tasks/$TASK_ID?workspace_id=$WORKSPACE_ID"
echo ""
echo "◀ Response:"
curl -s "$BASE_URL/api/v1/tasks/$TASK_ID?workspace_id=$WORKSPACE_ID" | python3 -m json.tool
echo ""
