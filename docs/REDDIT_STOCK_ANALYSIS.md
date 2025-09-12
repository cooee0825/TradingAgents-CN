# Reddit 股票热度分析功能

## 概述

这个功能允许你分析股票在 Reddit 上的讨论热度，生成热度排行榜，并跟踪趋势变化。该功能基于 6 个主要的股票讨论 subreddit：

- `r/wallstreetbets` - 最活跃的股票讨论社区
- `r/stocks` - 传统股票讨论
- `r/investing` - 投资策略讨论
- `r/StockMarket` - 股市综合讨论
- `r/SecurityAnalysis` - 证券分析
- `r/ValueInvesting` - 价值投资

## 功能特性

### 🎯 单股分析

- 分析特定股票的 Reddit 讨论热度
- 智能关键词匹配（股票代码+公司名）
- 相关度评分和热度计算
- 时间趋势分析

### 🏆 热度排行榜

- 生成 Reddit 股票讨论热度排行榜
- 支持自定义时间范围和分析参数
- 美观的结果展示

### 🔥 趋势追踪

- 识别近期热门股票
- 异常热度检测
- 多股票对比分析

### 📊 高级分析

- subreddit 分布分析
- 帖子质量评分
- 时间衰减因子
- 综合热度算法

## 快速开始

### 1. 环境准备

```bash
# 安装依赖
pip install praw

# 设置Reddit API凭证（可选，仅下载功能需要）
export REDDIT_CLIENT_ID="your_client_id"
export REDDIT_CLIENT_SECRET="your_client_secret"
```

### 2. 下载数据

```bash
# 下载股票相关subreddit数据
python -m tradingagents.dataflows.reddit_utils --category company_news --limit 100
```

### 3. 基础使用

```python
from tradingagents.dataflows.reddit_utils import (
    analyze_stock_popularity,
    generate_reddit_stock_ranking
)

# 分析单只股票
result = analyze_stock_popularity("AAPL", days_back=7)
print(f"AAPL热度: {result['total_popularity_score']}")

# 生成排行榜
ranking = generate_reddit_stock_ranking(top_n=10, days_back=7)
```

## API 参考

### 便捷函数

#### `analyze_stock_popularity(ticker, days_back=7, min_relevance=0.1, data_dir=None)`

分析单只股票的 Reddit 热度。

**参数:**

- `ticker`: 股票代码（如 "AAPL"）
- `days_back`: 分析过去几天的数据
- `min_relevance`: 最小相关度阈值（0-1）
- `data_dir`: 数据目录路径

**返回:** 包含分析结果的字典

**示例:**

```python
result = analyze_stock_popularity("TSLA", days_back=14)
print(f"提及次数: {result['total_mentions']}")
print(f"热度分数: {result['total_popularity_score']}")
```

#### `generate_reddit_stock_ranking(top_n=20, days_back=7, tickers=None, data_dir=None, print_results=True, show_details=False)`

生成 Reddit 股票热度排行榜。

**参数:**

- `top_n`: 返回前 N 名
- `days_back`: 分析天数
- `tickers`: 指定股票列表（默认分析所有）
- `data_dir`: 数据目录
- `print_results`: 是否打印结果
- `show_details`: 是否显示详细信息

**示例:**

```python
# 生成前15名排行榜，显示详细信息
ranking = generate_reddit_stock_ranking(
    top_n=15,
    days_back=7,
    show_details=True
)
```

#### `get_trending_stocks(days_back=1, min_mentions=5, data_dir=None)`

获取近期热门股票。

**参数:**

- `days_back`: 分析天数
- `min_mentions`: 最少提及次数
- `data_dir`: 数据目录

**示例:**

```python
# 获取昨天讨论超过10次的热门股票
trending = get_trending_stocks(days_back=1, min_mentions=10)
for stock in trending:
    print(f"{stock['ticker']}: {stock['total_mentions']}次提及")
```

#### `compare_stock_popularity(tickers, days_back=7, data_dir=None)`

比较多只股票的热度。

**示例:**

```python
# 比较科技股热度
tech_stocks = ["AAPL", "GOOGL", "MSFT", "TSLA"]
comparison = compare_stock_popularity(tech_stocks)
print(f"获胜者: {comparison['winner']}")
```

#### `download_and_analyze_stocks(tickers, subreddit_category="company_news", limit_per_subreddit=100, analysis_days=7, data_dir=None)`

一键下载数据并分析股票热度。

**示例:**

```python
# 下载最新数据并分析指定股票
result = download_and_analyze_stocks(
    tickers=["AAPL", "TSLA", "NVDA"],
    limit_per_subreddit=50
)
```

### 高级用法：StockPopularityAnalyzer 类

对于更复杂的分析需求，可以直接使用`StockPopularityAnalyzer`类：

