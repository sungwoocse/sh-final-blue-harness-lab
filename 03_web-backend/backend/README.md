# FaaS Backend API

SoftBank Hackathon FaaS 플랫폼의 공식 FastAPI 백엔드입니다. 워크스페이스·함수 관리, 빌드/배포 파이프라인, 로그·메트릭 연동을 한 곳에서 제공합니다.

> API version `1.0.0` (FastAPI metadata) · Last verified `2025-12-07 KST`

## Deployment Targets
| Target | URL | Notes |
|--------|-----|-------|
| Production API | https://api.eunha.icu | ArgoCD 기준 레퍼런스 환경 |
| Builder Service | https://builder.eunha.icu | Python→WASM 빌드·ECR Push·Spin 배포 |
| Health | https://api.eunha.icu/health | FastAPI 프로브 |

## What This Service Provides
- Workspace / Function CRUD + 실행(`invoke`) API (DynamoDB + S3 기반)
- Python Spin 앱 코드 업로드 → Builder Service 연계 빌드 → ECR Push → SpinApp 배포(쿠버네티스)
- Loki / Prometheus 연동으로 함수별 로그·CPU 메트릭 조회
- IRSA + optional credentials: Builder 연동 시 `username/password` 없이도 동작
- Function 삭제 시 SpinApp(K8s) 자원 정리 및 S3 코드 정리 자동화

## System Overview
```
┌───────────────┐      ┌─────────────────────┐
│   Frontend    │─────▶│  FaaS Backend API   │
└───────────────┘      │ FastAPI @ api.icu   │
                                    └─────────┬────┬─────┘
                                                   │    │
                   ┌────────────────────┘    └──────────────────────┐
                   ▼                                                ▼
    DynamoDB (Single Table)                        Builder Service (Spin)
    S3 (code + build sources)             ┌──────┬────────┬────────┬──────┐
                                                             │Build │ Push   │ Deploy │Tasks │
                                                             └──────┴────────┴────────┴──────┘
                                                   ┌──────────────┐   ┌──────────────────┐
                                                   ▼              ▼   ▼                  ▼
                                             Loki (logs)   Prometheus (metrics)   ECR / EKS
```

## Tech Stack
| Layer | Choice |
|-------|--------|
| Framework | FastAPI + Pydantic |
| Runtime | Python 3.12 |
| Infra | AWS EKS + ALB + ArgoCD |
| Data | DynamoDB (single-table), S3 |
| Observability | Loki, Prometheus |
| Build/Deploy | Custom Builder Service + Spin |

## Repository Layout
```
backend/
├── app/
│   ├── main.py         # FastAPI 엔트리, CORS 설정, 라우터 바인딩
│   ├── config.py       # pydantic-settings 기반 환경 변수
│   ├── database.py     # DynamoDB/S3 래퍼 + build task persistence
│   ├── models.py       # 요청/응답 스키마
│   ├── routers/
│   │   ├── workspaces.py
│   │   ├── functions.py (CRUD + invoke)
│   │   ├── logs.py (Dynamo + Loki)
│   │   ├── metrics.py (Prometheus)
│   │   └── builds.py (build/push/deploy/scaffold)
│   └── utils/timezone.py
├── requirements.txt
├── Dockerfile
└── README.md
```

## API Surface (v1)
### Base
- `GET /health` · `GET /` : 상태 확인
- `GET /docs` / `GET /redoc` : OpenAPI 문서

