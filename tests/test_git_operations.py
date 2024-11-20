import pytest
from git_query.git_operations import GitOperations
import os
from unittest.mock import patch, MagicMock

def test_git_token_auth():
    """测试Git Token认证"""
    with patch.dict(os.environ, {'GIT_TOKEN': 'test_token'}):
        git_ops = GitOperations()
        callbacks = git_ops._create_callbacks()
        
        # 验证回调中包含认证信息
        assert callbacks is not None
        assert hasattr(callbacks, 'credentials')

def test_no_git_token():
    """测试没有Git Token的情况"""
    with patch.dict(os.environ, {'GIT_TOKEN': ''}):
        git_ops = GitOperations()
        callbacks = git_ops._create_callbacks()
        
        # 验证回调不包含认证信息
        assert callbacks is not None
        assert not hasattr(callbacks, 'credentials')

@pytest.mark.integration
def test_private_repo_access():
    """测试访问私有仓库（需要token）"""
    private_repo_url = "https://github.com/your-private/repo.git"
    
    # 确保设置了token
    assert os.getenv('GIT_TOKEN'), "需要设置GIT_TOKEN环境变量"
    
    git_ops = GitOperations()
    try:
        repo = git_ops._clone_repository(private_repo_url)
        assert repo is not None
    except Exception as e:
        pytest.fail(f"使用token克隆私有仓库失败: {str(e)}") 