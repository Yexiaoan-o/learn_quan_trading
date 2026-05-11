## 策略开发

### 3.1 双均线趋势信号

双均线交叉是最经典的趋势跟踪策略。其核心理念是：**当短期趋势上穿长期趋势时做多，下穿时平仓或做空**。在本案例中，我们使用MA20（快线）和MA60（慢线）。

#### 3.1.1 Python实现

```python
def generate_signals(df):
    """
    生成双均线趋势信号
    参数:
        df: DataFrame, 需包含 'close' 列
    返回:
        df: 添加了信号和仓位列的DataFrame
    """
    df = df.copy()

    # 1. 计算均线
    df['ma20'] = df['close'].rolling(20).mean()
    df['ma60'] = df['close'].rolling(60).mean()

    # 2. 生成原始信号: 1=做多, 0=空仓
    df['signal'] = 0
    df.loc[df['ma20'] > df['ma60'], 'signal'] = 1
    df.loc[df['ma20'] <= df['ma60'], 'signal'] = 0

    # 3. 生成交叉信号（1=金叉，-1=死叉）
    df['crossover'] = df['signal'].diff()
    df['golden_cross'] = (df['crossover'] == 1).astype(int)   # 金叉
    df['death_cross'] = (df['crossover'] == -1).astype(int)    # 死叉

    # 4. 持仓信号（信号滞后一期，避免使用未来数据）
    df['position'] = df['signal'].shift(1).fillna(0)

    return df

# 应用信号生成
df_signals = generate_signals(df_clean)

# 查看信号统计
print(f"金叉次数: {df_signals['golden_cross'].sum()}")
print(f"死叉次数: {df_signals['death_cross'].sum()}")
print(f"持仓占比: {df_signals['position'].mean():.2%}")

# 查看最近几次交叉信号
cross_dates = df_signals[df_signals['crossover'] != 0][['ma20', 'ma60', 'signal', 'crossover']]
print("\n最近10次交叉信号:")
print(cross_dates.tail(10))
```

#### 3.1.2 DolphinDB等价实现

在DolphinDB中，实现同样的信号逻辑：

```
// DolphinDB端：双均线信号生成
def generateSignals(close) {
    // 计算均线
    ma20 = avg(close, 20)
    ma60 = avg(close, 60)

    // 信号生成
    signal = iif(ma20 > ma60, 1, 0)

    // 交叉检测
    prev_signal = signal.prev()  // 前一期信号
    golden_cross = iif(signal == 1 and prev_signal == 0, 1, 0)
    death_cross = iif(signal == 0 and prev_signal == 1, 1, 0)

    // 持仓信号（滞后一期）
    position = signal.prev()
    position[0] = 0  // 第一天无持仓

    return dict(STRING, ANY, [
        ["ma20", ma20],
        ["ma60", ma60],
        ["signal", signal],
        ["goldenCross", golden_cross],
        ["deathCross", death_cross],
        ["position", position]
    ])
}

// 使用
data = loadTable("dfs://stock_daily", "daily_bar")
close = exec Close from data where Symbol == "600519" order by TradeDate
signals = generateSignals(close)
```

### 3.2 ATR仓位管理

策略不仅需要知道"何时交易"，还需要知道"交易多少"。ATR（平均真实波幅）仓位管理根据市场当前波动水平动态调整仓位大小。

#### 3.2.1 仓位计算原理

$$\text{Shares} = \frac{\text{Capital} \times \text{RiskPct}}{\text{ATR} \times \text{Multiplier}}$$

其中：
- **Capital**：当前可用资金
- **RiskPct**：单笔交易愿意承担的风险比例（如2%）
- **ATR**：14日平均真实波幅
- **Multiplier**：ATR倍数（如2倍）

```python
def calculate_atr_position(df, capital, risk_pct=0.02, atr_period=14, atr_multiplier=2):
    """
    根据ATR计算动态仓位大小
    风险控制思想：无论市场波动多大，单笔交易亏损上限为总资金的risk_pct
    """
    df = df.copy()

    # 计算真实波幅（True Range）
    df['prev_close'] = df['close'].shift(1)
    df['tr1'] = df['high'] - df['low']
    df['tr2'] = abs(df['high'] - df['prev_close'])
    df['tr3'] = abs(df['low'] - df['prev_close'])
    df['tr'] = df[['tr1', 'tr2', 'tr3']].max(axis=1)

    # 计算ATR
    df['atr'] = df['tr'].rolling(atr_period).mean()

    # 计算止损距离
    df['stop_distance'] = df['atr'] * atr_multiplier

    # 计算仓位（股数）
    # 每笔交易的最大亏损 = 总资金 × 风险比例
    max_loss_per_trade = capital * risk_pct
    # 仓位 = 最大亏损 / 止损距离
    df['position_size'] = np.floor(max_loss_per_trade / df['stop_distance'] / 100) * 100

    # 清理临时列
    df.drop(['prev_close', 'tr1', 'tr2', 'tr3', 'tr'], axis=1, inplace=True)

    return df

# 计算ATR仓位
df_position = calculate_atr_position(df_signals, capital=100000)
print(f"ATR范围: {df_position['atr'].min():.2f} - {df_position['atr'].max():.2f}")
print(f"仓位范围: {df_position['position_size'].min():.0f} - {df_position['position_size'].max():.0f}")
```

