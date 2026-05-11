## 风险度量指标

### 引言

在量化交易中，收益和风险是一枚硬币的两面。只关注收益而忽视风险，无异于蒙着眼睛在悬崖边行走。历史上有太多因为风险管理不当而导致的灾难性亏损事件——从长期资本管理公司（LTCM）的崩溃到2008年金融危机中量化基金的巨额回撤，无一不在提醒我们风险管理的重要性。

本章将系统地介绍量化交易中最核心的风险度量指标，包括它们的计算原理、使用场景和潜在局限。这些指标将帮助你在追求收益的同时，时刻保持对风险的清醒认知。

> **核心原则**：好的风险管理不是在亏损发生后才采取措施，而是在交易之前就已经将风险纳入了策略设计的每一个环节。

### 夏普比率（Sharpe Ratio）

#### 定义与公式

夏普比率由诺贝尔经济学奖得主威廉·夏普（William F. Sharpe）于1966年提出，是衡量风险调整后收益的最经典指标。它回答了这样一个问题：**我每承担一单位的总风险，能够获得多少超过无风险利率的超额收益？**

$$Sharpe\ Ratio = \frac{R_p - R_f}{\sigma_p}$$

其中：
- $R_p$：策略的年化收益率
- $R_f$：无风险利率（通常使用国债收益率或存款利率）
- $\sigma_p$：策略的年化波动率（收益率的标准差）

在实际计算中，我们使用日频数据先计算日度的夏普比率，再年化：

$$\text{日夏普比率} = \frac{\bar{r}_{daily} - r_{f,daily}}{\sigma_{daily}}$$

$$\text{年化夏普比率} = \text{日夏普比率} \times \sqrt{252}$$

#### 深入理解

夏普比率的直观含义是"每单位风险的超额报酬"。假设两个策略年化收益都是20%，但策略A波动率10%，策略B波动率20%。策略A的夏普比率是策略B的两倍——因为它在获得相同收益的同时承担了更少的波动风险。

```python
import pandas as pd
import numpy as np

def calculate_sharpe_ratio(returns: pd.Series, risk_free_rate: float = 0.03, 
                            periods_per_year: int = 252) -> float:
    """
    计算年化夏普比率
    
    Parameters:
    -----------
    returns : pd.Series
        策略日收益率序列
    risk_free_rate : float
        年化无风险利率（默认3%）
    periods_per_year : int
        每年交易天数（默认252）
    """
    # 日化无风险利率
    daily_rf = risk_free_rate / periods_per_year
    
    # 超额收益率
    excess_returns = returns - daily_rf
    
    # 日夏普比率
    daily_sharpe = excess_returns.mean() / excess_returns.std()
    
    # 年化
    annualized_sharpe = daily_sharpe * np.sqrt(periods_per_year)
    
    return annualized_sharpe
```

#### 夏普比率的解读

| 夏普比率范围 | 评价等级 | 说明 |
|-------------|---------|------|
| < 0 | 不合格 | 表现不如无风险资产 |
| 0 ~ 0.5 | 一般 | 策略有正收益，但风险调整效果不显著 |
| 0.5 ~ 1.0 | 良好 | 策略表现值得关注 |
| 1.0 ~ 2.0 | 优秀 | 大多数成功的量化策略在此区间 |
| 2.0 ~ 3.0 | 卓越 | 极少数策略能达到 |
| > 3.0 | 需警惕 | 很可能存在问题（过拟合/数据错误） |

> **夏普比率的局限性**：
> 1. 假设收益率服从正态分布，但现实中金融收益率存在尖峰厚尾特征
> 2. 对上行波动和下行波动一视同仁——但投资者通常乐见大涨，厌恶大跌
> 3. 对极端事件不敏感——一次巨大的单日亏损可能只将夏普比率拉低一点点
> 4. 不同时间频率计算出的夏普比率不能直接比较（日度、周度、月度年化后可能不一致）

### 索提诺比率（Sortino Ratio）

#### 定义与公式

索提诺比率是夏普比率的改进版，由 Frank Sortino 提出。核心区别在于分母：索提诺比率只使用**下行波动率**（Downside Deviation），而非总波动率。这更符合投资者的真实心理——我们真正担心的不是收益向上波动，而是向下亏损。

