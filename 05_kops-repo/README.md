# kOps Kubernetes Cluster - sfbank-blue

## 개요

AWS 서울 리전(ap-northeast-2)에 kOps를 사용하여 Kubernetes 클러스터를 배포하는 프로젝트입니다.
기존 VPC 인프라를 활용하며, Cluster Autoscaler를 통한 노드 자동 스케일링을 지원합니다.

---

## 클러스터 정보

| 항목 | 값 |
|------|-----|
| 클러스터 이름 | sfbank-blue.k8s.local |
| Kubernetes 버전 | 1.33.6 |
| 리전 | ap-northeast-2 (서울) |
| VPC | vpc-03b6863c762b38258 |
| Network CIDR | 10.180.0.0/20 |
| CNI | Cilium (kube-proxy 비활성화) |
| 노드 스케일링 | Cluster Autoscaler |

---

## S3 버킷 구성

kOps는 클러스터 상태 저장을 위해 S3 버킷을 사용합니다.

```bash
# State Store - 클러스터 설정 및 상태 저장
s3://sfbank-blue-kops-state-store

# OIDC Store - IRSA(IAM Roles for Service Accounts) 지원
s3://sfbank-blue-kops-oidc-store
```

### 버킷 생성 명령어

```bash
# 서울 리전에 S3 버킷 생성 (us-east-1 외 리전은 LocationConstraint 필요)
aws s3api create-bucket \
    --bucket sfbank-blue-kops-state-store \
    --region ap-northeast-2 \
    --create-bucket-configuration LocationConstraint=ap-northeast-2

aws s3api create-bucket \
    --bucket sfbank-blue-kops-oidc-store \
    --region ap-northeast-2 \
    --create-bucket-configuration LocationConstraint=ap-northeast-2

# 버전 관리 활성화
aws s3api put-bucket-versioning \
    --bucket sfbank-blue-kops-state-store \
    --versioning-configuration Status=Enabled

aws s3api put-bucket-versioning \
    --bucket sfbank-blue-kops-oidc-store \
    --versioning-configuration Status=Enabled

# 퍼블릭 액세스 차단
aws s3api put-public-access-block \
    --bucket sfbank-blue-kops-state-store \
    --public-access-block-configuration \
    "BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true"

aws s3api put-public-access-block \
    --bucket sfbank-blue-kops-oidc-store \
    --public-access-block-configuration \
    "BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true"
```

---

## 네트워크 구성

### 서브넷

| 이름 | ID | 타입 | AZ | 용도 |
|------|-----|------|-----|------|
| public-ap-northeast-2a | subnet-0cefb29d9b482ea5b | Public | ap-northeast-2a | - |
| public-ap-northeast-2c | subnet-0e40cf24e2078751b | Public | ap-northeast-2c | Control Plane |
| private-ap-northeast-2a | subnet-04ab7aec5b223bcfd | Private | ap-northeast-2a | Worker Nodes |
| private-ap-northeast-2c | subnet-058bb3aeee42e3ae4 | Private | ap-northeast-2c | Worker Nodes |

### 네트워크 토폴로지

```
┌─────────────────────────────────────────────────────────────────┐
│                         VPC (10.180.0.0/20)                      │
│                      vpc-03b6863c762b38258                       │
├─────────────────────────────────────────────────────────────────┤
│     ap-northeast-2a              │      ap-northeast-2c          │
├──────────────────────────────────┼────────────────────────────────┤
│  ┌─────────────────────┐         │  ┌─────────────────────┐      │
│  │   Public Subnet     │         │  │   Public Subnet     │      │
│  │                     │         │  │                     │      │
│  │                     │         │  │  ┌───────────────┐  │      │
│  │                     │         │  │  │ Control Plane │  │      │
│  │                     │         │  │  │  (t4g.medium) │  │      │
│  │                     │         │  │  │ 10.180.1.187  │  │      │
│  │                     │         │  │  └───────────────┘  │      │
│  └─────────────────────┘         │  └─────────────────────┘      │
│                                  │                                │
│  ┌─────────────────────┐         │  ┌─────────────────────┐      │
│  │   Private Subnet    │         │  │   Private Subnet    │      │
│  │                     │         │  │                     │      │
│  │  ┌───────────────┐  │         │  │  ┌───────────────┐  │      │
│  │  │ Worker Node   │  │         │  │  │ Worker Node   │  │      │
│  │  │  (t4g.large)  │  │         │  │  │  (t4g.large)  │  │      │
│  │  │ 10.180.6.227  │  │         │  │  │ 10.180.9.88   │  │      │
│  │  └───────────────┘  │         │  │  └───────────────┘  │      │
│  │        │ NAT        │         │  │        │ NAT        │      │
│  └────────┴────────────┘         │  └────────┴────────────┘      │
└─────────────────────────────────────────────────────────────────┘
```

