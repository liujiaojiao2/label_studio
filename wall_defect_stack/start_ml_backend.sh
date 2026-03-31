#!/bin/bash
# ML Backend 启动脚本

# 进入项目目录
cd "$(dirname "$0")"

# Label Studio 配置
export LABEL_STUDIO_URL="http://192.168.0.116:7080"
export LABEL_STUDIO_API_KEY=""  # 请在这里填入您的 Label Studio API Token

# 视觉模型配置
export VISION_PROVIDER="doubao"
export VISION_MODEL="doubao-1-5-vision-pro-32k-250115"
export ARK_API_KEY="${ARK_API_KEY}"  # 使用现有的环境变量

# MinIO 配置
export MINIO_ENDPOINT="localhost:39000"  # 使用宿主机端口
export MINIO_BUCKET="wall-defects"
export MINIO_DST_PREFIX="classified"
export MINIO_ACCESS_KEY="minioadmin"
export MINIO_SECRET_KEY="minioadmin123"

# 模型目录
export MODEL_DIR="$(pwd)/ml_backend/wall_backend"

# 启动服务
echo "🚀 启动 ML Backend 服务..."
echo "   Label Studio: ${LABEL_STUDIO_URL}"
echo "   端口: 9100"
echo ""

label-studio-ml start ml_backend/wall_backend --port 9100

