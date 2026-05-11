## 3.1 量化策略的分类框架

量化交易策略种类繁多，可以从多个维度进行分类。以下是主流的分类框架：

| 分类维度 | 策略类型 |
|----------|----------|
| 交易频率 | 高频交易、日内交易、日频交易、周频/低频交易 |
| 持仓周期 | T+0超短线、1-5天短线、数周中线、数月长线 |
| 收益来源 | 方向性交易、相对价值套利、事件驱动 |
| 策略逻辑 | 趋势跟踪、均值回归、统计套利、做市商 |
| 资产类别 | 股票、期货、期权、外汇、数字货币 |

本章将重点介绍几种最具代表性的量化策略类型。

## 3.2 趋势跟踪策略

趋势跟踪（Trend Following）是最古老、最经典的量化策略类型，其核心理念是"顺势而为"——不预测市场方向，而是跟随已经形成的趋势。

### 理论基础

趋势存在的经济学解释：
1. **信息渐进扩散**：新信息不会瞬间被所有市场参与者消化，导致价格逐步调整
2. **反馈循环（Feedback Loop）**：价格上涨→吸引更多买家→价格进一步上涨（正反馈）
3. **羊群效应**：投资者倾向于跟随大多数人的行为
4. **锚定效应**：投资者对新信息的反应不足（Underreaction），导致趋势延续

### 经典实现方法

```python
import pandas as pd
import numpy as np

def moving_average_crossover(close, short_window=20, long_window=60):
    """
    双均线交叉策略
    - 短期均线上穿长期均线：买入信号（金叉）
    - 短期均线下穿长期均线：卖出信号（死叉）
    """
    sma_short = close.rolling(window=short_window).mean()
    sma_long = close.rolling(window=long_window).mean()
    
    position = pd.Series(0, index=close.index)
    position[sma_short > sma_long] = 1    # 多头
    position[sma_short < sma_long] = -1   # 空头
    return position

def breakout_strategy(high, low, close, lookback=20):
    """
    突破策略（Donchian Channel）
    - 价格突破N日最高点：买入
    - 价格跌破N日最低点：卖出
    """
    highest = high.rolling(window=lookback).max()
    lowest = low.rolling(window=lookback).min()
    
    position = pd.Series(0, index=close.index)
    position[close > highest.shift(1)] = 1
    position[close < lowest.shift(1)] = -1
    return position

def macd_strategy(close, fast=12, slow=26, signal=9):
    """
    MACD策略
    MACD线 = 快均线 - 慢均线
    信号线 = MACD的指数均线
    金叉买入，死叉卖出
    """
    ema_fast = close.ewm(span=fast, adjust=False).mean()
    ema_slow = close.ewm(span=slow, adjust=False).mean()
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    
    position = pd.Series(0, index=close.index)
    position[macd_line > signal_line] = 1
    position[macd_line < signal_line] = -1
    return position
```

### 趋势跟踪的优缺点

| 优点 | 缺点 |
|------|------|
| 逻辑简单直观，容易理解和实现 | 震荡市中频繁假突破，产生亏损 |
| 在大趋势行情中表现优异 | 入场和出场滞后于价格拐点 |
| 适用于几乎所有流动性好的市场 | 回撤期可能非常长（数月甚至数年） |
| 自带风险管理（趋势反转即止损） | 参数选择对绩效影响较大 |

> **海龟交易法则**：最著名的趋势跟踪策略之一。Richard Dennis 在1980年代与朋友打赌，证明交易技巧可以传授。他招募了23个普通人（被称为"海龟"），用简单的趋势跟踪规则训练他们。这些海龟在4年内创造了超过1亿美元的利润。海龟法则的核心就是20日/55日突破系统加上严格的仓位管理和止损规则。

## 3.3 均值回归策略

均值回归（Mean Reversion）策略基于一个核心假设：资产价格在短期偏离其"公允价值"后，最终会回归到均值附近。

### 理论基础

均值回归的经济学解释：
- **套利力量**：当价格过度偏离合理区间时，套利者会进场将价格推回均衡水平
- **竞争性回归**：超额利润吸引竞争者，消除定价偏差
- **过度反应修正**：投资者对信息的过度反应会在后续被修正

### 常见实现方式

**1. 布林带策略**

```python
def bollinger_band_strategy(close, window=20, num_std=2):
    """
    布林带均值回归策略
    - 价格触及下轨：买入（认为被超卖）
    - 价格触及上轨：卖出（认为被超买）
    """
    sma = close.rolling(window=window).mean()
    std = close.rolling(window=window).std()
    
    upper_band = sma + num_std * std  # 上轨
    lower_band = sma - num_std * std  # 下轨
    
    position = pd.Series(0, index=close.index)
    position[close < lower_band] = 1   # 超卖，买入
    position[close > upper_band] = -1  # 超买，卖出
    
    return position
```

