# SpinKube FaaS Platform

WebAssembly 기반 Function as a Service (FaaS) 플랫폼입니다. Python 코드를 WASM으로 빌드하고 Kubernetes SpinKube 클러스터에 자동 배포합니다.

## 프로젝트 개요

이 프로젝트는 사용자가 Python 코드를 업로드하면 자동으로 WebAssembly로 컴파일하고 SpinKube 클러스터에 배포하는 서버리스 플랫폼입니다.

### 주요 기능

- **자동 빌드**: Python 코드를 ZIP으로 업로드하면 WASM으로 자동 컴파일
- **OCI 레지스트리 통합**: 빌드된 WASM을 Docker Hub에 자동 푸시
- **자동 배포**: SpinApp으로 Kubernetes 클러스터에 자동 배포
- **상태 모니터링**: 빌드/배포 상태 실시간 조회
- **앱 관리**: 배포된 앱 목록 조회, 삭제 기능

## 아키텍처

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  사용자 (ZIP)   │────▶│  FastAPI 서버    │────▶│  OCI Registry   │
│                 │     │  (빌드/배포 API)  │     │  (Docker Hub)   │
└─────────────────┘     └────────┬─────────┘     └────────┬────────┘
                                 │                        │
                                 ▼                        ▼
                        ┌────────────────────────────────────────┐
                        │         RKE2 Kubernetes Cluster        │
                        │  ┌──────────────┐  ┌────────────────┐  │
                        │  │ spin-operator│  │  SpinApp Pods  │  │
                        │  └──────────────┘  │  (WASM 실행)   │  │
                        │                    └────────────────┘  │
                        └────────────────────────────────────────┘
```

## 기술 스택

| 구성요소 | 기술 | 버전 |
|----------|------|------|
| 웹 프레임워크 | FastAPI | - |
| 컨테이너 오케스트레이션 | RKE2 Kubernetes | v1.33.6 |
| WASM 런타임 | containerd-shim-spin | v0.22.0 |
| SpinKube Operator | spin-operator | v0.6.1 |
| 인증서 관리 | cert-manager | v1.14.3 |
| 빌드 도구 | Spin CLI | - |

## 프로젝트 구조

```
demo-faas/
├── README.md                  # 프로젝트 설명서 (현재 파일)
├── INSTALL.md                 # Kubernetes 설치 가이드
├── setup-kube.sh              # kubeconfig 설정 스크립트
├── .gitignore                 # Git 제외 파일 목록
├── echo-app.zip               # 샘플 Python Spin WASM 프로젝트 (테스트용)
│
├── python-wasm-deploy/        # FastAPI 배포 서비스
│   ├── app/
│   │   ├── main.py            # FastAPI 진입점
│   │   ├── api/
│   │   │   ├── routes.py      # REST API 엔드포인트
│   │   │   └── models.py      # Pydantic 데이터 모델
│   │   ├── services/
│   │   │   ├── build_service.py   # WASM 빌드 서비스
│   │   │   └── deploy_service.py  # SpinApp 배포 서비스
│   │   └── storage/
│   │       └── build_storage.py   # 빌드 상태 저장소
│   ├── docs/                  # API 문서
│   ├── examples/echo-app/     # echo-app.zip 원본 소스
│   └── requirements.txt       # Python 의존성
│
├── simple.yaml                # 예제 SpinApp 매니페스트
└── .kiro/specs/               # 프로젝트 설계 문서
```

## 빠른 시작

### 1. 클러스터 설정

```bash
# kubeconfig 설정
source ./setup-kube.sh

# 클러스터 상태 확인
kubectl get nodes
```

### 2. FastAPI 서버 실행

```bash
cd python-wasm-deploy
source venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### 3. API 문서 확인

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

### 4. 샘플 앱으로 테스트

프로젝트에 포함된 `echo-app.zip`을 사용하여 빠르게 테스트할 수 있습니다:

