"""FastAPI 메인 애플리케이션"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.routers import workspaces, functions, logs, builds, metrics
import logging

# 기본 로깅 설정
logging.basicConfig(
    level=settings.log_level,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

# FastAPI 앱 생성
app = FastAPI(
    title="FaaS Backend API",
    description="Function as a Service Backend API for Softbank Hackathon",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_origin_regex=r"https?://.*\.eunha\.icu",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 라우터 등록
app.include_router(workspaces.router, prefix="/api", tags=["Workspaces"])
app.include_router(functions.router, prefix="/api", tags=["Functions"])
app.include_router(logs.router, prefix="/api", tags=["Logs"])
app.include_router(builds.router, prefix="/api", tags=["Builds"])
app.include_router(metrics.router, prefix="/api", tags=["Metrics"])


@app.get("/")
async def root():
    """헬스 체크"""
    return {
        "status": "ok",
        "message": "FaaS Backend API is running",
        "environment": settings.environment,
    }


@app.get("/health")
async def health():
    """헬스 체크 엔드포인트"""
    return {"status": "healthy"}
