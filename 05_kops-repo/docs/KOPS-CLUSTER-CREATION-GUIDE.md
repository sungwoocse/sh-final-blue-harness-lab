# kOps 클러스터 생성 가이드

기존 VPC를 사용하여 AWS에 kOps Kubernetes 클러스터를 생성하는 가이드입니다.

---

## 사전 요구사항

### 1. AWS CLI 설정
```bash
aws configure
# AWS Access Key ID, Secret Access Key, Region 설정
```

### 2. kOps 설치
```bash
# Linux (ARM64)
curl -Lo kops https://github.com/kubernetes/kops/releases/download/v1.30.0/kops-linux-arm64
chmod +x kops
sudo mv kops /usr/local/bin/

# Linux (AMD64)
curl -Lo kops https://github.com/kubernetes/kops/releases/download/v1.30.0/kops-linux-amd64
chmod +x kops
sudo mv kops /usr/local/bin/
```

### 3. kubectl 설치
```bash
curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"
chmod +x kubectl
sudo mv kubectl /usr/local/bin/
```

---

## Step 1: S3 버킷 생성

kOps 상태 저장용 S3 버킷이 필요합니다.

```bash
# 상태 저장용 버킷
aws s3api create-bucket \
  --bucket sfbank-blue-kops-state-store \
  --region ap-northeast-2 \
  --create-bucket-configuration LocationConstraint=ap-northeast-2

# OIDC 저장용 버킷 (IRSA 사용 시)
aws s3api create-bucket \
  --bucket sfbank-blue-kops-oidc-store \
  --region ap-northeast-2 \
  --create-bucket-configuration LocationConstraint=ap-northeast-2

# OIDC 버킷 퍼블릭 액세스 설정
aws s3api put-public-access-block \
  --bucket sfbank-blue-kops-oidc-store \
  --public-access-block-configuration \
  "BlockPublicAcls=false,IgnorePublicAcls=false,BlockPublicPolicy=false,RestrictPublicBuckets=false"

# 버전 관리 활성화 (권장)
aws s3api put-bucket-versioning \
  --bucket sfbank-blue-kops-state-store \
  --versioning-configuration Status=Enabled
```

---

## Step 2: 환경 변수 설정

```bash
export NAME=sfbank-blue.k8s.local
export KOPS_STATE_STORE=s3://sfbank-blue-kops-state-store
export AWS_REGION=ap-northeast-2
```

---

## Step 3: 기존 VPC 서브넷 확인

```bash
# VPC 확인
aws ec2 describe-vpcs --query 'Vpcs[*].[VpcId,CidrBlock,Tags[?Key==`Name`].Value|[0]]' --output table

# 서브넷 확인
VPC_ID=vpc-03b6863c762b38258
aws ec2 describe-subnets \
  --filters "Name=vpc-id,Values=$VPC_ID" \
  --query 'Subnets[*].[SubnetId,AvailabilityZone,CidrBlock,Tags[?Key==`Name`].Value|[0]]' \
  --output table
```

---

## Step 4: cluster.yaml 작성

