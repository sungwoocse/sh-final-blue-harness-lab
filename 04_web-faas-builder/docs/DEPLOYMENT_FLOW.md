# Blue FaaS 배포 플로우

Blue FaaS를 사용하여 Spin 애플리케이션을 빌드하고 배포하는 전체 프로세스를 설명합니다.

## 전체 아키텍처

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              Blue FaaS 배포 플로우                            │
└─────────────────────────────────────────────────────────────────────────────┘

  [Client]
     │
     │ 1. POST /api/v1/build-and-push
     │    (Python 소스 파일 업로드)
     ▼
┌─────────────────┐
│   Blue FaaS     │
│   API Server    │
└────────┬────────┘
         │
         │ 2. 백그라운드 태스크 시작
         │    - task_id 즉시 반환
         ▼
┌─────────────────────────────────────────────────────────────────┐
│                     백그라운드 처리                               │
│                                                                 │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐  │
│  │ PENDING  │───▶│ BUILDING │───▶│ PUSHING  │───▶│   DONE   │  │
│  └──────────┘    └────┬─────┘    └────┬─────┘    └──────────┘  │
│                       │               │                         │
│                       ▼               ▼                         │
│                 ┌──────────┐    ┌──────────┐                   │
│                 │    S3    │    │   ECR    │                   │
│                 │ (소스/   │    │ (이미지) │                   │
│                 │  WASM)   │    │          │                   │
│                 └──────────┘    └──────────┘                   │
└─────────────────────────────────────────────────────────────────┘
         │
         │ 3. GET /api/v1/tasks/{task_id}
         │    (상태 polling)
         │
         │ 4. 상태가 "done"이면 image_url 획득
         │
         │ 5. POST /api/v1/deploy
         │    (image_ref = image_url)
         ▼
┌─────────────────┐
│   Kubernetes    │
│   (SpinApp)     │
└─────────────────┘
```

## 단계별 상세 설명

### Step 1: 빌드 및 푸시 요청

Python 소스 파일(.py 또는 .zip)을 업로드하여 빌드 및 ECR 푸시를 요청합니다.

**Request:**
```bash
curl -X POST https://builder.eunha.icu/api/v1/build-and-push \
  -F "file=@app.py" \
  -F "workspace_id=my-workspace" \
  -F "app_name=my-function" \
  -F "registry_url=217350599014.dkr.ecr.ap-northeast-2.amazonaws.com/blue-final-faas-app" \
  -F "username=AWS" \
  -F "password=$(aws ecr get-login-password --region ap-northeast-2)"
```

**Response:**
```json
{
    "task_id": "550e8400-e29b-41d4-a716-446655440000",
    "status": "pending",
    "message": "Build and push task created",
    "source_s3_path": "s3://sfbank-blue-functions-code-bucket/build-sources/my-workspace/550e8400-e29b-41d4-a716-446655440000/"
}
```

### Step 2: 태스크 상태 확인 (Polling)

태스크가 완료될 때까지 상태를 주기적으로 확인합니다.

**Request:**
```bash
curl https://builder.eunha.icu/api/v1/tasks/{task_id}?workspace_id=my-workspace
```

**상태 변화:**
```
pending → building → pushing → done (또는 failed)
```

**진행 중 Response:**
```json
{
    "task_id": "550e8400-e29b-41d4-a716-446655440000",
    "status": "building",
    "result": null,
    "error": null
}
```

**완료 Response:**
```json
{
    "task_id": "550e8400-e29b-41d4-a716-446655440000",
    "status": "done",
    "result": {
        "wasm_path": "s3://sfbank-blue-functions-code-bucket/build-artifacts/550e8400.../app.wasm",
        "image_url": "217350599014.dkr.ecr.ap-northeast-2.amazonaws.com/blue-final-faas-app:a1b2c3d4"
    },
    "error": null
}
```

**실패 Response:**
```json
{
    "task_id": "550e8400-e29b-41d4-a716-446655440000",
    "status": "failed",
    "result": null,
    "error": "MyPy validation failed: app.py:10: error: Incompatible types..."
}
```

### Step 3: 배포 요청

빌드가 완료되면 `image_url`을 사용하여 Kubernetes에 SpinApp을 배포합니다.

**Request:**
```bash
curl -X POST https://builder.eunha.icu/api/v1/deploy \
  -H "Content-Type: application/json" \
  -d '{
    "namespace": "default",
    "image_ref": "217350599014.dkr.ecr.ap-northeast-2.amazonaws.com/blue-final-faas-app:a1b2c3d4",
    "function_id": "fn-my-function-001",
    "enable_autoscaling": true,
    "use_spot": false
  }'