---

## 인스턴스 구성

### Control Plane (Master)

| 항목 | 값 |
|------|-----|
| 인스턴스 타입 | t4g.medium (ARM64/Graviton2) |
| AMI | ami-0f491b955c27fd437 (Ubuntu 24.04 ARM64) |
| 서브넷 | public-ap-northeast-2c |
| 개수 | 1 |
| 역할 | Kubernetes API Server, etcd, Controller Manager, Scheduler |

### Worker Nodes

| 노드 그룹 | 인스턴스 타입 | 서브넷 | Min | Max | 용도 |
|----------|--------------|--------|-----|-----|------|
| nodes-ap-northeast-2a | t3a.large (x86_64) | private-ap-northeast-2a | 1 | 2 | 일반 워크로드 |
| nodes-ap-northeast-2c | t3a.large (x86_64) | private-ap-northeast-2c | 1 | 2 | 일반 워크로드 |
| spot-nodes-ap-northeast-2c | c5/c6i/c7i.large (x86_64) | private-ap-northeast-2c | 3 | 6 | 스팟 컴퓨팅 최적화 |
| observability-ap-northeast-2c | t3a.large (x86_64) | private-ap-northeast-2c | 1 | 2 | 모니터링/로깅 |
| build-ap-northeast-2c | c7i.xlarge (x86_64) | private-ap-northeast-2c | 1 | 1 | CI/CD 빌드 |

### Spot 노드 구성

```yaml
mixedInstancesPolicy:
  instances:
  - c5.large      # 2 vCPU, 4GB RAM
  - c6i.large     # 2 vCPU, 4GB RAM
  - c7i.large     # 2 vCPU, 4GB RAM
  onDemandAboveBase: 0
  onDemandBase: 0
  spotAllocationStrategy: capacity-optimized
nodeLabels:
  spot: "true"
```

**스팟 비용 (서울 리전 기준):**
- c5.large: ~$0.033/hr
- c6i.large: ~$0.035/hr
- 3대 기준 월 ~$73

### 특수 노드 그룹

| 노드 그룹 | Taint | Label | 용도 |
|----------|-------|-------|------|
| observability | `observability=true:NoSchedule` | `observability=true` | Prometheus, Loki 등 |
| build | `build=true:NoSchedule` | `build=true` | Kaniko, Buildah 등 |

### 인스턴스 타입 선택 이유

- **ARM64 (Graviton2)**: x86 대비 최대 40% 비용 절감
- **t4g 시리즈**: 버스트 가능한 범용 인스턴스로 개발/테스트 환경에 적합
- **Private 서브넷**: Worker 노드를 외부 접근으로부터 보호
- **Multi-AZ**: 두 개의 AZ에 노드 분산으로 고가용성 확보

---

## 활성화된 애드온

### 1. Cluster Autoscaler
노드 자동 스케일링을 담당합니다.

```yaml
clusterAutoscaler:
  enabled: true
  balanceSimilarNodeGroups: true
  scaleDownUtilizationThreshold: "0.5"
```

- **balanceSimilarNodeGroups**: 유사한 노드 그룹 간 균형 유지
- **scaleDownUtilizationThreshold**: 50% 이하 사용률 시 스케일 다운

### 2. Cilium CNI
eBPF 기반의 고성능 네트워킹을 제공합니다.

