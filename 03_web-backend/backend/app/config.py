"""애플리케이션 설정"""
from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    """환경 변수 설정"""

    # AWS 설정
    aws_region: str = "ap-northeast-2"
    aws_access_key_id: str = ""
    aws_secret_access_key: str = ""

    # DynamoDB
    dynamodb_table_name: str = "sfbank-blue-FaaSData"

    # S3
    s3_bucket_name: str = "sfbank-blue-functions-code-bucket"

    # FastAPI
    environment: str = "development"
    log_level: str = "DEBUG"

    # CORS
    cors_origins: List[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
        "https://eunha.icu",
        "http://eunha.icu",
        "https://www.eunha.icu",
        "http://www.eunha.icu",
    ]

    # Builder Service (Core Services)
    builder_service_url: str = "https://builder.eunha.icu"

    # Loki Log Service
    loki_service_url: str = "http://loki-stack.logging.svc.cluster.local:3100"

    # Prometheus Metrics Service
    # NOTE: keep in sync with cluster service name (kube-prometheus-stack chart)
    prometheus_service_url: str = (
        "http://prometheus-stack-kube-prom-prometheus.monitoring.svc.cluster.local:9090"
    )

    class Config:
        env_file = ".env"
        case_sensitive = False


# 전역 설정 인스턴스
settings = Settings()