```

**Response:**
```json
{
    "app_name": "spin-happy-cloud-1234",
    "namespace": "default",
    "service_name": "spin-happy-cloud-1234",
    "service_status": "found",
    "endpoint": "spin-happy-cloud-1234.default.svc.cluster.local",
    "enable_autoscaling": true,
    "use_spot": false,
    "error": null
}
```

## API 요약

| 단계 | API | 설명 |
|------|-----|------|
| 1 | `POST /api/v1/build-and-push` | 소스 업로드, 빌드, ECR 푸시 (비동기) |
| 2 | `GET /api/v1/tasks/{task_id}` | 태스크 상태 확인 (polling) |
| 3 | `POST /api/v1/deploy` | K8s에 SpinApp 배포 |

## 태스크 상태 (Task Status)

| 상태 | 설명 |
|------|------|
| `pending` | 태스크 생성됨, 처리 대기 중 |
| `building` | WASM 빌드 중 |
| `pushing` | ECR에 이미지 푸시 중 |
| `done` | 완료 (result에 image_url 포함) |
| `failed` | 실패 (error에 에러 메시지 포함) |

## Deploy 요청 파라미터

| 파라미터 | 필수 | 기본값 | 설명 |
|----------|------|--------|------|
| `namespace` | ✅ | - | K8s 네임스페이스 |
| `image_ref` | ✅ | - | ECR 이미지 URL |
| `function_id` | ❌ | null | Pod 레이블에 추가될 함수 ID |
| `app_name` | ❌ | 자동생성 | SpinApp 이름 |
| `enable_autoscaling` | ❌ | true | HPA 오토스케일링 활성화 |
| `replicas` | ❌ | null | 고정 레플리카 수 (autoscaling=false일 때) |
| `use_spot` | ❌ | true | Spot 인스턴스 우선 스케줄링 |
| `service_account` | ❌ | null | K8s 서비스 어카운트 |
| `cpu_limit` | ❌ | null | CPU 제한 (예: "500m") |
| `memory_limit` | ❌ | null | 메모리 제한 (예: "128Mi") |

## 배포 결과 확인

### SpinApp 확인
```bash
kubectl get spinapp -n default
```

### Pod 확인 (function_id로 필터링)
```bash
kubectl get pods -l function_id=fn-my-function-001
```

### 서비스 엔드포인트
배포 후 반환되는 `endpoint`는 K8s 내부 DNS 주소입니다:
```
{app_name}.{namespace}.svc.cluster.local
```

클러스터 내부에서만 접근 가능합니다. 외부 노출이 필요하면 Ingress를 별도로 설정해야 합니다.

## 예제 코드 (Python)

```python
import requests
import time

BASE_URL = "https://builder.eunha.icu"

# Step 1: 빌드 및 푸시
with open("app.py", "rb") as f:
    response = requests.post(
        f"{BASE_URL}/api/v1/build-and-push",
        files={"file": f},
        data={
            "workspace_id": "my-workspace",
            "app_name": "my-function",
            "registry_url": "217350599014.dkr.ecr.ap-northeast-2.amazonaws.com/blue-final-faas-app",
            "username": "AWS",
            "password": ecr_password,
        }
    )
    task_id = response.json()["task_id"]

# Step 2: 상태 확인 (polling)
while True:
    response = requests.get(
        f"{BASE_URL}/api/v1/tasks/{task_id}",
        params={"workspace_id": "my-workspace"}
    )
    status = response.json()["status"]

    if status == "done":
        image_url = response.json()["result"]["image_url"]
        break
    elif status == "failed":
        raise Exception(response.json()["error"])

    time.sleep(2)  # 2초 대기

# Step 3: 배포
response = requests.post(
    f"{BASE_URL}/api/v1/deploy",
    json={
        "namespace": "default",
        "image_ref": image_url,
        "function_id": "fn-my-function-001",
    }
)
result = response.json()
print(f"Deployed: {result['endpoint']}")
```

## 트러블슈팅

### 빌드 실패 - MyPy 에러
```json
{"status": "failed", "error": "MyPy validation failed: ..."}
```
→ Python 코드의 타입 에러를 수정하세요.

### 빌드 실패 - spin.toml 없음
```json
{"status": "failed", "error": "spin.toml not found in root directory"}
```
→ .zip 파일 루트에 spin.toml이 있어야 합니다. 단일 .py 파일은 자동 생성됩니다.

### 배포 실패 - 네임스페이스 없음
```json
{"detail": "Namespace 'xxx' not found"}
```
→ 네임스페이스를 먼저 생성하세요: `kubectl create namespace xxx`

---

## 코드 업데이트 (재배포)

사용자가 코드를 수정한 경우, **자동 업데이트가 아닌 전체 플로우를 다시 실행**해야 합니다.

### 업데이트 플로우

```
┌─────────────────────────────────────────────────────────────────┐
│                      코드 업데이트 플로우                         │
└─────────────────────────────────────────────────────────────────┘

  [사용자가 코드 수정]
         │
         ▼
  1. POST /api/v1/build-and-push (수정된 파일 업로드)
         │
         │  → 새 task_id 생성
         │  → 새 이미지 태그 생성 (예: abc123 → def456)
         ▼
  2. GET /api/v1/tasks/{task_id} (polling)
         │
         │  → 상태가 "done"이 될 때까지 대기
         │  → 새 image_url 획득
         ▼
  3. POST /api/v1/deploy
         │
         ├─ app_name 같게 지정 → 기존 SpinApp 업데이트 (Rolling Update)
         │
         └─ app_name 생략/다르게 → 새 SpinApp 생성
