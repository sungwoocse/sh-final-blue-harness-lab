# kOps 클러스터 부트스트랩 실패 트러블슈팅 리포트

**날짜**: 2025-12-02
**클러스터**: sfbank-blue.k8s.local
**Kubernetes 버전**: 1.33.6

---

## 증상

클러스터 배포 후 다음과 같은 문제 발생:
- 모든 Pod의 IP가 `<none>`
- Node의 `INTERNAL-IP`, `EXTERNAL-IP`가 `<none>`
- `aws-cloud-controller-manager`, `kops-controller` CrashLoopBackOff
- `kubectl get nodes` 로컬에서 timeout

---

## 근본 원인

### MutatingWebhookConfiguration의 Chicken-Egg 문제

kOps가 클러스터 부트스트랩 시 **Webhook들을 먼저 등록**했지만, 해당 Webhook의 **백엔드 Pod가 아직 실행되지 않은 상태**에서 Webhook이 활성화되어 **필수 리소스 생성이 차단**됨.

```
문제의 Webhook들:
1. aws-load-balancer-webhook (mservice.elbv2.k8s.aws)
2. pod-identity-webhook (pod-identity-webhook.amazonaws.com)
```

---

## 문제 발생 체인

```
1. kOps update cluster 실행
   ↓
2. MutatingWebhookConfiguration 생성됨 (aws-load-balancer-webhook, pod-identity-webhook)
   ↓
3. Webhook 백엔드 Pod들은 Worker 노드에 스케줄 필요 (Pending 상태)
   ↓
4. kube-apiserver가 "kubernetes" Service 생성 시도
   ↓
5. aws-load-balancer-webhook이 Service mutate 시도
   ↓
6. Webhook endpoint 없음 → Service 생성 실패
   ↓
   ┌──────────────────────────────────────────────────────┐
   │ "kubernetes" Service가 없어서:                        │
   │ - Pod들이 KUBERNETES_SERVICE_HOST 환경변수 없음        │
   │ - in-cluster config 로드 실패                         │
   │ - aws-cloud-controller-manager CrashLoopBackOff      │
   │ - kops-controller CrashLoopBackOff                   │
   └──────────────────────────────────────────────────────┘
   ↓
7. aws-cloud-controller-manager가 실행 안됨
   ↓
8. Node IP 초기화 안됨 (INTERNAL-IP, EXTERNAL-IP = <none>)
   ↓
9. kubelet이 API server와 통신 불가 (hostname으로 resolving 실패)
   ↓
10. 전체 클러스터 부트스트랩 실패
```

---

## 상세 에러 로그

### kube-apiserver 로그
```
E1202 09:21:34.964550 controller.go:163] "Unhandled Error"
err="unable to sync kubernetes service: Internal error occurred:
failed calling webhook \"mservice.elbv2.k8s.aws\":
failed to call webhook: Post \"https://aws-load-balancer-webhook-service.kube-system.svc:443/mutate-v1-service?timeout=10s\":
no endpoints available for service \"aws-load-balancer-webhook-service\""
```

### kops-controller 로그
```
E1202 09:18:05.011591 config.go:138] "unable to load in-cluster config"
"error"="unable to load in-cluster configuration,
KUBERNETES_SERVICE_HOST and KUBERNETES_SERVICE_PORT must be defined"
```

### aws-cloud-controller-manager 로그
```
F1202 09:18:18.838294 main.go:84] unable to execute command:
invalid configuration: no configuration has been provided,
try setting KUBERNETES_MASTER environment variable
```

---

## 해결 방법

### 즉시 해결 (수동)

문제가 되는 MutatingWebhookConfiguration 삭제:

```bash
kubectl delete mutatingwebhookconfiguration \
  aws-load-balancer-webhook \
  pod-identity-webhook
```

삭제 후:
1. `kubernetes` Service 자동 생성됨
2. `aws-cloud-controller-manager` 정상 시작
3. Node IP 할당됨
4. `kops-controller` 정상 시작
5. Worker 노드 조인 시작

---

## 영향 받은 컴포넌트

| 컴포넌트 | 문제 | 해결 후 상태 |
|---------|------|-------------|
| kubernetes Service | 생성 실패 | 생성됨 |
| aws-cloud-controller-manager | CrashLoopBackOff | Running |
| kops-controller | CrashLoopBackOff | Running |
| Node IP | `<none>` | 할당됨 |
| cert-manager | ContainerCreating | Running |
| Worker 노드 | Not joined | Joining |

---

## 권장 사항

### 1. kOps 이슈 확인
이 문제는 kOps의 부트스트랩 순서 문제로 보임. 관련 GitHub 이슈 확인 필요:
- Webhook을 Pod가 Ready 된 후에 활성화하는 로직 필요
- 또는 Webhook의 `failurePolicy: Ignore` 기본 설정 검토

### 2. cluster.yaml 조정 고려
부트스트랩 문제 방지를 위해 일부 애드온 비활성화 후 수동 설치 고려:
```yaml
# 초기 부트스트랩 시 비활성화
awsLoadBalancerController:
  enabled: false
podIdentityWebhook:
  enabled: false
```

### 3. ValidatingWebhookConfiguration 확인
Mutating 외에 Validating webhook도 동일한 문제 유발 가능:
```bash
kubectl get validatingwebhookconfiguration
```

---

## 참고

- kOps 버전: (기본 설치 버전)
- Kubernetes 버전: 1.33.6
- CNI: Cilium
- Cloud Provider: AWS (external)
