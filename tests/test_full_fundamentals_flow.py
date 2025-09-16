#!/usr/bin/env python3
"""
完整基本面分析流程测试
"""

import os
import sys

from pathlib import Path
from dotenv import load_dotenv

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent  # 向上一级到达项目根目录
sys.path.insert(0, str(project_root))

print(os.getcwd())
print(os.getenv("GOOGLE_API_KEY"))

# 加载环境变量
load_dotenv(project_root / ".env", override=True)


def test_full_fundamentals_flow():
    """测试完整的基本面分析流程"""
    print("\n🔍 完整基本面分析流程测试")
    print("=" * 80)

    # 测试分众传媒 002027
    test_ticker = "AAPL"
    print(f"📊 测试股票代码: {test_ticker} (分众传媒)")

    try:
        # 设置日志级别
        from tradingagents.utils.logging_init import get_logger

        logger = get_logger("default")
        logger.setLevel("INFO")

        print(f"\n🔧 步骤1: 初始化LLM和工具包...")

        # 导入必要的模块
        from tradingagents.agents.analysts.fundamentals_analyst import (
            create_fundamentals_analyst,
        )
        from tradingagents.agents.utils.agent_utils import Toolkit
        from langchain_google_genai import ChatGoogleGenerativeAI
        from tradingagents.default_config import DEFAULT_CONFIG
        from langchain_core.messages import HumanMessage

        # 获取LLM实例
        # 创建配置
        config = DEFAULT_CONFIG.copy()
        config["online_tools"] = False

        # 创建Gemini LLM
        llm = ChatGoogleGenerativeAI(
            model="gemini-2.5-pro",
            temperature=0.1,
            max_tokens=16000,
            google_api_key=os.getenv("GOOGLE_API_KEY"),
        )

        print(f"✅ LLM初始化完成: {type(llm).__name__}")

        # 创建工具包
        toolkit = Toolkit()
        print(f"✅ 工具包初始化完成")

        print(f"\n🔧 步骤2: 创建基本面分析师...")

        # 创建基本面分析师
        fundamentals_analyst = create_fundamentals_analyst(llm, toolkit)
        print(f"✅ 基本面分析师创建完成")

        print(f"\n🔧 步骤3: 准备分析状态...")

        # 创建分析状态
        state = {
            "company_of_interest": test_ticker,
            "trade_date": "2025-09-15",
            "messages": [HumanMessage(content="分析AAPL的基本面指标")],
        }

        print(f"✅ 分析状态准备完成")
        print(f"   - 股票代码: {state['company_of_interest']}")
        print(f"   - 交易日期: {state['trade_date']}")
        print(f"   - 消息数量: {len(state['messages'])}")

        print(f"\n🔧 步骤4: 执行基本面分析...")

        # 执行基本面分析
        result = fundamentals_analyst(state)

        print(f"\n✅ 基本面分析执行完成")
        print(f"📊 返回结果类型: {type(result)}")

        # 检查返回结果
        if isinstance(result, dict):
            if "fundamentals_report" in result:
                report = result["fundamentals_report"]
                print(f"📄 基本面报告长度: {len(report) if report else 0}")
                print(f"📄 基本面报告: {report}")
                # 检查报告中的股票代码

            else:
                print("❌ 返回结果中没有 fundamentals_report")
                print(f"   返回结果键: {list(result.keys())}")
        else:
            print(f"❌ 返回结果类型不正确: {type(result)}")
            if hasattr(result, "content"):
                print(f"   内容: {result.content[:200]}...")

        return True

    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("🚀 开始完整基本面分析流程测试")

    # 执行完整流程测试
    success = test_full_fundamentals_flow()

    if success:
        print("\n✅ 测试完成")
    else:
        print("\n❌ 测试失败")
