# Python WASM Deploy Platform

Python Spin 프로젝트를 WebAssembly(WASM)로 빌드하고 RKE2 SpinKube 클러스터에 자동 배포하는 플랫폼입니다.

## 주요 기능

- 🚀 Python 코드 ZIP 파일 업로드 및 자동 빌드
- 📦 WASM 아티팩트를 OCI 레지스트리에 자동 푸시
- ☸️ SpinKube 클러스터에 자동 배포
- 📊 빌드/배포 상태 모니터링
- 🗑️ 앱 삭제 기능

## 빠른 시작

### 1. 서버 실행

```bash
cd python-wasm-deploy
source venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### 2. API 문서 확인

서버 실행 후 브라우저에서 접속:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## API 사용법

### 빌드 API

#### ZIP 파일 업로드 및 빌드 시작

```bash
curl -X POST http://localhost:8000/api/v1/builds \
  -F "app_name=my-app" \
  -F "file=@my-project.zip"
```

**응답 예시:**
```json
{
  "id": "ba54a28d-8a68-448e-b160-8fcf80bc52c0",
  "app_name": "my-app",
  "status": "pending",
  "oci_reference": null,
  "error_message": null
}
```

#### 빌드 상태 조회

```bash
curl http://localhost:8000/api/v1/builds/{build_id}
```

**빌드 상태:**
- `pending`: 빌드 대기 중
- `building`: WASM 빌드 중
- `pushing`: OCI 레지스트리 푸시 중
- `success`: 빌드 성공
- `failed`: 빌드 실패

### 배포 API

#### 앱 배포

```bash
curl -X POST http://localhost:8000/api/v1/apps \
  -H "Content-Type: application/json" \
  -d '{
    "build_id": "ba54a28d-8a68-448e-b160-8fcf80bc52c0",
    "namespace": "default",
    "replicas": 1
  }'
```

#### 앱 목록 조회

```bash
curl "http://localhost:8000/api/v1/apps?namespace=default"
```

#### 앱 상태 조회

```bash
curl "http://localhost:8000/api/v1/apps/{app_name}?namespace=default"
```

**응답 예시:**
```json
{
  "name": "ba54a28d-8a68-448e-b160-8fcf80bc52c0",
  "namespace": "default",
  "oci_reference": "docker.io/galaxyeunha0530/wasm-test:ba54a28d-8a68-448e-b160-8fcf80bc52c0",
  "replicas": 1,
  "ready_replicas": 1,
  "endpoint": "http://10.43.75.134:80",
  "status": "Running"
}
```

#### 앱 삭제

```bash
curl -X DELETE "http://localhost:8000/api/v1/apps/{app_name}?namespace=default"
```

## Python Spin 프로젝트 구조

ZIP 파일에 포함되어야 하는 필수 파일:

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
        body = request.body
        if body:
            data = json.loads(body.decode("utf-8"))
            message = data.get("message", "")
        else:
            message = ""

        response_data = {
            "status": "success",
            "output": message
        }

        return Response(
            200,
            {"content-type": "application/json"},
            bytes(json.dumps(response_data), "utf-8")
        )
```

### spin.toml 예시

```toml
spin_manifest_version = 2

[application]
name = "my-app"
version = "0.1.0"
authors = ["Your Name"]
description = "My Python Spin application"

[[trigger.http]]
route = "/..."
component = "my-app"

[component.my-app]
source = "app.wasm"
[component.my-app.build]
command = "componentize-py -w spin-http componentize app -o app.wasm"
```

## 전체 워크플로우 예시

```bash
# 1. 프로젝트 ZIP 파일 생성
zip -r my-app.zip my-app/

# 2. 빌드 요청
BUILD_RESPONSE=$(curl -s -X POST http://localhost:8000/api/v1/builds \
  -F "app_name=my-app" \
  -F "file=@my-app.zip")
BUILD_ID=$(echo $BUILD_RESPONSE | jq -r '.id')
echo "빌드 ID: $BUILD_ID"

# 3. 빌드 완료 대기 (폴링)
while true; do
  STATUS=$(curl -s http://localhost:8000/api/v1/builds/$BUILD_ID | jq -r '.status')
  echo "빌드 상태: $STATUS"
  if [ "$STATUS" = "success" ] || [ "$STATUS" = "failed" ]; then
    break
  fi
  sleep 5
done

# 4. 배포 (빌드 성공 시)
curl -X POST http://localhost:8000/api/v1/apps \
  -H "Content-Type: application/json" \
  -d "{\"build_id\": \"$BUILD_ID\", \"namespace\": \"default\", \"replicas\": 1}"

# 5. 앱 상태 확인
curl "http://localhost:8000/api/v1/apps/$BUILD_ID?namespace=default"

# 6. 앱 테스트 (클러스터 내부에서)
kubectl run curl-test --image=curlimages/curl --rm -i --restart=Never -- \
  curl -s -X POST "http://$BUILD_ID.default.svc.cluster.local/" \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello!"}'
```

## 설정 파일

### Docker Hub 인증 (dockerhub-secret.txt)

```
DOCKER_USERNAME=your_username
DOCKER_PASSWORD=your_password_or_token
DOCKER_REGISTRY=docker.io
```

### Kubernetes 설정 (kube-config)

표준 kubeconfig 형식의 파일을 프로젝트 루트에 배치합니다.

## 요구사항

- Python 3.11+
- Spin CLI (spin build, spin registry push)
- Spin Kube Plugin (spin kube)
- componentize-py
- RKE2 클러스터 with SpinKube 설치

## 라이선스

MIT License
