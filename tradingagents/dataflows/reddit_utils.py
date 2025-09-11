import time
import json
from datetime import datetime
from typing import Annotated, List, Dict, Optional
import os
import re
from pathlib import Path
import logging
from tqdm import tqdm

# 导入Reddit API库
try:
    import praw

    PRAW_AVAILABLE = True
except ImportError:
    PRAW_AVAILABLE = False
    print("警告: praw库未安装，Reddit下载功能将不可用。请运行: pip install praw")

ticker_to_company = {
    "AAPL": "Apple",
    "MSFT": "Microsoft",
    "GOOGL": "Google",
    "AMZN": "Amazon",
    "TSLA": "Tesla",
    "NVDA": "Nvidia",
    "TSM": "Taiwan Semiconductor Manufacturing Company OR TSMC",
    "JPM": "JPMorgan Chase OR JP Morgan",
    "JNJ": "Johnson & Johnson OR JNJ",
    "V": "Visa",
    "WMT": "Walmart",
    "META": "Meta OR Facebook",
    "AMD": "AMD",
    "INTC": "Intel",
    "QCOM": "Qualcomm",
    "BABA": "Alibaba",
    "ADBE": "Adobe",
    "NFLX": "Netflix",
    "CRM": "Salesforce",
    "PYPL": "PayPal",
    "PLTR": "Palantir",
    "MU": "Micron",
    "SQ": "Block OR Square",
    "ZM": "Zoom",
    "CSCO": "Cisco",
    "SHOP": "Shopify",
    "ORCL": "Oracle",
    "X": "Twitter OR X",
    "SPOT": "Spotify",
    "AVGO": "Broadcom",
    "ASML": "ASML ",
    "TWLO": "Twilio",
    "SNAP": "Snap Inc.",
    "TEAM": "Atlassian",
    "SQSP": "Squarespace",
    "UBER": "Uber",
    "ROKU": "Roku",
    "PINS": "Pinterest",
}

# 配置日志
logger = logging.getLogger(__name__)

# 默认subreddit配置
DEFAULT_SUBREDDITS = {
    "global_news": [
        "worldnews",
        "news",
        "business",
        "economy",
        "finance",
        "markets",
        "investing",
    ],
    "company_news": [
        "stocks",
        "investing",
        "SecurityAnalysis",
        "ValueInvesting",
        "StockMarket",
        "wallstreetbets",
        "financialindependence",
    ],
    "crypto_news": [
        "CryptoCurrency",
        "Bitcoin",
        "ethereum",
        "CryptoMarkets",
        "altcoin",
    ],
}


