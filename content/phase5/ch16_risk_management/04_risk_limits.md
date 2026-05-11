## 风险限额体系

### 4.1 风险限额概述

风险限额（Risk Limits）是量化交易风险管理的核心工具。它通过对交易行为的各种约束，确保策略在任何市场条件下都不会产生超出预期的损失。一个完善的风险限额体系通常包括三个层次：止损控制、仓位限制和敞口管理。

> **核心理念**：永远不要让单笔亏损威胁到账户的生存。专业的交易者不是不会亏损，而是懂得如何控制亏损。

### 4.2 止损策略

止损（Stop-Loss）是最基础也是最关键的风险控制手段。根据触发方式的不同，止损策略可以分为以下三类：

#### 4.2.1 百分比止损

百分比止损是最简单的止损方式：当价格跌破进场价格的固定百分比时触发平仓。

| 止损比例 | 适用场景 | 优点 | 缺点 |
|----------|----------|------|------|
| 2%-3% | 短线交易 | 反应迅速 | 容易被噪音触发 |
| 5%-8% | 中线趋势 | 平衡性好 | 可能错过回调 |
| 10%-15% | 长线投资 | 避免过早离场 | 单笔亏损较大 |

#### 4.2.2 ATR止损

ATR（平均真实波幅）止损根据市场波动性动态调整止损距离，能更好地适应不同波动水平的市场环境：

```python
import numpy as np

def atr_stop_loss(high, low, close, period=14, multiplier=2):
    """
    基于ATR的动态止损
    period: ATR计算周期
    multiplier: ATR倍数，通常使用2-3倍
    """
    tr = np.maximum(
        high - low,
        np.maximum(abs(high - close.shift(1)), abs(low - close.shift(1)))
    )
    atr = tr.rolling(period).mean()
    stop_buy = close - multiplier * atr   # 多头止损价
    stop_sell = close + multiplier * atr  # 空头止损价
    return stop_buy, stop_sell, atr
```

ATR止损的核心优势在于"自适应"——当市场波动加剧时，止损距离自动扩大，避免被随机波动扫出市场；当市场趋于平稳时，止损距离收紧，及时保护利润。

#### 4.2.3 移动止损（Trailing Stop）

移动止损（或称跟踪止损）是最先进的止损策略之一。它不是固定的价格点，而是随着价格朝有利方向移动而不断上移（多头）或下移（空头），从而锁定浮动利润。

```python
def trailing_stop(prices, pct=0.05):
    """
    基于历史最高价的移动止损
    prices: 价格序列
    pct: 回撤比例，默认5%
    返回每个时点的止损价位
    """
    high_water = np.maximum.accumulate(prices)
    stop_level = high_water * (1 - pct)
    return stop_level

# 使用示例
import pandas as pd
df = pd.DataFrame({'close': [100, 102, 105, 103, 108, 110, 107, 112, 115, 113]})
stops = trailing_stop(df['close'].values, pct=0.05)
print(stops)  # 止损线跟随价格逐渐上移
```

移动止损的工作原理：
1. **追踪最高点**：`np.maximum.accumulate` 记录到目前为止的最高价（高位水印）
2. **计算止损线**：止损线 = 高位水印 × (1 - 回撤比例)
3. **触发条件**：当当前价格跌破止损线时，立即平仓

> **经验法则**：波段交易通常使用3%-5%的移动止损比例；趋势跟踪交易可使用8%-10%；日内交易则使用0.5%-1%。

### 4.3 仓位限制

仓位限制（Position Limits）控制投资组合在单一资产或特定类别上的集中度，防止因过度集中导致的灾难性风险。

#### 4.3.1 单一持仓上限

定义每只股票的最大持仓比例：

```python
def check_position_limit(current_positions, capital, max_single_pct=0.1):
    """
    检查单一持仓是否超限
    current_positions: dict {symbol: market_value}
    capital: 总资金
    max_single_pct: 单只股票最大持仓比例，默认10%
    """
    violations = {}
    for symbol, value in current_positions.items():
        weight = value / capital
        if weight > max_single_pct:
            violations[symbol] = {
                'current_weight': round(weight * 100, 2),
                'limit': round(max_single_pct * 100, 2),
                'excess': round((weight - max_single_pct) * capital, 2)
            }
    return violations
```

#### 4.3.2 行业板块上限

对同一板块的总持仓进行汇总控制：

| 限制类型 | 常见比例 | 目的 |
|----------|----------|------|
| 单一股票 | 5%-10% | 防止个股黑天鹅 |
| 单一行业 | 20%-30% | 防止板块系统风险 |
| 相关资产组 | 15%-25% | 防止相关性集中 |

