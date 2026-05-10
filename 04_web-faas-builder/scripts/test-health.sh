#!/bin/bash
# Health Check API 테스트
# Usage: ./scripts/test-health.sh
#
# BASE_URL 설정 방법:
#   export BLUE_FAAS_URL=https://your-api-url.com
#   ./scripts/test-health.sh

BASE_URL="${BLUE_FAAS_URL:?Error: BLUE_FAAS_URL 환경변수를 설정하세요. 예: export BLUE_FAAS_URL=https://builder.eunha.icu}"

echo "=========================================="
echo "1. Health Check"
echo "=========================================="
echo "▶ Request: GET $BASE_URL/health"
echo ""
echo "◀ Response:"
curl -s "$BASE_URL/health" | python3 -m json.tool
echo ""
