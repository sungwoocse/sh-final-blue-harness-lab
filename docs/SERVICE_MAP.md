# Service Map

이 문서는 이 monorepo 안에서 어떤 폴더가 어떤 역할을 가지는지, 그리고 Harness에서 어떤 단위로 파이프라인을 나누면 좋은지 정리합니다.

## 추천 파이프라인 단위

| 대상 | 경로 | 성격 | Harness 우선순위 |
|------|------|------|------------------|
| Builder API | `05_web-faas-builder` | Python 백엔드, 빌드 엔진 | 높음 |
| Main Backend API | `03_web-backend/backend` | 사용자용 핵심 API | 높음 |
| Frontend | `03_web-backend/frontend` | Vite 프론트엔드 | 높음 |
| Helm Deploy Assets | `04_helm-charts` | Kubernetes 배포 차트 | 중간 |
| Terraform Infra | `02_infra-iac` | 인프라 프로비저닝 | 중간 |
| Cluster Ops | `06_kops-repo` | 클러스터 운영 자료 | 낮음 |
| WASM POC | `01_poc-wasm-spin` | 초기 실험/PoC | 낮음 |

## 왜 `05_web-faas-builder`부터 시작하나

- 서비스 경계가 분명합니다.
- 테스트 코드가 존재합니다.
- 빌드 결과물과 배포 흐름이 뚜렷합니다.
- 나중에 `03_web-backend`와 연동하기 쉽습니다.

## 첫 번째로 만들 파이프라인 구조

### 1. Builder CI

대상: `05_web-faas-builder`

- Python 의존성 설치
- 테스트 실행
- Docker 이미지 빌드
- 이미지 푸시

### 2. Backend CI

대상: `03_web-backend/backend`

- Python 의존성 설치
- 정적 점검 또는 테스트
- Docker 이미지 빌드
- 이미지 푸시

### 3. Frontend CI

대상: `03_web-backend/frontend`

- Node 의존성 설치
- 프론트엔드 빌드
- 정적 산출물 또는 이미지 생성

### 4. Deploy

대상: `04_helm-charts`

- values 선택
- 이미지 태그 주입
- Kubernetes 배포 또는 GitOps 반영

## 지금 당장 안 해도 되는 것

- `01_poc-wasm-spin` 전체를 CI에 넣는 것
- `06_kops-repo`를 바로 자동화하는 것
- Terraform까지 한 번에 묶는 것

처음에는 애플리케이션 CI/CD와 인프라 CI/CD를 분리해서 보는 편이 훨씬 이해하기 쉽습니다.
