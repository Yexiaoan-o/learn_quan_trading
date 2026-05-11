## 2.1 Pandas 简介与金融数据的关系

Pandas 是 Python 数据分析的瑞士军刀，也是量化交易者最频繁使用的工具库。它建立在 NumPy 之上，提供了两个核心数据结构——Series 和 DataFrame——专为处理表格化、时间序列数据而设计，这与金融数据的结构高度吻合。

### Pandas 在量化交易中的定位

```
原始数据          Pandas 处理              策略输出
┌─────────┐      ┌──────────────┐      ┌─────────┐
│ CSV文件  │ --->  │ DataFrame    │ --->  │ 策略收益  │
│ 数据库   │ --->  │ 清洗/转换     │ --->  │ 回测报告  │
│ API接口  │ --->  │ 计算/分析     │ --->  │ 可视化图  │
└─────────┘      └──────────────┘      └─────────┘
```

## 2.2 Series：一维带标签数组

Series 是 Pandas 最基础的数据结构，可以理解为一个带有索引的一维数组。

### 创建 Series

```python
import pandas as pd
import numpy as np

# === 从列表创建 ===
prices = pd.Series([10.5, 11.2, 10.8, 11.5, 12.0])
print(prices)
# 0    10.5
# 1    11.2
# 2    10.8
# 3    11.5
# 4    12.0
# dtype: float64

# === 指定自定义索引 ===
dates = pd.date_range('2024-01-01', periods=5, freq='B')
prices = pd.Series([10.5, 11.2, 10.8, 11.5, 12.0], index=dates)
print(prices)
# 2024-01-01    10.5
# 2024-01-02    11.2
# 2024-01-03    10.8
# 2024-01-04    11.5
# 2024-01-05    12.0
# Freq: B, dtype: float64

# === 从字典创建 ===
price_dict = {'AAPL': 178.50, 'MSFT': 405.20, 'GOOGL': 142.30}
stocks = pd.Series(price_dict)
print(stocks)
```

### Series 的关键操作

```python
close = pd.Series([100, 101, 102, 103, 104, 105, 106],
                   index=pd.date_range('2024-01-01', periods=7))

# === 访问数据 ===
print(close[0])              # 按位置: 100
print(close.iloc[2])         # 明确按位置: 102
print(close['2024-01-03'])   # 按标签: 102
print(close.loc['2024-01-03']) # 明确按标签: 102

# === 切片操作 ===
print(close[2:5])            # 位置切片
print(close['2024-01-03':'2024-01-06'])  # 标签切片（包含结束标签）

# === 向量化运算 ===
returns = close.pct_change()  # 计算百分比变化（收益率）
print(returns)

log_ret = np.log(close / close.shift(1))  # 对数收益率

# === 滚动窗口计算 ===
ma5 = close.rolling(window=5).mean()  # 5日移动平均
volatility = close.rolling(window=20).std()  # 20日波动率
print(ma5)
```

## 2.3 DataFrame：二维表格数据

DataFrame 是 Pandas 最核心的结构，可以看作一组共享相同索引的 Series 拼接而成的二维表格。

### 创建 DataFrame

```python
import pandas as pd
import numpy as np

# === 从字典创建 ===
data = {
    'open':  [100.0, 101.0, 102.0, 103.0, 104.0],
    'high':  [102.0, 103.5, 104.0, 105.0, 106.5],
    'low':   [99.0,  100.5, 101.0, 102.0, 103.5],
    'close': [101.0, 102.5, 103.0, 104.5, 105.0],
    'volume':[1000000, 1200000, 900000, 1500000, 1100000]
}
df = pd.DataFrame(data)
print(df)

# === 添加时间索引 ===
df.index = pd.date_range('2024-01-01', periods=5, freq='B')
print(df)

# === 从NumPy数组创建 ===
# 模拟1000只股票的日收益率矩阵
np.random.seed(42)
returns_matrix = np.random.randn(1000, 252) * 0.02  # 1000只股票×252天
stock_codes = [f'stock_{i:04d}' for i in range(1000)]
dates = pd.date_range('2024-01-01', periods=252, freq='B')
df_returns = pd.DataFrame(returns_matrix.T, index=dates, columns=stock_codes)
print(df_returns.head())
```

### DataFrame 数据访问