```yaml
networking:
  cilium:
    enableNodePort: true
kubeProxy:
  enabled: false  # Cilium이 kube-proxy 대체
```

### 3. AWS Load Balancer Controller
ALB/NLB를 자동으로 생성하고 관리합니다.

```yaml
awsLoadBalancerController:
  enabled: true
  cpuRequest: "100m"
  cpuLimit: "200m"
  memoryRequest: "200Mi"
  memoryLimit: "500Mi"
```

### 4. Cert Manager
TLS 인증서를 자동으로 발급하고 갱신합니다.

```yaml
certManager:
  enabled: true
```

- AWS Load Balancer Controller와 Metrics Server가 의존
- Let's Encrypt 등 외부 CA 연동 가능

### 5. Metrics Server
Pod/Node 메트릭을 수집하여 HPA(Horizontal Pod Autoscaler)를 지원합니다.

```yaml
metricsServer:
  enabled: true
  insecure: false
```

### 6. AWS EBS CSI Driver
EBS 볼륨을 Kubernetes PersistentVolume으로 사용할 수 있게 합니다.

```yaml
cloudConfig:
  awsEBSCSIDriver:
    enabled: true
```

---

## API 접근 구성

### Network Load Balancer

```yaml
api:
  loadBalancer:
    class: Network
    type: Public
```

- Kubernetes API는 Public NLB를 통해 접근
- 접근 제어: `kubernetesApiAccess: 0.0.0.0/0` (필요시 제한 권장)

### SSH 접근

```yaml
sshAccess:
  - 0.0.0.0/0  # 프로덕션에서는 제한 필요
```

---

## 클러스터 접근 방법

### 필수 도구

클러스터에 접근하려면 다음 도구들이 설치되어 있어야 합니다:

| 도구 | 용도 | 설치 방법 |
|------|------|----------|
| AWS CLI | AWS 인증 및 리소스 접근 | `curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip" && unzip awscliv2.zip && sudo ./aws/install` |
| kops | 클러스터 관리 | `curl -Lo kops https://github.com/kubernetes/kops/releases/download/v1.30.0/kops-linux-amd64 && chmod +x kops && sudo mv kops /usr/local/bin/` |
| kubectl | Kubernetes API 접근 | `curl -LO "https://dl.k8s.io/release/v1.33.0/bin/linux/amd64/kubectl" && chmod +x kubectl && sudo mv kubectl /usr/local/bin/` |

### AWS 자격 증명 설정

```bash
# 방법 1: 환경변수 설정
export AWS_ACCESS_KEY_ID=<your-access-key>
export AWS_SECRET_ACCESS_KEY=<your-secret-key>
export AWS_DEFAULT_REGION=ap-northeast-2

# 방법 2: AWS CLI 프로파일 설정
aws configure
# AWS Access Key ID: <입력>
# AWS Secret Access Key: <입력>
# Default region name: ap-northeast-2
# Default output format: json

# 자격 증명 확인
aws sts get-caller-identity
```

### kubeconfig 파일 생성

kOps는 S3에 저장된 클러스터 정보를 기반으로 kubeconfig를 생성합니다.

```bash
# 환경변수 설정 (필수)
export KOPS_STATE_STORE=s3://sfbank-blue-kops-state-store
export NAME=sfbank-blue.k8s.local

# kubeconfig 내보내기 (admin 권한)
kops export kubeconfig --admin --name $NAME

# kubeconfig 파일 위치 확인
ls -la ~/.kube/config

# 현재 컨텍스트 확인
kubectl config current-context
# 출력: sfbank-blue.k8s.local
```

### kubeconfig 파일 구조

생성된 `~/.kube/config` 파일:

