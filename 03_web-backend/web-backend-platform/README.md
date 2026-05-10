# Web Backend Platform Helm Chart

이 Helm 차트는 `web-backend` 애플리케이션의 API 요청 처리를 담당하는 핵심 서비스인 **Web Backend Platform**을 배포합니다. AWS EC2 인스턴스 위에 **Kops**로 구성된 Kubernetes 클러스터에서 실행되도록 설계되었으며, **Cilium CNI** 환경을 고려하였습니다.

## 역할 및 책임 (Role & Responsibilities)

`web-backend-platform`은 주 백엔드 API 서비스로서 다음과 같은 주요 책임을 가집니다:
- **API 처리**: 프론트엔드 애플리케이션으로부터 오는 RESTful API 요청을 처리합니다.
- **리소스 관리**: 데이터 저장을 위한 AWS DynamoDB 및 파일 저장을 위한 S3와 상호 작용합니다.
- **비즈니스 로직**: 핵심 애플리케이션 로직을 실행합니다.

## 주요 구성 요소 설명 (Key Components)

### 1. ServiceAccount & IAM 권한
`ServiceAccount`는 Pod가 AWS 리소스(DynamoDB, S3 등)에 접근할 수 있도록 **IAM Role**과 연결하는 역할을 합니다 (IRSA - IAM Roles for Service Accounts).
- `values.yaml`의 `serviceAccount.annotations`에 IAM Role ARN을 지정하면, **Kops** 클러스터가 OIDC Provider와 연동되어 있는 경우 Pod에 해당 IAM 권한이 임시 자격 증명으로 주입됩니다.
- 이를 통해 Access Key/Secret Key를 하드코딩하지 않고도 안전하게 AWS 리소스를 제어할 수 있습니다.

### 2. Service Type: NodePort
본 차트에서 Service 타입은 `NodePort`로 구성되어 있습니다. 그 이유는 **AWS Load Balancer Controller**의 동작 모드 때문입니다.
- **Ingress 설정**: `values.yaml`에서 `alb.ingress.kubernetes.io/target-type: instance`로 설정되어 있습니다.
- **동작 원리**: `instance` 모드는 ALB가 트래픽을 EC2 인스턴스의 **NodePort**로 직접 라우팅합니다. 따라서 Service는 ALB가 접근할 수 있도록 포트를 노출해야 하므로 `NodePort` 타입을 사용해야 합니다.
- (참고: `target-type: ip`를 사용하려면 AWS VPC CNI를 사용하여 Pod가 VPC IP를 직접 할당받아야 하지만, 현재 환경은 **Cilium CNI**와 **Kops** 구성이므로 호환성과 안정성을 위해 `instance` 모드(NodePort)가 적합한 선택일 수 있습니다.)

## 아키텍처 (Architecture)

다음 다이어그램은 요청 흐름과 아키텍처를 보여줍니다:

```mermaid
graph LR
    User["사용자"] -->|HTTPS| ALB["AWS ALB Ingress"]
    ALB -->|HTTP| Service["Service: NodePort"]
    Service -->|TCP| Pod["Pod: web-backend"]
    
    subgraph "Kops Kubernetes Cluster (EC2)"
        ALB
        Service
        Pod
    end
    
    subgraph "AWS Cloud"
        Pod -.->|"IRSA (IAM Role)"| IAM["AWS IAM"]
        Pod -->|SDK| DynamoDB[("DynamoDB")]
        Pod -->|SDK| S3[("S3 버킷")]
    end
```

## 전제 조건 (Prerequisites)

- **Kubernetes 1.19+** (Kops managed)
- **Helm 3.0+**
- **Cilium CNI** (네트워크 플러그인)
- **AWS Load Balancer Controller**가 클러스터에 설치되어 있어야 합니다 (Ingress ALB 필수).
- **AWS Certificate Manager (ACM)** 인증서 (HTTPS용, `api.eunha.icu` 도메인 필요).

## 설치 (Installation)

### 1. 값 설정 (Configure Values)
`values.yaml` 파일, 특히 AWS 설정과 Ingress 어노테이션이 올바르게 구성되었는지 확인하십시오.

**중요 단계**: `values.yaml`에 유효한 ACM 인증서 ARN을 반드시 제공해야 합니다:
```yaml
ingress:
  annotations:
    alb.ingress.kubernetes.io/certificate-arn: "arn:aws:acm:REGION:ACCOUNT-ID:certificate/YOUR-CERT-ID"
```

### 2. 차트 설치/업그레이드
`web-backend-platform` 릴리스 이름으로 차트를 설치하거나 업그레이드하려면:

```bash
helm upgrade --install web-backend-platform ./web-backend-platform \
  --namespace <YOUR_NAMESPACE>
```

## 구성 (Configuration)

다음 표는 web-backend 차트의 구성 가능한 매개변수와 기본값을 나열합니다.

| 매개변수 | 설명 | 기본값 |
|-----------|-------------|---------|
| `replicaCount` | 레플리카 수 | `1` |
| `image.repository` | 이미지 리포지토리 | `""` |
| `image.tag` | 이미지 태그 | `"latest"` |
| `service.port` | 서비스 포트 | `8000` |
| `ingress.enabled` | Ingress 통합 활성화 | `true` |
| `ingress.className` | Ingress 클래스 이름 | `"alb"` |
| `env.AWS_REGION` | AWS 리전 | `"ap-northeast-2"` |
| `env.DYNAMODB_TABLE_NAME` | DynamoDB 테이블 이름 | `"sfbank-blue-FaaSData"` |
| `env.S3_BUCKET_NAME` | S3 버킷 이름 | `"sfbank-blue-functions-code-bucket"` |
| `env.CORS_ORIGINS` | 허용된 CORS 오리진 | `["https://eunha.icu", "http://eunha.icu"]` |

## 문제 해결 (Troubleshooting)

**Ingress가 ALB를 생성하지 않나요?**
- AWS Load Balancer Controller 로그를 확인하세요.
- 서브넷이 자동 검색을 위해 올바르게 태그되었는지 확인하세요.

**HTTPS가 작동하지 않나요?**
- `values.yaml`의 ACM 인증서 ARN이 정확하고 유효한지 확인하세요.
- 인증서가 `api.eunha.icu` 도메인을 커버하는지 확인하세요.
