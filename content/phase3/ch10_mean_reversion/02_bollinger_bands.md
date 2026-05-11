## 布林带（Bollinger Bands）详解

布林带由John Bollinger在1980年代提出，是量化交易中最经典的技术指标之一。它由三条线组成，直观地展示了价格的相对高低位置和波动率水平。

### 布林带的构成

布林带由三条线组成：

| 线名 | 公式 | 含义 |
|------|------|------|
| **中轨** | SMA(N) = N期简单移动平均 | 价格趋势的"均值" |
| **上轨** | 中轨 + K × σ(N) | 价格区间的上边界 |
| **下轨** | 中轨 - K × σ(N) | 价格区间的下边界 |

其中：
- N：计算周期（通常为20）
- K：标准差倍数（通常为2）
- σ(N)：N期收益率的标准差

```python
import numpy as np
import pandas as pd


def calculate_bollinger_bands(df, period=20, num_std=2.0, price_col='close'):
    """
    计算布林带
    
    参数:
        period: 计算周期
        num_std: 标准差倍数
        price_col: 价格列名
    """
    df = df.copy()
    
    # 中轨（20日均线）
    df['bb_middle'] = df[price_col].rolling(period).mean()
    
    # 标准差
    rolling_std = df[price_col].rolling(period).std()
    
    # 上下轨
    df['bb_upper'] = df['bb_middle'] + num_std * rolling_std
    df['bb_lower'] = df['bb_middle'] - num_std * rolling_std
    
    # 布林带宽度（波动率指标）
    df['bb_width'] = (df['bb_upper'] - df['bb_lower']) / df['bb_middle']
    
    # %b指标：价格在布林带中的相对位置
    # %b = (price - lower) / (upper - lower)
    # %b > 1 → 价格在上轨之上
    # %b < 0 → 价格在下轨之下
    df['bb_pct_b'] = (df[price_col] - df['bb_lower']) / \
                      (df['bb_upper'] - df['bb_lower'])
    
    # 带宽指标（BandWidth）
    # 带宽变窄通常预示大行情即将到来
    df['bb_bandwidth'] = (df['bb_upper'] - df['bb_lower']) / df['bb_middle']
    
    return df
```

---

### 一、布林带的核心统计含义

布林带基于一个重要的统计假设：**价格在大多数时间内会在中轨上下两个标准差范围内波动**。

| 统计特性 | 含义 |
|----------|------|
| 假设价格服从正态分布 | 约95%的价格波动落在±2σ范围内 |
| 上轨 = 阻力位 | 价格触及上轨意味着价格偏高 |
| 下轨 = 支撑位 | 价格触及下轨意味着价格偏低 |
| 带宽变窄 | 低波动 → 蓄力 → 即将突破 |
| 带宽变宽 | 高波动 → 行情展开中 |

---

### 二、布林带均值回归策略

核心交易逻辑：当价格触及上下轨时，假设价格会向中轨回归。

#### 策略规则

```python
def bollinger_band_strategy(df, period=20, num_std=2.0):
    """
    布林带均值回归策略
    
    入场规则：
    - 价格跌破下轨 → 买入（超跌信号）
    - 价格突破上轨 → 卖出/做空（超涨信号）
    
    出场规则：
    - 价格回归中轨 → 平仓
    - 价格突破反向通道 → 止损
    """
    df = calculate_bollinger_bands(df, period, num_std)
    
    # 生成信号
    df['signal'] = 0
    df['position'] = 0
    
    # 买入信号：价格从上向下穿透下轨
    df.loc[df['close'] <= df['bb_lower'], 'signal'] = 1
    
    # 卖出信号：价格从下向上穿透上轨
    df.loc[df['close'] >= df['bb_upper'], 'signal'] = -1
    
    # 平仓信号：价格回到中轨
    # 持仓状态下，价格穿越中轨时平仓
    for i in range(1, len(df)):
        prev_close = df['close'].iloc[i-1]
        prev_mid = df['bb_middle'].iloc[i-1]
        curr_close = df['close'].iloc[i]
        curr_mid = df['bb_middle'].iloc[i]
        
        # 多仓平仓：价格从下方穿越中轨
        if df['position'].iloc[i-1] == 1 and \
           prev_close <= prev_mid and curr_close >= curr_mid:
            df.loc[df.index[i], 'signal'] = 0
            df.loc[df.index[i], 'position'] = 0
        
        # 空仓平仓：价格从上方穿越中轨
        elif df['position'].iloc[i-1] == -1 and \
             prev_close >= prev_mid and curr_close <= curr_mid:
            df.loc[df.index[i], 'signal'] = 0
            df.loc[df.index[i], 'position'] = 0
    
    return df
```

#### 完整的策略回测实现

