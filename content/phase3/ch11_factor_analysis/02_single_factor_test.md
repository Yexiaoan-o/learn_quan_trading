## 单因子检验方法

单因子检验（Single Factor Test）是因子研究中最关键的环节——它决定一个因子是否真的有预测未来收益的能力。本节将系统介绍因子IC分析、分层回测和因子收益率评估三大核心方法。

---

### 一、信息系数（IC）分析

IC（Information Coefficient）衡量因子值与未来收益之间的相关性，是最常用的因子有效性度量指标。

#### 1.1 Rank IC（排名信息系数）

Rank IC使用Spearman秩相关系数，衡量因子排名的预测能力。相比普通IC，Rank IC对极端值更加鲁棒，因此被业界广泛采用。

```python
import numpy as np
from scipy.stats import spearmanr
import pandas as pd


def calculate_rank_ic(factor_values, forward_returns):
    """
    计算Rank IC（横截面Spearman秩相关）

    参数:
        factor_values: 当期的因子值（横截面）
        forward_returns: 未来期的收益率
    返回:
        rank_ic: Spearman秩相关系数
        p_value: 统计显著性
    """
    # 去除缺失值
    valid = ~(np.isnan(factor_values) | np.isnan(forward_returns))
    factor_clean = factor_values[valid]
    returns_clean = forward_returns[valid]

    if len(factor_clean) < 10:
        return np.nan, np.nan

    # Spearman秩相关
    ic, p_value = spearmanr(factor_clean, returns_clean)
    return ic, p_value


def rolling_ic_analysis(factor_df, periods=[1, 5, 20]):
    """
    滚动IC分析：计算不同未来持有期的IC序列

    参数:
        factor_df: DataFrame，索引=date列=symbol，值为因子值
        periods: 未来持有期列表
    返回:
        ic_summary: IC统计量汇总
    """
    results = {}

    for period in periods:
        ic_series = []
        dates = sorted(factor_df.index.unique())

        for i, date in enumerate(dates[:-period]):
            # 当期因子值
            factor = factor_df.loc[date]

            # 未来收益率（period持有期）
            future_price = factor_df.shift(-period).loc[date]
            current_price = factor_df.loc[date]
            fwd_ret = (future_price - current_price) / current_price

            # 计算Rank IC
            ic, _ = calculate_rank_ic(factor.values, fwd_ret.values)
            ic_series.append((date, ic))

        ic_df = pd.DataFrame(ic_series, columns=['date', 'IC'])
        ic_df = ic_df.dropna()

        results[period] = {
            'IC_mean': ic_df['IC'].mean(),
            'IC_std': ic_df['IC'].std(),
            'ICIR': ic_df['IC'].mean() / ic_df['IC'].std(),        # IC信息比率
            'IC_pos_ratio': (ic_df['IC'] > 0).mean(),              # IC正值比例
            'IC_tstat': ic_df['IC'].mean() / ic_df['IC'].std() * np.sqrt(len(ic_df))
        }

    return pd.DataFrame(results).T


# 使用示例
factor_df = pd.DataFrame(...)  # 行=日期，列=股票代码
ic_results = rolling_ic_analysis(factor_df, periods=[1, 5, 20])
print(ic_results)
```

#### 1.2 IC分析的评估标准

| 指标 | 良好 | 优秀 | 含义 |
|------|------|------|------|
| **IC均值** | > 0.02 | > 0.05 | 因子与收益的正相关性 |
| **ICIR（IC信息比率）** | > 0.3 | > 0.5 | IC的稳定性（均值/标准差） |
| **IC正值比例** | > 55% | > 60% | IC持续为正的比例 |
| **IC t值** | > 2 | > 3 | IC均值的统计显著性 |

---

### 二、分层回测（Quantile Analysis）

分层回测将股票按因子值分为若干组（通常5或10组），观察各组未来收益的单调性：

