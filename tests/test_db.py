def test_save_commits(neo4j_connection, mock_repo_url, mock_commits):
    """测试保存提交信息到数据库"""
    # 保存提交信息
    neo4j_connection.save_commits(mock_repo_url, mock_commits)
    
    # 验证保存结果
    # 从最新的提交开始查询（commit2），它应该能找到所有提交
    saved_commits = neo4j_connection.get_commits_by_depth(
        mock_repo_url,
        mock_commits[1]["id"]  # commit2
    )
    assert len(saved_commits) == 2
    # commit2 应该是第一个（深度0）
    assert saved_commits[0]["id"] == mock_commits[1]["id"]  # commit2
    # commit1 应该是第二个（深度1）
    assert saved_commits[1]["id"] == mock_commits[0]["id"]  # commit1

def test_environment_variables(env_vars):
    """测试环境变量是否正确加载"""
    assert env_vars["TEST_MODE"] == "true"
    assert env_vars["NEO4J_URI"] == "bolt://localhost:7687" 