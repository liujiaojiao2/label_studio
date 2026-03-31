#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
创建黄金数据集 - 从本地数据集按比例采样
支持均衡采样和聚焦墙体缺陷两种方案
"""

import os
import json
import random
import argparse
from pathlib import Path
from typing import List, Dict, Any, Tuple
from collections import defaultdict


class GoldenDatasetCreator:
    """黄金数据集创建器"""

    # 支持的图片扩展名
    IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif', '.webp', '.jfif', '.bmp'}

    # 新分类体系映射
    CATEGORY_MAPPING = {
        # 环境实拍图 - 墙面缺陷分类
        "孔洞": "环境实拍图",
        "裂缝": "环境实拍图",
        "起皮掉皮": "环境实拍图",
        "露出基层": "环境实拍图",
        "涂鸦&污渍": "环境实拍图",
        "全部未分类": "环境实拍图",  # 可能需要人工审核

        # 购物app截图
        "商品头图": "购物app截图",
        "商品详情页截图": "购物app截图",
        "商品分类选项": "购物app截图",
        "订单详情页面": "购物app截图",
        "购物车页面": "购物app截图",
        "评论区截图页面": "购物app截图",
        "支付页面": "购物app截图",
        "物流页面-物流列表页面": "购物app截图",
        "物流页面-物流跟踪页面": "购物app截图",
        "物流页面-物流异常页面": "购物app截图",
        "退款页面": "购物app截图",
        "退货页面": "购物app截图",
        "换货页面": "购物app截图",

        # 商品/包裹实拍图
        "实物拍摄(含售后)": "商品/包裹实拍图",

        # 其他
        "其他类别图片": "其他",
        "外部APP截图": "其他",
        "店铺页面": "购物app截图",
        "活动页面": "购物app截图",
        "优惠券领取页面": "购物app截图",
        "账单": "购物app截图",
        "投诉举报页面": "购物app截图",
        "平台介入页面": "购物app截图",
    }

    def __init__(self, base_dir: str, seed: int = 42):
        """
        初始化

        Args:
            base_dir: 数据集根目录
            seed: 随机种子
        """
        self.base_dir = Path(base_dir)
        self.seed = seed
        random.seed(seed)

        print(f"✅ 黄金数据集创建器初始化")
        print(f"   数据集目录: {self.base_dir}")
        print(f"   随机种子: {seed}")

    def scan_dataset(self, dataset_name: str) -> Dict[str, List[Path]]:
        """
        扫描指定数据集

        Args:
            dataset_name: 数据集名称 (dataset, wall_dataset_v1_organized, wall_dataset_v1)

        Returns:
            {分类: [图片路径列表]}
        """
        dataset_path = self.base_dir / dataset_name

        if not dataset_path.exists():
            print(f"❌ 数据集不存在: {dataset_path}")
            return {}

        print(f"\n📁 扫描数据集: {dataset_name}")

        categories = defaultdict(list)

        for cat_dir in sorted(dataset_path.iterdir()):
            if not cat_dir.is_dir():
                continue

            cat_name = cat_dir.name
            images = []

            for img_file in cat_dir.iterdir():
                if img_file.suffix.lower() in self.IMAGE_EXTENSIONS:
                    images.append(img_file)

            if images:
                categories[cat_name] = images
                print(f"  ✓ {cat_name}: {len(images)} 张")

        total = sum(len(imgs) for imgs in categories.values())
        print(f"  总计: {total} 张图片, {len(categories)} 个分类")

        return categories

    def sample_balanced(self, total_size: int = 300) -> List[Dict[str, Any]]:
        """
        方案 A: 均衡采样
        - 环境实拍图: 50%
        - 购物app截图: 30%
        - 商品/包裹实拍图: 10%
        - 其他: 10%

        Args:
            total_size: 总采样数量

        Returns:
            Label Studio 导入数据列表
        """
        print("\n" + "=" * 60)
        print("🎯 方案 A: 均衡采样")
        print("=" * 60)

        # 扫描所有数据集
        all_categories = {}

        # 1. 扫描墙面数据集
        wall_dataset = self.scan_dataset("wall_dataset_v1_organized")
        for cat, imgs in wall_dataset.items():
            all_categories[cat] = imgs

        # 2. 扫描电商数据集
        ecommerce_dataset = self.scan_dataset("dataset")
        for cat, imgs in ecommerce_dataset.items():
            if cat in all_categories:
                all_categories[cat].extend(imgs)
            else:
                all_categories[cat] = imgs

        # 按新分类体系分组
        new_categories = {
            "环境实拍图": [],
            "购物app截图": [],
            "商品/包裹实拍图": [],
            "其他": []
        }

        for old_cat, images in all_categories.items():
            new_cat = self.CATEGORY_MAPPING.get(old_cat, "其他")
            new_categories[new_cat].extend([(img, old_cat) for img in images])

        # 打印统计
        print(f"\n📊 原始数据分布:")
        for new_cat, items in new_categories.items():
            print(f"  {new_cat}: {len(items)} 张")

        # 计算采样数量
        sample_plan = {
            "环境实拍图": int(total_size * 0.5),
            "购物app截图": int(total_size * 0.3),
            "商品/包裹实拍图": int(total_size * 0.1),
            "其他": total_size - int(total_size * 0.5) - int(total_size * 0.3) - int(total_size * 0.1)
        }

        print(f"\n📋 采样计划 (共 {total_size} 张):")
        for cat, count in sample_plan.items():
            available = len(new_categories[cat])
            print(f"  {cat}: {count} 张 (可用: {available})")

        # 执行采样
        sampled_data = []

        for new_cat, target_count in sample_plan.items():
            available = new_categories[new_cat]

            if len(available) < target_count:
                print(f"\n⚠️  警告: {new_cat} 可用图片不足 ({len(available)} < {target_count})")
                target_count = len(available)

            # 随机采样
            sampled = random.sample(available, target_count)

            for img_path, old_cat in sampled:
                sampled_data.append({
                    "image": str(img_path),
                    "primary_category": new_cat,
                    "original_category": old_cat
                })

        # 打乱顺序
        random.shuffle(sampled_data)

        return sampled_data

    def sample_focused_wall(self, total_size: int = 300) -> List[Dict[str, Any]]:
        """
        方案 B: 聚焦墙体缺陷
        - 环境实拍图: 83%
        - 其他类别: 17%

        Args:
            total_size: 总采样数量

        Returns:
            Label Studio 导入数据列表
        """
        print("\n" + "=" * 60)
        print("🎯 方案 B: 聚焦墙体缺陷")
        print("=" * 60)

        # 扫描墙面数据集
        wall_dataset = self.scan_dataset("wall_dataset_v1_organized")

        # 扫描电商数据集
        ecommerce_dataset = self.scan_dataset("dataset")

        # 按新分类体系分组
        wall_images = []
        other_images = []

        for cat, images in wall_dataset.items():
            for img in images:
                wall_images.append((img, cat))

        for cat, images in ecommerce_dataset.items():
            for img in images:
                other_images.append((img, cat))

        print(f"\n📊 原始数据分布:")
        print(f"  环境实拍图: {len(wall_images)} 张")
        print(f"  其他类别: {len(other_images)} 张")

        # 计算采样数量
        wall_count = int(total_size * 0.83)
        other_count = total_size - wall_count

        print(f"\n📋 采样计划 (共 {total_size} 张):")
        print(f"  环境实拍图: {wall_count} 张")
        print(f"  其他类别: {other_count} 张")

        sampled_data = []

        # 采样墙体图片
        if len(wall_images) < wall_count:
            print(f"\n⚠️  警告: 墙体图片不足 ({len(wall_images)} < {wall_count})")
            wall_count = len(wall_images)

        sampled_wall = random.sample(wall_images, wall_count)
        for img_path, old_cat in sampled_wall:
            sampled_data.append({
                "image": str(img_path),
                "primary_category": "环境实拍图",
                "original_category": old_cat
            })

        # 采样其他图片
        if len(other_images) < other_count:
            print(f"\n⚠️  警告: 其他图片不足 ({len(other_images)} < {other_count})")
            other_count = len(other_images)

        sampled_other = random.sample(other_images, other_count)
        for img_path, old_cat in sampled_other:
            new_cat = self.CATEGORY_MAPPING.get(old_cat, "其他")
            sampled_data.append({
                "image": str(img_path),
                "primary_category": new_cat,
                "original_category": old_cat
            })

        # 打乱顺序
        random.shuffle(sampled_data)

        return sampled_data

    def sample_custom_wall_balanced(self, total_size: int = 300) -> List[Dict[str, Any]]:
        """
        方案 C: 墙体缺陷均衡采样
        从 wall_dataset_v1_organized 中按比例采样各类别

        目标分布:
        - 起皮掉皮: 40%
        - 露出基层: 27%
        - 涂鸦&污渍: 17%
        - 孔洞: 10%
        - 裂缝: 7%

        Args:
            total_size: 总采样数量

        Returns:
            Label Studio 导入数据列表
        """
        print("\n" + "=" * 60)
        print("🎯 方案 C: 墙体缺陷均衡采样")
        print("=" * 60)

        wall_dataset = self.scan_dataset("wall_dataset_v1_organized")

        # 排除"全部未分类"
        defect_categories = {k: v for k, v in wall_dataset.items() if k != "全部未分类"}

        # 目标分布
        target_distribution = {
            "起皮掉皮": 0.40,
            "露出基层": 0.27,
            "涂鸦&污渍": 0.17,
            "孔洞": 0.10,
            "裂缝": 0.07
        }

        print(f"\n📋 采样计划:")
        sample_plan = {}
        for cat, ratio in target_distribution.items():
            count = int(total_size * ratio)
            available = len(defect_categories.get(cat, []))
            sample_plan[cat] = min(count, available)
            print(f"  {cat}: {count} 张 (可用: {available})")

        # 执行采样
        sampled_data = []

        for cat, target_count in sample_plan.items():
            if cat not in defect_categories:
                continue

            available = defect_categories[cat]

            if len(available) < target_count:
                print(f"\n⚠️  警告: {cat} 可用图片不足")
                target_count = len(available)

            sampled = random.sample(available, target_count)

            for img_path in sampled:
                sampled_data.append({
                    "image": str(img_path),
                    "primary_category": "环境实拍图",
                    "original_category": cat
                })

        # 打乱顺序
        random.shuffle(sampled_data)

        return sampled_data

    def generate_labelstudio_import(
        self,
        sampled_data: List[Dict[str, Any]],
        output_file: str = None
    ):
        """
        生成 Label Studio 导入文件

        Args:
            sampled_data: 采样数据
            output_file: 输出文件路径
        """
        if output_file is None:
            output_file = f"golden_dataset_{len(sampled_data)}_{self.seed}.json"

        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # 转换为相对路径或 S3 URL
        import_data = []

        base_minio = "/home/star/jiaojiao/Label Studio/wall_defect_stack/data/minio/wall-defects/"

        for item in sampled_data:
            img_path = item["image"]

            # 转换为 S3 URL
            if img_path.startswith(base_minio):
                relative_path = img_path[len(base_minio):]
                s3_url = f"s3://wall-defects/{relative_path}"
            else:
                s3_url = img_path

            import_data.append({
                "image": s3_url
            })

        # 保存 JSON
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(import_data, f, ensure_ascii=False, indent=2)

        # 保存详细信息（含分类）
        detail_file = output_path.stem + "_detail.json"
        detail_path = output_path.parent / detail_file

        with open(detail_path, 'w', encoding='utf-8') as f:
            json.dump(sampled_data, f, ensure_ascii=False, indent=2)

        print(f"\n✅ 导入文件已保存: {output_path}")
        print(f"✅ 详细信息已保存: {detail_path}")

        # 生成统计报告
        self._generate_report(sampled_data, output_path)

        return output_path

    def _generate_report(self, sampled_data: List[Dict[str, Any]], output_path: Path):
        """生成统计报告"""
        report_file = output_path.stem + "_report.txt"
        report_path = output_path.parent / report_file

        # 统计
        primary_dist = defaultdict(int)
        original_dist = defaultdict(int)

        for item in sampled_data:
            primary = item.get("primary_category", "未知")
            original = item.get("original_category", "未知")
            primary_dist[primary] += 1
            original_dist[original] += 1

        # 写入报告
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write("=" * 60 + "\n")
            f.write("黄金数据集统计报告\n")
            f.write("=" * 60 + "\n\n")

            f.write(f"总图片数: {len(sampled_data)}\n")
            f.write(f"随机种子: {self.seed}\n\n")

            f.write("一级分类分布:\n")
            f.write("-" * 40 + "\n")
            for cat, count in sorted(primary_dist.items(), key=lambda x: x[1], reverse=True):
                pct = count / len(sampled_data) * 100
                f.write(f"  {cat}: {count} ({pct:.1f}%)\n")

            f.write("\n原始分类分布:\n")
            f.write("-" * 40 + "\n")
            for cat, count in sorted(original_dist.items(), key=lambda x: x[1], reverse=True):
                pct = count / len(sampled_data) * 100
                f.write(f"  {cat}: {count} ({pct:.1f}%)\n")

        print(f"✅ 统计报告已保存: {report_path}")


def main():
    """命令行入口"""
    parser = argparse.ArgumentParser(
        description="创建黄金数据集 - 按比例采样",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例用法:

  # 方案 A: 均衡采样 300 张
  python create_golden_dataset.py --scheme balanced --total 300

  # 方案 B: 聚焦墙体缺陷 300 张
  python create_golden_dataset.py --scheme focused --total 300

  # 方案 C: 墙体缺陷均衡采样
  python create_golden_dataset.py --scheme wall-balanced --total 300

  # 指定输出文件
  python create_golden_dataset.py --scheme balanced -o my_golden.json
        """
    )

    parser.add_argument(
        "--base-dir",
        default="/home/star/jiaojiao/Label Studio/wall_defect_stack/data/minio/wall-defects",
        help="数据集根目录"
    )
    parser.add_argument(
        "--scheme", "-s",
        choices=["balanced", "focused", "wall-balanced"],
        default="balanced",
        help="采样方案: balanced(均衡), focused(聚焦墙体), wall-balanced(墙体均衡)"
    )
    parser.add_argument(
        "--total", "-n",
        type=int,
        default=300,
        help="总采样数量 (默认: 300)"
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="随机种子 (默认: 42)"
    )
    parser.add_argument(
        "--output", "-o",
        default=None,
        help="输出文件路径 (默认: golden_dataset_<n>_<seed>.json)"
    )

    args = parser.parse_args()

    # 创建采样器
    creator = GoldenDatasetCreator(
        base_dir=args.base_dir,
        seed=args.seed
    )

    # 根据方案采样
    if args.scheme == "balanced":
        sampled_data = creator.sample_balanced(args.total)
    elif args.scheme == "focused":
        sampled_data = creator.sample_focused_wall(args.total)
    elif args.scheme == "wall-balanced":
        sampled_data = creator.sample_custom_wall_balanced(args.total)
    else:
        parser.error(f"未知方案: {args.scheme}")

    # 生成导入文件
    if sampled_data:
        creator.generate_labelstudio_import(sampled_data, args.output)
        print(f"\n🎉 黄金数据集创建完成！共 {len(sampled_data)} 张图片")
    else:
        print("\n❌ 未采样到任何图片")


if __name__ == "__main__":
    main()
