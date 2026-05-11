## 信号生成的基本概念

信号（Signal）是量化交易策略的核心输入。信号可以理解为一个数值或分类，表示对资产未来收益方向的预测。好的信号应具备以下特性：

- **预测性**：信号值与未来收益之间存在统计上显著的相关性
- **稳定性**：信号的预测能力在时间上保持相对稳定
- **可解释性**：信号背后的经济逻辑清晰合理

### 信号的类型

量化策略中常见的信号类型包括：

| 信号类型 | 输出形式 | 示例 |
|----------|----------|------|
| **方向信号** | 离散值（买入/持有/卖出） | MACD金叉死叉 |
| **强度信号** | 连续值（-1到1或0到1） | RSI标准化值 |
| **排序信号** | 排名（1到N） | 动量因子排名 |
| **概率信号** | 概率值（0到1） | 机器学习预测概率 |

### 技术指标作为信号

技术指标是量化策略中最常用的信号来源。它们通过对价格、成交量等市场数据的数学变换，提取出有助于预测价格走势的信息。

#### 趋势类指标

趋势类指标用于识别和确认价格趋势的方向和强度：

```python
import pandas as pd
import numpy as np

def compute_trend_signals(df):
    """
    计算常见的趋势类信号
    """
    df = df.copy()
    
    # 1. 移动平均线 (MA)
    df['ma_5'] = df['close'].rolling(5).mean()
    df['ma_20'] = df['close'].rolling(20).mean()
    df['ma_60'] = df['close'].rolling(60).mean()
    
    # 方向信号：价格在均线上方为1（看多），下方为-1（看空）
    df['ma_trend'] = np.where(df['close'] > df['ma_20'], 1, -1)
    
    # 2. MACD (指数平滑异同移动平均线)
    ema_12 = df['close'].ewm(span=12, adjust=False).mean()
    ema_26 = df['close'].ewm(span=26, adjust=False).mean()
    df['macd'] = ema_12 - ema_26
    df['macd_signal'] = df['macd'].ewm(span=9, adjust=False).mean()
    df['macd_hist'] = df['macd'] - df['macd_signal']
    
    # MACD方向信号
    df['macd_trend'] = np.where(df['macd'] > df['macd_signal'], 1, -1)
    
    # 3. ADX (平均趋向指数) - 衡量趋势强度
    high, low, close = df['high'], df['low'], df['close']
    
    tr1 = high - low
    tr2 = abs(high - close.shift(1))
    tr3 = abs(low - close.shift(1))
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    df['atr'] = tr.rolling(14).mean()  # 平均真实波幅
    
    return df
```

#### 震荡类指标

震荡类指标在特定范围内波动，常用于识别超买超卖和反转信号：

```python
def compute_oscillator_signals(df, period=14):
    """
    计算震荡类信号
    """
    df = df.copy()
    
    # 1. RSI (相对强弱指标)
    delta = df['close'].diff()
    gain = delta.where(delta > 0, 0)
    loss = (-delta).where(delta < 0, 0)
    
    avg_gain = gain.rolling(period).mean()
    avg_loss = loss.rolling(period).mean()
    
    # 使用指数平滑方式（Wilder's smoothing）
    for i in range(period + 1, len(df)):
        avg_gain.iloc[i] = (avg_gain.iloc[i-1] * (period-1) + gain.iloc[i]) / period
        avg_loss.iloc[i] = (avg_loss.iloc[i-1] * (period-1) + loss.iloc[i]) / period
    
    rs = avg_gain / avg_loss
    df['rsi'] = 100 - (100 / (1 + rs))
    
    # RSI信号：超卖区域买入，超买区域卖出
    df['rsi_signal'] = 0
    df.loc[df['rsi'] < 30, 'rsi_signal'] = 1    # 超卖买入
    df.loc[df['rsi'] > 70, 'rsi_signal'] = -1   # 超买卖出
    
    # 2. 随机指标 (KDJ/Stochastic)
    low_min = df['low'].rolling(period).min()
    high_max = df['high'].rolling(period).max()
    
    df['k'] = 100 * (df['close'] - low_min) / (high_max - low_min)
    df['d'] = df['k'].rolling(3).mean()
    df['j'] = 3 * df['k'] - 2 * df['d']
    
    # 3. 威廉指标 (Williams %R)
    df['wr'] = -100 * (high_max - df['close']) / (high_max - low_min)
    
    return df
```

#### 波动率与成交量信号

