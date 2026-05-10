# kOps + AWS ALB Ingress 가이드

## 개요

kOps 클러스터에서 AWS Application Load Balancer (ALB)를 Ingress로 사용하는 방법을 정리한 문서입니다.

---

## 테스트 환경

| 항목 | 값 |
|------|-----|
| kOps 버전 | 1.30 |
| Kubernetes 버전 | 1.30.x |
| CNI | Cilium (overlay mode) |
| Region | ap-northeast-2 (Seoul) |
| VPC | vpc-03b6863c762b38258 |

---

## 테스트 결과 요약

### 성공

| 방식 | 설명 |
|------|------|
| `target-type: instance` + NodePort | ALB → Node:NodePort → Pod |
| 기존 ALB + TargetGroupBinding | 수동으로 생성한 ALB/타겟그룹 연결 |

### 실패

| 방식 | 원인 |
|------|------|
| `target-type: ip` | Cilium overlay 네트워크에서 Pod IP가 VPC에서 라우팅 불가 |

---

## 방법 1: Ingress로 ALB 자동 생성 (권장)

### 1.1 사전 조건

- AWS Load Balancer Controller 설치됨 (kOps에서 자동 설치)
- 서브넷에 적절한 태그 필요:
  - Public 서브넷: `kubernetes.io/role/elb=1`
  - Private 서브넷: `kubernetes.io/role/internal-elb=1`

### 1.2 리소스 생성

```yaml
# namespace.yaml
apiVersion: v1
kind: Namespace
metadata:
  name: my-app
---
# deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: my-app
  namespace: my-app
spec:
  replicas: 2
  selector:
    matchLabels:
      app: my-app
  template:
    metadata:
      labels:
        app: my-app
    spec:
      containers:
      - name: nginx
        image: nginx:latest
        ports:
        - containerPort: 80
---
# service.yaml (NodePort 필수)
apiVersion: v1
kind: Service
metadata:
  name: my-app
  namespace: my-app
spec:
  type: NodePort
  selector:
    app: my-app
  ports:
  - port: 80
    targetPort: 80
    nodePort: 30080  # 원하는 NodePort 지정 (30000-32767)
---
# ingress.yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: my-app-ingress
  namespace: my-app
  annotations:
    alb.ingress.kubernetes.io/scheme: internet-facing
    alb.ingress.kubernetes.io/target-type: instance  # 반드시 instance!
    alb.ingress.kubernetes.io/healthcheck-path: /
spec:
  ingressClassName: alb
  rules:
  - http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: my-app
            port:
              number: 80
```

### 1.3 배포 및 확인

```bash
# 리소스 배포
kubectl apply -f namespace.yaml
kubectl apply -f deployment.yaml
kubectl apply -f service.yaml
kubectl apply -f ingress.yaml

# ALB 주소 확인
kubectl get ingress -n my-app

# 테스트
curl http://<ALB-DNS-NAME>/
```

---

## 방법 2: 기존 ALB에 TargetGroupBinding 연결

이미 생성된 ALB와 타겟 그룹이 있을 때 Kubernetes 서비스를 연결하는 방법입니다.

### 2.1 AWS에서 타겟 그룹 생성

```bash
# 타겟 그룹 생성
aws elbv2 create-target-group \
  --name my-app-tg \
  --protocol HTTP \
  --port 30080 \
  --vpc-id vpc-03b6863c762b38258 \
  --target-type instance \
  --health-check-path / \
  --region ap-northeast-2

# ALB에 리스너 추가
aws elbv2 create-listener \
  --load-balancer-arn <ALB_ARN> \
  --protocol HTTP \
  --port 80 \
  --default-actions Type=forward,TargetGroupArn=<TARGET_GROUP_ARN> \
  --region ap-northeast-2
```

### 2.2 Kubernetes 리소스 생성

```yaml
# service.yaml
apiVersion: v1
kind: Service
metadata:
  name: my-app
  namespace: my-app
spec:
  type: NodePort
  selector:
    app: my-app
  ports:
  - port: 80
    targetPort: 80
    nodePort: 30080
---
# targetgroupbinding.yaml
apiVersion: elbv2.k8s.aws/v1beta1
kind: TargetGroupBinding
metadata:
  name: my-app-tgb
  namespace: my-app
spec:
  serviceRef:
    name: my-app
    port: 80
  targetGroupARN: arn:aws:elasticloadbalancing:ap-northeast-2:217350599014:targetgroup/my-app-tg/xxxxx
  targetType: instance
```

### 2.3 수동 타겟 등록 (IAM 권한 문제 시)

AWS Load Balancer Controller가 수동 생성한 타겟 그룹에 타겟을 등록할 권한이 없을 수 있습니다.
이 경우 수동으로 등록합니다:

```bash
# 노드 인스턴스 ID 확인
kubectl get nodes -o jsonpath='{.items[*].spec.providerID}' | tr ' ' '\n' | awk -F'/' '{print $NF}'

# 타겟 수동 등록
aws elbv2 register-targets \
  --target-group-arn <TARGET_GROUP_ARN> \
  --targets "Id=i-xxxxx,Port=30080" "Id=i-yyyyy,Port=30080" \
  --region ap-northeast-2
```

### 2.4 보안 그룹 설정

ALB가 노드의 NodePort에 접근할 수 있도록 보안 그룹 규칙을 추가해야 합니다:

```bash
# ALB 보안 그룹 확인
ALB_SG=$(aws elbv2 describe-load-balancers \
  --names <ALB_NAME> \
  --query 'LoadBalancers[0].SecurityGroups[0]' \
  --output text --region ap-northeast-2)

# 노드 보안 그룹에 규칙 추가
aws ec2 authorize-security-group-ingress \
  --group-id <NODE_SECURITY_GROUP> \
  --protocol tcp \
  --port 30080 \
  --source-group $ALB_SG \
  --region ap-northeast-2
```

---

## 주요 Ingress Annotations

```yaml
annotations:
  # ALB 스키마 (internet-facing 또는 internal)
  alb.ingress.kubernetes.io/scheme: internet-facing

  # 타겟 타입 (instance 권장, ip는 Cilium overlay에서 동작 안 함)
  alb.ingress.kubernetes.io/target-type: instance

  # 헬스체크 경로
  alb.ingress.kubernetes.io/healthcheck-path: /

  # 헬스체크 포트 (기본: traffic-port)
  alb.ingress.kubernetes.io/healthcheck-port: traffic-port

  # 서브넷 지정 (자동 탐지 안 될 때)
  alb.ingress.kubernetes.io/subnets: subnet-xxx,subnet-yyy

  # 보안 그룹 지정
  alb.ingress.kubernetes.io/security-groups: sg-xxx

  # SSL 인증서 (HTTPS 사용 시)
  alb.ingress.kubernetes.io/certificate-arn: arn:aws:acm:...

  # SSL 리다이렉트
  alb.ingress.kubernetes.io/ssl-redirect: '443'
```

---

## 트러블슈팅

### 1. 타겟이 unhealthy (Request timed out)

**원인:** 보안 그룹에서 ALB → Node:NodePort 트래픽이 차단됨

**해결:**
```bash
aws ec2 authorize-security-group-ingress \
  --group-id <NODE_SG> \
  --protocol tcp \
  --port <NODE_PORT> \
  --source-group <ALB_SG> \
  --region ap-northeast-2
```

### 2. target-type: ip 사용 시 타겟 unhealthy

**원인:** Cilium overlay 네트워크에서 Pod IP (100.96.x.x)가 VPC에서 라우팅 불가

**해결:** `target-type: instance` 사용 (NodePort 서비스 필요)

### 3. TargetGroupBinding에서 AccessDenied 오류

**원인:** AWS Load Balancer Controller IAM 역할이 수동 생성한 타겟 그룹에 대한 권한 없음

**해결:**
- 타겟 그룹에 클러스터 태그 추가:
  ```bash
  aws elbv2 add-tags \
    --resource-arns <TG_ARN> \
    --tags "Key=elbv2.k8s.aws/cluster,Value=<CLUSTER_NAME>" \
    --region ap-northeast-2
  ```
- 또는 수동으로 타겟 등록

### 4. Namespace 삭제가 Terminating 상태에서 멈춤

**원인:** Ingress에 `ingress.k8s.aws/resources` finalizer가 남아있음

**해결:**
```bash
# Ingress의 finalizer 제거
kubectl patch ingress <INGRESS_NAME> -n <NAMESPACE> \
  -p '{"metadata":{"finalizers":null}}' --type=merge

# Namespace의 finalizer 제거
kubectl get ns <NAMESPACE> -o json | \
  jq '.spec.finalizers = []' | \
  kubectl replace --raw "/api/v1/namespaces/<NAMESPACE>/finalize" -f -
```

---

## 참고 링크

- [AWS Load Balancer Controller 문서](https://kubernetes-sigs.github.io/aws-load-balancer-controller/)
- [Ingress Annotations 전체 목록](https://kubernetes-sigs.github.io/aws-load-balancer-controller/latest/guide/ingress/annotations/)
- [TargetGroupBinding 문서](https://kubernetes-sigs.github.io/aws-load-balancer-controller/latest/guide/targetgroupbinding/targetgroupbinding/)

---

## 테스트 결과 (2025-12-01)

| 테스트 | 결과 | ALB URL |
|--------|------|---------|
| Ingress + target-type: ip | ❌ 실패 | - |
| Ingress + target-type: instance | ✅ 성공 | (자동 생성) |
| 기존 ALB + TargetGroupBinding | ✅ 성공 | blue-final-alb-294459071.ap-northeast-2.elb.amazonaws.com |