```yaml
apiVersion: v1
kind: Config
clusters:
- cluster:
    certificate-authority-data: <base64-encoded-ca-cert>
    server: https://api-sfbank-blue-k8s-lo-xxxxxx.elb.ap-northeast-2.amazonaws.com
  name: sfbank-blue.k8s.local
contexts:
- context:
    cluster: sfbank-blue.k8s.local
    user: sfbank-blue.k8s.local
  name: sfbank-blue.k8s.local
current-context: sfbank-blue.k8s.local
users:
- name: sfbank-blue.k8s.local
  user:
    exec:
      apiVersion: client.authentication.k8s.io/v1beta1
      command: kops
      args:
      - get
      - token
      - --name=sfbank-blue.k8s.local
      env:
      - name: KOPS_STATE_STORE
        value: s3://sfbank-blue-kops-state-store
```

### 다른 PC/환경에서 접근하기

다른 환경에서 클러스터에 접근하려면:

```bash
# 1. 필수 도구 설치 (AWS CLI, kops, kubectl)

# 2. AWS 자격 증명 설정
aws configure

# 3. 환경변수 설정
export KOPS_STATE_STORE=s3://sfbank-blue-kops-state-store
export NAME=sfbank-blue.k8s.local

# 4. kubeconfig 내보내기
kops export kubeconfig --admin --name $NAME

# 5. 접근 테스트
kubectl get nodes
```

### 필요한 IAM 권한

클러스터에 접근하려면 AWS IAM 사용자/역할에 다음 권한이 필요합니다:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:GetObject",
        "s3:ListBucket"
      ],
      "Resource": [
        "arn:aws:s3:::sfbank-blue-kops-state-store",
        "arn:aws:s3:::sfbank-blue-kops-state-store/*"
      ]
    }
  ]
}
```

### 접근 확인 명령어

```bash
# 클러스터 정보 확인
kubectl cluster-info

# 노드 목록
kubectl get nodes -o wide

# 모든 네임스페이스의 Pod
kubectl get pods -A

# 시스템 컴포넌트 상태
kubectl get componentstatuses

# API 서버 버전
kubectl version
```

### SSH 접근 (Control Plane/Worker)

```bash
# Control Plane 인스턴스 IP 확인
aws ec2 describe-instances \
  --filters "Name=tag:Name,Values=*control-plane*" \
  --query 'Reservations[].Instances[].PublicIpAddress' \
  --output text

# SSH 접속 (프로젝트 폴더의 id_rsa 키 사용)
ssh -i id_rsa ubuntu@<control-plane-public-ip>

# Worker 노드는 Private 서브넷에 있으므로 Control Plane을 통해 접근
ssh -i id_rsa -J ubuntu@<control-plane-ip> ubuntu@<worker-private-ip>
```

---

## 사용 방법

### 환경변수 설정

```bash
export KOPS_STATE_STORE=s3://sfbank-blue-kops-state-store
export NAME=sfbank-blue.k8s.local
```

### 클러스터 생성

```bash
# 1. 클러스터 설정 생성
kops create -f cluster.yaml

# 2. SSH 키 등록
kops create secret sshpublickey admin -i id_rsa.pub --name $NAME

# 3. 클러스터 배포
kops update cluster --name $NAME --yes

# 4. 클러스터 검증 (최대 10분 대기)
kops validate cluster --wait 10m
```

### kubeconfig 설정

```bash
# admin 권한으로 kubeconfig 내보내기
kops export kubeconfig --admin --name $NAME

# kubectl 테스트
kubectl get nodes
kubectl get pods -A
```

### 클러스터 상태 확인

```bash
# 클러스터 유효성 검사
kops validate cluster --name $NAME

# 노드 상태
kubectl get nodes -o wide

# 시스템 Pod 상태
kubectl get pods -n kube-system
```

### 클러스터 수정

```bash
# 설정 파일 수정 후 적용
kops replace -f cluster.yaml --force
kops update cluster --name $NAME --yes

