# wall_backend.py
from label_studio_ml.api import init_app
from label_studio_ml.model import LabelStudioMLBase
from label_studio_tools.core.utils.io import get_local_path as get_local_path_from_url

from minio import Minio
from urllib.parse import urlparse
from pathlib import Path
import os
import json
import logging
import tempfile
import requests

from ml_backend.model_3 import UnifiedVisionModel

# 配置日志
logger = logging.getLogger(__name__)


class WallDefectBackend(LabelStudioMLBase):
    """墙面缺陷自动标注 + MinIO 自动分桶"""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        # 确保 hostname 和 access_token 被设置（从 kwargs 或环境变量或默认值）
        if not self.hostname:
            self.hostname = os.getenv('LABEL_STUDIO_URL', 'https://ls-dev.zdeepcare.com:10443')
        if not self.access_token:
            self.access_token = os.getenv('LABEL_STUDIO_API_KEY', '')

        logger.info(f"ML Backend 配置:")
        logger.info(f"  - Label Studio URL: {self.hostname}")
        logger.info(f"  - API Token 已设置: {'是' if self.access_token else '否'}")

        # 如果 API Token 仍然为空，显示警告
        if not self.access_token:
            logger.warning("⚠️  未设置 LABEL_STUDIO_API_KEY，可能无法获取图片")
            logger.warning("   请设置环境变量: export LABEL_STUDIO_API_KEY='your-token-here'")

        # 1) 初始化统一视觉模型（用你刚才已经跑通的那个）
        provider = os.getenv("VISION_PROVIDER", "doubao")
        model_name = os.getenv("VISION_MODEL", "doubao-1-5-vision-pro-32k-250115")
        self.model = UnifiedVisionModel(model_name=model_name, provider=provider)

        # 2) MinIO 配置，可以先用环境变量，没配就走默认
        self.minio_bucket = os.getenv("MINIO_BUCKET", "wall-defects")
        self.minio_dst_prefix = os.getenv("MINIO_DST_PREFIX", "classified")

        self.minio = Minio(
            os.getenv("MINIO_ENDPOINT", "192.168.0.116:39000"),
            access_key=os.getenv("MINIO_ACCESS_KEY", "minioadmin"),
            secret_key=os.getenv("MINIO_SECRET_KEY", "minioadmin123"),
            secure=False,
        )

        # 实时上传开关（如果遇到认证问题，可以关闭实时上传）
        # ENABLE_REALTIME_UPLOAD=false 会禁用实时上传，改为批量返回
        self.enable_realtime_upload = os.getenv("ENABLE_REALTIME_UPLOAD", "true").lower() == "true"
        
        logger.info("✅ WallDefectBackend 初始化完成")
        logger.info(
            f"模型: provider={provider}, model={model_name}; "
            f"MinIO bucket={self.minio_bucket}, dst_prefix={self.minio_dst_prefix}; "
            f"实时上传: {'启用' if self.enable_realtime_upload else '禁用（批量返回模式）'}"
        )

    # ---------- Label Studio API：实时上传单个预测结果 ----------
    def _upload_prediction_to_labelstudio(self, task_id: int, result: list, score: float):
        """
        将单个任务的预测结果立即上传到 Label Studio
        task_id: 任务 ID
        result: 预测结果列表
        score: 置信度分数
        """
        if not self.hostname or not self.access_token:
            logger.warning("未配置 Label Studio URL 或 API Token，无法实时上传")
            return False
        
        url = f"{self.hostname}/api/predictions/"
        
        # 支持多种 Token 格式
        # Label Studio 1.20.0+ 可能需要不同的 token 格式
        token = self.access_token.strip()
        
        # 如果 token 已经包含 "Token " 前缀，直接使用
        if token.startswith("Token "):
            auth_header = token
        # 否则添加 "Token " 前缀（标准格式）
        else:
            auth_header = f"Token {token}"
        
        headers = {
            "Authorization": auth_header,
            "Content-Type": "application/json"
        }
        
        payload = {
            "task": task_id,
            "result": result,
            "score": score,
            "model_version": "wall_defect_v1"
        }
        
        try:
            response = requests.post(url, json=payload, headers=headers, timeout=10)
            if response.status_code in [200, 201]:
                logger.info(f"✅ 任务 {task_id} 预测结果已实时上传到 Label Studio")
                print(f"✅ 任务 {task_id} 已上传", flush=True)
                return True
            elif response.status_code == 401:
                # 认证失败的特殊处理
                error_detail = response.text
                logger.error(f"❌ 认证失败 [task {task_id}]: {error_detail}")
                print(f"❌ 任务 {task_id} 认证失败 (401)", flush=True)
                print(f"⚠️  错误详情: {error_detail}", flush=True)
                print(f"⚠️  请检查 API Token 是否有效（Label Studio 1.20.0+ 需要新版 token）", flush=True)
                return False
            else:
                logger.error(f"❌ 上传失败 [task {task_id}]: {response.status_code} - {response.text}")
                print(f"❌ 任务 {task_id} 上传失败: {response.status_code}", flush=True)
                return False
        except Exception as e:
            logger.error(f"❌ 上传异常 [task {task_id}]: {e}")
            print(f"❌ 任务 {task_id} 上传异常: {e}", flush=True)
            return False

    # ---------- MinIO 助手：根据类别复制到对应文件夹 ----------
    def _copy_to_class_folder(self, image_url: str, cls_name: str):
        """
        image_url: s3://wall-defects/墙面图片_合并/xxx.jpg
        cls_name : '裂缝' / '起皮掉皮' / '露出基层' / ...
        """
        parsed = urlparse(image_url)
        bucket = parsed.netloc or self.minio_bucket
        key = parsed.path.lstrip("/")  # 桶内真实 key

        filename = Path(key).name
        dst_key = f"{self.minio_dst_prefix}/{cls_name}/{filename}"

        self.minio.copy_object(
            bucket_name=bucket,
            object_name=dst_key,
            source=f"/{bucket}/{key}",
        )
        logger.info(f"MinIO copy: {key} -> {dst_key}")

    # ---------- Label Studio 核心：接任务 → 跑模型 → 回传结果 ----------
    def predict(self, tasks, context=None, **kwargs):
        """
        tasks 形如：
        [
          {
            "id": 123,
            "data": {
              "image": "s3://wall-defects/墙面图片_合并/xxx.jpg"
            },
            ...
          },
          ...
        ]
        context: Label Studio 传递的上下文信息，包含项目配置等
        """
        # 强制输出到标准输出
        print("=" * 80, flush=True)
        print(f"🚨 PREDICT 方法被调用！任务数量: {len(tasks)}", flush=True)
        print(f"Tasks: {tasks}", flush=True)
        print(f"Context: {context}", flush=True)
        print("=" * 80, flush=True)
        
        # 📝 批量大小限制
        # 实时上传模式：支持大批量（默认 10000）
        # 批量返回模式：支持小批量（默认 20）避免超时
        if self.enable_realtime_upload:
            MAX_BATCH_SIZE = int(os.getenv("MAX_BATCH_SIZE", "10000"))
            logger.info(f"🔄 实时上传模式：每处理完一个任务立即上传，批量限制: {MAX_BATCH_SIZE}")
            print(f"🔄 实时上传模式：处理完即上传到 Label Studio", flush=True)
        else:
            MAX_BATCH_SIZE = int(os.getenv("MAX_BATCH_SIZE", "20"))
            logger.info(f"📦 批量返回模式：处理完统一返回，批量限制: {MAX_BATCH_SIZE}")
            print(f"📦 批量返回模式：每次最多处理 {MAX_BATCH_SIZE} 个任务", flush=True)
        
        if len(tasks) > MAX_BATCH_SIZE:
            error_msg = (
                f"❌ 任务数量 ({len(tasks)}) 超过最大批量限制 ({MAX_BATCH_SIZE})！\n"
                f"请分批处理或调整环境变量 MAX_BATCH_SIZE。"
            )
            print("=" * 80, flush=True)
            print(error_msg, flush=True)
            print("=" * 80, flush=True)
            logger.error(error_msg)
            return [{"result": [], "score": 0.0, "error": "批量任务过多，请分批处理"} for _ in tasks]
        
        predictions = []
        
        # 调试信息
        logger.info(f"=" * 60)
        logger.info(f"🔍 收到预测请求，任务数量: {len(tasks)}")
        logger.info(f"Context: {context}")
        
        # 获取项目目录，用于云存储文件下载
        project = context.get('project') if context else None
        print(f"📁 Project: {project}", flush=True)

        for task in tasks:
            print(f"🔄 开始处理任务 {task.get('id')}", flush=True)
            logger.info(f"处理任务: {task.get('id')}")
            image_url = task["data"]["image"]  # <Image name="image" value="$image"/>
            task_id = task.get("id")  # 获取 task ID，用于云存储文件
            print(f"📸 图片 URL: {image_url}", flush=True)
            logger.info(f"图片 URL: {image_url}")
            
            # 处理云存储文件
            try:
                print(f"⚙️ 开始处理图片...", flush=True)
                if image_url.startswith('s3://'):
                    # 直接从 MinIO 下载，不经过 Label Studio
                    print(f"🔹 检测到 S3 URL，准备从 MinIO 下载", flush=True)
                    logger.info(f"🔹 检测到 S3 URL，准备从 MinIO 下载")
                    parsed = urlparse(image_url)
                    bucket = parsed.netloc or self.minio_bucket
                    key = parsed.path.lstrip("/")
                    
                    print(f"📦 Bucket: {bucket}, Key: {key}", flush=True)
                    
                    # 下载到临时目录
                    temp_dir = Path(tempfile.gettempdir()) / "label_studio_ml"
                    temp_dir.mkdir(exist_ok=True)
                    local_path = temp_dir / f"task_{task_id}_{Path(key).name}"
                    
                    print(f"📥 从 MinIO 下载: {bucket}/{key} -> {local_path}", flush=True)
                    logger.info(f"📥 从 MinIO 下载 [task {task_id}]: {bucket}/{key}")
                    self.minio.fget_object(bucket, key, str(local_path))
                    print(f"✅ 下载完成: {local_path}", flush=True)
                    logger.info(f"✅ 下载完成: {local_path}")
                else:
                    print(f"🔹 非 S3 URL，使用 Label Studio 方式获取", flush=True)
                    logger.info(f"🔹 非 S3 URL，使用 Label Studio 方式获取")
                    # 本地文件或 HTTP URL
                    local_path = get_local_path_from_url(
                        image_url,
                        project_dir=project,
                        hostname=self.hostname,
                        access_token=self.access_token,
                        task_id=task_id
                    )
                    logger.info(f"获取图片路径 [task {task_id}]: {image_url} -> {local_path}")
            except Exception as e:
                print(f"❌ 异常发生: {e}", flush=True)
                print(f"❌ 异常类型: {type(e)}", flush=True)
                logger.error(f"❌ 获取图片失败 [task {task_id}, {image_url}]: {e}")
                import traceback
                traceback.print_exc()
                logger.error(traceback.format_exc())
                predictions.append({"result": [], "score": 0.0})
                continue

            # 调你的统一视觉模型
            print(f"🤖 开始调用 AI 模型处理图片: {local_path}", flush=True)
            try:
                out = self.model.process(str(local_path))
                print(f"🤖 模型处理完成，结果: {out}", flush=True)
            except BaseException as e:  # ⬅️ 关键修改：捕获所有错误
                print(f"‼️‼️ 捕获到致命错误 (BaseException) ‼️‼️", flush=True)
                print(f"❌ 导致崩溃的图片是: {local_path}", flush=True)
                print(f"❌ 错误类型: {type(e)}", flush=True)
                print(f"❌ 错误内容: {e}", flush=True)

                import traceback
                traceback.print_exc()
                logger.error(f"‼️ 捕获到致命错误 [task {task_id}]: {e}")
                logger.error(traceback.format_exc())

                predictions.append({"result": [], "score": 0.0})
                continue # 继续处理下一个任务，不要让服务崩溃

            if not out.get("success"):
                print(f"⚠️ 模型返回失败: {out.get('error')}", flush=True)
                logger.warning(f"模型失败: {out.get('error')}")
                predictions.append({"result": [], "score": 0.0})
                continue

            print(f"✅ 模型处理成功！", flush=True)

            # 📋 使用 model_3.py 的字段名
            image_type = out.get("image_type")  # 一级分类
            problem_type = out.get("problem_type")  # 问题类型（墙体缺陷）
            location = out.get("location")  # 具体位置
            material = out.get("material")  # 材质
            environment = out.get("environment")  # 环境位置

            print(f"📊 分类结果 - 一级: {image_type}, 问题类型: {problem_type}", flush=True)
            print(f"🔍 详细字段: location={location}, material={material}, environment={environment}", flush=True)

            score = 0.9  # 没有置信度就先写个固定值
            if isinstance(out.get("confidence"), (int, float)):
                score = float(out["confidence"])

            # === MinIO 自动归档功能已禁用 ===
            # 原因：标注需要人工审核后再归档，避免 MinIO 中产生冗余文件
            # 如需启用，请取消下面代码的注释：
            # try:
            #     cls_for_folder = secondary or image_type or "未分类"
            #     self._copy_to_class_folder(image_url, cls_for_folder)
            # except Exception as e:
            #     logger.warning(f"MinIO 复制失败: {e}")

            # === 组装 Label Studio 需要的 result ===
            result = []

            # ① 一级分类
            if image_type:
                result.append(
                    {
                        "from_name": "v_primary",  # XML 模板中的一级分类
                        "to_name": "v_image",
                        "type": "choices",
                        "value": {"choices": [image_type]},
                    }
                )

            # ② 购物app截图的子标签
            if image_type == "购物app截图":
                sub_label = out.get("sub_label")  # 从 details 中获取
                if sub_label:
                    result.append(
                        {
                            "from_name": "v_sub_app",
                            "to_name": "v_image",
                            "type": "choices",
                            "value": {"choices": [sub_label]},
                        }
                    )

            # ③ 制式图片的子标签
            if image_type == "制式图片":
                sub_label = out.get("sub_label")  # 从 details 中获取
                if sub_label:
                    result.append(
                        {
                            "from_name": "v_sub_std",
                            "to_name": "v_image",
                            "type": "choices",
                            "value": {"choices": [sub_label]},
                        }
                    )

            # ④ 环境属性（仅当一级分类是"环境实拍图"时）
            if image_type == "环境实拍图":
                # 环境位置
                if environment:
                    result.append(
                        {
                            "from_name": "v_env_pos",
                            "to_name": "v_image",
                            "type": "choices",
                            "value": {"choices": [environment]},
                        }
                    )
                # 具体位置
                if location:
                    result.append(
                        {
                            "from_name": "v_env_loc",
                            "to_name": "v_image",
                            "type": "choices",
                            "value": {"choices": [location]},
                        }
                    )
                # 表面材质
                if material:
                    result.append(
                        {
                            "from_name": "v_env_mat",
                            "to_name": "v_image",
                            "type": "choices",
                            "value": {"choices": [material]},
                        }
                    )
                # 问题类型
                if problem_type:
                    result.append(
                        {
                            "from_name": "v_env_prob",
                            "to_name": "v_image",
                            "type": "choices",
                            "value": {"choices": [problem_type]},
                        }
                    )

            # ⑤ 商品信息提取（如果有）
            products = out.get("products", [])
            if products and isinstance(products, list) and len(products) > 0:
                # 添加为备注信息（因为 XML 模板中用 TextArea 展示）
                products_json = json.dumps(products, ensure_ascii=False, indent=2)
                result.append(
                    {
                        "from_name": "v_txt_notes",  # 用于显示商品信息
                        "to_name": "v_image",
                        "type": "textarea",
                        "value": {"text": [products_json]},  # TextArea 需要数组格式
                    }
                )

            # ⑥ AI 推理结果（显示模型的思考过程）
            reasoning = out.get("reasoning", "")
            if reasoning:
                result.append(
                    {
                        "from_name": "v_txt_ai",  # AI 推理结果
                        "to_name": "v_image",
                        "type": "textarea",
                        "value": {"text": [reasoning]},  # TextArea 需要数组格式
                    }
                )

            prediction = {
                "result": result,
                "score": float(score),
            }
            predictions.append(prediction)
            
            # 根据配置决定是否实时上传
            if self.enable_realtime_upload:
                # 实时上传：立即上传到 Label Studio
                upload_success = self._upload_prediction_to_labelstudio(task_id, result, float(score))
                
                if upload_success:
                    print(f"✅ 任务 {task_id} 处理完成，生成 {len(result)} 个标注并已上传", flush=True)
                else:
                    print(f"⚠️  任务 {task_id} 处理完成，生成 {len(result)} 个标注但上传失败", flush=True)
            else:
                # 批量返回模式：不实时上传，最后一起返回
                print(f"✅ 任务 {task_id} 处理完成，生成 {len(result)} 个标注", flush=True)

        print(f"🎯 所有任务处理完成，共生成 {len(predictions)} 个预测结果", flush=True)

        # 计算返回数据大小（用于调试）
        import sys
        predictions_json = json.dumps(predictions)
        data_size_mb = sys.getsizeof(predictions_json) / (1024 * 1024)
        
        print(f"📦 返回数据大小: {data_size_mb:.2f} MB", flush=True)
        print(f"📤 返回结果示例 (前2个): {predictions[:2]}", flush=True)
        
        if self.enable_realtime_upload:
            logger.info(f"📊 实时上传模式：已处理 {len(predictions)} 个任务，所有结果已实时上传到 Label Studio")
            print(f"✅ 所有 {len(predictions)} 个任务的预测结果已实时上传到 Label Studio", flush=True)
            print(f"💡 提示：刷新 Label Studio 页面即可看到预测结果", flush=True)
            # 实时上传模式：返回空列表，避免重复创建预测
            # 因为结果已经通过 API 上传了
            return []
        else:
            logger.info(f"📊 批量返回模式：已处理 {len(predictions)} 个任务，将通过返回值提交到 Label Studio")
            print(f"✅ 所有 {len(predictions)} 个任务的预测结果将返回给 Label Studio", flush=True)
            # 批量返回模式：返回完整结果，由 Label Studio 创建预测
            return predictions

    def fit(self, tasks, workdir=None, **kwargs):
        """
        训练接口 - 由于使用预训练模型，这里只返回成功状态
        """
        logger.info(f"收到训练请求，共 {len(tasks) if tasks else 0} 个标注任务，使用预训练模型无需训练")
        return {
            'train_output': {
                'status': 'success',
                'message': '使用预训练模型',
                'tasks_count': len(tasks) if tasks else 0
            }
        }


# Flask app 入口（一定要有这个）
# 设置 model_dir 用于存储训练任务的临时文件
app = init_app(
    WallDefectBackend, 
    model_dir=os.getenv('MODEL_DIR', os.path.dirname(__file__))
)
