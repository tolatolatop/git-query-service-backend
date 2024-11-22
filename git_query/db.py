from neo4j import GraphDatabase
from typing import List, Dict, Union, Optional
import logging

class GitDatabase:
    def __init__(self, uri: str, user: str, password: str):
        """
        初始化Neo4j数据库连接

        :param uri: Neo4j数据库URI
        :param user: 用户名
        :param password: 密码
        """
        self._driver = GraphDatabase.driver(uri, auth=(user, password))
        self._init_constraints()

    def _init_constraints(self):
        """初始化数据库约束"""
        with self._driver.session() as session:
            # 为Commit节点创建唯一性约束
            session.run("""
                CREATE CONSTRAINT commit_id IF NOT EXISTS
                FOR (c:Commit) REQUIRE c.id IS UNIQUE
            """)
            
            # 为Repository节点创建唯一性约束
            session.run("""
                CREATE CONSTRAINT repo_url IF NOT EXISTS
                FOR (r:Repository) REQUIRE r.url IS UNIQUE
            """)

    def close(self):
        """关闭数据库连接"""
        self._driver.close()

    def save_commits(self, repo_url: str, commits: List[Dict[str, Union[str, int, List[str]]]]):
        """
        保存提交信息到数据库

        :param repo_url: 仓库URL
        :param commits: 提交信息列表
        """
        with self._driver.session() as session:
            # 创建或获取Repository节点
            session.run("""
                MERGE (r:Repository {url: $repo_url})
            """, repo_url=repo_url)

            # 首先创建所有Commit节点
            for commit in commits:
                session.run("""
                    MERGE (c:Commit {id: $commit_id})
                    ON CREATE SET 
                        c.message = $message,
                        c.author = $author,
                        c.time = $time,
                        c.depth = $depth
                    WITH c
                    MATCH (r:Repository {url: $repo_url})
                    MERGE (c)-[:BELONGS_TO]->(r)
                """, {
                    'repo_url': repo_url,
                    'commit_id': commit['id'],
                    'message': commit['message'],
                    'author': commit['author'],
                    'time': commit['time'],
                    'depth': commit['depth']
                })

            # 然后创建所有父子关系
            for commit in commits:
                if commit['parents']:
                    session.run("""
                        MATCH (c:Commit {id: $commit_id})
                        UNWIND $parents as parent_id
                        MATCH (p:Commit {id: parent_id})
                        MERGE (c)-[:PARENT]->(p)
                    """, {
                        'commit_id': commit['id'],
                        'parents': commit['parents']
                    })

    def get_commits_between(self, repo_url: str, start_commit_id: str, end_commit_id: str) -> List[Dict]:
        """
        获取两个提交之间的所有提交

        :param repo_url: 仓库URL
        :param start_commit_id: 起始提交ID（较新的提交）
        :param end_commit_id: 结束提交ID（较老的提交）
        :return: 提交信息列表，按深度排序（从新到旧）
        """
        with self._driver.session() as session:
            result = session.run("""
                MATCH path = shortestPath((start:Commit {id: $start_id})-[:PARENT*]->(end:Commit {id: $end_id}))
                WITH nodes(path) as commits
                UNWIND range(0, size(commits)-1) as idx
                WITH commits[idx] as commit, idx as depth
                MATCH (commit)-[:BELONGS_TO]->(r:Repository {url: $repo_url})
                OPTIONAL MATCH (commit)-[:PARENT]->(p:Commit)
                WITH commit, depth, COLLECT(p.id) as parents
                RETURN {
                    id: commit.id,
                    message: commit.message,
                    author: commit.author,
                    time: commit.time,
                    depth: depth,
                    parents: parents
                } as commit_info
                ORDER BY depth ASC
            """, start_id=start_commit_id, end_id=end_commit_id, repo_url=repo_url)
            
            return [record["commit_info"] for record in result]

    def get_commits_by_depth(self, repo_url: str, start_commit_id: str, max_depth: int = -1) -> List[Dict]:
        """
        获取指定深度的提交，从起始提交（最新）向父提交（更早）遍历

        :param repo_url: 仓库URL
        :param start_commit_id: 起始提交ID（最新的提交）
        :param max_depth: 最大深度，-1表示不限制
        :return: 提交信息列表，按深度排序（从新到旧）
        """
        with self._driver.session() as session:
            query = """
                MATCH path = (start:Commit {id: $start_id})-[:PARENT*0..]->(c:Commit)
                WHERE $max_depth = -1 OR length(path) <= $max_depth
                MATCH (c)-[:BELONGS_TO]->(r:Repository {url: $repo_url})
                OPTIONAL MATCH (c)-[:PARENT]->(p:Commit)
                WITH c, length(path) as depth, COLLECT(p.id) as parents
                RETURN {
                    id: c.id,
                    message: c.message,
                    author: c.author,
                    time: c.time,
                    depth: depth,
                    parents: parents
                } as commit_info
                ORDER BY depth ASC
            """
            
            result = session.run(
                query,
                start_id=start_commit_id,
                max_depth=max_depth,
                repo_url=repo_url
            )
            
            return [record["commit_info"] for record in result]

    def get_commit_by_id(self, repo_url: str, commit_id: str) -> Optional[Dict]:
        """
        根据commit id快速查询单个提交信息

        :param repo_url: 仓库URL
        :param commit_id: 提交ID
        :return: 提交信息，如果不存在则返回None
        """
        with self._driver.session() as session:
            result = session.run("""
                MATCH (c:Commit {id: $commit_id})-[:BELONGS_TO]->(r:Repository {url: $repo_url})
                OPTIONAL MATCH (c)-[:PARENT]->(p:Commit)
                WITH c, COLLECT(p.id) as parents
                RETURN {
                    id: c.id,
                    message: c.message,
                    author: c.author,
                    time: c.time,
                    depth: c.depth,
                    parents: parents
                } as commit_info
            """, commit_id=commit_id, repo_url=repo_url)
            
            record = result.single()
            return record["commit_info"] if record else None

    def delete_repository(self, repo_url: str) -> int:
        """
        删除仓库及其所有相关的提交信息

        :param repo_url: 仓库URL
        :return: 删除的节点数量
        """
        with self._driver.session() as session:
            # 首先统计要删除的节点数量
            count_result = session.run("""
                MATCH (r:Repository {url: $repo_url})<-[:BELONGS_TO]-(c:Commit)
                RETURN count(c) as commit_count
            """, repo_url=repo_url)
            commit_count = count_result.single()["commit_count"] if count_result.single() else 0

            # 删除仓库及其所有相关的提交
            result = session.run("""
                MATCH (r:Repository {url: $repo_url})
                OPTIONAL MATCH (r)<-[:BELONGS_TO]-(c:Commit)
                DETACH DELETE c, r
            """, repo_url=repo_url)
            
            return commit_count

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