$$Sortino\ Ratio = \frac{R_p - R_{MAR}}{\text{Downside Deviation}}$$

其中 MAR（Minimum Acceptable Return）是最低可接受收益率，通常设为0或无风险利率。下行偏差的计算方式为：

$$\text{Downside Deviation} = \sqrt{\frac{1}{N} \sum_{t=1}^{N} \min(r_t - MAR, 0)^2}$$

```python
def calculate_sortino_ratio(returns: pd.Series, mar: float = 0.0, 
                             periods_per_year: int = 252) -> float:
    """
    计算年化索提诺比率
    
    Parameters:
    -----------
    returns : pd.Series
        策略日收益率序列
    mar : float
        最低可接受日收益率（默认0）
    periods_per_year : int
        每年交易天数
    """
    # 下行收益率：低于MAR的部分
    downside_returns = returns[returns < mar]
    
    if len(downside_returns) == 0:
        return float('inf')  # 没有下行，完美
    
    # 日下行偏差
    downside_deviation = np.sqrt(np.mean((downside_returns - mar) ** 2))
    
    # 年化下行偏差
    annualized_downside = downside_deviation * np.sqrt(periods_per_year)
    
    # 年化超额收益
    annualized_excess = (returns.mean() - mar) * periods_per_year
    
    return annualized_excess / annualized_downside
```

#### 索提诺比率与夏普比率的比较

```python
# 模拟两种不同的收益分布来比较两个指标
import matplotlib.pyplot as plt

np.random.seed(42)
n = 500

# 策略A：对称分布，正负波动均衡
returns_a = np.random.normal(0.001, 0.02, n)

# 策略B：偏态分布，经常小赚、偶尔大亏（像卖期权策略）
returns_b = np.concatenate([
    np.random.normal(0.002, 0.01, 480),  # 大部分时间小赚
    np.random.normal(-0.03, 0.02, 20)    # 偶尔大亏
])

sr_a = calculate_sharpe_ratio(pd.Series(returns_a))
sr_b = calculate_sharpe_ratio(pd.Series(returns_b))

sortino_a = calculate_sortino_ratio(pd.Series(returns_a))
sortino_b = calculate_sortino_ratio(pd.Series(returns_b))

print(f"策略A - 夏普: {sr_a:.3f}, 索提诺: {sortino_a:.3f}")
print(f"策略B - 夏普: {sr_b:.3f}, 索提诺: {sortino_b:.3f}")
```

在多数情况下，Sortino 比率能够更好地区分那些"偶尔大亏"的策略和"平稳亏损"的策略——前者可能夏普比率不算太差，但 Sortino 比率会显著更低。

### 卡玛比率（Calmar Ratio）

#### 定义与公式

卡玛比率由 Terry W. Young 于1991年提出，它使用**最大回撤（Maximum Drawdown）**替代波动率作为风险度量。这个指标的直观含义非常清晰：**为了获得这些收益，我在最糟糕的时候承受了多大的损失？**

$$Calmar\ Ratio = \frac{年化收益率}{|最大回撤|}$$

> 最大回撤作为静态指标存在一个缺陷：它只反映历史上最大的单次回撤，而对回撤的频率、持续时间不敏感。尽管如此，它对投资者的心理影响却是最直接的——"我最多会亏多少钱"往往是投资者最关心的问题。

```python
def calculate_calmar_ratio(net_values: pd.Series, periods_per_year: int = 252) -> float:
    """
    计算卡玛比率
    
    Parameters:
    -----------
    net_values : pd.Series
        净值序列
    periods_per_year : int
        每年交易天数
    """
    # 计算年化收益率
    total_return = net_values.iloc[-1] / net_values.iloc[0] - 1
    n_periods = len(net_values)
    annualized_return = (1 + total_return) ** (periods_per_year / n_periods) - 1
    
    # 计算最大回撤
    rolling_max = net_values.expanding().max()
    drawdowns = (net_values - rolling_max) / rolling_max
    max_drawdown = abs(drawdowns.min())
    
    if max_drawdown == 0:
        return float('inf')
    
    return annualized_return / max_drawdown
```

#### 卡玛比率的参考标准

