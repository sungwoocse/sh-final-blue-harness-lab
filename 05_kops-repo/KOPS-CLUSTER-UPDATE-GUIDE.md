# kOps Cluster Update Guide

## 개요

이 문서는 kOps 클러스터의 Control Plane 확장 및 Cilium ENI 모드 전환 작업 내용을 정리한 것입니다.

## 변경 사항 요약

| 항목 | 변경 전 | 변경 후 |
|------|---------|---------|
| Control Plane | 1개 (ap-northeast-2c) | 3개 (2a: 1개, 2c: 2개) |
| etcd 클러스터 | 1노드 | 3노드 (etcd-a, etcd-c1, etcd-c2) |
| Cilium IPAM | kubernetes | eni |
| Worker Nodes (일반) | 2개 AZ | 1개 AZ (ap-northeast-2a) |
| Spot Nodes | kwasm label 없음 | kwasm.sh/kwasm-node=true 추가 |

---

## 1. cluster.yaml 주요 변경 내용

### 1.1 Cilium ENI 모드 설정

```yaml
networking:
  cilium:
    ipam: eni
    enableNodePort: true
```

### 1.2 Control Plane 3개로 확장

```yaml
# etcd 클러스터 멤버 설정
etcdClusters:
- etcdMembers:
  - encryptedVolume: true
    instanceGroup: control-plane-ap-northeast-2a
    name: a
  - encryptedVolume: true
    instanceGroup: control-plane-ap-northeast-2c-1
    name: c1
  - encryptedVolume: true
    instanceGroup: control-plane-ap-northeast-2c-2
    name: c2
  manager:
    backupRetentionDays: 90
  name: main
```

### 1.3 Instance Groups

```yaml
# Control Plane - ap-northeast-2a
apiVersion: kops.k8s.io/v1alpha2
kind: InstanceGroup
metadata:
  name: control-plane-ap-northeast-2a
spec:
  machineType: t4g.medium
  maxSize: 1
  minSize: 1
  role: ControlPlane
  subnets:
  - public-ap-northeast-2a

# Control Plane - ap-northeast-2c-1
apiVersion: kops.k8s.io/v1alpha2
kind: InstanceGroup
metadata:
  name: control-plane-ap-northeast-2c-1
spec:
  machineType: t4g.medium
  maxSize: 1
  minSize: 1
  role: ControlPlane
  subnets:
  - public-ap-northeast-2c

# Control Plane - ap-northeast-2c-2
apiVersion: kops.k8s.io/v1alpha2
kind: InstanceGroup
metadata:
  name: control-plane-ap-northeast-2c-2
spec:
  machineType: t4g.medium
  maxSize: 1
  minSize: 1
  role: ControlPlane
  subnets:
  - public-ap-northeast-2c

# Worker Nodes - ap-northeast-2a만 유지
apiVersion: kops.k8s.io/v1alpha2
kind: InstanceGroup
metadata:
  name: nodes-ap-northeast-2a
spec:
  machineType: t3a.large
  maxSize: 2
  minSize: 2
  role: Node
  subnets:
  - private-ap-northeast-2a

# Spot Nodes - kwasm label 추가
apiVersion: kops.k8s.io/v1alpha2
kind: InstanceGroup
metadata:
  name: spot-nodes-ap-northeast-2c
spec:
  machineType: t3a.large
  maxSize: 2
  minSize: 1
  mixedInstancesPolicy:
    instances:
    - t3a.large
    - t3.large
    onDemandAboveBase: 0
    onDemandBase: 0
    spotAllocationStrategy: lowest-price
  nodeLabels:
    spot: "true"
    kwasm.sh/kwasm-node: "true"  # 추가됨
  role: Node
  subnets:
  - private-ap-northeast-2c
  taints:
  - spot=true:NoSchedule
```

---

## 2. 클러스터 업데이트 절차

### 2.1 클러스터 설정 업데이트

```bash
# cluster.yaml 수정 후 적용
kops replace -f cluster.yaml --state=s3://sfbank-blue-kops-state-store

# 변경 사항 미리보기
kops update cluster sfbank-blue.k8s.local --state=s3://sfbank-blue-kops-state-store

# 변경 사항 적용
kops update cluster sfbank-blue.k8s.local --state=s3://sfbank-blue-kops-state-store --yes

# Rolling Update 실행
kops rolling-update cluster sfbank-blue.k8s.local --state=s3://sfbank-blue-kops-state-store --yes
```

---

## 3. 트러블슈팅

### 3.1 문제: Static Pod Mirror 생성 실패

**증상:**
- Control Plane 노드에서 kube-controller-manager, kube-scheduler pod가 보이지 않음
- kubelet 로그에 webhook 오류 발생

```
Failed creating a mirror pod: failed calling webhook "pod-identity-webhook.amazonaws.com":
Post "https://pod-identity-webhook.kube-system.svc:443/mutate?timeout=10s": context deadline exceeded
```

**원인:**
- pod-identity-webhook이 worker 노드에서만 실행됨
- 새 control plane 노드에서 webhook 서비스에 연결 불가
- failurePolicy: Fail 설정으로 인해 static pod 등록 차단