class RedditDataDownloader:
    """Reddit数据下载器"""

    def __init__(
        self,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
        user_agent: Optional[str] = None,
        data_dir: Optional[str] = None,
    ):
        """
        初始化Reddit下载器

        Args:
            client_id: Reddit客户端ID
            client_secret: Reddit客户端密钥
            user_agent: 用户代理字符串
            data_dir: 数据存储目录
        """
        if not PRAW_AVAILABLE:
            raise ImportError("praw库未安装，请运行: pip install praw")

        # 获取API凭证
        self.client_id = client_id or os.getenv("REDDIT_CLIENT_ID")
        self.client_secret = client_secret or os.getenv("REDDIT_CLIENT_SECRET")
        self.user_agent = user_agent or os.getenv(
            "REDDIT_USER_AGENT", "TradingAgents/1.0"
        )

        if not all([self.client_id, self.client_secret]):
            raise ValueError(
                "Reddit API凭证未配置。请设置REDDIT_CLIENT_ID和REDDIT_CLIENT_SECRET环境变量"
            )

        # 设置数据目录
        self.data_dir = Path(data_dir or "data/reddit_data")
        self.data_dir.mkdir(parents=True, exist_ok=True)

        # 初始化Reddit API客户端
        try:
            self.reddit = praw.Reddit(
                client_id=self.client_id,
                client_secret=self.client_secret,
                user_agent=self.user_agent,
            )
            # 测试连接
            self.reddit.user.me()
            logger.info("✅ Reddit API连接成功")
        except Exception as e:
            logger.error(f"❌ Reddit API连接失败: {e}")
            raise

    def download_subreddit_data(
        self,
        subreddit_name: str,
        category: str = "hot",
        limit: int = 100,
        time_filter: str = "week",
    ) -> List[Dict]:
        """
        从指定subreddit下载数据

        Args:
            subreddit_name: subreddit名称
            category: 帖子分类 (hot, new, top, rising)
            limit: 下载数量限制
            time_filter: 时间筛选 (all, day, week, month, year) - 仅对top有效

        Returns:
            List[Dict]: 帖子数据列表
        """
        try:
            logger.info(
                f"📥 开始下载 r/{subreddit_name} 的{category}帖子 (限制: {limit})"
            )

            subreddit = self.reddit.subreddit(subreddit_name)

            # 根据分类获取帖子
            if category == "hot":
                posts = subreddit.hot(limit=limit)
            elif category == "new":
                posts = subreddit.new(limit=limit)
            elif category == "top":
                posts = subreddit.top(time_filter=time_filter, limit=limit)
            elif category == "rising":
                posts = subreddit.rising(limit=limit)
            else:
                logger.warning(f"未知分类 {category}，使用默认的hot")
                posts = subreddit.hot(limit=limit)

            results = []
            for post in posts:
                try:
                    post_data = {
                        "id": post.id,
                        "title": post.title,
                        "selftext": post.selftext,
                        "url": post.url,
                        "ups": post.ups,
                        "downs": getattr(post, "downs", 0),
                        "score": post.score,
                        "upvote_ratio": post.upvote_ratio,
                        "num_comments": post.num_comments,
                        "created_utc": post.created_utc,
                        "author": str(post.author) if post.author else "[deleted]",
                        "subreddit": post.subreddit.display_name,
                        "permalink": f"https://reddit.com{post.permalink}",
                        "is_self": post.is_self,
                        "domain": post.domain,
                        "stickied": post.stickied,
                        "over_18": post.over_18,
                        "spoiler": post.spoiler,
                        "locked": post.locked,
                    }
                    results.append(post_data)

                    # 添加延迟以避免触发API限制
                    time.sleep(0.1)

                except Exception as e:
                    logger.warning(f"获取帖子数据失败: {e}")
                    continue

            logger.info(f"✅ 成功下载 {len(results)} 个帖子从 r/{subreddit_name}")
            return results

        except Exception as e:
            logger.error(f"❌ 下载 r/{subreddit_name} 数据失败: {e}")
            return []

    def save_posts_to_jsonl(self, posts: List[Dict], file_path: Path) -> bool:
        """
        将帖子数据保存为JSONL格式

        Args:
            posts: 帖子数据列表
            file_path: 保存文件路径

        Returns:
            bool: 保存是否成功
        """
        try:
            file_path.parent.mkdir(parents=True, exist_ok=True)

            with open(file_path, "w", encoding="utf-8") as f:
                for post in posts:
                    json.dump(post, f, ensure_ascii=False)
                    f.write("\n")

            logger.info(f"💾 成功保存 {len(posts)} 个帖子到 {file_path}")
            return True

        except Exception as e:
            logger.error(f"❌ 保存文件失败 {file_path}: {e}")
            return False

    def download_category_data(
        self,
        category: str,
        subreddits: Optional[List[str]] = None,
        limit_per_subreddit: int = 100,
        category_type: str = "hot",
        time_filter: str = "week",
        force_refresh: bool = False,
    ) -> bool:
        """
        下载指定分类的所有subreddit数据

        Args:
            category: 分类名称 (global_news, company_news, crypto_news 等)
            subreddits: subreddit列表，如果为None则使用默认配置
            limit_per_subreddit: 每个subreddit的下载限制
            category_type: 帖子分类 (hot, new, top, rising)
            time_filter: 时间筛选
            force_refresh: 是否强制刷新已存在的文件

        Returns:
            bool: 下载是否成功
        """
        try:
            # 使用提供的subreddit列表或默认配置
            if subreddits is None:
                subreddits = DEFAULT_SUBREDDITS.get(category, [])

            if not subreddits:
                logger.error(f"❌ 未找到分类 {category} 的subreddit配置")
                return False

            # 创建分类目录
            category_dir = self.data_dir / category
            category_dir.mkdir(parents=True, exist_ok=True)

            logger.info(f"🚀 开始下载分类 {category} 数据")
            logger.info(f"📋 Subreddits: {subreddits}")
            logger.info(f"📊 每个subreddit限制: {limit_per_subreddit}")

            success_count = 0
            total_posts = 0

            with tqdm(subreddits, desc=f"下载 {category}") as pbar:
                for subreddit_name in pbar:
                    pbar.set_description(f"下载 r/{subreddit_name}")

                    # 检查文件是否已存在
                    file_path = category_dir / f"{subreddit_name}.jsonl"
                    if file_path.exists() and not force_refresh:
                        logger.info(f"📄 文件已存在，跳过: {file_path}")
                        continue

                    # 下载数据
                    posts = self.download_subreddit_data(
                        subreddit_name=subreddit_name,
                        category=category_type,
                        limit=limit_per_subreddit,
                        time_filter=time_filter,
                    )

                    if posts:
                        # 保存数据
                        if self.save_posts_to_jsonl(posts, file_path):
                            success_count += 1
                            total_posts += len(posts)

                    # 添加延迟以避免API限制
                    time.sleep(1)

            logger.info(f"🎉 分类 {category} 下载完成!")
            logger.info(f"📊 成功: {success_count}/{len(subreddits)} 个subreddit")
            logger.info(f"📝 总计下载: {total_posts} 个帖子")

            return success_count > 0

        except Exception as e:
            logger.error(f"❌ 下载分类 {category} 失败: {e}")
            return False

    def download_all_categories(
        self,
        limit_per_subreddit: int = 100,
        category_type: str = "hot",
        time_filter: str = "week",
        force_refresh: bool = False,
    ) -> Dict[str, bool]:
        """
        下载所有预配置分类的数据

        Args:
            limit_per_subreddit: 每个subreddit的下载限制
            category_type: 帖子分类
            time_filter: 时间筛选
            force_refresh: 是否强制刷新

        Returns:
            Dict[str, bool]: 各分类的下载结果
        """
        results = {}

        logger.info("🌍 开始下载所有分类的Reddit数据")

        for category in DEFAULT_SUBREDDITS.keys():
            logger.info(f"\n📂 处理分类: {category}")
            results[category] = self.download_category_data(
                category=category,
                limit_per_subreddit=limit_per_subreddit,
                category_type=category_type,
                time_filter=time_filter,
                force_refresh=force_refresh,
            )

        # 输出总结
        successful = sum(results.values())
        total = len(results)
        logger.info("\n🏁 全部下载完成!")
        logger.info(f"📊 成功: {successful}/{total} 个分类")

        return results


