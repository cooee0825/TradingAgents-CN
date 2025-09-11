import requests
from bs4 import BeautifulSoup
from datetime import datetime
import time
import random
from concurrent.futures import ThreadPoolExecutor, as_completed
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    retry_if_result,
)

# 导入日志模块
from tradingagents.utils.logging_manager import get_logger

logger = get_logger("agents")


def is_rate_limited(response):
    """Check if the response indicates rate limiting (status code 429)"""
    return response.status_code == 429


@retry(
    retry=(
        retry_if_result(is_rate_limited)
        | retry_if_exception_type(requests.exceptions.ConnectionError)
        | retry_if_exception_type(requests.exceptions.Timeout)
        | retry_if_exception_type(requests.exceptions.SSLError)
    ),
    wait=wait_exponential(multiplier=1, min=4, max=60),
    stop=stop_after_attempt(3),  # 减少重试次数，避免过长等待
)
def make_request(url, headers):
    """Make a request with retry logic for rate limiting and connection issues"""
    # Random delay before each request to avoid detection
    time.sleep(random.uniform(1, 3))  # 减少延迟时间

    # 创建session并配置SSL
    session = requests.Session()
    session.headers.update(headers)

    # 添加更多的配置来处理SSL和连接问题
    try:
        response = session.get(
            url,
            timeout=(10, 30),  # 连接超时10秒，读取超时30秒
            verify=True,  # 验证SSL证书
            allow_redirects=True,
            stream=False,
        )
        response.raise_for_status()  # 检查HTTP状态码
        return response
    except requests.exceptions.SSLError as e:
        logger.warning(f"SSL错误，尝试不验证证书: {e}")
        # 如果SSL验证失败，尝试不验证证书
        response = session.get(
            url,
            timeout=(10, 30),
            verify=False,  # 不验证SSL证书
            allow_redirects=True,
            stream=False,
        )
        response.raise_for_status()
        return response
    finally:
        session.close()


def getNewsData(query, start_date, end_date):
    """
    Scrape Google News search results for a given query and date range.
    query: str - search query
    start_date: str - start date in the format yyyy-mm-dd or mm/dd/yyyy
    end_date: str - end date in the format yyyy-mm-dd or mm/dd/yyyy
    """
    if "-" in start_date:
        start_date = datetime.strptime(start_date, "%Y-%m-%d")
        start_date = start_date.strftime("%m/%d/%Y")
    if "-" in end_date:
        end_date = datetime.strptime(end_date, "%Y-%m-%d")
        end_date = end_date.strftime("%m/%d/%Y")

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/101.0.4951.54 Safari/537.36"
        )
    }

    news_results = []
    page = 0
    while True:
        offset = page * 10
        url = (
            f"https://www.google.com/search?q={query}"
            f"&tbs=cdr:1,cd_min:{start_date},cd_max:{end_date}"
            f"&tbm=nws&start={offset}"
        )

        try:
            print(f"获取Google新闻: {url} 获取第{page}页 ")
            response = make_request(url, headers)
            soup = BeautifulSoup(response.content, "html.parser")
            results_on_page = soup.select("div.SoaBEf")

            if not results_on_page:
                break  # No more results found

            for el in results_on_page:
                try:
                    link = el.find("a")["href"]
                    title = el.select_one("div.MBeuO").get_text()
                    snippet = el.select_one(".GI74Re").get_text()
                    date = el.select_one(".LfVVr").get_text()
                    source = el.select_one(".NUnG9d span").get_text()
                    news_results.append(
                        {
                            "link": link,
                            "title": title,
                            "snippet": snippet,
                            "date": date,
                            "source": source,
                        }
                    )
                except Exception as e:
                    logger.error(f"Error processing result: {e}")
                    # If one of the fields is not found, skip this result
                    continue

            # Update the progress bar with the current count of results scraped

            # Check for the "Next" link (pagination)
            next_link = soup.find("a", id="pnnext")
            if not next_link:
                break

            page += 1

        except requests.exceptions.Timeout as e:
            logger.error(f"连接超时: {e}")
            # 不立即中断，记录错误后继续尝试下一页
            page += 1
            if page > 3:  # 如果连续多页都超时，则退出循环
                logger.error("多次连接超时，停止获取Google新闻")
                break
            continue
        except requests.exceptions.ConnectionError as e:
            logger.error(f"连接错误: {e}")
            # 不立即中断，记录错误后继续尝试下一页
            page += 1
            if page > 3:  # 如果连续多页都连接错误，则退出循环
                logger.error("多次连接错误，停止获取Google新闻")
                break
            continue
        except Exception as e:
            logger.error(f"获取Google新闻失败: {e}")
            break

    return news_results


