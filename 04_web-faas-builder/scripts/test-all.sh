#!/bin/bash
# Blue FaaS API 전체 테스트 스크립트
# Usage: ./scripts/test-all.sh
#
# BASE_URL 설정 방법:
#   export BLUE_FAAS_URL=https://your-api-url.com
#   ./scripts/test-all.sh

set -e

BASE_URL="${BLUE_FAAS_URL:?Error: BLUE_FAAS_URL 환경변수를 설정하세요. 예: export BLUE_FAAS_URL=https://builder.eunha.icu}"
SCRIPTS_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "============================================"
echo "Blue FaaS API 전체 테스트"
echo "Base URL: $BASE_URL"
echo "============================================"
echo ""

# Run all tests
"$SCRIPTS_DIR/test-health.sh"
"$SCRIPTS_DIR/test-build.sh"
"$SCRIPTS_DIR/test-scaffold.sh"
"$SCRIPTS_DIR/test-deploy.sh"

echo "============================================"
echo "전체 테스트 완료!"
echo "============================================"
