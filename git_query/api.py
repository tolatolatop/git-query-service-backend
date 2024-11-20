from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Union
from git_query.git_operations import GitOperations
import uvicorn

app = FastAPI(
    title="Git Commit 查询服务",
    description="用于查询Git仓库中两个引用之间的所有提交信息"
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
        git_ops = GitOperations()
        commits = git_ops.get_commits_between(repo_url, start_ref, end_ref)
        return commits
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True) 