def fetch_top_from_category(
    category: Annotated[
        str, "Category to fetch top post from. Collection of subreddits."
    ],
    date: Annotated[str, "Date to fetch top posts from."],
    max_limit: Annotated[int, "Maximum number of posts to fetch."],
    query: Annotated[str, "Optional query to search for in the subreddit."] = None,
    data_path: Annotated[
        str,
        "Path to the data folder. Default is 'reddit_data'.",
    ] = "reddit_data",
):
    base_path = data_path

    all_content = []

    # 检查分类目录是否存在
    category_path = os.path.join(base_path, category)
    if not os.path.exists(category_path):
        logger.warning(f"⚠️ Reddit数据目录不存在: {category_path}")
        return []

    # 只计算 .jsonl 文件的数量
    jsonl_files = [f for f in os.listdir(category_path) if f.endswith(".jsonl")]

    if len(jsonl_files) == 0:
        logger.warning(f"⚠️ 在 {category_path} 中没有找到 .jsonl 文件")
        return []

    # 修复逻辑：确保每个subreddit至少可以获取1个帖子
    if max_limit < len(jsonl_files):
        logger.warning(
            f"⚠️ max_limit ({max_limit}) 小于 .jsonl 文件数量 ({len(jsonl_files)})，"
            f"每个subreddit只能获取1个帖子"
        )
        limit_per_subreddit = 1
    else:
        limit_per_subreddit = max_limit // len(jsonl_files)

    for data_file in os.listdir(os.path.join(base_path, category)):
        # check if data_file is a .jsonl file
        if not data_file.endswith(".jsonl"):
            continue

        all_content_curr_subreddit = []

        with open(os.path.join(base_path, category, data_file), "rb") as f:
            for i, line in enumerate(f):
                # skip empty lines
                if not line.strip():
                    continue

                parsed_line = json.loads(line)

                # select only lines that are from the date
                post_date = datetime.utcfromtimestamp(
                    parsed_line["created_utc"]
                ).strftime("%Y-%m-%d")
                if post_date != date:
                    continue

                # if is company_news, check that the title or the content has the company's name (query) mentioned
                if "company" in category and query:
                    search_terms = []
                    if "OR" in ticker_to_company[query]:
                        search_terms = ticker_to_company[query].split(" OR ")
                    else:
                        search_terms = [ticker_to_company[query]]

                    search_terms.append(query)

                    found = False
                    for term in search_terms:
                        if re.search(
                            term, parsed_line["title"], re.IGNORECASE
                        ) or re.search(term, parsed_line["selftext"], re.IGNORECASE):
                            found = True
                            break

                    if not found:
                        continue

                post = {
                    "title": parsed_line["title"],
                    "content": parsed_line["selftext"],
                    "url": parsed_line["url"],
                    "upvotes": parsed_line["ups"],
                    "posted_date": post_date,
                }

                all_content_curr_subreddit.append(post)

        # sort all_content_curr_subreddit by upvote_ratio in descending order
        all_content_curr_subreddit.sort(key=lambda x: x["upvotes"], reverse=True)

        all_content.extend(all_content_curr_subreddit[:limit_per_subreddit])

    return all_content


