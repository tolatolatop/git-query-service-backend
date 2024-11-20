from typing import Optional
import os
import re
from .git_operations import GitOperations

class GitOperationsFactory:
    """Git操作工厂类，根据不同域名提供对应的认证信息"""
    
    # 域名到环境变量的映射
    DOMAIN_TOKEN_MAP = {
        'github.com': 'GITHUB_TOKEN',
        'gitee.com': 'GITEE_TOKEN',
        'gitlab.com': 'GITLAB_TOKEN',
    }

    @classmethod
    def create(cls, repo_url: str) -> GitOperations:
        """
        根据仓库URL创建对应的Git操作实例
        
        :param repo_url: 仓库URL
        :return: GitOperations实例
        """
        domain = cls._extract_domain(repo_url)
        token = cls._get_token_for_domain(domain)
        return GitOperations(token)

    @classmethod
    def _extract_domain(cls, url: str) -> str:
        """
        从URL中提取域名
        
        :param url: 仓库URL
        :return: 域名
        """
        # 支持 HTTP(S) 和 SSH 格式的 URL
        patterns = [
            r'https?://(?:www\.)?([^/]+)',  # HTTP(S) URL
            r'git@([^:]+):',                # SSH URL
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        
        raise ValueError(f"无法从URL中提取域名: {url}")

    @classmethod
    def _get_token_for_domain(cls, domain: str) -> Optional[str]:
        """
        获取指定域名的认证token
        
        :param domain: 域名
        :return: 认证token，如果未配置则返回None
        """
        env_var = cls.DOMAIN_TOKEN_MAP.get(domain)
        if env_var:
            return os.getenv(env_var)
        return None 