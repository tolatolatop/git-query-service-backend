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


@pytest.fixture
def mock_git_operations():
    with patch('git_query.query.GitOperations') as mock:
        ops = mock.return_value
        # 模拟克隆仓库
        ops._clone_repository.return_value = MagicMock()
        # 模拟获取commit对象
        ops._get_commit_object.return_value = MagicMock(id='commit1')
        # 模拟获取提交
        ops.get_commits_between.return_value = MOCK_COMMITS
        ops.get_commits_by_depth.return_value = MOCK_COMMITS
        yield ops

@pytest.fixture
def mock_db():
    with patch('git_query.query.GitDatabase') as mock:
        db = mock.return_value
        # 第一次查询返回空（模拟缓存未命中）
        db.get_commits_between.side_effect = [[], MOCK_COMMITS]
        db.get_commits_by_depth.side_effect = [[], MOCK_COMMITS]
        yield db

def test_get_commits_between_with_cache(mock_git_operations, mock_db):
    """测试获取提交时的缓存机制"""
    repo_url = "https://github.com/test/repo.git"
    start_ref = "main"
    end_ref = "v1.0.0"

    # 第一次请求（缓存未命中）
    response1 = client.get(f"/commits/?repo_url={repo_url}&start_ref={start_ref}&end_ref={end_ref}")
    assert response1.status_code == 200
    result1 = response1.json()

    # 验证 Git 操作被调用
    mock_git_operations.get_commits_between.assert_called_once()
    # 验证数据被保存到数据库
    mock_db.save_commits.assert_called_once()

    # 重置计数器
    mock_git_operations.get_commits_between.reset_mock()
    mock_db.save_commits.reset_mock()

    # 第二次请求（应该命中缓存）
    response2 = client.get(f"/commits/?repo_url={repo_url}&start_ref={start_ref}&end_ref={end_ref}")
    assert response2.status_code == 200
    result2 = response2.json()

    # 验证结果一致
    assert result1 == result2
    # 验证没有再次调用 Git 操作
    mock_git_operations.get_commits_between.assert_not_called()
    # 验证没有再次保存到数据库
    mock_db.save_commits.assert_not_called()

def test_get_commits_by_depth_with_cache(mock_git_operations, mock_db):
    """测试按深度获取提交时的缓存机制"""
    request_data = {
        "remote_url": "https://github.com/test/repo.git",
        "start_ref": "main",
        "max_depth": 2
    }

    # 第一次请求（缓存未命中）
    response1 = client.post("/commits/by-depth", json=request_data)
    assert response1.status_code == 200
    result1 = response1.json()

    # 验证 Git 操作被调用
    mock_git_operations.get_commits_by_depth.assert_called_once()
    # 验证数据被保存到数据库
    mock_db.save_commits.assert_called_once()

    # 重置计数器
    mock_git_operations.get_commits_by_depth.reset_mock()
    mock_db.save_commits.reset_mock()

    # 第二次请求（应该命中缓存）
    response2 = client.post("/commits/by-depth", json=request_data)
    assert response2.status_code == 200
    result2 = response2.json()

    # 验证结果一致
    assert result1 == result2
    # 验证没有再次调用 Git 操作
    mock_git_operations.get_commits_by_depth.assert_not_called()
    # 验证没有再次保存到数据库
    mock_db.save_commits.assert_not_called()

def test_database_fallback(mock_git_operations, mock_db):
    """测试数据库失败时的回退机制"""
    repo_url = "https://github.com/test/repo.git"
    start_ref = "main"
    end_ref = "v1.0.0"

    # 模拟数据库查询抛出异常
    mock_db.get_commits_between.side_effect = Exception("Database error")

    # 发送请求
    response = client.get(f"/commits/?repo_url={repo_url}&start_ref={start_ref}&end_ref={end_ref}")
    assert response.status_code == 200

    # 验证直接使用了 Git 操作
    mock_git_operations.get_commits_between.assert_called_once()
    # 验证没有尝试保存到数据库（因为数据库已经失败）
    mock_db.save_commits.assert_not_called()