```bash
# 샘플 앱 빌드 요청
curl -X POST http://localhost:8000/api/v1/builds \
  -F "app_name=echo-app" \
  -F "file=@echo-app.zip"

# 응답에서 build_id 확인 후 배포
curl -X POST http://localhost:8000/api/v1/apps \
  -H "Content-Type: application/json" \
  -d '{"build_id": "{build_id}", "namespace": "default", "replicas": 1}'
```

## API 사용법

### 빌드 요청 (ZIP 업로드)

```bash
# Python Spin 프로젝트를 ZIP으로 압축 후 업로드
curl -X POST http://localhost:8000/api/v1/builds \
  -F "app_name=my-app" \
  -F "file=@my-project.zip"
```

### 빌드 상태 조회

```bash
curl http://localhost:8000/api/v1/builds/{build_id}
```

### 앱 배포

```bash
curl -X POST http://localhost:8000/api/v1/apps \
  -H "Content-Type: application/json" \
  -d '{"build_id": "{build_id}", "namespace": "default", "replicas": 1}'
```

### 앱 목록 조회

```bash
curl "http://localhost:8000/api/v1/apps?namespace=default"
```

### 앱 삭제

```bash
curl -X DELETE "http://localhost:8000/api/v1/apps/{app_name}?namespace=default"
```

## Python Spin 프로젝트 구조

ZIP 파일에 포함되어야 하는 파일:

```
my-project/
├── app.py          # 필수: Python 애플리케이션 코드
├── spin.toml       # 필수: Spin 설정 파일
└── requirements.txt # 선택: Python 의존성
```

### app.py 예시

```python
from spin_sdk.http import IncomingHandler, Request, Response
import json

class IncomingHandler(IncomingHandler):
    def handle_request(self, request: Request) -> Response:
        return Response(
            200,
            {"content-type": "application/json"},
            bytes(json.dumps({"message": "Hello from WASM!"}), "utf-8")
        )
```

### spin.toml 예시

```toml
spin_manifest_version = 2

[application]
name = "my-app"
version = "0.1.0"

[[trigger.http]]
route = "/..."
component = "my-app"

[component.my-app]
source = "app.wasm"
[component.my-app.build]
command = "componentize-py -w spin-http componentize app -o app.wasm"
```

## 클러스터 정보

| 항목 | 값 |
|------|-----|
| API Server | https://192.168.50.235:6443 |
| Kubernetes 버전 | v1.33.6+rke2r1 |
| Master 노드 | softbank (control-plane) |
| Worker 노드 | softbank-worker1 |

## 설치 가이드

전체 설치 과정은 [INSTALL.md](./INSTALL.md)를 참조하세요.

### 설치 요약

```bash
# 1. cert-manager 설치
kubectl apply -f https://github.com/cert-manager/cert-manager/releases/download/v1.14.3/cert-manager.yaml

# 2. spin-operator 설치
kubectl apply -f https://github.com/spinframework/spin-operator/releases/download/v0.6.1/spin-operator.runtime-class.yaml
kubectl apply -f https://github.com/spinframework/spin-operator/releases/download/v0.6.1/spin-operator.crds.yaml
helm install spin-operator --namespace spin-operator --create-namespace --version 0.6.1 oci://ghcr.io/spinframework/charts/spin-operator
kubectl apply -f https://github.com/spinframework/spin-operator/releases/download/v0.6.1/spin-operator.shim-executor.yaml

# 3. Worker 노드에 containerd-shim-spin 설치 (SSH 접속 필요)
# 자세한 내용은 INSTALL.md 참조
```

## 요구사항

### 서버 환경
- Python 3.11+
- Spin CLI
- Spin Kube Plugin
- componentize-py

### 클러스터 환경
- RKE2 Kubernetes v1.33+
- cert-manager v1.14+
- spin-operator v0.6+
- containerd-shim-spin v0.22+

## 라이선스

MIT License