def fetch_single_page(url, headers, page_num):
    """
    获取单页Google新闻数据的函数，用于并发调用
    """
    try:
        logger.info(f"开始获取第{page_num}页: {url}")
        # 添加随机延迟以避免被检测
        time.sleep(random.uniform(0.5, 2))
        response = make_request(url, headers)
        soup = BeautifulSoup(response.content, "html.parser")
        results_on_page = soup.select("div.SoaBEf")

        page_results = []
        has_next = False

        if results_on_page:
            logger.info(f"第{page_num}页找到{len(results_on_page)}个新闻元素")
            for el in results_on_page:
                try:
                    link = el.find("a")["href"]
                    title = el.select_one("div.MBeuO").get_text()
                    snippet = el.select_one(".GI74Re").get_text()
                    date = el.select_one(".LfVVr").get_text()
                    source = el.select_one(".NUnG9d span").get_text()
                    page_results.append(
                        {
                            "link": link,
                            "title": title,
                            "snippet": snippet,
                            "date": date,
                            "source": source,
                        }
                    )
                except Exception as e:
                    logger.warning(f"第{page_num}页处理单个结果时出错: {e}")
                    continue

            # 检查是否有下一页
            next_link = soup.find("a", id="pnnext")
            has_next = next_link is not None
            logger.info(
                f"第{page_num}页成功解析{len(page_results)}条新闻，有下一页: {has_next}"
            )
        else:
            logger.warning(f"第{page_num}页没有找到新闻元素")

        return {
            "page": page_num,
            "results": page_results,
            "has_next": has_next,
            "success": True,
            "error": None,
        }

    except requests.exceptions.Timeout as e:
        logger.error(f"第{page_num}页连接超时: {e}")
        return {
            "page": page_num,
            "results": [],
            "has_next": False,
            "success": False,
            "error": "timeout",
        }
    except requests.exceptions.ConnectionError as e:
        logger.error(f"第{page_num}页连接错误: {e}")
        return {
            "page": page_num,
            "results": [],
            "has_next": False,
            "success": False,
            "error": "connection_error",
        }
    except requests.exceptions.SSLError as e:
        error_msg = f"第{page_num}页SSL错误: {e}"
        logger.error(error_msg)
        return {
            "page": page_num,
            "results": [],
            "has_next": False,
            "success": False,
            "error": "ssl_error",
        }
    except Exception as e:
        error_msg = f"第{page_num}页获取失败: {e}"
        logger.error(error_msg)
        return {
            "page": page_num,
            "results": [],
            "has_next": False,
            "success": False,
            "error": str(e),
        }


