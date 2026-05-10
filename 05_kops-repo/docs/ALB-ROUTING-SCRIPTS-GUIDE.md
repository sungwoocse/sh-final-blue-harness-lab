# ALB 라우팅 자동화 스크립트 가이드

기존 ALB에 Kubernetes 서비스를 호스트 기반으로 라우팅하는 자동화 스크립트입니다.

---

## 개요

### 아키텍처

```
                    ┌─────────────────────────────────────────────────────┐
                    │                    AWS ALB                          │
                    │              (blue-final-alb)                       │
                    │                                                     │
                    │  ┌─────────────────────────────────────────────┐   │
                    │  │              Listener (Port 80)              │   │
                    │  │                                               │   │
                    │  │  ┌─────────────────────────────────────┐     │   │
                    │  │  │ Rule 1: Host = api.example.com      │     │   │
 api.example.com ──────────▶  → Target Group: kops-api-tg       │     │   │
                    │  │  └─────────────────────────────────────┘     │   │
                    │  │                                               │   │
                    │  │  ┌─────────────────────────────────────┐     │   │
                    │  │  │ Rule 2: Host = web.example.com      │     │   │
 web.example.com ──────────▶  → Target Group: kops-web-tg       │     │   │
                    │  │  └─────────────────────────────────────┘     │   │
                    │  │                                               │   │
                    │  │  ┌─────────────────────────────────────┐     │   │
                    │  │  │ Default Rule                        │     │   │
      (기타) ──────────────▶  → Target Group: kops-default-tg   │     │   │
                    │  │  └─────────────────────────────────────┘     │   │
                    │  └─────────────────────────────────────────────┘   │
                    └─────────────────────────────────────────────────────┘
                                            │
                                            ▼
                    ┌─────────────────────────────────────────────────────┐
                    │              Kubernetes Cluster                      │
                    │                                                      │
                    │   NodePort:30081    NodePort:30082    NodePort:30080 │
                    │        │                 │                 │         │
                    │        ▼                 ▼                 ▼         │
                    │   ┌─────────┐      ┌─────────┐      ┌─────────┐     │
                    │   │ api-svc │      │ web-svc │      │ default │     │
                    │   └────┬────┘      └────┬────┘      └────┬────┘     │
                    │        ▼                 ▼                 ▼         │
                    │   ┌─────────┐      ┌─────────┐      ┌─────────┐     │
                    │   │ api-pod │      │ web-pod │      │ default │     │
                    │   └─────────┘      └─────────┘      └─────────┘     │
                    └─────────────────────────────────────────────────────┘
```

### 스크립트 목록

| 스크립트 | 설명 |
|----------|------|
| `add-alb-route.sh` | 새로운 호스트 기반 라우팅 추가 |
| `remove-alb-route.sh` | 라우팅 삭제 |
| `list-alb-routes.sh` | 현재 라우팅 목록 조회 |

### 스크립트 위치

```
/home/student/personal-project/softbank2025-hackerton-final/kops-test/scripts/
├── add-alb-route.sh
├── remove-alb-route.sh
└── list-alb-routes.sh
```

---

## 사전 요구사항

### 필수 도구
- AWS CLI (설정 완료)
- kubectl (클러스터 연결됨)
- jq

### 필수 설정 (스크립트 상단에서 수정)

```bash
# add-alb-route.sh 상단의 설정 변수
ALB_NAME="blue-final-alb"           # ALB 이름
VPC_ID="vpc-03b6863c762b38258"      # VPC ID
ALB_SG="sg-036d778d80ba9e20c"       # ALB 보안 그룹
NODE_SG="sg-0f8d6091ab9319761"      # 노드 보안 그룹
REGION="ap-northeast-2"              # AWS 리전
CLUSTER_NAME="sfbank-blue.k8s.local" # kOps 클러스터 이름
```

### Kubernetes 서비스 요구사항

라우팅을 추가하려면 다음 조건을 만족해야 합니다:

1. **Namespace** - 서비스가 존재하는 네임스페이스
2. **Service (NodePort)** - NodePort 타입의 서비스
3. **Deployment/Pod** - 실제 워크로드

---

## add-alb-route.sh - 라우팅 추가

### 사용법

```bash
./add-alb-route.sh <namespace> <service-name> <host> <node-port> [priority]
```

### 파라미터

| 파라미터 | 필수 | 설명 | 예시 |
|----------|------|------|------|
| `namespace` | ✅ | Kubernetes 네임스페이스 | `production` |
| `service-name` | ✅ | Kubernetes 서비스 이름 | `backend` |
| `host` | ✅ | 라우팅할 호스트 도메인 | `api.example.com` |
| `node-port` | ✅ | NodePort 포트 번호 (30000-32767) | `30081` |
| `priority` | ❌ | 리스너 규칙 우선순위 (기본: 자동) | `10` |

### 예시

```bash
# 기본 사용
./add-alb-route.sh production backend api.example.com 30081

# 우선순위 지정
./add-alb-route.sh staging frontend staging.example.com 30082 20

# 개발 환경
./add-alb-route.sh dev api dev-api.example.com 30083 30
```