```yaml
apiVersion: kops.k8s.io/v1alpha2
kind: Cluster
metadata:
  name: sfbank-blue.k8s.local
spec:
  # API 서버 설정
  api:
    loadBalancer:
      class: Network
      type: Public

  authorization:
    rbac: {}

  channel: stable
  cloudProvider: aws

  # EBS CSI 드라이버 활성화
  cloudConfig:
    awsEBSCSIDriver:
      enabled: true

  # 상태 저장 위치
  configBase: s3://sfbank-blue-kops-state-store/sfbank-blue.k8s.local

  # etcd 클러스터 설정
  etcdClusters:
  - cpuRequest: 200m
    etcdMembers:
    - encryptedVolume: true
      instanceGroup: control-plane-ap-northeast-2c
      name: c
    manager:
      backupRetentionDays: 90
    memoryRequest: 100Mi
    name: main
  - cpuRequest: 100m
    etcdMembers:
    - encryptedVolume: true
      instanceGroup: control-plane-ap-northeast-2c
      name: c
    manager:
      backupRetentionDays: 90
    memoryRequest: 100Mi
    name: events

  # IAM 설정 (IRSA 활성화)
  iam:
    allowContainerRegistry: true
    legacy: false
    useServiceAccountExternalPermissions: true

  # Cluster Autoscaler 활성화
  clusterAutoscaler:
    enabled: true
    balanceSimilarNodeGroups: true
    scaleDownUtilizationThreshold: "0.5"

  # kube-proxy 비활성화 (Cilium 사용 시)
  kubeProxy:
    enabled: false

  kubelet:
    anonymousAuth: false

  # API 서버 접근 허용 IP
  kubeAPIAccess:
  - 0.0.0.0/0

  kubernetesVersion: 1.30.0

  # 기존 VPC 설정
  networkCIDR: 10.180.0.0/20
  networkID: vpc-03b6863c762b38258

  # CNI: Cilium
  networking:
    cilium:
      enableNodePort: true

  nonMasqueradeCIDR: 100.64.0.0/10

  # OIDC Provider (IRSA용)
  serviceAccountIssuerDiscovery:
    discoveryStore: s3://sfbank-blue-kops-oidc-store/sfbank-blue.k8s.local/discovery/sfbank-blue.k8s.local
    enableAWSOIDCProvider: true

  # SSH 접근 허용 IP
  sshAccess:
  - 0.0.0.0/0

  # 기존 서브넷 설정
  subnets:
  - id: subnet-0cefb29d9b482ea5b
    name: public-ap-northeast-2a
    type: Public
    zone: ap-northeast-2a
  - id: subnet-0e40cf24e2078751b
    name: public-ap-northeast-2c
    type: Public
    zone: ap-northeast-2c
  - id: subnet-04ab7aec5b223bcfd
    name: private-ap-northeast-2a
    type: Private
    zone: ap-northeast-2a
    egress: nat
  - id: subnet-058bb3aeee42e3ae4
    name: private-ap-northeast-2c
    type: Private
    zone: ap-northeast-2c
    egress: nat

  # 추가 컴포넌트
  certManager:
    enabled: true

  awsLoadBalancerController:
    enabled: true

  metricsServer:
    enabled: true
    insecure: false

  topology:
    dns:
      type: None

---
# Control Plane (Master) 노드
apiVersion: kops.k8s.io/v1alpha2
kind: InstanceGroup
metadata:
  labels:
    kops.k8s.io/cluster: sfbank-blue.k8s.local
  name: control-plane-ap-northeast-2c
spec:
  image: ami-0f491b955c27fd437
  machineType: t4g.medium      # ARM64 인스턴스
  maxSize: 1
  minSize: 1
  role: Master
  subnets:
  - public-ap-northeast-2c     # Public 서브넷에 배치

---
# Worker 노드 - AZ a
apiVersion: kops.k8s.io/v1alpha2
kind: InstanceGroup
metadata:
  labels:
    kops.k8s.io/cluster: sfbank-blue.k8s.local
  name: nodes-ap-northeast-2a
spec:
  image: ami-0f491b955c27fd437
  machineType: t4g.large       # ARM64 인스턴스
  maxSize: 2
  minSize: 1
  role: Node
  subnets:
  - private-ap-northeast-2a    # Private 서브넷에 배치

---
# Worker 노드 - AZ c
apiVersion: kops.k8s.io/v1alpha2
kind: InstanceGroup
metadata:
  labels:
    kops.k8s.io/cluster: sfbank-blue.k8s.local
  name: nodes-ap-northeast-2c
spec:
  image: ami-0f491b955c27fd437
  machineType: t4g.large       # ARM64 인스턴스
  maxSize: 2
  minSize: 1
  role: Node
  subnets:
  - private-ap-northeast-2c    # Private 서브넷에 배치
```

---

## Step 5: 클러스터 생성

```bash
# 클러스터 설정 적용
kops create -f cluster.yaml

# SSH 키 생성 (없는 경우)
ssh-keygen -t rsa -b 4096 -f ~/.ssh/kops_rsa -N ""

# SSH 공개키 등록
kops create secret sshpublickey admin -i ~/.ssh/kops_rsa.pub --name $NAME --state $KOPS_STATE_STORE

# 클러스터 생성 실행
kops update cluster $NAME --yes

# 클러스터 상태 확인 (완료까지 5-10분 소요)
kops validate cluster --wait 10m
```

---

## Step 6: kubectl 설정

```bash
# kubeconfig 내보내기
kops export kubecfg --admin --name $NAME

# 클러스터 접근 확인
kubectl get nodes
kubectl get pods -A
```

---

## Step 7: 클러스터 검증

```bash
# 노드 상태 확인
kubectl get nodes -o wide

# 시스템 Pod 확인
kubectl get pods -n kube-system

# Cluster Autoscaler 확인
kubectl get pods -n kube-system -l app.kubernetes.io/name=cluster-autoscaler

# AWS Load Balancer Controller 확인
kubectl get pods -n kube-system -l app.kubernetes.io/name=aws-load-balancer-controller

# Cilium 상태 확인
kubectl get pods -n kube-system -l k8s-app=cilium
```