| 卡玛比率 | 评价 |
|---------|------|
| < 0 | 负收益，策略不可取 |
| 0 ~ 0.5 | 收益对回撤的补偿不足 |
| 0.5 ~ 1.0 | 可接受 |
| 1.0 ~ 2.0 | 良好 |
| 2.0 ~ 3.0 | 优秀 |
| > 3.0 | 极其优秀 |

### 最大回撤的深度分析

#### 不仅仅是最大回撤

最大回撤是单一的极值统计量，我们需要更全面地理解回撤的分布特征：

```python
def drawdown_analysis(net_values: pd.Series) -> dict:
    """
    对回撤进行多维度分析
    
    Returns:
    --------
    dict: 包含最大回撤、平均回撤、回撤持续时间等指标
    """
    rolling_max = net_values.expanding().max()
    drawdowns = (net_values - rolling_max) / rolling_max
    
    # 识别回撤区间（连续的回撤期间）
    underwater = drawdowns < 0
    # 标记不同的回撤区间
    dd_periods = (underwater != underwater.shift(1)).cumsum()
    
    dd_regions = []
    for period_id in dd_periods[underwater].unique():
        period_data = drawdowns[dd_periods == period_id]
        if len(period_data) > 0:
            dd_regions.append({
                'start': period_data.index[0],
                'end': period_data.index[-1],
                'duration_days': len(period_data),
                'max_dd': period_data.min(),
                'avg_dd': period_data.mean()
            })
    
    if not dd_regions:
        return {'max_drawdown': 0, 'avg_drawdown': 0, 'max_dd_duration': 0,
                'total_dd_periods': 0}
    
    dd_df = pd.DataFrame(dd_regions)
    
    return {
        'max_drawdown': drawdowns.min(),
        'avg_drawdown': dd_df['max_dd'].mean(),  # 平均最大回撤（各回撤区间的平均值）
        'max_dd_duration': dd_df['duration_days'].max(),
        'avg_dd_duration': dd_df['duration_days'].mean(),
        'total_dd_periods': len(dd_regions),
        'longest_dd_start': dd_df.loc[dd_df['duration_days'].idxmax(), 'start'],
        'longest_dd_end': dd_df.loc[dd_df['duration_days'].idxmax(), 'end']
    }
```

#### 回撤恢复时间

回撤恢复时间（Recovery Time）衡量从回撤最低点到净值恢复至前高所需的天数：

```python
def recovery_time_analysis(net_values: pd.Series) -> pd.Series:
    """
    计算每个时间点的回撤恢复时间

    返回系列中每个日期对应的尚未恢复的天数
    """
    rolling_max = net_values.expanding().max()
    
    recovery_days = pd.Series(0.0, index=net_values.index)
    
    for i in range(1, len(net_values)):
        if net_values.iloc[i] < rolling_max.iloc[i]:
            # 仍在回撤中，累加天数
            recovery_days.iloc[i] = recovery_days.iloc[i-1] + 1
        else:
            recovery_days.iloc[i] = 0
    
    return recovery_days
```

### 波动率与VaR指标

#### 波动率的多维度分析

年度波动率是最基础的风险指标，但我们可以进一步拆解它：

```python
def volatility_decomposition(returns: pd.Series, periods_per_year: int = 252) -> dict:
    """
    波动率的多维度分析
    """
    ann_vol = returns.std() * np.sqrt(periods_per_year)
    
    # 正负收益分解
    pos_returns = returns[returns > 0]
    neg_returns = returns[returns < 0]
    
    # 偏度：收益分布的不对称性
    skewness = returns.skew()
    # < 0：左偏（大亏概率高），> 0：右偏（大赚概率高）
    
    # 峰度：收益分布的尾部厚度
    kurtosis = returns.kurtosis()
    # > 0：尖峰厚尾（极端事件比正态分布更常见）
    
    # 滚动波动率——观察波动率的变化趋势
    rolling_vol = returns.rolling(60).std() * np.sqrt(periods_per_year)
    
    return {
        'annualized_volatility': ann_vol,
        'positive_volatility': pos_returns.std() * np.sqrt(periods_per_year) if len(pos_returns) > 0 else 0,
        'negative_volatility': neg_returns.std() * np.sqrt(periods_per_year) if len(neg_returns) > 0 else 0,
        'skewness': skewness,
        'kurtosis': kurtosis,
        'volatility_range': (rolling_vol.min(), rolling_vol.max()),
        'volatility_trend': np.polyfit(range(len(returns)), returns.values, 1)[0]  # 波动率趋势
    }
```