**해결:**
```bash
# webhook failurePolicy를 Ignore로 변경
kubectl patch mutatingwebhookconfiguration pod-identity-webhook \
  --type='json' \
  -p='[{"op": "replace", "path": "/webhooks/0/failurePolicy", "value": "Ignore"}]'

# 작업 완료 후 원복
kubectl patch mutatingwebhookconfiguration pod-identity-webhook \
  --type='json' \
  -p='[{"op": "replace", "path": "/webhooks/0/failurePolicy", "value": "Fail"}]'
```

### 3.2 문제: 새 Control Plane 노드가 클러스터에 조인하지 못함

**증상:**
- 새 control plane 노드에서 kube-apiserver가 CrashLoopBackOff
- etcd에 연결 불가 (127.0.0.1:4001 connection refused)

**원인:**
- 이전 control plane 노드(etcd-c)가 종료되었지만 etcd 멤버로 남아있음
- 새 노드(etcd-c1)가 etcd 클러스터에 조인하지 못함

**진단:**
```bash
# etcd 멤버 확인
ssh ubuntu@<control-plane-ip> "sudo ctr --namespace k8s.io run --rm --net-host \
  --mount type=bind,src=/srv/kubernetes,dst=/srv/kubernetes,options=rbind:ro \
  registry.k8s.io/etcd@sha256:042ef9c02799eb9303abf1aa99b09f09d94b8ee3ba0c2dd3f42dc4e1d3dce534 \
  etcdctl-check etcdctl \
  --endpoints=https://127.0.0.1:4001 \
  --cacert=/srv/kubernetes/kube-apiserver/etcd-ca.crt \
  --cert=/srv/kubernetes/kube-apiserver/etcd-client.crt \
  --key=/srv/kubernetes/kube-apiserver/etcd-client.key \
  member list"
```

**해결:**
```bash
# 죽은 etcd 멤버 제거 (member ID 확인 후)
ssh ubuntu@<working-control-plane-ip> "sudo ctr --namespace k8s.io run --rm --net-host \
  --mount type=bind,src=/srv/kubernetes,dst=/srv/kubernetes,options=rbind:ro \
  registry.k8s.io/etcd@sha256:042ef9c02799eb9303abf1aa99b09f09d94b8ee3ba0c2dd3f42dc4e1d3dce534 \
  etcdctl-remove etcdctl \
  --endpoints=https://127.0.0.1:4001 \
  --cacert=/srv/kubernetes/kube-apiserver/etcd-ca.crt \
  --cert=/srv/kubernetes/kube-apiserver/etcd-client.crt \
  --key=/srv/kubernetes/kube-apiserver/etcd-client.key \
  member remove <MEMBER_ID>"
```

### 3.3 문제: cluster-autoscaler Pod Pending

**증상:**
- cluster-autoscaler pod가 Pending 상태로 계속 남음
- topology spread constraints로 인해 스케줄 불가

**원인:**
- Deployment replicas=3이지만 스케줄 가능한 노드가 2개뿐
- Control plane 노드는 taint로 스케줄 불가
- Spot 노드도 taint로 스케줄 불가

**해결:**
```bash
# rolling update 전략 변경 (모든 pod 동시 재시작 허용)
kubectl patch deployment cluster-autoscaler -n kube-system \
  -p '{"spec":{"strategy":{"rollingUpdate":{"maxUnavailable":"100%","maxSurge":0}}}}'

# deployment 재시작
kubectl rollout restart deployment cluster-autoscaler -n kube-system

# replicas를 노드 수에 맞게 조정
kubectl scale deployment cluster-autoscaler -n kube-system --replicas=2
```

### 3.4 문제: Cilium ENI 모드에서 Pod Health Check 실패 (ap-northeast-2a)

**증상:**
- 새 Control Plane 노드(ap-northeast-2a)에서 ebs-csi-node pod가 CrashLoopBackOff
- kubelet → pod IP 연결 timeout
- cilium-health 상태: `Cluster health: 1/6 reachable`, localhost `0/1`

```bash
# 로그 예시
Liveness probe failed: Get "http://10.180.0.88:9808/healthz": context deadline exceeded
Readiness probe failed: Get "http://10.180.0.88:9808/healthz": context deadline exceeded
```

**진단:**
```bash
# 노드에 SSH 접속 후 health endpoint ping 테스트
ssh -i ~/.ssh/id_rsa ubuntu@<node-public-ip> "ping -c 3 10.180.0.146"
# 결과: 100% packet loss

# IP 충돌 확인
ssh -i ~/.ssh/id_rsa ubuntu@<node-public-ip> "ip addr | grep 10.180.0.146"
# 결과: inet 10.180.0.146/24 ... ens5 (Primary ENI에 할당됨!)

# cilium status 확인
kubectl exec cilium-xxxx -n kube-system -- cilium status --verbose | grep -A5 "Controller Status"
# cilium-health-ep 컨트롤러가 계속 실패
```

