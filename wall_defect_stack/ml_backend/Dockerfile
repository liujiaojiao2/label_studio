FROM python:3.11-slim

WORKDIR /app

# 基础依赖
RUN pip install --no-cache-dir \
    label-studio-ml==1.0.0 \
    minio \
    pillow

# 把模型代码和后端代码拷进容器
COPY unified_vision_model.py wall_backend.py ./

# 默认端口
ENV LABEL_STUDIO_ML_BACKEND_PORT=9090

CMD ["python", "wall_backend.py"]
