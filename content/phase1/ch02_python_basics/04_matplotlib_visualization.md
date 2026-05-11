## 4.1 为什么可视化在量化交易中如此重要？

在量化交易中，可视化不仅仅是"把图画出来"，更是质量控制和直觉验证的工具：

| 可视化目的 | 具体场景 |
|-----------|----------|
| **数据验证** | 检查下载的价格数据是否有异常跳空 |
| **策略直观理解** | 观察均线交叉、信号触发时机 |
| **回测绩效评估** | 净值和回撤曲线揭示策略本质 |
| **风险排查** | 识别策略在特定市场环境下的弱点 |
| **沟通表达** | 向他人展示策略逻辑和结果 |

> **"一图胜千言"**：在面对成百上千行数据和策略逻辑时，一张设计良好的图表能让你在几秒钟内发现问题——价格数据是否错误、策略是否在特定的历史区间失效、是否存在未来函数——这些信息的获取速度远超阅读表格数据。

## 4.2 Matplotlib 基础绘图

Matplotlib 是 Python 最基础的可视化库，几乎所有其他可视化库都是基于它的接口封装的。

### 第一个行情图

```python
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np

# 设置中文字体（解决中文显示问题）
plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False  # 解决负号显示问题

# 生成模拟数据
dates = pd.date_range('2023-01-01', '2023-12-31', freq='B')
np.random.seed(42)
prices = 100 + np.cumsum(np.random.randn(len(dates)) * 1.5)

# === 基础线条图 ===
fig, ax = plt.subplots(figsize=(12, 5))
ax.plot(dates, prices, linewidth=1, color='#1f77b4', label='收盘价')
ax.set_title('2023年模拟股价走势', fontsize=14, fontweight='bold')
ax.set_xlabel('日期')
ax.set_ylabel('价格')
ax.legend()
ax.grid(True, alpha=0.3)
plt.tight_layout()
plt.show()

# === 价格区间图 ===
# 模拟OHLC数据
df = pd.DataFrame({
    'open': prices + np.random.randn(len(dates)) * 0.5,
    'high': prices + np.abs(np.random.randn(len(dates)) * 2),
    'low': prices - np.abs(np.random.randn(len(dates)) * 2),
    'close': prices + np.random.randn(len(dates)) * 0.3,
}, index=dates)

fig, ax = plt.subplots(figsize=(12, 5))

# 绘制最高-最低价区间线
for i in range(len(df)):
    ax.plot([dates[i], dates[i]], [df['low'].iloc[i], df['high'].iloc[i]], 
            color='gray', linewidth=0.5, alpha=0.5)

# 绘制收盘价
ax.scatter(dates[df['close'] >= df['open']], 
           df.loc[df['close'] >= df['open'], 'close'],
           color='red', s=10, label='收阳')
ax.scatter(dates[df['close'] < df['open']], 
           df.loc[df['close'] < df['open'], 'close'],
           color='green', s=10, label='收阴')

ax.set_title('OHLC价格散点图', fontsize=14, fontweight='bold')
ax.legend()
plt.tight_layout()
plt.show()
```

## 4.3 K 线图（Candlestick Chart）

K 线图是金融交易中最经典、最广泛使用的图表类型，一根 K 线同时包含了开盘、收盘、最高、最低四个价格信息。

### 使用 mplfinance 绘制 K 线图

```python
# 安装: pip install mplfinance
import mplfinance as mpf
import pandas as pd
import numpy as np

# 准备OHLC数据（DataFrame必须有'Open','High','Low','Close','Volume'列）
dates = pd.date_range('2023-01-01', periods=100, freq='B')
np.random.seed(42)
price = 100
data = []
for i in range(100):
    daily_return = np.random.randn() * 0.02
    open_price = price
    close_price = price * (1 + daily_return)
    high_price = max(open_price, close_price) * (1 + np.random.rand() * 0.01)
    low_price = min(open_price, close_price) * (1 - np.random.rand() * 0.01)
    volume = np.random.randint(100000, 1000000)
    data.append([open_price, high_price, low_price, close_price, volume])
    price = close_price

df = pd.DataFrame(data, index=dates, 
                   columns=['Open', 'High', 'Low', 'Close', 'Volume'])

# === 绘制标准K线图 ===
mpf.plot(df, type='candle', style='charles',
         title='模拟股票K线图',
         ylabel='价格 (元)',
         volume=True,  # 显示成交量
         figsize=(12, 8),
         mav=(5, 20),  # 显示5日和20日均线
         savefig='candlestick_demo.png')

# === 自定义颜色和样式 ===
mc = mpf.make_marketcolors(
    up='red',          # 阳线颜色
    down='green',       # 阴线颜色
    edge='inherit',
    wick='inherit',
    volume='inherit'
)
s = mpf.make_mpf_style(marketcolors=mc, gridstyle='--', y_on_right=False)

mpf.plot(df, type='candle', style=s,
         title='A股风格K线图（红涨绿跌）',
         ylabel='价格 (元)',
         volume=True,
         figsize=(12, 8))
```

