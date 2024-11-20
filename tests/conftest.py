import sys
from pathlib import Path

# 将项目根目录添加到 Python 路径
project_root = str(Path(__file__).parent.parent)
if project_root not in sys.path:
    sys.path.insert(0, project_root) 