### 자동 수행 작업

스크립트가 자동으로 수행하는 작업:

```
[1/6] ALB 정보 확인
      - ALB ARN 조회
      - 리스너 ARN 조회

[2/6] 타겟 그룹 생성
      - 이름: kops-{service-name}-tg
      - 포트: {node-port}
      - 타입: instance
      - 헬스체크: HTTP /

[3/6] 보안 그룹 규칙 추가
      - 노드 SG에 ALB → NodePort 허용 규칙 추가

[4/6] 리스너 규칙 추가
      - Host 헤더 기반 라우팅 규칙
      - 우선순위 자동/수동 지정

[5/6] 타겟 등록
      - 모든 Worker 노드를 타겟으로 등록

[6/6] TargetGroupBinding 생성
      - Kubernetes CRD 생성
      - AWS Load Balancer Controller가 관리
```

### 출력 예시

```
========================================
 ALB 라우팅 추가 스크립트
========================================

설정:
  - Namespace: production
  - Service: backend
  - Host: api.example.com
  - NodePort: 30081
  - Target Group: kops-backend-tg

[1/6] ALB 정보 확인...
  ALB ARN: arn:aws:elasticloadbalancing:ap-northeast-2:...
  ALB DNS: blue-final-alb-xxx.ap-northeast-2.elb.amazonaws.com
  Listener ARN: arn:aws:elasticloadbalancing:ap-northeast-2:...

[2/6] 타겟 그룹 생성...
  타겟 그룹 생성됨: arn:aws:elasticloadbalancing:...

[3/6] 보안 그룹 규칙 추가...
  보안 그룹 규칙 추가됨

[4/6] 리스너 규칙 추가 (Host: api.example.com)...
  자동 할당된 우선순위: 10
  리스너 규칙 추가됨 (Priority: 10)

[5/6] 타겟 등록...
  등록된 타겟: i-xxx i-yyy i-zzz

[6/6] TargetGroupBinding 생성...
  targetgroupbinding.elbv2.k8s.aws/backend-tgb created

========================================
 완료!
========================================

라우팅 설정:
  Host: api.example.com
  → ALB: blue-final-alb-xxx.ap-northeast-2.elb.amazonaws.com
  → Target Group: kops-backend-tg
  → NodePort: 30081
  → Service: production/backend

DNS 설정:
  api.example.com → CNAME → blue-final-alb-xxx.ap-northeast-2.elb.amazonaws.com

테스트:
  curl -H "Host: api.example.com" http://blue-final-alb-xxx.ap-northeast-2.elb.amazonaws.com/
```

---

## remove-alb-route.sh - 라우팅 삭제

### 사용법

```bash
./remove-alb-route.sh <namespace> <service-name> <host>
```

### 파라미터

| 파라미터 | 필수 | 설명 |
|----------|------|------|
| `namespace` | ✅ | Kubernetes 네임스페이스 |
| `service-name` | ✅ | Kubernetes 서비스 이름 |
| `host` | ✅ | 삭제할 호스트 도메인 |

### 예시

```bash
./remove-alb-route.sh production backend api.example.com
```

### 자동 수행 작업

```
[1/4] ALB 정보 확인
[2/4] 리스너 규칙 삭제
[3/4] TargetGroupBinding 삭제
[4/4] 타겟 그룹 삭제
```

---

## list-alb-routes.sh - 라우팅 목록 조회

### 사용법

```bash
./list-alb-routes.sh
```

### 출력 예시

```
========================================
 ALB 라우팅 목록
========================================

ALB: blue-final-alb
DNS: blue-final-alb-294459071.ap-northeast-2.elb.amazonaws.com

========== 라우팅 규칙 ==========

[10] b.eunha.icu → kops-backend-tg (healthy: 3/3)
[20] api.example.com → kops-api-tg (healthy: 3/3)
[default] (기본) → kops-nginx-test-tg

========== 타겟 그룹 상세 ==========

- kops-backend-tg (Port: 30081)
- kops-api-tg (Port: 30082)
- kops-nginx-test-tg (Port: 30080)
```

---

## 전체 워크플로우 예시

### 1. 새 서비스 배포

```bash
# 1. Namespace 생성
kubectl create namespace myapp

# 2. Deployment 배포
kubectl apply -f - <<EOF
apiVersion: apps/v1
kind: Deployment
metadata:
  name: myapp
  namespace: myapp
spec:
  replicas: 2
  selector:
    matchLabels:
      app: myapp
  template:
    metadata:
      labels:
        app: myapp
    spec:
      containers:
      - name: myapp
        image: nginx:latest
        ports:
        - containerPort: 80
EOF

# 3. NodePort Service 생성
kubectl apply -f - <<EOF
apiVersion: v1
kind: Service
metadata:
  name: myapp
  namespace: myapp
spec:
  type: NodePort
  selector:
    app: myapp
  ports:
  - port: 80
    targetPort: 80
    nodePort: 30090
EOF
```