> **K线颜色约定差异**：A股市场习惯"红涨绿跌"，而美股市场习惯"绿涨红跌"。中美市场上相反的颜色惯例可能导致跨市场交易者混淆。本课程遵循 A 股习惯。

### 使用 plotly 绘制交互式 K 线图

```python
# 安装: pip install plotly
import plotly.graph_objects as go

fig = go.Figure(data=[go.Candlestick(
    x=df.index,
    open=df['Open'],
    high=df['High'],
    low=df['Low'],
    close=df['Close'],
    increasing_line_color='red',
    decreasing_line_color='green',
    name='K线'
)])

# 添加移动平均线
fig.add_trace(go.Scatter(
    x=df.index,
    y=df['Close'].rolling(20).mean(),
    mode='lines',
    line=dict(color='orange', width=1),
    name='MA20'
))

fig.update_layout(
    title='交互式K线图',
    xaxis_title='日期',
    yaxis_title='价格',
    xaxis_rangeslider_visible=False,
    height=600,
    template='plotly_white'
)
fig.show()
```

## 4.4 策略绩效可视化

### 净值曲线和回撤

```python
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

# 模拟策略日收益率
np.random.seed(42)
n_days = 252
strategy_returns = np.random.randn(n_days) * 0.012 + 0.001  # 年化约30%
benchmark_returns = np.random.randn(n_days) * 0.01 + 0.0005 # 年化约15%

# 计算累计净值
strategy_nav = np.cumprod(1 + strategy_returns)
benchmark_nav = np.cumprod(1 + benchmark_returns)

# 计算回撤
running_max = np.maximum.accumulate(strategy_nav)
drawdown = (strategy_nav - running_max) / running_max

# === 绘制净值和回撤双面板 ===
fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8), 
                                gridspec_kw={'height_ratios': [2, 1]},
                                sharex=True)

# 上板：净值曲线
ax1.plot(strategy_nav, color='#d62728', linewidth=1.5, label='策略净值')
ax1.plot(benchmark_nav, color='#1f77b4', linewidth=1.0, 
         label='基准净值', linestyle='--')
ax1.fill_between(range(n_days), 1, strategy_nav, 
                 where=(strategy_nav >= 1), alpha=0.15, color='red')
ax1.fill_between(range(n_days), strategy_nav, 1, 
                 where=(strategy_nav < 1), alpha=0.15, color='green')
ax1.axhline(y=1, color='gray', linestyle='-', linewidth=0.5)
ax1.set_ylabel('净值', fontsize=12)
ax1.set_title('策略净值曲线', fontsize=14, fontweight='bold')
ax1.legend(loc='upper left')
ax1.grid(True, alpha=0.3)

# 下板：回撤曲线
ax2.fill_between(range(n_days), drawdown, 0, 
                 color='red', alpha=0.3)
ax2.plot(drawdown, color='red', linewidth=0.5)
ax2.set_ylabel('回撤', fontsize=12)
ax2.set_xlabel('交易日', fontsize=12)
ax2.grid(True, alpha=0.3)
ax2.yaxis.set_major_formatter(plt.FuncFormatter(lambda y, _: f'{y:.0%}'))

max_dd = drawdown.min()
ax2.axhline(y=max_dd, color='darkred', linestyle='--', linewidth=0.5)
ax2.text(n_days / 2, max_dd + 0.02, f'最大回撤: {max_dd:.1%}', 
         color='darkred', ha='center')

plt.tight_layout()
plt.show()
```

### 收益分布直方图

