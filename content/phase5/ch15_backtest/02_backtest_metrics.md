## 回测绩效指标

### 概述

回测的目的是用数据来回答"策略好不好"这个问题。但"好"是一个多维度、综合性的概念——它可能意味着高收益，也可能意味着低风险，又或者是在承担合理风险的前提下获得令人满意的回报。因此，我们需要一套完整的绩效指标体系来全方位评估策略的表现。

本章将详细介绍量化交易回测中最为核心的几项绩效指标，包括它们的计算方法、适用场景和可能存在的缺陷。这些指标是量化交易者日常工作中最常用的分析工具，掌握它们对于理解策略特性至关重要。

### 收益率类指标

#### 总收益率（Total Return）

总收益率是最直观的绩效指标，衡量策略在整个回测期间累计产生的收益百分比。

```
总收益率 = (期末净值 - 期初净值) / 期初净值 × 100%
```

或者用累积乘积的形式：

```
总收益率 = (∏(1 + r_i) - 1) × 100%
```

其中 r_i 是第 i 期的收益率。

```python
import pandas as pd
import numpy as np

def total_return(daily_returns):
    """
    计算总收益率
    daily_returns: 每日收益率序列（小数形式，如 0.01 表示 1%）
    """
    cumulative = (1 + daily_returns).prod()
    return (cumulative - 1) * 100

# 示例
returns = pd.Series([0.01, -0.005, 0.02, 0.015, -0.01])
print(f"总收益率: {total_return(returns):.2f}%")
```

> **注意**：总收益率受回测时长影响很大。一个3年30%收益率的策略和一个1年30%收益率的策略，显然前者年化收益更低。因此单纯看总收益率是不够的，需要结合年化收益率综合判断。

#### 年化收益率（Annualized Return）

年化收益率将策略的总收益率折算到年度水平，使得不同时间长度的策略可以进行公平比较。

```
年化收益率 = (期末净值 / 期初净值)^(年化因子 / 总交易日数) - 1
```

其中常用的年化因子包括：
- **252**：用于日频数据（一年约252个交易日）
- **52**：用于周频数据
- **12**：用于月频数据

```python
def annualized_return(daily_returns, trading_days_per_year=252):
    """
    计算年化收益率
    """
    cumulative_return = (1 + daily_returns).prod()
    n_days = len(daily_returns)
    annualized = cumulative_return ** (trading_days_per_year / n_days) - 1
    return annualized * 100

# 示例：3年期间总收益60%的策略
n_days = 252 * 3
volatility = 0.15 / np.sqrt(252)  # 日波动率
np.random.seed(42)
returns_3y = pd.Series(np.random.normal(0.0005, volatility, n_days))
print(f"总收益率: {total_return(returns_3y):.2f}%")
print(f"年化收益率: {annualized_return(returns_3y):.2f}%")
```

#### 几何平均收益率

几何平均收益率考虑了复利效应，比算术平均收益率更准确地反映了策略的真实增长情况。

```
几何平均收益率 = (期末净值 / 期初净值)^(1/n) - 1
```

其中 n 为总期数。

```python
def geometric_mean_return(daily_returns):
    """计算几何平均日收益率"""
    cumulative = (1 + daily_returns).prod()
    n = len(daily_returns)
    return cumulative ** (1/n) - 1
```

### 波动性与风险类指标

#### 年化波动率（Annualized Volatility）

波动率衡量策略收益率的波动程度，是策略风险最基础的度量。通常使用收益率的标准差来计算。

```
年化波动率 = 日收益率标准差 × √252
```

较高的波动率意味着策略净值曲线更加颠簸，对于大多数投资者而言这意味着更高的心理压力。

```python
def annualized_volatility(daily_returns, trading_days_per_year=252):
    """
    计算年化波动率
    """
    return daily_returns.std() * np.sqrt(trading_days_per_year) * 100

# 示例
vol = annualized_volatility(returns_3y)
print(f"年化波动率: {vol:.2f}%")
```

#### 最大回撤（Maximum Drawdown）

> **最大回撤是衡量策略尾部风险的黄金指标**——它描述了在选取的历史时间段内，从最高净值点到随后的最低净值点之间发生的最大亏损幅度。

最大回撤的计算分为两步：

