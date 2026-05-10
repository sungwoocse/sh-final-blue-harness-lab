# DynamoDB 테이블 설계 (Single Table)

해커톤용 싱글 테이블 설계입니다. 빌드/배포 정보를 하나의 테이블에서 관리하고, 서비스 DNS를 저장하여 백엔드에서 WASM 함수를 호출할 수 있습니다.

---

## 테이블: `wasm-faas`

### 테이블 구조

| Attribute | Type | Description |
|-----------|------|-------------|
| `PK` | String | Partition Key (`BUILD#{build_id}`) |
| `SK` | String | Sort Key (`META` 또는 `DEPLOY#{namespace}`) |
| `GSI1PK` | String | GSI1 PK (조회용) |
| `GSI1SK` | String | GSI1 SK (정렬용) |
| `type` | String | 레코드 타입: `BUILD` 또는 `DEPLOY` |

### 키 설계

| 레코드 | PK | SK | GSI1PK | GSI1SK |
|--------|----|----|--------|--------|
| 빌드 정보 | `BUILD#{build_id}` | `META` | `STATUS#{status}` | `{created_at}` |
| 배포 정보 | `BUILD#{build_id}` | `DEPLOY#{namespace}` | `NS#{namespace}` | `{created_at}` |

### GSI

| GSI | PK | SK | 용도 |
|-----|----|----|------|
| GSI1 | `GSI1PK` | `GSI1SK` | 상태별/네임스페이스별 조회 |

---

## 스키마 상세

### Build 레코드

```json
{
  "PK": "BUILD#ba54a28d-8a68-448e-b160-8fcf80bc52c0",
  "SK": "META",
  "GSI1PK": "STATUS#success",
  "GSI1SK": "2024-11-29T12:00:00Z",
  "type": "BUILD",

  "build_id": "ba54a28d-8a68-448e-b160-8fcf80bc52c0",
  "app_name": "echo-app",
  "status": "success",
  "oci_reference": "docker.io/galaxyeunha0530/wasm-test:ba54a28d-8a68-448e-b160-8fcf80bc52c0",
  "error_message": null,
  "created_at": "2024-11-29T12:00:00Z",
  "updated_at": "2024-11-29T12:05:00Z"
}
```

### Deploy 레코드 (서비스 DNS 포함)

```json
{
  "PK": "BUILD#ba54a28d-8a68-448e-b160-8fcf80bc52c0",
  "SK": "DEPLOY#default",
  "GSI1PK": "NS#default",
  "GSI1SK": "2024-11-29T12:10:00Z",
  "type": "DEPLOY",

  "build_id": "ba54a28d-8a68-448e-b160-8fcf80bc52c0",
  "app_name": "ba54a28d-8a68-448e-b160-8fcf80bc52c0",
  "namespace": "default",
  "oci_reference": "docker.io/galaxyeunha0530/wasm-test:ba54a28d-8a68-448e-b160-8fcf80bc52c0",
  "replicas": 1,
  "ready_replicas": 1,
  "status": "Running",

  "service_dns": "ba54a28d-8a68-448e-b160-8fcf80bc52c0.default.svc.cluster.local",
  "service_url": "http://ba54a28d-8a68-448e-b160-8fcf80bc52c0.default.svc.cluster.local:80",
  "cluster_ip": "10.43.75.134",

  "created_at": "2024-11-29T12:10:00Z",
  "updated_at": "2024-11-29T12:10:30Z"
}
```

---

## 서비스 DNS 필드

| 필드 | 형식 | 설명 |
|------|------|------|
| `service_dns` | `{app_name}.{namespace}.svc.cluster.local` | K8s 내부 DNS |
| `service_url` | `http://{service_dns}:80` | 호출 가능한 전체 URL |
| `cluster_ip` | `10.43.x.x` | 클러스터 내부 IP |

---

## 접근 패턴

