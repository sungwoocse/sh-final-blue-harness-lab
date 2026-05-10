# Backend Helm Chart

FaaS Backend 애플리케이션을 위한 Helm Chart입니다.

## 기본 정보

| 항목 | 값 |
|------|-----|
| Image | `217350599014.dkr.ecr.ap-northeast-2.amazonaws.com/faas-backend:latest` |
| Port | 8000 (Python) |
| CPU | 500m (0.5 vCPU) |
| Memory | 512Mi |

## 설치

```bash
# 기본 설치
helm install backend ./backend

# 네임스페이스 지정
helm install backend ./backend -n my-namespace

# 커스텀 values 파일 사용
helm install backend ./backend -f my-values.yaml

# 업그레이드
helm upgrade backend ./backend
```

## 주요 설정값

### 기본 설정

```yaml
replicaCount: 1

image:
  repository: 217350599014.dkr.ecr.ap-northeast-2.amazonaws.com/faas-backend
  tag: latest
  pullPolicy: Always

containerPort: 8000
```

### 리소스 설정

```yaml
resources:
  requests:
    cpu: "500m"
    memory: "512Mi"
  limits:
    cpu: "500m"
    memory: "512Mi"
```

### Service 설정

```yaml
service:
  enabled: true
  type: ClusterIP
  port: 80
  targetPort: 8000
```

### Ingress 설정

```yaml
ingress:
  enabled: false
  className: "nginx"
  annotations:
    kubernetes.io/tls-acme: "true"
  hosts:
    - host: api.example.com
      paths:
        - path: /
          pathType: Prefix
  tls:
    - secretName: backend-tls
      hosts:
        - api.example.com
```

### Tolerations 설정

```yaml
tolerations:
  - key: "node-type"
    operator: "Equal"
    value: "backend"
    effect: "NoSchedule"
  - key: "dedicated"
    operator: "Exists"
    effect: "NoSchedule"
```

### Affinity 설정

```yaml
# Node Affinity
affinity:
  nodeAffinity:
    requiredDuringSchedulingIgnoredDuringExecution:
      nodeSelectorTerms:
        - matchExpressions:
            - key: node-type
              operator: In
              values:
                - backend
    preferredDuringSchedulingIgnoredDuringExecution:
      - weight: 100
        preference:
          matchExpressions:
            - key: zone
              operator: In
              values:
                - ap-northeast-2a

# Pod Anti-Affinity (고가용성)
affinity:
  podAntiAffinity:
    requiredDuringSchedulingIgnoredDuringExecution:
      - labelSelector:
          matchExpressions:
            - key: app.kubernetes.io/name
              operator: In
              values:
                - backend
        topologyKey: kubernetes.io/hostname
```

### 환경 변수 설정

```yaml
# 직접 설정
env:
  - name: DATABASE_URL
    value: "postgresql://localhost:5432/db"
  - name: SECRET_KEY
    valueFrom:
      secretKeyRef:
        name: backend-secrets
        key: secret-key

# ConfigMap/Secret 참조
envFrom:
  - configMapRef:
      name: backend-config
  - secretRef:
      name: backend-secrets
```

### Health Check 설정

```yaml
livenessProbe:
  enabled: true
  httpGet:
    path: /health
    port: 8000
  initialDelaySeconds: 30
  periodSeconds: 10

readinessProbe:
  enabled: true
  httpGet:
    path: /health
    port: 8000
  initialDelaySeconds: 5
  periodSeconds: 10
```

## 사용 예시

### 기본 배포

```bash
helm install backend ./backend
```

### 프로덕션 배포 (Ingress + TLS)

```bash
helm install backend ./backend \
  --set replicaCount=3 \
  --set ingress.enabled=true \
  --set ingress.hosts[0].host=api.myapp.com \
  --set ingress.hosts[0].paths[0].path=/ \
  --set ingress.hosts[0].paths[0].pathType=Prefix
```

### 특정 노드에 배포 (Toleration + Affinity)

```bash
helm install backend ./backend \
  --set tolerations[0].key=dedicated \
  --set tolerations[0].operator=Equal \
  --set tolerations[0].value=backend \
  --set tolerations[0].effect=NoSchedule \
  --set nodeSelector.node-type=backend
```

### 리소스 조정

```bash
helm install backend ./backend \
  --set resources.requests.cpu=1 \
  --set resources.requests.memory=1Gi \
  --set resources.limits.cpu=2 \
  --set resources.limits.memory=2Gi
```

## 템플릿 검증

```bash
# 렌더링된 매니페스트 확인
helm template backend ./backend

# 특정 values로 확인
helm template backend ./backend -f my-values.yaml

# Dry-run 설치
helm install backend ./backend --dry-run --debug
```

## 삭제

```bash
helm uninstall backend
```
