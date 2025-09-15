from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.agents import create_react_agent, AgentExecutor
from langchain import hub
import time
import json
import traceback

# 导入分析模块日志装饰器
from tradingagents.utils.tool_logging import log_analyst_module

# 导入统一日志系统
from tradingagents.utils.logging_init import get_logger

logger = get_logger("default")

# 导入Google工具调用处理器
from tradingagents.agents.utils.google_tool_handler import GoogleToolCallHandler


def _get_company_name(ticker: str, market_info: dict) -> str:
    """
    根据股票代码获取公司名称

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
                    f"📊 [DEBUG] 从统一接口获取中国股票名称: {ticker} -> {company_name}"
                )
                return company_name
            else:
                logger.warning(f"⚠️ [DEBUG] 无法从统一接口解析股票名称: {ticker}")
                return f"股票代码{ticker}"

        elif market_info["is_hk"]:
            # 港股：使用改进的港股工具
            try:
                from tradingagents.dataflows.improved_hk_utils import (
                    get_hk_company_name_improved,
                )

                company_name = get_hk_company_name_improved(ticker)
                logger.debug(
                    f"📊 [DEBUG] 使用改进港股工具获取名称: {ticker} -> {company_name}"
                )
                return company_name
            except Exception as e:
                logger.debug(f"📊 [DEBUG] 改进港股工具获取名称失败: {e}")
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
            logger.debug(f"📊 [DEBUG] 美股名称映射: {ticker} -> {company_name}")
            return company_name

        else:
            return f"股票{ticker}"

    except Exception as e:
        logger.error(f"❌ [DEBUG] 获取公司名称失败: {e}")
        return f"股票{ticker}"


def create_market_analyst_react(llm, toolkit):
    """使用ReAct Agent模式的市场分析师（适用于通义千问）"""

    @log_analyst_module("market_react")
    def market_analyst_react_node(state):
        logger.debug(f"📈 [DEBUG] ===== ReAct市场分析师节点开始 =====")

        current_date = state["trade_date"]
        ticker = state["company_of_interest"]

        logger.debug(f"📈 [DEBUG] 输入参数: ticker={ticker}, date={current_date}")

        # 检查是否为中国股票
        def is_china_stock(ticker_code):
            import re

            return re.match(r"^\d{6}$", str(ticker_code))

        is_china = is_china_stock(ticker)
        logger.debug(f"📈 [DEBUG] 股票类型检查: {ticker} -> 中国A股: {is_china}")

        if toolkit.config["online_tools"]:
            # 在线模式，使用ReAct Agent
            if is_china:
                logger.info(f"📈 [市场分析师] 使用ReAct Agent分析中国股票")

                # 创建中国股票数据工具
                from langchain_core.tools import BaseTool

                class ChinaStockDataTool(BaseTool):
                    name: str = "get_china_stock_data"
                    description: str = f"获取中国A股股票{ticker}的市场数据和技术指标（优化缓存版本）。直接调用，无需参数。"

                    def _run(self, query: str = "") -> str:
                        try:
                            logger.debug(
                                f"📈 [DEBUG] ChinaStockDataTool调用，股票代码: {ticker}"
                            )
                            # 使用优化的缓存数据获取
                            from tradingagents.dataflows.optimized_china_data import (
                                get_china_stock_data_cached,
                            )

                            return get_china_stock_data_cached(
                                symbol=ticker,
                                start_date="2025-05-28",
                                end_date=current_date,
                                force_refresh=False,
                            )
                        except Exception as e:
                            logger.error(f"❌ 优化A股数据获取失败: {e}")
                            # 备用方案：使用原始API
                            try:
                                return toolkit.get_china_stock_data.invoke(
                                    {
                                        "stock_code": ticker,
                                        "start_date": "2025-05-28",
                                        "end_date": current_date,
                                    }
                                )
                            except Exception as e2:
                                return f"获取股票数据失败: {str(e2)}"

                tools = [ChinaStockDataTool()]
                query = f"""请对中国A股股票{ticker}进行详细的技术分析。

执行步骤：
1. 使用get_china_stock_data工具获取股票市场数据
2. 基于获取的真实数据进行深入的技术指标分析
3. 直接输出完整的技术分析报告内容