```

### 기존 앱 업데이트 vs 새 앱 생성

| 방식 | app_name | 결과 |
|------|----------|------|
| **업데이트** | 기존과 같은 이름 지정 | 기존 SpinApp의 이미지만 교체 (Rolling Update) |
| **새로 생성** | 생략 또는 다른 이름 | 새 SpinApp 생성 |

### 예시: 기존 앱 업데이트

```bash
# 첫 번째 배포
curl -X POST /api/v1/deploy -d '{
  "app_name": "my-function",
  "image_ref": "...ecr.../blue-final-faas-app:v1-abc123",
  "namespace": "default"
}'
# → my-function 생성됨

# 코드 수정 후 재빌드...
# → 새 이미지: ...ecr.../blue-final-faas-app:v2-def456

# 업데이트 배포 (같은 app_name 사용)
curl -X POST /api/v1/deploy -d '{
  "app_name": "my-function",
  "image_ref": "...ecr.../blue-final-faas-app:v2-def456",
  "namespace": "default"
}'
# → my-function 이미지가 v2로 업데이트됨 (Rolling Update)
```

### 예시: 새 앱으로 배포

```bash
# app_name 생략 시 자동 생성
curl -X POST /api/v1/deploy -d '{
  "image_ref": "...ecr.../blue-final-faas-app:v2-def456",
  "namespace": "default"
}'
# → spin-random-name-1234 (새 앱) 생성됨
# → 기존 my-function은 그대로 유지됨
```

### 업데이트 시 주의사항

1. **같은 app_name 사용**: 기존 SpinApp을 업데이트하려면 반드시 같은 `app_name`을 지정해야 합니다.

2. **Rolling Update**: Kubernetes가 자동으로 Rolling Update를 수행합니다. 다운타임 없이 새 버전으로 전환됩니다.

3. **function_id 유지**: 같은 `function_id`를 사용하면 모니터링/추적이 용이합니다.

4. **이전 버전 롤백**: 이전 이미지 태그로 다시 deploy하면 롤백됩니다.

### 예제 코드: 업데이트 플로우 (Python)

```python
import requests
import time

BASE_URL = "https://builder.eunha.icu"
APP_NAME = "my-function"  # 고정된 앱 이름
FUNCTION_ID = "fn-my-function-001"

def deploy_or_update(file_path: str, workspace_id: str):
    """코드를 빌드하고 배포/업데이트합니다."""

    # Step 1: 빌드 및 푸시
    with open(file_path, "rb") as f:
        response = requests.post(
            f"{BASE_URL}/api/v1/build-and-push",
            files={"file": f},
            data={
                "workspace_id": workspace_id,
                "registry_url": "217350599014.dkr.ecr.ap-northeast-2.amazonaws.com/blue-final-faas-app",
                "username": "AWS",
                "password": get_ecr_password(),
            }
        )
        task_id = response.json()["task_id"]

    # Step 2: 상태 확인 (polling)
    while True:
        response = requests.get(
            f"{BASE_URL}/api/v1/tasks/{task_id}",
            params={"workspace_id": workspace_id}
        )
        data = response.json()

        if data["status"] == "done":
            image_url = data["result"]["image_url"]
            break
        elif data["status"] == "failed":
            raise Exception(data["error"])

        time.sleep(2)

    # Step 3: 배포 (같은 app_name으로 업데이트)
    response = requests.post(
        f"{BASE_URL}/api/v1/deploy",
        json={
            "app_name": APP_NAME,  # 같은 이름 → 업데이트
            "namespace": "default",
            "image_ref": image_url,
            "function_id": FUNCTION_ID,
        }
    )

    result = response.json()
    print(f"Deployed/Updated: {result['app_name']}")
    print(f"Endpoint: {result['endpoint']}")
    return result

# 사용 예시
# 첫 배포
deploy_or_update("app.py", "my-workspace")

# 코드 수정 후 업데이트
deploy_or_update("app.py", "my-workspace")  # 같은 함수 호출 → 업데이트됨
```
