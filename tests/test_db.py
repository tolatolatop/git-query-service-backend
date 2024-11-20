def test_save_commits(neo4j_connection, mock_repo_url, mock_commits):
    """测试保存提交信息到数据库"""
    # 保存提交信息
    neo4j_connection.save_commits(mock_repo_url, mock_commits)
    
    # 验证保存结果
    saved_commits = neo4j_connection.get_commits_by_depth(
        mock_repo_url,
        mock_commits[0]["id"]
    )
    assert len(saved_commits) == len(mock_commits)
    assert saved_commits[0]["id"] == mock_commits[0]["id"]

def test_environment_variables(env_vars):
    """测试环境变量是否正确加载"""
    assert env_vars["TEST_MODE"] == "true"
    assert env_vars["NEO4J_URI"] == "bolt://neo4j:7687" 