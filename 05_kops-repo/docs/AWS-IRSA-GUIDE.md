# AWS 서비스 접근 및 IRSA 가이드

## 개요

kOps 클러스터에서 Pod가 AWS 서비스(S3, DynamoDB 등)에 접근하는 방법을 설명합니다.
IRSA(IAM Roles for Service Accounts)를 사용하면 hostNetwork 없이도 안전하게 AWS 서비스에 접근할 수 있습니다.

## 아키텍처

```
┌─────────────────────────────────────────────────────────────────┐
│                         AWS Cloud                                │
│                                                                  │
│  ┌─────────────────┐     ┌─────────────────┐                    │
│  │   OIDC Provider │     │    IAM Role     │                    │
│  │  (S3 bucket)    │────▶│ (Trust Policy)  │                    │
│  └─────────────────┘     └────────┬────────┘                    │
│                                   │                              │
│                                   ▼                              │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │                  Kubernetes Cluster                      │    │
│  │                                                          │    │
│  │  ┌──────────────────┐    ┌──────────────────────────┐   │    │
│  │  │ Pod Identity     │    │ Pod                       │   │    │
│  │  │ Webhook          │───▶│ - AWS_ROLE_ARN           │   │    │
│  │  │ (Mutating)       │    │ - AWS_WEB_IDENTITY_TOKEN │   │    │
│  │  └──────────────────┘    │ - Token Volume Mount     │   │    │
│  │                          └──────────────────────────┘   │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                   │                              │
│                    ┌──────────────┼──────────────┐               │
│                    ▼              ▼              ▼               │
│              ┌─────────┐   ┌───────────┐   ┌─────────┐          │
│              │   S3    │   │ DynamoDB  │   │   SQS   │          │
│              └─────────┘   └───────────┘   └─────────┘          │
└─────────────────────────────────────────────────────────────────┘
```

## 사전 요구사항

### kOps 클러스터 설정 (cluster.yaml)

```yaml
spec:
  # IRSA 활성화
  iam:
    allowContainerRegistry: true
    legacy: false
    useServiceAccountExternalPermissions: true

  # OIDC Provider 설정
  serviceAccountIssuerDiscovery:
    discoveryStore: s3://YOUR-OIDC-BUCKET/cluster-name/discovery/cluster-name
    enableAWSOIDCProvider: true

  # 필수 애드온
  certManager:
    enabled: true

  podIdentityWebhook:
    enabled: true  # Pod Identity Webhook 활성화
```

## IRSA 설정 방법

### Step 1: IAM Role 생성

```bash
# 변수 설정
ACCOUNT_ID="217350599014"
OIDC_PROVIDER="sfbank-blue-kops-oidc-store.s3.ap-northeast-2.amazonaws.com/sfbank-blue.k8s.local/discovery/sfbank-blue.k8s.local"
NAMESPACE="default"
SA_NAME="my-app-sa"
ROLE_NAME="my-app-role"

# Trust Policy 생성
cat > trust-policy.json << EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Federated": "arn:aws:iam::${ACCOUNT_ID}:oidc-provider/${OIDC_PROVIDER}"
      },
      "Action": "sts:AssumeRoleWithWebIdentity",
      "Condition": {
        "StringEquals": {
          "${OIDC_PROVIDER}:sub": "system:serviceaccount:${NAMESPACE}:${SA_NAME}"
        }
      }
    }
  ]
}
EOF

# IAM Role 생성
aws iam create-role \
  --role-name ${ROLE_NAME} \
  --assume-role-policy-document file://trust-policy.json
```

### Step 2: 서비스별 정책 연결

#### S3 정책

```bash
BUCKET_NAME="my-bucket"

cat > s3-policy.json << EOF
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "s3:GetObject",
                "s3:PutObject",
                "s3:DeleteObject",
                "s3:ListBucket"
            ],
            "Resource": [
                "arn:aws:s3:::${BUCKET_NAME}",
                "arn:aws:s3:::${BUCKET_NAME}/*"
            ]
        }
    ]
}
EOF

aws iam put-role-policy \
  --role-name ${ROLE_NAME} \
  --policy-name s3-access \
  --policy-document file://s3-policy.json
```

#### DynamoDB 정책

```bash
TABLE_NAME="my-table"

cat > dynamodb-policy.json << EOF
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "dynamodb:PutItem",
                "dynamodb:GetItem",
                "dynamodb:UpdateItem",
                "dynamodb:DeleteItem",
                "dynamodb:Scan",
                "dynamodb:Query",
                "dynamodb:DescribeTable"
            ],
            "Resource": "arn:aws:dynamodb:ap-northeast-2:${ACCOUNT_ID}:table/${TABLE_NAME}"
        }
    ]
}
EOF

aws iam put-role-policy \
  --role-name ${ROLE_NAME} \
  --policy-name dynamodb-access \
  --policy-document file://dynamodb-policy.json
```

### Step 3: Kubernetes ServiceAccount 생성

```bash
# ServiceAccount 생성
kubectl create serviceaccount ${SA_NAME} -n ${NAMESPACE}

# IAM Role 연결
kubectl annotate serviceaccount ${SA_NAME} -n ${NAMESPACE} \
  eks.amazonaws.com/role-arn=arn:aws:iam::${ACCOUNT_ID}:role/${ROLE_NAME}
```

### Step 4: Pod에서 사용

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: my-app
spec:
  serviceAccountName: my-app-sa  # IRSA ServiceAccount
  containers:
  - name: app
    image: amazon/aws-cli:latest
    command: ["sleep", "infinity"]
