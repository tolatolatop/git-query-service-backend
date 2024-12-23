import pygit2
from pygit2.enums import ObjectType
from typing import List, Dict, Union, Optional
import tempfile
import shutil
import os
from pathlib import Path

class GitOperations:
    def __init__(self, token: Optional[str] = None):
        """
        初始化Git操作类
        
        :param token: Git认证token，如果不提供则尝试从GIT_TOKEN环境变量获取
        """
        # 创建临时目录
        self.temp_dir = tempfile.mkdtemp(prefix='git_query_')
        self.repo_path = Path(self.temp_dir) / 'repo'
        # 获取 Git Token
        self.git_token = token or os.getenv('GIT_TOKEN')

    def __del__(self):
        """清理临时目录"""
        try:
            if os.path.exists(self.temp_dir):
                shutil.rmtree(self.temp_dir)
        except Exception:
            pass

    def _create_callbacks(self) -> pygit2.RemoteCallbacks:
        """创建带有认证信息的回调"""
        if self.git_token:
            # 使用token创建认证回调
            credentials = pygit2.UserPass("git", self.git_token)
            return pygit2.RemoteCallbacks(credentials=credentials)
        return pygit2.RemoteCallbacks()

    def _clone_repository(self, remote_url: str) -> pygit2.Repository:
        """克隆仓库或使用现有仓库"""
        try:
            return pygit2.Repository(str(self.repo_path))
        except:
            # 确保目录存在
            self.repo_path.parent.mkdir(parents=True, exist_ok=True)
            
            # 使用带认证的回调
            callbacks = self._create_callbacks()
            return pygit2.clone_repository(
                remote_url,
                str(self.repo_path),
                bare=True,
                callbacks=callbacks
            )

    def _get_commit_object(self, repo: pygit2.Repository, ref_name: str) -> pygit2.Commit:
        """获取指定引用的commit对象"""
        try:
            if ref_name.startswith('refs/'):
                ref_path = ref_name
            else:
                # 尝试不同的引用路径
                possible_refs = [
                    f'refs/tags/{ref_name}',
                    f'refs/heads/{ref_name}',
                    ref_name  # 可能是commit id
                ]
                ref_path = next(
                    ref for ref in possible_refs
                    if ref in repo.references or repo.get(ref_name)
                )

            if ref_path in repo.references:
                ref = repo.lookup_reference(ref_path)
                obj = ref.peel()
                if obj.type == ObjectType.TAG:
                    return obj.peel()
                return obj
            else:
                # 尝试作为commit id处理
                obj = repo.get(ref_name)
                if obj and obj.type == ObjectType.COMMIT:
                    return obj
                raise ValueError(f"Error: Reference not found: {ref_name}")
        except StopIteration:
            raise ValueError(f"Error: Invalid reference: {ref_name}")

    def get_commits_between(
        self,
        remote_url: str,
        start_ref: str,
        end_ref: str
    ) -> List[Dict[str, Union[str, int, List[str]]]]:
        """
        获取两个引用之间的所有提交信息

        :param remote_url: 远程仓库地址
        :param start_ref: 起始引用（分支名、tag名或commit id）
        :param end_ref: 结束引用（分支名、tag名或commit id）
        :return: 包含提交信息的列表
        """
        repo = self._clone_repository(remote_url)
        
        # 获取起始和结束的commit对象
        start_commit = self._get_commit_object(repo, start_ref)
        end_commit = self._get_commit_object(repo, end_ref)

        # 使用广度优先搜索获取所有提交
        commits = []
        visited = set()
        queue = [(start_commit, 0)]  # (commit, depth)
        found_end = False

        while queue and not found_end:
            commit, depth = queue.pop(0)
            if commit.id in visited:
                continue

            visited.add(commit.id)
            
            # 添加提交信息
            commits.append({
                "id": str(commit.id),
                "message": commit.message,
                "author": commit.author.name,
                "time": commit.commit_time,
                "parents": [str(parent.id) for parent in commit.parents],
                "depth": depth
            })

            # 检查是否到达目标提交
            if commit.id == end_commit.id:
                found_end = True
                break

            # 将父提交添加到队列
            for parent in commit.parents:
                queue.append((parent, depth + 1))

        if not found_end:
            raise ValueError("在遍历过程中未找到目标提交")

        return commits 

    def get_commits_by_depth(
        self,
        remote_url: str,
        start_ref: str,
        max_depth: int = -1
    ) -> List[Dict[str, Union[str, int, List[str]]]]:
        """
        获取指定引用向前追溯指定深度的所有提交

        :param remote_url: 远程仓库地址
        :param start_ref: 起始引用（分支名、tag名或commit id）
        :param max_depth: 最大深度，-1表示不限制深度
        :return: 包含提交信息的列表
        """
        repo = self._clone_repository(remote_url)
        
        # 获取起始commit对象
        start_commit = self._get_commit_object(repo, start_ref)

        # 使用广度优先搜索获取所有提交
        commits = []
        visited = set()
        queue = [(start_commit, 0)]  # (commit, depth)

        while queue:
            commit, depth = queue.pop(0)
            
            # 如果设置了最大深度且当前深度超过最大深度，跳过
            if max_depth != -1 and depth > max_depth:
                continue
                
            if commit.id in visited:
                continue

            visited.add(commit.id)
            
            # 添加提交信息
            commits.append({
                "id": str(commit.id),
                "message": commit.message,
                "author": commit.author.name,
                "time": commit.commit_time,
                "parents": [str(parent.id) for parent in commit.parents],
                "depth": depth
            })

            # 将父提交添加到队列
            for parent in commit.parents:
                queue.append((parent, depth + 1))

        return commits 

    def get_first_commit(self, remote_url: str) -> Dict[str, Union[str, int, List[str]]]:
        """
        获取仓库的第一个提交节点（最初的提交）
        使用 git rev-list 命令直接获取最早的提交

        :param remote_url: 仓库URL
        :return: 提交信息
        """
        repo = self._clone_repository(remote_url)
        
        try:
            # 使用 rev-list 命令获取最早的提交
            # 这比遍历所有提交要快得多
            first_commit_id = repo.revparse_single('HEAD').hex
            for commit in repo.walk(first_commit_id, pygit2.GIT_SORT_TOPOLOGICAL | pygit2.GIT_SORT_TIME):
                # GIT_SORT_TOPOLOGICAL 确保按照拓扑顺序遍历
                # GIT_SORT_TIME 按时间戳排序
                if len(commit.parents) == 0:
                    # 找到没有父提交的提交，即为最初提交
                    return {
                        "id": str(commit.id),
                        "message": commit.message,
                        "author": commit.author.name,
                        "time": commit.commit_time,
                        "parents": [],
                        "depth": 0
                    }
            
            raise ValueError("未找到初始提交")
            
        except Exception as e:
            raise ValueError(f"获取第一个提交失败: {str(e)}")

    def get_commit_batch_with_parents(
        self,
        repo: pygit2.Repository,
        start_commit_id: str,
        batch_size: int = 100
    ) -> List[Dict[str, Union[str, int, List[str]]]]:
        """
        获取指定提交及其上游的一批提交

        :param repo: Git仓库对象
        :param start_commit_id: 起始提交ID
        :param batch_size: 批次大小
        :return: 提交信息列表
        """
        try:
            commits = []
            visited = set()
            queue = [(repo.get(start_commit_id), 0)]  # (commit, depth)
            
            while queue and len(commits) < batch_size:
                commit, depth = queue.pop(0)
                if commit.id in visited:
                    continue
                    
                visited.add(commit.id)
                commits.append({
                    "id": str(commit.id),
                    "message": commit.message,
                    "author": commit.author.name,
                    "time": commit.commit_time,
                    "parents": [str(parent.id) for parent in commit.parents],
                    "depth": depth
                })
                
                # 将父提交添加到队列
                for parent in commit.parents:
                    queue.append((parent, depth + 1))
                    
            return commits
            
        except KeyError as e:
            raise ValueError(f"无效的提交ID: {start_commit_id}")
        except Exception as e:
            raise ValueError(f"获取提交批次失败: {str(e)}")