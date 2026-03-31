import sys
import os


# 添加项目根目录到Python路径
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
sys.path.insert(0, project_root)

# 然后进行导入
from ml_backend.wall_backend import app

if __name__ == "__main__":
    # 这里可以改端口，比如 9100，避免和 mihomo / 现有服务冲突
    app.run(host="0.0.0.0", port=9100)
