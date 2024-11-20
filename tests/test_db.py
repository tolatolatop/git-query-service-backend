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

def test_incremental_commits(neo4j_connection, mock_repo_url):
    """测试增量添加提交并查询中间提交"""
    # 准备老的提交数据
    old_commits = [
        {
            "id": "commit_old_1",
            "message": "Old commit 1",
            "author": "Test Author",
            "time": 1234567880,
            "parents": [],
            "depth": 1
        },
        {
            "id": "commit_old_2",
            "message": "Old commit 2",
            "author": "Test Author",
            "time": 1234567885,
            "parents": ["commit_old_1"],
            "depth": 0
        }
    ]
    
    # 准备新的提交数据
    new_commits = [
        {
            "id": "commit_new_1",
            "message": "New commit 1",
            "author": "Test Author",
            "time": 1234567890,
            "parents": ["commit_old_2"],
            "depth": 1
        },
        {
            "id": "commit_new_2",
            "message": "New commit 2",
            "author": "Test Author",
            "time": 1234567895,
            "parents": ["commit_new_1"],
            "depth": 0
        }
    ]
    
    # 首先保存老的提交
    neo4j_connection.save_commits(mock_repo_url, old_commits)
    
    # 然后保存新的提交
    neo4j_connection.save_commits(mock_repo_url, new_commits)
    
    # 获取从最新提交到最老提交之间的所有提交
    commits_between = neo4j_connection.get_commits_between(
        mock_repo_url,
        new_commits[1]["id"],  # commit_new_2
        old_commits[0]["id"]   # commit_old_1
    )
    
    # 验证结果
    assert len(commits_between) == 4  # 应该有4个提交
    
    # 验证提交顺序（从新到旧）
    expected_order = [
        "commit_new_2",  # 最新的提交
        "commit_new_1",
        "commit_old_2",
        "commit_old_1"   # 最老的提交
    ]
    
    actual_order = [commit["id"] for commit in commits_between]
    assert actual_order == expected_order
    
    # 验证深度值
    for i, commit in enumerate(commits_between):
        assert commit["depth"] == i
    
    # 验证父子关系
    assert commits_between[0]["parents"] == ["commit_new_1"]
    assert commits_between[1]["parents"] == ["commit_old_2"]
    assert commits_between[2]["parents"] == ["commit_old_1"]
    assert commits_between[3]["parents"] == []
    