#!/bin/bash
#
# 기존 ALB에 새로운 서비스 라우팅 추가 스크립트
# 사용법: ./add-alb-route.sh <namespace> <service-name> <host> <node-port> [priority]
#
# 예시: ./add-alb-route.sh production backend b.eunha.icu 30081 10
#

set -e

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 설정 (필요시 수정)
ALB_NAME="blue-final-alb"
VPC_ID="vpc-03b6863c762b38258"
ALB_SG="sg-036d778d80ba9e20c"
NODE_SG="sg-0f8d6091ab9319761"
REGION="ap-northeast-2"
CLUSTER_NAME="sfbank-blue.k8s.local"

# 파라미터 확인
if [ $# -lt 4 ]; then
    echo -e "${RED}사용법: $0 <namespace> <service-name> <host> <node-port> [priority]${NC}"
    echo ""
    echo "파라미터:"
    echo "  namespace    - Kubernetes 네임스페이스"
    echo "  service-name - Kubernetes 서비스 이름"
    echo "  host         - 라우팅할 호스트 (예: api.example.com)"
    echo "  node-port    - NodePort 포트 번호 (30000-32767)"
    echo "  priority     - (선택) 리스너 규칙 우선순위 (기본: 자동)"
    echo ""
    echo "예시:"
    echo "  $0 production backend api.example.com 30081"
    echo "  $0 staging frontend staging.example.com 30082 20"
    exit 1
fi

NAMESPACE=$1
SERVICE_NAME=$2
HOST=$3
NODE_PORT=$4
PRIORITY=${5:-""}

# 타겟 그룹 이름 생성 (32자 제한)
TG_NAME="kops-${SERVICE_NAME:0:20}-tg"

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN} ALB 라우팅 추가 스크립트${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo "설정:"
echo "  - Namespace: $NAMESPACE"
echo "  - Service: $SERVICE_NAME"
echo "  - Host: $HOST"
echo "  - NodePort: $NODE_PORT"
echo "  - Target Group: $TG_NAME"
echo ""

# 1. ALB 정보 확인
echo -e "${YELLOW}[1/6] ALB 정보 확인...${NC}"
ALB_ARN=$(aws elbv2 describe-load-balancers --names "$ALB_NAME" --query 'LoadBalancers[0].LoadBalancerArn' --output text --region $REGION 2>/dev/null)
if [ -z "$ALB_ARN" ] || [ "$ALB_ARN" == "None" ]; then
    echo -e "${RED}오류: ALB '$ALB_NAME'를 찾을 수 없습니다.${NC}"
    exit 1
fi
ALB_DNS=$(aws elbv2 describe-load-balancers --names "$ALB_NAME" --query 'LoadBalancers[0].DNSName' --output text --region $REGION)
echo "  ALB ARN: $ALB_ARN"
echo "  ALB DNS: $ALB_DNS"

# 2. 리스너 ARN 확인
LISTENER_ARN=$(aws elbv2 describe-listeners --load-balancer-arn "$ALB_ARN" --query 'Listeners[?Port==`80`].ListenerArn' --output text --region $REGION)
if [ -z "$LISTENER_ARN" ] || [ "$LISTENER_ARN" == "None" ]; then
    echo -e "${RED}오류: HTTP(80) 리스너를 찾을 수 없습니다.${NC}"
    exit 1
fi
echo "  Listener ARN: $LISTENER_ARN"

# 3. 타겟 그룹 생성
echo ""
echo -e "${YELLOW}[2/6] 타겟 그룹 생성...${NC}"
TG_ARN=$(aws elbv2 describe-target-groups --names "$TG_NAME" --query 'TargetGroups[0].TargetGroupArn' --output text --region $REGION 2>/dev/null || echo "")

if [ -z "$TG_ARN" ] || [ "$TG_ARN" == "None" ]; then
    TG_RESULT=$(aws elbv2 create-target-group \
        --name "$TG_NAME" \
        --protocol HTTP \
        --port "$NODE_PORT" \
        --vpc-id "$VPC_ID" \
        --target-type instance \
        --health-check-path / \
        --health-check-interval-seconds 30 \
        --healthy-threshold-count 2 \
        --unhealthy-threshold-count 3 \
        --region $REGION)
    TG_ARN=$(echo "$TG_RESULT" | jq -r '.TargetGroups[0].TargetGroupArn')
    echo "  타겟 그룹 생성됨: $TG_ARN"
else
    echo "  기존 타겟 그룹 사용: $TG_ARN"
fi

# 4. 보안 그룹 규칙 추가
echo ""
echo -e "${YELLOW}[3/6] 보안 그룹 규칙 추가...${NC}"
aws ec2 authorize-security-group-ingress \
    --group-id "$NODE_SG" \
    --protocol tcp \
    --port "$NODE_PORT" \
    --source-group "$ALB_SG" \
    --region $REGION 2>/dev/null && echo "  보안 그룹 규칙 추가됨" || echo "  보안 그룹 규칙이 이미 존재함"

# 5. 리스너 규칙 추가
echo ""
echo -e "${YELLOW}[4/6] 리스너 규칙 추가 (Host: $HOST)...${NC}"

# 우선순위 자동 계산
if [ -z "$PRIORITY" ]; then
    EXISTING_PRIORITIES=$(aws elbv2 describe-rules --listener-arn "$LISTENER_ARN" --query 'Rules[?!IsDefault].Priority' --output text --region $REGION | tr '\t' '\n' | sort -n)
    PRIORITY=10
    while echo "$EXISTING_PRIORITIES" | grep -q "^$PRIORITY$"; do
        PRIORITY=$((PRIORITY + 10))
    done
    echo "  자동 할당된 우선순위: $PRIORITY"
fi

# 기존 규칙 확인 (같은 호스트)
EXISTING_RULE=$(aws elbv2 describe-rules --listener-arn "$LISTENER_ARN" --query "Rules[?Conditions[?Values[?contains(@, '$HOST')]]].RuleArn" --output text --region $REGION 2>/dev/null || echo "")

if [ -n "$EXISTING_RULE" ] && [ "$EXISTING_RULE" != "None" ]; then
    echo "  기존 규칙 삭제 중..."
    aws elbv2 delete-rule --rule-arn "$EXISTING_RULE" --region $REGION
fi

aws elbv2 create-rule \
    --listener-arn "$LISTENER_ARN" \
    --priority "$PRIORITY" \
    --conditions "Field=host-header,Values=$HOST" \
    --actions "Type=forward,TargetGroupArn=$TG_ARN" \
    --region $REGION > /dev/null
echo "  리스너 규칙 추가됨 (Priority: $PRIORITY)"

# 6. 타겟 등록
echo ""
echo -e "${YELLOW}[5/6] 타겟 등록...${NC}"
WORKER_IDS=$(aws ec2 describe-instances \
    --filters "Name=tag:k8s.io/role/node,Values=1" \
              "Name=tag:kubernetes.io/cluster/$CLUSTER_NAME,Values=owned" \
              "Name=instance-state-name,Values=running" \
    --query 'Reservations[*].Instances[*].InstanceId' \
    --output text --region $REGION | tr '\n' ' ')

TARGETS=""
for ID in $WORKER_IDS; do
    TARGETS="$TARGETS Id=$ID,Port=$NODE_PORT"
done

aws elbv2 register-targets --target-group-arn "$TG_ARN" --targets $TARGETS --region $REGION
echo "  등록된 타겟: $WORKER_IDS"

# 7. TargetGroupBinding 생성 (Kubernetes)
echo ""
echo -e "${YELLOW}[6/6] TargetGroupBinding 생성...${NC}"
kubectl apply -f - <<EOF
apiVersion: elbv2.k8s.aws/v1beta1
kind: TargetGroupBinding
metadata:
  name: ${SERVICE_NAME}-tgb
  namespace: ${NAMESPACE}
spec:
  serviceRef:
    name: ${SERVICE_NAME}
    port: 80
  targetGroupARN: ${TG_ARN}
  targetType: instance
EOF

# 완료
echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN} 완료!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo "라우팅 설정:"
echo "  Host: $HOST"
echo "  → ALB: $ALB_DNS"
echo "  → Target Group: $TG_NAME"
echo "  → NodePort: $NODE_PORT"
echo "  → Service: $NAMESPACE/$SERVICE_NAME"
echo ""
echo "DNS 설정:"
echo "  $HOST → CNAME → $ALB_DNS"
echo ""
echo "테스트:"
echo "  curl -H \"Host: $HOST\" http://$ALB_DNS/"