### Workspaces (`/api/workspaces`)
| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/workspaces` | 워크스페이스 생성 |
| GET | `/api/workspaces` | 전체 목록 |
| GET | `/api/workspaces/{workspace_id}` | 단건 조회 |
| PATCH | `/api/workspaces/{workspace_id}` | 이름/설명 수정 |
| DELETE | `/api/workspaces/{workspace_id}` | 함수/코드 포함 삭제 |

### Functions (`/api/workspaces/{workspace_id}/functions`)
| Method | Path | Description |
|--------|------|-------------|
| POST | `.../functions` | Base64 코드 업로드 + 메타데이터 저장 + S3 저장 |
| GET | `.../functions` | 해당 워크스페이스 함수 목록 |
| GET | `.../functions/{function_id}` | 함수 상세 |
| PATCH | `.../functions/{function_id}` | 코드/런타임/환경변수/URL 업데이트 |
| DELETE | `.../functions/{function_id}` | Dynamo/S3 정리 + `kubectl delete spinapp` 실행 |
| POST | `.../functions/{function_id}/invoke` | 배포된 Spin 서비스 HTTP 호출 및 실행 로그 적재 |

### Build / Deploy (`/api/v1/*`)
| Endpoint | Purpose |
|----------|---------|
| `POST /api/v1/build` | Python/ZIP 업로드 → Builder build task 생성 |
| `POST /api/v1/push` | 기존 아티팩트 기반으로 ECR push |
| `POST /api/v1/build-and-push` | 업로드→빌드→ECR push 원샷 (IRSA 기본) |
| `GET /api/v1/tasks/{task_id}` | build/push/task 상태 폴링 (`completed/done/failed`) |
| `GET /api/v1/workspaces/{ws_id}/tasks` | 워크스페이스별 task 히스토리 |
| `POST /api/v1/scaffold` | Spin 배포 매니페스트 YAML 생성 |
| `POST /api/v1/deploy` | Builder를 통해 SpinApp 배포, `function_id` 레이블 지원 |

### Observability
| Endpoint | Source | Notes |
|----------|--------|-------|
| `GET /api/workspaces/{ws}/functions/{fn}/logs` | DynamoDB | invoke 시 저장된 실행 이력 |
| `GET /api/functions/{fn}/loki-logs` | Loki HTTP API | `function_id` 라벨 기반 실시간 로그 |
| `GET /api/functions/{fn}/metrics` | Prometheus | CPU 사용량(instant + 60분 range) |

📘 전체 스키마는 Swagger(https://api.eunha.icu/docs)에서 확인 가능합니다.

## Typical Workflow
1. `POST /api/workspaces` 로 워크스페이스 생성.
2. `POST /api/workspaces/{ws}/functions` 로 Base64 코드와 설정을 저장 (S3 업로드 동시 수행).
3. `POST /api/v1/build-and-push` 로 Python/ZIP 업로드 → Builder build/push task 시작 (`task_id` 기록).
4. `GET /api/v1/tasks/{task_id}` (또는 workspace task 리스트) 로 wasm/image 링크 확보.
5. `POST /api/v1/deploy` 호출 시 `function_id` 와 이미지 참조를 넘겨 SpinApp 배포, 응답의 `endpoint` 또는 DNS 정보를 함수 `invocationUrl` 로 PATCH.
6. `POST .../invoke` 또는 프론트엔드에서 배포된 엔드포인트 호출, 로그/메트릭 확인.
7. 함수 삭제 시 자동으로 SpinApp 및 S3 코드 정리됨.

## Local Development
### Prerequisites
- Docker (Compose v2)
- AWS 자격 증명 (로컬 DynamoDB/S3 대신 실제 리소스를 사용할 경우)

### `.env` 예시 (`backend/.env`)
```
AWS_REGION=ap-northeast-2
DYNAMODB_TABLE_NAME=sfbank-blue-FaaSData
S3_BUCKET_NAME=sfbank-blue-functions-code-bucket
ENVIRONMENT=development
LOG_LEVEL=DEBUG
CORS_ORIGINS=["http://localhost:5173"]
BUILDER_SERVICE_URL=https://builder.eunha.icu
LOKI_SERVICE_URL=http://loki-stack.logging.svc.cluster.local:3100
PROMETHEUS_SERVICE_URL=http://prometheus-stack-kube-prom-prometheus.monitoring.svc.cluster.local:9090
```

### Run with Docker Compose (project root)
```bash
docker-compose up -d backend
open http://localhost:8000/docs
curl http://localhost:8000/health
docker-compose logs -f backend
```

### Run via Uvicorn (optional)
```bash
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## Configuration Reference
| Env | Default (`config.py`) | Explanation |
|-----|-----------------------|-------------|
| `AWS_REGION` | `ap-northeast-2` | boto3 region |
| `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` | empty | IRSA 사용 시 비워둡니다 |
| `DYNAMODB_TABLE_NAME` | `sfbank-blue-FaaSData` | Single-table 이름 |
| `S3_BUCKET_NAME` | `sfbank-blue-functions-code-bucket` | 함수 코드/빌드 소스 버킷 |
| `ENVIRONMENT` | `development` | FastAPI 응답용 태그 |
| `LOG_LEVEL` | `DEBUG` | Python logging level |
| `CORS_ORIGINS` | 여러 기본값 | 프론트엔드 도메인을 JSON 배열 문자열로 지정 |
| `BUILDER_SERVICE_URL` | `https://builder.eunha.icu` | Builder REST endpoint |
| `LOKI_SERVICE_URL` | `http://loki-stack.logging.svc.cluster.local:3100` | Loki Query Range URL 베이스 |
| `PROMETHEUS_SERVICE_URL` | `http://prometheus-stack...:9090` | Prometheus API 베이스 |

## Data Model & AWS Resources
### DynamoDB (`sfbank-blue-FaaSData`)
- PK/SK 조합
   - Workspace: `PK=WS#{workspace_id}`, `SK=METADATA`
   - Function: `PK=WS#{workspace_id}`, `SK=FN#{function_id}`
   - Build Task: `PK=WS#{workspace_id}`, `SK=BUILD#{task_id}`
   - Logs: `PK=FN#{function_id}`, `SK=LOG#{timestamp}#{log_id}`
- `db_client.refresh_workspace_metrics` 가 invoke 시 워크스페이스 aggregate 갱신

### S3 (`sfbank-blue-functions-code-bucket`)
- `save_code`: `{workspace}/{function}.py`
- `save_build_source`: `build-sources/{workspace}/{task}/{filename}`

## Builder Service Integration Notes
- 백엔드에서는 build/push/deploy API를 호출 후 5초 간격 폴링 (`completed` 또는 `done` 둘 다 성공으로 처리)
- IRSA 기본값 지원: `username=AWS`, `password` 비워도 Builder 측에서 IAM Role 사용
- `build-and-push` 완료 시 DynamoDB task row에 `wasm_path`, `image_url` 저장 → UI가 즉시 Deploy API 호출 가능
- Deploy 시 `function_id` 를 넘겨 Spin Pod 라벨(`label_function_id`)에 반영 → Loki/Prometheus 필터 일치

## Observability
- Invoke 성공/실패시 DynamoDB 실행로그(`ExecutionLog`) + 워크스페이스/함수 메트릭 업데이트
- 실시간 로그: `/api/functions/{function_id}/loki-logs` 가 Loki `query_range` 사용
- 메트릭: `/api/functions/{function_id}/metrics` 가 CPU rate(sum of containers) 60분 range 데이터를 반환

## Testing Snippets
```bash
# Create workspace
curl -X POST https://api.eunha.icu/api/workspaces \
   -H 'Content-Type: application/json' \
   -d '{"name":"demo","description":"Demo workspace"}'

# Upload & build in one shot
curl -X POST https://api.eunha.icu/api/v1/build-and-push \
   -H 'Content-Type: multipart/form-data' \
   -F file=@app.py \
   -F registry_url=217350599014.dkr.ecr.ap-northeast-2.amazonaws.com/blue-final-faas-app \
   -F workspace_id=ws-default

# Invoke function after deployment
curl -X POST https://api.eunha.icu/api/workspaces/ws-default/functions/fn-xxxx/invoke \
   -H 'Content-Type: application/json' \
   -d '{"message":"hello"}'
```

Spin Python handler 스켈레톤:
```python
from spin_sdk import http
from spin_sdk.http import Request, Response

class IncomingHandler(http.IncomingHandler):
      def handle_request(self, request: Request) -> Response:
            return Response(200, {"content-type": "text/plain"}, b"Hello from Blue FaaS!")
```

## Troubleshooting
- **Build timeout**: Builder task는 10분(5초 × 120회)까지 폴링. `GET /api/v1/tasks/{task_id}` 에서 `error_message` 확인.
- **ECR push unauthorized**: IRSA 권한 확인 또는 `username/password` 명시.
- **Deploy endpoint empty**: Deploy 응답에 endpoint가 없으면 백엔드가 자동으로 5초 후 재시도. 그래도 미생성 시 Builder logs 확인.
- **Invoke 400 (NOT_DEPLOYED)**: `invocationUrl` 미설정. Deploy 후 함수 `PATCH` 로 URL 저장하거나 fallback K8s 서비스명 규칙 확인.
- **Loki connection error**: `LOKI_SERVICE_URL` 이 Kubernetes DNS 기준으로 설정되어야 함. 로컬에서 사용할 경우 프록시 필요.

## Change Log
- **2025-12-07**: README 전면 갱신, 빌드/배포/관측 관련 문서 최신화.
- **2025-12-06**: Builder IRSA 지원, `function_id` 레이블 도입, status 호환성 확보 (코드 기준).

---
Maintainers: Backend (Sungwoo Choi) · Infra (Hyunmin Cho) · Observability (Jaejun Lee)