1. 计算滚动最大值（历史最高净值）：`peak_t = max(净值_0, 净值_1, ..., 净值_t)`
2. 计算回撤：`drawdown_t = (净值_t - peak_t) / peak_t`
3. 取最小值（即最大回撤）：`max_drawdown = min(drawdown_t)`

```python
def max_drawdown(net_values):
    """
    计算最大回撤
    net_values: 净值序列（或价格序列）
    返回: 最大回撤（负数）, 最大回撤开始日期, 最大回撤结束日期, 回撤序列
    """
    rolling_max = net_values.expanding().max()
    drawdowns = (net_values - rolling_max) / rolling_max

    max_dd = drawdowns.min()

    # 找到最大回撤的开始和结束日期
    end_idx = drawdowns.idxmin()

    # 找到回撤开始日期（end_idx之前的历史最高点）
    start_idx = net_values[:end_idx].idxmax()

    return max_dd, start_idx, end_idx, drawdowns

# 示例：使用模拟数据
import matplotlib.pyplot as plt

np.random.seed(123)
n = 500
random_walk = 100 * np.exp(np.random.randn(n).cumsum() * 0.01)
net_values = pd.Series(random_walk, index=pd.date_range('2020-01-01', periods=n))

dd, peak_date, trough_date, dd_series = max_drawdown(net_values)
print(f"最大回撤: {dd:.2%}")
print(f"回撤开始: {peak_date.date()}")
print(f"回撤结束: {trough_date.date()}")

# 可选：绘制净值曲线和回撤
fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 6))
ax1.plot(net_values.index, net_values.values)
ax1.set_title('净值曲线')
ax2.fill_between(dd_series.index, 0, dd_series.values, color='red', alpha=0.3)
ax2.set_title('回撤序列')
plt.tight_layout()
```

#### 最大回撤持续时间

除了回撤的深度，回撤的持续时间同样重要。一个持续两年的30%回撤和一个持续两个月的30%回撤，对投资者的心理考验截然不同。

```python
def max_drawdown_duration(drawdown_series):
    """
    计算最大回撤持续时间
    drawdown_series: 回撤序列（由max_drawdown函数返回）
    返回：最大持续时间的天数
    """
    # 找出回撤期间（回撤 < 0）的连续天数
    underwater = drawdown_series < 0
    # 标记连续的组
    groups = (underwater != underwater.shift(1)).cumsum()
    durations = underwater.groupby(groups).sum()
    return durations.max()
```

#### 年化下行波动率（Downside Volatility）

标准波动率对称地处理上涨和下跌，但投资者通常只关心向下的波动。下行波动率只衡量负收益率的标准差，更能反映策略的真实风险。

```python
def downside_volatility(daily_returns, target_return=0, trading_days=252):
    """
    计算年化下行波动率
    target_return: 目标收益率阈值，低于此值的收益率才被视为"下行"
    """
    downside = daily_returns[daily_returns < target_return]
    return downside.std() * np.sqrt(trading_days) * 100
```

### 风险调整收益指标

#### 夏普比率（Sharpe Ratio）

夏普比率是最经典的风险调整收益指标，衡量每承担一单位总风险所获得的超额收益。

```
夏普比率 = (策略年化收益率 - 无风险利率) / 策略年化波动率
```

```python
def sharpe_ratio(daily_returns, risk_free_rate=0.03, trading_days=252):
    """
    计算夏普比率
    risk_free_rate: 年化无风险利率（如 0.03 表示 3%）
    """
    excess_returns = daily_returns - risk_free_rate / trading_days
    return np.sqrt(trading_days) * excess_returns.mean() / excess_returns.std()

print(f"夏普比率: {sharpe_ratio(returns_3y):.3f}")
```

夏普比率的参考标准：
| 夏普比率 | 评价 |
|---------|------|
| < 0 | 表现不如无风险资产 |
| 0 ~ 0.5 | 一般 |
| 0.5 ~ 1.0 | 较好 |
| 1.0 ~ 2.0 | 优秀 |
| > 2.0 | 极其优秀（需警惕过拟合）|
| > 3.0 | 很可能存在数据问题或过拟合 |

> **夏普比率的局限性**：它假设收益率服从正态分布，对正收益和负收益的惩罚完全一样。但在现实中，投资者欢迎正偏差（大涨），厌恶负偏差（大跌）。此外，夏普比率对极端事件的敏感度不足。

