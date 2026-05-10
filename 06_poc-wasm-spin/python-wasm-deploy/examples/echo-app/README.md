# Echo App 예제

간단한 에코 기능을 제공하는 Python Spin 애플리케이션 예제입니다.

## 기능

- POST 요청으로 받은 `message` 필드를 그대로 반환
- JSON 형식의 요청/응답

## 파일 구조

```
echo-app/
├── app.py           # 메인 애플리케이션 코드
├── spin.toml        # Spin 설정 파일
├── requirements.txt # Python 의존성
└── README.md        # 이 문서
```

## 사용법

### 1. ZIP 파일 생성

```bash
zip -r echo-app.zip echo-app/
```

### 2. 빌드 및 배포

```bash
# 빌드 요청
curl -X POST http://localhost:8000/api/v1/builds \
  -F "app_name=echo-app" \
  -F "file=@echo-app.zip"

# 배포 (build_id를 위 응답에서 가져옴)
curl -X POST http://localhost:8000/api/v1/apps \
  -H "Content-Type: application/json" \
  -d '{"build_id": "YOUR_BUILD_ID", "namespace": "default", "replicas": 1}'
```

### 3. 테스트

```bash
# 클러스터 내부에서 테스트
kubectl run curl-test --image=curlimages/curl --rm -i --restart=Never -- \
  curl -s -X POST "http://YOUR_APP_NAME.default.svc.cluster.local/" \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello, World!"}'
```

**예상 응답:**
```json
{
  "status": "success",
  "output": "Hello, World!"
}
```

## API 스펙

### 요청

- **Method:** POST
- **Content-Type:** application/json
- **Body:**
  ```json
  {
    "message": "에코할 메시지"
  }
  ```

### 응답

- **성공 (200):**
  ```json
  {
    "status": "success",
    "output": "에코할 메시지"
  }
  ```

- **에러 (400):**
  ```json
  {
    "status": "error",
    "message": "에러 메시지"
  }
  ```