```python
from tradingagents.dataflows.reddit_utils import StockPopularityAnalyzer

# 创建分析器
analyzer = StockPopularityAnalyzer(data_dir="custom/path")

# 生成关键词
keywords = analyzer.generate_stock_keywords("AAPL")

# 详细分析
analysis = analyzer.analyze_stock_popularity("AAPL", days_back=30)

# 查看subreddit分布
for subreddit, data in analysis['subreddit_breakdown'].items():
    if data['mentions'] > 0:
        print(f"r/{subreddit}: {data['mentions']}次提及")

# 生成排行榜
ranking = analyzer.generate_stock_popularity_ranking(top_n=25)
analyzer.print_popularity_ranking(ranking, show_details=True)
```

## 热度计算算法

热度分数基于以下因素计算：

```
热度分数 = (基础互动分数 + 质量分数) × subreddit权重 × 时间衰减

其中：
- 基础互动分数 = (点赞数 × 1.0) + (评论数 × 0.8) + (分数 × 0.6)
- 质量分数 = upvote_ratio × 0.5
- 时间衰减 = max(0.1, 1.0 / (1 + 时间差小时数/24))
```

### subreddit 权重配置

```python
SUBREDDIT_WEIGHTS = {
    "wallstreetbets": 1.0,    # 影响力最大
    "stocks": 0.8,
    "investing": 0.7,
    "StockMarket": 0.6,
    "SecurityAnalysis": 0.5,
    "ValueInvesting": 0.4
}
```

## 示例输出

### 排行榜示例

```
🏆 Reddit股票热度排行榜
============================================================
📅 分析时间段: 最近 7 天
📊 分析股票总数: 59
💬 有讨论的股票: 15
⏰ 生成时间: 2024-01-15T10:30:00

📈 热度排行榜:
------------------------------------------------------------
排名   股票   公司名                 提及   热度     趋势
------------------------------------------------------------
1    TSLA   Tesla                18     245.3   活跃讨论
2    AAPL   Apple                15     198.7   活跃讨论
3    NVDA   Nvidia               12     156.2   中等讨论
4    AMD    AMD                  8      89.4    轻度讨论
5    MSFT   Microsoft            6      67.8    轻度讨论
```

### 单股分析示例

```python
result = analyze_stock_popularity("AAPL")

# 输出示例:
{
    "ticker": "AAPL",
    "keywords": ["AAPL", "$AAPL", "Apple", "apple"],
    "total_mentions": 15,
    "total_popularity_score": 198.7,
    "average_popularity_score": 13.2,
    "subreddit_breakdown": {
        "wallstreetbets": {"mentions": 8, "popularity_score": 120.5},
        "stocks": {"mentions": 4, "popularity_score": 45.2},
        "investing": {"mentions": 3, "popularity_score": 33.0}
    },
    "top_posts": [
        {
            "title": "AAPL earnings beat expectations",
            "subreddit": "wallstreetbets",
            "upvotes": 450,
            "comments": 89,
            "relevance": 0.95,
            "popularity_score": 67.8
        }
    ]
}
```

## 故障排除

### 常见问题

1. **"数据文件不存在"错误**

   ```bash
   # 下载数据
   python -m tradingagents.dataflows.reddit_utils --category company_news
   ```

2. **"未找到相关讨论"**

   - 增加`days_back`参数
   - 降低`min_relevance`阈值
   - 检查股票代码是否正确

3. **Reddit API 连接失败**

   ```bash
   # 检查环境变量
   echo $REDDIT_CLIENT_ID
   echo $REDDIT_CLIENT_SECRET
   ```

4. **性能优化**
   - 使用较小的`days_back`值
   - 限制`tickers`列表大小
   - 增加`min_relevance`阈值

### 测试功能

运行测试脚本检查功能是否正常：

```bash
# 快速测试
python test_reddit_stock_analysis.py

# 完整演示
python examples/reddit_stock_analysis_demo.py
```

## 扩展和自定义

### 添加新股票

编辑`ticker_to_company`字典：

```python
ticker_to_company.update({
    "NEW": "New Company Name",
    "EXAMPLE": "Example Corp OR Example Company"
})
```

### 自定义 subreddit

```python
# 使用自定义subreddit列表
custom_subreddits = ["investing", "SecurityAnalysis"]
analyzer = StockPopularityAnalyzer()
result = analyzer.analyze_stock_popularity(
    "AAPL",
    subreddits=custom_subreddits
)
```

### 调整权重

修改`SUBREDDIT_WEIGHTS`配置：

```python
SUBREDDIT_WEIGHTS["wallstreetbets"] = 1.5  # 增加权重
```

## 最佳实践

1. **定期更新数据**: 建议每天更新 Reddit 数据以获取最新趋势
2. **合理设置参数**: 根据分析需求调整时间范围和相关度阈值
3. **结合其他指标**: 将 Reddit 热度与股价、成交量等指标结合分析
4. **关注异常值**: 注意突然爆红的股票，可能有重要消息
5. **长期趋势**: 观察股票讨论热度的长期变化趋势

## 许可证

此功能是 TradingAgents 项目的一部分，遵循项目的开源许可证。

---

**需要帮助?** 请查看项目文档或创建 issue。
