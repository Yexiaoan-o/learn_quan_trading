## 完整回测实现

### 4.1 回测引擎设计

回测是量化策略验证的核心环节。我们设计一个向量化的回测引擎（Vectorized Backtester），基于pandas的向量化计算能力，在日线数据上高效地计算策略的表现。

向量化回测的优点是速度快、代码简洁；缺点是难以模拟复杂的订单管理逻辑（如部分成交、挂单等）。对于日频的趋势跟踪策略，向量化回测完全足够。

### 4.2 完整回测代码

将前述的信号生成、仓位管理和回测计算整合到一个完整的函数中：

```python
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

def run_backtest(df, initial_capital=100000, commission_rate=0.0003,
                 slippage_rate=0.0001, stop_loss_pct=0.05):
    """
    完整的向量化回测引擎

    参数:
        df:             输入DataFrame (需包含close, high, low列)
        initial_capital: 初始资金
        commission_rate: 手续费率 (默认万分之三)
        slippage_rate:   滑点率 (默认万分之一)
        stop_loss_pct:   移动止损回撤比例 (默认5%)

    返回:
        metrics:  绩效指标字典
        df:       包含完整回测结果的DataFrame
    """
    df = df.copy()

    # ==================== 第一步：信号生成 ====================
    df['ma20'] = df['close'].rolling(20).mean()
    df['ma60'] = df['close'].rolling(60).mean()
    df['signal'] = (df['ma20'] > df['ma60']).astype(int)
    df['crossover'] = df['signal'].diff()

    # ==================== 第二步：移动止损 ====================
    df['stop_level'] = np.nan
    df['position_raw'] = df['signal'].shift(1).fillna(0)
    df['final_position'] = df['position_raw'].copy()

    in_position = False
    high_water = 0
    entry_price = 0

    for i in range(len(df)):
        idx = df.index[i]
        if not in_position:
            if df.loc[idx, 'position_raw'] == 1:
                in_position = True
                entry_price = df.loc[idx, 'close']
                high_water = entry_price
                df.loc[idx, 'stop_level'] = high_water * (1 - stop_loss_pct)
        else:
            current_close = df.loc[idx, 'close']
            high_water = max(high_water, current_close)
            current_stop = high_water * (1 - stop_loss_pct)
            df.loc[idx, 'stop_level'] = current_stop

            # 止损检查
            if current_close <= current_stop:
                df.loc[idx, 'final_position'] = 0
                df.loc[idx, 'stop_level'] = np.nan
                in_position = False
            # 信号平仓检查
            elif df.loc[idx, 'position_raw'] == 0:
                in_position = False
                df.loc[idx, 'stop_level'] = np.nan

    # ==================== 第三步：计算收益率 ====================
    df['position'] = df['final_position']

    # 每日收益率（考虑滑点和手续费）
    df['price_return'] = df['close'].pct_change()
    df['trade_signal'] = df['position'].diff().abs()  # 换仓信号
    df['slippage_cost'] = df['trade_signal'] * slippage_rate
    df['commission_cost'] = df['trade_signal'] * commission_rate
    df['strategy_return'] = (df['position'].shift(1) * df['price_return']
                             - df['slippage_cost'] - df['commission_cost'])
    df['strategy_return'].fillna(0, inplace=True)

    # ==================== 第四步：计算净值曲线 ====================
    df['equity'] = (1 + df['strategy_return']).cumprod() * initial_capital

    # 基准净值（买入持有）
    df['benchmark_equity'] = (1 + df['price_return'].fillna(0)).cumprod() * initial_capital

    # ==================== 第五步：计算绩效指标 ====================
    total_return = (df['equity'].iloc[-1] / initial_capital - 1) * 100
    benchmark_return = (df['benchmark_equity'].iloc[-1] / initial_capital - 1) * 100
    excess_return = total_return - benchmark_return

    n_days = len(df)
    n_years = n_days / 252
    annual_return = ((df['equity'].iloc[-1] / initial_capital) ** (1 / n_years) - 1) * 100

    daily_ret = df['strategy_return']
    daily_ret_mean = daily_ret.mean()
    daily_ret_std = daily_ret.std()
    sharpe_ratio = daily_ret_mean / daily_ret_std * np.sqrt(252) if daily_ret_std > 0 else 0

    annual_volatility = daily_ret_std * np.sqrt(252) * 100

    cummax = df['equity'].cummax()
    drawdown_series = (df['equity'] - cummax) / cummax
    max_drawdown = drawdown_series.min() * 100

    calmar_ratio = annual_return / abs(max_drawdown) if max_drawdown != 0 else 0

    # 胜率与盈亏比
    trades = []
    in_trade = False
    trade_entry = 0
    for i in range(1, len(df)):
        if df['position'].iloc[i] == 1 and not in_trade:
            in_trade = True
            trade_entry = df['close'].iloc[i]
        elif df['position'].iloc[i] == 0 and in_trade:
            in_trade = False
            trade_exit = df['close'].iloc[i]
            trades.append(trade_exit / trade_entry - 1)

    if trades:
        win_rate = sum(1 for t in trades if t > 0) / len(trades) * 100
        avg_win = np.mean([t for t in trades if t > 0]) * 100 if any(t > 0 for t in trades) else 0
        avg_loss = abs(np.mean([t for t in trades if t < 0]) * 100) if any(t < 0 for t in trades) else 0
        profit_loss_ratio = avg_win / avg_loss if avg_loss > 0 else float('inf')
    else:
        win_rate = 0
        profit_loss_ratio = 0
        avg_win = 0
        avg_loss = 0

    metrics = {
        '总收益率(%)': round(total_return, 2),
        '基准收益(%)': round(benchmark_return, 2),
        '超额收益(%)': round(excess_return, 2),
        '年化收益(%)': round(annual_return, 2),
        '夏普比率': round(sharpe_ratio, 2),
        '年化波动(%)': round(annual_volatility, 2),
        '最大回撤(%)': round(max_drawdown, 2),
        '卡玛比率': round(calmar_ratio, 2),
        '交易次数': len(trades),
        '胜率(%)': round(win_rate, 2),
        '盈亏比': round(profit_loss_ratio, 2),
    }

    return metrics, df

# 执行回测
metrics, df_backtest = run_backtest(
    df_clean,
    initial_capital=100000,
    stop_loss_pct=0.05
)

# 打印绩效报告
print("=" * 50)
print("           回测绩效报告           ")
print("=" * 50)
for key, value in metrics.items():
    print(f"{key:<15}: {value}")
print("=" * 50)
```

