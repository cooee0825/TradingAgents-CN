from langchain_core.messages import BaseMessage, HumanMessage, ToolMessage, AIMessage
from typing import List
from typing import Annotated
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import RemoveMessage
from langchain_core.tools import tool
from datetime import date, timedelta, datetime
import functools
import pandas as pd
import os
from dateutil.relativedelta import relativedelta
from langchain_openai import ChatOpenAI
import tradingagents.dataflows.interface as interface
from tradingagents.default_config import DEFAULT_CONFIG
from langchain_core.messages import HumanMessage

# 导入统一日志系统和工具日志装饰器
from tradingagents.utils.logging_init import get_logger
from tradingagents.utils.tool_logging import log_tool_call, log_analysis_step

# 导入日志模块
from tradingagents.utils.logging_manager import get_logger

logger = get_logger("agents")


def create_msg_delete():
    def delete_messages(state):
        """Clear messages and add placeholder for Anthropic compatibility"""
        messages = state["messages"]

        # Remove all messages
        removal_operations = [RemoveMessage(id=m.id) for m in messages]

        # Add a minimal placeholder message
        placeholder = HumanMessage(content="Continue")

        return {"messages": removal_operations + [placeholder]}

    return delete_messages


class Toolkit:
    _config = DEFAULT_CONFIG.copy()

    @classmethod
    def update_config(cls, config):
        """Update the class-level configuration."""
        cls._config.update(config)

    @property
    def config(self):
        """Access the configuration."""
        return self._config

    def __init__(self, config=None):
        if config:
            self.update_config(config)

    @staticmethod
    @tool
    def get_reddit_news(
        curr_date: Annotated[str, "Date you want to get news for in yyyy-mm-dd format"],
    ) -> str:
        """
        Retrieve global news from Reddit within a specified time frame.
        Args:
            curr_date (str): Date you want to get news for in yyyy-mm-dd format
        Returns:
            str: A formatted dataframe containing the latest global news from Reddit in the specified time frame.
        """

        global_news_result = interface.get_reddit_global_news(curr_date, 7, 20)

        return global_news_result

    @staticmethod
    @tool
    def get_finnhub_news(
        ticker: Annotated[
            str,
            "Search query of a company, e.g. 'AAPL, TSM, etc.",
        ],
        start_date: Annotated[str, "Start date in yyyy-mm-dd format"],
        end_date: Annotated[str, "End date in yyyy-mm-dd format"],
    ):
        """
        Retrieve the latest news about a given stock from Finnhub within a date range
        Args:
            ticker (str): Ticker of a company. e.g. AAPL, TSM
            start_date (str): Start date in yyyy-mm-dd format
            end_date (str): End date in yyyy-mm-dd format
        Returns:
            str: A formatted dataframe containing news about the company within the date range from start_date to end_date
        """

        end_date_str = end_date

        end_date = datetime.strptime(end_date, "%Y-%m-%d")
        start_date = datetime.strptime(start_date, "%Y-%m-%d")
        look_back_days = (end_date - start_date).days

        print(f"Finnhub新闻数据3333: {ticker}, {end_date_str}, {look_back_days}")
        finnhub_news_result = interface.get_finnhub_news(
            ticker, end_date_str, look_back_days
        )

        return finnhub_news_result

    @staticmethod
    @tool
    def get_reddit_stock_info(
        ticker: Annotated[
            str,
            "Ticker of a company. e.g. AAPL, TSM",
        ],
        curr_date: Annotated[str, "Current date you want to get news for"],
    ) -> str:
        """
        Retrieve the latest news about a given stock from Reddit, given the current date.
        Args:
            ticker (str): Ticker of a company. e.g. AAPL, TSM
            curr_date (str): current date in yyyy-mm-dd format to get news for
        Returns:
            str: A formatted dataframe containing the latest news about the company on the given date
        """
        print(
            f"📊 [DEBUG] get_reddit_stock_info 被调用: ticker={ticker}, date={curr_date}"
        )
        stock_news_results = interface.get_reddit_company_news(ticker, curr_date, 7, 20)

        return stock_news_results

    @staticmethod
    @tool
    @log_tool_call(tool_name="download_reddit_company_data", log_args=True)
    def download_reddit_company_data(
        ticker: Annotated[str, "公司股票代码，如 AAPL, TSLA, MSFT"],
        category_name: Annotated[str, "数据分类名称，建议使用公司名称或ticker"] = None,
        limit_per_subreddit: Annotated[int, "每个subreddit的下载限制"] = 150,
        category_type: Annotated[str, "帖子分类"] = "hot",
        time_filter: Annotated[str, "时间筛选 (all, day, week, month, year)"] = "week",
        force_refresh: Annotated[bool, "是否强制刷新已存在的数据"] = False,
    ) -> str:
        """
        下载特定公司的Reddit讨论数据
        自动选择相关的subreddit并下载该公司的讨论帖子

        Args:
            ticker (str): 公司股票代码，如 AAPL, TSLA, MSFT
            category_name (str): 数据分类名称，默认使用ticker
            limit_per_subreddit (int): 每个subreddit的下载限制，默认150
            category_type (str): 帖子分类 (hot, new, top, rising)，默认hot
            time_filter (str): 时间筛选，仅对top有效，默认week
            force_refresh (bool): 是否强制刷新已存在的数据，默认False

        Returns:
            str: 下载结果报告
        """
        try:
            from tradingagents.dataflows.reddit_utils import download_custom_subreddits

            logger.info(f"📥 [Reddit下载工具] 开始下载 {ticker} 公司数据")

            # 设置分类名称
            if not category_name:
                category_name = f"company_{ticker.lower()}"

            # 选择与股票投资相关的subreddit
            investment_subreddits = [
                "stocks",
                "investing",
                "SecurityAnalysis",
                "ValueInvesting",
                "StockMarket",
                "wallstreetbets",
                "financialindependence",
                "dividends",
                "options",
                "pennystocks",
            ]

            # 下载数据
            success = download_custom_subreddits(
                subreddits=investment_subreddits,
                category_name=category_name,
                limit_per_subreddit=limit_per_subreddit,
                category_type=category_type,
                time_filter=time_filter,
                force_refresh=force_refresh,
            )

            if success:
                result = f"""# {ticker} Reddit数据下载完成

## 下载配置
- **股票代码**: {ticker}
- **分类名称**: {category_name}  
- **每个subreddit限制**: {limit_per_subreddit}
- **帖子类型**: {category_type}
- **时间筛选**: {time_filter}
- **强制刷新**: {force_refresh}

## 下载的subreddit
{chr(10).join([f"- r/{sub}" for sub in investment_subreddits])}

## 数据存储位置
- 路径: `data/reddit_data/{category_name}/`
- 格式: 每个subreddit保存为单独的.jsonl文件
- 总计: {len(investment_subreddits)} 个subreddit

✅ **下载成功！** 现在可以使用 `get_reddit_stock_info` 工具分析该公司的Reddit讨论数据。

💡 **提示**: 下载的数据将自动与现有的Reddit分析工具集成，无需额外配置。
"""
                logger.info(f"✅ [Reddit下载工具] {ticker} 数据下载成功")
                return result
            else:
                error_msg = f"❌ {ticker} Reddit数据下载失败，请检查网络连接和API配置"
                logger.error(f"❌ [Reddit下载工具] {error_msg}")
                return error_msg

        except Exception as e:
            error_msg = f"Reddit数据下载工具执行失败: {str(e)}"
            logger.error(f"❌ [Reddit下载工具] {error_msg}")
            return error_msg

    @staticmethod
    @tool
    @log_tool_call(tool_name="download_reddit_global_data", log_args=True)
    def download_reddit_global_data(
        categories: Annotated[str, "要下载的分类"] = "all",
        limit_per_subreddit: Annotated[int, "每个subreddit的下载限制"] = 100,
        category_type: Annotated[str, "帖子分类"] = "hot",
        time_filter: Annotated[str, "时间筛选"] = "week",
        force_refresh: Annotated[bool, "是否强制刷新"] = False,
    ) -> str:
        """
        下载全球新闻和市场相关的Reddit数据
        支持批量下载多个预配置的分类

        Args:
            categories (str): 要下载的分类，可选: all, global_news, company_news, crypto_news
            limit_per_subreddit (int): 每个subreddit的下载限制，默认100
            category_type (str): 帖子分类 (hot, new, top, rising)，默认hot
            time_filter (str): 时间筛选，仅对top有效，默认week
            force_refresh (bool): 是否强制刷新已存在的数据，默认False

        Returns:
            str: 下载结果报告
        """
        try:
            from tradingagents.dataflows.reddit_utils import download_reddit_data

            logger.info(f"🌍 [Reddit批量下载] 开始下载 {categories} 分类数据")

            # 下载数据
            results = download_reddit_data(
                category=categories,
                limit_per_subreddit=limit_per_subreddit,
                category_type=category_type,
                time_filter=time_filter,
                force_refresh=force_refresh,
            )

            # 统计结果
            successful_categories = [cat for cat, success in results.items() if success]
            failed_categories = [cat for cat, success in results.items() if not success]

            result = f"""# Reddit全球数据下载报告

## 下载配置
- **目标分类**: {categories}
- **每个subreddit限制**: {limit_per_subreddit}
- **帖子类型**: {category_type}
- **时间筛选**: {time_filter}
- **强制刷新**: {force_refresh}

## 下载结果
- **成功分类**: {len(successful_categories)}/{len(results)}
- **成功列表**: {", ".join(successful_categories) if successful_categories else "无"}
- **失败列表**: {", ".join(failed_categories) if failed_categories else "无"}

## 数据存储位置
- 路径: `data/reddit_data/`
- 格式: 按分类组织，每个subreddit保存为.jsonl文件

{"✅ **下载完成！**" if successful_categories else "❌ **下载失败！**"}

💡 **后续使用**: 下载的数据可通过 `get_reddit_news` 和 `get_reddit_stock_info` 工具进行分析。
"""

            if successful_categories:
                logger.info(
                    f"✅ [Reddit批量下载] 成功下载 {len(successful_categories)} 个分类"
                )
            else:
                logger.error(f"❌ [Reddit批量下载] 所有分类下载失败")

            return result

        except Exception as e:
            error_msg = f"Reddit批量下载工具执行失败: {str(e)}"
            logger.error(f"❌ [Reddit批量下载] {error_msg}")
            return error_msg

    @staticmethod
    @tool
    @log_tool_call(tool_name="download_reddit_custom_data", log_args=True)
    def download_reddit_custom_data(
        subreddits: Annotated[str, "subreddit列表，用逗号分隔"],
        category_name: Annotated[str, "数据分类名称"],
        limit_per_subreddit: Annotated[int, "每个subreddit的下载限制"] = 200,
        category_type: Annotated[str, "帖子分类"] = "hot",
        time_filter: Annotated[str, "时间筛选"] = "week",
        force_refresh: Annotated[bool, "是否强制刷新"] = False,
    ) -> str:
        """
        下载自定义subreddit列表的Reddit数据
        允许用户指定特定的subreddit进行数据采集

        Args:
            subreddits (str): subreddit列表，用逗号分隔，如 "wallstreetbets,investing,stocks"
            category_name (str): 数据分类名称，用于组织数据
            limit_per_subreddit (int): 每个subreddit的下载限制，默认200
            category_type (str): 帖子分类 (hot, new, top, rising)，默认hot
            time_filter (str): 时间筛选，仅对top有效，默认week
            force_refresh (bool): 是否强制刷新已存在的数据，默认False

        Returns:
            str: 下载结果报告
        """
        try:
            from tradingagents.dataflows.reddit_utils import download_custom_subreddits

            # 解析subreddit列表
            subreddit_list = [
                sub.strip() for sub in subreddits.split(",") if sub.strip()
            ]

            if not subreddit_list:
                return "❌ 错误: 请提供有效的subreddit列表"

            logger.info(f"📋 [Reddit自定义下载] 下载 {len(subreddit_list)} 个subreddit")
            logger.info(f"📋 [Reddit自定义下载] 分类: {category_name}")

            # 下载数据
            success = download_custom_subreddits(
                subreddits=subreddit_list,
                category_name=category_name,
                limit_per_subreddit=limit_per_subreddit,
                category_type=category_type,
                time_filter=time_filter,
                force_refresh=force_refresh,
            )

            if success:
                result = f"""# 自定义Reddit数据下载完成

## 下载配置
- **分类名称**: {category_name}
- **subreddit数量**: {len(subreddit_list)}
- **每个subreddit限制**: {limit_per_subreddit}
- **帖子类型**: {category_type}
- **时间筛选**: {time_filter}
- **强制刷新**: {force_refresh}

## 下载的subreddit
{chr(10).join([f"- r/{sub}" for sub in subreddit_list])}

## 数据存储位置
- 路径: `data/reddit_data/{category_name}/`
- 格式: 每个subreddit保存为单独的.jsonl文件
- 预计数据量: {len(subreddit_list) * limit_per_subreddit} 个帖子 (最大)

✅ **下载成功！** 数据已保存到指定位置。

💡 **使用建议**: 可以修改 `get_reddit_stock_info` 工具的数据路径来分析这些自定义数据。
"""
                logger.info(f"✅ [Reddit自定义下载] {category_name} 数据下载成功")
                return result
            else:
                error_msg = f"❌ {category_name} 自定义Reddit数据下载失败"
                logger.error(f"❌ [Reddit自定义下载] {error_msg}")
                return error_msg

        except Exception as e:
            error_msg = f"Reddit自定义下载工具执行失败: {str(e)}"
            logger.error(f"❌ [Reddit自定义下载] {error_msg}")
            return error_msg

    @staticmethod
    @tool
    def get_chinese_social_sentiment(
        ticker: Annotated[str, "Ticker of a company. e.g. AAPL, TSM"],
        curr_date: Annotated[str, "Current date in yyyy-mm-dd format"],
    ) -> str:
        """
        获取中国社交媒体和财经平台上关于特定股票的情绪分析和讨论热度。
        整合雪球、东方财富股吧、新浪财经等中国本土平台的数据。
        Args:
            ticker (str): 股票代码，如 AAPL, TSM
            curr_date (str): 当前日期，格式为 yyyy-mm-dd
        Returns:
            str: 包含中国投资者情绪分析、讨论热度、关键观点的格式化报告
        """
        try:
            # 这里可以集成多个中国平台的数据
            chinese_sentiment_results = interface.get_chinese_social_sentiment(
                ticker, curr_date
            )
            return chinese_sentiment_results
        except Exception as e:
            # 如果中国平台数据获取失败，回退到原有的Reddit数据
            return interface.get_reddit_company_news(ticker, curr_date, 7, 20)

    @staticmethod
    # @tool  # 已移除：请使用 get_stock_fundamentals_unified 或 get_stock_market_data_unified
    def get_china_stock_data(
        stock_code: Annotated[
            str, "中国股票代码，如 000001(平安银行), 600519(贵州茅台)"
        ],
        start_date: Annotated[str, "开始日期，格式 yyyy-mm-dd"],
        end_date: Annotated[str, "结束日期，格式 yyyy-mm-dd"],
    ) -> str:
        """
        获取中国A股实时和历史数据，通过Tushare等高质量数据源提供专业的股票数据。
        支持实时行情、历史K线、技术指标等全面数据，自动使用最佳数据源。
        Args:
            stock_code (str): 中国股票代码，如 000001(平安银行), 600519(贵州茅台)
            start_date (str): 开始日期，格式 yyyy-mm-dd
            end_date (str): 结束日期，格式 yyyy-mm-dd
        Returns:
            str: 包含实时行情、历史数据、技术指标的完整股票分析报告
        """
        try:
            logger.debug(
                f"📊 [DEBUG] ===== agent_utils.get_china_stock_data 开始调用 ====="
            )
            logger.debug(
                f"📊 [DEBUG] 参数: stock_code={stock_code}, start_date={start_date}, end_date={end_date}"
            )

            from tradingagents.dataflows.interface import get_china_stock_data_unified

            logger.debug(f"📊 [DEBUG] 成功导入统一数据源接口")

            logger.debug(f"📊 [DEBUG] 正在调用统一数据源接口...")
            result = get_china_stock_data_unified(stock_code, start_date, end_date)

            logger.debug(f"📊 [DEBUG] 统一数据源接口调用完成")
            logger.debug(f"📊 [DEBUG] 返回结果类型: {type(result)}")
            logger.debug(f"📊 [DEBUG] 返回结果长度: {len(result) if result else 0}")
            logger.debug(f"📊 [DEBUG] 返回结果前200字符: {str(result)[:200]}...")
            logger.debug(
                f"📊 [DEBUG] ===== agent_utils.get_china_stock_data 调用结束 ====="
            )

            return result
        except Exception as e:
            import traceback

            error_details = traceback.format_exc()
            logger.error(
                f"❌ [DEBUG] ===== agent_utils.get_china_stock_data 异常 ====="
            )
            logger.error(f"❌ [DEBUG] 错误类型: {type(e).__name__}")
            logger.error(f"❌ [DEBUG] 错误信息: {str(e)}")
            logger.error(f"❌ [DEBUG] 详细堆栈:")
            print(error_details)
            logger.error(f"❌ [DEBUG] ===== 异常处理结束 =====")
            return f"中国股票数据获取失败: {str(e)}。建议安装pytdx库: pip install pytdx"

    @staticmethod
    @tool
    def get_china_market_overview(
        curr_date: Annotated[str, "当前日期，格式 yyyy-mm-dd"],
    ) -> str:
        """
        获取中国股市整体概览，包括主要指数的实时行情。
        涵盖上证指数、深证成指、创业板指、科创50等主要指数。
        Args:
            curr_date (str): 当前日期，格式 yyyy-mm-dd
        Returns:
            str: 包含主要指数实时行情的市场概览报告
        """
        try:
            # 使用Tushare获取主要指数数据
            from tradingagents.dataflows.tushare_adapter import get_tushare_adapter

            adapter = get_tushare_adapter()
            if not adapter.provider or not adapter.provider.connected:
                # 如果Tushare不可用，回退到TDX
                logger.warning(f"⚠️ Tushare不可用，回退到TDX获取市场概览")
                from tradingagents.dataflows.tdx_utils import get_china_market_overview

                return get_china_market_overview()

            # 使用Tushare获取主要指数信息
            # 这里可以扩展为获取具体的指数数据
            return f"""# 中国股市概览 - {curr_date}

## 📊 主要指数
- 上证指数: 数据获取中...
- 深证成指: 数据获取中...
- 创业板指: 数据获取中...
- 科创50: 数据获取中...

## 💡 说明
市场概览功能正在从TDX迁移到Tushare，完整功能即将推出。
当前可以使用股票数据获取功能分析个股。

数据来源: Tushare专业数据源
更新时间: {curr_date}
"""

        except Exception as e:
            return f"中国市场概览获取失败: {str(e)}。正在从TDX迁移到Tushare数据源。"

    @staticmethod
    @tool
    def get_YFin_data(
        symbol: Annotated[str, "ticker symbol of the company"],
        start_date: Annotated[str, "Start date in yyyy-mm-dd format"],
        end_date: Annotated[str, "End date in yyyy-mm-dd format"],
    ) -> str:
        """
        Retrieve the stock price data for a given ticker symbol from Yahoo Finance.
        Args:
            symbol (str): Ticker symbol of the company, e.g. AAPL, TSM
            start_date (str): Start date in yyyy-mm-dd format
            end_date (str): End date in yyyy-mm-dd format
        Returns:
            str: A formatted dataframe containing the stock price data for the specified ticker symbol in the specified date range.
        """

        result_data = interface.get_YFin_data(symbol, start_date, end_date)

        return result_data

    @staticmethod
    @tool
    def get_YFin_data_online(
        symbol: Annotated[str, "ticker symbol of the company"],
        start_date: Annotated[str, "Start date in yyyy-mm-dd format"],
        end_date: Annotated[str, "End date in yyyy-mm-dd format"],
    ) -> str:
        """
        Retrieve the stock price data for a given ticker symbol from Yahoo Finance.
        Args:
            symbol (str): Ticker symbol of the company, e.g. AAPL, TSM
            start_date (str): Start date in yyyy-mm-dd format
            end_date (str): End date in yyyy-mm-dd format
        Returns:
            str: A formatted dataframe containing the stock price data for the specified ticker symbol in the specified date range.
        """

        result_data = interface.get_YFin_data_online(symbol, start_date, end_date)

        return result_data

    @staticmethod
    @tool
    def get_stockstats_indicators_report(
        symbol: Annotated[str, "ticker symbol of the company"],
        indicator: Annotated[
            str, "technical indicator to get the analysis and report of"
        ],
        curr_date: Annotated[
            str, "The current trading date you are trading on, YYYY-mm-dd"
        ],
        look_back_days: Annotated[int, "how many days to look back"] = 30,
    ) -> str:
        """
        Retrieve stock stats indicators for a given ticker symbol and indicator.
        Args:
            symbol (str): Ticker symbol of the company, e.g. AAPL, TSM
            indicator (str): Technical indicator to get the analysis and report of
            curr_date (str): The current trading date you are trading on, YYYY-mm-dd
            look_back_days (int): How many days to look back, default is 30
        Returns:
            str: A formatted dataframe containing the stock stats indicators for the specified ticker symbol and indicator.
        """

        result_stockstats = interface.get_stock_stats_indicators_window(
            symbol, indicator, curr_date, look_back_days, False
        )

        return result_stockstats

    @staticmethod
    @tool
    def get_stockstats_indicators_report_online(
        symbol: Annotated[str, "ticker symbol of the company"],
        indicator: Annotated[
            str, "technical indicator to get the analysis and report of"
        ],
        curr_date: Annotated[
            str, "The current trading date you are trading on, YYYY-mm-dd"
        ],
        look_back_days: Annotated[int, "how many days to look back"] = 30,
    ) -> str:
        """
        Retrieve stock stats indicators for a given ticker symbol and indicator.
        Args:
            symbol (str): Ticker symbol of the company, e.g. AAPL, TSM
            indicator (str): Technical indicator to get the analysis and report of
            curr_date (str): The current trading date you are trading on, YYYY-mm-dd
            look_back_days (int): How many days to look back, default is 30
        Returns:
            str: A formatted dataframe containing the stock stats indicators for the specified ticker symbol and indicator.
        """

        result_stockstats = interface.get_stock_stats_indicators_window(
            symbol, indicator, curr_date, look_back_days, True
        )

        return result_stockstats

    @staticmethod
    @tool
    def get_finnhub_company_insider_sentiment(
        ticker: Annotated[str, "ticker symbol for the company"],
        curr_date: Annotated[
            str,
            "current date of you are trading at, yyyy-mm-dd",
        ],
    ):
        """
        Retrieve insider sentiment information about a company (retrieved from public SEC information) for the past 30 days
        Args:
            ticker (str): ticker symbol of the company
            curr_date (str): current date you are trading at, yyyy-mm-dd
        Returns:
            str: a report of the sentiment in the past 30 days starting at curr_date
        """

        data_sentiment = interface.get_finnhub_company_insider_sentiment(
            ticker, curr_date, 30
        )

        return data_sentiment

    @staticmethod
    @tool
    def get_finnhub_company_insider_transactions(
        ticker: Annotated[str, "ticker symbol"],
        curr_date: Annotated[
            str,
            "current date you are trading at, yyyy-mm-dd",
        ],
    ):
        """
        Retrieve insider transaction information about a company (retrieved from public SEC information) for the past 30 days
        Args:
            ticker (str): ticker symbol of the company
            curr_date (str): current date you are trading at, yyyy-mm-dd
        Returns:
            str: a report of the company's insider transactions/trading information in the past 30 days
        """

        data_trans = interface.get_finnhub_company_insider_transactions(
            ticker, curr_date, 30
        )

        return data_trans

    @staticmethod
    @tool
    def get_simfin_balance_sheet(
        ticker: Annotated[str, "ticker symbol"],
        freq: Annotated[
            str,
            "reporting frequency of the company's financial history: annual/quarterly",
        ],
        curr_date: Annotated[str, "current date you are trading at, yyyy-mm-dd"],
    ):
        """
        Retrieve the most recent balance sheet of a company
        Args:
            ticker (str): ticker symbol of the company
            freq (str): reporting frequency of the company's financial history: annual / quarterly
            curr_date (str): current date you are trading at, yyyy-mm-dd
        Returns:
            str: a report of the company's most recent balance sheet
        """

        data_balance_sheet = interface.get_simfin_balance_sheet(ticker, freq, curr_date)

        return data_balance_sheet

    @staticmethod
    @tool
    def get_simfin_cashflow(
        ticker: Annotated[str, "ticker symbol"],
        freq: Annotated[
            str,
            "reporting frequency of the company's financial history: annual/quarterly",
        ],
        curr_date: Annotated[str, "current date you are trading at, yyyy-mm-dd"],
    ):
        """
        Retrieve the most recent cash flow statement of a company
        Args:
            ticker (str): ticker symbol of the company
            freq (str): reporting frequency of the company's financial history: annual / quarterly
            curr_date (str): current date you are trading at, yyyy-mm-dd
        Returns:
                str: a report of the company's most recent cash flow statement
        """

        data_cashflow = interface.get_simfin_cashflow(ticker, freq, curr_date)

        return data_cashflow

    @staticmethod
    @tool
    def get_simfin_income_stmt(
        ticker: Annotated[str, "ticker symbol"],
        freq: Annotated[
            str,
            "reporting frequency of the company's financial history: annual/quarterly",
        ],
        curr_date: Annotated[str, "current date you are trading at, yyyy-mm-dd"],
    ):
        """
        Retrieve the most recent income statement of a company
        Args:
            ticker (str): ticker symbol of the company
            freq (str): reporting frequency of the company's financial history: annual / quarterly
            curr_date (str): current date you are trading at, yyyy-mm-dd
        Returns:
                str: a report of the company's most recent income statement
        """

        data_income_stmt = interface.get_simfin_income_statements(
            ticker, freq, curr_date
        )

        return data_income_stmt

    @staticmethod
    @tool
    def get_google_news(
        query: Annotated[str, "Query to search with"],
        curr_date: Annotated[str, "Curr date in yyyy-mm-dd format"],
    ):
        """
        Retrieve the latest news from Google News based on a query and date range.
        Args:
            query (str): Query to search with
            curr_date (str): Current date in yyyy-mm-dd format
            look_back_days (int): How many days to look back
        Returns:
            str: A formatted string containing the latest news from Google News based on the query and date range.
        """

        google_news_results = interface.get_google_news(query, curr_date, 7)

        return google_news_results

    @staticmethod
    @tool
    def get_realtime_stock_news(
        ticker: Annotated[str, "Ticker of a company. e.g. AAPL, TSM"],
        curr_date: Annotated[str, "Current date in yyyy-mm-dd format"],
    ) -> str:
        """
        获取股票的实时新闻分析，解决传统新闻源的滞后性问题。
        整合多个专业财经API，提供15-30分钟内的最新新闻。
        支持多种新闻源轮询机制，优先使用实时新闻聚合器，失败时自动尝试备用新闻源。
        对于A股和港股，会优先使用中文财经新闻源（如东方财富）。

        Args:
            ticker (str): 股票代码，如 AAPL, TSM, 600036.SH
            curr_date (str): 当前日期，格式为 yyyy-mm-dd
        Returns:
            str: 包含实时新闻分析、紧急程度评估、时效性说明的格式化报告
        """
        from tradingagents.dataflows.realtime_news_utils import get_realtime_stock_news

        return get_realtime_stock_news(ticker, curr_date, hours_back=6)

    @staticmethod
    @tool
    def get_stock_news_openai(
        ticker: Annotated[str, "the company's ticker"],
        curr_date: Annotated[str, "Current date in yyyy-mm-dd format"],
    ):
        """
        Retrieve the latest news about a given stock by using OpenAI's news API.
        Args:
            ticker (str): Ticker of a company. e.g. AAPL, TSM
            curr_date (str): Current date in yyyy-mm-dd format
        Returns:
            str: A formatted string containing the latest news about the company on the given date.
        """
        print(
            f"📊 [DEBUG] get_stock_news_openai 被调用: ticker={ticker}, date={curr_date}"
        )
        openai_news_results = interface.get_stock_news_gemini(ticker, curr_date)

        return openai_news_results

    @staticmethod
    @tool
    def get_global_news_openai(
        ticker: Annotated[str, "the company's ticker"],
        curr_date: Annotated[str, "Current date in yyyy-mm-dd format"],
    ):
        """
        Retrieve the latest macroeconomics news on a given date using OpenAI's macroeconomics news API.
        Args:
            curr_date (str): Current date in yyyy-mm-dd format
        Returns:
            str: A formatted string containing the latest macroeconomic news on the given date.
        """

        openai_news_results = interface.get_global_news_openai(ticker, curr_date)

        return openai_news_results

    @staticmethod
    # @tool  # 已移除：请使用 get_stock_fundamentals_unified
    def get_fundamentals_openai(
        ticker: Annotated[str, "the company's ticker"],
        curr_date: Annotated[str, "Current date in yyyy-mm-dd format"],
    ):
        """
        Retrieve the latest fundamental information about a given stock on a given date by using OpenAI's news API.
        Args:
            ticker (str): Ticker of a company. e.g. AAPL, TSM
            curr_date (str): Current date in yyyy-mm-dd format
        Returns:
            str: A formatted string containing the latest fundamental information about the company on the given date.
        """
        logger.debug(
            f"📊 [DEBUG] get_fundamentals_openai 被调用: ticker={ticker}, date={curr_date}"
        )

        # 检查是否为中国股票
        import re

        if re.match(r"^\d{6}$", str(ticker)):
            logger.debug(f"📊 [DEBUG] 检测到中国A股代码: {ticker}")
            # 使用统一接口获取中国股票名称
            try:
                from tradingagents.dataflows.interface import (
                    get_china_stock_info_unified,
                )

                stock_info = get_china_stock_info_unified(ticker)

                # 解析股票名称
                if "股票名称:" in stock_info:
                    company_name = (
                        stock_info.split("股票名称:")[1].split("\n")[0].strip()
                    )
                else:
                    company_name = f"股票代码{ticker}"

                logger.debug(f"📊 [DEBUG] 中国股票名称映射: {ticker} -> {company_name}")
            except Exception as e:
                logger.error(f"⚠️ [DEBUG] 从统一接口获取股票名称失败: {e}")
                company_name = f"股票代码{ticker}"

            # 修改查询以包含正确的公司名称
            modified_query = f"{company_name}({ticker})"
            logger.debug(f"📊 [DEBUG] 修改后的查询: {modified_query}")
        else:
            logger.debug(f"📊 [DEBUG] 检测到非中国股票: {ticker}")
            modified_query = ticker

        try:
            openai_fundamentals_results = interface.get_fundamentals_openai(
                modified_query, curr_date
            )
            logger.debug(
                f"📊 [DEBUG] OpenAI基本面分析结果长度: {len(openai_fundamentals_results) if openai_fundamentals_results else 0}"
            )
            return openai_fundamentals_results
        except Exception as e:
            logger.error(f"❌ [DEBUG] OpenAI基本面分析失败: {str(e)}")
            return f"基本面分析失败: {str(e)}"

    @staticmethod
    # @tool  # 已移除：请使用 get_stock_fundamentals_unified
    def get_china_fundamentals(
        ticker: Annotated[str, "中国A股股票代码，如600036"],
        curr_date: Annotated[str, "当前日期，格式为yyyy-mm-dd"],
    ):
        """
        获取中国A股股票的基本面信息，使用中国股票数据源。
        Args:
            ticker (str): 中国A股股票代码，如600036, 000001
            curr_date (str): 当前日期，格式为yyyy-mm-dd
        Returns:
            str: 包含股票基本面信息的格式化字符串
        """
        logger.debug(
            f"📊 [DEBUG] get_china_fundamentals 被调用: ticker={ticker}, date={curr_date}"
        )

        # 检查是否为中国股票
        import re

        if not re.match(r"^\d{6}$", str(ticker)):
            return f"错误：{ticker} 不是有效的中国A股代码格式"

        try:
            # 使用统一数据源接口获取股票数据（默认Tushare，支持备用数据源）
            from tradingagents.dataflows.interface import get_china_stock_data_unified

            logger.debug(f"📊 [DEBUG] 正在获取 {ticker} 的股票数据...")

            # 获取最近30天的数据用于基本面分析
            from datetime import datetime, timedelta

            end_date = datetime.strptime(curr_date, "%Y-%m-%d")
            start_date = end_date - timedelta(days=30)

            stock_data = get_china_stock_data_unified(
                ticker, start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d")
            )

            logger.debug(
                f"📊 [DEBUG] 股票数据获取完成，长度: {len(stock_data) if stock_data else 0}"
            )

            if not stock_data or "获取失败" in stock_data or "❌" in stock_data:
                return f"无法获取股票 {ticker} 的基本面数据：{stock_data}"

            # 调用真正的基本面分析
            from tradingagents.dataflows.optimized_china_data import (
                OptimizedChinaDataProvider,
            )

            # 创建分析器实例
            analyzer = OptimizedChinaDataProvider()

            # 生成真正的基本面分析报告
            fundamentals_report = analyzer._generate_fundamentals_report(
                ticker, stock_data
            )

            logger.debug(f"📊 [DEBUG] 中国基本面分析报告生成完成")
            logger.debug(
                f"📊 [DEBUG] get_china_fundamentals 结果长度: {len(fundamentals_report)}"
            )

            return fundamentals_report

        except Exception as e:
            import traceback

            error_details = traceback.format_exc()
            logger.error(f"❌ [DEBUG] get_china_fundamentals 失败:")
            logger.error(f"❌ [DEBUG] 错误: {str(e)}")
            logger.error(f"❌ [DEBUG] 堆栈: {error_details}")
            return f"中国股票基本面分析失败: {str(e)}"

    @staticmethod
    # @tool  # 已移除：请使用 get_stock_fundamentals_unified 或 get_stock_market_data_unified
    def get_hk_stock_data_unified(
        symbol: Annotated[str, "港股代码，如：0700.HK、9988.HK等"],
        start_date: Annotated[str, "开始日期，格式：YYYY-MM-DD"],
        end_date: Annotated[str, "结束日期，格式：YYYY-MM-DD"],
    ) -> str:
        """
        获取港股数据的统一接口，优先使用AKShare数据源，备用Yahoo Finance

        Args:
            symbol: 港股代码 (如: 0700.HK)
            start_date: 开始日期 (YYYY-MM-DD)
            end_date: 结束日期 (YYYY-MM-DD)

        Returns:
            str: 格式化的港股数据
        """
        logger.debug(
            f"🇭🇰 [DEBUG] get_hk_stock_data_unified 被调用: symbol={symbol}, start_date={start_date}, end_date={end_date}"
        )

        try:
            from tradingagents.dataflows.interface import get_hk_stock_data_unified

            result = get_hk_stock_data_unified(symbol, start_date, end_date)

            logger.debug(
                f"🇭🇰 [DEBUG] 港股数据获取完成，长度: {len(result) if result else 0}"
            )

            return result

        except Exception as e:
            import traceback

            error_details = traceback.format_exc()
            logger.error(f"❌ [DEBUG] get_hk_stock_data_unified 失败:")
            logger.error(f"❌ [DEBUG] 错误: {str(e)}")
            logger.error(f"❌ [DEBUG] 堆栈: {error_details}")
            return f"港股数据获取失败: {str(e)}"

    @staticmethod
    @tool
    @log_tool_call(tool_name="get_stock_fundamentals_unified", log_args=True)
    def get_stock_fundamentals_unified(
        ticker: Annotated[str, "股票代码（支持A股、港股、美股）"],
        start_date: Annotated[str, "开始日期，格式：YYYY-MM-DD"] = None,
        end_date: Annotated[str, "结束日期，格式：YYYY-MM-DD"] = None,
        curr_date: Annotated[str, "当前日期，格式：YYYY-MM-DD"] = None,
    ) -> str:
        """
        统一的股票基本面分析工具
        自动识别股票类型（A股、港股、美股）并调用相应的数据源

        Args:
            ticker: 股票代码（如：000001、0700.HK、AAPL）
            start_date: 开始日期（可选，格式：YYYY-MM-DD）
            end_date: 结束日期（可选，格式：YYYY-MM-DD）
            curr_date: 当前日期（可选，格式：YYYY-MM-DD）

        Returns:
            str: 基本面分析数据和报告
        """
        logger.info(f"📊 [统一基本面工具] 分析股票: {ticker}")

        # 添加详细的股票代码追踪日志
        logger.info(
            f"🔍 [股票代码追踪] 统一基本面工具接收到的原始股票代码: '{ticker}' (类型: {type(ticker)})"
        )
        logger.info(f"🔍 [股票代码追踪] 股票代码长度: {len(str(ticker))}")
        logger.info(f"🔍 [股票代码追踪] 股票代码字符: {list(str(ticker))}")

        # 保存原始ticker用于对比
        original_ticker = ticker

        try:
            from tradingagents.utils.stock_utils import StockUtils
            from datetime import datetime, timedelta

            # 自动识别股票类型
            market_info = StockUtils.get_market_info(ticker)
            is_china = market_info["is_china"]
            is_hk = market_info["is_hk"]
            is_us = market_info["is_us"]

            logger.info(
                f"🔍 [股票代码追踪] StockUtils.get_market_info 返回的市场信息: {market_info}"
            )
            logger.info(f"📊 [统一基本面工具] 股票类型: {market_info['market_name']}")
            logger.info(
                f"📊 [统一基本面工具] 货币: {market_info['currency_name']} ({market_info['currency_symbol']})"
            )

            # 检查ticker是否在处理过程中发生了变化
            if str(ticker) != str(original_ticker):
                logger.warning(
                    f"🔍 [股票代码追踪] 警告：股票代码发生了变化！原始: '{original_ticker}' -> 当前: '{ticker}'"
                )

            # 设置默认日期
            if not curr_date:
                curr_date = datetime.now().strftime("%Y-%m-%d")
            if not start_date:
                start_date = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
            if not end_date:
                end_date = curr_date

            result_data = []

            if is_china:
                # 中国A股：获取股票数据 + 基本面数据
                logger.info(f"🇨🇳 [统一基本面工具] 处理A股数据...")
                logger.info(f"🔍 [股票代码追踪] 进入A股处理分支，ticker: '{ticker}'")

                try:
                    # 获取股票价格数据
                    from tradingagents.dataflows.interface import (
                        get_china_stock_data_unified,
                    )

                    logger.info(
                        f"🔍 [股票代码追踪] 调用 get_china_stock_data_unified，传入参数: ticker='{ticker}', start_date='{start_date}', end_date='{end_date}'"
                    )
                    stock_data = get_china_stock_data_unified(
                        ticker, start_date, end_date
                    )
                    logger.info(
                        f"🔍 [股票代码追踪] get_china_stock_data_unified 返回结果前200字符: {stock_data[:200] if stock_data else 'None'}"
                    )
                    result_data.append(f"## A股价格数据\n{stock_data}")
                except Exception as e:
                    logger.error(
                        f"🔍 [股票代码追踪] get_china_stock_data_unified 调用失败: {e}"
                    )
                    result_data.append(f"## A股价格数据\n获取失败: {e}")

                try:
                    # 获取基本面数据
                    from tradingagents.dataflows.optimized_china_data import (
                        OptimizedChinaDataProvider,
                    )

                    analyzer = OptimizedChinaDataProvider()
                    logger.info(
                        f"🔍 [股票代码追踪] 调用 OptimizedChinaDataProvider._generate_fundamentals_report，传入参数: ticker='{ticker}'"
                    )
                    fundamentals_data = analyzer._generate_fundamentals_report(
                        ticker, stock_data if "stock_data" in locals() else ""
                    )
                    logger.info(
                        f"🔍 [股票代码追踪] _generate_fundamentals_report 返回结果前200字符: {fundamentals_data[:200] if fundamentals_data else 'None'}"
                    )
                    result_data.append(f"## A股基本面数据\n{fundamentals_data}")
                except Exception as e:
                    logger.error(
                        f"🔍 [股票代码追踪] _generate_fundamentals_report 调用失败: {e}"
                    )
                    result_data.append(f"## A股基本面数据\n获取失败: {e}")

            elif is_hk:
                # 港股：使用AKShare数据源，支持多重备用方案
                logger.info(f"🇭🇰 [统一基本面工具] 处理港股数据...")

                hk_data_success = False

                # 主要数据源：AKShare
                try:
                    from tradingagents.dataflows.interface import (
                        get_hk_stock_data_unified,
                    )

                    hk_data = get_hk_stock_data_unified(ticker, start_date, end_date)

                    # 检查数据质量
                    if hk_data and len(hk_data) > 100 and "❌" not in hk_data:
                        result_data.append(f"## 港股数据\n{hk_data}")
                        hk_data_success = True
                        logger.info(f"✅ [统一基本面工具] 港股主要数据源成功")
                    else:
                        logger.warning(f"⚠️ [统一基本面工具] 港股主要数据源质量不佳")

                except Exception as e:
                    logger.error(f"⚠️ [统一基本面工具] 港股主要数据源失败: {e}")

                # 备用方案：基础港股信息
                if not hk_data_success:
                    try:
                        from tradingagents.dataflows.interface import (
                            get_hk_stock_info_unified,
                        )

                        hk_info = get_hk_stock_info_unified(ticker)

                        basic_info = f"""## 港股基础信息

**股票代码**: {ticker}
**股票名称**: {hk_info.get("name", f"港股{ticker}")}
**交易货币**: 港币 (HK$)
**交易所**: 香港交易所 (HKG)
**数据源**: {hk_info.get("source", "基础信息")}

⚠️ 注意：详细的价格和财务数据暂时无法获取，建议稍后重试或使用其他数据源。

**基本面分析建议**：
- 建议查看公司最新财报
- 关注港股市场整体走势
- 考虑汇率因素对投资的影响
"""
                        result_data.append(basic_info)
                        logger.info(f"✅ [统一基本面工具] 港股备用信息成功")

                    except Exception as e2:
                        # 最终备用方案
                        fallback_info = f"""## 港股信息（备用）

**股票代码**: {ticker}
**股票类型**: 港股
**交易货币**: 港币 (HK$)
**交易所**: 香港交易所 (HKG)

❌ 数据获取遇到问题: {str(e2)}

**建议**：
1. 检查网络连接
2. 稍后重试分析
3. 使用其他港股数据源
4. 查看公司官方财报
"""
                        result_data.append(fallback_info)
                        logger.warning(f"⚠️ [统一基本面工具] 港股使用最终备用方案")

            else:
                # 美股：使用OpenAI/Finnhub数据源
                logger.info(f"🇺🇸 [统一基本面工具] 处理美股数据...")

                try:
                    from tradingagents.dataflows.interface import (
                        get_fundamentals_openai,
                    )

                    us_data = get_fundamentals_openai(ticker, curr_date)
                    result_data.append(f"## 美股基本面数据\n{us_data}")
                except Exception as e:
                    result_data.append(f"## 美股基本面数据\n获取失败: {e}")

            # 组合所有数据
            combined_result = f"""# {ticker} 基本面分析数据

**股票类型**: {market_info["market_name"]}
**货币**: {market_info["currency_name"]} ({market_info["currency_symbol"]})
**分析日期**: {curr_date}

{chr(10).join(result_data)}

---
*数据来源: 根据股票类型自动选择最适合的数据源*
"""

            logger.info(
                f"📊 [统一基本面工具] 数据获取完成，总长度: {len(combined_result)}"
            )
            return combined_result

        except Exception as e:
            error_msg = f"统一基本面分析工具执行失败: {str(e)}"
            logger.error(f"❌ [统一基本面工具] {error_msg}")
            return error_msg

    @staticmethod
    @tool
    @log_tool_call(tool_name="get_stock_market_data_unified", log_args=True)
    def get_stock_market_data_unified(
        ticker: Annotated[str, "股票代码（支持A股、港股、美股）"],
        start_date: Annotated[str, "开始日期，格式：YYYY-MM-DD"],
        end_date: Annotated[str, "结束日期，格式：YYYY-MM-DD"],
    ) -> str:
        """
        统一的股票市场数据工具
        自动识别股票类型（A股、港股、美股）并调用相应的数据源获取价格和技术指标数据

        Args:
            ticker: 股票代码（如：000001、0700.HK、AAPL）
            start_date: 开始日期（格式：YYYY-MM-DD）
            end_date: 结束日期（格式：YYYY-MM-DD）

        Returns:
            str: 市场数据和技术分析报告
        """
        logger.info(f"📈 [统一市场工具] 分析股票: {ticker}")

        try:
            from tradingagents.utils.stock_utils import StockUtils

            # 自动识别股票类型
            market_info = StockUtils.get_market_info(ticker)
            is_china = market_info["is_china"]
            is_hk = market_info["is_hk"]
            is_us = market_info["is_us"]

            logger.info(f"📈 [统一市场工具] 股票类型: {market_info['market_name']}")
            logger.info(
                f"📈 [统一市场工具] 货币: {market_info['currency_name']} ({market_info['currency_symbol']}"
            )

            result_data = []

            if is_china:
                # 中国A股：使用中国股票数据源
                logger.info(f"🇨🇳 [统一市场工具] 处理A股市场数据...")

                try:
                    from tradingagents.dataflows.interface import (
                        get_china_stock_data_unified,
                    )

                    stock_data = get_china_stock_data_unified(
                        ticker, start_date, end_date
                    )
                    result_data.append(f"## A股市场数据\n{stock_data}")
                except Exception as e:
                    result_data.append(f"## A股市场数据\n获取失败: {e}")

            elif is_hk:
                # 港股：使用AKShare数据源
                logger.info(f"🇭🇰 [统一市场工具] 处理港股市场数据...")

                try:
                    from tradingagents.dataflows.interface import (
                        get_hk_stock_data_unified,
                    )

                    hk_data = get_hk_stock_data_unified(ticker, start_date, end_date)
                    result_data.append(f"## 港股市场数据\n{hk_data}")
                except Exception as e:
                    result_data.append(f"## 港股市场数据\n获取失败: {e}")

            else:
                # 美股：优先使用FINNHUB API数据源
                logger.info(f"🇺🇸 [统一市场工具] 处理美股市场数据...")

                try:
                    from tradingagents.dataflows.optimized_us_data import (
                        get_us_stock_data_cached,
                    )

                    us_data = get_us_stock_data_cached(ticker, start_date, end_date)
                    result_data.append(f"## 美股市场数据\n{us_data}")
                except Exception as e:
                    result_data.append(f"## 美股市场数据\n获取失败: {e}")

            # 组合所有数据
            combined_result = f"""# {ticker} 市场数据分析

**股票类型**: {market_info["market_name"]}
**货币**: {market_info["currency_name"]} ({market_info["currency_symbol"]})
**分析期间**: {start_date} 至 {end_date}

{chr(10).join(result_data)}

---
*数据来源: 根据股票类型自动选择最适合的数据源*
"""

            logger.info(
                f"📈 [统一市场工具] 数据获取完成，总长度: {len(combined_result)}"
            )
            return combined_result

        except Exception as e:
            error_msg = f"统一市场数据工具执行失败: {str(e)}"
            logger.error(f"❌ [统一市场工具] {error_msg}")
            return error_msg

    @staticmethod
    @tool
    @log_tool_call(tool_name="get_stock_news_unified", log_args=True)
    def get_stock_news_unified(
        ticker: Annotated[str, "股票代码（支持A股、港股、美股）"],
        curr_date: Annotated[str, "当前日期，格式：YYYY-MM-DD"],
    ) -> str:
        """
        统一的股票新闻工具
        自动识别股票类型（A股、港股、美股）并调用相应的新闻数据源

        Args:
            ticker: 股票代码（如：000001、0700.HK、AAPL）
            curr_date: 当前日期（格式：YYYY-MM-DD）

        Returns:
            str: 新闻分析报告
        """
        logger.info(f"📰 [统一新闻工具] 分析股票: {ticker}")

        try:
            from tradingagents.utils.stock_utils import StockUtils
            from datetime import datetime, timedelta

            # 自动识别股票类型
            market_info = StockUtils.get_market_info(ticker)
            is_china = market_info["is_china"]
            is_hk = market_info["is_hk"]
            is_us = market_info["is_us"]

            logger.info(f"📰 [统一新闻工具] 股票类型: {market_info['market_name']}")

            # 计算新闻查询的日期范围
            end_date = datetime.strptime(curr_date, "%Y-%m-%d")
            start_date = end_date - timedelta(days=7)
            start_date_str = start_date.strftime("%Y-%m-%d")

            result_data = []

            if is_china or is_hk:
                # 中国A股和港股：使用AKShare东方财富新闻和Google新闻（中文搜索）
                logger.info(f"🇨🇳🇭🇰 [统一新闻工具] 处理中文新闻...")

                # 1. 尝试获取AKShare东方财富新闻
                try:
                    # 处理股票代码
                    clean_ticker = (
                        ticker.replace(".SH", "")
                        .replace(".SZ", "")
                        .replace(".SS", "")
                        .replace(".HK", "")
                        .replace(".XSHE", "")
                        .replace(".XSHG", "")
                    )

                    logger.info(
                        f"🇨🇳🇭🇰 [统一新闻工具] 尝试获取东方财富新闻: {clean_ticker}"
                    )

                    # 导入AKShare新闻获取函数
                    from tradingagents.dataflows.akshare_utils import get_stock_news_em

                    # 获取东方财富新闻
                    news_df = get_stock_news_em(clean_ticker)

                    if not news_df.empty:
                        # 格式化东方财富新闻
                        em_news_items = []
                        for _, row in news_df.iterrows():
                            news_title = row.get("标题", "")
                            news_time = row.get("时间", "")
                            news_url = row.get("链接", "")

                            news_item = f"- **{news_title}** [{news_time}]({news_url})"
                            em_news_items.append(news_item)

                        # 添加到结果中
                        if em_news_items:
                            em_news_text = "\n".join(em_news_items)
                            result_data.append(f"## 东方财富新闻\n{em_news_text}")
                            logger.info(
                                f"🇨🇳🇭🇰 [统一新闻工具] 成功获取{len(em_news_items)}条东方财富新闻"
                            )
                except Exception as em_e:
                    logger.error(f"❌ [统一新闻工具] 东方财富新闻获取失败: {em_e}")
                    result_data.append(f"## 东方财富新闻\n获取失败: {em_e}")

                # 2. 获取Google新闻作为补充
                try:
                    # 获取公司中文名称用于搜索
                    if is_china:
                        # A股使用股票代码搜索，添加更多中文关键词
                        clean_ticker = (
                            ticker.replace(".SH", "")
                            .replace(".SZ", "")
                            .replace(".SS", "")
                            .replace(".XSHE", "")
                            .replace(".XSHG", "")
                        )
                        search_query = f"{clean_ticker} 股票 公司 财报 新闻"
                        logger.info(
                            f"🇨🇳 [统一新闻工具] A股Google新闻搜索关键词: {search_query}"
                        )
                    else:
                        # 港股使用代码搜索
                        search_query = f"{ticker} 港股"
                        logger.info(
                            f"🇭🇰 [统一新闻工具] 港股Google新闻搜索关键词: {search_query}"
                        )

                    from tradingagents.dataflows.interface import get_google_news

                    news_data = get_google_news(search_query, curr_date)
                    result_data.append(f"## Google新闻\n{news_data}")
                    logger.info(f"🇨🇳🇭🇰 [统一新闻工具] 成功获取Google新闻")
                except Exception as google_e:
                    logger.error(f"❌ [统一新闻工具] Google新闻获取失败: {google_e}")
                    result_data.append(f"## Google新闻\n获取失败: {google_e}")

            else:
                # 美股：使用Finnhub新闻
                logger.info(f"🇺🇸 [统一新闻工具] 处理美股新闻...")

                try:
                    from tradingagents.dataflows.interface import get_finnhub_news

                    news_data = get_finnhub_news(ticker, start_date_str, curr_date)
                    result_data.append(f"## 美股新闻\n{news_data}")
                except Exception as e:
                    result_data.append(f"## 美股新闻\n获取失败: {e}")

            # 组合所有数据
            combined_result = f"""# {ticker} 新闻分析

**股票类型**: {market_info["market_name"]}
**分析日期**: {curr_date}
**新闻时间范围**: {start_date_str} 至 {curr_date}

{chr(10).join(result_data)}

---
*数据来源: 根据股票类型自动选择最适合的新闻源*
"""

            logger.info(
                f"📰 [统一新闻工具] 数据获取完成，总长度: {len(combined_result)}"
            )
            return combined_result

        except Exception as e:
            error_msg = f"统一新闻工具执行失败: {str(e)}"
            logger.error(f"❌ [统一新闻工具] {error_msg}")
            return error_msg

    @staticmethod
    @tool
    @log_tool_call(tool_name="get_stock_sentiment_unified", log_args=True)
    def get_stock_sentiment_unified(
        ticker: Annotated[str, "股票代码（支持A股、港股、美股）"],
        curr_date: Annotated[str, "当前日期，格式：YYYY-MM-DD"],
    ) -> str:
        """
        统一的股票情绪分析工具
        自动识别股票类型（A股、港股、美股）并调用相应的情绪数据源

        Args:
            ticker: 股票代码（如：000001、0700.HK、AAPL）
            curr_date: 当前日期（格式：YYYY-MM-DD）

        Returns:
            str: 情绪分析报告
        """
        logger.info(f"😊 [统一情绪工具] 分析股票: {ticker}")

        try:
            from tradingagents.utils.stock_utils import StockUtils

            # 自动识别股票类型
            market_info = StockUtils.get_market_info(ticker)
            is_china = market_info["is_china"]
            is_hk = market_info["is_hk"]
            is_us = market_info["is_us"]

            logger.info(f"😊 [统一情绪工具] 股票类型: {market_info['market_name']}")

            result_data = []

            if is_china or is_hk:
                # 中国A股和港股：使用社交媒体情绪分析
                logger.info(f"🇨🇳🇭🇰 [统一情绪工具] 处理中文市场情绪...")

                try:
                    # 可以集成微博、雪球、东方财富等中文社交媒体情绪
                    # 目前使用基础的情绪分析
                    sentiment_summary = f"""
## 中文市场情绪分析

**股票**: {ticker} ({market_info["market_name"]})
**分析日期**: {curr_date}

### 市场情绪概况
- 由于中文社交媒体情绪数据源暂未完全集成，当前提供基础分析
- 建议关注雪球、东方财富、同花顺等平台的讨论热度
- 港股市场还需关注香港本地财经媒体情绪

### 情绪指标
- 整体情绪: 中性
- 讨论热度: 待分析
- 投资者信心: 待评估

*注：完整的中文社交媒体情绪分析功能正在开发中*
"""
                    result_data.append(sentiment_summary)
                except Exception as e:
                    result_data.append(f"## 中文市场情绪\n获取失败: {e}")

            else:
                # 美股：使用Reddit情绪分析
                logger.info(f"🇺🇸 [统一情绪工具] 处理美股情绪...")

                try:
                    from tradingagents.dataflows.interface import get_reddit_sentiment

                    sentiment_data = get_reddit_sentiment(ticker, curr_date)
                    result_data.append(f"## 美股Reddit情绪\n{sentiment_data}")
                except Exception as e:
                    result_data.append(f"## 美股Reddit情绪\n获取失败: {e}")

            # 组合所有数据
            combined_result = f"""# {ticker} 情绪分析

**股票类型**: {market_info["market_name"]}
**分析日期**: {curr_date}

{chr(10).join(result_data)}

---
*数据来源: 根据股票类型自动选择最适合的情绪数据源*
"""

            logger.info(
                f"😊 [统一情绪工具] 数据获取完成，总长度: {len(combined_result)}"
            )
            return combined_result

        except Exception as e:
            error_msg = f"统一情绪分析工具执行失败: {str(e)}"
            logger.error(f"❌ [统一情绪工具] {error_msg}")
            return error_msg