# 便捷函数
def download_reddit_data(
    category: str = "all",
    limit_per_subreddit: int = 100,
    category_type: str = "hot",
    time_filter: str = "week",
    force_refresh: bool = False,
    data_dir: Optional[str] = None,
) -> Dict[str, bool]:
    """
    便捷的Reddit数据下载函数

    Args:
        category: 要下载的分类 ("all", "global_news", "company_news", "crypto_news")
        limit_per_subreddit: 每个subreddit的下载限制
        category_type: 帖子分类 (hot, new, top, rising)
        time_filter: 时间筛选 (all, day, week, month, year)
        force_refresh: 是否强制刷新已存在的文件
        data_dir: 数据存储目录

    Returns:
        Dict[str, bool]: 下载结果
    """
    try:
        downloader = RedditDataDownloader(data_dir=data_dir)

        if category == "all":
            return downloader.download_all_categories(
                limit_per_subreddit=limit_per_subreddit,
                category_type=category_type,
                time_filter=time_filter,
                force_refresh=force_refresh,
            )
        else:
            result = downloader.download_category_data(
                category=category,
                limit_per_subreddit=limit_per_subreddit,
                category_type=category_type,
                time_filter=time_filter,
                force_refresh=force_refresh,
            )
            return {category: result}

    except Exception as e:
        logger.error(f"❌ Reddit数据下载失败: {e}")
        return {}


