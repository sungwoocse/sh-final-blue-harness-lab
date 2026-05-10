# Backend API Integration Guide (2025-12-07)

프론트엔드 콘솔이 FastAPI 백엔드를 호출할 때 필요한 데이터 모델과 엔드포인트를 최신 스펙에 맞게 정리한 문서입니다. `VITE_API_URL`(기본: `http://localhost:8000`) 아래에 `/api` 네임스페이스가 존재하며, 빌드/배포 파이프라인은 `/api/v1` prefix를 사용합니다.

---

## 📚 목차

1. [데이터 모델](#데이터-모델)
2. [워크스페이스 API](#워크스페이스-api)
3. [함수 API](#함수-api)
4. [로그 & 관측 API](#로그--관측-api)
5. [빌드 & 배포 API](#빌드--배포-api)
6. [에러 포맷 & 공통 규칙](#에러-포맷--공통-규칙)
7. [프론트엔드 연동 노트](#프론트엔드-연동-노트)

---

## 데이터 모델

### Workspace
```typescript
interface Workspace {
  id: string;
  name: string;
  description?: string;
  createdAt: string;       // ISO (KST 변환 완료)
  functionCount: number;   // DynamoDB 집계값
  invocations24h: number;  // 최근 24시간 호출 수 (백엔드 계산)
  errorRate: number;       // errors24h / invocations24h * 100
}
```

### FunctionConfig
```typescript
interface FunctionConfig {
  id: string;
  workspaceId: string;
  name: string;
  description?: string;
  runtime: string;                    // default "Python 3.12"
  memory: number;                     // 128~1024 MB
  timeout: number;                    // 1~900초
  httpMethods: string[];
  environmentVariables: Record<string, string>;
  code: string;                       // Base64 encoded Python source
  invocationUrl?: string | null;      // 배포 완료 시 URL 저장
  status: 'active' | 'disabled';
  lastModified: string;               // ISO KST
  lastDeployed?: string | null;
  invocations24h: number;
  errors24h: number;
  avgDuration: number;                // ms
}
```

> 중요: `code`는 항상 Base64 인코딩 상태로 주고받습니다. 백엔드는 유효성 검증 후 S3에 디코딩된 원본을 저장합니다.

### ExecutionLog / LogsResponse
```typescript
interface ExecutionLog {
  id: string;
  functionId: string;
  timestamp: string;            // ISO KST
  status: 'success' | 'error';
  duration: number;             // ms
  statusCode: number;
  requestBody?: any;
  responseBody?: any;
  logs: string[];
  level: 'info' | 'warn' | 'error';
}

interface LogsResponse {
  logs: ExecutionLog[];
  total: number;
}
```

### Loki & Metrics
```typescript
interface LokiLogEntry {
  timestamp: string;  // nanoseconds string
  line: string;
}

interface LokiLogsResponse {
  logs: LokiLogEntry[];
  total: number;
  function_id: string;
}

interface PrometheusTimeseriesPoint {
  timestamp: number;  // unix seconds
  value: number;
}

interface PrometheusMetricsResponse {
  status: 'success' | 'partial';
  function_id: string;
  data: {
    cpu_total: number | null;      // sum over last minute
    cpu_series: PrometheusTimeseriesPoint[];
    window_seconds: number;        // default 3600
    instant_query: string;         // PromQL used
    range_query: string;           // PromQL used
    raw_instant?: Record<string, any>;
    raw_range?: Record<string, any>;
  };
}
```

### Build / Deploy
```typescript
type BuildStatus = 'pending' | 'running' | 'completed' | 'failed' | 'done';

interface BuildResponse {
  task_id: string;
  status: BuildStatus;
  message: string;
  source_s3_path?: string;
}

interface BuildTaskResult {
  wasm_path?: string | null;
  image_url?: string | null;  // builder가 image_url/image_uri 둘 중 하나 제공
  image_uri?: string | null;
  file_path?: string | null;
}

interface TaskStatusResponse {
  task_id: string;
  status: BuildStatus;
  result: BuildTaskResult | null;
  error: string | null;
}

interface WorkspaceTaskItem {
  task_id: string;
  status: BuildStatus;
  app_name?: string;
  created_at: string;
  updated_at: string;
  result?: BuildTaskResult;
  error?: string | null;
}
```

---

## 워크스페이스 API
| 액션 | Method & Path | Notes |
|------|---------------|-------|
| 생성 | `POST /api/workspaces` | `name` 필수. 응답은 ISO KST 형식. |
| 목록 | `GET /api/workspaces` | Landing 카드, 워크스페이스 선택 등에 사용. |
| 상세 | `GET /api/workspaces/{workspaceId}` | 존재하지 않으면 404 `NOT_FOUND`. |
| 수정 | `PATCH /api/workspaces/{workspaceId}` | `name`는 빈 문자열 불가. |
| 삭제 | `DELETE /api/workspaces/{workspaceId}` | 204 응답. 연관 함수도 정리 필요. |

**sample**
```http
POST /api/workspaces
Content-Type: application/json

{
  "name": "Production",
  "description": "Customer facing"
}
```

```json
{
  "id": "ws-abc123",
  "name": "Production",
  "description": "Customer facing",
  "createdAt": "2025-12-07T12:00:00+09:00",
  "functionCount": 0,
  "invocations24h": 0,
  "errorRate": 0
}
```

---

## 함수 API
### 목록 & 상세
- `GET /api/workspaces/{workspaceId}/functions`
- `GET /api/workspaces/{workspaceId}/functions/{functionId}`

응답은 `FunctionConfig[]` or `FunctionConfig`. `lastModified`/`lastDeployed`는 항상 KST ISO 문자열입니다.

### 생성
```http
POST /api/workspaces/{workspaceId}/functions
Content-Type: application/json
{
  "name": "user-auth",
  "runtime": "Python 3.12",
  "memory": 256,
  "timeout": 30,
  "httpMethods": ["POST"],
  "environmentVariables": {"JWT_SECRET": "***"},
  "code": "ZGVmIGhhbmRsZXIoLi4u"  // Base64
}
```
- 워크스페이스 존재 검증 후 DynamoDB + S3에 저장.
- `code`는 Base64 유효성 체크.
- `httpMethods` 최소 1개.

### 수정 (설정/상태/코드)
```http
PATCH /api/workspaces/{workspaceId}/functions/{functionId}
Content-Type: application/json
{
  "description": "Updated",
  "status": "disabled",
  "invocationUrl": "https://fn.prod.example/run",
  "code": "..." // 선택
}
```
- 전달된 필드만 패치.
- `invocationUrl`은 scheme 없으면 http:// 전체 보정.
- `code` 변경 시 Base64 재검증 + S3 업데이트.
- `lastDeployed`를 보낼 경우 ISO 문자열을 사용하면 KST로 변환 저장.

### 삭제
`DELETE /api/workspaces/{workspaceId}/functions/{functionId}`
- 성공 시 204.
- 백엔드가 `kubectl delete spinapp {functionName}` 실행(없어도 무시) 후 S3와 DynamoDB 레코드 제거.

### Invoke (실제 함수 호출)
```http
POST /api/workspaces/{workspaceId}/functions/{functionId}/invoke
Content-Type: application/json
{ "test": true }
```
- Backend가 `invocationUrl`(없으면 함수명 기반 fallback DNS)로 HTTP POST.
- 응답 body는 실제 함수 응답 그대로 전달.
- 실행 결과가 `ExecutionLog` 형태로 DynamoDB에 적재되고 `invocations24h/errors24h/avgDuration` 갱신.
- 타임아웃 시 504, 네트워크 오류 시 503, 기타 오류 500.

---

## 로그 & 관측 API
### 실행 로그 (DynamoDB)
| Path | 설명 |
|------|------|
| `GET /api/workspaces/{workspaceId}/logs?limit=50` | 워크스페이스 내 최근 로그를 함수별로 모아 최신순 정렬. |
| `GET /api/workspaces/{workspaceId}/functions/{functionId}/logs?limit=100` | 단일 함수 로그. 최대 1000. |

### Loki 실시간 로그
`GET /api/functions/{function_id}/loki-logs?limit=100`
- Promtail이 함수 Pod 라벨 `function_id`로 보낸 로그를 바로 조회.
- 응답은 `LokiLogsResponse`; 실패 시 503(`LOKI_CONNECTION_ERROR`) 또는 500(`LOKI_ERROR`).

### Prometheus 메트릭
`GET /api/functions/{function_id}/metrics`
- 최근 60분 동안의 CPU 사용량(1분 rate)을 반환.
- `status`가 `partial`이면 Instant/Range 둘 중 하나만 성공한 상황.
- 에러 시 503(`PROMETHEUS_CONNECTION_ERROR`).

---

## 빌드 & 배포 API
Builder Service(https://builder.eunha.icu)와 연동하며, 모든 장기 작업은 백엔드 BackgroundTask가 Builder의 작업 ID를 폴링합니다.

### 파일 업로드 & 빌드
`POST /api/v1/build` (multipart/form-data)
| 필드 | 타입 | 필수 | 설명 |
|------|------|------|------|
| `file` | binary | ✅ | `.py` 또는 `.zip` 파일 |
| `app_name` | text | ❌ | 미지정 시 task 기반 이름 자동 생성 |
| `workspace_id` | text | ❌ | 기본 `ws-default` |

응답: `BuildResponse` (`202 Accepted`). 백엔드는 S3에 소스 업로드 후 Builder `/api/v1/build` 호출 → 5초 간격 10분 폴링.

### 작업 상태 / 이력
- `GET /api/v1/tasks/{task_id}` → `TaskStatusResponse`
- `GET /api/v1/workspaces/{workspace_id}/tasks` → 워크스페이스 작업 히스토리 목록

### ECR 이미지 푸시
`POST /api/v1/push` (JSON)
```json
{
  "registry_url": "123456789012.dkr.ecr.ap-northeast-2.amazonaws.com/my-app",
  "username": "AWS",
  "password": "<optional>",
  "tag": "v1.0.0",
  "workspace_id": "ws-default",
  "s3_source_path": "s3://..."
}
```
- IRSA 사용 시 username/password 생략 가능 (백엔드가 빈 문자열 전달).
- 응답은 `BuildResponse`(`task_id`). 백엔드가 Builder `/api/v1/push` 호출 후 상태 폴링.

### SpinApp 매니페스트 생성
`POST /api/v1/scaffold`
```json
{
  "image_ref": "123.dkr.ecr/...:v1.0.0",
  "component": "api",
  "replicas": 1,
  "output_path": "/tmp/spinapp.yaml"
}
```
- Builder `/api/v1/scaffold` 동기 호출, 성공 시 YAML 내용을 그대로 반환.

### Kubernetes 배포
`POST /api/v1/deploy`
```json
{
  "app_name": "my-spin-app",
  "namespace": "default",
  "image_ref": "123.dkr.ecr/...:v1.0.0",
  "enable_autoscaling": true,
  "replicas": 3,            // enable_autoscaling=true 이면 백엔드가 필드 제거
  "use_spot": true,
  "function_id": "fn-xyz789"
}
```
- 추가 필드: `service_account`, `cpu_limit`, `memory_limit`, `cpu_request`, `memory_request`, `custom_tolerations`, `custom_affinity`.
- Builder 응답에 `endpoint`가 없으면 5초 대기 후 재조회.

### 빌드+푸시 통합
`POST /api/v1/build-and-push` (multipart/form-data)
| 필드 | 설명 |
|------|------|
| `file` | `.py`/`.zip` |
| `registry_url` | ECR URL |
| `username`/`password` | IRSA 사용 시 비워둘 수 있음 |
| `tag` | 기본 `sha256` (백엔드가 `task-{task_id}`로 치환) |
| `app_name` | 선택 |
| `workspace_id` | 기본 `ws-default` |

- 백엔드는 Builder `/api/v1/build-and-push` 호출 → 5초 폴링.
- Builder가 `image_url`을 주지 않으면 `registry_url:tag` 조합으로 보완 후 DynamoDB 작업 상태 갱신.

---

## 에러 포맷 & 공통 규칙
```json
{
  "error": {
    "code": "VALIDATION_ERROR" | "NOT_FOUND" | "CREATE_ERROR" | ...,
    "message": "Human readable message",
    "details": { "field": "name" }
  }
}
```
- 404: 리소스 미존재 (`NOT_FOUND`).
- 400: 검증 실패 (`VALIDATION_ERROR`).
- 500: 예외 (`*_ERROR`).
- 502/503/504는 Builder/오브저버빌리티 연동 실패 케이스에서 반환.

---

## 프론트엔드 연동 노트
- `lib/api.ts`는 모든 호출에 `VITE_API_URL` prefix를 붙입니다. 새 API 추가 시 동일한 에러 파싱(`ApiError`)을 재사용하세요.
- 함수 코드 편집 시 **저장 전에 Base64 인코딩**하고, 응답을 디코딩해 Monaco Editor에 표시합니다.
- 함수 삭제 후에는 워크스페이스의 `functionCount`와 캐시된 함수 목록을 즉시 갱신해야 합니다.
- Build/Deploy 플로우는 `npm run dev` 환경에서도 작동하지만, Builder 서비스와의 네트워크가 필요합니다. 장기 작업은 `GET /api/v1/tasks/{task_id}`를 5초 간격으로 폴링(최대 10분)하세요.
- 로그 탭은 DynamoDB 로그와 Loki 스트림을 각각 탭으로 구분해 오류 격리 메시지를 보여주세요.
- Metrics 탭은 Prometheus API 실패 시에도 페이지가 유지되도록 `status === 'partial'`을 허용하고, `raw_*` 데이터를 개발자 도구용으로만 사용하세요.

---

최종 점검일: **2025-12-07**
