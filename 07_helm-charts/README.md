# Helm Charts

FaaS 백엔드 애플리케이션을 Kubernetes에 배포하기 위한 Helm 차트 저장소입니다.

## 프로젝트 구조

```
helm-charts/
└── charts/
    └── backend/          # FaaS 백엔드 서비스 차트
        ├── Chart.yaml
        ├── values.yaml
        ├── README.md
        └── templates/
            ├── _helpers.tpl
            ├── deployment.yaml
            ├── service.yaml
            ├── ingress.yaml
            └── serviceaccount.yaml
```

## 사전 요구사항

- Kubernetes 클러스터 (v1.19+)
- Helm v3.x
- kubectl 설정 완료

## 차트 목록

| 차트 | 버전 | 설명 |
|------|------|------|
| backend | 0.1.0 | FaaS 백엔드 Python 서비스 |

## 빠른 시작

### 1. 기본 설치

```bash
helm install backend ./charts/backend
```

### 2. 커스텀 values 파일 사용

```bash
helm install backend ./charts/backend -f my-values.yaml
```

### 3. 네임스페이스 지정 설치

```bash
helm install backend ./charts/backend -n my-namespace --create-namespace
```

## 주요 설정

### 이미지 설정

```yaml
image:
  repository: 217350599014.dkr.ecr.ap-northeast-2.amazonaws.com/faas-backend
  tag: "latest"
  pullPolicy: Always
```

### 리소스 설정

```yaml
resources:
  requests:
    cpu: 500m
    memory: 512Mi
  limits:
    cpu: 500m
    memory: 512Mi
```

### Ingress 활성화

```yaml
ingress:
  enabled: true
  className: nginx
  hosts:
    - host: backend.example.com
      paths:
        - path: /
          pathType: Prefix
```

## 유용한 명령어

```bash
# 차트 문법 검증
helm lint ./charts/backend

# 렌더링된 매니페스트 확인
helm template backend ./charts/backend

# 설치된 릴리스 목록
helm list

# 릴리스 업그레이드
helm upgrade backend ./charts/backend

# 릴리스 삭제
helm uninstall backend
```

## 환경별 배포

개발, 스테이징, 프로덕션 환경별로 별도의 values 파일을 사용하는 것을 권장합니다:

```bash
# 개발 환경
helm install backend ./charts/backend -f values-dev.yaml

# 프로덕션 환경
helm install backend ./charts/backend -f values-prod.yaml
```

## 라이선스

Internal Use Only