```python
# === 收益分布与风险指标 ===
fig, axes = plt.subplots(2, 2, figsize=(12, 8))

# 1. 日收益直方图
ax = axes[0, 0]
ax.hist(strategy_returns, bins=50, density=True, alpha=0.7, 
        color='steelblue', edgecolor='white')
ax.axvline(x=np.mean(strategy_returns), color='red', 
           linestyle='--', label=f'均值: {np.mean(strategy_returns):.4f}')
ax.axvline(x=0, color='gray', linestyle='-', linewidth=0.5)
ax.set_title('日收益率分布')
ax.set_xlabel('日收益率')
ax.set_ylabel('频率密度')
ax.legend()

# 2. 月度收益热力图
monthly_returns = pd.Series(strategy_returns).resample('ME').apply(
    lambda x: (1 + x).prod() - 1
)
months = [f'{m}' for m in range(1, 13)]
# 简化为直接展示柱状图
ax = axes[0, 1]
colors = ['red' if r > 0 else 'green' for r in monthly_returns.values]
ax.bar(range(len(monthly_returns)), monthly_returns.values, color=colors)
ax.axhline(y=0, color='gray', linewidth=0.5)
ax.set_title('月度收益率')
ax.set_xlabel('月份')
ax.set_ylabel('月度收益率')

# 3. 绩效指标表格
ax = axes[1, 0]
ax.axis('off')

metrics = [
    ['指标', '策略', '基准'],
    ['年化收益', f'{np.mean(strategy_returns)*252:.2%}', f'{np.mean(benchmark_returns)*252:.2%}'],
    ['年化波动', f'{np.std(strategy_returns)*np.sqrt(252):.2%}', f'{np.std(benchmark_returns)*np.sqrt(252):.2%}'],
    ['夏普比率', f'{np.mean(strategy_returns)/np.std(strategy_returns)*np.sqrt(252):.2f}', 
                f'{np.mean(benchmark_returns)/np.std(benchmark_returns)*np.sqrt(252):.2f}'],
    ['最大回撤', f'{max_dd:.2%}', 'N/A'],
    ['胜率', f'{np.mean(strategy_returns > 0):.2%}', f'{np.mean(benchmark_returns > 0):.2%}'],
]

table = ax.table(cellText=metrics, loc='center', cellLoc='center')
table.auto_set_font_size(False)
table.set_fontsize(10)
table.scale(1.2, 1.5)
ax.set_title('核心绩效指标对比', pad=20)

# 4. 滚动夏普比率
ax = axes[1, 1]
window = 60
rolling_sharpe = pd.Series(strategy_returns).rolling(window).apply(
    lambda x: np.mean(x) / np.std(x) * np.sqrt(252)
)
ax.plot(rolling_sharpe, color='purple', linewidth=1)
ax.axhline(y=1, color='green', linestyle='--', label='优秀(>1)')
ax.axhline(y=0, color='red', linestyle='--', label='零界')
ax.set_title(f'{window}日滚动夏普比率')
ax.set_xlabel('交易日')
ax.set_ylabel('夏普比率')
ax.legend()
ax.grid(True, alpha=0.3)

plt.tight_layout()
plt.show()
```

## 4.5 技术指标可视化