```python
# === 列访问 ===
print(df['close'])                 # 返回 Series
print(df[['open', 'close']])       # 返回 DataFrame（多列）

# === 行访问 ===
print(df.iloc[0])                  # 按位置第一行
print(df.loc['2024-01-01'])        # 按标签第一行

# === 元素访问 ===
print(df.loc['2024-01-01', 'close'])   # 标签定位: 101.0
print(df.iloc[0, 3])                    # 位置定位: 101.0

# === 条件筛选 ===
high_volume = df[df['volume'] > 1000000]
print(high_volume)

# 多条件筛选
condition = (df['close'] > df['open']) & (df['volume'] > 1000000)
bullish_days = df[condition]
print(bullish_days)
```

## 2.4 DataFrame 的核心操作

### 列的基本运算

```python
df = pd.DataFrame({
    'open':  [100.0, 101.0, 102.0, 103.0, 104.0],
    'high':  [102.0, 103.5, 104.0, 105.0, 106.5],
    'low':   [99.0,  100.5, 101.0, 102.0, 103.5],
    'close': [101.0, 102.5, 103.0, 104.5, 105.0],
    'volume':[1000000, 1200000, 900000, 1500000, 1100000]
})

# === 创建新列 ===
df['returns'] = df['close'].pct_change()  # 日收益率
df['range'] = df['high'] - df['low']      # 日内振幅
df['is_up'] = df['close'] > df['open']    # 是否收阳
df['log_returns'] = np.log(df['close'] / df['close'].shift(1))

# === 删除列 ===
df = df.drop('is_up', axis=1)

# === 计算多列统计量 ===
stat_summary = df[['open', 'high', 'low', 'close']].describe()
print(stat_summary)
#         open   high    low  close
# count   5.00   5.00   5.00   5.00
# mean  102.00 104.20  95.20 103.20
# std     1.58   1.72  19.75   1.64
# ...

# === 分类汇总（groupby） ===
# 按月分组计算平均成交量
df['month'] = df.index.month
monthly_vol = df.groupby('month')['volume'].mean()
```

### 缺失值处理

```python
# 模拟带缺失值的金融数据
df['next_open'] = [101.0, np.nan, 103.0, np.nan, 105.0]

# === 检测缺失值 ===
print(df.isnull().sum())

# === 处理缺失值 ===
df_filled = df.fillna(method='ffill')  # 前向填充（金融数据最常用）
df_filled = df.fillna(method='bfill')  # 后向填充
df_filled = df.fillna(df.mean())       # 均值填充（不推荐金融数据）
df_dropped = df.dropna()               # 删除含缺失值的行

# 金融数据更推荐的插值方法
df['next_open'] = df['next_open'].interpolate(method='linear')
```

> **金融数据缺失值处理原则**：优先使用前向填充（ffill）——因为金融数据具有时序性，前一个有效值通常是最合理的猜测。但对于停牌复牌的情况，前向填充可能导致严重偏差，更好的做法是标记这些日期在后续分析中排除。

## 2.5 时间序列处理

### 日期时间索引操作

```python
# 创建5年日频交易日序列
dates = pd.date_range('2020-01-01', '2024-12-31', freq='B')
n = len(dates)
np.random.seed(42)
df = pd.DataFrame({
    'close': 100 + np.cumsum(np.random.randn(n) * 0.5),
    'volume': np.random.randint(100000, 1000000, n)
}, index=dates)

# === 按日期筛选 ===
# 2023年的所有数据
df_2023 = df['2023']

# 2023年第一季度的数据
df_q1_2023 = df['2023-01':'2023-03']

# 我只关心每月的第一个交易日
first_days = df[df.index.is_month_start]

# === 时间属性提取 ===
df['year'] = df.index.year
df['month'] = df.index.month
df['day'] = df.index.day
df['dayofweek'] = df.index.dayofweek   # 0=周一, 4=周五
df['quarter'] = df.index.quarter
df['week_of_year'] = df.index.isocalendar().week

# === 时区处理 ===
df_tz = df.tz_localize('Asia/Shanghai')  # 本地化为北京时间
df_tz = df_tz.tz_convert('US/Eastern')   # 转换为美东时间
```

### 位移与滞后