### 4.3 DolphinDB回测替代方案

在DolphinDB中实现同样功能的回测逻辑：

```
// DolphinDB端：向量化回测
def dolphinDBBacktest(close, signals, initCapital=100000, commission=0.0003) {
    // 计算每日收益率
    dailyReturn = close / close.prev() - 1
    dailyReturn[0] = 0

    // 策略收益率（考虑信号滞后）
    position = signals.prev()
    position[0] = 0
    strategyReturn = position * dailyReturn

    // 扣除交易成本
    tradeSignal = abs(diff(position))
    strategyReturn = strategyReturn - tradeSignal * commission

    // 净值曲线
    equity = (1 + strategyReturn).cumprod() * initCapital

    // 绩效指标
    totalReturn = equity[equity.size()-1] / initCapital - 1
    sharpe = avg(strategyReturn) / std(strategyReturn) * sqrt(252)
    peak = equity[0]
    maxDD = 0.0
    for (e in equity) {
        if (e > peak) peak = e
        dd = (e - peak) / peak
        if (dd < maxDD) maxDD = dd
    }

    return dict(STRING, ANY, [
        ["equity", equity],
        ["totalReturn", totalReturn * 100],
        ["sharpe", sharpe],
        ["maxDrawdown", maxDD * 100]
    ])
}
```

### 4.4 结果可视化

全面的回测结果可视化包括净值曲线、回撤图和年度收益分析：

```python
def plot_backtest_results(df, metrics):
    """绘制回测结果全景图"""
    fig, axes = plt.subplots(3, 2, figsize=(15, 12))

    # 1. 净值曲线对比
    ax = axes[0, 0]
    ax.plot(df.index, df['equity'], label='策略净值', color='blue', linewidth=1)
    ax.plot(df.index, df['benchmark_equity'], label='买入持有', color='gray', alpha=0.6, linewidth=1)
    ax.set_title('净值曲线对比')
    ax.set_ylabel('账户净值')
    ax.legend()
    ax.grid(True, alpha=0.3)

    # 2. 回撤曲线
    ax = axes[0, 1]
    cummax = df['equity'].cummax()
    drawdown = (df['equity'] - cummax) / cummax * 100
    ax.fill_between(df.index, drawdown, 0, color='red', alpha=0.3)
    ax.plot(df.index, drawdown, color='red', linewidth=0.8)
    ax.set_title(f'回撤曲线 (最大回撤: {metrics["最大回撤(%)"]}%)')
    ax.set_ylabel('回撤 (%)')
    ax.grid(True, alpha=0.3)

    # 3. 每日收益率分布
    ax = axes[1, 0]
    ax.hist(df['strategy_return'].dropna() * 100, bins=50,
            color='steelblue', edgecolor='white', alpha=0.8)
    ax.axvline(x=0, color='red', linestyle='--', linewidth=1)
    ax.set_title('每日收益率分布')
    ax.set_xlabel('日收益率 (%)')
    ax.set_ylabel('频次')
    ax.grid(True, alpha=0.3)

    # 4. 年度收益柱状图
    ax = axes[1, 1]
    df['year'] = df.index.year
    yearly = df.groupby('year')['strategy_return'].apply(
        lambda x: (1 + x).prod() - 1
    ) * 100
    colors = ['green' if v > 0 else 'red' for v in yearly.values]
    ax.bar(yearly.index.astype(str), yearly.values, color=colors, alpha=0.8)
    ax.set_title('年度收益率')
    ax.set_ylabel('收益率 (%)')
    ax.axhline(y=0, color='black', linewidth=0.5)
    ax.grid(True, alpha=0.3, axis='y')
    plt.setp(ax.xaxis.get_majorticklabels(), rotation=45)

    # 5. 持仓状态热力图（按年份展示）
    ax = axes[2, 0]
    df_monthly = df['position'].resample('M').mean()
    ax.fill_between(df_monthly.index, df_monthly.values,
                    color='green', alpha=0.4)
    ax.set_title('月度平均持仓比例')
    ax.set_ylabel('持仓比例')
    ax.set_ylim(0, 1.1)
    ax.grid(True, alpha=0.3)

    # 6. 绩效指标汇总表
    ax = axes[2, 1]
    ax.axis('off')
    table_text = (
        f"=========== 绩效汇总 ===========\n"
        f"总收益率:      {metrics['总收益率(%)']}%\n"
        f"基准收益:      {metrics['基准收益(%)']}%\n"
        f"超额收益:      {metrics['超额收益(%)']}%\n"
        f"年化收益:      {metrics['年化收益(%)']}%\n"
        f"夏普比率:      {metrics['夏普比率']}\n"
        f"最大回撤:      {metrics['最大回撤(%)']}%\n"
        f"卡玛比率:      {metrics['卡玛比率']}\n"
        f"交易次数:      {metrics['交易次数']}\n"
        f"胜率:           {metrics['胜率(%)']}%\n"
        f"盈亏比:        {metrics['盈亏比']}\n"
        f"================================"
    )
    ax.text(0.1, 0.5, table_text, transform=ax.transAxes,
            fontsize=9, fontfamily='monospace',
            verticalalignment='center',
            bbox=dict(boxstyle='round', facecolor='lightyellow', alpha=0.8))

    plt.suptitle('策略回测全景分析', fontsize=14, fontweight='bold')
    plt.tight_layout()
    plt.show()

plot_backtest_results(df_backtest, metrics)
```

