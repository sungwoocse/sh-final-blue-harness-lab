#!/bin/bash
# Deploy API 테스트 (with function_id)
# Usage: ./scripts/test-deploy.sh [NAMESPACE] [FUNCTION_ID] [IMAGE_REF]
#
# BASE_URL 설정 방법:
#   export BLUE_FAAS_URL=https://your-api-url.com
#   ./scripts/test-deploy.sh

BASE_URL="${BLUE_FAAS_URL:?Error: BLUE_FAAS_URL 환경변수를 설정하세요. 예: export BLUE_FAAS_URL=https://builder.eunha.icu}"
NAMESPACE="${1:-default}"
FUNCTION_ID="${2:-fn-test-$(date +%s)}"
IMAGE_REF="${3:-ghcr.io/spinkube/containerd-shim-spin/examples/spin-rust-hello:v0.13.0}"

echo "=========================================="
echo "4. Deploy API (with function_id)"
echo "=========================================="
echo "▶ Request: POST $BASE_URL/api/v1/deploy"
echo "  Body:"
echo "    {"
echo "      \"namespace\": \"$NAMESPACE\","
echo "      \"image_ref\": \"$IMAGE_REF\","
echo "      \"function_id\": \"$FUNCTION_ID\","
echo "      \"enable_autoscaling\": false,"
echo "      \"replicas\": 1,"
echo "      \"use_spot\": false"
echo "    }"
echo ""
echo "◀ Response:"
RESPONSE=$(curl -s -X POST "$BASE_URL/api/v1/deploy" \
  -H "Content-Type: application/json" \
  -d "{\"namespace\":\"$NAMESPACE\",\"image_ref\":\"$IMAGE_REF\",\"function_id\":\"$FUNCTION_ID\",\"enable_autoscaling\":false,\"replicas\":1,\"use_spot\":false}")

echo "$RESPONSE" | python3 -m json.tool

# Extract app_name
APP_NAME=$(echo "$RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin).get('app_name', ''))" 2>/dev/null)

if [ -n "$APP_NAME" ]; then
    echo ""
    echo "=========================================="
    echo "5. Verify SpinApp & Pod Labels"
    echo "=========================================="
    echo "▶ SpinApp spec.podLabels:"
    kubectl get spinapp "$APP_NAME" -n "$NAMESPACE" -o jsonpath='{.spec.podLabels}' 2>/dev/null | python3 -m json.tool
    echo ""
    echo ""
    echo "▶ Pod with function_id=$FUNCTION_ID:"
    kubectl get pods -n "$NAMESPACE" -l "function_id=$FUNCTION_ID" -o wide 2>/dev/null
    echo ""
    echo "=========================================="
    echo "Cleanup command:"
    echo "  kubectl delete spinapp $APP_NAME -n $NAMESPACE"
    echo "=========================================="
fi
echo ""
