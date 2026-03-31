#!/home/star/anaconda3/envs/common/bin/python
# -*- coding: utf-8 -*-
"""
Label Studio ML Backend - 墙体缺陷检测
启动脚本
"""

import os
import sys
import logging

# 强制禁用输出缓冲，确保实时显示日志
os.environ['PYTHONUNBUFFERED'] = '1'

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 设置 DEBUG 级别日志（更详细）
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)  # 强制输出到 stdout
    ]
)

logger = logging.getLogger(__name__)

if __name__ == "__main__":
    from label_studio_ml.api import start_server
    from wall_backend import WallDefectBackend

    # 启动 ML Backend 服务器 - 开启 debug 模式
    start_server(
        model_class=WallDefectBackend,
        # 当没有传入参数时的默认值
        default_model_name=os.getenv('VISION_MODEL', 'doubao-1-5-vision-pro-32k-250115'),
        default_provider=os.getenv('VISION_PROVIDER', 'doubao'),
        # 开启 debug 模式
        debug=True,
        disable_nltk_download=True  # 禁用 nltk 下载
    )
