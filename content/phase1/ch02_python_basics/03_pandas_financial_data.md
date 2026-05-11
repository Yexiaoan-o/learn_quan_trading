## 3.1 OHLCV 数据结构

OHLCV 是金融数据中最核心的数据结构，五个字母分别代表：

| 缩写 | 全称 | 中文名 | 说明 |
|------|------|--------|------|
| **O** | Open | 开盘价 | 交易日（或周期）第一笔成交价 |
| **H** | High | 最高价 | 周期内成交的最高价 |
| **L** | Low | 最低价 | 周期内成交的最低价 |
| **C** | Close | 收盘价 | 周期内最后一笔成交价 |
| **V** | Volume | 成交量 | 周期内成交的总数量（股/手） |

### 为什么量化交易如此依赖 OHLCV？

```
┌─────────────────────────────────────────────────┐
│    一根K线包含的信息远超过价格本身                  │
├─────────────────────────────────────────────────┤
│ High —— 日内多头力量的最大推动力                    │
│ Low  —— 日内空头力量的最大压制力                   │
│ Open —— 开盘情绪的直接反映                         │
│ Close—— 经过一天博弈后的"共识价格"                 │
│ Volume—— 市场参与度和趋势可信度的"投票机"           │
└─────────────────────────────────────────────────┘
```

OHLCV 的组合形态可以生成大量技术指标和策略信号，是技术分析和量化交易的基础。

## 3.2 获取 A 股数据

下面的示例展示如何通过 Tushare 获取数据，并使用 Pandas 进行初步处理：

```python
import pandas as pd
import numpy as np
import tushare as ts

# 设置Tushare token（替换为你的token）
ts.set_token('your_token_here')
pro = ts.pro_api()

# === 获取单个股票的日K线数据 ===
df = pro.daily(ts_code='000001.SZ', start_date='20200101', end_date='20231231')
print(df.info())
print(df.head())

# 典型的DataFrame结构：
#   ts_code    trade_date  open  high   low  close  pre_close  change  pct_chg  vol  amount
# 0 000001.SZ  20231229  9.39  9.45  9.35   9.41       9.41     0.0      0.0  ...    ...
```

### 使用 AKShare 获取数据（完全免费方案）

```python
import akshare as ak

# 获取平安银行日K线数据
stock_zh_a_hist_df = ak.stock_zh_a_hist(
    symbol="000001", 
    period="daily", 
    start_date="20200101", 
    end_date="20231231", 
    adjust="qfq"  # 前复权
)
print(stock_zh_a_hist_df.head())
```

## 3.3 日期时间处理

金融数据的索引必须是正确的日期时间格式，这是所有时间序列操作的基础。

```python
import pandas as pd

# === 字符串转为日期时间 ===
df['trade_date'] = pd.to_datetime(df['trade_date'])
df.set_index('trade_date', inplace=True)

# === 日期范围生成 ===
# 生成2020~2024年所有交易日
trading_days = pd.date_range('2020-01-01', '2024-12-31', freq='B')  # B=Business Day
print(f'交易日总数: {len(trading_days)}')

# === 交易日历处理 ===
# 中国市场需要考虑节假日、调休等
# AKShare可以提供交易日历
calendar_df = ak.tool_trade_date_hist_sina()
trading_dates = pd.to_datetime(calendar_df['trade_date'])
print(f'A股历史交易日数量: {len(trading_dates)}')

# === 索引必须是DatetimeIndex才能做时间操作 ===
df.index = pd.DatetimeIndex(df.index)

# === 按时间切片 ===
df_2023 = df.loc['2023']                       # 2023年全年
df_h1_2023 = df.loc['2023-01':'2023-06']       # 2023上半年
df_recent = df.loc[df.index >= '2023-06-01']    # 2023年6月及之后
```

## 3.4 数据清洗与预处理

原始行情数据往往存在各种问题，需要清洗后才能用于策略研发。

