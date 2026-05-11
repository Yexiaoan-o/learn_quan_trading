## 1.1 什么是股票？

股票（Stock/Share）是股份公司发行的所有权凭证，代表持有者对公司资产和利润的一份所有权。从量化交易的角度来看，股票是交易所上可交易的标准化金融资产，具有以下几个关键属性：

| 属性 | 说明 | 量化交易中的意义 |
|------|------|-----------------|
| 可交易性 | 在交易所公开挂牌，流动性好 | 可以快速建仓和平仓 |
| 标准化 | 每手数量固定（A股100股/手） | 便于批量处理 |
| 价格连续 | 交易时段价格持续更新 | 支持各种频率的策略 |
| 信息透明 | 定期披露财报，价格公开 | 数据驱动的分析成为可能 |

### 股票类型的区分

```python
# A股市场股票代码规则
"""
上海证券交易所 (SSE)
  600xxx - 主板（A股）
  601xxx - 主板（A股）
  688xxx - 科创板

深圳证券交易所 (SZSE)  
  000xxx - 主板（A股）
  002xxx - 中小板
  300xxx - 创业板
"""
```

> **股票的本质**：从量化视角看，股票就是一组多维时间序列数据——价格、成交量、估值指标、财务数据……量化交易并不需要"相信"某家公司，而是通过数学和统计方法寻找这些时间序列中的可盈利模式。

## 1.2 交易所与市场机制

### 全球主要交易所

| 交易所 | 代码简称 | 所在地 | 主要指数 | 交易时间（本地） |
|--------|---------|--------|----------|-----------------|
| 上海证券交易所 | SSE | 中国上海 | 上证综指 | 9:30-15:00 |
| 深圳证券交易所 | SZSE | 中国深圳 | 深证成指 | 9:30-15:00 |
| 纽约证券交易所 | NYSE | 美国纽约 | 道琼斯 | 9:30-16:00 |
| 纳斯达克 | NASDAQ | 美国 | 纳斯达克100 | 9:30-16:00 |
| 香港交易所 | HKEX | 中国香港 | 恒生指数 | 9:30-16:00 |

### A 股交易机制关键规则

```
┌────────────────────────────────────────────┐
│             A股交易机制要点                    │
├──────────────┬─────────────────────────────┤
│ 交易时间       │ 9:15-9:25 集合竞价            │
│              │ 9:30-11:30 连续竞价            │
│              │ 13:00-15:00 连续竞价           │
├──────────────┼─────────────────────────────┤
│ 涨跌停限制     │ 主板 ±10%（ST股±5%）           │
│              │ 科创/创业板 ±20%               │
│              │ 新股上市首日特殊规定              │
├──────────────┼─────────────────────────────┤
│ T+1交易      │ 当日买入，次日才能卖出            │
│ T+0回转      │ 当日卖出后可用资金当日可买          │
├──────────────┼─────────────────────────────┤
│ 最小变动单位   │ 0.01元（A股）                 │
│ 交易单位      │ 100股/手                      │
└──────────────┴─────────────────────────────┘
```

### 涨跌停制度对量化策略的影响

涨跌停制度是 A 股区别于美股的重要特征，对量化策略有深远影响：

1. **流动性陷阱**：涨停板买入、跌停板卖出无法成交，导致策略信号失效
2. **动量效应增强**：涨停板次日往往继续高开（涨停板溢出效应）
3. **止损困难**：跌停板无法卖出，实际亏损可能远超模型预期

```python
import pandas as pd
import numpy as np

def filter_limit_stocks(df, upper_limit=0.098, lower_limit=-0.098):
    """
    过滤掉涨跌停的股票（无法交易）
    
    参数:
    df: DataFrame，包含 'close' 和 'pre_close' 列
    upper_limit: 涨停阈值（考虑四舍五入，略小于0.10）
    lower_limit: 跌停阈值
    """
    daily_return = df['close'] / df['pre_close'] - 1
    
    # 涨停和跌停的股票无法交易
    limit_up = daily_return > upper_limit
    limit_down = daily_return < lower_limit
    
    df['tradeable'] = ~(limit_up | limit_down)
    return df
```

## 1.3 订单类型

在量化交易中，正确地选择和使用订单类型至关重要。不同的订单类型直接影响成交价格和执行成功率。

| 订单类型 | 英文名 | 说明 | 量化中的用途 |
|----------|--------|------|-------------|
| 市价单 | Market Order | 以当前最优价格立即成交 | 需要快速建仓/平仓时使用 |
| 限价单 | Limit Order | 指定价格，只有达到或优于指定价才成交 | 精确控制成本，但可能无法成交 |
| 止损单 | Stop Order | 触发价格后转为市价单 | 风险控制、突破入场 |
| 止损限价单 | Stop-Limit | 触发后转为限价单 | 控制滑点的止损 |
| 冰山单 | Iceberg Order | 只显示订单总量的一部分 | 隐藏大订单，减少市场冲击 |

