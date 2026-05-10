#!/bin/bash
# Scaffold API 테스트
# Usage: ./scripts/test-scaffold.sh [IMAGE_REF]
#
# BASE_URL 설정 방법:
#   export BLUE_FAAS_URL=https://your-api-url.com
#   ./scripts/test-scaffold.sh

BASE_URL="${BLUE_FAAS_URL:?Error: BLUE_FAAS_URL 환경변수를 설정하세요. 예: export BLUE_FAAS_URL=https://builder.eunha.icu}"
IMAGE_REF="${1:-ghcr.io/spinkube/containerd-shim-spin/examples/spin-rust-hello:v0.13.0}"

echo "=========================================="
echo "3. Scaffold API"
echo "=========================================="
echo "▶ Request: POST $BASE_URL/api/v1/scaffold"
echo "  Body:"
echo "    {"
echo "      \"image_ref\": \"$IMAGE_REF\","
echo "      \"replicas\": 1"
echo "    }"
echo ""
echo "◀ Response:"
curl -s -X POST "$BASE_URL/api/v1/scaffold" \
  -H "Content-Type: application/json" \
  -d "{\"image_ref\": \"$IMAGE_REF\", \"replicas\": 1}" | python3 -m json.tool
echo ""
