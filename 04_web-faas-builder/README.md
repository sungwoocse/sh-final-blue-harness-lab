# Blue FaaS - Spin K8s Deployment Tool

FastAPI 기반 Spin 애플리케이션 배포 도구입니다. Python Spin 애플리케이션을 WASM으로 빌드하고, AWS ECR에 푸시한 후, Kubernetes 환경에 SpinApp으로 배포하는 전체 파이프라인을 제공합니다.

## 주요 기능

- **REST API**: FastAPI 기반 REST API로 모든 작업 수행
- **코드 검증**: MyPy를 통한 Python 코드 정적 타입 검사
- **유연한 업로드**: 단일 .py 파일 또는 zip 아카이브 지원
- **백그라운드 작업**: 빌드/푸시 작업을 백그라운드에서 실행하고 상태 조회
- **AWS 통합**: S3에 소스/아티팩트 저장, DynamoDB에 작업 상태 영속화
- **IRSA 지원**: IAM Roles for Service Accounts를 통한 안전한 AWS 인증
- **Spot 인스턴스**: 기본적으로 Spot 인스턴스 우선 스케줄링
- **오토스케일링**: HPA/KEDA 연동을 위한 enableAutoscaling 지원

## 요구사항

- Python 3.12+
- Spin 2.2+
- Kubernetes 클러스터 (SpinKube 설치됨)
- AWS ECR, S3, DynamoDB 접근 권한

## 설치

```bash
# uv 사용 (권장)
uv sync

# 또는 pip 사용
pip install -e .

# 개발 의존성 포함
pip install -e ".[dev]"
```

## 실행

```bash
# 개발 서버 실행
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# 또는
python main.py
```

## API 엔드포인트

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/health` | 헬스 체크 |
| `POST` | `/api/v1/build` | 파일 업로드 및 빌드 시작 |
| `POST` | `/api/v1/push` | ECR에 이미지 푸시 |
| `POST` | `/api/v1/build-and-push` | 빌드 및 푸시 통합 |
| `POST` | `/api/v1/scaffold` | SpinApp 매니페스트 생성 |
| `POST` | `/api/v1/deploy` | K8s에 SpinApp 배포 |
| `GET` | `/api/v1/tasks/{task_id}` | 작업 상태 조회 |
| `GET` | `/api/v1/workspaces/{workspace_id}/tasks` | 워크스페이스별 작업 목록 |

### API 사용 예시

```bash
# 빌드 요청
curl -X POST http://localhost:8000/api/v1/build \
  -F "file=@app.py" \
  -F "workspace_id=my-workspace"

# 작업 상태 조회
curl http://localhost:8000/api/v1/tasks/{task_id}

# SpinApp 매니페스트 생성
curl -X POST http://localhost:8000/api/v1/scaffold \
  -H "Content-Type: application/json" \
  -d '{"image_ref": "123456789.dkr.ecr.ap-northeast-2.amazonaws.com/spin-app:v1.0.0"}'

# 배포 (Spot 인스턴스 + 오토스케일링 기본 활성화)
curl -X POST http://localhost:8000/api/v1/deploy \
  -H "Content-Type: application/json" \
  -d '{
    "namespace": "default",
    "image_ref": "123456789.dkr.ecr.ap-northeast-2.amazonaws.com/spin-app:v1.0.0",
    "cpu_limit": "500m",
    "memory_limit": "128Mi",
    "function_id": "fn-12345"
  }'
