#!/bin/bash
# ECR에 백엔드 이미지 업로드 스크립트

set -e  # 에러 시 중단

# 색상 코드
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}=== FaaS Backend ECR Upload ===${NC}\n"

# 1. AWS Account ID 확인
echo -e "${YELLOW}[1/6] AWS Account ID 확인 중...${NC}"
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text 2>/dev/null)

if [ -z "$AWS_ACCOUNT_ID" ]; then
    echo -e "${RED}❌ AWS CLI 설정이 필요합니다.${NC}"
    echo "aws configure를 먼저 실행하세요."
    exit 1
fi

echo -e "${GREEN}✓ AWS Account ID: $AWS_ACCOUNT_ID${NC}\n"

# 변수 설정
AWS_REGION=ap-northeast-2
REPO_NAME=faas-backend
IMAGE_NAME=faas-backend
ECR_URL=$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com

# 2. ECR 로그인
echo -e "${YELLOW}[2/6] ECR 로그인 중...${NC}"
aws ecr get-login-password --region $AWS_REGION | \
  docker login --username AWS --password-stdin $ECR_URL

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ ECR 로그인 성공${NC}\n"
else
    echo -e "${RED}❌ ECR 로그인 실패${NC}"
    exit 1
fi

# 3. ECR 리포지토리 확인 및 생성
echo -e "${YELLOW}[3/6] ECR 리포지토리 확인 중...${NC}"
aws ecr describe-repositories --repository-names $REPO_NAME --region $AWS_REGION > /dev/null 2>&1

if [ $? -ne 0 ]; then
    echo -e "${YELLOW}리포지토리가 없습니다. 생성 중...${NC}"
    aws ecr create-repository \
      --repository-name $REPO_NAME \
      --region $AWS_REGION \
      --image-scanning-configuration scanOnPush=true
    echo -e "${GREEN}✓ 리포지토리 생성 완료${NC}\n"
else
    echo -e "${GREEN}✓ 리포지토리가 이미 존재합니다${NC}\n"
fi

# 4. Docker 이미지 빌드
echo -e "${YELLOW}[4/6] Docker 이미지 빌드 중...${NC}"
cd "$(dirname "$0")"  # backend 디렉토리로 이동
docker build -t $IMAGE_NAME:latest .

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ 이미지 빌드 성공${NC}\n"
else
    echo -e "${RED}❌ 이미지 빌드 실패${NC}"
    exit 1
fi

# 5. 이미지 태그
echo -e "${YELLOW}[5/6] 이미지 태그 지정 중...${NC}"
docker tag $IMAGE_NAME:latest $ECR_URL/$REPO_NAME:latest
echo -e "${GREEN}✓ 태그 지정 완료${NC}\n"

# 6. ECR에 푸시
echo -e "${YELLOW}[6/6] ECR에 푸시 중...${NC}"
docker push $ECR_URL/$REPO_NAME:latest

if [ $? -eq 0 ]; then
    echo -e "\n${GREEN}================================${NC}"
    echo -e "${GREEN}✓ ECR 업로드 완료!${NC}"
    echo -e "${GREEN}================================${NC}\n"
    echo -e "이미지 URL:"
    echo -e "${YELLOW}$ECR_URL/$REPO_NAME:latest${NC}\n"
    echo -e "인프라 엔지니어에게 위 URL을 전달하세요."
else
    echo -e "${RED}❌ ECR 푸시 실패${NC}"
    exit 1
fi
