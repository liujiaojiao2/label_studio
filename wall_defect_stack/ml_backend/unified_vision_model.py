#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
统一视觉模型
基于 model.py 架构，整合 unified_image_processor 的统一提示词
支持一级分类、二级标签识别（墙面缺陷/商品信息提取）
"""

import os
import json
import base64
import time
import requests
from typing import Any, Dict, Optional, List
from pathlib import Path
from PIL import Image
import io
 

class UnifiedVisionModel:
    """
    统一视觉模型
    整合电商图片分类、墙面缺陷识别、商品信息提取功能
    """
    
    # 23个一级电商标签
    PRIMARY_LABELS = [
        '商品分类选项', '商品头图', '商品详情页截图', '下单过程中出现异常（显示购买失败浮窗）',
        '订单详情页面', '支付页面', '评论区截图页面', '物流页面-物流列表页面',
        '物流页面-物流跟踪页面', '物流页面-物流异常页面', '退款页面', '退货页面',
        '换货页面', '购物车页面', '店铺页面', '活动页面', '优惠券领取页面',
        '账单/账户页面', '投诉举报页面', '实物拍摄(含售后)', '外部APP截图',
        '平台介入页面', '其他类别图片'
    ]
    
    # 需要提取商品信息的类别
    PRODUCT_EXTRACTION_LABELS = {
        '商品分类选项', '商品详情页截图', '商品头图', '购物车页面', '订单详情页面'
    }
    
    # 墙面缺陷标签
    WALL_DEFECT_LABEL = '实物拍摄(含售后)'
    WALL_DEFECT_SUBLABELS = ['孔洞', '裂缝', '露出基层', '起皮掉皮', '涂鸦&污渍', '全部未分类']
    
    # 墙面属性标签（与 Prompt 中的字段名保持一致）
    # WALL_ATTRIBUTES = [
    #     'environment', 'surface_position', 'surface_material', 'defect_area', 
    #     'defect_color', 'wet_area', 'water_leak', 'reasoning'
    # ]
    WALL_ATTRIBUTES = [
        'environment', 'surface_position', 'surface_material', 
        'defect_color', 'wet_area', 'water_leak', 'reasoning'
    ]
    def __init__(self, model_name: str = "doubao-1-5-vision-pro-32k-250115", 
                 provider: str = "doubao"):
        """
        初始化统一视觉模型
        
        Args:
            model_name: 使用的视觉模型名称
            provider: API提供商，支持 "doubao" 或 "openrouter"
        """
        self.model_name = model_name
        self.provider = provider.lower()
        self.debug_mode = os.getenv('DEBUG_API', '').lower() in ('1', 'true', 'yes')
        
        # 根据提供商选择 API 配置
        if self.provider == "openrouter":
            self.api_key = os.getenv('OPENROUTER_API_KEY')
            if not self.api_key:
                raise ValueError("请设置环境变量 OPENROUTER_API_KEY")
            self.base_url = "https://openrouter.ai/api/v1"
            # OpenRouter 使用标准的模型名称格式
            if model_name == "doubao-1-5-vision-pro-32k-250115":
                # 如果用户没指定，默认使用 GPT-4o
                self.model_name = "openai/gpt-4o"
        else:  # doubao
            self.api_key = os.getenv('ARK_API_KEY')
            if not self.api_key:
                raise ValueError("请设置环境变量 ARK_API_KEY")
            self.base_url = "https://ark.cn-beijing.volces.com/api/v3"
        
        print(f"✅ 统一视觉模型初始化成功")
        print(f"   提供商: {self.provider}")
        print(f"   模型: {self.model_name}")
        print(f"   调试模式: {'开启' if self.debug_mode else '关闭'}")
    
    def preprocess(self, image_path: str) -> Dict[str, Any]:
        """
        预处理：加载并编码图片
        
        Args:
            image_path: 图片路径
            
        Returns:
            包含 image_base64 和元数据的字典
        """
        try:
            with Image.open(image_path) as img:
                # 调整尺寸
                max_size = 1024
                if img.width > max_size or img.height > max_size:
                    img.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)
                
                # 转换为RGB
                if img.mode != 'RGB':
                    img = img.convert('RGB')
                
                # 编码为base64
                buffer = io.BytesIO()
                img.save(buffer, format='JPEG', quality=85)
                image_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
                
                return {
                    'success': True,
                    'image_base64': image_base64,
                    'image_path': str(image_path),
                    'original_size': (img.width, img.height)
                }
        
        except Exception as e:
            return {
                'success': False,
                'error': f"图片预处理失败: {str(e)}",
                'image_path': str(image_path)
            }
    
    def build_unified_prompt(self) -> str:
        """
        构建统一提示词模板
        
        Returns:
            完整的提示词字符串
        """
        primary_labels_text = "\n".join([f"{i+1}. {label}" for i, label in enumerate(self.PRIMARY_LABELS)])
        wall_labels_text = "\n".join([f"  {i+1}. {label}" for i, label in enumerate(self.WALL_DEFECT_SUBLABELS)])
        product_labels_text = "\n".join([f"  - {label}" for label in sorted(self.PRODUCT_EXTRACTION_LABELS)])
        
        prompt = f""" b vv g："""
        
        return prompt
    
    def call_api(self, image_base64: str, prompt: str, max_tokens: int = 4096, 
                 temperature: float = 0.2) -> Dict[str, Any]:
        """
        调用视觉API
        
        Args:
            image_base64: Base64编码的图片
            prompt: 提示词
            max_tokens: 最大token数
            temperature: 温度参数
            
        Returns:
            API响应结果
        """
        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            # OpenRouter 需要额外的 headers
            if self.provider == "openrouter":
                headers["HTTP-Referer"] = "https://github.com/your-repo"  # 可选，用于统计
                headers["X-Title"] = "Wall Defect Detection"  # 可选，显示在 OpenRouter 面板
            
            data = {
                "model": self.model_name,
                "messages": [{
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:image/jpeg;base64,{image_base64}"}
                        }
                    ]
                }],
                "max_tokens": max_tokens,
                "temperature": temperature
            }
            
            if self.debug_mode:
                print(f"    → API请求 ({self.provider})...", flush=True)
            
            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=data,
                timeout=120  # OpenRouter 可能需要更长时间
            )
            
            if response.status_code != 200:
                error_detail = response.text[:500]
                if self.debug_mode:
                    print("API 详细信息：", error_detail)
                return {
                    "success": False,
                    "error": f"API调用失败: {response.status_code}",
                    "response_text": error_detail
                }
            
            result = response.json()
            content = result["choices"][0]["message"]["content"].strip()
            finish_reason = result["choices"][0].get("finish_reason", "unknown")
            
            if self.debug_mode:
                print(f"    → API返回完整内容（长度: {len(content)} 字符，结束原因: {finish_reason}）：", flush=True)
                print(content, flush=True)
                print("=" * 80, flush=True)
                
                # 保存原始响应到文件用于调试
                with open('debug_api_response.txt', 'w', encoding='utf-8') as f:
                    f.write(content)
                    f.write(f"\n\n[finish_reason: {finish_reason}]")
            
            return {
                "success": True,
                "content": content
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"API调用异常: {str(e)}"
            }
    
    def parse_response(self, content: str) -> Dict[str, Any]:
        """
        解析API响应的JSON内容
        
        Args:
            content: API返回的文本内容
            
        Returns:
            解析后的结果字典
        """
        # 尝试解析JSON
        parsed = None
        raw_content = content

        # 1) 先去掉可能的 Markdown 代码块包裹（例如 ```json ... ```）
        content_stripped = raw_content.strip()
        if content_stripped.startswith("```"):
            if self.debug_mode:
                print(f"    → 检测到 Markdown 代码块，开始去除", flush=True)
            lines = content_stripped.splitlines()
            # 去掉第一行 ``` 或 ```json
            if lines and lines[0].startswith("```"):
                lines = lines[1:]
            # 去掉最后一行 ```（如果有）
            if lines and lines[-1].strip().startswith("```"):
                lines = lines[:-1]
            content_stripped = "\n".join(lines).strip()
            if self.debug_mode:
                print(f"    → 去除后内容: {content_stripped[:200]}...", flush=True)
        else:
            content_stripped = raw_content

        # 2) 直接解析去掉代码块后的内容
        parsed = None
        try:
            parsed = json.loads(content_stripped)
            if self.debug_mode:
                print(f"    → JSON 解析成功", flush=True)
        except json.JSONDecodeError as e:
            if self.debug_mode:
                print(f"    → JSON 解析失败: {str(e)}", flush=True)
                print(f"    → 尝试修复不完整的 JSON...", flush=True)
            
            # 3) 尝试修复不完整的 JSON（补全缺失的引号和括号）
            import re
            fixed_content = content_stripped
            
            # 如果最后一个字段的值没有闭合引号，补上
            if re.search(r':\s*"[^"]*$', fixed_content):
                fixed_content += '"'
                if self.debug_mode:
                    print(f"    → 补充了缺失的引号", flush=True)
            
            # 如果缺少闭合大括号，补上
            open_braces = fixed_content.count('{')
            close_braces = fixed_content.count('}')
            if open_braces > close_braces:
                fixed_content += '\n}' * (open_braces - close_braces)
                if self.debug_mode:
                    print(f"    → 补充了 {open_braces - close_braces} 个闭合括号", flush=True)
            
            try:
                parsed = json.loads(fixed_content)
                if self.debug_mode:
                    print(f"    → 修复后解析成功", flush=True)
            except json.JSONDecodeError:
                # 4) 如果修复后还失败，尝试从原始内容中提取第一个 {...} 片段
                match = re.search(r"\{[\s\S]*\}", raw_content)
                if match:
                    if self.debug_mode:
                        print(f"    → 尝试正则提取 JSON...", flush=True)
                    try:
                        parsed = json.loads(match.group())
                        if self.debug_mode:
                            print(f"    → 正则提取成功", flush=True)
                    except json.JSONDecodeError as e2:
                        if self.debug_mode:
                            print(f"    → 正则提取后仍失败: {str(e2)}", flush=True)
                        parsed = None
        
        if not isinstance(parsed, dict):
            if self.debug_mode:
                print(f"    → 解析结果不是字典类型，返回错误", flush=True)
            return {
                "success": False,
                "error": "无法解析模型输出为JSON",
                "raw_content": content[:500] if len(content) > 500 else content
            }
        
        # 优先获取image_type，如果没有则从primary_label获取（兼容旧格式）
        image_type = parsed.get("image_type", "")
        if not image_type:
            # 兼容旧格式：从primary_label获取
            image_type = parsed.get("primary_label", "")
        
        # 验证image_type
        if image_type not in self.PRIMARY_LABELS:
            # 尝试模糊匹配
            matched = False
            for label in self.PRIMARY_LABELS:
                if label in image_type or image_type in label:
                    image_type = label
                    matched = True
                    break
            if not matched:
                return {
                    "success": False,
                    "error": f"image_type无效: {image_type}",
                    "raw_content": content
                }
        
        result = {
            "success": True,
            "image_type": image_type,
            "raw_content": content
        }
        
        # 处理墙面缺陷识别结果
        if image_type == self.WALL_DEFECT_LABEL and "secondary_label" in parsed:
            secondary_label = parsed["secondary_label"]
            if secondary_label in self.WALL_DEFECT_SUBLABELS:
                result["secondary_label"] = secondary_label
                result["secondary_confidence"] = parsed.get("confidence", "unknown")
            
            # 提取墙面属性（只保留有实际判断的值，不要"无法判断"或空值）
            for attr in self.WALL_ATTRIBUTES:
                if attr in parsed:
                    value = parsed[attr]
                    # 不允许"无法判断"，也不保留纯空白
                    if isinstance(value, str) and value.strip() and value.strip() != "无法判断":
                        result[attr] = value
        
        # 处理商品信息提取结果（统一products数组结构）
        if image_type in self.PRODUCT_EXTRACTION_LABELS:
            # 统一提取products数组结构
            result["products"] = parsed.get("products", [])
            
            # 兼容旧格式：如果API返回的是旧格式，尝试转换
            if not result["products"]:
                # 尝试从旧格式转换
                products = []
                
                # 商品头图旧格式
                if image_type == "商品头图" and "product_name" in parsed:
                    products.append({
                        "product_name": parsed.get("product_name", ""),
                        "sku": "",
                        "quantity": 1,
                        "price_original": parsed.get("price_before", "").replace("¥", "").replace("￥", ""),
                        "price_current": parsed.get("price_after", "").replace("¥", "").replace("￥", ""),
                        "price_discount": "",
                        "shop_name": "",
                        "image_description": "",
                        "features": parsed.get("features", ""),
                        "usage_scenario": parsed.get("usage_scenarios", ""),
                        "gifts": parsed.get("gifts", ""),
                        "order_status": "",
                        "order_number": "",
                        "logistics_status": ""
                    })
                
                # 商品详情页旧格式
                elif image_type == "商品详情页截图" and "product_name" in parsed:
                    products.append({
                        "product_name": parsed.get("product_name", ""),
                        "sku": "",
                        "quantity": 1,
                        "price_original": parsed.get("price_before", "").replace("¥", "").replace("￥", ""),
                        "price_current": parsed.get("price_after", "").replace("¥", "").replace("￥", ""),
                        "price_discount": "",
                        "shop_name": "",
                        "image_description": parsed.get("main_image_description", ""),
                        "features": parsed.get("features", ""),
                        "usage_scenario": "",
                        "gifts": "",
                        "order_status": "",
                        "order_number": "",
                        "logistics_status": ""
                    })
                
                # 商品分类选项旧格式
                elif image_type == "商品分类选项" and "product_name" in parsed:
                    products.append({
                        "product_name": parsed.get("product_name", ""),
                        "sku": parsed.get("specification", ""),
                        "quantity": int(parsed.get("quantity", "1")) if parsed.get("quantity", "").isdigit() else 1,
                        "price_original": "",
                        "price_current": parsed.get("price", "").replace("¥", "").replace("￥", ""),
                        "price_discount": "",
                        "shop_name": "",
                        "image_description": parsed.get("main_image_description", ""),
                        "features": "",
                        "usage_scenario": "",
                        "gifts": "",
                        "order_status": "",
                        "order_number": "",
                        "logistics_status": ""
                    })
                
                # 购物车页面旧格式（shops结构）
                elif image_type == "购物车页面" and "shops" in parsed:
                    for shop in parsed.get("shops", []):
                        for old_product in shop.get("products", []):
                            products.append({
                                "product_name": old_product.get("product_name", ""),
                                "sku": old_product.get("sku", ""),
                                "quantity": int(old_product.get("quantity", "1")) if str(old_product.get("quantity", "1")).isdigit() else 1,
                                "price_original": "",
                                "price_current": old_product.get("actual_price", "").replace("¥", "").replace("￥", ""),
                                "price_discount": old_product.get("discount_price", "").replace("¥", "").replace("￥", ""),
                                "shop_name": shop.get("shop_name", ""),
                                "image_description": "",
                                "features": "",
                                "usage_scenario": "",
                                "gifts": "",
                                "order_status": "",
                                "order_number": "",
                                "logistics_status": ""
                            })
                
                # 订单详情页面旧格式（orders结构）
                elif image_type == "订单详情页面" and "orders" in parsed:
                    for order in parsed.get("orders", []):
                        for old_product in order.get("products", []):
                            products.append({
                                "product_name": old_product.get("product_name", ""),
                                "sku": old_product.get("specification", ""),
                                "quantity": int(old_product.get("quantity", "1")) if str(old_product.get("quantity", "1")).isdigit() else 1,
                                "price_original": "",
                                "price_current": "",
                                "price_discount": "",
                                "shop_name": "",
                                "image_description": "",
                                "features": "",
                                "usage_scenario": "",
                                "gifts": "",
                                "order_status": order.get("order_status", ""),
                                "order_number": order.get("order_number", ""),
                                "logistics_status": ""
                            })
                
                if products:
                    result["products"] = products
        
        return result
    
    def inference(self, preprocessed_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        推理：使用统一提示词进行分类和信息提取
        
        Args:
            preprocessed_data: 预处理后的数据（包含image_base64）
            
        Returns:
            推理结果
        """
        if not preprocessed_data.get('success'):
            return preprocessed_data
        
        image_base64 = preprocessed_data['image_base64']
        
        # 构建统一提示词
        prompt = self.build_unified_prompt()
        
        # 调用API
        api_result = self.call_api(image_base64, prompt)
        
        if not api_result.get('success'):
            return {
                'success': False,
                'error': api_result.get('error'),
                'image_path': preprocessed_data.get('image_path')
            }
        
        # 解析响应
        parsed_result = self.parse_response(api_result['content'])
        
        if not parsed_result.get('success'):
            return {
                'success': False,
                'error': parsed_result.get('error'),
                'raw_content': parsed_result.get('raw_content'),
                'image_path': preprocessed_data.get('image_path')
            }
        
        # 添加图片路径
        parsed_result['image_path'] = preprocessed_data.get('image_path')
        
        return parsed_result
    
    def _remove_empty_strings(self, obj: Any) -> Any:
        """
        递归移除字典中的空字符串字段
        
        Args:
            obj: 要处理的对象（字典、列表或其他）
            
        Returns:
            处理后的对象
        """
        if isinstance(obj, dict):
            result = {}
            for key, value in obj.items():
                # 递归处理嵌套结构
                processed_value = self._remove_empty_strings(value)
                
                # 跳过空字符串字段（但保留必需字段）
                if processed_value == "":
                    # 必需字段列表（即使为空也要保留）
                    required_fields = ['product_name', 'quantity', 'sku']
                    if key not in required_fields:
                        continue
                
                # 跳过空列表和空字典
                if processed_value == [] or processed_value == {}:
                    continue
                
                result[key] = processed_value
            return result
        elif isinstance(obj, list):
            return [self._remove_empty_strings(item) for item in obj]
        else:
            return obj
    
    def postprocess(self, inference_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        后处理：格式化输出结果（只输出image_type、products和processing_time）
        
        Args:
            inference_result: 推理结果
            
        Returns:
            格式化后的最终结果
        """
        if not inference_result.get('success'):
            return {
                'success': False,
                'error': inference_result.get('error')
            }
        
        image_type = inference_result.get('image_type', '')
        
        # 处理墙面缺陷识别结果（实物拍摄）
        if image_type == self.WALL_DEFECT_LABEL:
            # 构建墙面缺陷结果（包含所有墙面属性）
            wall_result = {
                'success': True,
                'image_type': image_type,
                'products': []
            }
            
            # 添加 secondary_label 和 confidence（如果存在）
            if 'secondary_label' in inference_result:
                wall_result['secondary_label'] = inference_result.get('secondary_label', '')
                wall_result['confidence'] = inference_result.get('secondary_confidence', 'unknown')
            
            # 添加墙面属性（只保留有实际判断的值）
            for attr in self.WALL_ATTRIBUTES:
                if attr in inference_result:
                    value = inference_result[attr]
                    if isinstance(value, str) and value.strip() and value.strip() != "无法判断":
                        wall_result[attr] = value
            
            # 如果没有任何墙面缺陷信息，添加调试信息
            if 'secondary_label' not in wall_result and not any(attr in wall_result for attr in self.WALL_ATTRIBUTES):
                wall_result['debug_info'] = '模型未返回墙面缺陷详细信息'
                # 保留原始内容用于调试
                if 'raw_content' in inference_result:
                    wall_result['raw_response'] = inference_result.get('raw_content', '')[:500]
            
            return wall_result
        
        # 处理商品信息提取结果
        if image_type in self.PRODUCT_EXTRACTION_LABELS:
            products = inference_result.get('products', [])
            
            # 清理products数组中的空字符串字段
            cleaned_products = []
            for product in products:
                cleaned_product = {}
                for key, value in product.items():
                    # 保留必需字段，即使为空
                    required_fields = ['product_name', 'quantity']
                    if key in required_fields:
                        cleaned_product[key] = value
                    # 跳过空字符串字段
                    elif value != "":
                        cleaned_product[key] = value
                    # 对于订单页，保留order_status和order_number即使为空（因为它们是必需的）
                    elif image_type == "订单详情页面" and key in ['order_status', 'order_number']:
                        cleaned_product[key] = value
                cleaned_products.append(cleaned_product)
            
            return {
                'success': True,
                'image_type': image_type,
                'products': cleaned_products
            }
        
        # 其他类型（非商品相关）
        return {
            'success': True,
            'image_type': image_type,
            'products': []
        }
    
    def process(self, image_path: str) -> Dict[str, Any]:
        """
        完整处理流程：预处理 -> 推理 -> 后处理
        
        Args:
            image_path: 图片路径
            
        Returns:
            最终处理结果
        """
        start_time = time.time()
        
        # 预处理
        preprocessed = self.preprocess(image_path)
        
        # 推理
        inference_result = self.inference(preprocessed)
        
        # 后处理
        final_result = self.postprocess(inference_result)
        
        # 添加处理时间
        processing_time = round(time.time() - start_time, 3)
        
        # 返回完整结果（包含所有字段）
        if final_result.get('success'):
            result = {
                'success': True,
                'image_type': final_result.get('image_type', ''),
                'products': final_result.get('products', []),
                'processing_time': processing_time
            }
            
            # 添加墙面缺陷相关字段（如果存在）
            if 'secondary_label' in final_result:
                result['secondary_label'] = final_result['secondary_label']
            if 'confidence' in final_result:
                result['confidence'] = final_result['confidence']
            
            # 添加墙面属性（如果存在）
            for attr in self.WALL_ATTRIBUTES:
                if attr in final_result:
                    result[attr] = final_result[attr]
            
            # 添加调试信息（如果存在）
            if 'debug_info' in final_result:
                result['debug_info'] = final_result['debug_info']
            if 'raw_response' in final_result:
                result['raw_response'] = final_result['raw_response']
            
            return result
        else:
            # 失败时也保持简洁格式，但包含调试信息
            result = {
                'success': False,
                'error': final_result.get('error', '未知错误'),
                'processing_time': processing_time
            }
            # 添加调试信息（如果存在）
            if 'raw_content' in final_result:
                result['raw_content'] = final_result['raw_content']
            if 'image_path' in final_result:
                result['image_path'] = final_result['image_path']
            return result

        def predict_image(self, image_path: str):
            """
            给 Label Studio ML Backend 用的统一接口：
            输入：图片本地路径
            输出：
            cls_name: 墙面缺陷一级类别（如 "裂缝"、"孔洞" 等）
            extra_tags: 其他多维标签字典，key 要和 Label Studio 模板里的 name 对齐
            """
        result = self.process(image_path)

        # 默认值：全部未分类
        cls_name = "全部未分类"
        extra_tags = {}

        if not result.get("success"):
            # 失败时，可以在 reasoning 里写一下原因
            extra_tags["reasoning"] = result.get("error", "模型推理失败")
            return cls_name, extra_tags

        image_type = result.get("image_type", "")

        # 只在"实物拍摄(含售后)"时走墙面缺陷逻辑
        if image_type == self.WALL_DEFECT_LABEL:
            cls_name = result.get("secondary_label", "全部未分类")

            # 这些 key 要和你在 Label Studio 里配置的 name 一致
            for k in [
                "environment",
                "surface_position",
                "surface_material",
                # "defect_area",  # 已删除：不再使用面积估算
                "defect_color",
                "wet_area",
                "water_leak",
                "reasoning",   # 这个通常是 TextArea 文本
            ]:
                # if k in result and isinstance(result[k], str) and result[k].strip():
                #     extra_tags[k] = result[k]
                # elif k == "wet_area" and k not in result:
                #     # 如果 AI 没有返回 wet_area，添加默认值
                #     extra_tags[k] = "无法判断"
                # 1. 第一步：不管有没有这个 key，也不管是 None 还是空，先取出来
                # 如果取不到，raw_val 就是 None
                raw_val = result.get(k)
                
                # 2. 第二步：清洗数据（转成字符串，去掉空格）
                # 如果 raw_val 是 None，final_val 变为空字符串 ""
                final_val = str(raw_val).strip() if raw_val is not None else ""

                # ================= 核心修改开始 =================
                # 3. 针对 wet_area 的“强制兜底”逻辑
                if k == "wet_area":
                    # 如果处理完是空的（说明 AI 没返回，或者返回了 None/空字符串）
                    if not final_val:
                        extra_tags[k] = "无法判断"  # 强制给默认值
                    else:
                        # 如果有值，直接用（比如 "干区"）
                        extra_tags[k] = final_val
                
                # 4. 针对其他字段的逻辑（有值才要，没值拉倒）
                elif final_val:
                    extra_tags[k] = final_val
                # ================= 核心修改结束 =================
        else:
            # 不是墙面图，就统一丢到“全部未分类”
            cls_name = "全部未分类"
            extra_tags["reasoning"] = f"非墙面缺陷图片，类别: {image_type}"

        return cls_name, extra_tags

    
    def batch_process(self, image_paths: List[str], output_dir: str = None) -> List[Dict[str, Any]]:
        """
        批量处理图片
        
        Args:
            image_paths: 图片路径列表
            output_dir: 输出目录（可选），如果指定，会将每个结果保存为JSON文件
            
        Returns:
            处理结果列表
        """
        results = []
        output_path_obj = Path(output_dir) if output_dir else None
        
        if output_path_obj:
            output_path_obj.mkdir(parents=True, exist_ok=True)
        
        for i, image_path in enumerate(image_paths, 1):
            # 简化输出：只显示进度和文件名
            filename = Path(image_path).name
            print(f"[{i}/{len(image_paths)}] {filename}", end=" ... ", flush=True)
            
            try:
                result = self.process(image_path)
                results.append(result)
                
                # 显示简要结果
                if result.get('success'):
                    if result.get('image_type') == self.WALL_DEFECT_LABEL:
                        print(f"✅ {result.get('secondary_label', '?')}", flush=True)
                    else:
                        print(f"✅ {result.get('image_type', '?')}", flush=True)
                else:
                    print(f"❌ {result.get('error', '失败')}", flush=True)
                
                # 保存到文件
                if output_path_obj:
                    image_path_obj = Path(image_path)
                    output_filename = image_path_obj.stem + '.json'
                    output_file = output_path_obj / output_filename
                    
                    with open(output_file, 'w', encoding='utf-8') as f:
                        json.dump(result, f, ensure_ascii=False, indent=2)
                
            except Exception as e:
                error_result = {
                    'success': False,
                    'error': str(e),
                    'image_path': image_path
                }
                results.append(error_result)
                print(f"❌ 异常: {str(e)}", flush=True)
        
        # 保存汇总结果
        if output_path_obj:
            summary_file = output_path_obj / 'batch_summary.json'
            summary = {
                'total': len(image_paths),
                'success': sum(1 for r in results if r.get('success')),
                'failed': sum(1 for r in results if not r.get('success')),
                'results': results
            }
            with open(summary_file, 'w', encoding='utf-8') as f:
                json.dump(summary, f, ensure_ascii=False, indent=2)
            print(f"\n✅ 批量处理完成，汇总结果已保存到: {summary_file}")
        
        return results


def main():
    """测试函数"""
    import argparse
    from pathlib import Path
    
    parser = argparse.ArgumentParser(description="统一视觉模型测试")
    parser.add_argument("--image", type=str, help="单张图片路径")
    parser.add_argument("--input-dir", type=str, help="输入目录（批量处理）")
    parser.add_argument("--output", "-o", type=str, help="输出JSON文件路径（单张图片时使用）")
    parser.add_argument("--output-dir", type=str, help="输出目录（批量处理时使用）")
    args = parser.parse_args()
    
    # 检查参数
    if not args.image and not args.input_dir:
        parser.error("必须指定 --image 或 --input-dir")
    
    # 初始化模型
    # 检查使用哪个提供商
    provider = os.getenv('VISION_PROVIDER', 'doubao').lower()
    if provider == 'openrouter':
        model_name = os.getenv('VISION_MODEL', 'openai/gpt-4o')
        model = UnifiedVisionModel(model_name=model_name, provider='openrouter')
    else:
        model = UnifiedVisionModel()
    
    # 批量处理模式
    if args.input_dir:
        input_dir = Path(args.input_dir)
        if not input_dir.exists():
            print(f"❌ 错误：输入目录不存在: {input_dir}")
            return
        
        # 递归查找所有图片文件
        image_files = []
        patterns = ['**/*.jpg', '**/*.jpeg', '**/*.png', '**/*.JPG', '**/*.JPEG', '**/*.PNG']
        
        for pattern in patterns:
            image_files.extend(input_dir.glob(pattern))
        
        # 去重
        image_files = list(set(image_files))
        
        if not image_files:
            print(f"❌ 错误：在 {input_dir} 中未找到匹配的图片文件")
            return
        
        print(f"找到 {len(image_files)} 张图片")
        
        # 批量处理
        output_dir = args.output_dir or str(input_dir / 'output')
        results = model.batch_process([str(f) for f in image_files], output_dir=output_dir)
        
        print(f"\n{'='*80}")
        print(f"批量处理完成")
        print(f"{'='*80}")
        print(f"总计: {len(results)}")
        print(f"成功: {sum(1 for r in results if r.get('success'))}")
        print(f"失败: {sum(1 for r in results if not r.get('success'))}")
    
    # 单张图片处理模式
    else:
        if not Path(args.image).exists():
            print(f"❌ 错误：图片文件不存在: {args.image}")
            return
        
        # 处理图片
        result = model.process(args.image)
        
        # 打印结果
        print(f"\n{'='*80}")
        print(f"处理结果")
        print(f"{'='*80}")
        print(json.dumps(result, ensure_ascii=False, indent=2))
        
        # 保存到文件
        if args.output:
            output_path = Path(args.output)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
            print(f"\n✅ 结果已保存到: {output_path}")
        
        elif args.output_dir:
            # 使用输出目录，自动生成文件名
            output_dir = Path(args.output_dir)
            output_dir.mkdir(parents=True, exist_ok=True)
            
            # 使用图片文件名（不含扩展名）+ .json
            image_path = Path(args.image)
            output_filename = image_path.stem + '.json'
            output_path = output_dir / output_filename
            
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
            print(f"\n✅ 结果已保存到: {output_path}")


if __name__ == "__main__":
    main()