```

## 프로젝트 구조

```
.
├── main.py                 # FastAPI 애플리케이션 진입점
├── Dockerfile              # 멀티스테이지 Docker 빌드
├── k8s/                    # Kubernetes 매니페스트
│   ├── namespace.yaml
│   ├── serviceaccount.yaml # IRSA 설정
│   ├── configmap.yaml      # 환경변수
│   ├── deployment.yaml
│   ├── service.yaml
│   ├── ingress.yaml
│   ├── hpa.yaml
│   ├── kustomization.yaml
│   └── iam-policy.json     # IRSA용 IAM 정책
├── src/
│   ├── api/
│   │   └── routes.py       # API 라우터
│   ├── models/
│   │   ├── api_models.py   # Pydantic 요청/응답 모델
│   │   └── manifest.py     # SpinApp 매니페스트 모델
│   ├── services/
│   │   ├── build.py        # 빌드 서비스 (spin build)
│   │   ├── push.py         # 푸시 서비스 (spin registry push)
│   │   ├── scaffold.py     # 스캐폴드 서비스 (spin kube scaffold)
│   │   ├── deploy.py       # 배포 서비스 (kubectl apply)
│   │   ├── manifest.py     # 매니페스트 YAML 직렬화
│   │   ├── validation.py   # MyPy 검증
│   │   ├── file_handler.py # 파일 처리 (zip, .py)
│   │   ├── task_manager.py # 백그라운드 작업 관리
│   │   ├── s3_storage.py   # S3 저장소
│   │   ├── dynamodb.py     # DynamoDB 영속화
│   │   └── core_service.py # Core Service 클라이언트
│   └── config.py           # 설정 및 상수
└── tests/                  # 테스트 코드
```

## 환경변수

| 변수명 | 설명 | 기본값 |
|--------|------|--------|
| `DYNAMODB_TABLE_NAME` | DynamoDB 테이블명 | `sfbank-blue-FaaSData` |
| `S3_BUCKET_NAME` | S3 버킷명 | `sfbank-blue-functions-code-bucket` |
| `AWS_REGION` | AWS 리전 | `ap-northeast-2` |
| `SPIN_PYTHON_VENV_TEMPLATE` | Spin Python venv 템플릿 경로 | `/opt/spin-python-venv` |
| `CORE_SERVICE_ENDPOINT` | Core Service 엔드포인트 (비어있으면 Mock 사용) | - |
| `ECR_REGISTRY_URL` | ECR 레지스트리 URL | `217350599014.dkr.ecr.ap-northeast-2.amazonaws.com/blue-final-faas-app` |

### 로컬 개발 환경 설정

```bash
# .env.example을 복사하여 .env 생성
cp .env.example .env

# 필요한 값 수정 후 실행
source .env
uvicorn main:app --reload
```

## Kubernetes 배포

### IRSA 설정

```bash
# IAM Policy 생성
aws iam create-policy \
  --policy-name blue-faas-policy \
  --policy-document file://k8s/iam-policy.json

# IRSA 설정
eksctl create iamserviceaccount \
  --name blue-faas-sa \
  --namespace blue-faas \
  --cluster YOUR_CLUSTER_NAME \
  --attach-policy-arn arn:aws:iam::ACCOUNT_ID:policy/blue-faas-policy \
  --approve
```

### 배포

```bash
# Kustomize로 배포
kubectl apply -k k8s/

# 상태 확인
kubectl -n blue-faas get pods
kubectl -n blue-faas logs -l app.kubernetes.io/name=blue-faas -f
```

## SpinApp 레이블

배포되는 SpinApp에는 다음 레이블이 자동으로 추가됩니다:

```yaml
metadata:
  labels:
    app.kubernetes.io/managed-by: blue-faas
spec:
  podLabels:
    faas: "true"
    function_id: "fn-12345"  # deploy 요청 시 function_id 지정 시 추가
```

FaaS Pod 조회:
```bash
# 모든 FaaS Pod 조회
kubectl get pods -l faas=true

# 특정 function_id로 조회
kubectl get pods -l function_id=fn-12345
```

## 테스트

```bash
# 전체 테스트 실행
pytest tests/ -v

# 특정 테스트 실행
pytest tests/test_manifest_roundtrip.py -v
```

## Docker 빌드

```bash
# 이미지 빌드
docker build -t blue-faas:latest .

# ECR에 푸시
aws ecr get-login-password --region ap-northeast-2 | docker login --username AWS --password-stdin ACCOUNT_ID.dkr.ecr.ap-northeast-2.amazonaws.com
docker tag blue-faas:latest ACCOUNT_ID.dkr.ecr.ap-northeast-2.amazonaws.com/blue-faas:latest
docker push ACCOUNT_ID.dkr.ecr.ap-northeast-2.amazonaws.com/blue-faas:latest
```

## Changelog

### 2025-12-05

#### Added
- **function_id 지원**: `/api/v1/deploy` API에 `function_id` 파라미터 추가
  - 배포 시 `function_id`를 지정하면 SpinApp의 `podLabels`에 `function_id` 레이블이 추가됨
  - 이를 통해 특정 함수의 Pod를 쉽게 조회하고 관리 가능
  - 예: `kubectl get pods -l function_id=fn-12345`

- **ECR 레지스트리 URL 환경변수**: `ECR_REGISTRY_URL` 환경변수 추가
  - 기본값: `217350599014.dkr.ecr.ap-northeast-2.amazonaws.com/blue-final-faas-app`
  - `src/config.py`, `.env.example`, `k8s/configmap.yaml`에 설정 추가

## 라이선스

MIT
