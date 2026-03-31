#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
改进版黄金数据集采样器
确保每个分类至少有 min_samples 张样本
"""

import os
import json
import random
from pathlib import Path
from typing import List, Dict, Any
from collections import defaultdict


class ImprovedGoldenDatasetSampler:
    """改进的黄金数据集采样器"""

    IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif', '.webp', '.jfif', '.bmp'}

    # 分类映射
    CATEGORY_MAPPING = {
        # 环境实拍图
        "孔洞": "环境实拍图", "裂缝": "环境实拍图", "起皮掉皮": "环境实拍图",
        "露出基层": "环境实拍图", "涂鸦&污渍": "环境实拍图", "全部未分类": "环境实拍图",
        # 购物app截图
        "商品头图": "购物app截图", "商品详情页截图": "购物app截图",
        "商品分类选项": "购物app截图", "订单详情页面": "购物app截图",
        "购物车页面": "购物app截图", "评论区截图页面": "购物app截图",
        "支付页面": "购物app截图", "物流页面-物流列表页面": "购物app截图",
        "物流页面-物流跟踪页面": "购物app截图", "物流页面-物流异常页面": "购物app截图",
        "退款页面": "购物app截图", "退货页面": "购物app截图", "换货页面": "购物app截图",
        "店铺页面": "购物app截图", "活动页面": "购物app截图",
        "优惠券领取页面": "购物app截图", "账单": "购物app截图",
        "投诉举报页面": "购物app截图", "平台介入页面": "购物app截图",
        # 其他
        "其他类别图片": "其他", "外部APP截图": "其他",
        "实物拍摄(含售后)": "商品/包裹实拍图",
    }

    def __init__(self, base_dir: str, seed: int = 42):
        self.base_dir = Path(base_dir)
        self.seed = seed
        random.seed(seed)

    def scan_all_datasets(self) -> Dict[str, List[Path]]:
        """扫描所有数据集"""
        all_images = defaultdict(list)

        # 扫描 wall_dataset_v1_organized
        for cat_dir in (self.base_dir / "wall_dataset_v1_organized").iterdir():
            if cat_dir.is_dir():
                for img in cat_dir.glob("*"):
                    if img.suffix.lower() in self.IMAGE_EXTENSIONS:
                        all_images[cat_dir.name].append(img)

        # 扫描 dataset
        for cat_dir in (self.base_dir / "dataset").iterdir():
            if cat_dir.is_dir():
                for img in cat_dir.glob("*"):
                    if img.suffix.lower() in self.IMAGE_EXTENSIONS:
                        all_images[cat_dir.name].append(img)

        return all_images

    def sample_with_minimum(
        self,
        min_samples_per_category: int = 5,
        max_total: int = 350,
        wall_ratio: float = 0.5
    ) -> List[Dict[str, Any]]:
        """
        带最小样本量的采样策略

        Args:
            min_samples_per_category: 每个分类的最小样本量
            max_total: 最大总样本数
            wall_ratio: 墙体缺陷图片的目标比例
        """
        print("="*60)
        print("🎯 改进版采样策略")
        print("="*60)
        print(f"每个分类最少: {min_samples_per_category} 张")
        print(f"墙体缺陷占比: {wall_ratio*100}%")

        # 扫描所有数据
        all_images = self.scan_all_datasets()

        # 按一级分类分组
        primary_groups = defaultdict(list)
        for cat, images in all_images.items():
            primary = self.CATEGORY_MAPPING.get(cat, "其他")
            for img in images:
                primary_groups[primary].append((img, cat))

        print(f"\n📊 原始数据分布:")
        for primary, items in sorted(primary_groups.items()):
            print(f"  {primary}: {len(items)} 张")

        # 第一阶段: 确保每个原始分类至少有 min_samples_per_category 张
        sampled = []
        used_images = set()

        for cat, images in all_images.items():
            available = len(images)
            target = min(min_samples_per_category, available)

            if available < min_samples_per_category:
                print(f"\n⚠️  警告: {cat} 只有 {available} 张，少于最小值 {min_samples_per_category}")

            # 采样
            selected = random.sample(images, target)
            for img in selected:
                primary = self.CATEGORY_MAPPING.get(cat, "其他")
                sampled.append({
                    "image": str(img),
                    "primary_category": primary,
                    "original_category": cat
                })
                used_images.add(img)

        print(f"\n✅ 第一阶段完成: {len(sampled)} 张（每个分类至少 {min_samples_per_category} 张）")

        # 第二阶段: 补充到目标数量
        current_wall = sum(1 for s in sampled if s["primary_category"] == "环境实拍图")
        target_wall = int(max_total * wall_ratio)
        wall_needed = max(0, target_wall - current_wall)

        current_other = len(sampled) - current_wall
        other_needed = max_total - current_wall - wall_needed - current_other

        print(f"\n📋 第二阶段计划:")
        print(f"  环境实拍图: 当前 {current_wall}, 需要 {wall_needed}")
        print(f"  其他类别: 当前 {current_other}, 需要 {other_needed}")

        # 收集未使用的图片
        wall_pool = []
        other_pool = []

        for cat, images in all_images.items():
            primary = self.CATEGORY_MAPPING.get(cat, "其他")
            for img in images:
                if img not in used_images:
                    if primary == "环境实拍图":
                        wall_pool.append((img, cat))
                    else:
                        other_pool.append((img, cat))

        # 采样补充
        if wall_needed > 0 and wall_pool:
            additional = min(wall_needed, len(wall_pool))
            selected = random.sample(wall_pool, additional)
            for img, cat in selected:
                sampled.append({
                    "image": str(img),
                    "primary_category": "环境实拍图",
                    "original_category": cat
                })

        if other_needed > 0 and other_pool:
            additional = min(other_needed, len(other_pool))
            selected = random.sample(other_pool, additional)
            for img, cat in selected:
                primary = self.CATEGORY_MAPPING.get(cat, "其他")
                sampled.append({
                    "image": str(img),
                    "primary_category": primary,
                    "original_category": cat
                })

        # 打乱顺序
        random.shuffle(sampled)

        return sampled

    def save_results(self, sampled_data: List[Dict[str, Any]], output_prefix: str = "golden_dataset_v2"):
        """保存结果"""
        # 保存详细数据
        detail_file = Path(f"{output_prefix}_detail.json")
        with open(detail_file, 'w', encoding='utf-8') as f:
            json.dump(sampled_data, f, ensure_ascii=False, indent=2)

        # 生成统计
        cat_count = defaultdict(int)
        for item in sampled_data:
            cat_count[item['original_category']] += 1

        # 保存报告
        report_file = Path(f"{output_prefix}_report.txt")
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write("="*60 + "\n")
            f.write("黄金数据集 V2 统计报告\n")
            f.write("="*60 + "\n\n")
            f.write(f"总图片数: {len(sampled_data)}\n")
            f.write(f"随机种子: {self.seed}\n\n")

            # 一级分类统计
            primary_count = defaultdict(int)
            for item in sampled_data:
                primary_count[item['primary_category']] += 1

            f.write("一级分类分布:\n")
            f.write("-" * 40 + "\n")
            for cat, count in sorted(primary_count.items(), key=lambda x: x[1], reverse=True):
                pct = count / len(sampled_data) * 100
                f.write(f"  {cat}: {count} ({pct:.1f}%)\n")

            f.write("\n原始分类分布:\n")
            f.write("-" * 40 + "\n")
            for cat, count in sorted(cat_count.items(), key=lambda x: x[1], reverse=True):
                pct = count / len(sampled_data) * 100
                f.write(f"  {cat}: {count} ({pct:.1f}%)\n")

        print(f"\n✅ 详细数据: {detail_file}")
        print(f"✅ 统计报告: {report_file}")

        return detail_file, report_file


def main():
    import argparse

    parser = argparse.ArgumentParser(description="改进版黄金数据集采样器")
    parser.add_argument("--min-samples", type=int, default=5, help="每个分类的最小样本量")
    parser.add_argument("--max-total", type=int, default=350, help="最大总样本数")
    parser.add_argument("--wall-ratio", type=float, default=0.5, help="墙体缺陷图片占比")
    parser.add_argument("--seed", type=int, default=42, help="随机种子")

    args = parser.parse_args()

    base_dir = "/home/star/jiaojiao/Label Studio/wall_defect_stack/data/minio/wall-defects"

    sampler = ImprovedGoldenDatasetSampler(base_dir, args.seed)

    sampled_data = sampler.sample_with_minimum(
        min_samples_per_category=args.min_samples,
        max_total=args.max_total,
        wall_ratio=args.wall_ratio
    )

    detail_file, report_file = sampler.save_results(sampled_data)

    print(f"\n🎉 黄金数据集 V2 创建完成！共 {len(sampled_data)} 张图片")
    print(f"\n📄 查看详细报告: cat {report_file}")


if __name__ == "__main__":
    main()
