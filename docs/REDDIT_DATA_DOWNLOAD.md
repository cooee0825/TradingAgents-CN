# Reddit 数据下载指南

本文档介绍如何使用 Reddit 数据下载功能获取社交媒体数据。

## 🔧 环境配置

### 1. 安装依赖

```bash
pip install praw tqdm
```

### 2. 获取 Reddit API 凭证

1. 访问 [Reddit App Preferences](https://www.reddit.com/prefs/apps)
2. 点击 "Create App" 或 "Create Another App"
3. 填写以下信息：
   - **name**: 您的应用名称 (如: TradingAgents)
   - **App type**: 选择 "script"
   - **description**: 应用描述 (可选)
   - **about url**: 留空
   - **redirect uri**: http://localhost:8080 (必填，但不会使用)
4. 创建后记录以下信息：
   - **Client ID**: 应用名称下方的字符串
   - **Client Secret**: "secret" 后面的字符串

### 3. 配置环境变量

创建或编辑 `.env` 文件，添加以下内容：

```bash
# Reddit API配置
REDDIT_CLIENT_ID=your_client_id_here
REDDIT_CLIENT_SECRET=your_client_secret_here
REDDIT_USER_AGENT=TradingAgents/1.0
```

或在系统中设置环境变量：

```bash
export REDDIT_CLIENT_ID="your_client_id_here"
export REDDIT_CLIENT_SECRET="your_client_secret_here"
export REDDIT_USER_AGENT="TradingAgents/1.0"
```

## 📥 使用方法

### 方法 1: 使用专用下载脚本

```bash
# 检查环境配置
python scripts/download_reddit_data.py --check

# 查看使用示例
python scripts/download_reddit_data.py --demo

# 下载公司新闻数据
python scripts/download_reddit_data.py --category company_news --limit 100

# 下载所有分类数据
python scripts/download_reddit_data.py --category all --limit 50

# 下载最热门的帖子
python scripts/download_reddit_data.py --category global_news --type top --time-filter week

# 下载自定义subreddit
python scripts/download_reddit_data.py --custom-subreddits wallstreetbets investing --limit 200

# 强制刷新已存在的数据
python scripts/download_reddit_data.py --category company_news --force-refresh
```

### 方法 2: 在代码中使用

```python
from tradingagents.dataflows.reddit_utils import (
    download_reddit_data,
    download_custom_subreddits,
    RedditDataDownloader
)

# 下载所有预配置分类
results = download_reddit_data(
    category="all",
    limit_per_subreddit=100,
    category_type="hot"
)

# 下载特定分类
results = download_reddit_data(
    category="company_news",
    limit_per_subreddit=200,
    category_type="top",
    time_filter="week"
)

# 下载自定义subreddit
success = download_custom_subreddits(
    subreddits=["wallstreetbets", "investing", "stocks"],
    category_name="trading_focus",
    limit_per_subreddit=150
)

# 使用高级API
downloader = RedditDataDownloader(data_dir="custom/data/path")
posts = downloader.download_subreddit_data("wallstreetbets", limit=500)
```

## 📂 数据结构

### 目录结构

```
data/reddit_data/
├── global_news/
│   ├── worldnews.jsonl
│   ├── news.jsonl
│   ├── business.jsonl
│   └── ...
├── company_news/
│   ├── stocks.jsonl
│   ├── investing.jsonl
│   ├── wallstreetbets.jsonl
│   └── ...
└── crypto_news/
    ├── CryptoCurrency.jsonl
    ├── Bitcoin.jsonl
    └── ...
```

### JSONL 文件格式

每行包含一个 JSON 对象，表示一个 Reddit 帖子：

```json
{
  "id": "post_id",
  "title": "帖子标题",
  "selftext": "帖子内容",
  "url": "链接地址",
  "ups": 点赞数,
  "score": 总分数,
  "upvote_ratio": 点赞率,
  "num_comments": 评论数,
  "created_utc": 创建时间戳,
  "author": "作者名",
  "subreddit": "所属subreddit",
  "permalink": "永久链接",
  "is_self": 是否为文本帖,
  "domain": "域名",
  "stickied": 是否置顶,
  "over_18": 是否成人内容,
  "spoiler": 是否剧透,
  "locked": 是否锁定
}
```

## ⚙️ 配置选项

### 预配置的 Subreddit 分类

- **global_news**: 全球新闻

  - worldnews, news, business, economy, finance, markets, investing

- **company_news**: 公司新闻

  - stocks, investing, SecurityAnalysis, ValueInvesting, StockMarket, wallstreetbets, financialindependence

- **crypto_news**: 加密货币新闻
  - CryptoCurrency, Bitcoin, ethereum, CryptoMarkets, altcoin

### 帖子分类

- **hot**: 热门帖子 (默认)
- **new**: 最新帖子
- **top**: 最高分帖子
- **rising**: 上升帖子

### 时间筛选 (仅对 top 有效)

- **all**: 所有时间
- **day**: 24 小时内
- **week**: 一周内 (默认)
- **month**: 一个月内
- **year**: 一年内

## 🚨 注意事项

### API 限制

- Reddit API 有速率限制，建议：
  - 每个请求间隔至少 0.1 秒
  - 每个 subreddit 间隔至少 1 秒
  - 避免在短时间内大量请求

### 数据使用建议

- 首次下载建议限制每个 subreddit 为 50-100 个帖子
- 定期刷新数据以获取最新内容
- 注意存储空间，大量数据可能占用较多磁盘空间

### 错误处理

- 如果某个 subreddit 访问失败，程序会继续处理其他 subreddit
- 检查日志了解详细错误信息
- 确保网络连接稳定

## 🔧 故障排除

### 常见问题

1. **ImportError: No module named 'praw'**

   ```bash
   pip install praw
   ```

2. **Reddit API 连接失败**

   - 检查 CLIENT_ID 和 CLIENT_SECRET 是否正确
   - 确认网络可以访问 Reddit
   - 检查 USER_AGENT 格式

3. **权限被拒绝**

   - 确认 Reddit 应用类型为"script"
   - 检查 API 凭证是否有效

4. **下载速度慢**
   - 减少 limit_per_subreddit 参数
   - 检查网络连接
   - Reddit API 本身有速率限制

### 日志调试

启用详细日志：

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### 测试连接

```bash
python scripts/download_reddit_data.py --check
```

## 📊 性能优化

### 建议设置

- **小规模测试**: limit=10-50
- **日常使用**: limit=100-200
- **大规模采集**: limit=500+ (注意 API 限制)

### 并发控制

当前实现使用串行处理以避免 API 限制。如需并发，请：

1. 实现请求队列
2. 添加速率限制器
3. 处理 API 错误重试

## 📈 与 TradingAgents 集成

下载的数据会自动与现有的数据处理流程集成：

```python
from tradingagents.dataflows.interface import get_reddit_company_news

# 使用下载的数据
news = get_reddit_company_news(
    ticker="AAPL",
    start_date="2024-01-01",
    look_back_days=7,
    max_limit_per_day=50
)
```

数据下载完成后，现有的`fetch_top_from_category`函数会自动读取 JSONL 文件并提供给分析系统使用。
