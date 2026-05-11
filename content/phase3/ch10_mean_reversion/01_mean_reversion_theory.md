## 均值回归的基本原理

均值回归（Mean Reversion）是金融市场中最基本的统计现象之一：资产价格在短期偏离其长期均值后，有回归均值的倾向。如果说趋势跟踪是"顺势而为"，均值回归就是"逆势而行"——在价格超跌时买入、超涨时卖出，博弈价格回到正常轨道。

### 均值回归的统计学基础

从统计学角度看，均值回归假设价格序列至少具备以下特性之一：

#### 1. 平稳性（Stationarity）

一个平稳的时间序列，其统计特性（均值、方差）不随时间变化。平稳序列在偏离均值后会自然回归。

```python
import numpy as np
import pandas as pd
from statsmodels.tsa.stattools import adfuller


def test_stationarity(series, significance=0.05):
    """
    ADF检验（Augmented Dickey-Fuller Test）
    检验时间序列是否平稳
    
    H0（原假设）：序列存在单位根，即非平稳
    H1（备择假设）：序列平稳
    """
    result = adfuller(series.dropna(), autolag='AIC')
    
    adf_stat = result[0]
    p_value = result[1]
    critical_values = result[4]
    
    is_stationary = p_value < significance
    
    print("=== ADF单位根检验 ===")
    print(f"ADF统计量: {adf_stat:.4f}")
    print(f"p值: {p_value:.4f}")
    print("临界值:")
    for key, value in critical_values.items():
        print(f"  {key}: {value:.4f}")
    print(f"结论: {'平稳' if is_stationary else '非平稳'}")
    
    return is_stationary, p_value
```

> **重要**：绝大多数价格序列是非平稳的（如股票价格一直涨），但价格收益率或其线性组合（如配对交易的价差）可能是平稳的。找到平稳的关系是均值回归策略成功的关键。

#### 2. 协整（Cointegration）

两个或多个非平稳序列之间可能存在长期均衡关系，这种关系是平稳的。著名的配对交易（Pairs Trading）就基于协整关系。

```python
from statsmodels.tsa.stattools import coint

def test_cointegration(series1, series2, significance=0.05):
    """
    协整检验（Engle-Granger方法）
    
    H0：两个序列不是协整的
    H1：两个序列是协整的
    """
    coint_t, p_value, critical_values = coint(series1, series2)
    
    is_cointegrated = p_value < significance
    
    print("=== 协整检验 ===")
    print(f"协整统计量: {coint_t:.4f}")
    print(f"p值: {p_value:.4f}")
    print(f"结论: {'协整' if is_cointegrated else '非协整'}")
    
    return is_cointegrated, p_value
```

#### 3. 自相关性

许多均值回归策略利用收益率的一阶负自相关——今天的收益率与明天的收益率呈负相关关系。

```python
def test_autocorrelation(returns, lags=[1, 5, 10]):
    """
    检验收益率的自相关性
    
    负的自相关支持均值回归假设
    """
    results = {}
    for lag in lags:
        autocorr = returns.autocorr(lag=lag)
        results[lag] = autocorr
        print(f"滞后{lag}期自相关系数: {autocorr:.4f}")
    return results
```

---

### 二、均值回归策略成立的条件

| 条件 | 说明 | 检验方法 |
|------|------|----------|
| 价格有均值 | 存在明确的"正常"价格水平 | 长期移动平均、基本面估值 |
| 存在偏离机制 | 价格会短期大幅偏离均值 | 波动率分析 |
| 存在回归机制 | 偏离后价格会回归 | ADF检验、自相关分析 |
| 回归时间可预测 | 回归通常在一定时间内发生 | 半衰期分析 |

#### 均值回归的半衰期

半衰期（Half-Life）衡量序列偏离后回归均值一半所需的时间，是衡量回归速度的关键参数：