```

## 테스트 결과

### 현재 클러스터 설정

| 항목 | 값 |
|------|-----|
| OIDC Provider | `sfbank-blue-kops-oidc-store.s3.ap-northeast-2.amazonaws.com/...` |
| IAM Role | `kops-s3-test-role` |
| ServiceAccount | `s3-access-sa` (default namespace) |

### S3 테스트

| 작업 | 명령어 | 결과 |
|------|--------|------|
| 업로드 | `aws s3 cp file s3://bucket/` | 성공 |
| 목록 조회 | `aws s3 ls s3://bucket/` | 성공 |
| 다운로드 | `aws s3 cp s3://bucket/file .` | 성공 |
| 삭제 | `aws s3 rm s3://bucket/file` | 성공 |

**테스트 버킷**: `kops-test-bucket-sfbank-1764573118`

### DynamoDB 테스트

| 작업 | 명령어 | 결과 |
|------|--------|------|
| PutItem | `aws dynamodb put-item` | 성공 |
| GetItem | `aws dynamodb get-item` | 성공 |
| UpdateItem | `aws dynamodb update-item` | 성공 |
| Scan | `aws dynamodb scan` | 성공 |
| DeleteItem | `aws dynamodb delete-item` | 성공 |

**테스트 테이블**: `kops-test-table-1764577194`

## IRSA 동작 확인

Pod 생성 시 자동으로 주입되는 환경변수:

```bash
$ kubectl exec my-pod -- env | grep AWS

AWS_STS_REGIONAL_ENDPOINTS=regional
AWS_DEFAULT_REGION=ap-northeast-2
AWS_REGION=ap-northeast-2
AWS_ROLE_ARN=arn:aws:iam::217350599014:role/kops-s3-test-role
AWS_WEB_IDENTITY_TOKEN_FILE=/var/run/secrets/eks.amazonaws.com/serviceaccount/token
```

## IRSA vs 다른 방식 비교

| 방식 | 보안 | 권한 범위 | 설정 복잡도 | 권장 |
|------|------|----------|------------|------|
| **IRSA** | 높음 | ServiceAccount별 | 중간 | **프로덕션 권장** |
| hostNetwork | 낮음 | 노드 전체 권한 | 낮음 | 테스트용 |
| Access Key | 낮음 | 키별 | 낮음 | 비권장 |

### IRSA 장점

1. **최소 권한 원칙**: Pod별로 필요한 권한만 부여
2. **자동 자격증명 갱신**: 토큰이 자동으로 갱신됨
3. **감사 추적**: CloudTrail에서 어떤 Pod가 API를 호출했는지 추적 가능
4. **보안**: Access Key를 코드나 환경변수에 저장할 필요 없음

## 트러블슈팅

### 1. "Unable to locate credentials" 오류

**원인**: Pod Identity Webhook이 환경변수를 주입하지 못함

**해결**:
```bash
# Pod Identity Webhook 확인
kubectl get pods -n kube-system | grep pod-identity

# Webhook 설정 확인
kubectl get mutatingwebhookconfigurations | grep identity

# 모든 Pod 재시작
kubectl rollout restart deployment -n kube-system
```

### 2. "AccessDenied" 오류

**원인**: IAM Role에 권한이 없거나 Trust Policy가 잘못됨

**확인**:
```bash
# Trust Policy 확인
aws iam get-role --role-name <role-name> --query 'Role.AssumeRolePolicyDocument'

# ServiceAccount annotation 확인
kubectl get sa <sa-name> -o yaml | grep eks.amazonaws.com

# 정책 확인
aws iam list-role-policies --role-name <role-name>
```

### 3. 환경변수가 주입되지 않음

**원인**: ServiceAccount annotation이 없거나 Pod Identity Webhook이 미설치

**해결**:
```bash
# annotation 재설정
kubectl annotate serviceaccount <sa-name> \
  eks.amazonaws.com/role-arn=arn:aws:iam::<account>:role/<role> \
  --overwrite

# Pod 재생성
kubectl delete pod <pod-name>
```

### 4. Pod Identity Webhook이 없음

**해결**:
```yaml
# cluster.yaml에 추가
spec:
  podIdentityWebhook:
    enabled: true
```

```bash
kops replace -f cluster.yaml --state=s3://...
kops update cluster --yes --state=s3://...
kubectl rollout restart deployment -n kube-system
```

## 정리 명령어

```bash
# ServiceAccount 삭제
kubectl delete sa s3-access-sa -n default

# IAM Role 정책 삭제
aws iam delete-role-policy --role-name kops-s3-test-role --policy-name s3-access
aws iam delete-role-policy --role-name kops-s3-test-role --policy-name dynamodb-access

# IAM Role 삭제
aws iam delete-role --role-name kops-s3-test-role

# S3 버킷 삭제
aws s3 rb s3://kops-test-bucket-sfbank-1764573118

# DynamoDB 테이블 삭제
aws dynamodb delete-table --table-name kops-test-table-1764577194 --region ap-northeast-2
```

## 참고 자료

- [kOps IRSA Documentation](https://kops.sigs.k8s.io/addons/#pod-identity-webhook)
- [AWS IRSA Documentation](https://docs.aws.amazon.com/eks/latest/userguide/iam-roles-for-service-accounts.html)
- [Pod Identity Webhook](https://github.com/aws/amazon-eks-pod-identity-webhook)
