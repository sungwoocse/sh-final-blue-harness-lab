# Blue FaaS Kubernetes Deployment

## Prerequisites

1. EKS 클러스터에 IRSA(IAM Roles for Service Accounts) 설정
2. kubectl 및 kustomize 설치
3. ECR 레포지토리 생성

## IRSA 설정

### 1. IAM Policy 생성

```bash
aws iam create-policy \
  --policy-name blue-faas-policy \
  --policy-document file://iam-policy.json
```

### 2. IAM Role 생성 (IRSA)

```bash
eksctl create iamserviceaccount \
  --name blue-faas-sa \
  --namespace blue-faas \
  --cluster YOUR_CLUSTER_NAME \
  --attach-policy-arn arn:aws:iam::ACCOUNT_ID:policy/blue-faas-policy \
  --approve \
  --override-existing-serviceaccounts
```

또는 수동으로:

```bash
# Trust policy 생성
cat > trust-policy.json << EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Federated": "arn:aws:iam::ACCOUNT_ID:oidc-provider/oidc.eks.ap-northeast-2.amazonaws.com/id/OIDC_ID"
      },
      "Action": "sts:AssumeRoleWithWebIdentity",
      "Condition": {
        "StringEquals": {
          "oidc.eks.ap-northeast-2.amazonaws.com/id/OIDC_ID:sub": "system:serviceaccount:blue-faas:blue-faas-sa"
        }
      }
    }
  ]
}
EOF

# IAM Role 생성
aws iam create-role \
  --role-name blue-faas-irsa-role \
  --assume-role-policy-document file://trust-policy.json

# Policy 연결
aws iam attach-role-policy \
  --role-name blue-faas-irsa-role \
  --policy-arn arn:aws:iam::ACCOUNT_ID:policy/blue-faas-policy
```

### 3. ServiceAccount 업데이트

`serviceaccount.yaml`의 annotation에서 IAM Role ARN 업데이트:

```yaml
annotations:
  eks.amazonaws.com/role-arn: arn:aws:iam::ACCOUNT_ID:role/blue-faas-irsa-role
```

## 배포

### 1. 환경변수 설정

`configmap.yaml`에서 필요한 값 수정:

```yaml
data:
  DYNAMODB_TABLE_NAME: "sfbank-blue-FaaSData"
  S3_BUCKET_NAME: "sfbank-blue-functions-code-bucket"
  AWS_REGION: "ap-northeast-2"
```

### 2. 이미지 태그 설정

`kustomization.yaml`에서 이미지 태그 수정:

```yaml
images:
  - name: ACCOUNT_ID.dkr.ecr.ap-northeast-2.amazonaws.com/blue-faas
    newTag: v1.0.0
```

### 3. 배포 실행

```bash
# Dry-run으로 확인
kubectl apply -k . --dry-run=client

# 실제 배포
kubectl apply -k .

# 배포 상태 확인
kubectl -n blue-faas get pods
kubectl -n blue-faas get svc
kubectl -n blue-faas get ingress
```

### 4. 로그 확인

```bash
kubectl -n blue-faas logs -l app.kubernetes.io/name=blue-faas -f
```

## 환경별 설정

### Production

```bash
# kustomization.yaml 수정
images:
  - name: ACCOUNT_ID.dkr.ecr.ap-northeast-2.amazonaws.com/blue-faas
    newTag: v1.0.0-prod

# deployment.yaml 수정
replicas: 3
```

### Staging

```bash
# 별도 overlay 생성
mkdir -p overlays/staging
cat > overlays/staging/kustomization.yaml << EOF
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization
resources:
  - ../../
namePrefix: staging-
images:
  - name: ACCOUNT_ID.dkr.ecr.ap-northeast-2.amazonaws.com/blue-faas
    newTag: staging
EOF
```

## 트러블슈팅

### IRSA 권한 확인

```bash
# Pod에서 AWS 자격 증명 확인
kubectl -n blue-faas exec -it deploy/blue-faas -- env | grep AWS

# 예상 출력:
# AWS_ROLE_ARN=arn:aws:iam::ACCOUNT_ID:role/blue-faas-irsa-role
# AWS_WEB_IDENTITY_TOKEN_FILE=/var/run/secrets/eks.amazonaws.com/serviceaccount/token
```

### S3 접근 테스트

```bash
kubectl -n blue-faas exec -it deploy/blue-faas -- python -c "
import boto3
s3 = boto3.client('s3')
print(s3.list_buckets())
"
```

### DynamoDB 접근 테스트

```bash
kubectl -n blue-faas exec -it deploy/blue-faas -- python -c "
import boto3
dynamodb = boto3.client('dynamodb', region_name='ap-northeast-2')
print(dynamodb.describe_table(TableName='sfbank-blue-FaaSData'))
"
```