重要要求：
- 必须输出完整的技术分析报告内容，不要只是描述报告已完成
- 报告必须基于工具获取的真实数据进行分析
- 报告长度不少于800字
- 包含具体的数据、指标数值和专业分析

报告格式应包含：
## 股票基本信息
## 技术指标分析
## 价格趋势分析
## 成交量分析
## 市场情绪分析
## 投资建议"""
            else:
                logger.info(f"📈 [市场分析师] 使用ReAct Agent分析美股/港股")

                # 创建美股数据工具
                from langchain_core.tools import BaseTool

                class USStockDataTool(BaseTool):
                    name: str = "get_us_stock_data"
                    description: str = f"获取美股/港股{ticker}的市场数据和技术指标（优化缓存版本）。直接调用，无需参数。"

                    def _run(self, query: str = "") -> str:
                        try:
                            logger.debug(
                                f"📈 [DEBUG] USStockDataTool调用，股票代码: {ticker}"
                            )
                            # 使用优化的缓存数据获取
                            from tradingagents.dataflows.optimized_us_data import (
                                get_us_stock_data_cached,
                            )

                            return get_us_stock_data_cached(
                                symbol=ticker,
                                start_date="2025-05-28",
                                end_date=current_date,
                                force_refresh=False,
                            )
                        except Exception as e:
                            logger.error(f"❌ 优化美股数据获取失败: {e}")
                            # 备用方案：使用原始API
                            try:
                                return toolkit.get_YFin_data_online.invoke(
                                    {
                                        "symbol": ticker,
                                        "start_date": "2025-05-28",
                                        "end_date": current_date,
                                    }
                                )
                            except Exception as e2:
                                return f"获取股票数据失败: {str(e2)}"

                class FinnhubNewsTool(BaseTool):
                    name: str = "get_finnhub_news"
                    description: str = f"获取美股{ticker}的最新新闻和市场情绪（通过FINNHUB API）。直接调用，无需参数。"

                    def _run(self, query: str = "") -> str:
                        try:
                            logger.debug(
                                f"📈 [DEBUG] FinnhubNewsTool调用，股票代码: {ticker}"
                            )
                            return toolkit.get_finnhub_news.invoke(
                                {
                                    "ticker": ticker,
                                    "start_date": "2025-05-28",
                                    "end_date": current_date,
                                }
                            )
                        except Exception as e:
                            return f"获取新闻数据失败: {str(e)}"

                tools = [USStockDataTool(), FinnhubNewsTool()]
                query = f"""请对美股{ticker}进行详细的技术分析。

执行步骤：
1. 使用get_us_stock_data工具获取股票市场数据和技术指标（通过FINNHUB API）
2. 使用get_finnhub_news工具获取最新新闻和市场情绪
3. 基于获取的真实数据进行深入的技术指标分析
4. 直接输出完整的技术分析报告内容

重要要求：
- 必须输出完整的技术分析报告内容，不要只是描述报告已完成
- 报告必须基于工具获取的真实数据进行分析
- 报告长度不少于800字
- 包含具体的数据、指标数值和专业分析
- 结合新闻信息分析市场情绪

报告格式应包含：
## 股票基本信息
## 技术指标分析
## 价格趋势分析
## 成交量分析
## 新闻和市场情绪分析
## 投资建议"""

            try:
                # 创建ReAct Agent
                prompt = hub.pull("hwchase17/react")
                agent = create_react_agent(llm, tools, prompt)
                agent_executor = AgentExecutor(
                    agent=agent,
                    tools=tools,
                    verbose=True,
                    handle_parsing_errors=True,
                    max_iterations=10,  # 增加到10次迭代，确保有足够时间完成分析
                    max_execution_time=180,  # 增加到3分钟，给更多时间生成详细报告
                )

                logger.debug(f"📈 [DEBUG] 执行ReAct Agent查询...")
                result = agent_executor.invoke({"input": query})

                report = result["output"]
                logger.info(f"📈 [市场分析师] ReAct Agent完成，报告长度: {len(report)}")

            except Exception as e:
                logger.error(f"❌ [DEBUG] ReAct Agent失败: {str(e)}")
                report = f"ReAct Agent市场分析失败: {str(e)}"
        else:
            # 离线模式，使用原有逻辑
            report = "离线模式，暂不支持"

        logger.debug(f"📈 [DEBUG] ===== ReAct市场分析师节点结束 =====")

        return {
            "messages": [("assistant", report)],
            "market_report": report,
        }

    return market_analyst_react_node


