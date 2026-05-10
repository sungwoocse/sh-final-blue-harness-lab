#!/bin/bash
#
# ALB 라우팅 삭제 스크립트
# 사용법: ./remove-alb-route.sh <namespace> <service-name> <host>
#
# 예시: ./remove-alb-route.sh production backend b.eunha.icu
#

set -e

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# 설정
ALB_NAME="blue-final-alb"
REGION="ap-northeast-2"

# 파라미터 확인
if [ $# -lt 3 ]; then
    echo -e "${RED}사용법: $0 <namespace> <service-name> <host>${NC}"
    echo ""
    echo "예시:"
    echo "  $0 production backend api.example.com"
    exit 1
fi

NAMESPACE=$1
SERVICE_NAME=$2
HOST=$3
TG_NAME="kops-${SERVICE_NAME:0:20}-tg"

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN} ALB 라우팅 삭제 스크립트${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

# 1. ALB 정보 확인
echo -e "${YELLOW}[1/4] ALB 정보 확인...${NC}"
ALB_ARN=$(aws elbv2 describe-load-balancers --names "$ALB_NAME" --query 'LoadBalancers[0].LoadBalancerArn' --output text --region $REGION 2>/dev/null)
LISTENER_ARN=$(aws elbv2 describe-listeners --load-balancer-arn "$ALB_ARN" --query 'Listeners[?Port==`80`].ListenerArn' --output text --region $REGION)

# 2. 리스너 규칙 삭제
echo -e "${YELLOW}[2/4] 리스너 규칙 삭제...${NC}"
RULE_ARN=$(aws elbv2 describe-rules --listener-arn "$LISTENER_ARN" --query "Rules[?Conditions[?Values[?contains(@, '$HOST')]]].RuleArn" --output text --region $REGION 2>/dev/null || echo "")

if [ -n "$RULE_ARN" ] && [ "$RULE_ARN" != "None" ]; then
    aws elbv2 delete-rule --rule-arn "$RULE_ARN" --region $REGION
    echo "  규칙 삭제됨: $RULE_ARN"
else
    echo "  삭제할 규칙 없음"
fi

# 3. TargetGroupBinding 삭제
echo -e "${YELLOW}[3/4] TargetGroupBinding 삭제...${NC}"
kubectl delete targetgroupbinding ${SERVICE_NAME}-tgb -n $NAMESPACE 2>/dev/null && echo "  TargetGroupBinding 삭제됨" || echo "  TargetGroupBinding 없음"

# 4. 타겟 그룹 삭제
echo -e "${YELLOW}[4/4] 타겟 그룹 삭제...${NC}"
TG_ARN=$(aws elbv2 describe-target-groups --names "$TG_NAME" --query 'TargetGroups[0].TargetGroupArn' --output text --region $REGION 2>/dev/null || echo "")

if [ -n "$TG_ARN" ] && [ "$TG_ARN" != "None" ]; then
    aws elbv2 delete-target-group --target-group-arn "$TG_ARN" --region $REGION
    echo "  타겟 그룹 삭제됨: $TG_NAME"
else
    echo "  타겟 그룹 없음"
fi

echo ""
echo -e "${GREEN}완료!${NC}"
