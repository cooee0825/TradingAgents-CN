from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

# 导入统一日志系统和分析模块日志装饰器
from tradingagents.utils.logging_init import get_logger
from tradingagents.utils.tool_logging import log_analyst_module

# 导入Google工具调用处理器
from tradingagents.agents.utils.google_tool_handler import GoogleToolCallHandler

logger = get_logger("analysts.social_media")


def _get_company_name_for_social_media(ticker: str, market_info: dict) -> str:
    """
    为社交媒体分析师获取公司名称

    Args:
        ticker: 股票代码
        market_info: 市场信息字典

    Returns:
        str: 公司名称
    """
    try:
        if market_info["is_china"]:
            # 中国A股：使用统一接口获取股票信息
            from tradingagents.dataflows.interface import get_china_stock_info_unified

            stock_info = get_china_stock_info_unified(ticker)

            # 解析股票名称
            if "股票名称:" in stock_info:
                company_name = stock_info.split("股票名称:")[1].split("\n")[0].strip()
                logger.debug(
                    f"📊 [社交媒体分析师] 从统一接口获取中国股票名称: {ticker} -> {company_name}"
                )
                return company_name
            else:
                logger.warning(
                    f"⚠️ [社交媒体分析师] 无法从统一接口解析股票名称: {ticker}"
                )
                return f"股票代码{ticker}"

        elif market_info["is_hk"]:
            # 港股：使用改进的港股工具
            try:
                from tradingagents.dataflows.improved_hk_utils import (
                    get_hk_company_name_improved,
                )

                company_name = get_hk_company_name_improved(ticker)
                logger.debug(
                    f"📊 [社交媒体分析师] 使用改进港股工具获取名称: {ticker} -> {company_name}"
                )
                return company_name
            except Exception as e:
                logger.debug(f"📊 [社交媒体分析师] 改进港股工具获取名称失败: {e}")
                # 降级方案：生成友好的默认名称
                clean_ticker = ticker.replace(".HK", "").replace(".hk", "")
                return f"港股{clean_ticker}"

        elif market_info["is_us"]:
            # 美股：使用简单映射或返回代码
            us_stock_names = {
                "AAPL": "苹果公司",
                "TSLA": "特斯拉",
                "NVDA": "英伟达",
                "MSFT": "微软",
                "GOOGL": "谷歌",
                "AMZN": "亚马逊",
                "META": "Meta",
                "NFLX": "奈飞",
            }

            company_name = us_stock_names.get(ticker.upper(), f"美股{ticker}")
            logger.debug(
                f"📊 [社交媒体分析师] 美股名称映射: {ticker} -> {company_name}"
            )
            return company_name

        else:
            return f"股票{ticker}"

    except Exception as e:
        logger.error(f"❌ [社交媒体分析师] 获取公司名称失败: {e}")
        return f"股票{ticker}"