### 4.4 敞口管理

敞口（Exposure）衡量的是投资组合对市场风险的敏感程度。

#### 4.4.1 净敞口与总敞口

- **净敞口** = 多头市值 - 空头市值。正值表示净多头，负值表示净空头。
- **总敞口** = 多头市值 + 空头市值。衡量总的市场参与程度。
- **杠杆率** = 总敞口 / 净资产。反映资金使用效率。

```python
def calculate_exposure(positions, capital):
    """计算投资组合的敞口指标"""
    long_value = sum(v for v in positions.values() if v > 0)
    short_value = sum(abs(v) for v in positions.values() if v < 0)

    net_exposure = (long_value - short_value) / capital
    gross_exposure = (long_value + short_value) / capital

    return {
        'net_exposure_pct': round(net_exposure * 100, 2),
        'gross_exposure_pct': round(gross_exposure * 100, 2),
        'long_pct': round(long_value / capital * 100, 2),
        'short_pct': round(short_value / capital * 100, 2)
    }
```

#### 4.4.2 Beta调整敞口

考虑每只股票的Beta系数后，可以计算Beta调整后的净敞口：

$$\text{BetaAdjustExposure} = \sum (w_i \times \beta_i)$$

其中 $w_i$ 是持仓权重，$\beta_i$ 是个股的Beta系数。

### 4.5 压力测试

压力测试（Stress Testing）评估投资组合在极端市场条件下的潜在损失。

#### 4.5.1 历史情景

基于真实历史事件构建测试场景：

| 情景名称 | 时间 | 市场跌幅 | 测试内容 |
|----------|------|----------|----------|
| 2008金融危机 | 2008.09-2009.03 | -50%+ | 系统性风险 |
| 2015股灾 | 2015.06-2015.08 | -40%+ | 流动性危机 |
| 2020疫情冲击 | 2020.02-2020.03 | -15%+ | 黑天鹅事件 |

```python
def stress_test_historical(portfolio_value, shock_pct):
    """基于历史情景的简单压力测试"""
    scenarios = {
        'mild': -0.05,      # 温和下跌5%
        'moderate': -0.15,  # 中度下跌15%
        'severe': -0.30,    # 严重下跌30%
        'extreme': -0.50    # 极端下跌50%
    }
    results = {}
    for name, pct in scenarios.items():
        results[name] = {
            'loss': round(portfolio_value * pct, 2),
            'remaining': round(portfolio_value * (1 + pct), 2)
        }
    return results
```

#### 4.5.2 假设性情景

假设性情景不依赖历史数据，而是基于"如果……会怎样"的逻辑：

- **相关性崩溃**：假设所有资产的相关系数骤升至0.9
- **流动性枯竭**：假设市场流动性下降80%，滑点扩大5倍
- **波动率飙升**：假设波动率上升至平时的3倍
- **跳空缺口**：假设关键持仓次日跳空低开10%

### 4.6 风险监控仪表盘

一个完整的风险监控系统应实时展示以下指标：

```python
def risk_dashboard(portfolio):
    """生成风险监控仪表盘"""
    dashboard = {
        '-----------------------------',
        '       风险监控仪表盘        ',
        '-----------------------------',
        f'总资产:     {portfolio["capital"]:>12,.0f}',
        f'净敞口:     {portfolio["net_exposure"]:>10.1f}%',
        f'总敞口:     {portfolio["gross_exposure"]:>10.1f}%',
        f'杠杆倍数:   {portfolio["leverage"]:>10.2f}x',
        f'当前回撤:   {portfolio["current_dd"]:>10.1f}%',
        f'最大回撤:   {portfolio["max_dd"]:>10.1f}%',
        f'VaR(95%):   {portfolio["var_95"]:>10,.0f}',
        f'持仓数量:   {portfolio["n_positions"]:>10}',
        f'单票最大:   {portfolio["max_single"]:>10.1f}%',
        f'-----------------------------------',
    }
    return '\n'.join(dashboard)
```

> **监控频率建议**：日内交易者需要分钟级别的实时监控；日频策略在每日收盘后运行；周频策略每周检查一次即可。

### 4.7 实施要点总结

1. **止损先行**：入场前就确定止损位，不要等亏损后再决策
2. **动态调整**：根据市场波动性（ATR）实时调整止损距离
3. **分散投资**：严格遵守单一持仓和行业上限，避免过度集中
4. **压力测试**：定期运行极端情景测试，确保极端行情下不会爆仓
5. **自动化执行**：将风险限额写入交易系统，实现自动阻断超限行为
6. **日志记录**：每次超限触发都应记录日志，用于事后分析和策略优化
