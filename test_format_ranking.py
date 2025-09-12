#!/usr/bin/env python3
"""
测试格式化排行榜功能
"""

import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))


def test_format_ranking():
    """测试格式化排行榜功能"""
    try:
        from tradingagents.dataflows.reddit_utils import format_reddit_stock_ranking

        print("🧪 测试格式化排行榜功能...")

        # 测试单只股票，包含完整信息
        ranking_text = format_reddit_stock_ranking(
            tickers=["AAPL"],
            days_back=3,
            top_n=5,
            show_details=True,
            include_full_posts=True,
        )

        print("📊 生成的排行榜文本:")
        print("=" * 80)
        print(ranking_text)
        print("=" * 80)

        print(f"\n✅ 成功生成！文本长度: {len(ranking_text)} 字符")
        print(f"📝 行数: {len(ranking_text.split(chr(10)))}")

        # 保存到文件供后续分析
        output_file = Path("reddit_ranking_output.txt")
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(ranking_text)
        print(f"💾 已保存到: {output_file}")

        return True

    except Exception as e:
        print(f"❌ 测试失败: {e}")
        return False


def test_analyzer_format():
    """测试分析器的格式化功能"""
    try:
        from tradingagents.dataflows.reddit_utils import StockPopularityAnalyzer

        print("\n🧪 测试分析器格式化功能...")

        analyzer = StockPopularityAnalyzer()

        # 生成排行榜
        ranking_result = analyzer.generate_stock_popularity_ranking(
            tickers=["AAPL"], days_back=7, top_n=5
        )

        # 格式化为字符串
        formatted_text = analyzer.format_popularity_ranking(
            ranking_result, show_details=True, include_full_posts=True
        )

        print("📊 分析器格式化结果:")
        print("-" * 50)
        print(formatted_text)
        print("-" * 50)

        print(f"✅ 分析器格式化成功！长度: {len(formatted_text)}")

        return True

    except Exception as e:
        print(f"❌ 分析器测试失败: {e}")
        return False


def main():
    """主测试函数"""
    print("🔍 Reddit排行榜格式化功能测试")
    print("=" * 50)

    tests = [test_format_ranking, test_analyzer_format]

    passed = 0

    for test_func in tests:
        try:
            if test_func():
                passed += 1
        except Exception as e:
            print(f"❌ 测试异常: {e}")

    print(f"\n📊 测试结果: {passed}/{len(tests)} 通过")

    if passed == len(tests):
        print("🎉 所有测试通过！格式化功能可以使用。")
        print("\n💡 使用示例:")
        print("```python")
        print(
            "from tradingagents.dataflows.reddit_utils import format_reddit_stock_ranking"
        )
        print("")
        print("# 生成格式化的排行榜文本")
        print("ranking_text = format_reddit_stock_ranking(")
        print("    tickers=['AAPL', 'TSLA'], ")
        print("    days_back=7, ")
        print("    show_details=True, ")
        print("    include_full_posts=True")
        print(")")
        print("")
        print("# 将文本发送给LLM分析")
        print("# llm_analysis = send_to_llm(ranking_text)")
        print("```")
    else:
        print("⚠️ 部分测试失败，请检查实现。")

    return 0 if passed == len(tests) else 1


if __name__ == "__main__":
    sys.exit(main())
