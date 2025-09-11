#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Reddit数据下载脚本

这个脚本用于从Reddit API下载新闻和讨论数据。
支持批量下载多个subreddit的数据，并保存为JSONL格式。

使用方法:
    python scripts/download_reddit_data.py --category company_news --limit 100
    python scripts/download_reddit_data.py --category all --limit 50
    python scripts/download_reddit_data.py --demo
"""

import os
import sys
import argparse
import logging
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 导入项目模块
try:
    from tradingagents.dataflows.reddit_utils import (
        download_reddit_data,
        download_custom_subreddits,
        demo_usage,
        PRAW_AVAILABLE,
    )
    from tradingagents.utils.logging_manager import get_logger

    logger = get_logger("reddit_downloader")
except ImportError as e:
    print(f"❌ 导入模块失败: {e}")
    print("请确保在项目根目录运行此脚本")
    sys.exit(1)


def check_requirements():
    """检查运行要求"""
    print("🔍 检查运行要求...")

    # 检查praw库
    if not PRAW_AVAILABLE:
        print("❌ praw库未安装")
        print("💡 请运行: pip install praw")
        return False

    # 检查环境变量
    client_id = os.getenv("REDDIT_CLIENT_ID")
    client_secret = os.getenv("REDDIT_CLIENT_SECRET")

    if not all([client_id, client_secret]):
        print("❌ Reddit API凭证未配置")
        print("💡 请设置以下环境变量:")
        print("   REDDIT_CLIENT_ID=your_client_id")
        print("   REDDIT_CLIENT_SECRET=your_client_secret")
        print("   REDDIT_USER_AGENT=YourApp/1.0 (可选)")
        return False

    print("✅ 所有要求已满足")
    return True


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="Reddit数据下载工具")
    parser.add_argument(
        "--category",
        default="company_news",
        choices=["all", "global_news", "company_news", "crypto_news"],
        help="要下载的分类",
    )
    parser.add_argument(
        "--limit", type=int, default=100, help="每个subreddit的下载限制"
    )
    parser.add_argument(
        "--type",
        default="hot",
        choices=["hot", "new", "top", "rising"],
        help="帖子分类",
    )
    parser.add_argument(
        "--time-filter",
        default="week",
        choices=["all", "day", "week", "month", "year"],
        help="时间筛选 (仅对top类型有效)",
    )
    parser.add_argument(
        "--force-refresh", action="store_true", help="强制刷新已存在的文件"
    )
    parser.add_argument("--demo", action="store_true", help="显示使用示例")
    parser.add_argument(
        "--data-dir", default=None, help="数据存储目录 (默认: data/reddit_data)"
    )
    parser.add_argument("--custom-subreddits", nargs="+", help="自定义subreddit列表")
    parser.add_argument("--check", action="store_true", help="检查运行要求")

    args = parser.parse_args()

    # 配置日志
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    # 显示使用示例
    if args.demo:
        demo_usage()
        return

    # 检查要求
    if args.check:
        if check_requirements():
            print("🎉 环境配置正确，可以开始下载数据")
        else:
            print("❌ 环境配置有问题，请先解决")
        return

    # 检查运行要求
    if not check_requirements():
        sys.exit(1)

    print("🚀 开始下载Reddit数据")
    print("=" * 50)
    print(f"📂 分类: {args.category}")
    print(f"📊 限制: {args.limit}")
    print(f"🏷️ 类型: {args.type}")
    print(f"⏰ 时间筛选: {args.time_filter}")
    print(f"🔄 强制刷新: {args.force_refresh}")
    if args.data_dir:
        print(f"📁 数据目录: {args.data_dir}")
    print("")

    try:
        if args.custom_subreddits:
            # 下载自定义subreddit
            print(f"📋 自定义Subreddits: {args.custom_subreddits}")
            result = download_custom_subreddits(
                subreddits=args.custom_subreddits,
                category_name="custom",
                limit_per_subreddit=args.limit,
                category_type=args.type,
                time_filter=args.time_filter,
                force_refresh=args.force_refresh,
                data_dir=args.data_dir,
            )
            results = {"custom": result}
        else:
            # 下载预配置分类
            results = download_reddit_data(
                category=args.category,
                limit_per_subreddit=args.limit,
                category_type=args.type,
                time_filter=args.time_filter,
                force_refresh=args.force_refresh,
                data_dir=args.data_dir,
            )

        print("\n🎉 下载完成!")
        print("📊 结果:")
        for category, success in results.items():
            status = "✅ 成功" if success else "❌ 失败"
            print(f"   {category}: {status}")

        # 显示数据位置
        data_dir = args.data_dir or "data/reddit_data"
        print(f"\n📁 数据保存位置: {data_dir}")
        print("💡 数据格式: 每个subreddit保存为单独的.jsonl文件")

    except Exception as e:
        logger.error(f"❌ 下载失败: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
