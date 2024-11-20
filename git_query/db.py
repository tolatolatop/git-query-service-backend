from neo4j import GraphDatabase
from typing import List, Dict, Union
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

            # 批量创建Commit节点和关系
            for commit in commits:
                session.run("""
                    MATCH (r:Repository {url: $repo_url})
                    MERGE (c:Commit {id: $commit_id})
                    ON CREATE SET 
                        c.message = $message,
                        c.author = $author,
                        c.time = $time,
                        c.depth = $depth
                    MERGE (c)-[:BELONGS_TO]->(r)
                    WITH c
                    UNWIND $parents as parent_id
                    MERGE (p:Commit {id: parent_id})
                    MERGE (c)-[:PARENT]->(p)
                """, {
                    'repo_url': repo_url,
                    'commit_id': commit['id'],
                    'message': commit['message'],
                    'author': commit['author'],
                    'time': commit['time'],
                    'depth': commit['depth'],
                    'parents': commit['parents']
                })

    def get_commits_between(self, repo_url: str, start_commit_id: str, end_commit_id: str) -> List[Dict]:
        """
        获取两个提交之间的所有提交

        :param repo_url: 仓库URL
        :param start_commit_id: 起始提交ID
        :param end_commit_id: 结束提交ID
        :return: 提交信息列表
        """
        with self._driver.session() as session:
            result = session.run("""
                MATCH (start:Commit {id: $start_id})-[*0..]->(c:Commit)
                WHERE c.id <> $end_id
                WITH COLLECT(c) as commits
                MATCH (end:Commit {id: $end_id})
                WITH commits + end as all_commits
                UNWIND all_commits as commit
                MATCH (commit)-[:BELONGS_TO]->(r:Repository {url: $repo_url})
                OPTIONAL MATCH (commit)-[:PARENT]->(p:Commit)
                WITH commit, COLLECT(p.id) as parents
                RETURN {
                    id: commit.id,
                    message: commit.message,
                    author: commit.author,
                    time: commit.time,
                    depth: commit.depth,
                    parents: parents
                } as commit_info
                ORDER BY commit.depth
            """, start_id=start_commit_id, end_id=end_commit_id, repo_url=repo_url)
            
            return [record["commit_info"] for record in result]

    def get_commits_by_depth(self, repo_url: str, start_commit_id: str, max_depth: int = -1) -> List[Dict]:
        """
        获取指定深度的提交

        :param repo_url: 仓库URL
        :param start_commit_id: 起始提交ID
        :param max_depth: 最大深度，-1表示不限制
        :return: 提交信息列表
        """
        with self._driver.session() as session:
            query = """
                MATCH (start:Commit {id: $start_id})-[*0..]->(c:Commit)
                WHERE c.depth <= $max_depth OR $max_depth = -1
                MATCH (c)-[:BELONGS_TO]->(r:Repository {url: $repo_url})
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
                ORDER BY c.depth
            """
            
            result = session.run(query, 
                               start_id=start_commit_id, 
                               max_depth=max_depth,
                               repo_url=repo_url)
            
            return [record["commit_info"] for record in result]

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
