from typing import Any, Dict, List, Optional
import os
import json
import base64
import requests
import re
import sys
import logging
import time
from pathlib import Path
from PIL import Image
import io

# 添加项目根目录到路径 (根据你的项目结构保留)
project_root = Path(__file__).parent.parent.parent.parent.parent
sys.path.insert(0, str(project_root))

class UnifiedVisionModel:
    """
    统一视觉模型 (V3.0 Final)
    
    功能特性：
    1. 完美适配 XML Prompt 的5大分类体系。
    2. 双路信息提取引擎：
       - 路径A：[环境实拍图] -> 强制提取 4维属性 (环境/位置/材质/问题)。
       - 路径B：[购物截图] OR [商品实拍] -> 智能提取 products 列表。
    3. 鲁棒的 JSON 解析与后处理。
    """
    
    # 5个一级分类 (与 Prompt 严格一致)
    PRIMARY_LABELS = [
        '商品/包裹实拍图', 
        '购物app截图', 
        '制式图片', 
        '环境实拍图', 
        '其他'
    ]
    
    # 环境属性的键名映射
    ENV_ATTR_KEYS = ['environment', 'location', 'material', 'problem_type']
    
    def __init__(self, config: dict = None, model_name: str = None, provider: str = None):
        """
        兼容多种初始化方式

        方式1 (新): UnifiedVisionModel(config={...})
        方式2 (旧): UnifiedVisionModel(model_name="...", provider="...")
        """
        self.config = config or {}
        self.logger = logging.getLogger(__name__)
        # 设置日志级别，方便调试
        logging.basicConfig(level=logging.INFO)

        self.model_dir = Path(__file__).parent

        # 1. 获取 API Key
        self.api_key = os.getenv('ARK_API_KEY')
        if not self.api_key:
            # 为了防止运行报错，这里打印警告，实际运行时请确保环境变量已设置
            self.logger.warning("⚠️ 未检测到 ARK_API_KEY 环境变量，请确保已设置！")

        # 2. 获取模型配置 (兼容新旧两种方式)
        params = self.config.get('parameters', {})

        # 优先使用直接参数，其次使用 config 中的参数
        self.model_name = model_name or params.get('model_name', 'doubao-1-5-vision-pro-32k-250115')
        self.base_url = params.get('base_url', 'https://ark.cn-beijing.volces.com/api/v3')
        self.max_tokens = params.get('max_tokens', 2048) # 调大Token数以容纳复杂的JSON
        self.temperature = params.get('temperature', 0) # 低温采样，保证JSON格式稳定

        # provider 参数暂不使用，保留用于扩展
        self.provider = provider

        # 3. 加载提示词
        self._load_prompt()

        self.logger.info(f"统一视觉模型初始化完成，使用模型: {self.model_name}")

    def _load_prompt(self):
        """加载 prompt_2.0_xml.txt"""
        prompt_path = self.model_dir / 'prompt_2.0_xml.txt'
        if prompt_path.exists():
            self.prompt_template = prompt_path.read_text(encoding='utf-8')
            self.logger.info(f"✅ 提示词已加载: {len(self.prompt_template)} 字符")
        else:
            self.logger.error(f"❌ 提示词文件缺失: {prompt_path}")
            # 这是一个阻塞性错误，如果没有提示词，模型无法工作
            self.prompt_template = "" 

    async def _preprocess(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """图像预处理：尺寸压缩 + Base64编码"""
        binary_content = input_data.get('binary_content', b'')
        if not binary_content:
            raise ValueError("Input binary_content is empty")
            
        # 如果传入的是 base64 字符串，先解码
        if isinstance(binary_content, str):
            try:
                binary_content = base64.b64decode(binary_content)
            except:
                pass # 可能是 raw string，继续尝试
        
        try:
            image = Image.open(io.BytesIO(binary_content))
            
            # 尺寸控制：长边不超过 1536 (根据Doubao Vision的最佳实践调整)
            max_size = 1536
            if image.width > max_size or image.height > max_size:
                image.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)
            
            # 转 RGB (去除 Alpha 通道)
            if image.mode != 'RGB':
                image = image.convert('RGB')
                
            buffer = io.BytesIO()
            # 稍微降低质量以减少传输体积，JPEG quality 85 视觉损失极小
            image.save(buffer, format='JPEG', quality=85)
            image_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
            
            return {'image_base64': image_base64}
            
        except Exception as e:
            self.logger.error(f"预处理失败: {e}")
            # 兜底：如果图片损坏，尝试直接透传原始数据的base64
            if isinstance(binary_content, bytes):
                return {'image_base64': base64.b64encode(binary_content).decode('utf-8')}
            raise e

    async def _inference(self, preprocessed_data: Dict[str, Any]) -> Dict[str, Any]:
        """执行 API 调用"""
        if not self.prompt_template:
            return {"success": False, "error": "提示词模版未加载"}

        image_base64 = preprocessed_data['image_base64']
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        data = {
            "model": self.model_name,
            "messages": [{
                "role": "user",
                "content": [
                    {"type": "text", "text": self.prompt_template},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_base64}"}}
                ]
            }],
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
            # 关键：强制模型输出 JSON Object
            "response_format": {"type": "json_object"}
        }
        
        try:
            # 使用 requests (同步库)，在 async 函数中通常建议用 aiohttp，这里为了保持代码依赖简单沿用 requests
            # 实际生产中建议放入 thread pool
            response = requests.post(
                f"{self.base_url}/chat/completions", 
                headers=headers, 
                json=data, 
                timeout=60
            )
            
            if response.status_code != 200:
                return {
                    "success": False, 
                    "error": f"API Error {response.status_code}", 
                    "raw_response": response.text
                }
            
            result_json = response.json()
            content = result_json["choices"][0]["message"]["content"]

            # 调试：打印原始返回内容
            self.logger.info(f"📥 模型原始返回 (前500字符): {content[:500]}...")

            return self._parse_response(content)
            
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _parse_response(self, content: str) -> Dict[str, Any]:
        """解析 LLM 返回的 JSON 内容"""
        try:
            # 清洗 markdown 标记 (```json ... ```)
            content = re.sub(r'^```json\s*', '', content, flags=re.MULTILINE)
            content = re.sub(r'\s*```$', '', content, flags=re.MULTILINE)
            content = content.strip()
            
            parsed = json.loads(content)
        except json.JSONDecodeError:
            self.logger.error(f"JSON解析失败，原始内容: {content[:100]}...")
            return {
                "success": False, 
                "error": "Invalid JSON format", 
                "raw_content": content
            }
        
        # 提取字段
        primary_category = parsed.get("primary_category", "其他")
        sub_label = parsed.get("sub_label")
        env_attrs = parsed.get("environment_attributes")
        products = parsed.get("products", [])
        thinking = parsed.get("thinking", "")

        # 调试：打印解析后的关键字段
        self.logger.info(f"🔍 解析结果: category={primary_category}, sub_label={sub_label}, products_count={len(products) if products else 0}")

        # 构造标准化输出结构
        result = {
            "success": True,
            "category": primary_category,
            "thinking": thinking,
            "details": {}
        }
        
        # 逻辑分支 1: 填充环境属性
        if primary_category == "环境实拍图" and env_attrs:
            for key in self.ENV_ATTR_KEYS:
                result["details"][key] = env_attrs.get(key, "其他")
        
        # 逻辑分支 2: 填充子标签 (App截图/制式图)
        if sub_label:
            result["details"]["sub_label"] = sub_label
            
        # 逻辑分支 3: 填充商品信息 (任何分类下，只要提取到了就返回)
        # 这就是我们讨论的重点：实物图也能返回 products
        if products and isinstance(products, list) and len(products) > 0:
            result["details"]["products"] = products
            
        return result

    async def _postprocess(self, raw_output: Dict[str, Any]) -> Dict[str, Any]:
        """将结构化数据转换为人类可读的各种格式"""
        if not raw_output.get("success"):
            return {
                "result": f"识别失败: {raw_output.get('error')}",
                "status_code": 1,
                "debug_info": raw_output
            }
            
        category = raw_output["category"]
        details = raw_output["details"]
        thinking = raw_output.get("thinking", "")
        
        # 1. 构建简报文本 (Summary)
        summary_lines = [f"【图像分类】: {category}"]
        
        # 补充环境信息
        if category == "环境实拍图":
            env = details.get('environment', '-')
            loc = details.get('location', '-')
            mat = details.get('material', '-')
            prob = details.get('problem_type', '-')
            summary_lines.append(f"【缺陷诊断】: 在{env}的{loc}发现{mat}材质存在[{prob}]问题。")
            
        # 补充子标签
        if "sub_label" in details:
            summary_lines.append(f"【页面类型】: {details['sub_label']}")
            
        # 补充商品信息
        products = details.get("products", [])
        if products:
            p_names = [p.get('product_name', '未知商品') for p in products[:2]] # 只列前两个
            count_str = f"等{len(products)}个商品" if len(products) > 2 else ""
            summary_lines.append(f"【商品提取】: 发现 {', '.join(p_names)} {count_str}")

        # 2. 返回完整包
        return {
            "result": "\n".join(summary_lines), # 简报
            "confidence": 0.95, # 占位符
            "status_code": 0,
            "category": category, # 一级分类（重要！）
            "details": details, # 核心结构化数据
            "thinking_process": thinking # 思维链，用于调试
        }

    async def __call__(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """入口函数"""
        try:
            # 1. Preprocess
            pre_data = await self._preprocess(input_data)

            # 2. Inference
            raw_result = await self._inference(pre_data)

            # 3. Postprocess
            final_result = await self._postprocess(raw_result)

            return final_result

        except Exception as e:
            self.logger.exception("UnifiedVisionModel 执行异常")
            return {
                "result": "系统内部错误",
                "status_code": 500,
                "error_message": str(e)
            }

    def process(self, image_path: str) -> Dict[str, Any]:
        """
        同步处理图片的入口方法（兼容旧版本调用）

        Args:
            image_path: 图片路径

        Returns:
            处理结果字典，包含 success, image_type, products 等字段
        """
        import asyncio

        # 读取图片
        with open(image_path, "rb") as f:
            binary_content = f.read()

        # 调用异步方法
        result = asyncio.run(self({"binary_content": binary_content}))

        # 转换为旧版本兼容格式
        if result.get("status_code") == 0:
            # 成功
            details = result.get("details", {})
            category = result.get("category", "其他")  # 直接从 result 中获取一级分类

            # 🔍 调试输出
            self.logger.info(f"✅ [DEBUG] result.get('category') = {repr(result.get('category'))}")
            self.logger.info(f"✅ [DEBUG] result.get('result') = {repr(result.get('result')[:100])}")
            self.logger.info(f"✅ [DEBUG] 最终 image_type = {repr(category)}")

            # 构造旧版本格式的返回值
            return {
                "success": True,
                "image_type": category,  # 一级分类
                "products": details.get("products", []),
                # 子标签（统一使用 sub_label）
                "sub_label": details.get("sub_label"),
                # 环境实拍图的特殊字段
                "environment": details.get("environment"),
                "location": details.get("location"),
                "material": details.get("material"),
                "problem_type": details.get("problem_type"),
                # 思维过程
                "reasoning": result.get("thinking_process", "")
            }
        else:
            # 失败
            return {
                "success": False,
                "error": result.get("error_message", result.get("result", "未知错误")),
                "image_path": image_path
            }

    def predict_image(self, image_path: str):
        """
        给 Label Studio ML Backend 用的统一接口：
        输入：图片本地路径
        输出：
        cls_name: 墙面缺陷一级类别（从 problem_type 映射）
        extra_tags: 其他多维标签字典，key 要和 Label Studio 模板里的 name 对齐
        """
        import asyncio

        # 读取图片
        with open(image_path, "rb") as f:
            binary_content = f.read()

        # 调用异步方法
        result = asyncio.run(self({"binary_content": binary_content}))

        # 默认值
        cls_name = "全部未分类"
        extra_tags = {}

        if not result.get("success") or result.get("status_code") != 0:
            # 失败时返回错误信息
            extra_tags["reasoning"] = result.get("error_message", result.get("result", "模型推理失败"))
            return cls_name, extra_tags

        category = result.get("details", {}).get("category", "")
        details = result.get("details", {})

        # 只处理"环境实拍图"
        if category == "环境实拍图":
            # 使用 problem_type 作为 cls_name
            problem_type = details.get("problem_type", "全部未分类")

            # 映射 problem_type 到旧格式的二级标签
            problem_mapping = {
                "掉皮&起皮": "起皮掉皮",
                "开裂&孔洞": "裂缝",
                "污渍&涂鸦": "涂鸦&污渍",
                # 其他直接使用
            }
            cls_name = problem_mapping.get(problem_type, problem_type)

            # 提取环境属性
            # 新格式：environment, location, material, problem_type
            # 旧格式需要：environment, surface_position, surface_material, defect_color, wet_area, water_leak, reasoning

            extra_tags["environment"] = details.get("environment", "")
            extra_tags["surface_position"] = details.get("location", "")  # location -> surface_position
            extra_tags["surface_material"] = details.get("material", "")
            # problem_type 作为 cls_name 已处理
            extra_tags["reasoning"] = details.get("reasoning", result.get("thinking_process", ""))
        else:
            # 非环境实拍图，归为"全部未分类"
            cls_name = "全部未分类"
            extra_tags["reasoning"] = f"非环境实拍图，类别: {category}"

        return cls_name, extra_tags

    def _load_images_from_dir(
        self,
        image_dir: str,
        max_count: int = None,
        seed: int = None,
        extensions: tuple = ('.jpg', '.jpeg', '.png', '.jfif', '.gif', '.webp')
    ) -> List[Path]:
        """
        从目录加载图片文件列表

        Args:
            image_dir: 图片目录路径
            max_count: 最大返回数量，None 表示返回所有
            seed: 随机种子，用于固定采样结果
            extensions: 支持的图片扩展名

        Returns:
            图片文件路径列表
        """
        dir_path = Path(image_dir)
        if not dir_path.exists():
            self.logger.error(f"❌ 目录不存在: {image_dir}")
            return []

        # 收集所有图片
        images = []
        for ext in extensions:
            images.extend(dir_path.glob(f'*{ext}'))
            images.extend(dir_path.glob(f'*{ext.upper()}'))

        # 排序确保顺序一致
        images = sorted(images)

        if seed is not None:
            # 设置随机种子进行采样
            import random
            random.seed(seed)
            if max_count is not None and max_count < len(images):
                sampled = random.sample(images, max_count)
                self.logger.info(f"📁 从 {image_dir} 找到 {len(images)} 张图片，使用种子 {seed} 随机采样 {max_count} 张")
                return sorted(sampled)  # 再次排序保持稳定顺序

        if max_count is not None:
            images = images[:max_count]

        self.logger.info(f"📁 从 {image_dir} 加载 {len(images)} 张图片")
        return images

    async def batch_process(
        self,
        image_dir: str,
        max_count: int = None,
        seed: int = 123,
        output_file: str = None
    ) -> List[Dict]:
        """
        批量处理目录中的图片

        Args:
            image_dir: 图片目录路径
            max_count: 最大处理数量，None 表示处理所有
            seed: 随机种子，用于固定采样结果（默认42）
            output_file: 结果输出文件路径（JSON格式），None 表示不保存

        Returns:
            处理结果列表
        """
        # 1. 加载图片列表（带随机种子）
        images = self._load_images_from_dir(image_dir, max_count=max_count, seed=seed)

        if not images:
            self.logger.warning("⚠️ 未找到任何图片")
            return []

        # 3. 批量处理
        results = []
        total = len(images)
        success_count = 0
        fail_count = 0

        print(f"\n{'='*60}")
        print(f"🚀 开始批量处理 {total} 张图片")
        print(f"{'='*60}\n")

        for idx, img_path in enumerate(images, 1):
            print(f"[{idx}/{total}] 处理: {img_path.name}...")

            try:
                # 读取图片
                with open(img_path, "rb") as f:
                    binary_content = f.read()

                # 推理
                start_time = time.time()
                result = await self({"binary_content": binary_content})
                cost_time = time.time() - start_time

                # 记录结果
                record = {
                    "image_name": img_path.name,
                    "image_path": str(img_path),
                    "result": result.get("result"),
                    "status_code": result.get("status_code"),
                    "details": result.get("details"),
                    "thinking": result.get("thinking_process"),
                    "cost_time": round(cost_time, 2),
                    "success": result.get("status_code") == 0
                }

                results.append(record)

                if record["success"]:
                    success_count += 1
                    print(f"  ✅ 成功 ({cost_time:.2f}s) - {result.get('result', '')[:50]}...")
                else:
                    fail_count += 1
                    print(f"  ❌ 失败 - {result.get('error_message', result.get('result', 'Unknown error'))}")

            except Exception as e:
                fail_count += 1
                self.logger.error(f"  ❌ 处理异常: {e}")
                results.append({
                    "image_name": img_path.name,
                    "image_path": str(img_path),
                    "success": False,
                    "error": str(e)
                })

            # 每10张打印一次进度
            if idx % 10 == 0:
                print(f"\n📊 当前进度: 成功 {success_count} | 失败 {fail_count} | 剩余 {total - idx}\n")

        # 4. 打印统计
        print(f"\n{'='*60}")
        print(f"✅ 批量处理完成!")
        print(f"{'='*60}")
        print(f"总计: {total} 张")
        print(f"成功: {success_count} 张 ({success_count/total*100:.1f}%)")
        print(f"失败: {fail_count} 张 ({fail_count/total*100:.1f}%)")

        if results:
            total_time = sum(r.get("cost_time", 0) for r in results if "cost_time" in r)
            avg_time = total_time / len(results) if results else 0
            print(f"总耗时: {total_time:.2f}s, 平均: {avg_time:.2f}s/张")
        print(f"{'='*60}\n")

        # 5. 保存结果
        if output_file:
            output_path = Path(output_file)
            output_path.parent.mkdir(parents=True, exist_ok=True)

            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump({
                    "summary": {
                        "total": total,
                        "success": success_count,
                        "failed": fail_count,
                        "success_rate": f"{success_count/total*100:.1f}%" if total > 0 else "0%"
                    },
                    "results": results
                }, f, ensure_ascii=False, indent=2)

            print(f"💾 结果已保存到: {output_path}\n")

        return results


# ==========================================
# 单元测试模块
# ==========================================
if __name__ == "__main__":
    import asyncio

    # 模拟简单的测试环境
    async def run_single_test():
        """单张图片测试"""
        print("🚀 开始测试 UnifiedVisionModel (New)...")

        # 1. 检查 Prompt 文件
        p_path = Path(__file__).parent / 'prompts' / 'prompt_2.0_xml.txt'
        if not p_path.exists():
            print(f"❌ 错误：请先创建 {p_path}")
            return

        # 2. 加载图片数据
        img_path = "/Users/liujiaojiao/Documents/new_prompt/images_wall/商品分类选项/O1CN01ae2KZo25kpKZe9s4t_!!4611686018427381821-0-amp.jpg"

        with open(img_path, "rb") as f:
            binary_content = f.read()

        # 3. 初始化并运行
        if not os.getenv('ARK_API_KEY'):
             print("⚠️ 警告：未设置 ARK_API_KEY，API调用将失败")

        model = UnifiedVisionModel()
        input_data = {"binary_content": binary_content}

        start = time.time()
        result = await model(input_data)
        cost = time.time() - start

        # 4. 打印结果
        print(f"\n✅ 执行完成 (耗时 {cost:.2f}s)")
        print("="*50)
        print("🤖 Human Readable Result:")
        print(result.get('result'))
        print("-" * 30)
        print("📦 Structured Details (JSON):")
        print(json.dumps(result.get('details'), ensure_ascii=False, indent=2))
        print("="*50)

    async def run_batch_test():
        """批量图片测试"""
        print("🚀 批量测试模式\n")

        # 检查 API Key
        if not os.getenv('ARK_API_KEY'):
            print("⚠️ 警告：未设置 ARK_API_KEY，API调用将失败")
            print("   请运行: export ARK_API_KEY='your_key'\n")

        # 初始化模型
        model = UnifiedVisionModel()

        # 批量处理测试数据集
        test_dataset = Path(__file__).parent / "test_dataset_v2"
        output_file = Path(__file__).parent / "results" / f"batch_results_{int(time.time())}.json"

        # 处理指定数量的图片 (None 表示处理所有)
        results = await model.batch_process(
            image_dir=str(test_dataset),
            max_count=10,  # 修改这里指定处理数量
            seed=123,        # 修改这里指定随机种子
            output_file=str(output_file)
        )

        # 按类别统计
        if results:
            categories = {}
            for r in results:
                if r.get("success"):
                    cat = r.get("details", {}).get("category", "未知")
                    categories[cat] = categories.get(cat, 0) + 1

            print("\n📊 分类统计:")
            for cat, count in sorted(categories.items(), key=lambda x: x[1], reverse=True):
                print(f"  {cat}: {count}")

    # 选择运行模式
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "batch":
        asyncio.run(run_batch_test())
    else:
        asyncio.run(run_single_test())