```python
def compute_volume_volatility_signals(df, period=20):
    """
    计算成交量和波动率信号
    """
    df = df.copy()
    
    # 1. 布林带宽度（衡量波动率）
    df['bb_mid'] = df['close'].rolling(period).mean()
    bb_std = df['close'].rolling(period).std()
    df['bb_upper'] = df['bb_mid'] + 2 * bb_std
    df['bb_lower'] = df['bb_mid'] - 2 * bb_std
    df['bb_width'] = (df['bb_upper'] - df['bb_lower']) / df['bb_mid']
    df['bb_position'] = (df['close'] - df['bb_lower']) / (df['bb_upper'] - df['bb_lower'])
    
    # 2. 历史波动率
    returns = df['close'].pct_change()
    df['hist_vol'] = returns.rolling(period).std() * np.sqrt(252)
    
    # 3. 成交量信号
    df['vol_ma'] = df['volume'].rolling(20).mean()
    df['vol_ratio'] = df['volume'] / df['vol_ma']  # 量比
    
    # 放量信号
    df['vol_breakout'] = np.where(df['vol_ratio'] > 1.5, 1, 0)
    
    # 4. OBV (能量潮) - 累积成交量方向
    df['obv'] = (np.sign(df['close'].diff()) * df['volume']).fillna(0).cumsum()
    
    return df
```

### 信号组合与合成

单一信号往往噪声较大，组合多个信号可以提高预测的稳定性和准确性。常见的信号组合方法包括：

#### 方法一：加权组合

```python
def weighted_signal_composition(df, signals, weights):
    """
    将多个信号按权重组合
    
    参数:
        df: 包含各信号列的DataFrame
        signals: 信号列名列表
        weights: 对应权重列表（应总和为1）
    """
    # 首先将各信号标准化到相同范围（如[-1, 1]或[0, 1]）
    standardized = pd.DataFrame()
    for sig, w in zip(signals, weights):
        # Z-score标准化
        normalized = (df[sig] - df[sig].mean()) / df[sig].std()
        # 使用tanh函数压缩到[-1, 1]，减少极端值影响
        standardized[sig] = np.tanh(normalized)
    
    # 加权组合
    composite = sum(standardized[s] * w for s, w in zip(signals, weights))
    return composite
```

#### 方法二：投票机制

```python
def voting_signal_composition(df, signals):
    """
    多信号投票机制
    每个信号给出方向（看多=1, 看空=-1），按多数决定
    """
    # 将各信号转换为方向
    directions = pd.DataFrame()
    for sig in signals:
        directions[sig] = np.where(df[sig] > 0, 1, -1)
    
    # 投票（等权重）
    vote_sum = directions.sum(axis=1)
    
    # 多数决定：净票数>0看多，<0看空
    composite = np.where(vote_sum > 0, 1, np.where(vote_sum < 0, -1, 0))
    
    # 同时给出置信度（一致性程度）
    confidence = abs(vote_sum) / len(signals)
    
    return composite, confidence
```

#### 方法三：条件逻辑

```python
def conditional_signal_composition(df):
    """
    基于条件逻辑的复合信号
    例如：趋势向上 AND 短期超卖 → 买入
    """
    df = df.copy()
    
    # 定义条件
    trend_up = df['ma_20'] > df['ma_60']           # 中期趋势向上
    oversold = df['rsi'] < 30                       # 短期超卖
    high_volume = df['vol_ratio'] > 1.2             # 有量能支持
    
    # 组合逻辑
    df['composite_signal'] = 0
    df.loc[trend_up & oversold & high_volume, 'composite_signal'] = 1  # 强买入
    df.loc[trend_up & oversold, 'composite_signal'] = 0.5              # 弱买入
    df.loc[~trend_up & (df['rsi'] > 70), 'composite_signal'] = -1     # 卖出
    
    return df
```

### 信号质量评估

生成信号后，需要评估其预测质量：

```python
def evaluate_signal_quality(df, signal_col, forward_periods=[1, 5, 10]):
    """
    评估信号的预测质量
    
    返回:
        各未来周期的IC值和胜率
    """
    # 计算未来收益
    future_returns = {}
    for p in forward_periods:
        future_returns[p] = df['close'].shift(-p) / df['close'] - 1
    
    results = {}
    for p in forward_periods:
        # 信息系数 (IC) - 信号与未来收益的相关性
        valid_data = pd.DataFrame({
            'signal': df[signal_col],
            'fwd_ret': future_returns[p]
        }).dropna()
        
        if len(valid_data) > 10:
            ic = valid_data['signal'].corr(valid_data['fwd_ret'])
            # 方向胜率
            correct = (np.sign(valid_data['signal']) == np.sign(valid_data['fwd_ret'])).mean()
            results[f'IC_{p}d'] = ic
            results[f'win_rate_{p}d'] = correct
    
    return results
```

> **温馨提示**：信号并不需要完美预测每一次价格波动。一个好的信号只需要在市场大多数时候提供统计上的优势即可。正如交易格言所说："重要的不是正确率，而是正确的仓位赚多少，错误的仓位亏多少。"
