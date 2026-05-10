# Blue FaaS 테스트 스크립트

API 테스트를 위한 스크립트 모음입니다.

## 사전 설정 (필수)

테스트 스크립트를 실행하기 전에 **반드시** `BLUE_FAAS_URL` 환경변수를 설정해야 합니다.

```bash
# API 서버 URL 설정
export BLUE_FAAS_URL=https://builder.eunha.icu

# 또는 로컬 개발 환경
export BLUE_FAAS_URL=http://localhost:8000
```

환경변수를 설정하지 않으면 다음과 같은 에러가 발생합니다:
```
Error: BLUE_FAAS_URL 환경변수를 설정하세요. 예: export BLUE_FAAS_URL=https://builder.eunha.icu
```

## 스크립트 목록

| 스크립트 | 설명 |
|---------|------|
| `test-all.sh` | 전체 API 테스트 실행 |
| `test-health.sh` | Health Check API 테스트 |
| `test-build.sh` | Build API 테스트 |
| `test-scaffold.sh` | Scaffold API 테스트 |
| `test-deploy.sh` | Deploy API 테스트 (function_id 포함) |
| `test-task-status.sh` | Task Status 조회 테스트 |
| `test-workspace-tasks.sh` | Workspace Tasks 목록 조회 테스트 |
| `cleanup-test-spinapps.sh` | 테스트용 SpinApp 정리 |

## 사용법

### 1. 환경변수 설정

```bash
export BLUE_FAAS_URL=https://builder.eunha.icu
```

### 2. 전체 테스트 실행

```bash
./scripts/test-all.sh
```

### 3. 개별 테스트

```bash
# Health Check
./scripts/test-health.sh

# Build (workspace_id, app_name 지정 가능)
./scripts/test-build.sh my-workspace my-app

# Scaffold (image_ref 지정 가능)
./scripts/test-scaffold.sh my-image:tag

# Deploy (namespace, function_id 지정 가능)
./scripts/test-deploy.sh default fn-my-function

# Task Status 조회
./scripts/test-task-status.sh <task_id> <workspace_id>

# Workspace Tasks 목록
./scripts/test-workspace-tasks.sh <workspace_id>
```

### 4. 테스트 리소스 정리

```bash
# default namespace의 테스트 SpinApp 정리
./scripts/cleanup-test-spinapps.sh

# 특정 namespace 정리
./scripts/cleanup-test-spinapps.sh my-namespace
```

## 빠른 시작

```bash
# 1. 환경변수 설정
export BLUE_FAAS_URL=https://builder.eunha.icu

# 2. 전체 테스트 실행
./scripts/test-all.sh

# 3. 테스트 리소스 정리
./scripts/cleanup-test-spinapps.sh
```

## 출력 예시

```
==========================================
4. Deploy API (with function_id)
==========================================
▶ Request: POST https://builder.eunha.icu/api/v1/deploy
  Body:
    {
      "namespace": "default",
      "image_ref": "ghcr.io/spinkube/...",
      "function_id": "fn-test-001",
      ...
    }

◀ Response:
{
    "app_name": "spin-last-son-6997",
    "namespace": "default",
    "service_name": "spin-last-son-6997",
    ...
}
```
