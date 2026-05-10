FROM node:20-alpine

# 작업 디렉토리
WORKDIR /app

# 의존성 설치
COPY package.json package-lock.json ./
RUN npm ci

# 소스 복사
COPY . .

# Vite 빌드
RUN npm run build

# 컨테이너 포트 3000 사용
EXPOSE 3000

# Vite preview 서버로 정적 파일 서빙
CMD ["npm", "run", "preview", "--", "--host", "0.0.0.0", "--port", "3000"]
