# Softbank 2025 Hackathon - Infrastructure Template

AWS 인프라를 Terraform으로 구성하는 해커톤 템플릿입니다.

## 현재 배포 상태

배포 후 `terraform output` 명령어로 실제 값을 확인하세요.

```bash
# 전체 출력값 확인
terraform output

# 개별 확인
terraform output <OUTPUT_NAME>
```

### 주요 Output 항목

| Output | 설명 |
|--------|------|
| `cloudfront_domain_name` | CloudFront 배포 도메인 |
| `cloudfront_id` | CloudFront Distribution ID |
| `frontend_s3_bucket_id` | 프론트엔드 S3 버킷 ID |
| `frontend_s3_bucket_arn` | 프론트엔드 S3 버킷 ARN |
| `alb_dns_name` | ALB DNS 주소 |
| `alb_arn` | ALB ARN |
| `alb_default_target_group_arn` | ALB 기본 타겟 그룹 ARN |
| `alb_https_listener_arn` | ALB HTTPS 리스너 ARN |
| `bastion_public_ip` | Bastion Host Public IP |
| `bastion_ssh_command` | Bastion SSH 접속 명령어 |
| `ecr_repositories` | ECR 레포지토리 URL (backend/frontend) |
| `k3s_master_public_ip` | K3s Master Public IP |
| `k3s_master_private_ip` | K3s Master Private IP |
| `k3s_ssh_master_command` | K3s Master SSH 접속 명령어 |
| `k3s_kubeconfig_command` | kubeconfig 가져오기 명령어 |
| `k3s_worker_instances` | K3s Worker 인스턴스 정보 |
| `k3s_security_group_id` | K3s 보안 그룹 ID |
| `vpc_id` | VPC ID |
| `public_subnet_ids` | Public Subnet ID 목록 |
| `private_app_subnet_ids` | Private App Subnet ID 목록 |
| `private_db_subnet_ids` | Private DB Subnet ID 목록 |
| `alb_security_group_id` | ALB 보안 그룹 ID |
| `waf_web_acl_arn` | WAF Web ACL ARN |

## 사전 준비 (필수)

**Terraform 실행 전에 [PRE-REQUIREMENTS.md](./PRE-REQUIREMENTS.md)를 먼저 확인하세요.**

필수 사전 작업:
- S3 버킷 생성 (Terraform State 저장용)
- DynamoDB 테이블 생성 (State Locking용)
- EC2 Key Pair 생성 (Bastion 사용시)
- ACM 인증서 생성
  - CloudFront용: us-east-1 리전 (*.eunha.icu)
  - ALB용: ap-northeast-2 리전 (*.eunha.icu)

## 아키텍처

```
                              Internet
                                 │
              ┌──────────────────┴──────────────────┐
              │                                      │
              ▼                                      ▼
┌─────────────────────────┐            ┌─────────────────────────┐
│      CloudFront         │            │          ALB            │
│   (www.eunha.icu)       │            │    (*.eunha.icu)        │
│        + WAF            │            │   HTTP → HTTPS 301      │
└───────────┬─────────────┘            └───────────┬─────────────┘
            │                                      │
            ▼                                      ▼
┌─────────────────────────┐            ┌─────────────────────────┐
│     S3 Bucket           │            │     Target Group        │
│  (eunha-icu-frontend)   │            │    (K3s Services)       │
│   Static Frontend       │            │                         │
└─────────────────────────┘            └─────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                         VPC (10.180.0.0/20)                     │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │              K3s Cluster (Public Subnet)                  │  │
│  │  ┌─────────┐  ┌─────────────────────────────────────────┐ │  │
│  │  │ Master  │  │              Workers                    │ │  │
│  │  │(m7i-fx) │  │ ┌────────┐ ┌────────┐ ┌────────┐ ┌────┐│ │  │
│  │  │         │  │ │  Wasm  │ │ Build  │ │Observ. │ │Infra││ │  │
│  │  └─────────┘  │ └────────┘ └────────┘ └────────┘ └────┘│ │  │
│  │               └─────────────────────────────────────────┘ │  │
│  └───────────────────────────────────────────────────────────┘  │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │              Private App Subnets (2 AZ)                   │  │
│  └───────────────────────────────────────────────────────────┘  │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │              Private DB Subnets (2 AZ)                    │  │
│  └───────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

### 트래픽 흐름

| 도메인 | 경로 | 설명 |
|--------|------|------|
| `www.eunha.icu` | CloudFront → S3 | 프론트엔드 정적 파일 (React/Vue 등) |
| `*.eunha.icu` | ALB → Target Group | API 백엔드 (K3s 서비스) |

## 모듈 구성

| 모듈 | 설명 | 상태 |
|------|------|------|
| vpc | VPC, 서브넷, NAT Gateway, 라우팅 | 배포됨 |
| security-groups | ALB, ECS, Bastion 보안그룹 | 배포됨 |
| ecr | Docker 이미지 레지스트리 | 배포됨 |
| alb | Application Load Balancer (HTTPS) | 배포됨 |
| cloudfront | S3 프론트엔드 CDN (www.eunha.icu) | 배포됨 |
| waf | Web Application Firewall | 배포됨 |
| bastion | Bastion Host (점프 서버) | 비활성화 |
| k3s | K3s Kubernetes 클러스터 (Master 1 + Worker 4) | 배포됨 |

## 빠른 시작

### 1. 사전 준비 완료 확인

[PRE-REQUIREMENTS.md](./PRE-REQUIREMENTS.md) 참조

### 2. 배포

```bash
# 초기화
terraform init

