import pygit2
from pygit2.enums import ObjectType

def fetch_tag_ancestors(remote_url, tag_name, depth=1):
    """
    获取远程仓库中特定 tag 的所有祖先 commit 信息。

    :param remote_url: 远程仓库地址
    :param tag_name: 目标 tag 名称
    :param depth: 克隆深度
    :return: 包含祖先 commit 的列表，每个 commit 是一个字典
    """
    # 设置临时路径，pygit2 会在内存中创建虚拟仓库
    repo_path = './temp_repo'

    # 克隆仓库 (浅克隆)
    callbacks = pygit2.RemoteCallbacks()  # 配置认证方式，如需要可以扩展
    repo = pygit2.clone_repository(
        remote_url,
        repo_path,
        bare=True,
        callbacks=callbacks
    )
    
    # 获取指定 tag 的引用
    tag_ref = f'refs/tags/{tag_name}'
    if tag_ref not in repo.references:
        raise ValueError(f"Tag '{tag_name}' not found in the repository")

    # 获取 tag 的 commit 对象
    tag_ref = repo.lookup_reference(tag_ref)
    tag_obj = tag_ref.peel()  # 使用 peel() 来获取底层对象
    
    if tag_obj.type == ObjectType.TAG:
        target_commit = tag_obj.peel()  # 如果是标签对象，需要再次 peel 来获取 commit
    elif tag_obj.type == ObjectType.COMMIT:
        target_commit = tag_obj
    else:
        raise ValueError("Tag does not point to a commit or tag object")

    # 遍历祖先
    ancestor_commits = []
    visited = set()
    stack = [target_commit]

    while stack:
        commit = stack.pop()
        if commit.id in visited:
            continue

        visited.add(commit.id)
        ancestor_commits.append({
            "id": str(commit.id),
            "message": commit.message,
            "author": commit.author.name,
            "time": commit.commit_time,
            "parents": [str(parent.id) for parent in commit.parents]
        })

        # 添加父节点到堆栈
        stack.extend(commit.parents)

    return ancestor_commits


# 示例调用
if __name__ == "__main__":
    remote_url = "https://github.com/libgit2/pygit2.git"  # 替换为你的远程仓库地址
    tag_name = "v1.4.0"  # 替换为目标 tag 名称

    try:
        ancestors = fetch_tag_ancestors(remote_url, tag_name)
        for commit in ancestors:
            print(f"Commit ID: {commit['id']}")
            print(f"Author: {commit['author']}")
            print(f"Message: {commit['message']}")
            print(f"Time: {commit['time']}")
            print(f"Parents: {commit['parents']}")
            print("-" * 40)
    except Exception as e:
        print(f"Error: {e}")
