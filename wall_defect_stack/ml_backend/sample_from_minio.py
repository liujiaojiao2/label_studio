#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
从 MinIO 采样图片用于训练标注集
功能：
1. 连接 MinIO 并列出指定 bucket 中的图片
2. 随机采样指定数量的图片
3. 生成 Label Studio 导入格式的 JSON 文件
"""

import os
import json
import random
import argparse
from pathlib import Path
from typing import List, Dict, Any
from minio import Minio
from urllib.parse import urlparse


class MinIOSampler:
    """MinIO 图片采样器"""

    # 支持的图片扩展名
    IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif', '.webp', '.jfif', '.bmp'}

    def __init__(
        self,
        endpoint: str = None,
        access_key: str = None,
        secret_key: str = None,
        secure: bool = False
    ):
        """
        初始化 MinIO 客户端

        Args:
            endpoint: MinIO 服务地址 (如 "192.168.0.116:39000")
            access_key: 访问密钥
            secret_key: 秘密密钥
            secure: 是否使用 HTTPS
        """
        self.endpoint = endpoint or os.getenv("MINIO_ENDPOINT", "192.168.0.116:39000")
        self.access_key = access_key or os.getenv("MINIO_ACCESS_KEY", "minioadmin")
        self.secret_key = secret_key or os.getenv("MINIO_SECRET_KEY", "minioadmin123")
        self.secure = secure

        # 初始化 MinIO 客户端
        self.client = Minio(
            self.endpoint,
            access_key=self.access_key,
            secret_key=self.secret_key,
            secure=self.secure
        )

        print(f"✅ MinIO 客户端初始化成功")
        print(f"   端点: {self.endpoint}")
        print(f"   访问密钥: {self.access_key}")

    def list_images(
        self,
        bucket: str,
        prefix: str = "",
        recursive: bool = True
    ) -> List[str]:
        """
        列出 bucket 中的所有图片

        Args:
            bucket: bucket 名称
            prefix: 对象前缀过滤
            recursive: 是否递归遍历子目录

        Returns:
            图片对象列表 (object name 列表)
        """
        print(f"\n📁 正在列出 bucket '{bucket}' 中的图片...")
        print(f"   前缀: {prefix or '(无)'}")
        print(f"   递归: {'是' if recursive else '否'}")

        images = []
        objects = self.client.list_objects(bucket, prefix=prefix, recursive=recursive)

        for obj in objects:
            # 跳过目录本身（以 / 结尾）
            if obj.object_name.endswith('/'):
                continue

            # 检查文件扩展名
            ext = Path(obj.object_name).suffix.lower()
            if ext in self.IMAGE_EXTENSIONS:
                images.append(obj.object_name)

        print(f"✅ 找到 {len(images)} 张图片")
        return images

    def sample_images(
        self,
        images: List[str],
        sample_size: int,
        seed: int = None
    ) -> List[str]:
        """
        随机采样图片

        Args:
            images: 图片对象列表
            sample_size: 采样数量
            seed: 随机种子

        Returns:
            采样的图片列表
        """
        if sample_size >= len(images):
            print(f"\n⚠️  采样数量 ({sample_size}) 大于等于图片总数 ({len(images)})")
            print(f"   返回所有图片")
            return images

        if seed is not None:
            random.seed(seed)
            print(f"\n🎲 使用随机种子: {seed}")

        sampled = random.sample(images, sample_size)
        print(f"✅ 已随机采样 {len(sampled)} 张图片")
        return sampled

    def generate_labelstudio_import(
        self,
        sampled_images: List[str],
        bucket: str,
        output_file: str = None
    ) -> List[Dict[str, Any]]:
        """
        生成 Label Studio 导入格式的 JSON

        Args:
            sampled_images: 采样的图片对象列表
            bucket: bucket 名称
            output_file: 输出文件路径（可选）

        Returns:
            Label Studio 导入数据列表
        """
        print(f"\n📝 生成 Label Studio 导入文件...")

        import_data = []
        for img_obj in sampled_images:
            # 构建 S3 URL 格式
            s3_url = f"s3://{bucket}/{img_obj}"

            import_data.append({
                "image": s3_url
            })

        # 保存到文件
        if output_file:
            output_path = Path(output_file)
            output_path.parent.mkdir(parents=True, exist_ok=True)

            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(import_data, f, ensure_ascii=False, indent=2)

            print(f"✅ 导入文件已保存到: {output_path}")

        return import_data

    def run(
        self,
        bucket: str,
        prefix: str = "",
        sample_size: int = 300,
        seed: int = 42,
        output_file: str = None
    ):
        """
        执行完整的采样流程

        Args:
            bucket: bucket 名称
            prefix: 对象前缀过滤
            sample_size: 采样数量
            seed: 随机种子
            output_file: 输出文件路径
        """
        print("=" * 60)
        print("🚀 MinIO 图片采样工具")
        print("=" * 60)

        # 1. 列出所有图片
        images = self.list_images(bucket, prefix, recursive=True)

        if not images:
            print("\n❌ 未找到任何图片，退出")
            return

        # 2. 随机采样
        sampled = self.sample_images(images, sample_size, seed)

        # 3. 生成 Label Studio 导入文件
        if output_file is None:
            output_file = f"labelstudio_import_{sample_size}_{seed}.json"

        import_data = self.generate_labelstudio_import(
            sampled,
            bucket,
            output_file
        )

        print("\n" + "=" * 60)
        print("✅ 采样完成！")
        print("=" * 60)
        print(f"总图片数: {len(images)}")
        print(f"采样数量: {len(sampled)}")
        print(f"输出文件: {output_file}")
        print("=" * 60)

        # 打印前 3 个示例
        print(f"\n📋 示例数据 (前 3 条):")
        for item in import_data[:3]:
            print(f"  - {item['image']}")


def main():
    """命令行入口"""
    parser = argparse.ArgumentParser(
        description="从 MinIO 采样图片用于训练标注集",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例用法:

  # 从默认 bucket 采样 300 张图片
  python sample_from_minio.py

  # 指定 bucket 和采样数量
  python sample_from_minio.py --bucket wall-defects --sample-size 500

  # 指定前缀过滤（只采样特定目录下的图片）
  python sample_from_minio.py --bucket wall-defects --prefix "墙面图片_合并/"

  # 设置随机种子以复现结果
  python sample_from_minio.py --seed 123
        """
    )

    parser.add_argument(
        "--endpoint",
        default=None,
        help="MinIO 服务地址 (默认: 从环境变量 MINIO_ENDPOINT 读取，或使用 192.168.0.116:39000)"
    )
    parser.add_argument(
        "--access-key",
        default=None,
        help="MinIO 访问密钥 (默认: 从环境变量 MINIO_ACCESS_KEY 读取，或使用 minioadmin)"
    )
    parser.add_argument(
        "--secret-key",
        default=None,
        help="MinIO 秘密密钥 (默认: 从环境变量 MINIO_SECRET_KEY 读取，或使用 minioadmin123)"
    )
    parser.add_argument(
        "--bucket",
        default="wall-defects",
        help="MinIO bucket 名称 (默认: wall-defects)"
    )
    parser.add_argument(
        "--prefix",
        default="",
        help="对象前缀过滤，例如 '墙面图片_合并/' (默认: 无过滤)"
    )
    parser.add_argument(
        "--sample-size", "-n",
        type=int,
        default=300,
        help="采样数量 (默认: 300)"
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="随机种子，用于复现采样结果 (默认: 42)"
    )
    parser.add_argument(
        "--output", "-o",
        default=None,
        help="输出文件路径 (默认: labelstudio_import_<n>_<seed>.json)"
    )

    args = parser.parse_args()

    # 创建采样器并执行
    sampler = MinIOSampler(
        endpoint=args.endpoint,
        access_key=args.access_key,
        secret_key=args.secret_key
    )

    sampler.run(
        bucket=args.bucket,
        prefix=args.prefix,
        sample_size=args.sample_size,
        seed=args.seed,
        output_file=args.output
    )


if __name__ == "__main__":
    main()
