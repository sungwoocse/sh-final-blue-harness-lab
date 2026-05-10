# S3 프론트엔드 배포 가이드

CloudFront + S3를 사용한 정적 프론트엔드 배포 방법입니다.

## 구성 정보

| 항목 | 값 |
|------|-----|
| S3 버킷 | `eunha-icu-frontend` |
| CloudFront 도메인 | `www.eunha.icu` |
| CloudFront Distribution ID | `terraform output cloudfront_id` 로 확인 |

## 배포 방법

### 1. 기본 배포 (aws s3 sync)

```bash
# 빌드된 정적 파일을 S3에 업로드
aws s3 sync ./dist s3://eunha-icu-frontend --delete

# 또는 특정 폴더
aws s3 sync ./build s3://eunha-icu-frontend --delete
```

#### 옵션 설명
- `--delete`: S3에만 있고 로컬에 없는 파일 삭제
- `--exclude`: 특정 파일/패턴 제외
- `--include`: 특정 파일/패턴 포함

```bash
# .git 폴더 제외하고 업로드
aws s3 sync ./dist s3://eunha-icu-frontend --delete --exclude ".git/*"

# 특정 확장자만 업로드
aws s3 sync ./dist s3://eunha-icu-frontend --exclude "*" --include "*.html" --include "*.js" --include "*.css"
```

### 2. 개별 파일 업로드

```bash
# 단일 파일 업로드
aws s3 cp ./dist/index.html s3://eunha-icu-frontend/index.html

# Content-Type 지정
aws s3 cp ./dist/index.html s3://eunha-icu-frontend/index.html --content-type "text/html"

# 폴더 전체 복사
aws s3 cp ./dist s3://eunha-icu-frontend --recursive
```

### 3. Content-Type 자동 설정

```bash
# MIME 타입 자동 감지 (기본 동작)
aws s3 sync ./dist s3://eunha-icu-frontend --delete

# 특정 파일에 Content-Type 명시
aws s3 cp ./dist/data.json s3://eunha-icu-frontend/data.json --content-type "application/json"
```

## CloudFront 캐시 무효화

S3에 파일을 업로드해도 CloudFront 캐시로 인해 즉시 반영되지 않을 수 있습니다.

### 1. 전체 캐시 무효화

```bash
# Distribution ID 확인
DISTRIBUTION_ID=$(terraform output -raw cloudfront_id)

# 전체 경로 무효화
aws cloudfront create-invalidation \
  --distribution-id $DISTRIBUTION_ID \
  --paths "/*"
```

### 2. 특정 파일만 무효화

```bash
# index.html만 무효화
aws cloudfront create-invalidation \
  --distribution-id $DISTRIBUTION_ID \
  --paths "/index.html"

# 여러 파일 무효화
aws cloudfront create-invalidation \
  --distribution-id $DISTRIBUTION_ID \
  --paths "/index.html" "/assets/*" "/static/*"
```

### 3. 무효화 상태 확인

```bash
# 무효화 목록 조회
aws cloudfront list-invalidations --distribution-id $DISTRIBUTION_ID

# 특정 무효화 상태 확인
aws cloudfront get-invalidation \
  --distribution-id $DISTRIBUTION_ID \
  --id <INVALIDATION_ID>
```

### 무효화 비용
- 월 1,000개 경로까지 무료
- 이후 경로당 $0.005
- `/*` 는 1개 경로로 계산

## 배포 스크립트 예시

### deploy.sh

```bash
#!/bin/bash
set -e

# 설정
S3_BUCKET="eunha-icu-frontend"
DISTRIBUTION_ID=$(terraform output -raw cloudfront_id)
BUILD_DIR="./dist"

echo "1. 빌드 중..."
npm run build

echo "2. S3 업로드 중..."
aws s3 sync $BUILD_DIR s3://$S3_BUCKET --delete

echo "3. CloudFront 캐시 무효화 중..."
INVALIDATION_ID=$(aws cloudfront create-invalidation \
  --distribution-id $DISTRIBUTION_ID \
  --paths "/*" \
  --query 'Invalidation.Id' \
  --output text)

echo "무효화 ID: $INVALIDATION_ID"

echo "4. 무효화 완료 대기 중..."
aws cloudfront wait invalidation-completed \
  --distribution-id $DISTRIBUTION_ID \
  --id $INVALIDATION_ID

echo "배포 완료!"
echo "URL: https://www.eunha.icu"
```

### 사용법

```bash
chmod +x deploy.sh
./deploy.sh
```

## CI/CD 파이프라인 예시

### GitHub Actions

```yaml
name: Deploy Frontend

on:
  push:
    branches: [main]
    paths:
      - 'frontend/**'

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'npm'
          cache-dependency-path: frontend/package-lock.json

      - name: Install dependencies
        run: npm ci
        working-directory: frontend

      - name: Build
        run: npm run build
        working-directory: frontend

      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v4
        with:
          aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
          aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          aws-region: ap-northeast-2

      - name: Deploy to S3
        run: aws s3 sync ./dist s3://eunha-icu-frontend --delete
        working-directory: frontend

      - name: Invalidate CloudFront
        run: |
          aws cloudfront create-invalidation \
            --distribution-id ${{ secrets.CLOUDFRONT_DISTRIBUTION_ID }} \
            --paths "/*"
```

## 캐싱 전략

### 권장 설정

| 파일 유형 | 캐시 정책 | 설명 |
|-----------|-----------|------|
| `index.html` | 캐시 안함 | 항상 최신 버전 제공 |
| `*.js`, `*.css` | 장기 캐시 | 파일명에 해시 포함 (예: `app.abc123.js`) |
| `assets/*` | 장기 캐시 | 이미지, 폰트 등 |

### Cache-Control 헤더 설정

```bash
# index.html - 캐시 안함
aws s3 cp ./dist/index.html s3://eunha-icu-frontend/index.html \
  --cache-control "no-cache, no-store, must-revalidate" \
  --content-type "text/html"

# JS/CSS - 1년 캐시 (해시 파일명 사용시)
aws s3 sync ./dist/assets s3://eunha-icu-frontend/assets \
  --cache-control "public, max-age=31536000, immutable"
```

## 트러블슈팅

### 403 Forbidden 에러
- CloudFront OAC 설정 확인
- S3 버킷 정책 확인

```bash
# 버킷 정책 확인
aws s3api get-bucket-policy --bucket eunha-icu-frontend
```

### 변경사항이 반영되지 않음
1. CloudFront 캐시 무효화 실행
2. 브라우저 캐시 삭제 (Ctrl+Shift+R)
3. 무효화 완료까지 대기 (보통 1-2분)

### SPA 라우팅 문제 (404)
CloudFront에 커스텀 에러 응답이 설정되어 있습니다:
- 403 → 200 `/index.html`
- 404 → 200 `/index.html`

## 유용한 명령어

```bash
# S3 버킷 내용 확인
aws s3 ls s3://eunha-icu-frontend --recursive

# 버킷 용량 확인
aws s3 ls s3://eunha-icu-frontend --recursive --summarize

# 특정 파일 삭제
aws s3 rm s3://eunha-icu-frontend/old-file.js

# 버킷 비우기 (주의!)
aws s3 rm s3://eunha-icu-frontend --recursive
```