### 3.3 移动止损

移动止损（Trailing Stop）用于在持仓期间保护利润。当价格从最高点回撤超过一定比例时自动平仓。

```python
def apply_trailing_stop(df, stop_pct=0.05):
    """
    应用移动止损
    在持仓期间，如果价格跌破止损线，则强制平仓
    """
    df = df.copy()
    df['stop_level'] = np.nan
    df['stopped_out'] = 0

    in_position = False
    entry_price = 0
    high_water = 0

    for i in range(len(df)):
        if not in_position:
            # 开仓：信号=1
            if df.loc[df.index[i], 'position'] == 1:
                in_position = True
                entry_price = df.loc[df.index[i], 'close']
                high_water = entry_price
                df.loc[df.index[i], 'stop_level'] = high_water * (1 - stop_pct)
        else:
            # 持续持仓中
            current_close = df.loc[df.index[i], 'close']
            high_water = max(high_water, current_close)
            current_stop = high_water * (1 - stop_pct)
            df.loc[df.index[i], 'stop_level'] = current_stop

            # 检查是否触发止损
            if current_close <= current_stop:
                df.loc[df.index[i], 'position'] = 0  # 止损平仓
                df.loc[df.index[i], 'stopped_out'] = 1
                in_position = False
                df.loc[df.index[i], 'stop_level'] = np.nan

            # 检查信号卖出（死叉平仓）
            if df.loc[df.index[i], 'crossover'] == -1:
                df.loc[df.index[i], 'position'] = 0
                in_position = False
                df.loc[df.index[i], 'stop_level'] = np.nan

    return df

df_stop = apply_trailing_stop(df_position, stop_pct=0.05)
stop_events = df_stop[df_stop['stopped_out'] == 1]
print(f"止损触发次数: {len(stop_events)}")
if len(stop_events) > 0:
    print(f"止损触发日期: {stop_events.index.tolist()}")
```

### 3.4 信号可视化

在正式回测前，用图表验证信号生成是否正确：

```python
import matplotlib.pyplot as plt

def plot_signals(df, start_date=None, end_date=None):
    """可视化均线、信号和止损线"""
    if start_date and end_date:
        plot_df = df.loc[start_date:end_date]
    else:
        plot_df = df.tail(250)  # 默认展示最近一年

    fig, axes = plt.subplots(2, 1, figsize=(14, 10), sharex=True)

    # 上图：价格和均线
    ax1 = axes[0]
    ax1.plot(plot_df.index, plot_df['close'], label='收盘价', color='black', alpha=0.8)
    ax1.plot(plot_df.index, plot_df['ma20'], label='MA20', color='blue', alpha=0.6)
    ax1.plot(plot_df.index, plot_df['ma60'], label='MA60', color='red', alpha=0.6)

    # 标注金叉和死叉
    buy_signals = plot_df[plot_df['golden_cross'] == 1]
    sell_signals = plot_df[plot_df['death_cross'] == 1]
    ax1.scatter(buy_signals.index, plot_df.loc[buy_signals.index, 'close'],
                marker='^', color='green', s=100, label='金叉(买入)')
    ax1.scatter(sell_signals.index, plot_df.loc[sell_signals.index, 'close'],
                marker='v', color='red', s=100, label='死叉(卖出)')

    ax1.set_title('双均线趋势信号 (MA20 vs MA60)')
    ax1.set_ylabel('价格')
    ax1.legend(loc='upper left')
    ax1.grid(True, alpha=0.3)

    # 下图：止损线和持仓状态
    ax2 = axes[1]
    ax2.fill_between(plot_df.index, 0, plot_df['position'],
                     alpha=0.3, color='green', label='持仓状态')
    if 'stop_level' in plot_df.columns:
        ax2.plot(plot_df.index, plot_df['stop_level'],
                 color='orange', linestyle='--', alpha=0.7, label='止损线')
    ax2.set_ylabel('仓位')
    ax2.set_title('持仓状态与止损线')
    ax2.legend(loc='upper left')
    ax2.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.show()

# 展示最近一年信号
plot_signals(df_stop)
```

### 3.5 策略开发小结

| 步骤 | 实现内容 | 关键参数 |
|------|----------|----------|
| 信号生成 | 双均线金叉/死叉 | MA20, MA60 |
| 仓位管理 | ATR动态仓位 | ATR(14), 风险2% |
| 止损控制 | 移动止损 | 回撤5% |
| 平仓规则 | 死叉或止损触发 | — |

> **策略完整性检查**：一个好的交易策略必须回答三个问题：1) 什么时候开仓？2) 买多少？3) 什么时候平仓（止盈和止损）？如果这三个问题都有明确的答案，策略就具备了可执行的基础。