```python
df = pd.DataFrame({
    'close': [100, 101, 102, 103, 104, 105, 106]
})

# === shift：数据平移 ===
df['close_lag1'] = df['close'].shift(1)  # 昨天的收盘价
df['close_lag5'] = df['close'].shift(5)  # 5天前的收盘价
df['close_lead1'] = df['close'].shift(-1) # 明天的收盘价（前视！小心使用）

# === 计算收益率（shift的典型应用） ===
df['returns'] = df['close'] / df['close'].shift(1) - 1

# === diff：数据差分 ===
df['diff'] = df['close'].diff()      # 一阶差分 = close - close.shift(1)
df['diff5'] = df['close'].diff(5)    # 5阶差分 = close - close.shift(5)
```

### 重采样（Resampling）

重采样是量化交易中最重要的时间序列操作之一，用于在不同频率之间转换数据。

```python
# 创建5年日频数据
dates = pd.date_range('2020-01-01', '2024-12-31', freq='B')
np.random.seed(42)
df = pd.DataFrame({
    'open': 100 + np.cumsum(np.random.randn(len(dates)) * 0.3),
    'high': 102 + np.cumsum(np.random.randn(len(dates)) * 0.3),
    'low': 98 + np.cumsum(np.random.randn(len(dates)) * 0.3),
    'close': 100 + np.cumsum(np.random.randn(len(dates)) * 0.3),
    'volume': np.random.randint(500000, 2000000, len(dates))
}, index=dates)

# === 降采样（日频 → 周频） ===
weekly = df.resample('W').agg({
    'open': 'first',           # 周开盘价 = 周一开盘价
    'high': 'max',             # 周最高价
    'low': 'min',              # 周最低价
    'close': 'last',           # 周收盘价 = 周五收盘价
    'volume': 'sum'            # 周成交量 = 每日成交量之和
})
print(weekly.head())

# === 降采样（日频 → 月频） ===
monthly = df.resample('ME').agg({
    'open': 'first',
    'high': 'max',
    'low': 'min',
    'close': 'last',
    'volume': 'sum'
})

# === 重采样计算自定义聚合 ===
# 计算每月的收益率
monthly_return = df['close'].resample('ME').apply(
    lambda x: x.iloc[-1] / x.iloc[0] - 1
)

# === 升采样（周频 → 日频） ===
weekly_data = pd.DataFrame({
    'close': [100, 102, 104, 106, 108]
}, index=pd.date_range('2024-01-01', periods=5, freq='W'))
daily_data = weekly_data.resample('D').ffill()  # 前向填充
```

### OHLC 数据重采样表

| 价格列 | 降采样方法 | 说明 |
|--------|-----------|------|
| open | `first` | 周期第一个交易日的开盘价 |
| high | `max` | 周期内的最高价 |
| low | `min` | 周期内的最低价 |
| close | `last` | 周期最后一个交易日的收盘价 |
| volume | `sum` | 周期内成交量总和 |
| adj_factor | `last` | 周期最后的复权因子 |

> **重采样的陷阱**：使用 `resample('M')` 时，收盘价`close`必须用 `last` 而非 `mean`。曾经有人因为月频数据用了 `mean` 产生错误的回测结果，导致策略上线后巨额亏损——这个教训值得牢记。

## 2.6 Pandas 与 DolphinDB 的对比视角

理解 Pandas 的操作模式，将极大帮助你后续学习 DolphinDB：

| 操作 | Pandas | DolphinDB | 说明 |
|------|--------|-----------|------|
| 计算收益率 | `df['close'].pct_change()` | `ratios(close) - 1` | 向量化操作 |
| 移动平均 | `df['close'].rolling(20).mean()` | `mavg(close, 20)` | 滚动窗口 |
| 分组聚合 | `df.groupby('symbol').mean()` | `select avg(x) from t group by sym` | SQL风格 |
| 时间范围筛选 | `df['2023']` | `select * from t where date between 2023.01.01 : 2023.12.31` | 按时间查询 |
| 矩阵运算 | `np.cov(df.values.T)` | `cov(matrix(returns))` | 协方差 |

> Pandas 是为单机数据分析设计的，处理千万行级别数据时会遇到性能瓶颈。DolphinDB 专为亿级以上的金融时序数据而设计，处理速度可以达到 Pandas 的 10-100 倍。Pandas 是数据分析的起点，DolphinDB 是大规模量化交易的利器。
