from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Union, Optional
from .query import GitQueryService
import uvicorn

app = FastAPI(
    title="Git Commit 查询服务",
    description="用于查询Git仓库中的提交信息"
)

# 配置 CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 允许所有来源
    allow_credentials=True,  # 允许携带凭证
    allow_methods=["*"],    # 允许所有方法
    allow_headers=["*"],    # 允许所有请求头
)

class CommitResponse(BaseModel):
    id: str
    message: str
    author: str
    time: int
    parents: List[str]
    depth: int

class ErrorResponse(BaseModel):
    error: str

class CommitDepthRequest(BaseModel):
    remote_url: str
    start_ref: str
    max_depth: int = -1

@app.get(
    "/commits/",
    response_model=List[CommitResponse],
    responses={400: {"model": ErrorResponse}},
    summary="获取两个引用之间的提交信息"
)
async def get_commits_between(
    repo_url: str,
    start_ref: str,
    end_ref: str
):
    """
    获取Git仓库中两个引用之间的所有提交信息

    - **repo_url**: Git仓库的URL
    - **start_ref**: 起始引用（可以是分支名、tag名或commit id）
    - **end_ref**: 结束引用（可以是分支名、tag名或commit id）
    """
    try:
        with GitQueryService() as query_service:
            commits = query_service.get_commits_between(repo_url, start_ref, end_ref)
            return commits
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post(
    "/commits/by-depth",
    response_model=List[CommitResponse],
    responses={400: {"model": ErrorResponse}},
    summary="获取指定深度的提交信息"
)
async def get_commits_by_depth(request: CommitDepthRequest):
    """
    获取Git仓库中从指定引用开始的指定深度的所有提交

    - **remote_url**: Git仓库的URL
    - **start_ref**: 起始引用（可以是分支名、tag名或commit id）
    - **max_depth**: 最大深度，-1表示不限制深度
    """
    try:
        with GitQueryService() as query_service:
            commits = query_service.get_commits_by_depth(
                request.remote_url,
                request.start_ref,
                request.max_depth
            )
            return commits
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get(
    "/commits/first",
    response_model=CommitResponse,
    responses={400: {"model": ErrorResponse}},
    summary="获取仓库的第一个提交"
)
async def get_first_commit(repo_url: str):
    """
    获取Git仓库的第一个提交（最初的提交）

    - **repo_url**: Git仓库的URL
    """
    try:
        with GitQueryService() as query_service:
            commit = query_service.get_first_commit(repo_url)
            return commit
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True) 