**근본 원인:**
- Cilium ENI 모드에서 health endpoint IP (예: 10.180.0.146)가 **Primary ENI (ens5)**에 할당됨
- 정상 작동하는 노드에서는 health IP가 **Secondary ENI (ens6)**에 할당됨
- Primary ENI에 IP가 있으면 라우팅 충돌 발생:
  - 라우팅 테이블: `10.180.0.146 dev lxc_health` (veth를 통해 health pod로 가야 함)
  - 실제: IP가 ens5에 있어서 로컬 인터페이스로 처리됨 → health pod에 도달 못함

**작동 노드 vs 문제 노드:**
| 항목 | 작동 노드 (ap-northeast-2c) | 문제 노드 (ap-northeast-2a) |
|------|---------------------------|---------------------------|
| Health IP 위치 | ens6 (Secondary ENI) | ens5 (Primary ENI) |
| Ping 테스트 | 성공 | 실패 (100% loss) |
| Pod Health Check | 정상 | Timeout |

**해결:**
```bash
# 1. 노드에 SSH 접속
ssh -i ~/.ssh/id_rsa ubuntu@<node-public-ip>

# 2. Primary ENI에서 충돌하는 IP 제거

sudo ip addr del 10.180.0.146/24 dev ens5

# 3. 확인
ping -c 3 10.180.0.146  # 이제 성공해야 함
```

**영구적 해결 (근본 원인 수정):**
- 이 문제는 Cilium이 ENI IP pool에서 health endpoint IP를 Primary ENI에 할당할 때 발생
- Cilium ConfigMap에서 ENI 선택 정책 확인 필요
- AWS ENI IP 할당 순서 또는 Cilium IPAM 로직 이슈일 수 있음
- 노드 재시작 또는 cilium pod 재시작 시 문제가 재발할 수 있음

**예방 조치:**
```bash
# Rolling Update 시 새 노드가 조인되면 아래 확인
# 1. cilium health 상태 확인
kubectl exec cilium-xxxx -n kube-system -- cilium-health status

# 2. localhost가 0/1이면 IP 충돌 확인
ssh ubuntu@<node-ip> "ip addr | grep <health-ip>"

# 3. Primary ENI에 있으면 제거
ssh ubuntu@<node-ip> "sudo ip addr del <health-ip>/24 dev ens5"
```

---

## 4. 검증

### 4.1 클러스터 상태 확인

```bash
# 클러스터 validation
kops validate cluster sfbank-blue.k8s.local --state=s3://sfbank-blue-kops-state-store

# 노드 상태 확인
kubectl get nodes -o wide

# Control Plane 컴포넌트 확인
kubectl get pods -n kube-system | grep -E "(etcd|controller|scheduler|apiserver)"

# etcd 클러스터 멤버 확인
kubectl get componentstatuses
```

### 4.2 예상 결과

```
NODE STATUS
NAME                  ROLE           READY
i-xxxxx               control-plane  True
i-xxxxx               control-plane  True
i-xxxxx               control-plane  True
i-xxxxx               node           True
i-xxxxx               node           True
i-xxxxx               node           True

Your cluster sfbank-blue.k8s.local is ready
```

---

## 5. 주의사항

1. **Control Plane 확장 시**
   - 1개에서 3개로 확장 시 etcd 클러스터 마이그레이션 필요
   - 기존 etcd 데이터 백업 확인 필수
   - S3 백업 위치: `s3://<state-store>/<cluster-name>/backups/etcd/main/`

2. **Rolling Update 중**
   - 한 번에 하나의 노드만 업데이트됨
   - validation 실패 시 15분 후 timeout
   - `--cloudonly` 옵션으로 Kubernetes validation 건너뛸 수 있음

3. **Webhook 관련**
   - pod-identity-webhook의 failurePolicy 변경은 임시 조치
   - 작업 완료 후 반드시 원복 필요

4. **etcd 멤버 관리**
   - 죽은 멤버는 수동으로 제거해야 새 멤버 조인 가능
   - etcd 클러스터는 과반수(quorum) 유지 필수

---

## 6. 관련 명령어 Quick Reference

```bash
# 클러스터 상태 확인
kops validate cluster <cluster-name> --state=s3://<state-store>

# 설정 업데이트
kops replace -f cluster.yaml --state=s3://<state-store>
kops update cluster <cluster-name> --state=s3://<state-store> --yes

# Rolling Update
kops rolling-update cluster <cluster-name> --state=s3://<state-store> --yes

# 특정 Instance Group만 업데이트
kops rolling-update cluster <cluster-name> --state=s3://<state-store> --yes \
  --instance-group=<instance-group-name>

# etcd 백업 확인
aws s3 ls s3://<state-store>/<cluster-name>/backups/etcd/main/ --recursive

# Control Plane SSH 접속
ssh -i ~/.ssh/id_rsa ubuntu@<public-ip>
```

---

## 변경 이력

| 날짜 | 작업 내용 | 담당자 |
|------|-----------|--------|
| 2025-12-02 | Control Plane 1개 → 3개 확장, Cilium ENI 모드 전환 | - |
| 2025-12-02 | Cilium ENI Primary ENI IP 충돌 문제 진단 및 해결 문서화 | - |
