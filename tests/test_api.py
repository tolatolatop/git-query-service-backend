import pytest
from fastapi.testclient import TestClient
from git_query.api import app
import json
from typing import List, Dict

client = TestClient(app)

# 测试数据
TEST_REPO = "https://github.com/libgit2/pygit2.git"
VALID_TAGS = ["v1.4.0", "v1.3.0"]
INVALID_TAG = "v999.999.0"
VALID_COMMIT = "57b03b8d4a1f8b214f6ce5f0f6dfd35918b46399"

def test_get_commits_between_valid_tags():
    """测试使用有效的tag获取提交信息"""
    response = client.get(
        "/commits/",
        params={
            "repo_url": TEST_REPO,
            "start_ref": VALID_TAGS[0],
            "end_ref": VALID_TAGS[1]
        }
    )
    
    assert response.status_code == 200
    commits = response.json()
    assert isinstance(commits, list)
    assert len(commits) > 0
    
    # 验证返回的提交信息格式
    first_commit = commits[0]
    assert all(key in first_commit for key in [
        "id", "message", "author", "time", "parents", "depth"
    ])

def test_get_commits_with_invalid_tag():
    """测试使用无效的tag"""
    response = client.get(
        "/commits/",
        params={
            "repo_url": TEST_REPO,
            "start_ref": INVALID_TAG,
            "end_ref": VALID_TAGS[0]
        }
    )
    
    assert response.status_code == 400
    assert INVALID_TAG in response.json()["detail"]

def test_get_commits_with_commit_id():
    """测试使用commit id作为引用"""
    response = client.get(
        "/commits/",
        params={
            "repo_url": TEST_REPO,
            "start_ref": VALID_COMMIT,
            "end_ref": VALID_TAGS[0]
        }
    )
    
    assert response.status_code == 200
    commits = response.json()
    assert isinstance(commits, list)
    assert len(commits) > 0

def test_get_commits_with_invalid_repo():
    """测试使用无效的仓库地址"""
    response = client.get(
        "/commits/",
        params={
            "repo_url": "https://github.com/nonexistent/repo.git",
            "start_ref": VALID_TAGS[0],
            "end_ref": VALID_TAGS[1]
        }
    )
    
    assert response.status_code == 400

def test_commits_response_structure():
    """测试返回的提交信息结构"""
    response = client.get(
        "/commits/",
        params={
            "repo_url": TEST_REPO,
            "start_ref": VALID_TAGS[0],
            "end_ref": VALID_TAGS[1]
        }
    )
    
    assert response.status_code == 200
    commits = response.json()
    
    for commit in commits:
        assert isinstance(commit["id"], str)
        assert isinstance(commit["message"], str)
        assert isinstance(commit["author"], str)
        assert isinstance(commit["time"], int)
        assert isinstance(commit["parents"], list)
        assert isinstance(commit["depth"], int)
        
        # 验证commit id的格式（40个十六进制字符）
        assert len(commit["id"]) == 40
        int(commit["id"], 16)  # 确保是有效的十六进制

    assert len(commits) == 22

def test_commits_depth_order():
    """测试提交的深度是否正确递增"""
    response = client.get(
        "/commits/",
        params={
            "repo_url": TEST_REPO,
            "start_ref": VALID_TAGS[0],
            "end_ref": VALID_TAGS[1]
        }
    )
    
    assert response.status_code == 200
    commits = response.json()
    
    # 验证深度值是否合理
    assert commits[0]["depth"] == 0  # 第一个提交的深度应该是0
    for i in range(1, len(commits)):
        assert commits[i]["depth"] >= commits[i-1]["depth"]

@pytest.mark.parametrize("params", [
    {},  # 缺少所有参数
    {"repo_url": TEST_REPO},  # 缺少引用参数
    {"repo_url": TEST_REPO, "start_ref": VALID_TAGS[0]},  # 缺少end_ref
    {"start_ref": VALID_TAGS[0], "end_ref": VALID_TAGS[1]},  # 缺少repo_url
])
def test_missing_parameters(params):
    """测试缺少必要参数的情况"""
    response = client.get("/commits/", params=params)
    assert response.status_code == 422  # FastAPI的参数验证错误码 
