"""Metrics API 라우터"""
from datetime import datetime, timedelta
from fastapi import APIRouter, HTTPException, status
from app.models import (
    PrometheusMetricsResponse,
    PrometheusMetricsData,
    PrometheusTimeseriesPoint,
)
from app.config import settings
import httpx

router = APIRouter()


@router.get("/functions/{function_id}/metrics", response_model=PrometheusMetricsResponse)
async def get_function_metrics(function_id: str):
    """Prometheus에서 function_id로 Pod 메트릭 조회"""
    try:
        # Prometheus API 호출
        base_query = (
            'sum(rate(container_cpu_usage_seconds_total{container!=""}[1m]) '
            '* on(namespace, pod) '
            'group_left(label_function_id) kube_pod_labels{label_function_id="'
            f"{function_id}" + '"})'
        )

        # CPU 사용량 조회 기간: 최근 60분
        window_seconds = 60 * 60
        now = datetime.utcnow()
        start = now - timedelta(seconds=window_seconds)

        instant_url = f"{settings.prometheus_service_url}/api/v1/query"
        range_url = f"{settings.prometheus_service_url}/api/v1/query_range"

        async with httpx.AsyncClient(timeout=30.0) as client:
            instant_resp = await client.get(instant_url, params={"query": base_query})
            instant_resp.raise_for_status()
            instant_json = instant_resp.json()

            range_resp = await client.get(
                range_url,
                params={
                    "query": base_query,
                    "start": start.timestamp(),
                    "end": now.timestamp(),
                    "step": "60s",
                },
            )
            range_resp.raise_for_status()
            range_json = range_resp.json()

        cpu_total = None
        instant_results = instant_json.get("data", {}).get("result", [])
        if instant_results:
            value = instant_results[0].get("value")
            if isinstance(value, list) and len(value) >= 2:
                try:
                    cpu_total = float(value[1])
                except (TypeError, ValueError):
                    cpu_total = None

        cpu_series = []
        for result in range_json.get("data", {}).get("result", []):
            for ts, val in result.get("values", []):
                try:
                    cpu_series.append(
                        PrometheusTimeseriesPoint(
                            timestamp=float(ts), value=float(val)
                        )
                    )
                except (TypeError, ValueError):
                    continue

        # status는 두 쿼리 모두 성공했을 때만 success
        status_value = (
            "success"
            if instant_json.get("status") == "success"
            and range_json.get("status") == "success"
            else "partial"
        )

        metrics_data = PrometheusMetricsData(
            cpu_total=cpu_total,
            cpu_series=cpu_series,
            window_seconds=window_seconds,
            instant_query=base_query,
            range_query=base_query,
            raw_instant=instant_json,
            raw_range=range_json,
        )

        return PrometheusMetricsResponse(
            status=status_value,
            data=metrics_data,
            function_id=function_id,
        )

    except httpx.HTTPError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "error": {
                    "code": "PROMETHEUS_CONNECTION_ERROR",
                    "message": f"메트릭 시스템 연결 불가: {str(e)}",
                }
            },
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": {
                    "code": "PROMETHEUS_ERROR",
                    "message": f"메트릭 조회 실패: {str(e)}",
                }
            },
        )
