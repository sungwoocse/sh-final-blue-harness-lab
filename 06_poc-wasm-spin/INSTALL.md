# Kubernetes 설치 가이드

이 문서는 SpinKube 기반 WebAssembly FaaS 환경 구축을 위한 설치 가이드입니다.

## 사전 준비

### kubeconfig 설정
```bash
source ./setup-kube.sh
```

## 클러스터 정보

| 항목 | 값 |
|------|-----|
| 서버 | https://192.168.50.235:6443 |
| Kubernetes 버전 | v1.33.6+rke2r1 |

### 노드 구성
| 노드 | 역할 |
|------|------|
| softbank | control-plane, etcd, master |
| softbank-worker1 | worker |

---

## 설치 순서

### 1. cert-manager 설치

cert-manager는 Kubernetes에서 TLS 인증서를 자동으로 관리하는 컨트롤러입니다.

```bash
# cert-manager v1.14.3 설치
kubectl apply -f https://github.com/cert-manager/cert-manager/releases/download/v1.14.3/cert-manager.yaml

# webhook이 준비될 때까지 대기
kubectl wait --for=condition=available --timeout=300s deployment/cert-manager-webhook -n cert-manager
```

#### 설치 확인
```bash
kubectl get pods -n cert-manager
```

예상 출력:
```
NAME                                       READY   STATUS    RESTARTS   AGE
cert-manager-xxxxxxxxxx-xxxxx              1/1     Running   0          XXm
cert-manager-cainjector-xxxxxxxxxx-xxxxx   1/1     Running   0          XXm
cert-manager-webhook-xxxxxxxxxx-xxxxx      1/1     Running   0          XXm
```

---

### 2. Spin Operator 설치

Spin Operator는 WebAssembly(Wasm) 애플리케이션을 Kubernetes에서 실행하기 위한 런타임입니다.

#### 2.1 RuntimeClass 설치
```bash
kubectl apply -f https://github.com/spinframework/spin-operator/releases/download/v0.6.1/spin-operator.runtime-class.yaml
```

#### 2.2 CRDs 설치
```bash
kubectl apply -f https://github.com/spinframework/spin-operator/releases/download/v0.6.1/spin-operator.crds.yaml
```

#### 2.3 Spin Operator (Helm)
```bash
helm install spin-operator \
  --namespace spin-operator \
  --create-namespace \
  --version 0.6.1 \
  --wait \
  oci://ghcr.io/spinframework/charts/spin-operator
```

#### 2.4 Shim Executor 설치
```bash
kubectl apply -f https://github.com/spinframework/spin-operator/releases/download/v0.6.1/spin-operator.shim-executor.yaml
```

#### 설치 확인
```bash
# RuntimeClass 확인
kubectl get runtimeclass wasmtime-spin-v2

# CRDs 확인
kubectl get crds | grep spinkube

# spin-operator pod 확인
kubectl get pods -n spin-operator

# SpinAppExecutor 확인
kubectl get spinappexecutor
```

예상 출력:
```
NAME               HANDLER   AGE
wasmtime-spin-v2   spin      XXs

spinappexecutors.core.spinkube.dev   XXXX-XX-XXTXX:XX:XXZ
spinapps.core.spinkube.dev           XXXX-XX-XXTXX:XX:XXZ

NAME                                         READY   STATUS    RESTARTS   AGE
spin-operator-controller-manager-xxxxxxxxx   1/1     Running   0          XXs

NAME                   AGE
containerd-shim-spin   XXs
```

---

### 3. RKE2 노드에 Spin 런타임 설치 (필수)

RKE2 클러스터에서는 각 worker 노드에 containerd-shim-spin을 직접 설치해야 합니다.

#### 3.1 containerd-shim-spin 바이너리 설치

각 worker 노드에 SSH 접속하여 실행:

```bash
# containerd-shim-spin v0.22.0 다운로드 및 설치
sudo curl -fsSL -o /tmp/containerd-shim-spin-v2.tar.gz \
  https://github.com/spinframework/containerd-shim-spin/releases/download/v0.22.0/containerd-shim-spin-v2-linux-x86_64.tar.gz
sudo tar -xzf /tmp/containerd-shim-spin-v2.tar.gz -C /usr/local/bin
sudo chmod +x /usr/local/bin/containerd-shim-spin-v2
```

#### 3.2 RKE2 containerd 설정 추가

```bash
# config.toml.tmpl 생성
sudo tee /var/lib/rancher/rke2/agent/etc/containerd/config.toml.tmpl > /dev/null << 'EOF'
version = 3

[plugins."io.containerd.cri.v1.runtime".containerd.runtimes.spin]
  runtime_type = "io.containerd.spin.v2"

[plugins."io.containerd.cri.v1.runtime".containerd.runtimes.spin.options]
  BinaryPath = "/usr/local/bin/containerd-shim-spin-v2"
  SystemdCgroup = true
EOF
```

#### 3.3 RKE2 에이전트 재시작

```bash
sudo systemctl restart rke2-agent
```

#### 설치 확인
```bash
# containerd 설정 확인
sudo cat /var/lib/rancher/rke2/agent/etc/containerd/config.toml | grep -A5 spin
```

---

## 설치 요약

| 컴포넌트 | 버전 | 상태 |
|----------|------|------|
| cert-manager | v1.14.3 | ✅ 설치됨 |
| spin-operator runtime-class | v0.6.1 | ✅ 설치됨 |
| spin-operator CRDs | v0.6.1 | ✅ 설치됨 |
| spin-operator controller | v0.6.1 | ✅ 설치됨 |
| spin-operator shim-executor | v0.6.1 | ✅ 설치됨 |
| containerd-shim-spin (노드) | v0.22.0 | ✅ 설치됨 |

---

## 빠른 설치 (전체 명령어)

```bash
# 1. kubeconfig 설정
source ./setup-kube.sh

# 2. cert-manager 설치
kubectl apply -f https://github.com/cert-manager/cert-manager/releases/download/v1.14.3/cert-manager.yaml
kubectl wait --for=condition=available --timeout=300s deployment/cert-manager-webhook -n cert-manager

# 3. spin-operator 설치
kubectl apply -f https://github.com/spinframework/spin-operator/releases/download/v0.6.1/spin-operator.runtime-class.yaml
kubectl apply -f https://github.com/spinframework/spin-operator/releases/download/v0.6.1/spin-operator.crds.yaml
helm install spin-operator \
  --namespace spin-operator \
  --create-namespace \
  --version 0.6.1 \
  --wait \
  oci://ghcr.io/spinframework/charts/spin-operator
kubectl apply -f https://github.com/spinframework/spin-operator/releases/download/v0.6.1/spin-operator.shim-executor.yaml
```
