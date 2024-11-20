import os
import pytest
from pathlib import Path
from dotenv import load_dotenv
from git_query.db import GitDatabase
from fastapi.testclient import TestClient
from git_query.api import app

def pytest_configure(config):
    """
    pytest 配置初始化
    """
    # 获取项目根目录
    root_dir = Path(__file__).parent.parent
    
    # 加载测试环境配置
    env_file = root_dir / '.env.test'
    if env_file.exists():
        load_dotenv(env_file)
    else:
        raise RuntimeError(f"测试环境配置文件不存在: {env_file}")

@pytest.fixture(scope="session")
def neo4j_connection():
    """
    提供 Neo4j 数据库连接
    """
    db = GitDatabase(
        uri=os.getenv('NEO4J_URI'),
        user=os.getenv('NEO4J_USER'),
        password=os.getenv('NEO4J_PASSWORD')
    )
    yield db
    db.close()

@pytest.fixture
def test_client():
    """
    提供测试用的 FastAPI 客户端
    """
    with TestClient(app) as client:
        yield client

@pytest.fixture(autouse=True)
def setup_test_environment(neo4j_connection):
    """
    设置测试环境，每个测试前自动运行
    """
    # 在这里可以添加测试前的准备工作
    yield
    # 测试后清理数据库
    with neo4j_connection._driver.session() as session:
        session.run("MATCH (n) DETACH DELETE n")

@pytest.fixture
def mock_repo_url():
    """
    提供测试用的仓库 URL
    """
    return "https://github.com/test/repo.git"

@pytest.fixture
def mock_commits():
    """
    提供测试用的提交数据
    """
    return [
        {
            "id": "commit1",
            "message": "First commit",
            "author": "Test Author",
            "time": 1234567890,
            "parents": [],
            "depth": 0
        },
        {
            "id": "commit2",
            "message": "Second commit",
            "author": "Test Author",
            "time": 1234567891,
            "parents": ["commit1"],
            "depth": 1
        }
    ]

@pytest.fixture
def mock_refs():
    """
    提供测试用的引用数据
    """
    return {
        "start_ref": "main",
        "end_ref": "v1.0.0"
    }

@pytest.fixture
def env_vars():
    """
    提供测试环境变量
    """
    return {
        "NEO4J_URI": os.getenv("NEO4J_URI"),
        "NEO4J_USER": os.getenv("NEO4J_USER"),
        "NEO4J_PASSWORD": os.getenv("NEO4J_PASSWORD"),
        "API_HOST": os.getenv("API_HOST"),
        "API_PORT": os.getenv("API_PORT"),
        "DEBUG": os.getenv("DEBUG"),
        "TEST_MODE": os.getenv("TEST_MODE")
    } 