```python
def quantile_analysis(factor_values, forward_returns, n_quantiles=5):
    """
    分层回测：按因子值分成N组，分析各组收益特征

    参数:
        factor_values: 当期因子值（Series）
        forward_returns: 未来收益率（Series）
        n_quantiles: 分组数量
    """
    df = pd.DataFrame({
        'factor': factor_values,
        'fwd_ret': forward_returns
    }).dropna()

    # 按因子值分位数分组
    df['quantile'] = pd.qcut(df['factor'], n_quantiles,
                              labels=range(1, n_quantiles + 1))

    quantile_stats = df.groupby('quantile')['fwd_ret'].agg([
        ('平均收益', 'mean'),
        ('收益标准差', 'std'),
        ('夏普比率', lambda x: x.mean() / x.std() * np.sqrt(252)),
        ('胜率', lambda x: (x > 0).mean()),
        ('股票数量', 'count')
    ])

    return quantile_stats


def quantile_returns_over_time(factor_df, return_df, n_quantiles=5, period=20):
    """
    计算各分层组的累计收益（用于绘制分层收益曲线）
    """
    dates = sorted(factor_df.index.intersection(return_df.index))
    quantile_returns = {q: [] for q in range(1, n_quantiles + 1)}

    for i, date in enumerate(dates[:-period]):
        factor = factor_df.loc[date]
        fwd_ret = (return_df.shift(-period).loc[date] / return_df.loc[date] - 1)

        df = pd.DataFrame({'factor': factor, 'fwd_ret': fwd_ret}).dropna()
        df['quantile'] = pd.qcut(df['factor'], n_quantiles,
                                  labels=range(1, n_quantiles + 1))

        for q in range(1, n_quantiles + 1):
            avg_ret = df[df['quantile'] == q]['fwd_ret'].mean()
            quantile_returns[q].append((date, avg_ret))

    return quantile_returns
```

> **判断标准**：一个有效因子的分层收益应呈现明显的**单调性**——最高因子值组（Q5）的收益应显著高于最低因子值组（Q1）。此外，多空组合（Top-Bottom组）的收益应显著为正。

---

### 三、因子收益率分析

因子收益率衡量一个标准差的因子暴露能带来多少超额收益。通常使用Fama-MacBeth回归的第二步来计算：

```python
def factor_return_analysis(factor_df, return_df, industry_df=None):
    """
    因子收益率分析（横截面回归法）

    对每个截面期：
    returns_i = α + λ × factor_i + ε_i

    λ即为当期的因子收益率
    """
    dates = sorted(factor_df.index.intersection(return_df.index))
    factor_returns = []

    for date in dates:
        factor = factor_df.loc[date]
        returns = return_df.loc[date]

        valid = ~(factor.isna() | returns.isna())
        factor_clean = factor[valid]
        returns_clean = returns[valid]

        if len(factor_clean) < 20:
            continue

        # 横截面回归：ret = α + λ × factor
        X = np.column_stack([np.ones(len(factor_clean)), factor_clean])
        y = returns_clean.values
        coef = np.linalg.lstsq(X, y, rcond=None)[0]

        factor_returns.append({
            'date': date,
            'alpha': coef[0],
            'factor_return': coef[1]
        })

    fr_df = pd.DataFrame(factor_returns).set_index('date')

    # 因子收益率的t检验
    tstat = fr_df['factor_return'].mean() / \
            (fr_df['factor_return'].std() / np.sqrt(len(fr_df)))

    return {
        'factor_return_mean': fr_df['factor_return'].mean() * 252,     # 年化
        'factor_return_std': fr_df['factor_return'].std() * np.sqrt(252),
        't_statistic': tstat,
        'positive_ratio': (fr_df['factor_return'] > 0).mean()
    }
```

---

### 四、信息比率（Information Ratio）

ICIR（IC信息比率）和因子IR（因子信息比率）共同衡量因子表现的稳定性：

```
ICIR = mean(IC) / std(IC)      —— IC的稳定性
IR   = mean(Alpha) / std(Alpha) —— 超额收益的稳定性
```

### 五、单因子检验汇总框架

```python
def comprehensive_factor_test(factor_df, return_df, name='Factor'):
    """
    单因子综合检验报告
    """
    results = {}

    # 1. IC分析
    ic_result = rolling_ic_analysis(factor_df)
    results['IC分析'] = ic_result

    # 2. 分层回测
    # （取最近一期做演示）
    latest_date = sorted(factor_df.index)[-1]
    quantile = quantile_analysis(
        factor_df.loc[latest_date],
        return_df.loc[latest_date].shift(-1)
    )
    results['分层回测'] = quantile

    # 3. 因子收益率
    fr_result = factor_return_analysis(factor_df, return_df)
    results['因子收益率'] = fr_result

    return results
```

> **关键原则**：单因子检验中，Rank IC的**稳定性**（ICIR）比IC的绝对值更重要。一个IC均值不高但每次都能稳定正IC的因子，远比IC波动巨大的因子有价值——因为它可以被可靠地系统化执行。