def create_social_media_analyst(llm, toolkit):
    @log_analyst_module("social_media")
    def social_media_analyst_node(state):
        current_date = state["trade_date"]
        ticker = state["company_of_interest"]

        # 获取股票市场信息
        from tradingagents.utils.stock_utils import StockUtils

        market_info = StockUtils.get_market_info(ticker)

        # 获取公司名称
        company_name = _get_company_name_for_social_media(ticker, market_info)
        logger.info(f"[社交媒体分析师] 公司名称: {company_name}")

        if toolkit.config["online_tools"]:
            tools = [toolkit.get_reddit_stock_info]
            tools = []
        else:
            # 使用美股社交媒体数据源，主要是Reddit
            tools = [
                # toolkit.get_reddit_stock_info,
            ]

        system_message = """您是一位专业的美股市场社交媒体和投资情绪分析师，负责分析美股投资者对特定股票的讨论和情绪变化。

您的主要职责包括：
1. 分析美国主要社交媒体平台的投资者情绪（如Reddit、Twitter、StockTwits等）
2. 监控美国财经媒体和新闻对股票的报道倾向
3. 识别影响股价的热点事件和市场传言
4. 评估散户与机构投资者的观点差异
5. 分析美联储政策变化对投资者情绪的影响
6. 评估情绪变化对股价的潜在影响

重点关注平台：
- 社交媒体：Reddit (r/wallstreetbets, r/investing, r/stocks)、Twitter财经KOL、StockTwits
- 财经新闻：CNBC、Bloomberg、Yahoo Finance、MarketWatch、The Wall Street Journal
- 投资社区：Reddit投资板块、Discord投资群、Seeking Alpha评论区
- 专业分析：各大投行研报、Motley Fool、财经博客、YouTube财经频道

分析要点：
- 投资者情绪的变化趋势和原因
- 关键意见领袖(KOL)和财经大V的观点和影响力
- 热点事件对股价预期的影响
- 美联储政策解读和市场预期变化
- 散户情绪与机构观点的差异
- Meme股现象和散户抱团行为分析

📊 情绪价格影响分析要求：
- 量化投资者情绪强度（乐观/悲观程度）
- 评估情绪变化对短期股价的影响（1-5天）
- 分析散户情绪与股价走势的相关性
- 识别情绪驱动的价格支撑位和阻力位
- 提供基于情绪分析的价格预期调整
- 评估市场情绪对估值的影响程度
- 分析期权流量和散户期权活动对情绪的影响
- 不允许回复'无法评估情绪影响'或'需要更多数据'

💰 必须包含：
- 情绪指数评分（1-10分）
- 预期价格波动幅度
- 基于情绪的交易时机建议
- Reddit/Twitter热度指标分析

请撰写详细的中文分析报告，并在报告末尾附上Markdown表格总结关键发现。
注意：如果社交媒体数据获取受限，请明确说明并提供基于可用数据的替代分析建议。"""

        prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    "您是一位有用的AI助手，与其他助手协作。"
                    " 使用提供的工具来推进回答问题。"
                    " 如果您无法完全回答，没关系；具有不同工具的其他助手"
                    " 将从您停下的地方继续帮助。执行您能做的以取得进展。"
                    " 如果您或任何其他助手有最终交易提案：**买入/持有/卖出**或可交付成果，"
                    " 请在您的回应前加上最终交易提案：**买入/持有/卖出**，以便团队知道停止。"
                    " 您可以访问以下工具：{tool_names}。\n{system_message}"
                    "供您参考，当前日期是{current_date}。我们要分析的当前公司是{ticker}。请用中文撰写所有分析内容。",
                ),
                MessagesPlaceholder(variable_name="messages"),
            ]
        )

        prompt = prompt.partial(system_message=system_message)
        # 安全地获取工具名称，处理函数和工具对象
        tool_names = []
        for tool in tools:
            if hasattr(tool, "name"):
                tool_names.append(tool.name)
            elif hasattr(tool, "__name__"):
                tool_names.append(tool.__name__)
            else:
                tool_names.append(str(tool))

        prompt = prompt.partial(tool_names=", ".join(tool_names))
        prompt = prompt.partial(current_date=current_date)
        prompt = prompt.partial(ticker=ticker)

        # print(prompt)
        # print(tools)
        # print(prompt)
        chain = prompt | llm.bind_tools(tools)

        result = chain.invoke(state["messages"])

        # 使用统一的Google工具调用处理器
        if GoogleToolCallHandler.is_google_model(llm):
            logger.info("📊 [社交媒体分析师] 检测到Google模型，使用统一工具调用处理器")

            # 创建分析提示词
            analysis_prompt_template = GoogleToolCallHandler.create_analysis_prompt(
                ticker=ticker,
                company_name=company_name,
                analyst_type="社交媒体情绪分析",
                specific_requirements="重点关注投资者情绪、社交媒体讨论热度、舆论影响等。",
            )

            # 处理Google模型工具调用
            report, messages = GoogleToolCallHandler.handle_google_tool_calls(
                result=result,
                llm=llm,
                tools=[],
                state=state,
                analysis_prompt_template=analysis_prompt_template,
                analyst_name="社交媒体分析师",
            )
        else:
            # 非Google模型的处理逻辑
            logger.debug(
                f"📊 [DEBUG] 非Google模型 ({llm.__class__.__name__})，使用标准处理逻辑"
            )

            report = ""
            if len(result.tool_calls) == 0:
                report = result.content
            else:
                # 处理工具调用
                logger.info(
                    f"📊 [社交媒体分析师] 检测到 {len(result.tool_calls)} 个工具调用"
                )

                # 执行工具调用
                tool_results = []
                for tool_call in result.tool_calls:
                    tool_name = tool_call["name"]
                    tool_args = tool_call["args"]
                    logger.info(
                        f"📊 [社交媒体分析师] 调用工具: {tool_name} with args: {tool_args}"
                    )

                    # 查找对应的工具并执行
                    for tool in tools:
                        if (hasattr(tool, "name") and tool.name == tool_name) or (
                            hasattr(tool, "__name__") and tool.__name__ == tool_name
                        ):
                            try:
                                tool_result = tool.invoke(tool_args)
                                tool_results.append(
                                    {
                                        "tool_call_id": tool_call.get("id", ""),
                                        "content": str(tool_result),
                                    }
                                )
                                logger.info(
                                    f"📊 [社交媒体分析师] 工具调用成功: {tool_name}"
                                )
                                break
                            except Exception as e:
                                logger.error(
                                    f"❌ [社交媒体分析师] 工具调用失败 {tool_name}: {e}"
                                )
                                tool_results.append(
                                    {
                                        "tool_call_id": tool_call.get("id", ""),
                                        "content": f"工具调用失败: {str(e)}",
                                    }
                                )

                # 如果有工具结果，生成最终分析报告
                if tool_results:
                    # 创建包含工具结果的消息
                    from langchain_core.messages import ToolMessage, HumanMessage

                    messages_with_tools = state["messages"] + [result]
                    for tool_result in tool_results:
                        messages_with_tools.append(
                            ToolMessage(
                                content=tool_result["content"],
                                tool_call_id=tool_result["tool_call_id"],
                            )
                        )

                    # 生成分析报告
                    analysis_prompt = f"""基于以上工具调用的结果，请生成详细的{ticker}({company_name})社交媒体情绪分析报告。

请确保包含：
1. 投资者情绪分析和量化评分
2. 社交媒体讨论热度评估
3. 关键观点和影响因素
4. 基于情绪的交易建议
5. 风险提示

请用中文撰写详细分析报告。"""

                    messages_with_tools.append(HumanMessage(content=analysis_prompt))

                    # 重新调用LLM生成最终报告
                    final_result = llm.invoke(messages_with_tools)
                    report = final_result.content
                    logger.info("📊 [社交媒体分析师] 生成最终分析报告")
                else:
                    report = "工具调用失败，无法获取社交媒体数据"

        return {
            "messages": [result],
            "sentiment_report": report,
        }

    return social_media_analyst_node