def download_custom_subreddits(
    subreddits: List[str],
    category_name: str = "custom",
    limit_per_subreddit: int = 100,
    category_type: str = "hot",
    time_filter: str = "week",
    force_refresh: bool = False,
    data_dir: Optional[str] = None,
) -> bool:
    """
    下载自定义subreddit列表的数据

    Args:
        subreddits: subreddit名称列表
        category_name: 分类名称
        limit_per_subreddit: 每个subreddit的下载限制
        category_type: 帖子分类
        time_filter: 时间筛选
        force_refresh: 是否强制刷新
        data_dir: 数据存储目录

    Returns:
        bool: 下载是否成功
    """
    try:
        downloader = RedditDataDownloader(data_dir=data_dir)
        return downloader.download_category_data(
            category=category_name,
            subreddits=subreddits,
            limit_per_subreddit=limit_per_subreddit,
            category_type=category_type,
            time_filter=time_filter,
            force_refresh=force_refresh,
        )
    except Exception as e:
        logger.error(f"❌ 自定义subreddit下载失败: {e}")
        return False


# 使用示例函数
def demo_usage():
    """演示如何使用Reddit下载功能"""

    print("🔧 Reddit数据下载器使用示例")
    print("=" * 50)

    # 示例1: 下载所有预配置分类
    print("\n📥 示例1: 下载所有分类的数据")
    print("download_reddit_data(category='all', limit_per_subreddit=50)")

    # 示例2: 只下载公司新闻
    print("\n📥 示例2: 只下载公司新闻")
    print("download_reddit_data(category='company_news', limit_per_subreddit=100)")

    # 示例3: 下载自定义subreddit
    print("\n📥 示例3: 下载自定义subreddit")
    print(
        "download_custom_subreddits(['wallstreetbets', 'investing'], 'trading_focus')"
    )

    # 示例4: 下载最热门的帖子
    print("\n📥 示例4: 下载最热门的帖子")
    print(
        "download_reddit_data(category='global_news', category_type='top', time_filter='week')"
    )

    print("\n💡 提示:")
    print("1. 确保设置了REDDIT_CLIENT_ID和REDDIT_CLIENT_SECRET环境变量")
    print("2. 安装praw库: pip install praw")
    print("3. 数据将保存到data/reddit_data/目录下")
    print("4. 每个subreddit保存为单独的.jsonl文件")


if __name__ == "__main__":
    """直接运行此文件时的示例"""
    import argparse

    parser = argparse.ArgumentParser(description="Reddit数据下载工具")
    parser.add_argument(
        "--category",
        default="company_news",
        choices=["all", "global_news", "company_news", "crypto_news"],
        help="要下载的分类",
    )
    parser.add_argument(
        "--limit", type=int, default=100, help="每个subreddit的下载限制"
    )
    parser.add_argument(
        "--type",
        default="hot",
        choices=["hot", "new", "top", "rising"],
        help="帖子分类",
    )
    parser.add_argument(
        "--time-filter",
        default="week",
        choices=["all", "day", "week", "month", "year"],
        help="时间筛选",
    )
    parser.add_argument(
        "--force-refresh", action="store_true", help="强制刷新已存在的文件"
    )
    parser.add_argument("--demo", action="store_true", help="显示使用示例")
    parser.add_argument("--data-dir", default=None, help="数据存储目录")

    args = parser.parse_args()

    if args.demo:
        demo_usage()
    else:
        # 配置日志
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        )

        print("🚀 开始下载Reddit数据")
        print(f"📂 分类: {args.category}")
        print(f"📊 限制: {args.limit}")
        print(f"🏷️ 类型: {args.type}")
        print(f"⏰ 时间筛选: {args.time_filter}")
        print(f"🔄 强制刷新: {args.force_refresh}")

        results = download_reddit_data(
            category=args.category,
            limit_per_subreddit=args.limit,
            category_type=args.type,
            time_filter=args.time_filter,
            force_refresh=args.force_refresh,
            data_dir=args.data_dir,
        )

        print("\n🎉 下载完成!")
        print(f"📊 结果: {results}")