# 계획 확인
terraform plan

# 배포
terraform apply
```

### 3. 프론트엔드 배포

```bash
# S3에 정적 파일 업로드
aws s3 sync ./dist s3://eunha-icu-frontend --delete

# CloudFront 캐시 무효화 (선택)
aws cloudfront create-invalidation --distribution-id <DISTRIBUTION_ID> --paths "/*"
```

## 주요 변수

### 프로젝트 설정
| 변수 | 설명 | 기본값 |
|------|------|--------|
| `project_name` | 프로젝트 이름 (리소스 접두사) | `blue-final` |
| `environment` | 환경 (dev/staging/prod) | `dev` |

### VPC 설정
| 변수 | 설명 | 기본값 |
|------|------|--------|
| `vpc_cidr` | VPC CIDR | `10.180.0.0/20` |
| `availability_zones` | 가용 영역 | `["ap-northeast-2a", "ap-northeast-2c"]` |

### 인증서 설정
| 변수 | 설명 | 기본값 |
|------|------|--------|
| `cloudfront_certificate_arn` | CloudFront용 ACM (us-east-1) | `arn:aws:acm:us-east-1:...` |
| `alb_certificate_arn` | ALB용 ACM (ap-northeast-2) | `arn:aws:acm:ap-northeast-2:...` |

### 프론트엔드 설정
| 변수 | 설명 | 기본값 |
|------|------|--------|
| `frontend_s3_bucket_name` | 프론트엔드 S3 버킷 이름 | `eunha-icu-frontend` |

### 선택적 모듈
| 변수 | 설명 | 기본값 |
|------|------|--------|
| `create_cloudfront` | CloudFront 생성 여부 | `true` |
| `create_waf` | WAF 생성 여부 | `true` |
| `create_bastion` | Bastion Host 생성 여부 | `false` |
| `create_k3s` | K3s 클러스터 생성 여부 | `true` |

### K3s 클러스터 설정
| 변수 | 설명 | 기본값 |
|------|------|--------|
| `k3s_key_name` | EC2 Key Pair 이름 | `blue-key` |
| `k3s_master_instance_type` | Master 인스턴스 타입 | `m7i-flex.large` |
| `k3s_worker_instance_type` | Worker 인스턴스 타입 | `m7i-flex.large` |
| `k3s_master_volume_size` | Master 볼륨 크기 (GB) | `50` |
| `k3s_worker_volume_size` | Worker 볼륨 크기 (GB) | `50` |
| `k3s_token` | K3s 클러스터 토큰 (sensitive) | - |
| `k3s_allocate_eip` | Master에 EIP 할당 여부 | `true` |

### K3s Worker 노드 구성
| 노드 | 역할 | 설명 |
|------|------|------|
| `worker-wasm` | Wasm | WebAssembly 워크로드 실행 |
| `worker-build` | Build | CI/CD 빌드 작업 |
| `worker-observability` | Observability | 모니터링/로깅 |
| `worker-infra` | Infra | 인프라 관리 도구 |

## 출력값

```bash
# 주요 출력값 확인
terraform output

# CloudFront & S3
terraform output cloudfront_domain_name
terraform output frontend_s3_bucket_id

# ALB
terraform output alb_dns_name
terraform output alb_default_target_group_arn
terraform output alb_https_listener_arn

# VPC
terraform output vpc_id
terraform output public_subnet_ids

# ECR
terraform output ecr_repositories

# K3s
terraform output k3s_master_public_ip
terraform output k3s_ssh_master_command
terraform output k3s_kubeconfig_command
terraform output k3s_worker_instances
```

### K3s 클러스터 설치 (수동)

EC2 인스턴스 생성 후 K3s를 수동으로 설치해야 합니다.

#### 1. Master 노드 설치

```bash
# Master SSH 접속
$(terraform output -raw k3s_ssh_master_command)

