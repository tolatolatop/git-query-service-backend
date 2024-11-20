import pytest
from git_query.factory import GitOperationsFactory
from unittest.mock import patch

def test_extract_domain_https():
    """测试从HTTPS URL提取域名"""
    url = "https://github.com/user/repo.git"
    domain = GitOperationsFactory._extract_domain(url)
    assert domain == "github.com"

def test_extract_domain_ssh():
    """测试从SSH URL提取域名"""
    url = "git@github.com:user/repo.git"
    domain = GitOperationsFactory._extract_domain(url)
    assert domain == "github.com"

def test_get_token_for_domain():
    """测试获取域名对应的token"""
    with patch.dict('os.environ', {'GITHUB_TOKEN': 'test_token'}):
        token = GitOperationsFactory._get_token_for_domain('github.com')
        assert token == 'test_token'

def test_create_with_github():
    """测试创建GitHub仓库的操作实例"""
    with patch.dict('os.environ', {'GITHUB_TOKEN': 'github_token'}):
        git_ops = GitOperationsFactory.create('https://github.com/user/repo.git')
        assert git_ops.git_token == 'github_token'

def test_create_with_gitee():
    """测试创建Gitee仓库的操作实例"""
    with patch.dict('os.environ', {'GITEE_TOKEN': 'gitee_token'}):
        git_ops = GitOperationsFactory.create('https://gitee.com/user/repo.git')
        assert git_ops.git_token == 'gitee_token'

def test_unsupported_domain():
    """测试不支持的域名"""
    url = "https://unsupported.com/user/repo.git"
    git_ops = GitOperationsFactory.create(url)
    assert git_ops.git_token is None 