| 패턴 | 쿼리 방법 |
|------|----------|
| 빌드 ID로 빌드+배포 전체 조회 | `PK = BUILD#{id}` |
| 빌드 ID로 빌드 정보만 조회 | `PK = BUILD#{id}, SK = META` |
| 빌드 ID로 배포 정보 조회 | `PK = BUILD#{id}, SK begins_with DEPLOY#` |
| 상태별 빌드 목록 | GSI1: `GSI1PK = STATUS#{status}` |
| 네임스페이스별 배포 목록 | GSI1: `GSI1PK = NS#{namespace}` |

---

## Python 사용 예시

```python
import boto3
from datetime import datetime

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table('wasm-faas')


# ============ 빌드 저장 ============
def save_build(build_id: str, app_name: str, status: str, oci_reference: str = None):
    now = datetime.utcnow().isoformat() + 'Z'
    table.put_item(Item={
        'PK': f'BUILD#{build_id}',
        'SK': 'META',
        'GSI1PK': f'STATUS#{status}',
        'GSI1SK': now,
        'type': 'BUILD',
        'build_id': build_id,
        'app_name': app_name,
        'status': status,
        'oci_reference': oci_reference,
        'created_at': now,
        'updated_at': now,
    })


# ============ 빌드 상태 업데이트 ============
def update_build_status(build_id: str, status: str, oci_reference: str = None, error_message: str = None):
    now = datetime.utcnow().isoformat() + 'Z'
    update_expr = 'SET #status = :status, updated_at = :now, GSI1PK = :gsi1pk'
    expr_values = {
        ':status': status,
        ':now': now,
        ':gsi1pk': f'STATUS#{status}',
    }

    if oci_reference:
        update_expr += ', oci_reference = :oci'
        expr_values[':oci'] = oci_reference
    if error_message:
        update_expr += ', error_message = :err'
        expr_values[':err'] = error_message

    table.update_item(
        Key={'PK': f'BUILD#{build_id}', 'SK': 'META'},
        UpdateExpression=update_expr,
        ExpressionAttributeNames={'#status': 'status'},
        ExpressionAttributeValues=expr_values
    )


# ============ 배포 저장 (서비스 DNS 포함) ============
def save_deployment(build_id: str, app_name: str, namespace: str,
                    oci_reference: str, replicas: int, cluster_ip: str):
    now = datetime.utcnow().isoformat() + 'Z'

    # 서비스 DNS 생성
    service_dns = f'{app_name}.{namespace}.svc.cluster.local'
    service_url = f'http://{service_dns}:80'

    table.put_item(Item={
        'PK': f'BUILD#{build_id}',
        'SK': f'DEPLOY#{namespace}',
        'GSI1PK': f'NS#{namespace}',
        'GSI1SK': now,
        'type': 'DEPLOY',
        'build_id': build_id,
        'app_name': app_name,
        'namespace': namespace,
        'oci_reference': oci_reference,
        'replicas': replicas,
        'ready_replicas': 0,
        'status': 'Pending',
        'service_dns': service_dns,
        'service_url': service_url,
        'cluster_ip': cluster_ip,
        'created_at': now,
        'updated_at': now,
    })

    return service_url


# ============ 빌드 조회 ============
def get_build(build_id: str) -> dict:
    response = table.get_item(
        Key={'PK': f'BUILD#{build_id}', 'SK': 'META'}
    )
    return response.get('Item')


# ============ 빌드 + 배포 전체 조회 ============
def get_build_with_deployments(build_id: str) -> dict:
    response = table.query(
        KeyConditionExpression='PK = :pk',
        ExpressionAttributeValues={':pk': f'BUILD#{build_id}'}
    )
    items = response.get('Items', [])

    result = {'build': None, 'deployments': []}
    for item in items:
        if item['SK'] == 'META':
            result['build'] = item
        else:
            result['deployments'].append(item)

    return result


# ============ 서비스 URL 조회 (백엔드 호출용) ============
def get_service_url(build_id: str, namespace: str = 'default') -> str:
    response = table.get_item(
        Key={'PK': f'BUILD#{build_id}', 'SK': f'DEPLOY#{namespace}'}
    )
    item = response.get('Item')
    return item.get('service_url') if item else None


# ============ 네임스페이스별 배포 목록 ============
def list_deployments_by_namespace(namespace: str) -> list:
    response = table.query(
        IndexName='GSI1',
        KeyConditionExpression='GSI1PK = :pk',
        ExpressionAttributeValues={':pk': f'NS#{namespace}'},
        ScanIndexForward=False  # 최신순
    )
    return response.get('Items', [])


# ============ 상태별 빌드 목록 ============
def list_builds_by_status(status: str) -> list:
    response = table.query(
        IndexName='GSI1',
        KeyConditionExpression='GSI1PK = :pk',
        ExpressionAttributeValues={':pk': f'STATUS#{status}'},
        ScanIndexForward=False
    )
    return response.get('Items', [])
```

