# Pre-Requirements (사전 준비 사항)

Terraform 실행 전에 아래 AWS 리소스들을 먼저 생성해야 합니다.

## 1. AWS CLI 설정

```bash
aws configure
# AWS Access Key ID: [your-access-key]
# AWS Secret Access Key: [your-secret-key]
# Default region name: ap-northeast-2
# Default output format: json
```

## 2. S3 Bucket (Terraform State 저장용)

```bash
aws s3 mb s3://softbank2025-blue-tfstate --region ap-northeast-2
```

버킷 버전 관리 활성화 (권장):
```bash
aws s3api put-bucket-versioning \
  --bucket softbank2025-blue-tfstate \
  --versioning-configuration Status=Enabled
```

## 3. DynamoDB Table (State Locking용)

```bash
aws dynamodb create-table \
  --table-name softbank2025-blue-tfstate-lock \
  --attribute-definitions AttributeName=LockID,AttributeType=S \
  --key-schema AttributeName=LockID,KeyType=HASH \
  --billing-mode PAY_PER_REQUEST \
  --region ap-northeast-2
```

테이블 생성 확인:
```bash
aws dynamodb describe-table --table-name softbank2025-blue-tfstate-lock --region ap-northeast-2
```

## 4. EC2 Key Pair (Bastion Host SSH 접속용)

```bash
aws ec2 create-key-pair \
  --key-name blue-key \
  --query 'KeyMaterial' \
  --output text \
  --region ap-northeast-2 > blue-key.pem

chmod 400 blue-key.pem
```

또는 AWS 콘솔에서 생성:
```
EC2 > Key Pairs > Create key pair
- Name: blue-key
- Type: RSA
- Format: .pem
```

## 5. ACM 인증서 (CloudFront용 - us-east-1 필수)

CloudFront를 사용하려면 **us-east-1** 리전에 ACM 인증서가 필요합니다.

```bash
# us-east-1에 인증서 요청
aws acm request-certificate \
  --domain-name "*.your-domain.com" \
  --validation-method DNS \
  --region us-east-1
```

또는 AWS 콘솔에서:
```
리전을 us-east-1 (버지니아)로 변경
ACM > Request certificate > Public certificate
```

인증서 ARN을 `variables.tf`의 `cloudfront_certificate_arn`에 설정하세요.

## 6. (선택) ALB용 ACM 인증서 (ap-northeast-2)

ALB에서 HTTPS를 사용하려면 **ap-northeast-2** 리전에 별도 인증서가 필요합니다.

```bash
aws acm request-certificate \
  --domain-name "*.your-domain.com" \
  --validation-method DNS \
  --region ap-northeast-2
```

## 체크리스트

| 항목 | 명령어 | 필수 |
|------|--------|------|
| AWS CLI 설정 | `aws sts get-caller-identity` | O |
| S3 버킷 | `aws s3 ls s3://softbank2025-blue-tfstate` | O |
| DynamoDB 테이블 | `aws dynamodb describe-table --table-name softbank2025-blue-tfstate-lock` | O |
| EC2 Key Pair | `aws ec2 describe-key-pairs --key-names blue-key` | Bastion 사용시 |
| ACM 인증서 (us-east-1) | `aws acm list-certificates --region us-east-1` | CloudFront 사용시 |

## 모두 완료 후

```bash
cd infra-iac
terraform init
terraform plan
terraform apply
```
