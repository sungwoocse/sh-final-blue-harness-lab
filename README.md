# sh-final-blue Harness Lab

이 저장소는 `sh-final-blue` 계열 공개 레포를 한곳에서 읽고, Harness Engineering 관점으로 학습하기 위한 개인 학습용 monorepo입니다.

목표는 두 가지입니다.

- `sh-final-blue` 계열 프로젝트를 한 곳에서 읽고 구조를 이해한다.
- 이 복사본 위에서 Harness 중심의 CI/CD 실험을 안전하게 진행한다.

## 포함된 로컬 소스

현재 로컬 작업공간에서 복사한 항목은 아래와 같습니다.

- `01_poc-wasm-spin`: SpinKube 기반 WASM/FaaS 실험
- `02_infra-iac`: Terraform 인프라 코드
- `03_web-backend`: 메인 백엔드, 프론트엔드, terraform, 배포 리소스
- `04_helm-charts`: Helm 차트
- `05_web-faas-builder`: Python to WASM 빌드/푸시/배포 서비스
- `06_kops-repo`: kOps 클러스터 운영 문서와 매니페스트
- `07_.github`: 조직 프로필 및 공유 문서

## 로컬에 아직 없는 항목

GitHub 오거나이제이션 기준 레포 중 `2025softbank-hackathon-final`은 현재 이 로컬 작업본에는 포함되어 있지 않습니다. 필요하면 나중에 별도로 가져와 이 monorepo에 편입하면 됩니다.

## 추천 학습 순서

1. `03_web-backend`에서 제품 흐름을 먼저 이해합니다.
2. `05_web-faas-builder`에서 실제 빌드/푸시/배포 파이프라인을 봅니다.
3. `02_infra-iac`, `04_helm-charts`, `06_kops-repo`로 배포 인프라를 따라갑니다.
4. 그 다음 Harness 파이프라인으로 치환하거나 비교합니다.

## 이 레포에서 할 일

- 기존 GitHub 원본과 무관하게 자유롭게 구조를 바꿔본다.
- Harness용 파이프라인 초안을 만든다.
- 어떤 서비스가 빌드 대상이고 어떤 서비스가 배포 대상인지 문서화한다.
- 이후 필요하면 GitHub에 새 원격 레포 `sh-final-blue-harness-lab`를 만들어 연결한다.

## 다음에 바로 볼 문서

- [docs/SERVICE_MAP.md](docs/SERVICE_MAP.md)
- [ci/harness/README.md](ci/harness/README.md)