#### 胜率（Win Rate）

胜率衡量所有交易中盈利交易的比例。

```
胜率 = 盈利交易次数 / 总交易次数 × 100%
```

```python
def win_rate(trade_returns):
    """
    计算胜率
    trade_returns: 每笔交易的收益率序列
    """
    winning_trades = (trade_returns > 0).sum()
    total_trades = len(trade_returns)
    return (winning_trades / total_trades) * 100
```

#### 盈亏比（Profit-Loss Ratio / Profit Factor）

**盈利因子**（Profit Factor）衡量总盈利与总亏损的比值，是量化交易中非常重要的指标：

```
盈利因子 = 总盈利金额 / |总亏损金额|

或按收益率：
盈利因子 = 正收益总和 / |负收益总和|
```

盈利因子 > 1 表示策略整体盈利，值越大越好。通常认为盈利因子 > 1.5 的策略是好的。

```python
def profit_factor(trade_returns):
    """
    计算盈利因子
    """
    gross_profit = trade_returns[trade_returns > 0].sum()
    gross_loss = abs(trade_returns[trade_returns < 0].sum())
    if gross_loss == 0:
        return float('inf')  # 没有亏损交易
    return gross_profit / gross_loss
```

**平均盈亏比**衡量每次盈利交易与每次亏损交易的平均幅度之比：

```
平均盈亏比 = 平均盈利 / |平均亏损|
```

```python
def avg_profit_loss_ratio(trade_returns):
    """
    计算平均盈亏比
    """
    profits = trade_returns[trade_returns > 0]
    losses = trade_returns[trade_returns < 0]

    avg_win = profits.mean() if len(profits) > 0 else 0
    avg_loss = abs(losses.mean()) if len(losses) > 0 else float('inf')

    return avg_win / avg_loss if avg_loss != 0 else float('inf')
```

#### 卡玛比率（Calmar Ratio）

卡玛比率衡量策略的年化收益率与最大回撤之间的关系：

```
卡玛比率 = 年化收益率 / |最大回撤|
```

这个指标直接回答了"为了获得这些收益，我承担了多少最大回撤的代价"这个问题。

```python
def calmar_ratio(annual_return, max_drawdown):
    """
    计算卡玛比率
    """
    return annual_return / abs(max_drawdown)
```

#### 索提诺比率（Sortino Ratio）

索提诺比率是夏普比率的改进版，只用下行波动率作为风险分母。这更符合投资者对风险的直觉——我们关心的是下跌风险而非上涨波动。

```
索提诺比率 = (年化收益率 - 目标收益率) / 下行波动率
```

```python
def sortino_ratio(daily_returns, target_return=0, trading_days=252):
    """
    计算索提诺比率
    """
    excess = daily_returns - target_return / trading_days
    downside = excess[excess < 0]
    downside_std = downside.std() * np.sqrt(trading_days)
    return (excess.mean() * trading_days) / downside_std
```

### 进阶收益分解指标

#### Alpha 与 Beta

**Beta（β）**衡量策略收益率对市场收益率（基准）的敏感性：

```
β = Cov(策略收益率, 基准收益率) / Var(基准收益率)
```

- β = 1：策略与市场同步波动
- β > 1：策略波动大于市场（进攻型）
- β < 1：策略波动小于市场（防御型）

**Alpha（α）**衡量策略中不能被市场波动解释的超额收益部分：

```
α = 策略平均收益率 - [无风险利率 + β × (基准平均收益率 - 无风险利率)]
```

```python
def calc_alpha_beta(strategy_returns, benchmark_returns, risk_free_rate=0.03, trading_days=252):
    """
    计算Alpha和Beta
    """
    aligned = pd.DataFrame({
        'strategy': strategy_returns,
        'benchmark': benchmark_returns
    }).dropna()

    # Beta
    cov = aligned.cov().iloc[0, 1]
    var_benchmark = aligned['benchmark'].var()
    beta = cov / var_benchmark

    # Alpha（年化）
    strat_annual = aligned['strategy'].mean() * trading_days
    bench_annual = aligned['benchmark'].mean() * trading_days
    alpha = strat_annual - (risk_free_rate + beta * (bench_annual - risk_free_rate))

    return alpha * 100, beta

# 示例
benchmark_returns = pd.Series(
    np.random.normal(0.0003, 0.012, len(returns_3y)),
    index=returns_3y.index
)
alpha, beta = calc_alpha_beta(returns_3y, benchmark_returns)
print(f"Alpha: {alpha:.2f}%")
print(f"Beta: {beta:.3f}")
```