### 4.5 策略评价与分析

拿到回测结果后，需要从多个维度评价策略质量：

#### 4.5.1 收益指标解读

| 指标 | 含义 | 可接受范围 |
|------|------|:---:|
| 总收益率 | 整个回测期的累计收益 | 显著跑赢基准即可 |
| 年化收益 | 平均每年的收益 | 10%-25% |
| 超额收益 | 相对基准的超出部分 | >3%（年化） |

#### 4.5.2 风险指标解读

| 指标 | 含义 | 可接受范围 |
|------|------|:---:|
| 最大回撤 | 从峰值到谷底的最大跌幅 | < 25% |
| 年化波动 | 收益率的波动程度 | < 30% |
| 夏普比率 | 风险调整后收益 | > 0.5 |

#### 4.5.3 交易行为解读

| 指标 | 含义 | 关注点 |
|------|------|--------|
| 交易次数 | 总买卖次数 | 过少→信号不充分，过多→交易成本高 |
| 胜率 | 盈利交易占比 | 30%-60%均正常，需结合盈亏比 |
| 盈亏比 | 平均盈利/平均亏损 | 应 > 1.5 |

> **重要认知**：胜率低不代表策略差。许多优秀的趋势跟踪策略胜率只有30%-40%，但盈亏比可达3:1甚至更高——亏损时小亏，盈利时大赚。

### 4.6 策略改进方向

基于回测结果分析，可以从以下方向改进策略：

1. **参数优化**
   - 尝试不同的均线组合：MA10×MA30、MA20×MA120等
   - 调整ATR倍数（1.5×, 2.5×, 3×）
   - 测试不同的止损比例（3%, 5%, 8%）

2. **增加过滤条件**
   - 添加成交量过滤（放量突破才入场）
   - 添加趋势过滤（ADX > 20才交易）
   - 添加波动率过滤（ATR/close < 5%）

3. **仓位管理升级**
   - 盈利加仓（金字塔加仓法）
   - 基于凯利公式的仓位计算
   - 组合层面的资金分配

4. **多标的扩展**
   - 在沪深300成分股上同时运行
   - 加入行业轮动逻辑
   - 加入对冲机制（做多强势股 + 做空弱势股）

5. **过渡到DolphinDB**
   - 将Python验证通过的逻辑迁移到DolphinDB
   - 利用分布式计算在数千只股票上批量回测
   - 使用DolphinDB回测引擎获得更准确的结果
   - 直接对接实盘交易系统

### 4.7 本章总结

恭喜你完成了端到端的量化策略开发实战！你经历了以下完整流程：

```
✅ 数据获取与清洗           → 确保数据质量
✅ 策略逻辑开发             → 双均线 + ATR仓位 + 移动止损
✅ 回测引擎搭建             → 完整的向量化回测
✅ 绩效指标计算             → 收益、风险、交易行为三大类
✅ 结果可视化               → 净值曲线、回撤、年度收益
✅ 策略评价与改进方向       → 多维度分析 + 优化建议
```

> **最终寄语**：量化交易的本质是通过系统化的方法将投资逻辑转化为可验证、可执行、可复制的交易策略。本章的案例只是起点。真正优秀的策略需要反复迭代、不断完善、在样本外数据上验证，最终在市场中保持谦逊和纪律。
