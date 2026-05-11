## 移动平均线（Moving Average）基础

移动平均线是量化交易中最古老、最基础、也是最广泛使用的技术分析工具。它通过对一定时期内的价格进行平均，来平滑价格波动，揭示潜在的趋势方向。

### 移动平均线的本质

移动平均线的核心思想是：**通过平均化消除随机噪声，提取价格的趋势成分**。假设价格由两部分组成：

```
Price = Trend + Noise
```

移动平均线作为一个低通滤波器，滤除高频噪声分量，保留低频趋势信号。不同的移动平均计算方法对"近期的权重"有不同的处理方式。

---

### 一、简单移动平均线 (SMA)

简单移动平均线（Simple Moving Average，SMA）是对过去N个周期收盘价的算术平均值。

#### 数学定义

```
SMA(t, N) = (P_t + P_{t-1} + ... + P_{t-N+1}) / N
```

其中 P_t 是第 t 期的价格，N 是计算周期。

#### SMA的特点

| 特点 | 说明 |
|------|------|
| 优点 | 计算简单，含义直观，每个数据点权重相等 |
| 缺点 | 对旧数据和新数据一视同仁，反应迟钝 |
| 滞后性 | N越大，滞后越大；N越小，越贴近价格但噪声更多 |

```python
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

def calculate_sma(prices, window):
    """计算简单移动平均线"""
    return prices.rolling(window=window).mean()


# 生成示例数据
np.random.seed(42)
dates = pd.date_range('2024-01-01', periods=200, freq='D')
trend = np.linspace(100, 120, 200)  # 上升趋势
noise = np.random.randn(200) * 2     # 随机噪声
price = trend + noise
df = pd.DataFrame({'price': price}, index=dates)

# 计算不同周期的SMA
df['sma_5'] = calculate_sma(df['price'], 5)
df['sma_10'] = calculate_sma(df['price'], 10)
df['sma_20'] = calculate_sma(df['price'], 20)
df['sma_60'] = calculate_sma(df['price'], 60)

print("SMA计算示例（最后5行）：")
print(df[['price', 'sma_5', 'sma_10', 'sma_20']].tail())
```

---

### 二、指数移动平均线 (EMA)

指数移动平均线（Exponential Moving Average，EMA）赋予近期价格更高的权重，使均线对最新价格变化更加敏感。

#### 数学定义

```
EMA(t, N) = α × P_t + (1 - α) × EMA(t-1, N)
```

其中：
- α = 2/(N+1) （平滑因子，也写作span）
- EMA(0, N) = SMA(N)（初始值通常用SMA）

```python
def calculate_ema(prices, span, adjust=False):
    """计算指数移动平均线"""
    return prices.ewm(span=span, adjust=adjust).mean()


df['ema_5'] = calculate_ema(df['price'], 5)
df['ema_10'] = calculate_ema(df['price'], 10)
df['ema_20'] = calculate_ema(df['price'], 20)

# 对比SMA和EMA的响应速度
def analyze_ma_responsiveness(df, periods=[5, 20]):
    """分析SMA和EMA在趋势转折点的响应速度差异"""
    for p in periods:
        sma_col = f'sma_{p}'
        ema_col = f'ema_{p}'
        
        # 计算均线与价格的偏差（反映滞后程度）
        sma_lag = (df['price'] - df[sma_col]).abs().mean()
        ema_lag = (df['price'] - df[ema_col]).abs().mean()
        
        print(f"周期={p}: SMA平均偏差={sma_lag:.3f}, EMA平均偏差={ema_lag:.3f}")
        print(f"  EMA比SMA更贴近价格：{(sma_lag - ema_lag) / sma_lag * 100:.1f}%")
```

#### SMA vs EMA 对比

```python
import numpy as np

# 手动实现EMA来理解权重分配
def manual_ema(prices, span):
    """
    手动实现EMA，展示权重衰减
    """
    alpha = 2 / (span + 1)
    ema_values = [prices[0]]  # 初始值使用第一个价格
    
    for i in range(1, len(prices)):
        ema = alpha * prices[i] + (1 - alpha) * ema_values[-1]
        ema_values.append(ema)
    
    # 展示权重的指数衰减
    print(f"\nEMA(span={span}, alpha={alpha:.4f})的权重衰减：")
    remaining_weight = 1.0
    total_weight = 0.0
    for i in range(min(span, 10)):
        weight = alpha * (1 - alpha) ** i
        total_weight += weight
        remaining_weight -= weight
        print(f"  第{i}期前: 权重={weight:.4f}, 累计={total_weight:.4f}, 剩余={remaining_weight:.4f}")
    
    return np.array(ema_values)
```

