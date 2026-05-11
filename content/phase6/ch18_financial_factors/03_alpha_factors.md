## Alpha因子计算与预处理

### 3.1 Alpha因子概述

Alpha因子是量化投资中的核心概念，指能够预测股票未来超额收益的量化特征。与技术指标不同，Alpha因子更侧重于统计意义上的预测能力，通常通过截面上（Cross-Sectional）的分析来评估其有效性。

本章重点介绍五类基本Alpha因子的DolphinDB实现方法，以及因子的标准化预处理流程。

### 3.2 动量因子

动量因子（Momentum Factor）基于"强者恒强"的效应，捕捉股票价格的持续性趋势。

#### 3.2.1 N日收益率动量

```
// 20日动量因子：过去20日的累计收益率
mom20 = close / move(close, 20) - 1

// 60日动量（扣除最近5日，避免短期反转干扰）
mom60_5 = move(close, 5) / move(close, 60) - 1

// 12-1月动量（经典动量因子）
mom12_1 = move(close, 1) / move(close, 252) - 1
```

#### 3.2.2 夏普比动量

不仅考虑收益率大小，还考虑波动性：

```
returns = log(close / move(close, 1))
mom_sharpe_60 = avg(returns, 60) / std(returns, 60)  // 过去60日夏普比
```

### 3.3 反转因子

反转因子（Reversal Factor）捕捉"物极必反"的效应，短期过度上涨后倾向于回调，过度下跌后倾向于反弹。

```
// 5日短期反转因子
rev5 = - (close / move(close, 5) - 1)  // 取负数，值越大代表反转潜力越大

// 日内反转（基于日内最高价与开盘价差距）
intraday_rev = - (close - open) / open

// 成交量加权反转（放量下跌后的反转更可靠）
vol_weighted_rev = - (close / move(close, 5) - 1) * (volume / move(volume, 20))
```

> **关键区分**：短期反转因子（1-5天）通常有效，中期动量因子（3-12个月）通常有效，但中间的过渡期（1-3个月）两者可能都不稳定。

### 3.4 波动率因子

波动率因子衡量价格变动的幅度和稳定性：

```
// 日波动率（收益率标准差）
daily_vol = std(returns, 20)

// 振幅因子
range_factor = (high - low) / close

// 上行波动率 vs 下行波动率
up_returns = iif(returns > 0, returns, 0)
down_returns = iif(returns < 0, abs(returns), 0)
up_vol = std(up_returns, 20)      // 上行波动率
down_vol = std(down_returns, 20)  // 下行波动率

// 波动率变化（波动率相对于过去水平的变化）
vol_change = std(returns, 20) / move(std(returns, 20), 60) - 1

// 最大回撤因子（过去N日的最大回撤）
def maxDrawdown(close, n=60) {
    high_water = move(max(close, n), 0)  // 简化：需滚动计算
    dd = (close - max(high, n)) / max(high, n)
    return min(dd, n)
}
```

### 3.5 成交量因子

成交量因子从交易量中提取市场参与度和资金流向信息：

```
// 成交量比率（相对过去平均水平）
vol_ratio = volume / avg(volume, 20)

// VWAP偏离（收盘价相对成交量加权均价的偏离）
vwap = cumsum(close * volume) / cumsum(volume)
vwap_dev = (close - vwap) / vwap

// 换手率（流动性度量）
turnover = volume / totalShares

// 量价相关性（价格变化与成交量变化的相关性）
price_chg = close / move(close, 1) - 1
vol_chg = volume / move(volume, 1) - 1
price_vol_corr = mcorr(price_chg, vol_chg, 20)
```

### 3.6 流动性因子

流动性因子衡量交易的容易程度和交易成本：

```
// Amihud非流动性指标（价格对交易量的敏感度）
amihud = abs(returns) / amount      // amount = 成交额

// 取20日均值以平滑
amihud_20 = avg(amihud, 20)

// 流动性比率（日收益率与换手率比值）
liquidity_ratio = abs(returns) / turnover

// 波动调整换手率
vol_adj_turnover = turnover / std(returns, 60)
```

