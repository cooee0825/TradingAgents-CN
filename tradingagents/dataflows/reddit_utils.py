import time
import json
from datetime import datetime
from typing import Annotated, List, Dict, Optional
import os
import re
from pathlib import Path
import logging
from sqlalchemy import false
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

# 股票专用subreddit配置
STOCK_SUBREDDITS = [
    "wallstreetbets",
    "stocks",
    "investing",
    "StockMarket",
    "SecurityAnalysis",
    "ValueInvesting",
]

# subreddit权重配置 (用于热度计算)
SUBREDDIT_WEIGHTS = {
    "wallstreetbets": 1.0,  # 影响力最大
    "stocks": 0.8,
    "investing": 0.7,
    "StockMarket": 0.6,
    "SecurityAnalysis": 0.5,
    "ValueInvesting": 0.4,
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
        将帖子数据保存为JSONL格式，支持去重和增量更新

        Args:
            posts: 帖子数据列表
            file_path: 保存文件路径

        Returns:
            bool: 保存是否成功
        """
        try:
            file_path.parent.mkdir(parents=True, exist_ok=True)

            # 读取现有数据
            existing_posts = {}
            if file_path.exists():
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        for line in f:
                            line = line.strip()
                            if line:
                                try:
                                    post_data = json.loads(line)
                                    if "id" in post_data:
                                        existing_posts[post_data["id"]] = post_data
                                except json.JSONDecodeError as e:
                                    logger.warning(f"⚠️ 跳过无效的JSON行: {e}")
                                    continue
                except Exception as e:
                    logger.warning(f"⚠️ 读取现有文件失败，将创建新文件: {e}")

            # 处理新帖子数据
            new_posts = 0
            updated_posts = 0
            skipped_posts = 0

            for post in posts:
                if "id" not in post:
                    logger.warning("⚠️ 帖子缺少ID，跳过")
                    continue

                post_id = post["id"]

                if post_id in existing_posts:
                    # 比较帖子内容是否有更新
                    existing_post = existing_posts[post_id]

                    # 检查关键字段是否有变化
                    key_fields = [
                        "title",
                        "selftext",
                        "score",
                        "ups",
                        "num_comments",
                        "upvote_ratio",
                    ]
                    has_changes = False

                    for field in key_fields:
                        if post.get(field) != existing_post.get(field):
                            has_changes = True
                            break

                    if has_changes:
                        # 更新帖子数据，保留创建时间等原有信息
                        updated_post = existing_post.copy()
                        updated_post.update(post)
                        updated_post["last_updated"] = datetime.now().isoformat()
                        existing_posts[post_id] = updated_post
                        updated_posts += 1
                        logger.debug(f"🔄 更新帖子: {post_id}")
                    else:
                        # 内容无变化，跳过
                        skipped_posts += 1
                        logger.debug(f"⏭️ 帖子无变化，跳过: {post_id}")
                else:
                    # 新帖子
                    post["first_saved"] = datetime.now().isoformat()
                    existing_posts[post_id] = post
                    new_posts += 1
                    logger.debug(f"➕ 新增帖子: {post_id}")

            # 保存所有数据
            with open(file_path, "w", encoding="utf-8") as f:
                for post_data in existing_posts.values():
                    json.dump(post_data, f, ensure_ascii=False)
                    f.write("\n")

            total_posts = len(existing_posts)
            logger.info(f"💾 成功保存到 {file_path}")
            logger.info(
                f"📊 统计: 总计 {total_posts} 个帖子 (新增 {new_posts}, 更新 {updated_posts}, 跳过 {skipped_posts})"
            )

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
            force_refresh: 是否强制刷新，由于已支持增量更新，此参数主要用于日志显示

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


class StockPopularityAnalyzer:
    """股票热度分析器"""

    def __init__(self, data_dir: Optional[str] = None):
        """
        初始化股票热度分析器

        Args:
            data_dir: Reddit数据存储目录
        """
        self.data_dir = Path(data_dir or "data/reddit_data")

    def generate_stock_keywords(self, ticker: str) -> List[str]:
        """
        生成股票的关键词列表，用于匹配

        Args:
            ticker: 股票代码 (如 "AAPL")

        Returns:
            List[str]: 关键词列表
        """
        keywords = []

        # 基础股票代码匹配
        keywords.extend(
            [
                ticker,
                f"${ticker}",
                f"${ticker.upper()}",
                f"{ticker.upper()}",
                f"{ticker.lower()}",
            ]
        )

        # 从映射表获取公司名称
        if ticker in ticker_to_company:
            company_names = ticker_to_company[ticker]
            if " OR " in company_names:
                # 处理多个名称的情况
                for name in company_names.split(" OR "):
                    keywords.append(name.strip())
            else:
                keywords.append(company_names)

        # 去重并返回
        return list(set(keywords))

    def calculate_post_relevance(self, post: Dict, keywords: List[str]) -> float:
        """
        计算帖子与股票的相关度

        Args:
            post: 帖子数据
            keywords: 关键词列表

        Returns:
            float: 相关度分数 (0-1)
        """
        title = post.get("title", "").lower()
        content = post.get("selftext", "").lower()

        # 标题匹配权重更高
        title_matches = 0
        content_matches = 0

        for keyword in keywords:
            keyword_lower = keyword.lower()

            # 精确匹配
            if keyword_lower in title:
                title_matches += 1
            if keyword_lower in content:
                content_matches += 1

            # 单词边界匹配 (避免部分匹配)
            import re

            pattern = r"\b" + re.escape(keyword_lower) + r"\b"
            if re.search(pattern, title):
                title_matches += 2  # 更高权重
            if re.search(pattern, content):
                content_matches += 1

        # 计算相关度分数
        title_score = min(title_matches * 0.3, 1.0)  # 标题最高贡献0.3
        content_score = min(content_matches * 0.1, 0.7)  # 内容最高贡献0.7

        return min(title_score + content_score, 1.0)

    def calculate_post_popularity_score(
        self, post: Dict, subreddit_weight: float = 1.0
    ) -> float:
        """
        计算帖子的热度分数

        Args:
            post: 帖子数据
            subreddit_weight: subreddit权重

        Returns:
            float: 热度分数
        """
        # 基础互动数据
        ups = post.get("ups", 0)
        comments = post.get("num_comments", 0)
        score = post.get("score", 0)
        upvote_ratio = post.get("upvote_ratio", 0.5)

        # 时间衰减因子 (越新的帖子权重越高)
        created_utc = post.get("created_utc", 0)
        current_time = time.time()
        time_diff_hours = (current_time - created_utc) / 3600

        # 24小时内为1.0，之后逐渐衰减
        time_decay = max(0.1, 1.0 / (1 + time_diff_hours / 24))

        # 计算基础热度分数
        engagement_score = (ups * 1.0) + (comments * 0.8) + (score * 0.6)
        quality_score = upvote_ratio * 0.5

        # 综合分数
        total_score = (engagement_score + quality_score) * subreddit_weight * time_decay

        return total_score

    def analyze_stock_popularity(
        self,
        ticker: str,
        subreddits: Optional[List[str]] = None,
        min_relevance: float = 0.1,
        days_back: int = 7,
    ) -> Dict:
        """
        分析指定股票的热度

        Args:
            ticker: 股票代码
            subreddits: 要分析的subreddit列表，默认使用STOCK_SUBREDDITS
            min_relevance: 最小相关度阈值
            days_back: 分析过去几天的数据

        Returns:
            Dict: 分析结果
        """
        if subreddits is None:
            subreddits = STOCK_SUBREDDITS

        keywords = self.generate_stock_keywords(ticker)

        # 计算时间范围
        cutoff_time = time.time() - (days_back * 24 * 3600)

        results = {
            "ticker": ticker,
            "keywords": keywords,
            "analysis_period_days": days_back,
            "total_mentions": 0,
            "total_popularity_score": 0.0,
            "subreddit_breakdown": {},
            "top_posts": [],
            "average_sentiment": 0.0,
            "timestamp": datetime.now().isoformat(),
        }

        all_relevant_posts = []

        for subreddit_name in subreddits:
            subreddit_data = {
                "name": subreddit_name,
                "mentions": 0,
                "popularity_score": 0.0,
                "posts": [],
            }

            # 获取subreddit权重
            weight = SUBREDDIT_WEIGHTS.get(subreddit_name, 0.5)

            # 读取subreddit数据文件
            data_file = self.data_dir / "company_news" / f"{subreddit_name}.jsonl"
            if not data_file.exists():
                logger.warning(f"⚠️ 数据文件不存在: {data_file}")
                continue

            try:
                with open(data_file, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if not line:
                            continue

                        try:
                            post = json.loads(line)

                            # 时间过滤
                            if post.get("created_utc", 0) < cutoff_time:
                                continue

                            # 计算相关度
                            relevance = self.calculate_post_relevance(post, keywords)
                            if relevance < min_relevance:
                                continue

                            # 计算热度分数
                            popularity_score = self.calculate_post_popularity_score(
                                post, weight
                            )

                            # 添加到结果
                            post_result = {
                                "id": post.get("id"),
                                "title": post.get("title"),
                                "subreddit": subreddit_name,
                                "score": post.get("score", 0),
                                "comments": post.get("num_comments", 0),
                                "upvotes": post.get("ups", 0),
                                "relevance": relevance,
                                "popularity_score": popularity_score,
                                "url": post.get("permalink", ""),
                                "created_utc": post.get("created_utc"),
                            }

                            subreddit_data["posts"].append(post_result)
                            all_relevant_posts.append(post_result)
                            subreddit_data["mentions"] += 1
                            subreddit_data["popularity_score"] += popularity_score

                        except json.JSONDecodeError as e:
                            logger.warning(f"⚠️ JSON解析错误: {e}")
                            continue

            except Exception as e:
                logger.error(f"❌ 读取文件失败 {data_file}: {e}")
                continue

            results["subreddit_breakdown"][subreddit_name] = subreddit_data

        # 计算总体统计
        results["total_mentions"] = len(all_relevant_posts)
        results["total_popularity_score"] = sum(
            post["popularity_score"] for post in all_relevant_posts
        )

        # 获取热门帖子 (按热度分数排序)
        all_relevant_posts.sort(key=lambda x: x["popularity_score"], reverse=True)
        results["top_posts"] = all_relevant_posts[:10]  # 取前10个

        # 计算平均分数
        if results["total_mentions"] > 0:
            results["average_popularity_score"] = (
                results["total_popularity_score"] / results["total_mentions"]
            )
        else:
            results["average_popularity_score"] = 0.0

        logger.info(
            f"📊 {ticker} 分析完成: {results['total_mentions']} 次提及, 总热度: {results['total_popularity_score']:.2f}"
        )

        return results

    def generate_stock_popularity_ranking(
        self,
        tickers: Optional[List[str]] = None,
        subreddits: Optional[List[str]] = None,
        min_relevance: float = 0.1,
        days_back: int = 7,
        top_n: int = 20,
    ) -> Dict:
        """
        生成股票热度排行榜

        Args:
            tickers: 要分析的股票代码列表，默认使用ticker_to_company中的所有股票
            subreddits: 要分析的subreddit列表
            min_relevance: 最小相关度阈值
            days_back: 分析过去几天的数据
            top_n: 返回前N名

        Returns:
            Dict: 排行榜结果
        """
        if tickers is None:
            tickers = list(ticker_to_company.keys())

        logger.info(f"🏆 开始生成股票热度排行榜 (分析 {len(tickers)} 只股票)")

        rankings = []

        with tqdm(tickers, desc="分析股票热度") as pbar:
            for ticker in pbar:
                pbar.set_description(f"分析 {ticker}")

                try:
                    analysis = self.analyze_stock_popularity(
                        ticker=ticker,
                        subreddits=subreddits,
                        min_relevance=min_relevance,
                        days_back=days_back,
                    )

                    # 只包含有提及的股票
                    if analysis["total_mentions"] > 0:
                        ranking_entry = {
                            "rank": 0,  # 稍后填入
                            "ticker": ticker,
                            "company_name": ticker_to_company.get(ticker, ticker),
                            "total_mentions": analysis["total_mentions"],
                            "total_popularity_score": analysis[
                                "total_popularity_score"
                            ],
                            "average_popularity_score": analysis[
                                "average_popularity_score"
                            ],
                            "top_subreddit": self._get_top_subreddit(
                                analysis["subreddit_breakdown"]
                            ),
                            "trend_description": self._generate_trend_description(
                                analysis
                            ),
                            "sample_posts": analysis["top_posts"][
                                :3
                            ],  # 只取前3个代表性帖子
                        }
                        rankings.append(ranking_entry)

                except Exception as e:
                    logger.error(f"❌ 分析 {ticker} 失败: {e}")
                    continue

                # 避免API限制
                time.sleep(0.1)

        # 按总热度分数排序
        rankings.sort(key=lambda x: x["total_popularity_score"], reverse=True)

        # 添加排名
        for i, entry in enumerate(rankings[:top_n]):
            entry["rank"] = i + 1

        # 生成排行榜结果
        result = {
            "generated_at": datetime.now().isoformat(),
            "analysis_period_days": days_back,
            "total_stocks_analyzed": len(tickers),
            "stocks_with_mentions": len(rankings),
            "top_stocks": rankings[:top_n],
            "summary_stats": self._generate_summary_stats(rankings[:top_n]),
        }

        logger.info(f"🎉 排行榜生成完成! 共发现 {len(rankings)} 只有讨论的股票")

        return result

    def _get_top_subreddit(self, subreddit_breakdown: Dict) -> str:
        """获取讨论最多的subreddit"""
        if not subreddit_breakdown:
            return ""

        top_subreddit = max(subreddit_breakdown.items(), key=lambda x: x[1]["mentions"])
        return top_subreddit[0]

    def _generate_trend_description(self, analysis: Dict) -> str:
        """生成趋势描述"""
        mentions = analysis["total_mentions"]

        if mentions == 0:
            return "无讨论"
        elif mentions < 5:
            return "轻度讨论"
        elif mentions < 20:
            return "中等讨论"
        elif mentions < 50:
            return "活跃讨论"
        else:
            return "热门讨论"

    def _generate_summary_stats(self, top_stocks: List[Dict]) -> Dict:
        """生成汇总统计信息"""
        if not top_stocks:
            return {}

        total_mentions = sum(stock["total_mentions"] for stock in top_stocks)
        total_score = sum(stock["total_popularity_score"] for stock in top_stocks)

        return {
            "total_mentions_all_stocks": total_mentions,
            "total_popularity_score_all_stocks": total_score,
            "average_mentions_per_stock": total_mentions / len(top_stocks),
            "most_discussed_stock": top_stocks[0]["ticker"] if top_stocks else "",
            "hottest_stock": max(
                top_stocks, key=lambda x: x["average_popularity_score"]
            )["ticker"]
            if top_stocks
            else "",
        }

    def print_popularity_ranking(
        self, ranking_result: Dict, show_details: bool = False
    ):
        """
        美观地打印股票热度排行榜

        Args:
            ranking_result: generate_stock_popularity_ranking的返回结果
            show_details: 是否显示详细信息
        """
        output = self.format_popularity_ranking(ranking_result, show_details)
        print(output)

    def format_popularity_ranking(
        self,
        ranking_result: Dict,
        show_details: bool = False,
        include_full_posts: bool = False,
    ) -> str:
        """
        格式化股票热度排行榜为字符串

        Args:
            ranking_result: generate_stock_popularity_ranking的返回结果
            show_details: 是否显示详细信息
            include_full_posts: 是否包含完整的帖子内容

        Returns:
            str: 格式化后的排行榜字符串
        """
        lines = []

        # 标题和基本信息
        lines.append("🏆 Reddit股票热度排行榜")
        lines.append("=" * 60)
        lines.append(f"📅 分析时间段: 最近 {ranking_result['analysis_period_days']} 天")
        lines.append(f"📊 分析股票总数: {ranking_result['total_stocks_analyzed']}")
        lines.append(f"💬 有讨论的股票: {ranking_result['stocks_with_mentions']}")
        lines.append(f"⏰ 生成时间: {ranking_result['generated_at']}")
        lines.append("")

        top_stocks = ranking_result["top_stocks"]

        # 排行榜
        lines.append("📈 热度排行榜:")
        lines.append("-" * 60)
        lines.append(
            f"{'排名':<4} {'股票':<6} {'公司名':<20} {'提及':<6} {'热度':<8} {'趋势':<8}"
        )
        lines.append("-" * 60)

        for stock in top_stocks:
            lines.append(
                f"{stock['rank']:<4} {stock['ticker']:<6} {stock['company_name'][:18]:<20} "
                f"{stock['total_mentions']:<6} {stock['total_popularity_score']:<8.1f} {stock['trend_description']:<8}"
            )

        # 详细信息
        if show_details and top_stocks:
            lines.append("\n🔥 热门股票详情:")
            lines.append("-" * 60)

            for i, stock in enumerate(top_stocks[:5]):  # 只显示前5名详情
                lines.append(
                    f"\n{stock['rank']}. {stock['ticker']} - {stock['company_name']}"
                )
                lines.append(f"   📊 提及次数: {stock['total_mentions']}")
                lines.append(f"   🔥 总热度: {stock['total_popularity_score']:.1f}")
                lines.append(f"   📍 主要讨论区: r/{stock['top_subreddit']}")

                # 如果需要包含完整帖子内容，则添加subreddit分布详情
                if include_full_posts and i == 0:  # 只为第一名显示详细分布
                    # 计算subreddit分布
                    subreddit_dist = {}
                    for post in stock["sample_posts"]:
                        subreddit = post.get("subreddit", "unknown")
                        if subreddit not in subreddit_dist:
                            subreddit_dist[subreddit] = {"count": 0, "total_score": 0}
                        subreddit_dist[subreddit]["count"] += 1
                        subreddit_dist[subreddit]["total_score"] += post.get(
                            "popularity_score", 0
                        )

                    if subreddit_dist:
                        lines.append("   📋 各讨论区分布:")
                        sorted_subreddits = sorted(
                            subreddit_dist.items(),
                            key=lambda x: x[1]["count"],
                            reverse=True,
                        )
                        for subreddit, data in sorted_subreddits:
                            lines.append(
                                f"      r/{subreddit}: {data['count']}次提及, 总热度{data['total_score']:.1f}"
                            )
                        lines.append("")

                if stock["sample_posts"]:
                    lines.append("   📝 热门帖子:")
                    post_limit = (
                        len(stock["sample_posts"])
                        if include_full_posts
                        else min(3, len(stock["sample_posts"]))
                    )

                    for j, post in enumerate(stock["sample_posts"][:post_limit]):
                        if include_full_posts:
                            # 完整帖子信息
                            lines.append(f"      {j + 1}. 标题: {post['title']}")
                            lines.append(f"         来源: r/{post['subreddit']}")
                            lines.append(
                                f"         互动: 👍{post['upvotes']} 💬{post['comments']} 分数:{post['score']}"
                            )
                            lines.append(f"         相关度: {post['relevance']:.2f}")
                            lines.append(
                                f"         热度分数: {post['popularity_score']:.1f}"
                            )
                            if post.get("url"):
                                lines.append(f"         链接: {post['url']}")
                                # pass
                            lines.append("")
                        else:
                            # 简化信息
                            lines.append(f"      {j + 1}. {post['title'][:80]}...")
                            lines.append(
                                f"         (👍{post['upvotes']} 💬{post['comments']} "
                                f"相关度:{post['relevance']:.2f} 热度:{post['popularity_score']:.1f})"
                            )

        # 汇总统计
        if "summary_stats" in ranking_result:
            stats = ranking_result["summary_stats"]
            lines.append("\n📈 汇总统计:")
            lines.append(f"   🎯 最受讨论: {stats.get('most_discussed_stock', 'N/A')}")
            lines.append(f"   🔥 最热门: {stats.get('hottest_stock', 'N/A')}")
            lines.append(
                f"   💬 平均提及: {stats.get('average_mentions_per_stock', 0):.1f} 次/股票"
            )

        return "\n".join(lines)


# 便捷API函数
def analyze_stock_popularity(
    ticker: str,
    days_back: int = 7,
    min_relevance: float = 0.1,
    data_dir: Optional[str] = None,
) -> Dict:
    """
    便捷函数：分析单只股票的Reddit热度

    Args:
        ticker: 股票代码 (如 "AAPL")
        days_back: 分析过去几天的数据
        min_relevance: 最小相关度阈值
        data_dir: 数据目录

    Returns:
        Dict: 分析结果
    """
    analyzer = StockPopularityAnalyzer(data_dir=data_dir)
    return analyzer.analyze_stock_popularity(
        ticker=ticker, min_relevance=min_relevance, days_back=days_back
    )


def generate_reddit_stock_ranking(
    top_n: int = 20,
    days_back: int = 7,
    tickers: Optional[List[str]] = None,
    data_dir: Optional[str] = None,
    print_results: bool = True,
    show_details: bool = False,
) -> Dict:
    """
    便捷函数：生成Reddit股票热度排行榜

    Args:
        top_n: 返回前N名
        days_back: 分析过去几天的数据
        tickers: 要分析的股票列表，默认分析所有已配置的股票
        data_dir: 数据目录
        print_results: 是否打印结果
        show_details: 是否显示详细信息

    Returns:
        Dict: 排行榜结果
    """
    analyzer = StockPopularityAnalyzer(data_dir=data_dir)

    ranking_result = analyzer.generate_stock_popularity_ranking(
        tickers=tickers, days_back=days_back, top_n=top_n
    )

    # if print_results:
    #     analyzer.print_popularity_ranking(ranking_result, show_details=show_details)

    formatted_text = analyzer.format_popularity_ranking(
        ranking_result, show_details=True, include_full_posts=True
    )

    return formatted_text


def format_reddit_stock_ranking(
    top_n: int = 20,
    days_back: int = 7,
    tickers: Optional[List[str]] = None,
    data_dir: Optional[str] = None,
    show_details: bool = True,
    include_full_posts: bool = True,
) -> str:
    """
    便捷函数：生成Reddit股票热度排行榜并返回格式化字符串

    Args:
        top_n: 返回前N名
        days_back: 分析过去几天的数据
        tickers: 要分析的股票列表，默认分析所有已配置的股票
        data_dir: 数据目录
        show_details: 是否显示详细信息
        include_full_posts: 是否包含完整的帖子内容

    Returns:
        str: 格式化的排行榜字符串
    """
    analyzer = StockPopularityAnalyzer(data_dir=data_dir)

    ranking_result = analyzer.generate_stock_popularity_ranking(
        tickers=tickers, days_back=days_back, top_n=top_n
    )

    return analyzer.format_popularity_ranking(
        ranking_result, show_details=show_details, include_full_posts=include_full_posts
    )


def get_trending_stocks(
    days_back: int = 1, min_mentions: int = 5, data_dir: Optional[str] = None
) -> List[Dict]:
    """
    便捷函数：获取近期热门股票

    Args:
        days_back: 分析过去几天的数据
        min_mentions: 最少提及次数阈值
        data_dir: 数据目录

    Returns:
        List[Dict]: 热门股票列表
    """
    analyzer = StockPopularityAnalyzer(data_dir=data_dir)

    ranking_result = analyzer.generate_stock_popularity_ranking(
        days_back=days_back,
        top_n=50,  # 获取更多候选
    )

    # 筛选符合条件的热门股票
    trending_stocks = [
        stock
        for stock in ranking_result["top_stocks"]
        if stock["total_mentions"] >= min_mentions
    ]

    return trending_stocks


def compare_stock_popularity(
    tickers: List[str], days_back: int = 7, data_dir: Optional[str] = None
) -> Dict:
    """
    便捷函数：比较多只股票的热度

    Args:
        tickers: 股票代码列表
        days_back: 分析过去几天的数据
        data_dir: 数据目录

    Returns:
        Dict: 比较结果
    """
    analyzer = StockPopularityAnalyzer(data_dir=data_dir)

    comparisons = {}

    for ticker in tickers:
        try:
            analysis = analyzer.analyze_stock_popularity(
                ticker=ticker, days_back=days_back
            )
            comparisons[ticker] = {
                "mentions": analysis["total_mentions"],
                "popularity_score": analysis["total_popularity_score"],
                "average_score": analysis["average_popularity_score"],
                "company_name": ticker_to_company.get(ticker, ticker),
            }
        except Exception as e:
            logger.warning(f"⚠️ 分析 {ticker} 失败: {e}")
            comparisons[ticker] = None

    # 按热度排序
    valid_comparisons = {k: v for k, v in comparisons.items() if v is not None}
    sorted_tickers = sorted(
        valid_comparisons.items(), key=lambda x: x[1]["popularity_score"], reverse=True
    )

    result = {
        "comparison_date": datetime.now().isoformat(),
        "analysis_period_days": days_back,
        "tickers_analyzed": tickers,
        "successful_analyses": len(valid_comparisons),
        "rankings": sorted_tickers,
        "winner": sorted_tickers[0][0] if sorted_tickers else None,
    }

    return result


def download_and_analyze_stocks(
    tickers: List[str],
    subreddit_category: str = "company_news",
    limit_per_subreddit: int = 100,
    analysis_days: int = 7,
    data_dir: Optional[str] = None,
    need_download: bool = False,
) -> Dict:
    """
    便捷函数：一键下载数据并分析股票热度

    Args:
        tickers: 要分析的股票代码列表
        subreddit_category: subreddit分类
        limit_per_subreddit: 每个subreddit的下载限制
        analysis_days: 分析天数
        data_dir: 数据目录

    Returns:
        Dict: 分析结果
    """
    logger.info("🚀 开始一键下载并分析股票热度")

    # 步骤1: 下载最新数据
    logger.info("📥 步骤1: 下载Reddit数据...")
    if need_download:
        download_reddit_data(
            category=subreddit_category,
            limit_per_subreddit=limit_per_subreddit,
            data_dir=data_dir,
            force_refresh=True,
        )

    # 步骤2: 分析股票热度
    logger.info("📊 步骤2: 分析股票热度...")
    analysis_result = generate_reddit_stock_ranking(
        top_n=len(tickers),
        days_back=analysis_days,
        tickers=tickers,
        data_dir=data_dir,
        print_results=True,
        show_details=True,
    )

    return {
        "analysis_result": analysis_result,
        "summary": f"成功分析 {len(tickers)} 只股票的Reddit热度",
    }
