#!/usr/bin/env python3
"""
测试 Google Gemini 新闻获取功能
"""

import os
import sys
from datetime import datetime

# 添加项目路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))


def test_gemini_api_key():
    """测试 Google API 密钥是否配置"""
    google_api_key = os.getenv("GOOGLE_API_KEY")

    if not google_api_key:
        print("❌ 未找到 GOOGLE_API_KEY 环境变量")
        print("请在 .env 文件中配置:")
        print("GOOGLE_API_KEY=your_google_api_key_here")
        return False
    else:
        print(f"✅ Google API 密钥已配置: {google_api_key[:10]}...")
        return True


def test_gemini_news_function():
    """测试 Gemini 新闻获取函数"""
    try:
        from tradingagents.dataflows.interface import get_global_news_gemini

        # 使用当前日期进行测试
        curr_date = datetime.now().strftime("%Y-%m-%d")
        print(f"\n🧪 测试 get_global_news_gemini 函数，日期: {curr_date}")

        # 调用函数
        result = get_global_news_gemini(curr_date)

        if result and len(result) > 100:  # 检查是否有有意义的返回内容
            print("✅ Gemini 新闻获取功能测试成功")
            print(f"📝 返回内容长度: {len(result)} 字符")
            print("\n📄 部分内容预览:")
            print("=" * 50)
            print(result[:500] + "..." if len(result) > 500 else result)
            print("=" * 50)
            return True
        else:
            print(f"❌ Gemini 返回内容异常: {result}")
            return False

    except Exception as e:
        print(f"❌ Gemini 新闻获取功能测试失败: {e}")
        return False


def main():
    print("🧪 Google Gemini 新闻功能测试")
    print("=" * 50)

    # 测试 API 密钥
    if not test_gemini_api_key():
        return

    # 测试功能
    if test_gemini_news_function():
        print("\n🎉 所有测试通过！")
    else:
        print("\n❌ 测试失败，请检查配置")


if __name__ == "__main__":
    main()
