from typing import List, Dict, Union, Optional
from .db import GitDatabase
from .factory import GitOperationsFactory
import os
import pygit2

class GitQueryService:
    def __init__(self):
        self.db = GitDatabase(
            uri=os.getenv('NEO4J_URI'),
            user=os.getenv('NEO4J_USER'),
            password=os.getenv('NEO4J_PASSWORD')
        )

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
            # 使用工厂创建git操作实例
            git_ops = GitOperationsFactory.create(repo_url)
            
            # 先从git获取引用对应的commit id
            repo = git_ops._clone_repository(repo_url)
            start_commit = git_ops._get_commit_object(repo, start_ref)
            end_commit = git_ops._get_commit_object(repo, end_ref)
            
            # 尝试从数据库获取
            commits = self.db.get_commits_between(
                repo_url,
                str(start_commit.id),
                str(end_commit.id)
            )
            
            if commits:
                return commits
                
            # 数据库中不存在，从git获取
            commits = git_ops.get_commits_between(
                repo_url,
                start_ref,
                end_ref
            )
            
            # 同步到数据库
            self.db.save_commits(repo_url, commits)
            return commits
            
        except Exception as e:
            # 如果数据库查询失败，直接从git获取
            return git_ops.get_commits_between(
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
            # 使用工厂创建git操作实例
            git_ops = GitOperationsFactory.create(repo_url)
            
            # 先从git获取引用对应的commit id
            repo = git_ops._clone_repository(repo_url)
            start_commit = git_ops._get_commit_object(repo, start_ref)
            
            # 尝试从数据库获取
            commits = self.db.get_commits_by_depth(
                repo_url,
                str(start_commit.id),
                max_depth
            )
            
            if commits:
                return commits
                
            # 数据库中不存在，从git获取
            commits = git_ops.get_commits_by_depth(
                repo_url,
                start_ref,
                max_depth
            )
            
            # 同步到数据库
            self.db.save_commits(repo_url, commits)
            return commits
            
        except Exception as e:
            # 如果数据库查询失败，直接从git获取
            return git_ops.get_commits_by_depth(
                repo_url,
                start_ref,
                max_depth
            )

    def get_first_commit(self, repo_url: str) -> Dict[str, Union[str, int, List[str]]]:
        """
        获取仓库的第一个提交节点
        优先从数据库查询，如果数据不存在则从git仓库获取并同步到数据库
        """
        try:
            # 使用工厂创建git操作实例
            git_ops = GitOperationsFactory.create(repo_url)
            
            # 获取第一个提交
            commit = git_ops.get_first_commit(repo_url)
            
            # 同步到数据库
            self.db.save_commits(repo_url, [commit])
            return commit
            
        except Exception as e:
            raise ValueError(f"获取第一个提交失败: {str(e)}")

    def get_commit_by_id(
        self,
        repo_url: str,
        commit_id: str
    ) -> Dict[str, Union[str, int, List[str]]]:
        """
        快速查询单个提交信息
        优先从数据库查询，如果数据不存在则从git仓库获取并同步到数据库
        """
        try:
            # 先尝试从数据库获取
            commit = self.db.get_commit_by_id(repo_url, commit_id)
            if commit:
                return commit

            # 数据库中不存在，从git获取
            git_ops = GitOperationsFactory.create(repo_url)
            repo = git_ops._clone_repository(repo_url)
            
            try:
                commit_obj = repo.get(commit_id)
                if commit_obj and commit_obj.type == pygit2.GIT_OBJ_COMMIT:
                    commit = {
                        "id": str(commit_obj.id),
                        "message": commit_obj.message,
                        "author": commit_obj.author.name,
                        "time": commit_obj.commit_time,
                        "parents": [str(parent.id) for parent in commit_obj.parents],
                        "depth": 0  # 单个提交查询时深度设为0
                    }
                    # 同步到数据库
                    self.db.save_commits(repo_url, [commit])
                    return commit
                else:
                    raise ValueError(f"提交ID不存在或不是有效的提交: {commit_id}")
            except KeyError:
                raise ValueError(f"提交ID不存在: {commit_id}")
                
        except Exception as e:
            raise ValueError(f"获取提交信息失败: {str(e)}")

    def sync_commit_history(
        self,
        repo_url: str,
        commit_id: str,
        batch_size: int = 100
    ) -> int:
        """
        同步指定提交ID的上游历史到数据库
        采用分批获取和存储的方式，直到找到已存在的提交或到达仓库起始

        :param repo_url: 仓库URL
        :param commit_id: 起始提交ID
        :param batch_size: 每批获取的提交数量
        :return: 同步的提交总数
        """
        try:
            git_ops = GitOperationsFactory.create(repo_url)
            repo = git_ops._clone_repository(repo_url)
            
            total_synced = 0
            current_commit_id = commit_id
            
            while True:
                # 检查当前提交是否已存在于数据库
                if self.db.get_commit_by_id(repo_url, current_commit_id):
                    break
                
                # 获取一批提交
                commits = git_ops.get_commit_batch_with_parents(
                    repo,
                    current_commit_id,
                    batch_size
                )
                
                if not commits:
                    break
                
                # 保存到数据库
                self.db.save_commits(repo_url, commits)
                total_synced += len(commits)
                
                # 获取最后一个提交的父提交作为下一批的起点
                last_commit = commits[-1]
                if not last_commit["parents"]:
                    break  # 到达仓库起始点
                    
                current_commit_id = last_commit["parents"][0]
            
            return total_synced
            
        except Exception as e:
            raise ValueError(f"同步提交历史失败: {str(e)}")

    def delete_repository(self, repo_url: str) -> Dict[str, Union[int, str]]:
        """
        删除仓库的所有信息

        :param repo_url: 仓库URL
        :return: 包含删除结果的字典
        """
        try:
            deleted_count = self.db.delete_repository(repo_url)
            return {
                "deleted_commits": deleted_count,
                "repository_url": repo_url,
                "status": "success",
                "message": f"成功删除仓库及其 {deleted_count} 个提交"
            }
        except Exception as e:
            raise ValueError(f"删除仓库失败: {str(e)}")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.db.close() 