# 노드 롤링 업데이트 (설정 변경 시)
kops rolling-update cluster --name $NAME --yes
```

### 클러스터 삭제

```bash
kops delete cluster --name $NAME --yes
```

---

## 파일 구성

```
kops-test/
├── cluster.yaml           # 메인 클러스터 설정 파일
├── bucket.txt             # S3 버킷 생성 명령어
├── dry-run.yaml           # kops dry-run 출력 (참고용)
├── karpenter-nodepool.yaml # Karpenter 설정 (사용 안함)
├── id_rsa                 # SSH 개인키
├── id_rsa.pub             # SSH 공개키
└── README.md              # 이 문서
```

---

## 트러블슈팅

### 1. Karpenter vs Cluster Autoscaler

**문제**: Karpenter는 EKS 환경을 전제로 설계되어 kOps와 호환되지 않음

```
ERROR: failed calling webhook "validation.karpenter.sh":
failed to call webhook: Post "https://karpenter.kube-system.svc:8443/validate/karpenter.sh/v1/nodepools":
eks:DescribeCluster operation failed
```

**원인**: Karpenter AWS Provider는 `eks:DescribeCluster` API를 호출하는데, kOps 클러스터는 EKS가 아님

**해결**: Cluster Autoscaler로 전환
- kOps는 Cluster Autoscaler를 네이티브로 지원
- ASG(Auto Scaling Group) 기반으로 노드 스케일링

### 2. AMI 아키텍처 불일치

**문제**: 인스턴스 타입과 AMI 아키텍처 불일치

```
Error: machine type architecture "arm64" does not match image architecture "x86_64"
```

**해결**: 인스턴스 타입에 맞는 AMI 사용
- t4g (ARM64): `ami-0f491b955c27fd437` (Ubuntu 24.04 ARM64)
- t3 (x86_64): `ami-0f88d8a142a97098e` (Ubuntu 24.04 AMD64)

### 3. S3 버킷 리전 설정

**문제**: us-east-1 외 리전에서 S3 버킷 생성 시 오류

```
IllegalLocationConstraintException: The unspecified location constraint is incompatible
```

**해결**: `--create-bucket-configuration LocationConstraint=<region>` 추가

```bash
aws s3api create-bucket \
    --bucket my-bucket \
    --region ap-northeast-2 \
    --create-bucket-configuration LocationConstraint=ap-northeast-2
```

### 4. Cert Manager 필수

**문제**: AWS Load Balancer Controller 설치 시 cert-manager 필요

```
certManager:
  enabled: true  # 이 설정이 없으면 ALB Controller 설치 실패
```

### 5. Pod Pending 상태

**문제**: 시스템 Pod들이 Pending 상태로 유지

**원인**:
- Control Plane에 taint가 있어 일반 Pod 스케줄링 불가
- Worker 노드가 아직 Ready 상태가 아님

**해결**:
- 시스템 Pod들은 자동으로 toleration이 설정됨
- Worker 노드가 Ready 상태가 되면 자동 해결
- `kops validate cluster --wait 10m`으로 대기

### 5-1. MutatingWebhook Bootstrap 문제 (중요)

**문제**: 클러스터 부트스트랩 시 노드에 IP가 할당되지 않고, kops-controller와 aws-cloud-controller-manager가 CrashLoopBackOff

```
Error: unable to sync kubernetes service: failed calling webhook "mservice.elbv2.k8s.aws"
Error: KUBERNETES_SERVICE_HOST and KUBERNETES_SERVICE_PORT must be defined
```

**원인**:
- `aws-load-balancer-webhook`과 `pod-identity-webhook` MutatingWebhookConfiguration이 `kubernetes` Service 생성을 차단
- Webhook 백엔드 Pod가 아직 실행되지 않은 상태에서 webhook이 등록됨 (Chicken-egg 문제)
- kubernetes Service가 없어서 aws-cloud-controller-manager가 시작 불가
- CCM이 없어서 노드에 IP 할당 불가

**해결**:
```bash
# 문제가 되는 webhook 삭제
kubectl delete mutatingwebhookconfiguration aws-load-balancer-webhook
kubectl delete mutatingwebhookconfiguration pod-identity-webhook