| 对比维度 | SMA | EMA |
|----------|-----|-----|
| 权重分配 | 等权重 | 指数衰减权重 |
| 反应速度 | 较慢 | 较快 |
| 平滑程度 | 较平滑 | 相对粗糙 |
| 计算复杂度 | O(1)滚动 | O(1)递推 |
| 适用场景 | 长期趋势判断 | 短期交易信号 |

---

### 三、加权移动平均线 (WMA)

加权移动平均线（Weighted Moving Average，WMA）给不同时期的数据点分配线性递减的权重。

#### 数学定义

```
WMA(t, N) = [N × P_t + (N-1) × P_{t-1} + ... + 1 × P_{t-N+1}] / [N + (N-1) + ... + 1]
```

```python
def calculate_wma(prices, window):
    """计算加权移动平均线"""
    weights = np.arange(1, window + 1)
    return prices.rolling(window=window).apply(
        lambda x: np.dot(x, weights) / weights.sum(), raw=True
    )


df['wma_10'] = calculate_wma(df['price'], 10)
```

---

### 四、移动平均线交叉的概念

移动平均线交叉（MA Crossover）是最经典的量化交易信号之一。基本原理是：

- **短期均线**：反映近期趋势，对价格变化敏感
- **长期均线**：反映长期趋势，对价格变化迟钝

当短期均线上穿长期均线时，意味着短期趋势开始强于长期趋势，产生**买入信号**（金叉）。
当短期均线下穿长期均线时，意味着短期趋势开始弱于长期趋势，产生**卖出信号**（死叉）。

```python
def detect_crossover(short_ma, long_ma):
    """
    检测均线交叉点
    
    返回:
        1 = 金叉（短线上穿长线）
       -1 = 死叉（短线下穿长线）
        0 = 无交叉
    """
    # 计算差值
    diff = short_ma - long_ma
    
    # 差值符号变化即为交叉
    diff_sign = np.sign(diff)
    crossover = diff_sign.diff().fillna(0)
    
    # 金叉：差值从负变正
    golden_cross = (crossover > 0).astype(int)
    # 死叉：差值从正变负
    death_cross = (crossover < 0).astype(int) * -1
    
    return golden_cross + death_cross


# 检测5日EMA和20日EMA的交叉信号
df['crossover_signal'] = detect_crossover(df['ema_5'], df['ema_20'])

# 统计交叉频率
golden_crosses = (df['crossover_signal'] == 1).sum()
death_crosses = (df['crossover_signal'] == -1).sum()
print(f"\n金叉次数: {golden_crosses}, 死叉次数: {death_crosses}")
```

### 均线斜率作为补充信号

除了交叉，均线的斜率也能提供有用的趋势信息：

```python
def ma_slope(ma, lookback=5):
    """计算移动平均线的斜率"""
    return (ma - ma.shift(lookback)) / lookback


df['sma_20_slope'] = ma_slope(df['sma_20'], 5)

# 趋势强度信号
# 斜率>0且增大 → 趋势加速向上
# 斜率>0但减小 → 趋势减速向上
# 斜率<0且减小 → 趋势加速向下
# 斜率<0但增大 → 趋势减速向下
df['slope_change'] = df['sma_20_slope'].diff()
```

### 多周期均线系统

专业交易者常使用多周期均线系统来综合判断趋势：

```python
def multi_ma_system(df, periods=[5, 10, 20, 60, 120]):
    """
    多周期均线系统
    
    判断规则：
    - 多头排列（短期均线都在长期均线上方） → 强上升趋势
    - 空头排列（短期均线都在长期均线下方） → 强下降趋势
    - 均线缠绕 → 震荡市
    """
    # 计算各周期均线
    mas = {}
    for p in periods:
        mas[f'ma_{p}'] = df['price'].rolling(p).mean()
    
    # 判断多头排列（严格排列：MA5 > MA10 > MA20 > MA60 > MA120）
    ma_values = pd.DataFrame(mas)
    df['bullish_alignment'] = True
    for i in range(len(periods) - 1):
        col_short = f'ma_{periods[i]}'
        col_long = f'ma_{periods[i+1]}'
        df['bullish_alignment'] &= (ma_values[col_short] > ma_values[col_long])
    
    df['bearish_alignment'] = True
    for i in range(len(periods) - 1):
        col_short = f'ma_{periods[i]}'
        col_long = f'ma_{periods[i+1]}'
        df['bearish_alignment'] &= (ma_values[col_short] < ma_values[col_long])
    
    # 均线间的离散度（离散度小 = 震荡市）
    ma_std = ma_values.std(axis=1)
    df['ma_dispersion'] = ma_std / ma_values.mean(axis=1)
    
    return df
```

> **经验分享**：均线参数的选择没有"最优"答案，取决于交易周期和市场特性。日线交易常用5/10/20/60日均线组合，周线交易常用4/13/26/52周均线组合。关键是选定参数后保持一致性，不要频繁切换参数去"拟合"历史行情。
