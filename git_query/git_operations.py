import pygit2
from pygit2.enums import ObjectType
from typing import List, Dict, Union, Optional
import tempfile
import shutil
import os
from pathlib import Path

class GitOperations:
    def __init__(self):
        # 创建临时目录
        self.temp_dir = tempfile.mkdtemp(prefix='git_query_')
        self.repo_path = Path(self.temp_dir) / 'repo'

    def __del__(self):
        """清理临时目录"""
        try:
            if os.path.exists(self.temp_dir):
                shutil.rmtree(self.temp_dir)
        except Exception:
            pass

    def _clone_repository(self, remote_url: str) -> pygit2.Repository:
        """克隆仓库或使用现有仓库"""
        try:
            return pygit2.Repository(str(self.repo_path))
        except:
            # 确保目录存在
            self.repo_path.parent.mkdir(parents=True, exist_ok=True)
            
            callbacks = pygit2.RemoteCallbacks()
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