```python
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

# 模拟OHLC数据
dates = pd.date_range('2023-01-01', periods=200, freq='B')
np.random.seed(42)
price = 100
close_prices = []
for i in range(200):
    price *= (1 + np.random.randn() * 0.015)
    close_prices.append(price)
close = pd.Series(close_prices, index=dates)

# 计算指标
ma20 = close.rolling(20).mean()
ma60 = close.rolling(60).mean()
boll_mid = close.rolling(20).mean()
boll_std = close.rolling(20).std()
boll_up = boll_mid + 2 * boll_std
boll_dn = boll_mid - 2 * boll_std

# RSI
delta = close.diff()
gain = delta.where(delta > 0, 0).rolling(14).mean()
loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
rs = gain / loss
rsi = 100 - (100 / (1 + rs))

# === 三面板技术指标图 ===
fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(12, 10),
                                     gridspec_kw={'height_ratios': [3, 1, 1]},
                                     sharex=True)

# 面板1：K线 + 布林带 + 均线
ax1.plot(close.index, close, color='black', linewidth=0.8, label='收盘价')
ax1.plot(ma20.index, ma20, color='blue', linewidth=0.8, label='MA20')
ax1.plot(ma60.index, ma60, color='red', linewidth=0.8, label='MA60')
ax1.fill_between(boll_up.index, boll_dn, boll_up, 
                 alpha=0.1, color='gray', label='布林带')
ax1.plot(boll_up.index, boll_up, '--', color='gray', linewidth=0.5)
ax1.plot(boll_dn.index, boll_dn, '--', color='gray', linewidth=0.5)

# 标记均线交叉点
for i in range(1, len(close)):
    if (ma20.iloc[i-1] <= ma60.iloc[i-1]) and (ma20.iloc[i] > ma60.iloc[i]):
        ax1.scatter(close.index[i], close.iloc[i], 
                   color='red', s=30, marker='^', zorder=5)
    elif (ma20.iloc[i-1] >= ma60.iloc[i-1]) and (ma20.iloc[i] < ma60.iloc[i]):
        ax1.scatter(close.index[i], close.iloc[i], 
                   color='green', s=30, marker='v', zorder=5)

ax1.set_ylabel('价格')
ax1.set_title('技术指标综合图', fontsize=14, fontweight='bold')
ax1.legend(loc='upper left', ncol=2)
ax1.grid(True, alpha=0.3)

# 面板2：MACD
ema12 = close.ewm(span=12).mean()
ema26 = close.ewm(span=26).mean()
macd_line = ema12 - ema26
signal_line = macd_line.ewm(span=9).mean()
macd_hist = 2 * (macd_line - signal_line)

ax2.bar(macd_hist.index, macd_hist.values, 
        width=0.8, 
        color=['red' if v > 0 else 'green' for v in macd_hist.values],
        alpha=0.5)
ax2.plot(macd_line.index, macd_line.values, color='blue', linewidth=0.8, label='MACD')
ax2.plot(signal_line.index, signal_line.values, color='red', linewidth=0.8, label='Signal')
ax2.axhline(y=0, color='gray', linewidth=0.5)
ax2.set_ylabel('MACD')
ax2.legend(loc='upper left')
ax2.grid(True, alpha=0.3)

# 面板3：RSI
ax3.plot(rsi.index, rsi.values, color='purple', linewidth=0.8)
ax3.axhline(y=70, color='red', linestyle='--', linewidth=0.8, label='超买(70)')
ax3.axhline(y=30, color='green', linestyle='--', linewidth=0.8, label='超卖(30)')
ax3.axhline(y=50, color='gray', linestyle='-', linewidth=0.5)
ax3.fill_between(rsi.index, 30, 70, alpha=0.05, color='gray')
ax3.set_ylabel('RSI')
ax3.set_xlabel('日期')
ax3.legend(loc='upper left')
ax3.set_ylim(0, 100)
ax3.grid(True, alpha=0.3)

plt.tight_layout()
plt.show()
```

## 4.6 参数敏感性可视化

量化策略对参数敏感度的分析至关重要——这能帮助你判断策略的稳健性。

```python
# === 参数热力图 ===
def strategy_returns_with_params(data, short_window, long_window):
    """模拟一个带参数的策略返回年化夏普比率"""
    # 这里用模拟数据演示
    base_sharpe = 1.2
    noise = np.sin(short_window * 0.3) * np.cos(long_window * 0.2) * 0.8
    penalty = abs(short_window - 20) * 0.01 + abs(long_window - 60) * 0.005
    return base_sharpe + noise - penalty

short_windows = np.arange(5, 51, 1)
long_windows = np.arange(30, 121, 2)

sharpe_matrix = np.zeros((len(short_windows), len(long_windows)))
for i, sw in enumerate(short_windows):
    for j, lw in enumerate(long_windows):
        sharpe_matrix[i, j] = strategy_returns_with_params(None, sw, lw)

fig, ax = plt.subplots(figsize=(12, 6))
im = ax.imshow(sharpe_matrix, aspect='auto', origin='lower',
               extent=[long_windows[0], long_windows[-1], 
                       short_windows[0], short_windows[-1]],
               cmap='RdYlGn')
ax.set_xlabel('长期均线窗口')
ax.set_ylabel('短期均线窗口')
ax.set_title('参数敏感性分析：夏普比率热力图', fontsize=14, fontweight='bold')
plt.colorbar(im, label='夏普比率')
plt.tight_layout()
plt.show()
```

> **可视化黄金法则**：好的图表让发现规律变得容易，而不是炫耀绘图技巧。量化交易中的图表应当服务于清晰的信息传达——让读者在 3 秒内理解核心信息。过度装饰和混乱的颜色只会适得其反。