---

## 클러스터 관리 명령어

### 클러스터 정보 조회
```bash
kops get cluster
kops get instancegroups
```

### 클러스터 설정 변경
```bash
# 설정 편집
kops edit cluster $NAME

# 인스턴스 그룹 편집
kops edit ig nodes-ap-northeast-2a

# 변경사항 적용
kops update cluster $NAME --yes

# 롤링 업데이트 (노드 재시작 필요 시)
kops rolling-update cluster $NAME --yes
```

### 클러스터 삭제
```bash
kops delete cluster $NAME --yes
```

---

## 트러블슈팅

### 1. vCPU 한도 초과

**오류:**
```
You have requested more vCPU capacity than your current vCPU limit of 16 allows
```

**해결:**
```bash
# 현재 vCPU 사용량 확인
aws service-quotas get-service-quota \
  --service-code ec2 \
  --quota-code L-1216C47A \
  --region ap-northeast-2

# 실행 중인 인스턴스 확인
aws ec2 describe-instances \
  --filters "Name=instance-state-name,Values=running" \
  --query 'Reservations[*].Instances[*].[InstanceId,InstanceType]' \
  --output table --region ap-northeast-2

# 불필요한 인스턴스 종료하거나 Service Quotas에서 한도 증가 요청
```

### 2. AZ 용량 부족

**오류:**
```
We currently do not have sufficient t4g.medium capacity in ap-northeast-2a
```

**해결:** cluster.yaml에서 Control Plane을 다른 AZ로 변경
```yaml
# control-plane-ap-northeast-2a → control-plane-ap-northeast-2c
```

### 3. 노드가 NotReady 상태

```bash
# 노드 상태 확인
kubectl describe node <node-name>

# Cilium 상태 확인
kubectl get pods -n kube-system -l k8s-app=cilium

# Cilium 로그 확인
kubectl logs -n kube-system -l k8s-app=cilium --tail=50
```

### 4. API 서버 접근 불가

```bash
# NLB 상태 확인
aws elbv2 describe-load-balancers \
  --query 'LoadBalancers[?contains(LoadBalancerName, `api`)][LoadBalancerName,State.Code]' \
  --output table

# 타겟 그룹 헬스 확인
aws elbv2 describe-target-health \
  --target-group-arn <target-group-arn>
```

---

## 주요 구성 요소

| 컴포넌트 | 설명 |
|----------|------|
| **Cilium** | CNI (Container Network Interface) - kube-proxy 대체 |
| **Cluster Autoscaler** | 노드 자동 스케일링 |
| **AWS Load Balancer Controller** | ALB/NLB 자동 프로비저닝 |
| **Cert Manager** | TLS 인증서 자동 관리 |
| **Metrics Server** | Pod/Node 메트릭 수집 (HPA용) |
| **EBS CSI Driver** | EBS 볼륨 동적 프로비저닝 |

---

## 인스턴스 타입 권장

### ARM64 (Graviton) - 비용 효율적
| 용도 | 인스턴스 타입 | vCPU | 메모리 |
|------|--------------|------|--------|
| Control Plane | t4g.medium | 2 | 4GB |
| Worker (소규모) | t4g.large | 2 | 8GB |
| Worker (중규모) | t4g.xlarge | 4 | 16GB |

### x86_64 (Intel/AMD)
| 용도 | 인스턴스 타입 | vCPU | 메모리 |
|------|--------------|------|--------|
| Control Plane | t3.medium | 2 | 4GB |
| Worker (소규모) | t3.large | 2 | 8GB |
| Worker (중규모) | t3.xlarge | 4 | 16GB |

---

## 비용 최적화 팁

1. **ARM64 인스턴스 사용**: x86 대비 약 20% 저렴
2. **Spot 인스턴스**: Worker 노드에 Spot 인스턴스 사용
   ```yaml
   spec:
     mixedInstancesPolicy:
       instances:
       - t4g.large
       - t4g.xlarge
       onDemandBase: 1
       spotAllocationStrategy: capacity-optimized
   ```
3. **Cluster Autoscaler**: 사용량에 따라 노드 자동 조절
4. **단일 AZ Control Plane**: 개발/테스트 환경에서는 단일 Control Plane 사용

---

## 참고 링크

- [kOps 공식 문서](https://kops.sigs.k8s.io/)
- [kOps AWS 가이드](https://kops.sigs.k8s.io/getting_started/aws/)
- [kOps 기존 VPC 사용](https://kops.sigs.k8s.io/run_in_existing_vpc/)
- [Cilium 문서](https://docs.cilium.io/)
