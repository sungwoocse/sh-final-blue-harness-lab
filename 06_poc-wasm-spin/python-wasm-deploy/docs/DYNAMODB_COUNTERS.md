# DynamoDB 카운터 테이블 설계

FaaS 호출 횟수를 추적하기 위한 별도 카운터 테이블입니다.

---

## 테이블: `wasm-faas-counters`

### 테이블 구조

| Attribute | Type | Description |
|-----------|------|-------------|
| `PK` | String | Partition Key |
| `SK` | String | Sort Key |
| `count` | Number | 호출 횟수 (atomic increment) |
| `updated_at` | String | 마지막 업데이트 시간 |

### 키 설계

| 레코드 | PK | SK | 용도 |
|--------|----|----|------|
| 전체 호출 수 | `BUILD#{build_id}` | `TOTAL` | 빌드별 총 호출 횟수 |
| 일별 호출 수 | `BUILD#{build_id}` | `DAY#{YYYY-MM-DD}` | 일별 통계 |

---

## 스키마 상세

### 전체 호출 수 레코드

```json
{
  "PK": "BUILD#ba54a28d-8a68-448e-b160-8fcf80bc52c0",
  "SK": "TOTAL",
  "count": 1523,
  "updated_at": "2024-11-29T15:30:00Z"
}
```

### 일별 호출 수 레코드

```json
{
  "PK": "BUILD#ba54a28d-8a68-448e-b160-8fcf80bc52c0",
  "SK": "DAY#2024-11-29",
  "count": 42,
  "updated_at": "2024-11-29T15:30:00Z"
}
```

---

## Python 사용 예시

```python
import boto3
from datetime import datetime

dynamodb = boto3.resource('dynamodb')
counter_table = dynamodb.Table('wasm-faas-counters')


# ============ 호출 횟수 증가 (Atomic Increment) ============
def increment_invocation(build_id: str):
    """
    FaaS 호출 시 카운터를 원자적으로 증가시킵니다.
    TOTAL과 일별 카운터를 동시에 업데이트합니다.
    """
    now = datetime.utcnow()
    today = now.strftime('%Y-%m-%d')
    timestamp = now.isoformat() + 'Z'

    # 배치 쓰기로 두 카운터를 동시에 증가
    # (참고: 배치 쓰기는 원자적 증가를 지원하지 않아 개별 호출 필요)

    # 1. 전체 카운터 증가
    counter_table.update_item(
        Key={'PK': f'BUILD#{build_id}', 'SK': 'TOTAL'},
        UpdateExpression='ADD #count :inc SET updated_at = :now',
        ExpressionAttributeNames={'#count': 'count'},
        ExpressionAttributeValues={':inc': 1, ':now': timestamp}
    )

    # 2. 일별 카운터 증가
    counter_table.update_item(
        Key={'PK': f'BUILD#{build_id}', 'SK': f'DAY#{today}'},
        UpdateExpression='ADD #count :inc SET updated_at = :now',
        ExpressionAttributeNames={'#count': 'count'},
        ExpressionAttributeValues={':inc': 1, ':now': timestamp}
    )


# ============ 전체 호출 횟수 조회 ============
def get_total_invocations(build_id: str) -> int:
    response = counter_table.get_item(
        Key={'PK': f'BUILD#{build_id}', 'SK': 'TOTAL'}
    )
    item = response.get('Item')
    return int(item.get('count', 0)) if item else 0


# ============ 일별 호출 횟수 조회 ============
def get_daily_invocations(build_id: str, date: str = None) -> int:
    """
    특정 날짜의 호출 횟수를 조회합니다.
    date: YYYY-MM-DD 형식 (기본값: 오늘)
    """
    if date is None:
        date = datetime.utcnow().strftime('%Y-%m-%d')

    response = counter_table.get_item(
        Key={'PK': f'BUILD#{build_id}', 'SK': f'DAY#{date}'}
    )
    item = response.get('Item')
    return int(item.get('count', 0)) if item else 0


# ============ 최근 N일 통계 조회 ============
def get_invocation_stats(build_id: str, days: int = 7) -> dict:
    """
    최근 N일간의 호출 통계를 조회합니다.
    """
    response = counter_table.query(
        KeyConditionExpression='PK = :pk AND begins_with(SK, :prefix)',
        ExpressionAttributeValues={
            ':pk': f'BUILD#{build_id}',
            ':prefix': 'DAY#'
        },
        ScanIndexForward=False,  # 최신순
        Limit=days
    )

    stats = {}
    for item in response.get('Items', []):
        date = item['SK'].replace('DAY#', '')
        stats[date] = int(item.get('count', 0))

    return stats
```

---

## 통합 사용 예시 (WASM 함수 호출 + 카운터)

```python
import httpx
from app.dynamodb import get_service_url  # wasm-faas 테이블
from app.counters import increment_invocation  # wasm-faas-counters 테이블


async def invoke_wasm_function(build_id: str, payload: dict, namespace: str = 'default'):
    """
    WASM 함수를 호출하고 카운터를 증가시킵니다.
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

    # 3. 호출 성공 시 카운터 증가
    increment_invocation(build_id)

    return response.json()
```

---

## Terraform 설정

```hcl
resource "aws_dynamodb_table" "wasm_faas_counters" {
  name           = "wasm-faas-counters"
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

  tags = {
    Project = "wasm-faas-hackathon"
  }
}
```

---

## 왜 별도 테이블인가?

| 이유 | 설명 |
|------|------|
| **쓰기 패턴 분리** | 카운터는 매 호출마다 쓰기, 메인 테이블은 빌드/배포 시에만 쓰기 |
| **핫 파티션 관리** | 인기 함수의 카운터가 핫 파티션이 되어도 메인 테이블에 영향 없음 |
| **비용 최적화** | 필요시 카운터 테이블만 프로비저닝 용량 변경 가능 |
| **TTL 적용 용이** | 일별 카운터에 TTL 적용하여 오래된 데이터 자동 삭제 가능 |

---

## 요약

| 항목 | 값 |
|------|-----|
| 테이블 이름 | `wasm-faas-counters` |
| PK | `BUILD#{build_id}` |
| SK | `TOTAL` / `DAY#{YYYY-MM-DD}` |
| 증가 방식 | `ADD` (atomic increment) |
| 동시성 | 안전 (원자적 연산) |