### 2. ALB 라우팅 추가

```bash
./scripts/add-alb-route.sh myapp myapp myapp.example.com 30090
```

### 3. DNS 설정

Route 53 또는 DNS 서비스에서:
```
myapp.example.com → CNAME → blue-final-alb-xxx.ap-northeast-2.elb.amazonaws.com
```

### 4. 테스트

```bash
# Host 헤더로 테스트 (DNS 설정 전)
curl -H "Host: myapp.example.com" http://blue-final-alb-xxx.ap-northeast-2.elb.amazonaws.com/

# DNS 설정 후
curl http://myapp.example.com/
```

### 5. 라우팅 삭제 (필요시)

```bash
./scripts/remove-alb-route.sh myapp myapp myapp.example.com
```

---

## 우선순위 (Priority) 설명

ALB 리스너 규칙은 우선순위가 낮은 번호부터 평가됩니다.

| 우선순위 | 설명 |
|----------|------|
| 1-9 | 높은 우선순위 (특수 규칙) |
| 10-99 | 일반 서비스 |
| 100+ | 낮은 우선순위 |
| default | 기본 규칙 (일치하지 않는 모든 요청) |

### 우선순위 충돌 방지

스크립트는 자동으로 사용 가능한 우선순위를 찾습니다:
- 기본값: 10부터 시작
- 10씩 증가하며 빈 우선순위 검색
- 수동 지정도 가능

```bash
# 자동 우선순위
./add-alb-route.sh myapp myapp myapp.example.com 30090

# 수동 우선순위 지정
./add-alb-route.sh myapp myapp myapp.example.com 30090 5
```

---

## 트러블슈팅

### 1. 타겟이 unhealthy 상태

**증상:**
```
[10] api.example.com → kops-api-tg (healthy: 0/3)
```

**원인 및 해결:**

1. **서비스 포트 확인**
   ```bash
   kubectl get svc -n <namespace> <service>
   # targetPort가 컨테이너 포트와 일치하는지 확인
   ```

2. **Pod 상태 확인**
   ```bash
   kubectl get pods -n <namespace>
   kubectl logs -n <namespace> <pod-name>
   ```

3. **보안 그룹 확인**
   ```bash
   aws ec2 describe-security-group-rules \
     --filters "Name=group-id,Values=sg-0f8d6091ab9319761" \
     --query 'SecurityGroupRules[?FromPort==`30090`]'
   ```

### 2. 502 Bad Gateway 오류

**원인:**
- 타겟이 unhealthy
- 서비스 미실행
- 포트 불일치

**해결:**
```bash
# 헬스 상태 확인
./list-alb-routes.sh

# 직접 테스트
kubectl run test --rm -it --image=curlimages/curl -- \
  curl http://<node-ip>:<node-port>/
```

### 3. 규칙이 이미 존재

**증상:**
```
오류: 우선순위 10이 이미 사용 중
```

**해결:**
```bash
# 다른 우선순위 지정
./add-alb-route.sh myapp myapp myapp.example.com 30090 20

# 또는 기존 규칙 삭제 후 재생성
./remove-alb-route.sh myapp myapp myapp.example.com
./add-alb-route.sh myapp myapp myapp.example.com 30090
```

### 4. 타겟 그룹 이름 충돌

**증상:**
```
오류: 타겟 그룹 이름이 이미 존재
```

**원인:** 타겟 그룹 이름은 `kops-{service-name}-tg` 형식으로 생성됨

**해결:**
- 다른 서비스 이름 사용
- 또는 기존 타겟 그룹 삭제

---

## 설정 커스터마이징

### 다른 ALB 사용

스크립트 상단의 변수 수정:

```bash
# add-alb-route.sh
ALB_NAME="your-alb-name"
VPC_ID="vpc-xxxxxxxxx"
ALB_SG="sg-xxxxxxxxx"
NODE_SG="sg-yyyyyyyyy"
```

### 헬스체크 경로 변경

타겟 그룹 생성 후 수정:

```bash
aws elbv2 modify-target-group \
  --target-group-arn <tg-arn> \
  --health-check-path /health \
  --region ap-northeast-2
```

### HTTPS 지원

현재 스크립트는 HTTP(80) 리스너만 지원합니다. HTTPS 지원이 필요한 경우:

1. ALB에 HTTPS(443) 리스너 추가
2. ACM 인증서 연결
3. 스크립트의 `LISTENER_ARN` 쿼리 수정

---

## 현재 라우팅 상태 (2025-12-01)

```
========================================
 ALB 라우팅 목록
========================================

ALB: blue-final-alb
DNS: blue-final-alb-294459071.ap-northeast-2.elb.amazonaws.com

========== 라우팅 규칙 ==========

[10] b.eunha.icu → kops-backend-tg (healthy: 3/3)
[default] (기본) → kops-nginx-test-tg

========== 타겟 그룹 상세 ==========

- kops-backend-tg (Port: 30081)
- kops-nginx-test-tg (Port: 30080)
```
