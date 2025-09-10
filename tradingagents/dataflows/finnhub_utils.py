import json
import os
import datetime
# 导入日志模块
from tradingagents.utils.logging_manager import get_logger
logger = get_logger('agents')



def get_data_in_range(ticker, start_date, end_date, data_type, data_dir, period=None):
    """
    Gets finnhub data saved and processed on disk.
    Args:
        start_date (str): Start date in YYYY-MM-DD format.
        end_date (str): End date in YYYY-MM-DD format.
        data_type (str): Type of data from finnhub to fetch. Can be insider_trans, SEC_filings, news_data, insider_senti, or fin_as_reported.
        data_dir (str): Directory where the data is saved.
        period (str): Default to none, if there is a period specified, should be annual or quarterly.
    """
    print(f"新闻数据1111: {ticker}, {start_date}, {end_date}, {data_type}, {data_dir}, {period}")
    if period:
        data_path = os.path.join(
            data_dir,
            "finnhub_data",
            data_type,
            f"{ticker}_{period}_data_formatted.json",
        )
    else:
        
        data_path = os.path.join(
            data_dir, "finnhub_data", data_type, f"{ticker}_data_formatted.json"
        )
        print(f"新闻数据 data_path: {data_path}")

    try:
        if not os.path.exists(data_path):
            logger.warning(f"⚠️ [DEBUG] 数据文件不存在: {data_path}")
            logger.warning(f"⚠️ [DEBUG] 请确保已下载相关数据或检查数据目录配置")
            return {}
        
        with open(data_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        logger.error(f"❌ [ERROR] 文件未找到: {data_path}")
        return {}
    except json.JSONDecodeError as e:
        logger.error(f"❌ [ERROR] JSON解析错误: {e}")
        return {}
    except Exception as e:
        logger.error(f"❌ [ERROR] 读取数据文件时发生错误: {e}")
        return {}

    # filter keys (date, str in format YYYY-MM-DD) by the date range (str, str in format YYYY-MM-DD)
    filtered_data = {}
    for entry in data:
        if not entry:
            continue
        
        timestamp = entry.get("datetime", 0)

        date_key = datetime.datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d')
        # print(f"新闻数据 date_key: {date_key}")
        # 检查日期范围
        if start_date <= date_key <= end_date:
            # 如果该日期还没有条目，创建列表
            if date_key not in filtered_data:
                filtered_data[date_key] = []
            filtered_data[date_key].append(entry)
    
    return filtered_data
