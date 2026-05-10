# Changelog

이 프로젝트의 주요 변경 사항을 기록합니다.

## [1.1.0] - 2025-11-30

### K3s Kubernetes 클러스터 추가

경량 Kubernetes 클러스터인 K3s를 Public Subnet에 배포하기 위한 모듈 추가

#### 구성 요소

| 리소스 | 타입 | 설명 |
|--------|------|------|
| K3s Master | m7i-flex.large | Control Plane (1대) |
| Worker-Wasm | m7i-flex.large | Wasm 워크로드 전용 |
| Worker-Build | m7i-flex.large | CI/CD 빌드 작업 |
| Worker-Observability | m7i-flex.large | 모니터링/로깅 |
| Worker-Infra | m7i-flex.large | 인프라 관리 도구 |

#### 추가된 파일

```
modules/k3s/
├── main.tf        # EC2 인스턴스 (Master, Workers), EIP
├── iam.tf         # IAM 역할 (Control Plane, Worker)
├── sg.tf          # 보안 그룹 (22, 80, 443, 6443, 30000-32767)
├── variables.tf   # 모듈 변수
├── outputs.tf     # 출력값
└── versions.tf    # Provider 버전
```

#### IAM 권한

**Control Plane:**
- EC2 Describe/Create/Modify/Delete
- ELB 전체 권한
- Autoscaling Describe
- KMS DescribeKey

**Worker:**
- EC2 Describe
- ECR 이미지 Pull 권한

#### 보안 그룹 규칙

| 포트 | 프로토콜 | 소스 | 설명 |
|------|----------|------|------|
| 22 | TCP | 설정된 CIDR | SSH 접속 |
| 80 | TCP | 0.0.0.0/0 | HTTP |
| 443 | TCP | 0.0.0.0/0 | HTTPS |
| 6443 | TCP | 설정된 CIDR | K3s API Server (external) |
| 6443 | TCP | Self | K3s API Server (internal) |
| 8472 | UDP | Self | Flannel VXLAN (Pod 통신) |
| 30000-32767 | TCP | 0.0.0.0/0 | NodePort 서비스 |
| 전체 | 전체 | Self | 클러스터 내부 통신 |

#### 설치 방식

**수동 설치**: EC2 인스턴스 생성 후 SSH 접속하여 K3s 수동 설치 필요

```bash
# 1. terraform apply로 EC2 인스턴스 생성
terraform apply

# 2. Master SSH 접속 후 K3s 서버 설치
$(terraform output -raw k3s_ssh_master_command)
curl -sfL https://get.k3s.io | sh -s - server --cluster-init

# 3. Worker 노드에 K3s agent 설치
# 자세한 내용은 README.md 참조
```

---

## [1.0.1] - 2025-11-30

### Bastion Host Amazon Linux 2023 업그레이드

- AMI: Amazon Linux 2 → Amazon Linux 2023
- 패키지 매니저: yum → dnf
- MySQL 클라이언트: mysql → mariadb105
- 루트 볼륨: 8GB → 30GB (AL2023 요구사항)

---

## [1.0.0] - 2025-11-30

### 인프라 배포 완료

최초 Terraform 인프라 배포 완료

#### 배포된 리소스

| 리소스 | 상태 |
|--------|------|
| VPC (10.180.0.0/20) | 배포됨 |
| Public/Private Subnets (2 AZ) | 배포됨 |
| NAT Gateway | 배포됨 |
| ALB | 배포됨 |
| CloudFront + WAF | 배포됨 |
| ECR (backend/frontend) | 배포됨 |
| Bastion Host | 배포됨 |
| Security Groups | 배포됨 |

### 버그 수정

#### 1. Bastion 모듈 outputs.tf 오류 수정

**문제**: `terraform plan` 시 존재하지 않는 리소스 참조 에러

```
Error: Reference to undeclared resource
  - aws_key_pair.bastion
  - local_file.private_key
```

**원인**: `outputs.tf`에서 `main.tf`에 정의되지 않은 리소스 참조

**해결**: `modules/bastion/outputs.tf` 수정
- `aws_key_pair.bastion.key_name` → `var.key_name`
- `bastion_private_key_path` output 삭제
- `ssh_command`에서 `local_file.private_key.filename` → `${var.key_name}.pem`

### 보안 개선

#### .gitignore 업데이트

민감한 파일 보호를 위해 추가:
```
*.tfvars
*.tfvars.json
```

