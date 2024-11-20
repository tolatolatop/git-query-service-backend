from typing import List, Dict, Union, Optional
from .db import GitDatabase
from .git_operations import GitOperations
import os

class GitQueryService:
    def __init__(self):
        self.db = GitDatabase(
            uri=os.getenv('NEO4J_URI'),
            user=os.getenv('NEO4J_USER'),
            password=os.getenv('NEO4J_PASSWORD')
        )
        self.git_ops = GitOperations()

    def get_commits_between(
        self,
        repo_url: str,
        start_ref: str,
        end_ref: str
    ) -> List[Dict[str, Union[str, int, List[str]]]]:
        """
        获取两个引用之间的所有提交
        优先从数据库查询，如果数据不存在则从git仓库获取并同步到数据库
        """
        try:
            # 先从git获取引用对应的commit id
            repo = self.git_ops._clone_repository(repo_url)
            start_commit = self.git_ops._get_commit_object(repo, start_ref)
            end_commit = self.git_ops._get_commit_object(repo, end_ref)
            
            # 尝试从数据库获取
            commits = self.db.get_commits_between(
                repo_url,
                str(start_commit.id),
                str(end_commit.id)
            )
            
            if commits:
                return commits
                
            # 数据库中不存在，从git获取
            commits = self.git_ops.get_commits_between(
                repo_url,
                start_ref,
                end_ref
            )
            
            # 同步到数据库
            self.db.save_commits(repo_url, commits)
            return commits
            
        except Exception as e:
            # 如果数据库查询失败，直接从git获取
            return self.git_ops.get_commits_between(
                repo_url,
                start_ref,
                end_ref
            )

    def get_commits_by_depth(
        self,
        repo_url: str,
        start_ref: str,
        max_depth: int = -1
    ) -> List[Dict[str, Union[str, int, List[str]]]]:
        """
        获取指定深度的提交
        优先从数据库查询，如果数据不存在则从git仓库获取并同步到数据库
        """
        try:
            # 先从git获取引用对应的commit id
            repo = self.git_ops._clone_repository(repo_url)
            start_commit = self.git_ops._get_commit_object(repo, start_ref)
            
            # 尝试从数据库获取
            commits = self.db.get_commits_by_depth(
                repo_url,
                str(start_commit.id),
                max_depth
            )
            
            if commits:
                return commits
                
            # 数据库中不存在，从git获取
            commits = self.git_ops.get_commits_by_depth(
                repo_url,
                start_ref,
                max_depth
            )
            
            # 同步到数据库
            self.db.save_commits(repo_url, commits)
            return commits
            
        except Exception as e:
            # 如果数据库查询失败，直接从git获取
            return self.git_ops.get_commits_by_depth(
                repo_url,
                start_ref,
                max_depth
            )

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.db.close() 