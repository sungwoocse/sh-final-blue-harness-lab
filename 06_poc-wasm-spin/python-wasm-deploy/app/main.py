"""
FastAPI 앱 진입점

Python WASM Deploy 플랫폼의 메인 애플리케이션입니다.
- 라우터 등록
- CORS 설정
- 헬스 체크 엔드포인트

Requirements: 1.1
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api import build_router, deploy_router

# FastAPI 앱 생성
app = FastAPI(
    title="Python WASM Deploy Platform",
    description="Python Spin 프로젝트를 WASM으로 빌드하고 SpinKube 클러스터에 배포하는 플랫폼",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 프로덕션에서는 특정 도메인으로 제한 권장
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 라우터 등록
app.include_router(build_router)
app.include_router(deploy_router)


@app.get("/", tags=["health"])
async def root():
    """루트 엔드포인트 - API 정보 반환"""
    return {
        "name": "Python WASM Deploy Platform",
        "version": "1.0.0",
        "docs": "/docs",
    }


@app.get("/health", tags=["health"])
async def health_check():
    """헬스 체크 엔드포인트"""
    return {"status": "healthy"}