기존 보호 항목 확인:
- `*.pem` (SSH 키)
- `.terraform/` (Provider 바이너리)
- `*.tfstate` (상태 파일)
- `secret/*` (시크릿 디렉토리)

### 문서 업데이트

- `README.md`: 현재 배포 상태, 엔드포인트, 네트워크 구성 정보 추가

---

## 작업 타임라인

| 시간 | 작업 |
|------|------|
| 1 | 프로젝트 구조 파악 |
| 2 | `terraform plan` 에러 디버깅 및 수정 |
| 3 | `.gitignore` 보안 점검 및 `*.tfvars` 추가 |
| 4 | `terraform apply` 에러 디버깅 |
| 5 | CloudFront 도메인 설정 변경 (`*.eunha.icu`) |
| 6 | 인프라 배포 완료 |
| 7 | `README.md` 업데이트 |

---

## 현재 인프라 상태

`terraform output` 명령어로 실제 배포된 리소스 정보를 확인하세요.

```bash
# 전체 출력
terraform output

# 개별 확인 예시
terraform output cloudfront_domain_name
terraform output bastion_ssh_command
terraform output ecr_repositories
```

### 배포된 리소스
- CloudFront + WAF (*.eunha.icu)
- ALB (Application Load Balancer)
- ECR (backend/frontend 레포지토리)
- VPC (10.180.0.0/20, 2 AZ: ap-northeast-2a, 2c)
- Bastion Host (EC2)
- Security Groups (ALB, ECS, Bastion)

---

## Troubleshooting

### 1. Terraform State Lock 오류 (DynamoDB)

**문제**: `terraform plan` 또는 `terraform apply` 실행 시 State Lock 오류 발생

```
Error: Error acquiring the state lock

Error message: operation error DynamoDB: PutItem, https response error
StatusCode: 400, RequestID: xxx,
ConditionalCheckFailedException: The conditional request failed
Lock Info:
  ID:        bed0ab93-4e35-4f5c-47e9-64ca9f99b341
  Path:      softbank2025-blue-tfstate/blue/terraform.tfstate
  Operation: OperationTypePlan
  Who:       student@develop-trixie
  Version:   1.13.5
  Created:   2025-11-29 16:00:58.128687822 +0000 UTC
```

**원인**: 이전 Terraform 작업이 비정상 종료되어 DynamoDB에 Lock이 남아있음

**해결**: `terraform force-unlock` 명령어로 강제 해제

```bash
# Lock ID 확인 후 강제 해제
terraform force-unlock -force <LOCK_ID>

# 예시
terraform force-unlock -force bed0ab93-4e35-4f5c-47e9-64ca9f99b341
```

**출력 예시**:
```
Terraform state has been successfully unlocked!

The state has been unlocked, and Terraform commands should now be able to
obtain a new lock on the remote state.
```

**주의사항**:
- Lock ID는 에러 메시지의 `ID:` 항목에서 확인
- 다른 사용자가 실제로 작업 중인지 확인 후 실행
- `-force` 플래그 없이 실행하면 확인 프롬프트가 표시됨

**예방**:
- `Ctrl+C`로 Terraform 작업 중단 시 Lock이 남을 수 있음
- 작업 완료까지 기다리거나, 안전하게 종료 후 unlock 실행

### 2. CloudFront 삭제 방법

**문제**: CloudFront Distribution 삭제 필요

**해결 순서**:

1. **Distribution 비활성화** (AWS 콘솔 또는 CLI)
   ```bash
   # 현재 상태 확인
   aws cloudfront get-distribution --id <DISTRIBUTION_ID> \
     --query 'Distribution.{Status:Status,Enabled:DistributionConfig.Enabled}'
   ```

2. **Deployed 상태 대기** (비활성화 후 5-15분 소요)
   ```bash
   # 상태가 "Deployed"가 될 때까지 대기
   aws cloudfront get-distribution --id <DISTRIBUTION_ID> \
     --query 'Distribution.Status'
   ```

3. **삭제 실행**
   ```bash
   # ETag 확인
   ETAG=$(aws cloudfront get-distribution --id <DISTRIBUTION_ID> \
     --query 'ETag' --output text)

   # 삭제
   aws cloudfront delete-distribution --id <DISTRIBUTION_ID> --if-match $ETAG
   ```

**주의**: Distribution이 `InProgress` 상태에서는 삭제 불가, `Deployed` 상태여야 함