# K3s 서버 설치
curl -sfL https://get.k3s.io | sh -s - server \
  --write-kubeconfig-mode 644 \
  --tls-san $(curl -s http://169.254.169.254/latest/meta-data/public-ipv4) \
  --node-label "node-role=master" \
  --cluster-init

# 토큰 확인 (Worker 설치시 필요)
sudo cat /var/lib/rancher/k3s/server/node-token
```

#### 2. Worker 노드 설치

```bash
# 각 Worker에 SSH 접속 후 실행
# MASTER_IP: Master의 Private IP
# TOKEN: Master에서 확인한 토큰

curl -sfL https://get.k3s.io | K3S_URL=https://<MASTER_IP>:6443 \
  K3S_TOKEN=<TOKEN> sh -s - agent \
  --node-label "node-role=worker" \
  --node-label "workload=<WORKLOAD_TYPE>"
```

#### 3. kubeconfig 가져오기 (로컬)

```bash
# kubeconfig 복사
$(terraform output -raw k3s_kubeconfig_command) > ~/.kube/config-k3s

# Master IP로 server 주소 변경
MASTER_IP=$(terraform output -raw k3s_master_public_ip)
sed -i "s/127.0.0.1/$MASTER_IP/g" ~/.kube/config-k3s

# kubectl 사용
export KUBECONFIG=~/.kube/config-k3s
kubectl get nodes
```

## 디렉토리 구조

```
.
├── README.md            # 이 파일
├── PRE-REQUIREMENTS.md  # 사전 준비 사항
├── CHANGELOG.md         # 변경 이력
├── main.tf              # 메인 모듈 구성
├── variables.tf         # 변수 정의
├── outputs.tf           # 출력값 정의
├── providers.tf         # AWS Provider 설정 (kOps 태그 무시 포함)
├── backend.tf           # Terraform 백엔드 설정
└── modules/
    ├── vpc/             # VPC, 서브넷, NAT
    ├── security-groups/ # 보안그룹
    ├── ecr/             # ECR 레지스트리
    ├── alb/             # ALB (HTTPS 리스너, 타겟 그룹)
    ├── cloudfront/      # S3 프론트엔드 CDN
    ├── waf/             # WAF
    ├── bastion/         # Bastion Host
    └── k3s/             # K3s Kubernetes 클러스터
```

## kOps 태그 공존

kOps가 VPC/Subnet에 추가하는 태그가 Terraform apply 시 삭제되지 않도록 `providers.tf`에 다음 설정이 포함되어 있습니다:

```hcl
provider "aws" {
  # ...
  ignore_tags {
    keys = ["SubnetType"]
    key_prefixes = ["kubernetes.io/cluster/sfbank-blue"]
  }
}
```

## 최근 변경 사항 (2025-12-01)

### CloudFront + S3 프론트엔드
- CloudFront에서 ALB 연결 제거
- S3 버킷 (`eunha-icu-frontend`) 생성 및 OAC 연결
- SPA 지원 (403/404 → index.html)
- 도메인: `www.eunha.icu`

### ALB HTTPS 설정
- HTTPS 리스너 추가 (TLS 1.3)
- HTTP → HTTPS 301 리다이렉트
- 기본 타겟 그룹 생성
- 인증서: ap-northeast-2 리전 ACM

### kOps 태그 무시
- `SubnetType` 태그 무시
- `kubernetes.io/cluster/sfbank-blue*` prefix 태그 무시

## 예상 비용 (8일 기준)

> ap-northeast-2 리전 기준, 트래픽 미포함 예상치

| 리소스 | 스펙 | 8일 예상 |
|--------|------|----------|
| EC2 - K3s Master | m7i-flex.large | $22.60 |
| EC2 - K3s Workers (4) | m7i-flex.large × 4 | $90.40 |
| NAT Gateway | 1개 | $8.64 |
| ALB | 1개 | $4.32 |
| EBS | 250GB gp3 | $5.40 |
| Public IPv4 | 6개 | $5.76 |
| WAF | 1 Web ACL | $1.35 |
| CloudFront | 트래픽 미발생시 | $0.00 |
| S3 | 프론트엔드 버킷 | ~$0.10 |
| **합계** | | **~$138** |

### 비용 절감 팁
- 미사용시 EC2 인스턴스 중지 (EBS 비용만 발생)
- NAT Gateway는 시간당 과금되므로 필요시에만 유지
- K3s Worker 수를 필요에 따라 조절

## 정리

```bash
terraform destroy
```

## 라이선스

MIT
