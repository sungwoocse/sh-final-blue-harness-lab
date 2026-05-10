# Harness Bootstrap Notes

이 폴더는 Harness 학습용 초안을 두는 공간입니다.

## 목표

처음부터 전부 자동화하지 않고, 가장 작은 성공 경로를 만듭니다.

1. `05_web-faas-builder` CI 파이프라인 초안
2. `03_web-backend/backend` CI 파이프라인 초안
3. `03_web-backend/frontend` 빌드 파이프라인 초안
4. `04_helm-charts` 배포 단계 초안

## 추천 순서

### Step 1. Builder CI

경로: `05_web-faas-builder`

핵심 단계:

- dependency install
- test
- docker build
- image push

## Step 2. Backend CI

경로: `03_web-backend/backend`

핵심 단계:

- dependency install
- test or lint
- docker build
- image push

## Step 3. Frontend CI

경로: `03_web-backend/frontend`

핵심 단계:

- npm install
- build
- artifact publish or image build

## Step 4. Deploy

경로: `04_helm-charts`

핵심 단계:

- target environment 선택
- image tag 반영
- helm upgrade 또는 GitOps 반영

## 학습 포인트

- 서비스별 파이프라인을 나누는 이유
- 빌드 파이프라인과 배포 파이프라인을 분리하는 이유
- 공통 변수와 시크릿을 어디에 둘지 결정하는 방법
- 이미지 태그 전략을 어떻게 잡는지
