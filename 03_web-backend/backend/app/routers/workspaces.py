"""Workspace API 라우터"""
from fastapi import APIRouter, HTTPException, status
from app.models import WorkspaceCreate, WorkspaceUpdate, Workspace
from app.database import db_client
from typing import List
from datetime import datetime
from app.utils.timezone import to_kst

router = APIRouter()


@router.post("/workspaces", response_model=Workspace, status_code=status.HTTP_201_CREATED)
async def create_workspace(workspace: WorkspaceCreate):
    """워크스페이스 생성"""
    try:
        item = db_client.create_workspace(
            name=workspace.name, description=workspace.description
        )

        return Workspace(
            id=item["id"],
            name=item["name"],
            description=item["description"],
            createdAt=to_kst(datetime.fromisoformat(item["createdAt"])),
            functionCount=item["functionCount"],
            invocations24h=item["invocations24h"],
            errorRate=item["errorRate"],
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": {"code": "CREATE_ERROR", "message": str(e)}},
        )


@router.get("/workspaces", response_model=List[Workspace])
async def list_workspaces():
    """워크스페이스 목록 조회"""
    try:
        items = db_client.list_workspaces()

        return [
            Workspace(
                id=item["id"],
                name=item["name"],
                description=item.get("description", ""),
                createdAt=to_kst(datetime.fromisoformat(item["createdAt"])),
                functionCount=item.get("functionCount", 0),
                invocations24h=item.get("invocations24h", 0),
                errorRate=item.get("errorRate", 0.0),
            )
            for item in items
        ]
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": {"code": "LIST_ERROR", "message": str(e)}},
        )


@router.get("/workspaces/{workspace_id}", response_model=Workspace)
async def get_workspace(workspace_id: str):
    """워크스페이스 조회"""
    item = db_client.get_workspace(workspace_id)

    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": {
                    "code": "NOT_FOUND",
                    "message": f"Workspace {workspace_id} not found",
                }
            },
        )

    return Workspace(
        id=item["id"],
        name=item["name"],
        description=item.get("description", ""),
        createdAt=to_kst(datetime.fromisoformat(item["createdAt"])),
        functionCount=item.get("functionCount", 0),
        invocations24h=item.get("invocations24h", 0),
        errorRate=item.get("errorRate", 0.0),
    )


@router.patch("/workspaces/{workspace_id}", response_model=Workspace)
async def update_workspace(workspace_id: str, updates: WorkspaceUpdate):
    """워크스페이스 수정"""
    # 워크스페이스 존재 확인
    existing = db_client.get_workspace(workspace_id)
    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": {
                    "code": "NOT_FOUND",
                    "message": f"Workspace {workspace_id} not found",
                }
            },
        )

    # 수정
    item = db_client.update_workspace(
        workspace_id, name=updates.name, description=updates.description
    )

    return Workspace(
        id=item["id"],
        name=item["name"],
        description=item.get("description", ""),
        createdAt=to_kst(datetime.fromisoformat(item["createdAt"])),
        functionCount=item.get("functionCount", 0),
        invocations24h=item.get("invocations24h", 0),
        errorRate=item.get("errorRate", 0.0),
    )


@router.delete("/workspaces/{workspace_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_workspace(workspace_id: str):
    """워크스페이스 삭제"""
    # 워크스페이스 존재 확인
    existing = db_client.get_workspace(workspace_id)
    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": {
                    "code": "NOT_FOUND",
                    "message": f"Workspace {workspace_id} not found",
                }
            },
        )

    # 삭제
    db_client.delete_workspace(workspace_id)
    return None
