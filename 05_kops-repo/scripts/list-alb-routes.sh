#!/bin/bash
#
# ALB 라우팅 목록 조회 스크립트
# 사용법: ./list-alb-routes.sh
#

# 설정
ALB_NAME="blue-final-alb"
REGION="ap-northeast-2"

echo "========================================"
echo " ALB 라우팅 목록"
echo "========================================"
echo ""

# ALB 정보
ALB_ARN=$(aws elbv2 describe-load-balancers --names "$ALB_NAME" --query 'LoadBalancers[0].LoadBalancerArn' --output text --region $REGION)
ALB_DNS=$(aws elbv2 describe-load-balancers --names "$ALB_NAME" --query 'LoadBalancers[0].DNSName' --output text --region $REGION)

echo "ALB: $ALB_NAME"
echo "DNS: $ALB_DNS"
echo ""

# 리스너 정보
LISTENER_ARN=$(aws elbv2 describe-listeners --load-balancer-arn "$ALB_ARN" --query 'Listeners[?Port==`80`].ListenerArn' --output text --region $REGION)

echo "========== 라우팅 규칙 =========="
echo ""

# 규칙 목록
aws elbv2 describe-rules --listener-arn "$LISTENER_ARN" --region $REGION --query 'Rules[*].[Priority,Conditions[0].Values[0],Actions[0].TargetGroupArn]' --output text | while read PRIORITY HOST TG_ARN; do
    if [ "$PRIORITY" == "default" ]; then
        echo "[$PRIORITY] (기본) → $(echo $TG_ARN | awk -F'/' '{print $2}')"
    else
        TG_NAME=$(echo $TG_ARN | awk -F'/' '{print $2}')

        # 타겟 그룹 헬스 확인
        HEALTHY=$(aws elbv2 describe-target-health --target-group-arn "$TG_ARN" --query 'TargetHealthDescriptions[?TargetHealth.State==`healthy`] | length(@)' --output text --region $REGION 2>/dev/null || echo "?")
        TOTAL=$(aws elbv2 describe-target-health --target-group-arn "$TG_ARN" --query 'TargetHealthDescriptions | length(@)' --output text --region $REGION 2>/dev/null || echo "?")

        echo "[$PRIORITY] $HOST → $TG_NAME (healthy: $HEALTHY/$TOTAL)"
    fi
done

echo ""
echo "========== 타겟 그룹 상세 =========="
echo ""

aws elbv2 describe-target-groups --load-balancer-arn "$ALB_ARN" --query 'TargetGroups[*].[TargetGroupName,Port]' --output text --region $REGION | while read TG_NAME PORT; do
    echo "- $TG_NAME (Port: $PORT)"
done