# 잠시 후 kubernetes Service가 생성되고 클러스터 정상화
kubectl get svc kubernetes
```

**예방책**:
- 클러스터 최초 부트스트랩 시 webhook 관련 애드온 비활성화 후 클러스터 안정화 후 활성화
- 또는 webhook의 `failurePolicy`를 `Ignore`로 설정

### 6. vCPU 한도 초과

**문제**: EC2 인스턴스 생성 실패

```
You have requested more vCPU capacity than your current vCPU limit of 16 allows
for the instance bucket that the specified instance type belongs to.
```

**원인**: AWS 계정의 On-Demand 인스턴스 vCPU 한도 초과

**확인 방법**:
```bash
# 현재 실행 중인 인스턴스 확인
aws ec2 describe-instances --region ap-northeast-2 \
  --filters "Name=instance-state-name,Values=running" \
  --query 'Reservations[].Instances[].{Name:Tags[?Key==`Name`].Value|[0],Type:InstanceType}' \
  --output table

# vCPU 한도 확인
aws service-quotas list-service-quotas --region ap-northeast-2 --service-code ec2 \
  --query 'Quotas[?contains(QuotaName, `On-Demand`)].{Name:QuotaName,Value:Value}' \
  --output table
```

**해결**:
- 불필요한 인스턴스 종료
- AWS에 vCPU 한도 증가 요청 (Service Quotas > EC2)
- t4g.medium (2 vCPU), t4g.large (2 vCPU) 기준으로 계산

### 7. AZ 용량 부족

**문제**: 특정 AZ에서 인스턴스 타입 용량 부족

```
We currently do not have sufficient t4g.medium capacity in the Availability Zone
you requested (ap-northeast-2a). Our system will be working on provisioning
additional capacity.
```

**해결**: 다른 AZ 사용
- Control Plane을 ap-northeast-2a에서 ap-northeast-2c로 이동
- cluster.yaml에서 etcdClusters와 InstanceGroup의 서브넷 변경

---

## IAM 구성

### IRSA (IAM Roles for Service Accounts)

```yaml
iam:
  allowContainerRegistry: true
  legacy: false
  useServiceAccountExternalPermissions: true

serviceAccountIssuerDiscovery:
  discoveryStore: s3://sfbank-blue-kops-oidc-store/sfbank-blue.k8s.local/discovery/sfbank-blue.k8s.local
  enableAWSOIDCProvider: true
```

- 각 애드온(ALB Controller, EBS CSI Driver 등)은 자동으로 IAM Role 연동
- Pod별로 최소 권한 원칙 적용 가능

---

## 보안 고려사항

1. **SSH 키 관리**: `id_rsa` 파일은 안전하게 보관하고 Git에 커밋하지 않음
2. **API 접근 제한**: 프로덕션에서는 `kubernetesApiAccess`를 특정 IP로 제한
3. **SSH 접근 제한**: 프로덕션에서는 `sshAccess`를 특정 IP로 제한
4. **Private 서브넷**: Worker 노드는 Private 서브넷에 배포하여 직접 접근 차단
5. **암호화된 etcd 볼륨**: `encryptedVolume: true`로 etcd 데이터 암호화

---

## 비용 최적화

1. **ARM64 인스턴스**: t4g 시리즈는 x86 대비 20-40% 저렴
2. **Cluster Autoscaler**: 사용량에 따라 노드 자동 스케일링
3. **스케일 다운 임계값**: 50% 이하 사용률 시 노드 축소
4. **단일 Control Plane**: 개발/테스트 환경용 (프로덕션은 3개 권장)
5. **Multi-AZ 분산**: 각 AZ에 최소 1개 노드로 가용성과 비용 균형

---

## 현재 클러스터 상태 (2025-12-06)

### 노드 그룹

| 노드 그룹 | 인스턴스 타입 | 노드 수 | 용도 |
|----------|--------------|--------|------|
| control-plane-ap-northeast-2c | t4g.medium (ARM64) | 1 | Control Plane |
| nodes-ap-northeast-2a | t3a.large | 1 | 일반 워크로드 |
| nodes-ap-northeast-2c | t3a.large | 1 | 일반 워크로드 |
| spot-nodes-ap-northeast-2c | c5/c6i/c7i.large | 3 | 스팟 컴퓨팅 최적화 |
| observability-ap-northeast-2c | t3a.large | 1 | 모니터링/로깅 |
| build-ap-northeast-2c | c7i.xlarge | 1 | CI/CD 빌드 |

**총 노드 수**: 8개 (Master 1 + Worker 7)

### 실행 중인 주요 컴포넌트

| 컴포넌트 | 개수 | 상태 |
|----------|------|------|
| AWS Cloud Controller | 1 | Running |
| AWS Load Balancer Controller | 1 | Running |
| AWS Node Termination Handler | 1 | Running |
| Cert Manager | 3 | Running |
| Cilium | 8 | Running |
| Cilium Operator | 1 | Running |
| Cluster Autoscaler | 1 | Running |
| CoreDNS | 2 | Running |
| EBS CSI Driver | 8+ | Running |
| kOps Controller | 1 | Running |
| Metrics Server | 2 | Running |
| kwasm-annotator | 8 | Running |

---

## 참고 자료

- [kOps 공식 문서](https://kops.sigs.k8s.io/)
- [kOps Addons](https://kops.sigs.k8s.io/addons/)
- [Cluster Autoscaler](https://kops.sigs.k8s.io/addons/#cluster-autoscaler)
- [AWS Load Balancer Controller](https://kops.sigs.k8s.io/addons/#aws-load-balancer-controller)
- [Cilium CNI](https://kops.sigs.k8s.io/networking/cilium/)

---

## kwasm-annotator DaemonSet

모든 노드에 `kwasm.sh/kwasm-node=true` 어노테이션을 자동으로 추가하는 DaemonSet입니다.

**용도**: kwasm (WebAssembly) 런타임이 설치된 노드임을 표시

**파일**: `kwasm-annotator.yaml`

```yaml
apiVersion: apps/v1
kind: DaemonSet
metadata:
  name: kwasm-annotator
  namespace: kube-system