```python
import pandas as pd
import numpy as np

# 模拟一份带问题的行情数据
data = {
    'open':  [100, np.nan, 102, 0,  104, 105],
    'high':  [102, 103, 104, 0, 106, 107],
    'low':   [99,  100, 101, 0, 500, 103],  # 500 是异常值
    'close': [101, 102, 103, 104, 105, np.nan],
    'volume': [1000000, 1200000, None, 800000, 1500000, 2000000]
}
df = pd.DataFrame(data, 
    index=pd.date_range('2024-01-02', periods=6, freq='B'))

print("原始数据:")
print(df)

# ===== 数据清洗步骤 =====

# 1. 检查缺失值
print(f'\n缺失值统计:\n{df.isnull().sum()}')

# 2. 检查异常值（零值或负值）
price_cols = ['open', 'high', 'low', 'close']
for col in price_cols:
    n_zero = (df[col] <= 0).sum()
    if n_zero > 0:
        print(f'{col}中有{n_zero}个非正值（可能为异常）')

# 3. 处理价格异常值
# 方法1：中位数填充
median_val = df['low'].median()
df.loc[df['low'] > df['high'] * 1.2, 'low'] = np.nan  # 价格远超high视为异常

# 方法2：3-sigma准则
mean_close = df['close'].mean()
std_close = df['close'].std()
normal_close = (df['close'] > mean_close - 3*std_close) & \
               (df['close'] < mean_close + 3*std_close)

# 4. 处理缺失值
# 价格数据：前向填充
df[price_cols] = df[price_cols].fillna(method='ffill')
# 成交量数据：用0填充缺失
df['volume'] = df['volume'].fillna(0)

# 5. 最终检查
print(f'\n清洗后的数据:\n{df}')
print(f'\n清洗后缺失值统计:\n{df.isnull().sum()}')

# 6. 数据质量报告
data_quality = {
    '总行数': len(df),
    '完整行数': df.dropna().shape[0],
    '缺失值总数': df.isnull().sum().sum(),
    '价格为零的行': (df['close'] <= 0).sum(),
    '数据完整度': f'{df.dropna().shape[0]/len(df):.1%}'
}
print(f'\n数据质量报告:\n{pd.Series(data_quality)}')
```

> **数据清洗铁律**：在量化交易中，数据清洗可能占据 60% 甚至更多的时间。永远不要假设数据是干净的——缺失值、异常值、停牌、除权除息、拆分合并等都会在数据上留下痕迹。一份精心清洗的数据，胜过十个精巧的模型。

## 3.5 常用技术指标计算

Pandas 的向量化操作让技术指标计算变得非常简单。

```python
import pandas as pd
import numpy as np

def calculate_indicators(df):
    """
    计算常用技术指标
    输入的df需要包含 'open', 'high', 'low', 'close', 'volume' 列
    """
    df = df.copy()
    
    # === 移动平均线 ===
    df['MA5'] = df['close'].rolling(window=5).mean()
    df['MA10'] = df['close'].rolling(window=10).mean()
    df['MA20'] = df['close'].rolling(window=20).mean()
    df['MA60'] = df['close'].rolling(window=60).mean()
    
    # === 指数移动平均线 ===
    df['EMA12'] = df['close'].ewm(span=12, adjust=False).mean()
    df['EMA26'] = df['close'].ewm(span=26, adjust=False).mean()
    
    # === MACD ===
    df['DIFF'] = df['EMA12'] - df['EMA26']
    df['DEA'] = df['DIFF'].ewm(span=9, adjust=False).mean()
    df['MACD'] = 2 * (df['DIFF'] - df['DEA'])
    
    # === RSI（相对强弱指标） ===
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    df['RSI'] = 100 - (100 / (1 + rs))
    
    # === 布林带 ===
    df['BOLL_MID'] = df['close'].rolling(window=20).mean()
    df['BOLL_STD'] = df['close'].rolling(window=20).std()
    df['BOLL_UP'] = df['BOLL_MID'] + 2 * df['BOLL_STD']
    df['BOLL_DN'] = df['BOLL_MID'] - 2 * df['BOLL_STD']
    
    # === ATR（平均真实波幅） ===
    high_low = df['high'] - df['low']
    high_close = np.abs(df['high'] - df['close'].shift())
    low_close = np.abs(df['low'] - df['close'].shift())
    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    df['ATR'] = tr.rolling(window=14).mean()
    
    # === 成交量指标 ===
    df['VOL_MA5'] = df['volume'].rolling(window=5).mean()
    df['VOL_MA20'] = df['volume'].rolling(window=20).mean()
    df['VOL_RATIO'] = df['volume'] / df['VOL_MA20']
    
    # === 日收益率 ===
    df['returns'] = df['close'].pct_change()
    df['log_returns'] = np.log(df['close'] / df['close'].shift(1))
    
    return df
```

### 筛选信号的 Pandas 语法

```python
# 基于技术指标筛选买入信号
def generate_signals(df):
    """生成基础的交易信号"""
    df = calculate_indicators(df)
    
    # === 均线金叉信号 ===
    df['ma_cross'] = 0
    # MA5从下向上穿过MA20（需要昨天MA5<MA20，今天MA5>MA20）
    golden_cross = (df['MA5'] > df['MA20']) & (df['MA5'].shift(1) <= df['MA20'].shift(1))
    df.loc[golden_cross, 'ma_cross'] = 1
    
    # === 布林带突破信号 ===
    df['bb_signal'] = 0
    df.loc[df['close'] > df['BOLL_UP'], 'bb_signal'] = -1  # 突破上轨：超买
    df.loc[df['close'] < df['BOLL_DN'], 'bb_signal'] = 1   # 跌破下轨：超卖
    
    # === RSI 极端信号 ===
    df['rsi_signal'] = 0
    df.loc[df['RSI'] < 30, 'rsi_signal'] = 1   # 超卖：看多
    df.loc[df['RSI'] > 70, 'rsi_signal'] = -1   # 超买：看空
    
    # === 放量信号 ===
    df['vol_signal'] = 0
    df.loc[df['VOL_RATIO'] > 2, 'vol_signal'] = 1  # 成交量放大超2倍
    
    # === 综合信号 ===
    # 多个信号共振时认为可靠性更高
    df['composite'] = df['ma_cross'] + df['rsi_signal'] + df['vol_signal']
    df['strong_buy'] = (df['composite'] >= 3).astype(int)
    
    return df
```