```python
def estimate_half_life(spread):
    """
    估计均值回归的半衰期
    
    方法：对价差序列拟合 OU过程（Ornstein–Uhlenbeck process）
    dX = θ(μ - X)dt + σdW
    
    半衰期 = ln(2) / θ
    """
    spread = spread.dropna()
    
    # 计算下一期与当前期的差值
    spread_lag = spread.shift(1).dropna()
    spread_diff = spread.diff().dropna()
    
    # 对齐数据
    common_idx = spread_lag.index.intersection(spread_diff.index)
    X = spread_lag[common_idx].values
    y = spread_diff[common_idx].values
    
    # OLS: X_{t+1} - X_t = α + β * X_t
    X_with_const = np.column_stack([np.ones(len(X)), X])
    X_with_const = X_with_const[~np.isnan(y), :]
    y = y[~np.isnan(y)]
    
    coef = np.linalg.lstsq(X_with_const, y, rcond=None)[0]
    
    # θ = -β
    theta = -coef[1]
    half_life = np.log(2) / theta if theta > 0 else np.inf
    
    print(f"均值回复速度 θ: {theta:.4f}")
    print(f"半衰期: {half_life:.1f} 个周期")
    
    return half_life, theta
```

---

### 三、均值回归策略的典型形式

#### 形式1：价格偏离均线策略

```python
def zscore_deviation(prices, window=20):
    """
    计算价格偏离均值的Z-score
    
    Z-score = (price - moving_average) / moving_std
    """
    ma = prices.rolling(window).mean()
    std = prices.rolling(window).std()
    zscore = (prices - ma) / std
    return zscore


def deviation_signals(zscore, entry_threshold=2.0, exit_threshold=0.5):
    """
    基于Z-score偏离的交易信号
    
    Z-score > entry_threshold → 超涨，做空
    Z-score < -entry_threshold → 超跌，做多
    |Z-score| < exit_threshold → 回归均值，平仓
    """
    df['signal'] = 0
    
    # 入场条件
    df.loc[zscore > entry_threshold, 'signal'] = -1   # 超涨做空
    df.loc[zscore < -entry_threshold, 'signal'] = 1   # 超跌做多
    
    # 出场条件（回归均值）
    df.loc[(zscore.abs() < exit_threshold) & (df['position'] != 0), 'signal'] = 0
    
    return df
```

#### 形式2：RSI超买超卖策略

```python
def rsi_mean_reversion(prices, period=14, oversold=30, overbought=70):
    """
    RSI均值回归策略
    RSI < oversold → 超卖买入
    RSI > overbought → 超买卖出
    """
    delta = prices.diff()
    gain = delta.clip(lower=0)
    loss = (-delta).clip(lower=0)
    
    avg_gain = gain.rolling(period).mean()
    avg_loss = loss.rolling(period).mean()
    
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    
    signals = pd.Series(0, index=prices.index)
    signals[rsi < oversold] = 1
    signals[rsi > overbought] = -1
    
    return signals, rsi
```

---

### 四、均值回归策略的风险管理

```python
def mean_reversion_risk_control(df, max_holding_days=10, 
                                  stop_loss_pct=0.05, 
                                  volatility_filter=True):
    """
    均值回归策略的风险控制
    
    风险1：趋势市场中的连续亏损
    风险2：垃圾资产的价值陷阱
    风险3：回归速度太慢
    """
    df = df.copy()
    
    # 1. 持仓天数限制（防止"死扛"）
    df['holding_days'] = 0
    holding_start = 0
    for i in range(len(df)):
        if df['position'].iloc[i] != 0:
            if holding_start == 0:
                holding_start = i
            df['holding_days'].iloc[i] = i - holding_start
        else:
            holding_start = 0
    
    # 持仓超过最大天数则强制平仓
    df.loc[df['holding_days'] > max_holding_days, 'signal'] = 0
    
    # 2. 止损控制
    # 使用累计亏损比例作为止损条件
    cumulative_returns = (1 + df['returns']).cumprod()
    df['drawdown'] = cumulative_returns / cumulative_returns.cummax() - 1
    df.loc[df['drawdown'] < -stop_loss_pct, 'signal'] = 0
    
    # 3. 波动率过滤（高波动时谨慎参与）
    if volatility_filter:
        df['volatility'] = df['returns'].rolling(20).std() * np.sqrt(252)
        vol_threshold = df['volatility'].quantile(0.8)
        df.loc[df['volatility'] > vol_threshold, 'signal'] = 0
    
    return df
```

> **核心风险提示**：均值回归策略最大的风险来自"趋势突破"——当均值回归信号触发时，如果价格实际上正在开始一段新的趋势（而非暂时偏离），策略会遭受重大损失。这也是为什么大多数专业量化机构会将均值回归和趋势跟踪策略组合使用，而非依赖单一逻辑。