---

## 백엔드에서 WASM 함수 호출 예시

```python
import httpx

async def invoke_wasm_function(build_id: str, payload: dict, namespace: str = 'default'):
    """
    DynamoDB에서 서비스 URL을 조회하고 WASM 함수를 호출합니다.
    """
    # 1. 서비스 URL 조회
    service_url = get_service_url(build_id, namespace)
    if not service_url:
        raise ValueError(f"Deployment not found: {build_id}")

    # 2. WASM 함수 호출
    async with httpx.AsyncClient() as client:
        response = await client.post(
            service_url,
            json=payload,
            timeout=30.0
        )
        return response.json()


# 사용 예시
async def main():
    result = await invoke_wasm_function(
        build_id="ba54a28d-8a68-448e-b160-8fcf80bc52c0",
        payload={"message": "Hello from backend!"}
    )
    print(result)
    # {"status": "success", "output": "Hello from backend!"}
```

---

## Terraform 설정

```hcl
resource "aws_dynamodb_table" "wasm_faas" {
  name           = "wasm-faas"
  billing_mode   = "PAY_PER_REQUEST"
  hash_key       = "PK"
  range_key      = "SK"

  attribute {
    name = "PK"
    type = "S"
  }

  attribute {
    name = "SK"
    type = "S"
  }

  attribute {
    name = "GSI1PK"
    type = "S"
  }

  attribute {
    name = "GSI1SK"
    type = "S"
  }

  global_secondary_index {
    name            = "GSI1"
    hash_key        = "GSI1PK"
    range_key       = "GSI1SK"
    projection_type = "ALL"
  }

  tags = {
    Project = "wasm-faas-hackathon"
  }
}
```

---

## 아키텍처 흐름

```
┌──────────┐     ┌──────────────┐     ┌───────────┐
│  Client  │────▶│  FastAPI     │────▶│ DynamoDB  │
│          │     │  (Backend)   │     │ wasm-faas │
└──────────┘     └──────┬───────┘     └───────────┘
                        │                    │
                        │  service_url 조회   │
                        │◀───────────────────┤
                        │
                        ▼
              ┌─────────────────────┐
              │  Kubernetes 클러스터 │
              │  ┌─────────────────┐ │
              │  │ SpinApp (WASM)  │ │
              │  │ {app}.{ns}.svc  │ │
              │  └─────────────────┘ │
              └─────────────────────┘

1. 클라이언트 → 백엔드: 함수 실행 요청
2. 백엔드 → DynamoDB: service_url 조회
3. 백엔드 → SpinApp: HTTP 호출 (service_url)
4. SpinApp → 백엔드: 결과 반환
5. 백엔드 → 클라이언트: 최종 응답
```

---

## 요약

| 항목 | 값 |
|------|-----|
| 테이블 이름 | `wasm-faas` |
| PK | `BUILD#{build_id}` |
| SK | `META` (빌드) / `DEPLOY#{namespace}` (배포) |
| GSI1 | 상태별/네임스페이스별 조회 |
| 서비스 DNS | `{app_name}.{namespace}.svc.cluster.local` |
| 서비스 URL | `http://{service_dns}:80` |
