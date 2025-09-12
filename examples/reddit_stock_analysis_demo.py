#!/usr/bin/env python3
"""
Reddit股票热度分析演示脚本

此脚本演示如何使用新开发的Reddit股票热度分析功能。

使用前请确保：
1. 设置了REDDIT_CLIENT_ID和REDDIT_CLIENT_SECRET环境变量
2. 安装了praw库: pip install praw
3. 已有Reddit数据或运行数据下载功能

作者: TradingAgents团队
"""

import os
import sys
import logging
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from tradingagents.dataflows.reddit_utils import (
    analyze_stock_popularity,
    generate_reddit_stock_ranking,
    get_trending_stocks,
    compare_stock_popularity,
    download_and_analyze_stocks,
    StockPopularityAnalyzer,
)

# 配置日志
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)


def demo_single_stock_analysis():
    """演示单只股票分析"""
    print("🎯 演示1: 单只股票热度分析")
    print("=" * 50)

    # 分析AAPL的Reddit热度
    ticker = "AAPL"
    result = analyze_stock_popularity(ticker=ticker, days_back=7, min_relevance=0.1)

    print(f"📊 {ticker} 分析结果:")
    print(f"   提及次数: {result['total_mentions']}")
    print(f"   总热度分数: {result['total_popularity_score']:.2f}")
    print(f"   平均热度: {result['average_popularity_score']:.2f}")
    print(f"   分析关键词: {', '.join(result['keywords'][:5])}")

    if result["top_posts"]:
        print(f"   热门帖子示例: {result['top_posts'][0]['title'][:60]}...")

    print()


def demo_stock_ranking():
    """演示股票排行榜"""
    print("🏆 演示2: Reddit股票热度排行榜")
    print("=" * 50)

    # 生成前10名股票排行榜
    ranking = generate_reddit_stock_ranking(
        top_n=10, days_back=7, print_results=True, show_details=False
    )

    print()


def demo_trending_stocks():
    """演示热门股票获取"""
    print("🔥 演示3: 获取近期热门股票")
    print("=" * 50)

    trending = get_trending_stocks(days_back=3, min_mentions=5)

    print(f"发现 {len(trending)} 只热门股票:")
    for i, stock in enumerate(trending[:5]):
        print(
            f"{i + 1}. {stock['ticker']} - {stock['company_name']} "
            f"(提及: {stock['total_mentions']}, 热度: {stock['total_popularity_score']:.1f})"
        )

    print()


def demo_stock_comparison():
    """演示股票对比"""
    print("⚔️ 演示4: 多只股票热度对比")
    print("=" * 50)

    # 对比几只科技股
    tech_stocks = ["AAPL", "GOOGL", "MSFT", "TSLA", "NVDA"]
    comparison = compare_stock_popularity(tickers=tech_stocks, days_back=7)

    print(f"对比结果 (分析周期: {comparison['analysis_period_days']} 天):")
    print(f"获胜者: {comparison['winner']}")
    print()
    print("详细排名:")
    for i, (ticker, data) in enumerate(comparison["rankings"]):
        print(f"{i + 1}. {ticker} - {data['company_name']}")
        print(f"   提及: {data['mentions']}, 热度: {data['popularity_score']:.1f}")

    print()


def demo_advanced_analysis():
    """演示高级分析功能"""
    print("🔬 演示5: 高级分析功能")
    print("=" * 50)

    # 使用分析器类进行更详细的分析
    analyzer = StockPopularityAnalyzer()

    # 分析特定股票的subreddit分布
    ticker = "TSLA"
    analysis = analyzer.analyze_stock_popularity(ticker, days_back=7)

    print(f"📈 {ticker} 详细分析:")
    print(f"总提及: {analysis['total_mentions']}")
    print(f"总热度: {analysis['total_popularity_score']:.2f}")
    print()
    print("各subreddit分布:")

    for subreddit_name, data in analysis["subreddit_breakdown"].items():
        if data["mentions"] > 0:
            print(
                f"  r/{subreddit_name}: {data['mentions']} 次提及, "
                f"热度 {data['popularity_score']:.1f}"
            )

    print()
    print("热门帖子示例:")
    for i, post in enumerate(analysis["top_posts"][:3]):
        print(f"  {i + 1}. {post['title'][:50]}...")
        print(
            f"     (👍{post['upvotes']} 💬{post['comments']} "
            f"相关度:{post['relevance']:.2f})"
        )

    print()


def demo_full_workflow():
    """演示完整工作流：下载+分析"""
    print("🚀 演示6: 完整工作流 (下载+分析)")
    print("=" * 50)
    print("注意: 此演示需要Reddit API凭证")

    # 检查是否有Reddit API凭证
    if not (os.getenv("REDDIT_CLIENT_ID") and os.getenv("REDDIT_CLIENT_SECRET")):
        print("⚠️ 未找到Reddit API凭证，跳过下载演示")
        print("请设置REDDIT_CLIENT_ID和REDDIT_CLIENT_SECRET环境变量")
        return

    # 选择几只股票进行完整分析
    target_stocks = ["AAPL"]

    try:
        result = download_and_analyze_stocks(
            tickers=target_stocks,
            limit_per_subreddit=100,  # 减少下载量以加快演示
            analysis_days=7,
        )

        print("✅ 完整工作流完成!")
        print(f"📊 {result}")

    except Exception as e:
        print(f"❌ 演示失败: {e}")
        print("这可能是由于网络连接或API配置问题")


def main():
    """主函数"""
    print("🎉 Reddit股票热度分析演示")
    print("=" * 60)
    print()

    # 检查数据目录是否存在
    data_dir = Path("data/reddit_data")
    if not data_dir.exists():
        print("⚠️ 未找到Reddit数据目录")
        print("请先运行数据下载功能或手动创建测试数据")
        print(
            "示例命令: python -m tradingagents.dataflows.reddit_utils --category company_news"
        )
        print()

    try:
        # 运行各种演示
        # demo_single_stock_analysis()
        # demo_stock_ranking()
        # demo_trending_stocks()
        # demo_stock_comparison()
        # demo_advanced_analysis()
        demo_full_workflow()

        print("🎊 所有演示完成!")
        print()
        print("💡 使用提示:")
        print("1. 确保定期更新Reddit数据以获取最新热度信息")
        print("2. 可以调整min_relevance参数来过滤不相关的讨论")
        print("3. 使用不同的days_back参数来分析不同时间段的趋势")
        print("4. 结合其他数据源进行更全面的分析")

    except Exception as e:
        print(f"❌ 演示过程中出错: {e}")
        print("这可能是由于缺少数据文件或其他配置问题")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
