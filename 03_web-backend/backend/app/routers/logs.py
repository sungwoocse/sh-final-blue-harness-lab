"""Logs API 라우터"""
from fastapi import APIRouter, HTTPException, status, Query
from app.models import LogsResponse, ExecutionLog, LokiLogsResponse, LokiLogEntry
from app.database import db_client
from app.config import settings
from datetime import datetime
from app.utils.timezone import to_kst
import httpx

router = APIRouter()


@router.get("/workspaces/{workspace_id}/logs", response_model=LogsResponse)
async def get_workspace_logs(
    workspace_id: str, limit: int = Query(default=50, le=500, ge=1)
):
    """워크스페이스 전체 함수의 최근 실행 로그 조회"""
    workspace = db_client.get_workspace(workspace_id)
    if not workspace:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": {
                    "code": "NOT_FOUND",
                    "message": f"Workspace {workspace_id} not found",
                }
            },
        )

    try:
        functions = db_client.list_functions(workspace_id)
        per_function_limit = min(limit, 50)
        logs = []

        for fn in functions:
            items = db_client.list_logs(fn["id"], limit=per_function_limit)
            logs.extend(
                [
                    ExecutionLog(
                        id=item["id"],
                        functionId=item["functionId"],
                        timestamp=to_kst(datetime.fromisoformat(item["timestamp"])),
                        status=item["status"],
                        duration=item["duration"],
                        statusCode=item["statusCode"],
                        requestBody=item.get("requestBody"),
                        responseBody=item.get("responseBody"),
                        logs=item.get("logs", []),
                        level=item.get("level", "info"),
                    )
                    for item in items
                ]
            )

        # 최신순으로 정렬 후 limit만큼 자르기
        logs.sort(key=lambda log: log.timestamp, reverse=True)
        trimmed_logs = logs[:limit]

        return LogsResponse(logs=trimmed_logs, total=len(trimmed_logs))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": {"code": "LIST_ERROR", "message": str(e)}},
        )


@router.get(
    "/workspaces/{workspace_id}/functions/{function_id}/logs", response_model=LogsResponse
)
async def get_function_logs(
    workspace_id: str, function_id: str, limit: int = Query(default=100, le=1000, ge=1)
):
    """함수 실행 로그 조회"""
    # 함수 존재 확인
    function = db_client.get_function(workspace_id, function_id)
    if not function:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": {
                    "code": "NOT_FOUND",
                    "message": f"Function {function_id} not found",
                }
            },
        )

    try:
        items = db_client.list_logs(function_id, limit=limit)

        logs = [
            ExecutionLog(
                id=item["id"],
                functionId=item["functionId"],
                timestamp=to_kst(datetime.fromisoformat(item["timestamp"])),
                status=item["status"],
                duration=item["duration"],
                statusCode=item["statusCode"],
                requestBody=item.get("requestBody"),
                responseBody=item.get("responseBody"),
                logs=item.get("logs", []),
                level=item.get("level", "info"),
            )
            for item in items
        ]

        return LogsResponse(logs=logs, total=len(logs))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": {"code": "LIST_ERROR", "message": str(e)}},
        )


@router.get("/functions/{function_id}/loki-logs", response_model=LokiLogsResponse)
async def get_loki_logs(
    function_id: str, limit: int = Query(default=100, le=1000, ge=1)
):
    """Loki에서 function_id로 실시간 로그 조회"""
    try:
        # Loki API 호출
        async with httpx.AsyncClient(timeout=30.0) as client:
            loki_url = f"{settings.loki_service_url}/loki/api/v1/query_range"
            params = {
                "query": f'{{function_id="{function_id}"}}',
                "limit": limit,
                "direction": "backward",
            }

            response = await client.get(loki_url, params=params)
            response.raise_for_status()
            data = response.json()

        # Loki 응답 파싱
        logs = []
        if data.get("status") == "success":
            result = data.get("data", {}).get("result", [])
            for stream in result:
                values = stream.get("values", [])
                for value in values:
                    # value = [timestamp_nanoseconds, log_line]
                    if len(value) >= 2:
                        logs.append(
                            LokiLogEntry(timestamp=value[0], line=value[1])
                        )

        return LokiLogsResponse(
            logs=logs, total=len(logs), function_id=function_id
        )

    except httpx.HTTPError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "error": {
                    "code": "LOKI_CONNECTION_ERROR",
                    "message": f"로그 시스템 연결 불가: {str(e)}",
                }
            },
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": {
                    "code": "LOKI_ERROR",
                    "message": f"로그 조회 실패: {str(e)}",
                }
            },
        )