def getNewsDataConcurrent(query, start_date, end_date, max_workers=3, max_pages=10):
    """
    并发版本的Google新闻数据获取函数
    query: str - 搜索查询
    start_date: str - 开始日期，格式为 yyyy-mm-dd 或 mm/dd/yyyy
    end_date: str - 结束日期，格式为 yyyy-mm-dd 或 mm/dd/yyyy
    max_workers: int - 并发线程数，默认为3（避免过于频繁的请求）
    max_pages: int - 最大页数，默认为10
    """
    # 日期格式转换
    if "-" in start_date:
        start_date = datetime.strptime(start_date, "%Y-%m-%d")
        start_date = start_date.strftime("%m/%d/%Y")
    if "-" in end_date:
        end_date = datetime.strptime(end_date, "%Y-%m-%d")
        end_date = end_date.strftime("%m/%d/%Y")

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/101.0.4951.54 Safari/537.36"
        )
    }

    all_news_results = []

    # 第一步：先获取第一页来确定是否有结果
    first_page_url = (
        f"https://www.google.com/search?q={query}"
        f"&tbs=cdr:1,cd_min:{start_date},cd_max:{end_date}"
        f"&tbm=nws&start=0"
    )

    first_page_result = fetch_single_page(first_page_url, headers, 0)

    if not first_page_result["success"] or not first_page_result["results"]:
        logger.warning("第一页没有获取到结果，停止搜索")
        return []

    all_news_results.extend(first_page_result["results"])

    if not first_page_result["has_next"]:
        logger.info("只有一页结果")
        return all_news_results

    # 第二步：并发获取后续页面
    # 使用ThreadPoolExecutor进行并发请求
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # 创建URL列表（从第2页开始）
        future_to_page = {}

        for page in range(1, max_pages):
            offset = page * 10
            url = (
                f"https://www.google.com/search?q={query}"
                f"&tbs=cdr:1,cd_min:{start_date},cd_max:{end_date}"
                f"&tbm=nws&start={offset}"
            )
            future = executor.submit(fetch_single_page, url, headers, page)
            future_to_page[future] = page

        # 收集结果
        successful_pages = 1  # 第一页已经成功
        failed_pages = 0

        for future in as_completed(future_to_page):
            page_num = future_to_page[future]
            try:
                result = future.result()

                if result["success"] and result["results"]:
                    all_news_results.extend(result["results"])
                    successful_pages += 1
                    logger.info(
                        f"第{page_num}页获取成功，获得{len(result['results'])}条结果"
                    )

                    # 如果这一页没有下一页标记，说明已经到最后一页了
                    if not result["has_next"]:
                        logger.info(f"第{page_num}页是最后一页，停止获取")
                        break
                else:
                    failed_pages += 1
                    logger.warning(
                        f"第{page_num}页获取失败: {result.get('error', '未知错误')}"
                    )

                    # 如果连续失败页数过多，停止获取
                    if failed_pages >= 3:
                        logger.warning("连续失败页数过多，停止获取")
                        break

            except Exception as e:
                failed_pages += 1
                logger.error(f"处理第{page_num}页结果时出错: {e}")

                if failed_pages >= 3:
                    logger.warning("连续失败页数过多，停止获取")
                    break

    logger.info(
        f"并发获取完成，成功获取{successful_pages}页，失败{failed_pages}页，总共{len(all_news_results)}条新闻"
    )
    return all_news_results


def getNewsDataWithFallback(query, start_date, end_date, max_workers=3, max_pages=10):
    """
    带回退机制的新闻获取函数：优先使用并发版本，失败时回退到串行版本
    query: str - 搜索查询
    start_date: str - 开始日期，格式为 yyyy-mm-dd 或 mm/dd/yyyy
    end_date: str - 结束日期，格式为 yyyy-mm-dd 或 mm/dd/yyyy
    max_workers: int - 并发线程数，默认为3
    max_pages: int - 最大页数，默认为10
    """
    logger.info(f"开始获取新闻，查询: {query}, 日期范围: {start_date} 到 {end_date}")

    # 首先尝试并发版本
    try:
        logger.info("尝试使用并发模式获取新闻...")
        results = getNewsDataConcurrent(
            query, start_date, end_date, max_workers, max_pages
        )

        if results and len(results) > 0:
            logger.info(f"并发模式成功获取{len(results)}条新闻")
            return results
        else:
            logger.warning("并发模式没有获取到结果，回退到串行模式")

    except Exception as e:
        logger.error(f"并发模式失败: {e}, 回退到串行模式")

    # 回退到串行版本
    try:
        logger.info("使用串行模式获取新闻...")
        results = getNewsData(query, start_date, end_date)

        if results and len(results) > 0:
            logger.info(f"串行模式成功获取{len(results)}条新闻")
            return results
        else:
            logger.warning("串行模式也没有获取到结果")
            return []

    except Exception as e:
        logger.error(f"串行模式也失败: {e}")
        return []
