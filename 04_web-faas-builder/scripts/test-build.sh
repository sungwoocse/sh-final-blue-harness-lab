#!/bin/bash
# Build API 테스트
# Usage: ./scripts/test-build.sh [WORKSPACE_ID] [APP_NAME]
#
# BASE_URL 설정 방법:
#   export BLUE_FAAS_URL=https://your-api-url.com
#   ./scripts/test-build.sh

BASE_URL="${BLUE_FAAS_URL:?Error: BLUE_FAAS_URL 환경변수를 설정하세요. 예: export BLUE_FAAS_URL=https://builder.eunha.icu}"
WORKSPACE_ID="${1:-test-workspace}"
APP_NAME="${2:-test-app}"

echo "=========================================="
echo "2. Build API"
echo "=========================================="
echo "▶ Request: POST $BASE_URL/api/v1/build"
echo "  Form Data:"
echo "    - file: test_app.py"
echo "    - workspace_id: $WORKSPACE_ID"
echo "    - app_name: $APP_NAME"
echo ""

# Create test file
TMP_FILE=$(mktemp /tmp/test_app_XXXXXX.py)
cat > "$TMP_FILE" << 'EOF'
from spin_sdk.http import Response

def handle_request(request):
    return Response(200, {"content-type": "text/plain"}, b"Hello from Blue FaaS!")
EOF

echo "◀ Response:"
RESPONSE=$(curl -s -X POST "$BASE_URL/api/v1/build" \
  -F "file=@$TMP_FILE" \
  -F "workspace_id=$WORKSPACE_ID" \
  -F "app_name=$APP_NAME")

echo "$RESPONSE" | python3 -m json.tool

# Extract task_id for follow-up
TASK_ID=$(echo "$RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin).get('task_id', ''))" 2>/dev/null)

if [ -n "$TASK_ID" ]; then
    echo ""
    echo "▶ Task ID: $TASK_ID"
    echo "▶ Check status: curl -s '$BASE_URL/api/v1/tasks/$TASK_ID?workspace_id=$WORKSPACE_ID'"
fi

# Cleanup
rm -f "$TMP_FILE"
echo ""
