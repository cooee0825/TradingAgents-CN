#!/usr/bin/env python3
"""
简单测试Reddit股票分析功能

此脚本用于快速测试新开发的Reddit股票热度分析功能是否正常工作。
"""

import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))


def test_imports():
    """测试导入是否正常"""
    print("🧪 测试1: 检查导入...")
    try:
        from tradingagents.dataflows.reddit_utils import (
            StockPopularityAnalyzer,
            analyze_stock_popularity,
            generate_reddit_stock_ranking,
            STOCK_SUBREDDITS,
            SUBREDDIT_WEIGHTS,
            ticker_to_company,
        )

        print("✅ 所有导入成功")
        return True
    except ImportError as e:
        print(f"❌ 导入失败: {e}")
        return False


def test_basic_functionality():
    """测试基础功能"""
    print("\n🧪 测试2: 检查基础功能...")

    try:
        from tradingagents.dataflows.reddit_utils import StockPopularityAnalyzer

        # 创建分析器实例
        analyzer = StockPopularityAnalyzer()
        print("✅ 分析器创建成功")

        # 测试关键词生成
        keywords = analyzer.generate_stock_keywords("AAPL")
        print(f"✅ 关键词生成成功: {keywords[:3]}...")

        # 测试数据目录
        print(f"✅ 数据目录设置: {analyzer.data_dir}")

        return True

    except Exception as e:
        print(f"❌ 基础功能测试失败: {e}")
        return False


def test_configuration():
    """测试配置是否正确"""
    print("\n🧪 测试3: 检查配置...")

    try:
        from tradingagents.dataflows.reddit_utils import (
            STOCK_SUBREDDITS,
            SUBREDDIT_WEIGHTS,
            ticker_to_company,
        )

        print(f"✅ 股票subreddit配置: {len(STOCK_SUBREDDITS)} 个")
        print(f"   - {', '.join(STOCK_SUBREDDITS)}")

        print(f"✅ subreddit权重配置: {len(SUBREDDIT_WEIGHTS)} 个")
        for name, weight in SUBREDDIT_WEIGHTS.items():
            print(f"   - {name}: {weight}")

        print(f"✅ 股票映射表: {len(ticker_to_company)} 只股票")
        print(f"   - 示例: {list(ticker_to_company.items())[:3]}")

        return True

    except Exception as e:
        print(f"❌ 配置测试失败: {e}")
        return False


def test_data_availability():
    """测试数据文件是否存在"""
    print("\n🧪 测试4: 检查数据可用性...")

    data_dir = Path("data/reddit_data/company_news")

    if not data_dir.exists():
        print("⚠️ Reddit数据目录不存在")
        print(
            "请先运行: python -m tradingagents.dataflows.reddit_utils --category company_news"
        )
        return False

    # 检查各个subreddit的数据文件
    from tradingagents.dataflows.reddit_utils import STOCK_SUBREDDITS

    existing_files = []
    missing_files = []

    for subreddit in STOCK_SUBREDDITS:
        file_path = data_dir / f"{subreddit}.jsonl"
        if file_path.exists():
            existing_files.append(subreddit)
        else:
            missing_files.append(subreddit)

    print(f"✅ 找到数据文件: {len(existing_files)} 个")
    for subreddit in existing_files:
        file_path = data_dir / f"{subreddit}.jsonl"
        file_size = file_path.stat().st_size / 1024  # KB
        print(f"   - r/{subreddit}: {file_size:.1f}KB")

    if missing_files:
        print(f"⚠️ 缺少数据文件: {len(missing_files)} 个")
        for subreddit in missing_files:
            print(f"   - r/{subreddit}")

    return len(existing_files) > 0


def test_simple_analysis():
    """测试简单分析功能"""
    print("\n🧪 测试5: 简单分析测试...")

    try:
        from tradingagents.dataflows.reddit_utils import analyze_stock_popularity

        # 尝试分析AAPL（如果数据存在）
        result = analyze_stock_popularity(
            ticker="AAPL",
            days_back=30,  # 增加天数范围
            min_relevance=0.05,  # 降低相关度要求
        )

        print(f"✅ AAPL分析成功:")
        print(f"   - 提及次数: {result['total_mentions']}")
        print(f"   - 总热度: {result['total_popularity_score']:.2f}")
        print(f"   - 关键词: {', '.join(result['keywords'][:3])}")

        if result["total_mentions"] == 0:
            print("⚠️ 未找到相关讨论，这可能是正常的")
            print("   建议增加days_back参数或降低min_relevance阈值")

        return True

    except Exception as e:
        print(f"❌ 简单分析测试失败: {e}")
        return False


def main():
    """主测试函数"""
    print("🔍 Reddit股票分析功能测试")
    print("=" * 50)

    tests = [
        test_imports,
        test_basic_functionality,
        test_configuration,
        test_data_availability,
        test_simple_analysis,
    ]

    passed = 0
    total = len(tests)

    for test_func in tests:
        try:
            if test_func():
                passed += 1
        except Exception as e:
            print(f"❌ 测试异常: {e}")

    print(f"\n📊 测试结果: {passed}/{total} 通过")

    if passed == total:
        print("🎉 所有测试通过！系统可以使用。")
        print("\n💡 下一步建议:")
        print("1. 运行演示脚本: python examples/reddit_stock_analysis_demo.py")
        print("2. 下载最新数据: python -m tradingagents.dataflows.reddit_utils")
        print("3. 在你的项目中使用API函数")
    else:
        print("⚠️ 部分测试失败，请检查配置和数据。")
        if passed >= 3:
            print("基础功能正常，主要是数据问题。")

    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