def create_market_analyst(llm, toolkit):
    def market_analyst_node(state):
        logger.info(f"📈 [DEBUG] ===== 市场分析师节点开始 =====")

        current_date = state["trade_date"]
        ticker = state["company_of_interest"]

        logger.debug(f"📈 [DEBUG] 输入参数: ticker={ticker}, date={current_date}")
        logger.debug(
            f"📈 [DEBUG] 当前状态中的消息数量: {len(state.get('messages', []))}"
        )
        logger.debug(f"📈 [DEBUG] 现有市场报告: {state.get('market_report', 'None')}")

        # 根据股票代码格式选择数据源
        from tradingagents.utils.stock_utils import StockUtils

        market_info = StockUtils.get_market_info(ticker)

        logger.debug(
            f"📈 [DEBUG] 股票类型检查: {ticker} -> {market_info['market_name']} ({market_info['currency_name']})"
        )

        # 获取公司名称
        company_name = _get_company_name(ticker, market_info)
        logger.info(
            f"📈 [DEBUG] 公司名称: {ticker} -> {company_name} traceback: {traceback.extract_stack()} "
        )

        if toolkit.config["online_tools"]:
            # 使用统一的市场数据工具，工具内部会自动识别股票类型
            logger.info(f"📊 [市场分析师] 使用统一市场数据工具，自动识别股票类型")
            tools = [
                toolkit.get_stock_market_data_unified,
                toolkit.get_YFin_data_online,
            ]
            # 安全地获取工具名称用于调试
            tool_names_debug = []
            for tool in tools:
                if hasattr(tool, "name"):
                    tool_names_debug.append(tool.name)
                elif hasattr(tool, "__name__"):
                    tool_names_debug.append(tool.__name__)
                else:
                    tool_names_debug.append(str(tool))
            logger.debug(f"📊 [DEBUG] 选择的工具: {tool_names_debug}")
            logger.debug(
                f"📊 [DEBUG] 🔧 统一工具将自动处理: {market_info['market_name']}"
            )
        else:
            tools = [
                toolkit.get_YFin_data_online,
                # toolkit.get_stockstats_indicators_report,
            ]

        # 统一的系统提示，适用于所有股票类型
        system_message = f"""你是一位资深的股票技术分析专家。你必须对{company_name}（股票代码：{ticker}）进行深入全面的技术分析。

**股票信息：**
- 公司名称：{company_name}
- 股票代码：{ticker}
- 所属市场：{market_info["market_name"]}
- 计价货币：{market_info["currency_name"]}（{market_info["currency_symbol"]}）

**工具调用指令：**
你有一个工具叫做get_stock_market_data_unified，你必须立即调用这个工具来获取{company_name}（{ticker}）的市场数据。
不要说你将要调用工具，直接调用工具。

你还有一个工具叫做get_YFin_data_online，你必须立即调用这个工具来获取{company_name}（{ticker}）的市场数据。
不要说你将要调用工具，直接调用工具。

**分析要求（必须详细完整）：**
1. 调用工具后，基于获取的真实数据进行深度技术分析，必须使用到get_YFin_data_online工具返回的数据
2. 详细分析移动平均线系统（多条均线的排列、交叉、支撑阻力作用）
3. 深入解读MACD指标（MACD线、信号线、柱状图的变化和意义）
4. 全面分析RSI（超买超卖、背离、区间突破）
5. 详细分析布林带（价格位置、带宽变化、突破信号）
6. 成交量分析（量价关系、异常放量、资金流向）
7. K线形态分析（重要形态、反转信号、持续信号）
8. 考虑{market_info["market_name"]}市场特点进行分析
9. 提供具体的数值和专业分析
10. 给出明确详细的投资建议（买入/持有/卖出，目标价位，止损位）
11. 所有价格数据使用{market_info["currency_name"]}（{market_info["currency_symbol"]}）表示
12. 标注清楚时间数据时间范围

**重要：分析报告必须详尽深入，长度不少于2000字，体现专业技术分析师的水准。**

**输出格式：**
## 📊 股票基本信息和市场概况
- 公司名称：{company_name}
- 股票代码：{ticker}
- 所属市场：{market_info["market_name"]}

## 📈 价格走势和趋势分析
## 📊 技术指标综合解读
## 📉 支撑阻力位和关键点位分析  
## 📊 成交量和资金流向分析
## 💭 综合投资建议和风险评估

请使用中文，基于真实数据进行详细深入的专业分析。确保在分析中正确使用公司名称"{company_name}"和股票代码"{ticker}"。**请生成完整详细的技术分析报告，展现专业分析师的深度和广度。**"""

        prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    "你是一位专业的股票技术分析师，与其他分析师协作。"
                    "使用提供的工具来获取和分析股票数据。"
                    "如果你无法完全回答，没关系；其他分析师会从不同角度继续分析。"
                    "执行你能做的技术分析工作来取得进展。"
                    "如果你有明确的技术面投资建议：**买入/持有/卖出**，"
                    "请在你的回复中明确标注，但不要使用'最终交易建议'前缀，因为最终决策需要综合所有分析师的意见。"
                    "你可以使用以下工具：{tool_names}。\n{system_message}"
                    "供你参考，当前日期是{current_date}。"
                    "我们要分析的是{company_name}（股票代码：{ticker}）。"
                    "请确保所有分析都使用中文，并在分析中正确区分公司名称和股票代码。",
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
        prompt = prompt.partial(company_name=company_name)

        chain = prompt | llm.bind_tools(tools)

        result = chain.invoke(state["messages"])
        # print(f"📊 [市场分析师] 结果: {result}")

        # 使用统一的Google工具调用处理器
        if GoogleToolCallHandler.is_google_model(llm):
            logger.info(f"📊 [市场分析师] 检测到Google模型，使用统一工具调用处理器")

            # 创建分析提示词
            analysis_prompt_template = GoogleToolCallHandler.create_analysis_prompt(
                ticker=ticker,
                company_name=company_name,
                analyst_type="市场分析",
                specific_requirements="重点关注市场数据、价格走势、交易量变化等市场指标。",
            )

            # 处理Google模型工具调用
            report, messages = GoogleToolCallHandler.handle_google_tool_calls(
                result=result,
                llm=llm,
                tools=tools,
                state=state,
                analysis_prompt_template=analysis_prompt_template,
                analyst_name="市场分析师",
                ticker=ticker,  # 传递ticker参数
            )

            return {
                "messages": [result],
                "market_report": report,
            }
        else:
            # 非Google模型的处理逻辑
            logger.debug(
                f"📊 [DEBUG] 非Google模型 ({llm.__class__.__name__})，使用标准处理逻辑"
            )

            # 处理市场分析报告
            if len(result.tool_calls) == 0:
                # 没有工具调用，直接使用LLM的回复
                report = result.content
                logger.info(f"📊 [市场分析师] 直接回复，长度: {len(report)}")
                logger.debug(f"📊 [DEBUG] 直接回复内容预览: {report[:200]}...")
            else:
                # 有工具调用，执行工具并生成完整分析报告
                logger.info(
                    f"📊 [市场分析师] 工具调用: {[call.get('name', 'unknown') for call in result.tool_calls]}"
                )

                try:
                    # 执行工具调用
                    from langchain_core.messages import ToolMessage, HumanMessage

                    tool_messages = []
                    for tool_call in result.tool_calls:
                        tool_name = tool_call.get("name")
                        tool_args = tool_call.get("args", {})
                        tool_id = tool_call.get("id")

                        logger.debug(
                            f"📊 [DEBUG] 执行工具: {tool_name}, 参数: {tool_args}"
                        )

                        # 找到对应的工具并执行
                        tool_result = None
                        for tool in tools:
                            # 安全地获取工具名称进行比较
                            current_tool_name = None
                            if hasattr(tool, "name"):
                                current_tool_name = tool.name
                            elif hasattr(tool, "__name__"):
                                current_tool_name = tool.__name__

                            if current_tool_name == tool_name:
                                try:
                                    if tool_name == "get_china_stock_data":
                                        # 中国股票数据工具
                                        tool_result = tool.invoke(tool_args)
                                    else:
                                        # 其他工具
                                        tool_result = tool.invoke(tool_args)
                                    logger.debug(
                                        f"📊 [DEBUG] 工具执行成功，结果长度: {len(str(tool_result))}"
                                    )
                                    break
                                except Exception as tool_error:
                                    logger.error(
                                        f"❌ [DEBUG] 工具执行失败: {tool_error}"
                                    )
                                    tool_result = f"工具执行失败: {str(tool_error)}"

                        if tool_result is None:
                            tool_result = f"未找到工具: {tool_name}"

                        # 创建工具消息
                        tool_message = ToolMessage(
                            content=str(tool_result), tool_call_id=tool_id
                        )
                        tool_messages.append(tool_message)

                    # 基于工具结果生成完整分析报告
                    analysis_prompt = f"""现在请基于上述工具获取的真实数据，为{company_name}（{ticker}）生成一份深入详细的技术分析报告。

**重要要求：**

1. **数据充分利用**：
   - 深入分析工具返回的所有历史价格数据
   - 详细解读各项技术指标的数值和变化趋势
   - 充分利用成交量、市场情绪等所有可用数据

2. **技术分析深度**：
   - 移动平均线系统：详细分析5日、10日、20日、50日等多条均线的排列和交叉情况
   - MACD指标：深入解读MACD线、信号线、柱状图的变化和意义
   - RSI相对强弱指标：分析超买超卖情况和背离现象
   - 布林带：分析价格在布林带中的位置和突破情况
   - 成交量分析：量价关系、放量突破、缩量调整等
   - K线形态：重要的K线组合和形态特征

3. **趋势和支撑阻力**：
   - 详细识别主要趋势线和重要的支撑阻力位
   - 分析价格突破的有效性和持续性
   - 评估当前位置的风险收益比

4. **市场情绪和资金流向**：
   - 基于成交量和价格变化分析市场参与者行为
   - 评估多空力量对比和市场情绪变化

5. **投资策略制定**：
   - 给出明确的买入/持有/卖出建议
   - 设定具体的目标价位和止损位
   - 提供不同时间周期的操作建议（短线、中线、长线）
   - 详细说明投资风险和注意事项

6. **报告要求**：
   - 报告长度不少于2000字，确保分析的深度和广度
   - 使用专业的技术分析术语
   - 每个分析结论都要有具体数据支撑
   - 逻辑清晰，结构完整

**分析框架：**
请按以下结构进行深入分析：

## 📊 股票基本信息和市场概况
## 📈 价格走势和趋势分析  
## 📊 技术指标综合解读
## 📉 支撑阻力位和关键点位分析
## 📊 成交量和资金流向分析
## 💭 综合投资建议和风险评估

**请确保每个部分都有充实的内容和专业的分析，体现出技术分析的专业性和实用性。**

请现在开始生成完整的技术分析报告："""

                    # 构建完整的消息序列
                    messages = (
                        state["messages"]
                        + [result]
                        + tool_messages
                        + [HumanMessage(content=analysis_prompt)]
                    )

                    # 生成最终分析报告
                    final_result = llm.invoke(messages)
                    report = final_result.content

                    logger.info(
                        f"📊 [市场分析师] 生成完整分析报告，长度: {len(report)}"
                    )

                    # 返回包含工具调用和最终分析的完整消息序列
                    return {
                        "messages": [result] + tool_messages + [final_result],
                        "market_report": report,
                    }

                except Exception as e:
                    logger.error(f"❌ [市场分析师] 工具执行或分析生成失败: {e}")
                    traceback.print_exc()

                    # 降级处理：返回工具调用信息
                    report = f"市场分析师调用了工具但分析生成失败: {[call.get('name', 'unknown') for call in result.tool_calls]}"

                    return {
                        "messages": [result],
                        "market_report": report,
                    }

            return {
                "messages": [result],
                "market_report": report,
            }

    return market_analyst_node
