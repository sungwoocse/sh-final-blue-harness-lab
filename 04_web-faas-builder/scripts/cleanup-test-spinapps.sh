#!/bin/bash
# 테스트용 SpinApp 정리 스크립트
# Usage: ./scripts/cleanup-test-spinapps.sh [NAMESPACE]

NAMESPACE="${1:-default}"

echo "=========================================="
echo "테스트용 SpinApp 정리"
echo "Namespace: $NAMESPACE"
echo "=========================================="

# List SpinApps with faas=true label
echo "▶ FaaS SpinApps 목록:"
kubectl get spinapp -n "$NAMESPACE" -l faas=true -o custom-columns=NAME:.metadata.name,FUNCTION_ID:.spec.podLabels.function_id,AGE:.metadata.creationTimestamp 2>/dev/null

echo ""
read -p "위 SpinApp들을 모두 삭제하시겠습니까? (y/N): " confirm

if [[ "$confirm" =~ ^[Yy]$ ]]; then
    echo ""
    echo "▶ 삭제 중..."
    kubectl delete spinapp -n "$NAMESPACE" -l faas=true
    echo ""
    echo "✅ 정리 완료!"
else
    echo ""
    echo "취소되었습니다."
fi