### 综合风险评分体系

将多个风险指标整合为综合评分，便于不同策略之间的横向比较：

```python
def comprehensive_risk_score(returns: pd.Series, net_values: pd.Series,
                              risk_free_rate: float = 0.03) -> dict:
    """
    计算综合风险评分（0-100分，分数越高越好）
    """
    scores = {}
    
    # 1. 夏普比率评分（-1到3的范围映射到0-100）
    sharpe = calculate_sharpe_ratio(returns, risk_free_rate)
    scores['夏普比率'] = max(0, min(100, (sharpe + 1) * 25))
    
    # 2. 最大回撤评分（0%到50%的回撤映射到100-0）
    rolling_max = net_values.expanding().max()
    max_dd = abs((net_values - rolling_max) / rolling_max).max()
    scores['最大回撤'] = max(0, min(100, 100 - max_dd * 200))
    
    # 3. 卡玛比率评分
    calmar = calculate_calmar_ratio(net_values)
    scores['卡玛比率'] = max(0, min(100, calmar * 40))
    
    # 4. 胜率评分
    win_rate = (returns > 0).sum() / len(returns) * 100
    scores['胜率'] = max(0, min(100, win_rate))
    
    # 5. 盈亏比评分
    avg_win = returns[returns > 0].mean() if (returns > 0).any() else 0
    avg_loss = abs(returns[returns < 0].mean()) if (returns < 0).any() else 0
    pnl_ratio = avg_win / avg_loss if avg_loss != 0 else 5.0
    scores['盈亏比'] = max(0, min(100, pnl_ratio * 30))
    
    # 6. 下行波动率评分（0-50%的年化下行波动率映射到100-0）
    downside_returns = returns[returns < 0]
    ann_downside_vol = downside_returns.std() * np.sqrt(252) if len(downside_returns) > 0 else 0
    scores['下行风险'] = max(0, min(100, 100 - ann_downside_vol * 200))
    
    # 加权总分
    weights = {
        '夏普比率': 0.25,
        '最大回撤': 0.25,
        '卡玛比率': 0.15,
        '胜率': 0.10,
        '盈亏比': 0.10,
        '下行风险': 0.15
    }
    
    total_score = sum(scores[k] * weights[k] for k in weights)
    
    return {
        '分项得分': scores,
        '综合得分': total_score,
        '评级': _get_risk_grade(total_score)
    }

def _get_risk_grade(score: float) -> str:
    if score >= 85:
        return 'A (优秀)'
    elif score >= 70:
        return 'B (良好)'
    elif score >= 55:
        return 'C (一般)'
    elif score >= 40:
        return 'D (较差)'
    else:
        return 'E (危险)'
```

### 指标选择的最佳实践

| 场景 | 优先关注的指标 | 原因 |
|------|-------------|------|
| 高频交易策略 | 夏普比率、盈亏比 | 高频策略交易次数多，需要关注每笔交易质量 |
| 趋势跟踪策略 | 最大回撤、卡玛比率 | 趋势策略容易在震荡市中连续亏损 |
| 套利策略 | 夏普比率、信息比率 | 收益较薄，需要关注风险调整后收益 |
| 杠杆策略 | 最大回撤、下行波动率 | 杠杆放大风险，需要严格控制尾部风险 |
| 多因子策略 | Alpha、信息比率 | 需要评估因子对基准的超额贡献 |
| 期权策略 | Sortino比率、偏度 | 期权收益不对称，关注尾部风险 |

### 总结

风险度量指标不是孤立的数字，它们共同构成了一幅立体的策略风险画像。关键原则：

1. **永远不要只看单一指标**——综合多个维度才能全面理解风险
2. **夏普比率是基础，但不要迷信**——它存在多个局限性
3. **最大回撤是底线**——实盘中最直接的心理考验
4. **Sortino比率补充夏普**——更关注下行风险
5. **关注回撤的结构**——不仅是深度，还有持续时间和频率
6. **建立自己的一贯评估框架**——连贯的评估比单次精确的计算更重要

下一章，我们将深入学习风险价值（VaR）——金融行业中最广泛使用的风险量化标准之一。
