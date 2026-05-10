# API Reference

Python WASM Deploy Platform REST API 문서입니다.

## Base URL

```
http://localhost:8000
```

## 인증

현재 버전에서는 인증이 필요하지 않습니다.

---

## Health Check

### GET /health

서버 상태를 확인합니다.

**응답:**
```json
{
  "status": "healthy"
}
```

---

## Build API

### POST /api/v1/builds

ZIP 파일을 업로드하여 WASM 빌드를 시작합니다.

**Content-Type:** `multipart/form-data`

**Form Fields:**

| 필드 | 타입 | 필수 | 설명 |
|------|------|------|------|
| app_name | string | ✅ | 애플리케이션 이름 |
| file | file | ✅ | ZIP 파일 (application/zip) |

**요청 예시:**
```bash
curl -X POST http://localhost:8000/api/v1/builds \
  -F "app_name=my-app" \
  -F "file=@my-project.zip"
```

**성공 응답 (200):**
```json
{
  "id": "ba54a28d-8a68-448e-b160-8fcf80bc52c0",
  "app_name": "my-app",
  "status": "pending",
  "oci_reference": null,
  "error_message": null
}
```

**에러 응답 (400) - 잘못된 ZIP:**
```json
{
  "error": "invalid_zip",
  "message": "ZIP extraction failed"
}
```

**에러 응답 (400) - 필수 파일 누락:**
```json
{
  "error": "missing_files",
  "message": "Missing required files: spin.toml",
  "files": ["spin.toml"]
}
```

---

### GET /api/v1/builds/{build_id}

빌드 상태를 조회합니다.

**Path Parameters:**

| 파라미터 | 타입 | 설명 |
|----------|------|------|
| build_id | string | 빌드 ID |

**요청 예시:**
```bash
curl http://localhost:8000/api/v1/builds/ba54a28d-8a68-448e-b160-8fcf80bc52c0
```

**성공 응답 (200):**
```json
{
  "id": "ba54a28d-8a68-448e-b160-8fcf80bc52c0",
  "app_name": "my-app",
  "status": "success",
  "oci_reference": "docker.io/galaxyeunha0530/wasm-test:ba54a28d-8a68-448e-b160-8fcf80bc52c0",
  "error_message": null
}
```

**빌드 상태 값:**

| 상태 | 설명 |
|------|------|
| pending | 빌드 대기 중 |
| building | WASM 빌드 중 |
| pushing | OCI 레지스트리 푸시 중 |
| success | 빌드 성공 |
| failed | 빌드 실패 |

**에러 응답 (404):**
```json
{
  "error": "build_not_found",
  "message": "Build not found: invalid-id"
}
```

---

## Deploy API

### POST /api/v1/apps

빌드된 WASM 앱을 Kubernetes 클러스터에 배포합니다.

**Content-Type:** `application/json`

**Request Body:**

| 필드 | 타입 | 필수 | 기본값 | 설명 |
|------|------|------|--------|------|
| build_id | string | ✅ | - | 빌드 ID |
| namespace | string | ❌ | "default" | Kubernetes 네임스페이스 |
| replicas | integer | ❌ | 1 | 레플리카 수 |

**요청 예시:**
```bash
curl -X POST http://localhost:8000/api/v1/apps \
  -H "Content-Type: application/json" \
  -d '{
    "build_id": "ba54a28d-8a68-448e-b160-8fcf80bc52c0",
    "namespace": "default",
    "replicas": 1
  }'
```

**성공 응답 (200):**
```json
{
  "success": true,
  "app_name": "ba54a28d-8a68-448e-b160-8fcf80bc52c0",
  "namespace": "default",
  "endpoint": null,
  "message": "App deployed successfully"
}
```

**에러 응답 (400) - 빌드 미완료:**
```json
{
  "error": "build_not_ready",
  "message": "Build is not ready. Current status: building"
}
```

**에러 응답 (404) - 빌드 없음:**
```json
{
  "error": "build_not_found",
  "message": "Build not found: invalid-id"
}
```

---

### GET /api/v1/apps

네임스페이스의 모든 SpinApp 목록을 조회합니다.

**Query Parameters:**

| 파라미터 | 타입 | 기본값 | 설명 |
|----------|------|--------|------|
| namespace | string | "default" | Kubernetes 네임스페이스 |

**요청 예시:**
```bash
curl "http://localhost:8000/api/v1/apps?namespace=default"
```

**성공 응답 (200):**
```json
[
  {
    "name": "ba54a28d-8a68-448e-b160-8fcf80bc52c0",
    "namespace": "default",
    "oci_reference": "docker.io/galaxyeunha0530/wasm-test:ba54a28d-8a68-448e-b160-8fcf80bc52c0",
    "replicas": 1,
    "ready_replicas": 1,
    "endpoint": "http://10.43.75.134:80",
    "status": "Running"
  }
]
```

---

### GET /api/v1/apps/{app_name}

특정 앱의 상태를 조회합니다.

**Path Parameters:**

| 파라미터 | 타입 | 설명 |
|----------|------|------|
| app_name | string | 앱 이름 |

**Query Parameters:**

| 파라미터 | 타입 | 기본값 | 설명 |
|----------|------|--------|------|
| namespace | string | "default" | Kubernetes 네임스페이스 |

**요청 예시:**
```bash
curl "http://localhost:8000/api/v1/apps/ba54a28d-8a68-448e-b160-8fcf80bc52c0?namespace=default"
```

**성공 응답 (200):**
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

**앱 상태 값:**

| 상태 | 설명 |
|------|------|
| Running | 정상 실행 중 |
| Pending | 시작 대기 중 |
| Failed | 실행 실패 |

**에러 응답 (404):**
```json
{
  "error": "app_not_found",
  "message": "App not found: invalid-name"
}
```

---

### DELETE /api/v1/apps/{app_name}

SpinApp 리소스를 삭제합니다.

**Path Parameters:**

| 파라미터 | 타입 | 설명 |
|----------|------|------|
| app_name | string | 앱 이름 |

**Query Parameters:**

| 파라미터 | 타입 | 기본값 | 설명 |
|----------|------|--------|------|
| namespace | string | "default" | Kubernetes 네임스페이스 |

**요청 예시:**
```bash
curl -X DELETE "http://localhost:8000/api/v1/apps/ba54a28d-8a68-448e-b160-8fcf80bc52c0?namespace=default"
```

**성공 응답 (200):**
```json
{
  "success": true,
  "message": "App 'ba54a28d-8a68-448e-b160-8fcf80bc52c0' deleted successfully"
}
```

**에러 응답 (404):**
```json
{
  "error": "app_not_found",
  "message": "App not found: invalid-name"
}
```

---

## 에러 코드

| 에러 코드 | HTTP 상태 | 설명 |
|-----------|-----------|------|
| invalid_zip | 400 | ZIP 파일이 손상되었거나 유효하지 않음 |
| missing_files | 400 | 필수 파일(app.py, spin.toml) 누락 |
| build_not_found | 404 | 빌드 ID를 찾을 수 없음 |
| build_not_ready | 400 | 빌드가 아직 완료되지 않음 |
| app_not_found | 404 | 앱을 찾을 수 없음 |
| k8s_error | 500 | Kubernetes API 에러 |