> **Amihud指标解读**：该值越大说明流动性越差——较小的成交金额就能引发较大的价格波动。低Amihud值的股票流动性更好，交易成本更低。

### 3.7 因子预处理

原始因子值通常需要经过多步预处理才能用于建模。标准的因子预处理流程包括四个步骤：

#### 3.7.1 异常值处理（Winsorization/去极值）

```
// 百分位截尾（Winsorization）
def winsorize(factor, lower_pct=0.01, upper_pct=0.99) {
    lower_bound = percentile(factor, lower_pct * 100)
    upper_bound = percentile(factor, upper_pct * 100)
    result = iif(factor < lower_bound, lower_bound, factor)
    result = iif(result > upper_bound, upper_bound, result)
    return result
}

// MAD方法（中位数绝对偏差法）
def mad_winsorize(factor, n_dev=5) {
    med = median(factor)
    mad = median(abs(factor - med))
    upper_bound = med + n_dev * mad
    lower_bound = med - n_dev * mad
    result = iif(factor < lower_bound, lower_bound, factor)
    result = iif(result > upper_bound, upper_bound, result)
    return result
}
```

#### 3.7.2 缺失值处理

```
// 缺失值填充
factor_filled = nullFill!(factor, 0)              // 用0填充
factor_filled = nullFill!(factor, median(factor)) // 用中位数填充
// 分组均值填充
factor_group_filled = nullFill!(factor, avg(factor))
```

#### 3.7.3 标准化（Standardization）

```
// Z-Score标准化（最常用）
factor_std = (factor - avg(factor)) / std(factor)

// 通过context by在每个截面上分别标准化
factor_std = select
    Symbol, TradeDate,
    (factor - avg(factor)) / std(factor) as factor_std
from factorTable
context by TradeDate     // 每个交易日截面独立标准化

// 排名标准化（更稳健，不受极端值影响）
factor_rank = rank(factor) / count(factor)
```

#### 3.7.4 中性化（Neutralization）

中性化是指消除因子中的系统性偏差，最常用的是市值中性化和行业中性化：

```
// 市值中性化（回归取残差）
use stats
// 将因子对市值做线性回归，取残差作为中性化后的因子
factor_neu_market = stats::ols(factor, [1, marketCap], intercept=true).residual

// 行业中性化（减去行业均值）
factor_neu_ind = select
    Symbol, TradeDate,
    factor - avg(factor) as factor_neu_ind
from factorTable
context by TradeDate, Industry   // 按日期和行业分组
```

### 3.8 完整预处理流程示例

以下是一个完整的因子预处理实现：

```
// 完整的因子预处理流水线
def preprocessFactor(factor, tradeDate, symbol, marketCap, industry) {
    // 步骤1：异常值处理（t × 截面）
    factor_clean = select
        Symbol, TradeDate,
        iif(factor < -3 * std(factor) + avg(factor),
            -3 * std(factor) + avg(factor),
            iif(factor > 3 * std(factor) + avg(factor),
                3 * std(factor) + avg(factor),
                factor)) as factor
    from table(tradeDate, symbol, factor)
    context by TradeDate

    // 步骤2：缺失值填充
    factor_filled = nullFill!(factor_clean, 0)

    // 步骤3：标准化
    factor_std = (factor_filled - avg(factor_filled)) / std(factor_filled)

    // 步骤4：中性化
    // ... （按市值和行业做中性化处理）
    return factor_std
}
```

### 3.9 预处理注意事项

1. **截面处理**：标准化和去极值必须在同一交易日截面上进行（`context by TradeDate`），不能跨日期处理
2. **处理顺序**：必须先去极值再标准化，否则极值会严重影响均值和标准差
3. **幸存者偏差**：预处理时应包含所有历史股票，不能只处理当前存活的股票
4. **前瞻偏差**：预处理只能使用截至当前日期的数据，不能依赖未来信息
5. **一致性**：训练集和测试集使用相同的预处理参数（如训练集的均值和标准差）
