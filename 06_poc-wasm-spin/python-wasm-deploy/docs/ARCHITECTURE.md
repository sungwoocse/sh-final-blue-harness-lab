# Architecture

Python WASM Deploy Platform의 아키텍처 문서입니다.

## 시스템 개요

```
┌─────────────┐     ┌──────────────────────────────────────────────┐
│   Client    │     │         Python WASM Deploy Platform          │
│  (curl/UI)  │────▶│                                              │
└─────────────┘     │  ┌─────────────┐  ┌─────────────────────┐   │
                    │  │  FastAPI    │  │    Build Service    │   │
                    │  │  REST API   │──│  - 코드 검증         │   │
                    │  └─────────────┘  │  - WASM 빌드        │   │
                    │                   │  - 레지스트리 푸시   │   │
                    │                   └─────────────────────┘   │
                    │                              │               │
                    │  ┌─────────────┐  ┌─────────────────────┐   │
                    │  │   Build     │  │   Deploy Service    │   │
                    │  │   Storage   │  │  - SpinApp 생성     │   │
                    │  │  (임시파일)  │  │  - 상태 조회        │   │
                    │  └─────────────┘  │  - 앱 삭제          │   │
                    │                   └─────────────────────┘   │
                    └──────────────────────────────────────────────┘
                                           │           │
                              ┌────────────┘           └────────────┐
                              ▼                                     ▼
                    ┌─────────────────┐                   ┌─────────────────┐
                    │  OCI Registry   │                   │  RKE2 Cluster   │
                    │  (Docker Hub)   │                   │  (SpinKube)     │
                    │                 │                   │                 │
                    │ galaxyeunha0530 │                   │ ┌─────────────┐ │
                    │ /wasm-test      │◀──────────────────│ │  SpinApp    │ │
                    └─────────────────┘                   │ │  (WASM)     │ │
                                                          │ └─────────────┘ │
                                                          └─────────────────┘
```

## 컴포넌트 설명

### 1. REST API Server (FastAPI)

- **위치:** `app/api/routes.py`
- **역할:** 클라이언트 요청 처리, 라우팅
- **엔드포인트:**
  - `POST /api/v1/builds` - 빌드 시작
  - `GET /api/v1/builds/{id}` - 빌드 상태 조회
  - `POST /api/v1/apps` - 앱 배포
  - `GET /api/v1/apps` - 앱 목록
  - `GET /api/v1/apps/{name}` - 앱 상태
  - `DELETE /api/v1/apps/{name}` - 앱 삭제

### 2. Build Service

- **위치:** `app/services/build_service.py`
- **역할:** WASM 빌드 파이프라인 관리
- **주요 기능:**
  - 코드 검증 (필수 파일 확인)
  - 빌드 ID 생성 (UUID)
  - WASM 컴파일 (`spin build`)
  - OCI 레지스트리 푸시 (`spin registry push`)

### 3. Deploy Service

- **위치:** `app/services/deploy_service.py`
- **역할:** Kubernetes SpinApp 리소스 관리
- **주요 기능:**
  - SpinApp 매니페스트 생성 (`spin kube scaffold`)
  - SpinApp 배포 (`spin kube deploy`)
  - 앱 상태 조회 (`kubectl get spinapp`)
  - 앱 삭제 (`kubectl delete spinapp`)

### 4. Build Storage

- **위치:** `app/storage/build_storage.py`
- **역할:** 빌드 작업 공간 및 상태 관리
- **주요 기능:**
  - 작업 공간 생성/삭제
  - ZIP 파일 압축 해제
  - 빌드 상태 저장/조회

## 빌드 워크플로우

```
1. ZIP 업로드
   │
   ▼
2. ZIP 압축 해제 & 검증
   │ (app.py, spin.toml 필수)
   ▼
3. 작업 공간 생성
   │
   ▼
4. 가상환경 생성 & 의존성 설치
   │ (requirements.txt)
   ▼
5. WASM 빌드
   │ (spin build → componentize-py)
   ▼
6. OCI 레지스트리 푸시
   │ (spin registry push)
   ▼
7. 빌드 완료
```

## 배포 워크플로우

```
1. 배포 요청 (build_id)
   │
   ▼
2. 빌드 상태 확인
   │ (status == success?)
   ▼
3. SpinApp 배포
   │ (spin kube deploy)
   ▼
4. Pod 생성 & 실행
   │ (containerd-shim-spin)
   ▼
5. Service 생성
   │
   ▼
6. 배포 완료
```

## 빌드 상태 전이

```
PENDING ──▶ BUILDING ──▶ PUSHING ──▶ SUCCESS
                │            │
                └────────────┴──▶ FAILED
```

## 기술 스택

| 구분 | 기술 |
|------|------|
| 언어 | Python 3.11+ |
| 웹 프레임워크 | FastAPI |
| WASM 빌드 | Spin CLI, componentize-py |
| 컨테이너 레지스트리 | Docker Hub (OCI) |
| 오케스트레이션 | Kubernetes (RKE2) |
| WASM 런타임 | SpinKube (containerd-shim-spin) |

## 디렉토리 구조

```
python-wasm-deploy/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI 앱 진입점
│   ├── config.py            # 설정 (Docker/K8s 인증)
│   ├── api/
│   │   ├── __init__.py
│   │   ├── routes.py        # API 라우트
│   │   └── models.py        # Pydantic 모델
│   ├── services/
│   │   ├── __init__.py
│   │   ├── build_service.py # 빌드 서비스
│   │   └── deploy_service.py# 배포 서비스
│   └── storage/
│       ├── __init__.py
│       └── build_storage.py # 빌드 스토리지
├── tests/
│   └── __init__.py
├── docs/
│   ├── API.md               # API 문서
│   └── ARCHITECTURE.md      # 아키텍처 문서
├── examples/
│   └── echo-app/            # 예제 앱
├── requirements.txt
└── README.md
```

## 외부 의존성

### Spin CLI

```bash
# 설치
curl -fsSL https://developer.fermyon.com/downloads/install.sh | bash

# 플러그인 설치
spin plugins install kube
```

### componentize-py

```bash
pip install componentize-py spin-sdk
```

### Kubernetes 클러스터 요구사항

- SpinKube 설치
- containerd-shim-spin 설치
- RuntimeClass `wasmtime-spin-v2` 설정
