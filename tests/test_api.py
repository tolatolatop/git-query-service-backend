import pytest
from fastapi.testclient import TestClient
from git_query.api import app
import json
from typing import List, Dict
from unittest.mock import patch, MagicMock
from datetime import datetime

client = TestClient(app)

# 测试数据
TEST_REPO = "https://github.com/libgit2/pygit2.git"
VALID_TAGS = ["v1.4.0", "v1.3.0"]
INVALID_TAG = "v999.999.0"
VALID_COMMIT = "57b03b8d4a1f8b214f6ce5f0f6dfd35918b46399"

# 模拟提交数据
MOCK_COMMITS = [
    {
        "id": "commit1",
        "message": "First commit",
        "author": "Test Author",
        "time": int(datetime.now().timestamp()),
        "parents": [],
        "depth": 0
    },
    {
        "id": "commit2",
        "message": "Second commit",
        "author": "Test Author",
        "time": int(datetime.now().timestamp()),
        "parents": ["commit1"],
        "depth": 1
    }
]

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

def test_get_commits_by_depth_success():
    """测试成功获取指定深度的提交"""
    with patch('git_query.git_operations.GitOperations.get_commits_by_depth', return_value=MOCK_COMMITS):
        response = client.post(
            "/commits/by-depth",
            json={
                "remote_url": "https://github.com/test/repo.git",
                "start_ref": "main",
                "max_depth": 2
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "id" in data[0]
        assert len(data) == 2
        assert data[0]["id"] == "commit1"
        assert data[1]["id"] == "commit2"

def test_get_commits_by_depth_unlimited():
    """测试不限制深度获取提交"""
    with patch('git_query.git_operations.GitOperations.get_commits_by_depth', return_value=MOCK_COMMITS):
        response = client.post(
            "/commits/by-depth",
            json={
                "remote_url": "https://github.com/test/repo.git",
                "start_ref": "main",
                "max_depth": -1
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2

def test_get_commits_by_depth_invalid_ref():
    """测试使用无效的引用"""
    with patch('git_query.git_operations.GitOperations.get_commits_by_depth', 
              side_effect=ValueError("Invalid reference")):
        response = client.post(
            "/commits/by-depth",
            json={
                "remote_url": "https://github.com/test/repo.git",
                "start_ref": "invalid_ref",
                "max_depth": 1
            }
        )
        
        assert response.status_code == 400
        assert "Invalid reference" in response.json()["detail"]

def test_get_commits_by_depth_server_error():
    """测试服务器错误情况"""
    with patch('git_query.git_operations.GitOperations.get_commits_by_depth', 
              side_effect=Exception("Server error")):
        response = client.post(
            "/commits/by-depth",
            json={
                "remote_url": "https://github.com/test/repo.git",
                "start_ref": "main",
                "max_depth": 1
            }
        )
        
        assert response.status_code == 500
        assert "Server error" in response.json()["detail"]

def test_get_commits_by_depth_invalid_depth():
    """测试无效的深度值"""
    response = client.post(
        "/commits/by-depth",
        json={
            "remote_url": "https://github.com/test/repo.git",
            "start_ref": "main",
            "max_depth": "invalid"  # 应该是整数
        }
    )
    
    assert response.status_code == 422  # FastAPI的验证错误状态码

def test_get_commits_by_depth_missing_url():
    """测试缺少必需的URL参数"""
    response = client.post(
        "/commits/by-depth",
        json={
            "start_ref": "main",
            "max_depth": 1
        }
    )
    
    assert response.status_code == 422

def test_cors_preflight():
    """测试 CORS 预检请求"""
    response = client.options(
        "/commits/",
        headers={
            "Origin": "http://example.com",
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "Content-Type",
        }
    )
    
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "*"
    assert "GET" in response.headers["access-control-allow-methods"]
    assert "Content-Type" in response.headers["access-control-allow-headers"]

def test_cors_actual_request():
    """测试带有 CORS 头的实际请求"""
    response = client.get(
        "/commits/",
        headers={"Origin": "http://example.com"},
        params={
            "repo_url": TEST_REPO,
            "start_ref": VALID_TAGS[0],
            "end_ref": VALID_TAGS[1]
        }
    )
    
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "*"

def test_get_first_commit():
    """测试获取仓库的第一个提交"""
    response = client.get(
        "/commits/first",
        params={"repo_url": TEST_REPO}
    )
    
    assert response.status_code == 200
    commit = response.json()
    
    # 验证返回的提交信息格式
    assert all(key in commit for key in [
        "id", "message", "author", "time", "parents", "depth"
    ])
    # 第一个提交没有父提交
    assert commit["parents"] == []
    # 深度应该为0
    assert commit["depth"] == 0

def test_get_first_commit_invalid_repo():
    """测试获取无效仓库的第一个提交"""
    response = client.get(
        "/commits/first",
        params={"repo_url": "https://github.com/nonexistent/repo.git"}
    )
    
    assert response.status_code == 400