**2. 配对交易（Pairs Trading）**

配对交易是均值回归策略的经典应用。选择两只高度相关的股票（如工商银行和建设银行），当它们的价格比值偏离历史均值时，做多低估的、做空高估的，等待价差回归。

```python
def pairs_trading(stock_a, stock_b, lookback=60, entry_threshold=2.0):
    """
    配对交易策略
    基于两只股票价差的均值回归
    """
    spread = stock_a - stock_b
    spread_mean = spread.rolling(lookback).mean()
    spread_std = spread.rolling(lookback).std()
    
    z_score = (spread - spread_mean) / spread_std
    
    position = pd.Series(0, index=spread.index)
    position[z_score > entry_threshold] = -1   # A高估，做空A做多B
    position[z_score < -entry_threshold] = 1   # A低估，做多A做空B
    position[abs(z_score) < 0.5] = 0           # 价差回归，平仓
    
    return position
```

> **配对交易的风险**：价差回归并非必然发生。当两只股票的基本面发生了结构性变化（如其中一家公司出现了重大经营问题），价差可能永久性扩大而不再回归。这就是所谓的"协整关系破裂"。

## 3.4 统计套利策略

统计套利（Statistical Arbitrage，简称 Stat Arb）是量化交易中最核心的策略类型。它利用统计方法发现资产之间的价格关系错配，构建市场中性的投资组合。

### 核心特征

- **市场中性**：多空仓位基本对冲，不受大盘涨跌影响
- **大量交易**：通常同时持有数百到数千个仓位
- **概率优势**：依靠大量交易中统计意义上的微小优势获利
- **高频换手**：持仓周期短，通常日内到数日

### 股票统计套利流程

```
1. 股票池构建
   ↓ 流动性筛选、行业分类
2. 因子模型建立
   ↓ 多因子风险模型分解收益
3. 残差收益计算
   ↓ 剥离市场/行业/风格因子后的"纯alpha"
4. 信号生成
   ↓ 残差的均值回归或动量信号
5. 组合优化
   ↓ 风险约束下的最优权重
6. 执行交易
```

### 多因子模型示例

```python
import numpy as np
from sklearn.linear_model import LinearRegression

def calculate_residual_returns(stock_returns, factor_returns):
    """
    通过多因子回归提取残差收益
    残差 = 实际收益 - 因子解释的收益
    """
    model = LinearRegression()
    model.fit(factor_returns, stock_returns)
    predicted = model.predict(factor_returns)
    residuals = stock_returns - predicted
    return residuals  # 这部分就是无法被因子解释的"alpha"
```

### 统计套利的挑战
- 因子模型的准确性和时效性
- 交易成本会迅速侵蚀微薄的套利利润
- 信号的衰减速度快，需要持续更新模型
- 市场中性在某些极端行情下可能失效

## 3.5 做市商策略

做市商（Market Making）策略通过在买卖双方同时报价，赚取买卖价差（Bid-Ask Spread）获利。

### 做市商的盈利模式

```
卖价 (Ask): 10.02 ← 做市商的卖出报价
买价 (Bid): 10.00 ← 做市商的买入报价
价差 (Spread): 0.02 ← 做市商的利润空间
```

做市商的核心挑战是**库存风险管理**。当大量买单涌入，做市商积累了大量空头仓位时，需要调整报价来管理库存风险。

### 策略对比总结

| 策略类型 | 核心逻辑 | 收益来源 | 适合市场 | 风险特征 |
|----------|----------|----------|----------|----------|
| 趋势跟踪 | 顺势而为 | 价格趋势的延续 | 趋势明显的市场 | 震荡市中回撤大 |
| 均值回归 | 物极必反 | 价格偏离的修正 | 区间震荡市场 | 趋势市中可能巨亏 |
| 统计套利 | 概率套利 | 大量交易的微小优势 | 流动性好的市场 | 模型风险、黑天鹅 |
| 做市商 | 双向报价 | 买卖价差 | 高流动性资产 | 库存风险 |

> **关键洞察**：不同的策略类型在不同的市场环境下表现各异。优秀的量化交易者通常不会押注于单一策略类型，而是构建多策略组合，在不同的市场环境下各取所长。这种多策略分散化的思想，正是 Bridgewater 的"全天候"（All Weather）理念在量化领域的体现。