#### 信息比率（Information Ratio）

信息比率衡量策略相对于基准的超额收益的稳定性：

```
信息比率 = (策略年化收益率 - 基准年化收益率) / 跟踪误差
跟踪误差 = StdDev(策略收益率 - 基准收益率) × √252
```

```python
def information_ratio(strategy_returns, benchmark_returns, trading_days=252):
    """
    计算信息比率
    """
    diff = strategy_returns - benchmark_returns
    tracking_error = diff.std() * np.sqrt(trading_days)
    excess_return = diff.mean() * trading_days
    return excess_return / tracking_error if tracking_error != 0 else 0
```

### 综合绩效报告

将以上指标整合成一个综合的绩效报告函数：

```python
def performance_report(strategy_returns, benchmark_returns=None, trade_returns=None, 
                       risk_free_rate=0.03, trading_days=252):
    """
    生成综合绩效报告
    """
    # 基础指标
    cum_return = total_return(strategy_returns)
    ann_return = annualized_return(strategy_returns, trading_days)
    ann_vol = annualized_volatility(strategy_returns, trading_days)
    sharpe = sharpe_ratio(strategy_returns, risk_free_rate, trading_days)
    sortino = sortino_ratio(strategy_returns, 0, trading_days)
    dd, _, _, dd_series = max_drawdown((1 + strategy_returns).cumprod())
    
    report = {
        "总收益率": f"{cum_return:.2f}%",
        "年化收益率": f"{ann_return:.2f}%",
        "年化波动率": f"{ann_vol:.2f}%",
        "夏普比率": f"{sharpe:.3f}",
        "索提诺比率": f"{sortino:.3f}",
        "卡玛比率": f"{calmar_ratio(ann_return, dd):.3f}",
        "最大回撤": f"{dd:.2%}",
    }
    
    if benchmark_returns is not None:
        alpha, beta = calc_alpha_beta(strategy_returns, benchmark_returns, risk_free_rate, trading_days)
        ir = information_ratio(strategy_returns, benchmark_returns, trading_days)
        report["Alpha"] = f"{alpha:.2f}%"
        report["Beta"] = f"{beta:.3f}"
        report["信息比率"] = f"{ir:.3f}"
    
    if trade_returns is not None and len(trade_returns) > 0:
        report["胜率"] = f"{win_rate(trade_returns):.2f}%"
        report["盈利因子"] = f"{profit_factor(trade_returns):.3f}"
        report["平均盈亏比"] = f"{avg_profit_loss_ratio(trade_returns):.3f}"
        report["交易次数"] = len(trade_returns)
    
    return report

# 使用示例
report = performance_report(returns_3y, benchmark_returns)
for key, value in report.items():
    print(f"{key}: {value}")
```

### 指标选择的指导原则

| 评估维度 | 推荐指标 | 说明 |
|---------|---------|------|
| 收益评估 | 年化收益率、几何平均收益率 | 不同时间框架下公平比较 |
| 风险度量 | 最大回撤、年化波动率、下行波动率 | 全面衡量策略风险 |
| 风险调整收益 | 夏普比率、索提诺比率 | 衡量风险效率 |
| 交易质量 | 胜率、盈利因子、盈亏比 | 评估单笔交易的质量 |
| 市场相关性 | Alpha、Beta、信息比率 | 理解策略与市场的关系 |

> **重要提醒**：没有任何一个单一的指标可以全面评判一个策略。必须综合多个指标，从收益、风险、稳定性和可持续性等多个角度立体分析。同时，永远对极端优异的结果保持怀疑——它们往往意味着数据问题或方法论错误，而非真正找到了交易的"圣杯"。

### 总结

回测绩效指标是将策略表现从抽象的感受转化为可量化、可比较的数字的工具。掌握这些指标的计算方法和解读方式，是成为合格量化交易者的第一步。在实际使用中，请务必做到：
1. 用年化指标标准化不同时间段的比较
2. 同时关注收益和风险两方面的指标
3. 特别重视最大回撤——它是实盘中最折磨人的指标
4. 使用多个指标交叉验证，避免单一指标的局限性