```python
class BollingerBandStrategy:
    """
    布林带均值回归策略
    """
    
    def __init__(self, period=20, num_std=2.0, initial_capital=100000):
        self.period = period
        self.num_std = num_std
        self.initial_capital = initial_capital
    
    def run(self, df):
        """
        运行策略回测
        """
        df = calculate_bollinger_bands(df, self.period, self.num_std)
        
        capital = self.initial_capital
        position = 0      # 持仓股数
        in_position = False
        position_type = 0  # 1=多头, -1=空头
        
        portfolio_values = []
        trades = []
        
        for i in range(len(df)):
            price = df['close'].iloc[i]
            bb_lower = df['bb_lower'].iloc[i]
            bb_middle = df['bb_middle'].iloc[i]
            bb_upper = df['bb_upper'].iloc[i]
            
            # === 交易逻辑 ===
            action = None
            
            if not in_position:
                if price <= bb_lower:
                    # 买入信号
                    shares = int(capital * 0.95 / price)  # 留5%现金
                    cost = shares * price * (1 + 0.0003)  # 含手续费
                    if cost <= capital:
                        capital -= cost
                        position = shares
                        in_position = True
                        position_type = 1
                        action = 'BUY'
                
                elif price >= bb_upper:
                    # 做空信号（这里简化，用卖出持仓表示）
                    action = 'SHORT_SIGNAL'
            
            else:  # 已在持仓中
                # 多头平仓条件
                if position_type == 1:
                    # 回到中轨平仓
                    if i > 0 and df['close'].iloc[i-1] <= bb_middle and price >= bb_middle:
                        revenue = position * price * (1 - 0.0003)
                        capital += revenue
                        trades.append({
                            'exit_date': df.index[i],
                            'exit_price': price,
                            'pnl': revenue - (position * df['close'].iloc[i] / (1 + 0.0003))
                        })
                        position = 0
                        in_position = False
                        position_type = 0
                        action = 'SELL'
                    
                    # 止损：跌破下轨以下另一个标准差
                    elif price <= df['bb_lower'].iloc[i] * (1 - 0.02):
                        revenue = position * price * (1 - 0.0003)
                        capital += revenue
                        position = 0
                        in_position = False
                        position_type = 0
                        action = 'STOP_LOSS'
            
            # 记录组合价值
            portfolio_value = capital + position * price
            portfolio_values.append(portfolio_value)
        
        df['portfolio_value'] = portfolio_values
        df['returns'] = df['portfolio_value'].pct_change()
        df['equity_curve'] = df['portfolio_value'] / self.initial_capital
        
        self.trades = trades
        return df
```

---

### 三、%b 和 BandWidth 指标详解

#### %b 指标（相对位置）

%b 衡量价格在布林带区间内的相对位置，是均值回归策略的关键信号：

```python
def analyze_pct_b_signals(df):
    """
    分析%b指标的交易含义
    
    %b值范围及含义：
    - %b < 0：价格在下轨之下（超跌）
    - 0 < %b < 0.5：价格在区间的下半部分
    - %b = 0.5：价格恰好在均值处
    - 0.5 < %b < 1：价格在区间的上半部分
    - %b > 1：价格在上轨之上（超涨）
    """
    df = df.copy()
    
    # 基于%b的增强信号
    df['bb_signal_pct_b'] = 0
    
    # 强烈的买入信号：%b < 0（价格在下轨之下）
    df.loc[df['bb_pct_b'] < 0, 'bb_signal_pct_b'] = 1
    
    # 强烈的卖出信号：%b > 1（价格在上轨之上）
    df.loc[df['bb_pct_b'] > 1, 'bb_signal_pct_b'] = -1
    
    return df
```

#### BandWidth 指标（带宽）

```python
def analyze_bandwidth(df, lookback=125, percentile=10):
    """
    带宽分析 —— 布林带挤压（Bollinger Squeeze）
    
    当带宽压缩到历史低位时，预示大行情即将到来
    """
    # 计算带宽在历史中的分位数
    bandwidth_rank = df['bb_bandwidth'].rolling(lookback).apply(
        lambda x: (x.iloc[-1] <= x).sum() / len(x) * 100
    )
    
    # 带宽低于历史10%分位 → 挤压状态
    df['bb_squeeze'] = bandwidth_rank < percentile
    
    return df


def squeeze_strategy(df):
    """
    布林带挤压 + 突破策略
    
    当带宽压缩到极低水平后：
    - 价格突破上轨 → 趋势突破做多
    - 价格跌破下轨 → 趋势突破做空
    """
    df = calculate_bollinger_bands(df, 20, 2.0)
    df = analyze_bandwidth(df)
    
    df['squeeze_signal'] = 0
    
    for i in range(1, len(df)):
        if df['bb_squeeze'].iloc[i-1]:  # 前期处于挤压状态
            if df['close'].iloc[i] > df['bb_upper'].iloc[i-1]:
                df.loc[df.index[i], 'squeeze_signal'] = 1  # 向上突破做多
            elif df['close'].iloc[i] < df['bb_lower'].iloc[i-1]:
                df.loc[df.index[i], 'squeeze_signal'] = -1  # 向下突破做空
    
    return df
```

---

### 四、参数优化与经验法则

| 参数 | 常用值 | 调整方向 | 效果 |
|------|--------|----------|------|
| 中轨周期 | 20 | 增大 | 更平滑，信号更少 |
| | | 减小 | 更敏感，信号更多 |
| 标准差倍数 | 2.0 | 增大 | 通道变宽，信号更少但更可靠 |
| | | 减小 | 通道变窄，信号更多但假信号也多 |

```python
def optimize_bb_parameters(df, period_range, std_range, 
                            metric='sharpe_ratio'):
    """
    布林带参数网格搜索
    """
    results = []
    
    for period in period_range:
        for num_std in std_range:
            strategy = BollingerBandStrategy(
                period=period, num_std=num_std
            )
            result = strategy.run(df.copy())
            
            # 计算夏普比率
            returns = result['returns'].dropna()
            sharpe = returns.mean() / returns.std() * np.sqrt(252)
            
            results.append({
                'period': period,
                'num_std': num_std,
                'sharpe': sharpe,
                'total_return': result['equity_curve'].iloc[-1] - 1,
                'max_drawdown': (result['equity_curve'] / 
                                result['equity_curve'].cummax() - 1).min()
            })
    
    return pd.DataFrame(results).sort_values(metric, ascending=False)
```

> **使用建议**：布林带在日内交易和短线波段交易中表现出色，但需要配合趋势判断使用。在强趋势市场中，价格可以长时间"贴着上轨运行"——此时均值回归信号会不断触发假卖出信号。一种常见的做法是结合ADX来过滤：当ADX > 25（趋势明确）时关闭均值回归策略，当ADX < 20（震荡市）时启用。
