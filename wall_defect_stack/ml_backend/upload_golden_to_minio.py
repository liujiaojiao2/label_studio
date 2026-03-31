#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
将黄金数据集上传到 MinIO 并创建新的 bucket
按新的 5 大分类体系组织数据
"""

import os
import json
import shutil
from pathlib import Path
from minio import Minio
from minio.error import S3Error
from typing import List, Dict, Any


class GoldenDatasetUploader:
    """黄金数据集上传器"""

    # MinIO 配置
    ENDPOINT = "192.168.0.116:39000"
    ACCESS_KEY = "minioadmin"
    SECRET_KEY = "minioadmin123"
    BUCKET_NAME = "golden-dataset"

    # 新分类体系目录结构
    NEW_CATEGORIES = {
        "环境实拍图": [
            "孔洞", "裂缝", "起皮掉皮", "露出基层", "涂鸦&污渍", "全部未分类"
        ],
        "购物app截图": [
            "商品头图", "商品详情页截图", "商品分类选项", "订单详情页面",
            "购物车页面", "评论区截图页面", "支付页面", "物流页面-物流列表页面",
            "物流页面-物流跟踪页面", "物流页面-物流异常页面", "退款页面",
            "退货页面", "换货页面", "店铺页面", "活动页面", "优惠券领取页面",
            "账单", "投诉举报页面", "平台介入页面"
        ],
        "商品/包裹实拍图": [
            "实物拍摄(含售后)"
        ],
        "制式图片": [
            "户型图", "装修图", "其他"
        ],
        "其他": [
            "其他类别图片", "外部APP截图"
        ]
    }

    def __init__(self):
        """初始化 MinIO 客户端"""
        self.client = Minio(
            self.ENDPOINT,
            access_key=self.ACCESS_KEY,
            secret_key=self.SECRET_KEY,
            secure=False
        )

        print(f"✅ MinIO 客户端初始化成功")
        print(f"   端点: {self.ENDPOINT}")

    def create_bucket(self):
        """创建新的 bucket"""
        try:
            # 检查 bucket 是否存在
            if self.client.bucket_exists(self.BUCKET_NAME):
                print(f"\n⚠️  Bucket '{self.BUCKET_NAME}' 已存在")
                choice = input("是否清空并重建? (y/N): ").strip().lower()
                if choice == 'y':
                    # 删除所有对象
                    objects = self.client.list_objects(self.BUCKET_NAME, recursive=True)
                    for obj in objects:
                        self.client.remove_object(self.BUCKET_NAME, obj.object_name)
                    print(f"✅ 已清空 bucket")
                else:
                    print(f"✅ 使用现有 bucket")
                    return
            else:
                # 创建新 bucket
                self.client.make_bucket(self.BUCKET_NAME)
                print(f"✅ 已创建 bucket: {self.BUCKET_NAME}")

        except S3Error as e:
            print(f"❌ MinIO 操作失败: {e}")
            raise

    def load_sampled_data(self, detail_file: str) -> List[Dict[str, Any]]:
        """
        加载采样的详细数据

        Args:
            detail_file: 详细数据文件路径

        Returns:
            采样数据列表
        """
        detail_path = Path(detail_file)

        if not detail_path.exists():
            print(f"❌ 文件不存在: {detail_file}")
            return []

        with open(detail_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        print(f"✅ 已加载 {len(data)} 条采样数据")
        return data

    def upload_to_minio(
        self,
        sampled_data: List[Dict[str, Any]],
        base_minio_path: str = "/home/star/jiaojiao/Label Studio/wall_defect_stack/data/minio/wall-defects/"
    ):
        """
        上传图片到 MinIO

        Args:
            sampled_data: 采样数据列表
            base_minio_path: 本地 MinIO 数据路径
        """
        base_path = Path(base_minio_path)

        print(f"\n📤 开始上传到 MinIO...")
        print(f"   目标 Bucket: {self.BUCKET_NAME}")
        print(f"   源路径: {base_path}")

        success_count = 0
        failed_count = 0
        failed_files = []

        for i, item in enumerate(sampled_data, 1):
            img_path_str = item["image"]
            original_category = item["original_category"]
            primary_category = item["primary_category"]

            # 获取本地文件路径
            # 如果是绝对路径，直接使用
            img_path = Path(img_path_str)

            # 如果文件不存在，尝试从 MinIO 路径构造
            if not img_path.exists():
                # 可能是相对路径
                relative_path = None
                for cat_dir in base_path.iterdir():
                    potential = cat_dir / original_category
                    if potential.exists() and potential.is_dir():
                        # 检查文件是否在这个目录下
                        for f in potential.iterdir():
                            if f.name == img_path.name:
                                img_path = f
                                relative_path = f"{cat_dir.name}/{original_category}/{f.name}"
                                break
                        if img_path.exists():
                            break

            if not img_path.exists():
                print(f"  [{i}/{len(sampled_data)}] ❌ 文件不存在: {img_path_str}")
                failed_count += 1
                failed_files.append(img_path_str)
                continue

            # 构造目标路径：一级分类/原始分类/文件名
            # 例如: 环境实拍图/起皮掉皮/xxx.jpg
            file_name = img_path.name
            object_name = f"{primary_category}/{original_category}/{file_name}"

            try:
                # 上传文件
                self.client.fput_object(
                    self.BUCKET_NAME,
                    object_name,
                    str(img_path)
                )
                success_count += 1

                # 简化输出：每10个显示一次进度
                if i % 10 == 0 or i == len(sampled_data):
                    print(f"  [{i}/{len(sampled_data)}] ✅ 已上传 {success_count} 张")

            except S3Error as e:
                print(f"  [{i}/{len(sampled_data)}] ❌ 上传失败: {file_name} - {e}")
                failed_count += 1
                failed_files.append(img_path_str)

        # 打印统计
        print(f"\n{'='*60}")
        print(f"📊 上传完成统计")
        print(f"{'='*60}")
        print(f"总计: {len(sampled_data)}")
        print(f"成功: {success_count}")
        print(f"失败: {failed_count}")

        if failed_files:
            print(f"\n❌ 失败文件列表:")
            for f in failed_files[:10]:  # 只显示前10个
                print(f"  - {f}")
            if len(failed_files) > 10:
                print(f"  ... 还有 {len(failed_files) - 10} 个")

    def create_bucket_structure(self):
        """
        创建 bucket 中的目录结构（空文件占位）
        这样可以在 MinIO Console 中看到完整的目录树
        """
        print(f"\n📁 创建目录结构...")

        for primary, subcategories in self.NEW_CATEGORIES.items():
            for sub in subcategories:
                # 创建 .placeholder 文件
                object_name = f"{primary}/{sub}/.placeholder"
                try:
                    # 创建一个临时的空文件
                    import tempfile
                    with tempfile.NamedTemporaryFile(mode='w', delete=False) as tmp:
                        tmp.write("")
                        tmp_path = tmp.name

                    self.client.fput_object(self.BUCKET_NAME, object_name, tmp_path)

                    # 删除临时文件
                    os.unlink(tmp_path)

                except S3Error:
                    pass  # 忽略已存在的文件

        print(f"✅ 目录结构创建完成")

    def generate_labelstudio_import(self, output_file: str = None):
        """
        生成 Label Studio 导入文件（使用 S3 URL）

        Args:
            output_file: 输出文件路径
        """
        # 列出 bucket 中的所有图片
        print(f"\n📝 生成 Label Studio 导入文件...")

        objects = self.client.list_objects(self.BUCKET_NAME, recursive=True)

        import_data = []

        for obj in objects:
            # 跳过 placeholder 文件
            if obj.object_name.endswith('/.placeholder'):
                continue

            # 构建 S3 URL
            s3_url = f"s3://{self.BUCKET_NAME}/{obj.object_name}"
            import_data.append({"image": s3_url})

        # 保存文件
        if output_file is None:
            output_file = f"labelstudio_import_{self.BUCKET_NAME}.json"

        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(import_data, f, ensure_ascii=False, indent=2)

        print(f"✅ 导入文件已保存: {output_path}")
        print(f"   共 {len(import_data)} 张图片")

        return output_path

    def run(self, detail_file: str):
        """
        执行完整的上传流程

        Args:
            detail_file: 采样详细数据文件路径
        """
        print("="*60)
        print("🚀 黄金数据集上传工具")
        print("="*60)

        # 1. 创建 bucket
        self.create_bucket()

        # 2. 创建目录结构
        self.create_bucket_structure()

        # 3. 加载采样数据
        sampled_data = self.load_sampled_data(detail_file)

        if not sampled_data:
            print("\n❌ 没有数据需要上传")
            return

        # 4. 上传文件
        self.upload_to_minio(sampled_data)

        # 5. 生成 Label Studio 导入文件
        self.generate_labelstudio_import()

        print("\n" + "="*60)
        print("🎉 黄金数据集上传完成！")
        print("="*60)
        print(f"Bucket: {self.BUCKET_NAME}")
        print(f"MinIO Console: http://{self.ENDPOINT.replace('39000', '39001')}")


def main():
    """命令行入口"""
    import argparse

    parser = argparse.ArgumentParser(
        description="将黄金数据集上传到 MinIO",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument(
        "--detail-file", "-d",
        default="golden_dataset_270_42_detail.json",
        help="采样详细数据文件路径"
    )
    parser.add_argument(
        "--bucket", "-b",
        default="golden-dataset",
        help="目标 bucket 名称"
    )

    args = parser.parse_args()

    # 创建上传器
    uploader = GoldenDatasetUploader()
    uploader.BUCKET_NAME = args.bucket

    # 执行上传
    uploader.run(args.detail_file)


if __name__ == "__main__":
    main()
