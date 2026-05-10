#!/bin/bash
# Workspace Tasks API 테스트
# Usage: ./scripts/test-workspace-tasks.sh <WORKSPACE_ID>
#
# BASE_URL 설정 방법:
#   export BLUE_FAAS_URL=https://your-api-url.com
#   ./scripts/test-workspace-tasks.sh <workspace_id>

BASE_URL="${BLUE_FAAS_URL:?Error: BLUE_FAAS_URL 환경변수를 설정하세요. 예: export BLUE_FAAS_URL=https://builder.eunha.icu}"
WORKSPACE_ID="${1:?Error: WORKSPACE_ID is required}"

echo "=========================================="
echo "Workspace Tasks API"
echo "=========================================="
echo "▶ Request: GET $BASE_URL/api/v1/workspaces/$WORKSPACE_ID/tasks"
echo ""
echo "◀ Response:"
curl -s "$BASE_URL/api/v1/workspaces/$WORKSPACE_ID/tasks" | python3 -m json.tool
echo ""