```python
# 订单类型的程序化表示
class Order:
    """模拟订单系统"""
    def __init__(self, symbol, order_type, side, quantity, price=None, stop_price=None):
        self.symbol = symbol
        self.order_type = order_type  # 'market', 'limit', 'stop', 'stop-limit'
        self.side = side              # 'buy' or 'sell'
        self.quantity = quantity
        self.price = price            # 限价
        self.stop_price = stop_price  # 止损价
        self.status = 'pending'
        
    def __repr__(self):
        return f"Order({self.symbol}, {self.side}, {self.quantity}股)"

# 示例：各类订单
market_buy = Order('000001.SZ', 'market', 'buy', 1000)
limit_sell = Order('000001.SZ', 'limit', 'sell', 500, price=10.50)
stop_loss = Order('000001.SZ', 'stop', 'sell', 500, stop_price=9.50)

print(market_buy)
print(limit_sell)
```

### 订单簿与市场深度

```
订单簿（Order Book）示例：

卖5 ┃ 10.08  5000股  ┃  卖盘（Ask Side）
卖4 ┃ 10.07  3000股  ┃
卖3 ┃ 10.06  8000股  ┃ ← 卖一价（Best Ask）= 10.05
卖2 ┃ 10.06  4000股  ┃
卖1 ┃ 10.05  10000股 ┃
━━━━━╋━━━━━━━━━━━━━━━╋━━━━
买1 ┃ 10.04  8000股  ┃ ← 买一价（Best Bid）= 10.04
买2 ┃ 10.03  12000股 ┃  买盘（Bid Side）
买3 ┃ 10.02  6000股  ┃
买4 ┃ 10.01  15000股 ┃
买5 ┃ 10.00  20000股 ┃

买一卖一价差（Bid-Ask Spread）= 10.05 - 10.04 = 0.01
```

> **关键概念**：限价单加入订单簿等待成交（提供流动性），市价单立即成交但消耗订单簿（消耗流动性）。做市商策略的本质就是同时挂买卖限价单赚取价差。

## 1.4 除权除息处理

股票分红、送股、配股等事件会导致股价出现非交易性跳空，必须进行复权处理。

### 复权类型

| 复权方式 | 说明 | 适用场景 |
|----------|------|----------|
| 不复权 | 使用实际交易价格 | 检查真实历史价格 |
| 前复权 | 历史价格按比例调整，使最新价格不变 | 策略回测（最常用） |
| 后复权 | 最新价格按比例调整，使历史价格不变 | 分析长期涨幅 |

```python
def adjust_price(df, factor_col='adj_factor'):
    """
    使用复权因子进行前复权
    
    前复权公式: adj_price = price * (factor / latest_factor)
    """
    latest_factor = df[factor_col].iloc[-1]
    df['adj_open'] = df['open'] * df[factor_col] / latest_factor
    df['adj_high'] = df['high'] * df[factor_col] / latest_factor
    df['adj_low'] = df['low'] * df[factor_col] / latest_factor
    df['adj_close'] = df['close'] * df[factor_col] / latest_factor
    return df
```

> **复权是回测的生命线**：使用未经复权处理的价格数据进行回测，相当于在策略收益中加入了实际上不存在的"分红魔法"。更严重的是，除权除息造成的价格跳空会被当成真实的涨跌信号，产生大量的虚假交易。

## 1.5 股票数据的 Python 实战

```python
import pandas as pd
import numpy as np
# pip install akshare
import akshare as ak

# === 获取A股列表 ===
stock_info = ak.stock_info_a_code_name()
print(f'A股总数: {len(stock_info)}')
print(stock_info.head(10))

# === 获取行业分类 ===
# 东方财富行业分类
industry_df = ak.stock_board_industry_name_em()
print(f'行业数量: {len(industry_df)}')
print(industry_df.head())

# === 获取单只股票的详细数据 ===
# 平安银行 (000001) 日K线，前复权
df = ak.stock_zh_a_hist(
    symbol="000001", 
    period="daily",
    start_date="20220101", 
    end_date="20231231", 
    adjust="qfq"
)

# 标准化列名
df.columns = ['date', 'open', 'close', 'high', 'low', 'volume', 
              'amount', 'amplitude', 'pct_chg', 'change', 'turnover']
df['date'] = pd.to_datetime(df['date'])
df.set_index('date', inplace=True)

print(df.head())
print(f'数据行数: {len(df)}')
```

> **基础信息的掌握程度决定策略的上限**：不了解 T+1 制度的量化交易者可能会设计出一套日内回转策略，在回测中表现完美，实盘中却因为制度限制完全无法执行。量化交易不只是数学和编程，对市场基础规则的深刻理解同样不可或缺。