## 3.6 多股票数据处理

真实量化交易需要同时处理多只股票的数据，这是 Pandas 真正的强项。

```python
import pandas as pd
import numpy as np

# === 创建多股票DataFrame ===
# 模拟5只股票，每只500天的收盘价
np.random.seed(42)
n_stocks, n_days = 100, 500
dates = pd.date_range('2022-01-01', periods=n_days, freq='B')

# 生成股票代码
stock_codes = [f'{i:06d}.SZ' for i in range(1, n_stocks + 1)]

# 生成价格数据（带相关性）
# 假设有一个共同的市场因子
market_factor = np.random.randn(n_days) * 0.01  # 市场日回报因子
prices = pd.DataFrame(index=dates)

for code in stock_codes:
    idiosyncratic = np.random.randn(n_days) * 0.015  # 个股特有因子
    daily_returns = 0.7 * market_factor + 0.3 * idiosyncratic + 0.0005
    prices[code] = 100 * np.cumprod(1 + daily_returns)

print(prices.head())
print(f'DataFrame形状: {prices.shape}')

# === 按列操作 ===
# 计算每只股票的收益率
returns_all = prices.pct_change().dropna()

# 找出收益率最高的10只股票
top_stocks = returns_all.iloc[-1].nlargest(10)
print(f'最近一天涨幅最大的10只股票:\n{top_stocks}')

# === 计算市场等权指数 ===
market_index = prices.mean(axis=1)  # 等权平均作为市场指数
market_return = market_index.pct_change()

# === 计算每只股票的Beta ===
def calculate_beta(stock_returns, market_returns):
    """计算股票相对于市场的Beta系数"""
    covariance = np.cov(stock_returns, market_returns)[0, 1]
    market_variance = np.var(market_returns)
    return covariance / market_variance

betas = returns_all.apply(lambda col: calculate_beta(col.dropna(), 
                         market_return[col.dropna().index]))
print(f'\n最高Beta的5只股票:\n{betas.nlargest(5)}')
print(f'\n最低Beta的5只股票:\n{betas.nsmallest(5)}')
```

> **Pandas 处理多股票数据的性能边界**：当股票数量超过 1000 只、历史数据超过 10000 天时，单机的 Pandas 处理开始变得吃力。这就是为什么 DolphinDB 在量化交易中如此重要——它专为此类大规模金融时序数据而设计，可以利用分布式架构和列存引擎处理 PB 级别的数据。

## 3.7 数据透视与管理

```python
# === 多层索引（MultiIndex）处理多股票 ===
# 更优雅的多股票数据结构
stock_data = {
    '000001.SZ': {'date': dates, 'close': prices['000001.SZ'].values},
    '000002.SZ': {'date': dates, 'close': prices['000002.SZ'].values},
}

# 创建长格式（Long Format）的多股票数据
dfs = []
for code in ['000001.SZ', '000002.SZ', '000003.SZ', '000004.SZ', '000005.SZ']:
    temp = pd.DataFrame({
        'date': dates,
        'stock_code': code,
        'close': prices[code].values
    })
    dfs.append(temp)

long_df = pd.concat(dfs, ignore_index=True)
print(f'长格式数据形状: {long_df.shape}')
print(long_df.head(10))

# === 透视：长格式 → 宽格式 ===
wide_df = long_df.pivot(index='date', columns='stock_code', values='close')
print(f'宽格式数据形状: {wide_df.shape}')
print(wide_df.head())

# === GroupBy 操作 ===
# 按股票代码分组计算统计量
stock_stats = long_df.groupby('stock_code')['close'].agg([
    'mean', 'std', 'min', 'max',
    ('total_return', lambda x: x.iloc[-1] / x.iloc[0] - 1)
])
print(f'\n各股票统计:\n{stock_stats}')
```

> **长格式 vs 宽格式**：在 DolphinDB 中，数据天然采用长格式（每行一条记录），这更符合数据库的设计理念。理解 Pandas 中两种格式的转换，能帮助你更快适应 DolphinDB 的数据操作方式。