spec:
  selector:
    matchLabels:
      app: kwasm-annotator
  template:
    metadata:
      labels:
        app: kwasm-annotator
    spec:
      serviceAccountName: kwasm-annotator
      tolerations:
      - operator: Exists  # 모든 taint 허용
      containers:
      - name: annotator
        image: bitnami/kubectl:latest
        command: ["/bin/sh", "-c"]
        args:
        - |
          kubectl annotate node $NODE_NAME kwasm.sh/kwasm-node=true --overwrite
          echo "Annotation added to $NODE_NAME"
          sleep infinity
        env:
        - name: NODE_NAME
          valueFrom:
            fieldRef:
              fieldPath: spec.nodeName
```

**배포**:
```bash
kubectl apply -f kwasm-annotator.yaml
```

---

## 변경 이력

| 날짜 | 변경 내용 |
|------|----------|
| 2025-12-01 | 초기 클러스터 구성 (Karpenter 시도) |
| 2025-12-01 | Karpenter → Cluster Autoscaler 전환 (EKS 비호환 문제) |
| 2025-12-01 | ARM64 인스턴스로 전환 (비용 최적화) |
| 2025-12-01 | vCPU 한도 문제 해결 (불필요 인스턴스 정리) |
| 2025-12-01 | Control Plane AZ 변경 (ap-northeast-2a → 2c, 용량 부족 문제) |
| 2025-12-01 | Multi-AZ 노드 그룹 구성 (nodes-2a, nodes-2c 분리) |
| 2025-12-01 | 클러스터 정상 배포 완료 (3 nodes, 26 pods) |
| 2025-12-06 | MutatingWebhook Bootstrap 문제 해결 (aws-load-balancer-webhook, pod-identity-webhook 삭제) |
| 2025-12-06 | Spot 노드 그룹 추가 (t3a.large, minSize=4) |
| 2025-12-06 | Observability 노드 그룹 추가 (taint: observability=true:NoSchedule) |
| 2025-12-06 | Build 노드 그룹 추가 (c7i.xlarge, taint: build=true:NoSchedule) |
| 2025-12-06 | kwasm-annotator DaemonSet 배포 |
| 2025-12-06 | Spot 노드 T3 → C-series 전환 (c5.large, c6i.large, c7i.large) |
| 2025-12-06 | Spot 노드 minSize=3으로 변경, Taint 제거 |
