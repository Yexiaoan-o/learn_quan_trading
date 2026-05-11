## 风险价值 VaR

### 什么是VaR

风险价值（Value at Risk，VaR）是金融行业中使用最广泛的风险量化标准之一。它回答了一个极其直观的问题：**在正常的市场条件下，在一定置信水平下，我的投资组合在未来特定时间内最多可能亏损多少钱？**

更形式化地说：

> **VaR**：在给定的持有期 $\Delta t$ 和置信水平 $1-\alpha$ 下，投资组合可能遭受的最大损失为 VaR。即：
> $$P(\text{损失} > \text{VaR}) = \alpha$$

常见的VaR参数设置：
- **置信水平**：95%（标准）、99%（保守）、99.9%（极端保守）
- **持有期**：1天（日常风控）、10天（巴塞尔协议要求）、1个月（长期投资）

举例来说，如果某策略的日度95% VaR 为 50万元，意味着在下一个交易日，该策略只有5%的概率亏损超过50万元。

### VaR的三种计算方法

VaR的计算有三种主流方法，各有优缺点，适用于不同的场景。

#### 1. 参数法（方差-协方差法）

参数法假设收益率服从正态分布，利用均值和标准差直接计算VaR。这是最简单的VaR计算方法。

```
VaR_α = -(μ + z_α × σ) × V₀
```

其中：
- $\mu$：期望收益率
- $\sigma$：收益率标准差
- $z_\alpha$：标准正态分布的分位数（如95%对应 -1.645，99%对应 -2.326）
- $V_0$：初始投资金额

```python
import pandas as pd
import numpy as np
from scipy import stats

def parametric_var(returns: pd.Series, confidence_level: float = 0.95,
                   portfolio_value: float = 1000000, holding_period: int = 1) -> dict:
    """
    参数法计算VaR
    
    Parameters:
    -----------
    returns : pd.Series
        历史日收益率序列
    confidence_level : float
        置信水平（默认95%）
    portfolio_value : float
        组合当前价值
    holding_period : int
        持有天数
    """
    mu = returns.mean()
    sigma = returns.std()
    
    # 标准正态分布的分位数
    z_score = stats.norm.ppf(1 - confidence_level)
    
    # VaR
    var_ratio = -(mu + z_score * sigma) * np.sqrt(holding_period)
    var_amount = var_ratio * portfolio_value
    
    return {
        'VaR_ratio': var_ratio,
        'VaR_amount': var_amount,
        'confidence_level': confidence_level,
        'holding_period': holding_period,
        'method': 'Parametric (Normal)'
    }
```

> **参数法的局限**：金融收益率通常不服从正态分布——它们具有"尖峰厚尾"的特征，即极端事件发生的频率远高于正态分布假设。因此参数法倾向于低估真实的尾部风险。

#### 2. 历史模拟法

历史模拟法不对收益分布做任何假设，而是直接使用历史收益率数据来估计VaR。它假设"历史会在未来重演"——未来的收益率分布与历史一致。

```python
def historical_var(returns: pd.Series, confidence_level: float = 0.95,
                   portfolio_value: float = 1000000, holding_period: int = 1) -> dict:
    """
    历史模拟法计算VaR
    """
    # 获取历史收益率的百分位数
    var_ratio = -np.percentile(returns, 100 * (1 - confidence_level))
    
    # 使用平方根法则扩展到更长的持有期
    var_ratio_period = var_ratio * np.sqrt(holding_period)
    var_amount = var_ratio_period * portfolio_value
    
    return {
        'VaR_ratio': var_ratio_period,
        'VaR_amount': var_amount,
        'confidence_level': confidence_level,
        'holding_period': holding_period,
        'method': 'Historical Simulation'
    }
```

历史模拟法的优缺点：

| 优点 | 缺点 |
|------|------|
| 不需要假设收益分布 | 完全依赖历史数据，无法应对前所未有的情况 |
| 简单直观，易于理解 | 对数据时长敏感——数据太少不可靠，太多可能过时 |
| 捕获了收益序列的实际分布特征 | 不适用于新资产（历史太短） |
| 考虑了厚尾效应 | 假设过去能代表未来，可能过于保守或激进 |

```python
# 历史模拟法进阶：滚动窗口VaR——观察VaR的时变特性
def rolling_historical_var(returns: pd.Series, window: int = 252, 
                            confidence_level: float = 0.95) -> pd.Series:
    """
    计算滚动窗口的历史VaR
    """
    var_series = pd.Series(index=returns.index, dtype=float)
    
    for i in range(window, len(returns)):
        window_returns = returns.iloc[i-window:i]
        var_series.iloc[i] = -np.percentile(window_returns, 100 * (1 - confidence_level))
    
    return var_series
```

#### 3. 蒙特卡洛模拟法

蒙特卡洛模拟法是三者中最为灵活和强大的方法。它通过随机抽样的方式生成大量可能的未来情景，然后从这些情景中提取VaR。该方法可以处理任意复杂的投资组合和非线性产品（如期权）。

```python
def monte_carlo_var(returns: pd.Series, confidence_level: float = 0.95,
                    portfolio_value: float = 1000000, holding_period: int = 1,
                    n_simulations: int = 10000, model: str = 'normal') -> dict:
    """
    蒙特卡洛模拟法计算VaR
    
    Parameters:
    -----------
    model : str
        'normal': 假设正态分布
        't_dist': 使用t分布（厚尾）
        'historical': 从历史中bootstrap抽样
    """
    mu = returns.mean()
    sigma = returns.std()
    df_t = len(returns) - 1  # t分布的自由度
    
    if model == 'normal':
        # 从正态分布抽样
        simulated_returns = np.random.normal(
            mu * holding_period, 
            sigma * np.sqrt(holding_period), 
            n_simulations
        )
    elif model == 't_dist':
        # 从t分布抽样（模拟厚尾）
        simulated_returns = np.random.standard_t(
            df_t, n_simulations
        ) * sigma * np.sqrt(holding_period) + mu * holding_period
    elif model == 'historical':
        # Bootstrap重抽样
        indices = np.random.choice(
            len(returns) - holding_period + 1, 
            n_simulations
        )
        # 计算持有期收益
        simulated_returns = np.array([
            returns.iloc[i:i+holding_period].sum() 
            for i in indices
        ])
    else:
        raise ValueError(f"Unknown model: {model}")
    
    var_ratio = -np.percentile(simulated_returns, 100 * (1 - confidence_level))
    var_amount = var_ratio * portfolio_value
    
    return {
        'VaR_ratio': var_ratio,
        'VaR_amount': var_amount,
        'confidence_level': confidence_level,
        'holding_period': holding_period,
        'n_simulations': n_simulations,
        'simulation_model': model,
        'method': 'Monte Carlo Simulation'
    }
```

#### 三种方法的比较

```python
# 比较三种VaR计算方法
np.random.seed(42)

# 模拟具有厚尾特征的收益率序列
n_days = 1000
normal_returns = np.random.normal(0.0005, 0.015, n_days - 20)
extreme_events = np.random.choice([-0.05, -0.07, -0.03], 20)  # 20个极端日
all_returns = np.concatenate([normal_returns, extreme_events])
np.random.shuffle(all_returns)

returns_series = pd.Series(all_returns)

# 参数法
var_param = parametric_var(returns_series, 0.95, 1000000)
# 历史法
var_hist = historical_var(returns_series, 0.95, 1000000)
# 蒙特卡洛法
var_mc = monte_carlo_var(returns_series, 0.95, 1000000, model='t_dist')

print("不同方法的95%日度VaR比较 (组合价值100万)：")
print(f"参数法:        {var_param['VaR_amount']:,.0f} 元 ({var_param['VaR_ratio']:.2%})")
print(f"历史模拟法:    {var_hist['VaR_amount']:,.0f} 元 ({var_hist['VaR_ratio']:.2%})")
print(f"蒙特卡洛模拟:  {var_mc['VaR_amount']:,.0f} 元 ({var_mc['VaR_ratio']:.2%})")
```

### 进阶VaR指标

#### 条件风险价值（CVaR / Expected Shortfall）

VaR只告诉你在置信水平下的**最小**损失边界，但没有告诉你如果突破了这条边界，损失会有多严重。条件风险价值（Conditional VaR，又称 Expected Shortfall）弥补了这个缺陷：

> **CVaR**：当损失超过VaR时，这些损失的**平均值**是多少。

$$CVaR_\alpha = E[\text{损失} \mid \text{损失} > VaR_\alpha]$$

```python
def conditional_var(returns: pd.Series, confidence_level: float = 0.95,
                    portfolio_value: float = 1000000) -> dict:
    """
    计算条件风险价值（CVaR / Expected Shortfall）
    """
    # 先计算VaR
    var_ratio = -np.percentile(returns, 100 * (1 - confidence_level))
    
    # CVaR：所有超过VaR的损失的平均值
    losses = -returns  # 将收益转为损失
    cvar_ratio = losses[losses >= var_ratio].mean()
    
    return {
        'VaR_ratio': var_ratio,
        'VaR_amount': var_ratio * portfolio_value,
        'CVaR_ratio': cvar_ratio,
        'CVaR_amount': cvar_ratio * portfolio_value,
        'confidence_level': confidence_level
    }

# CVaR 示例
cvar_result = conditional_var(returns_series, 0.95, 1000000)
print(f"\nVaR vs CVaR 比较:")
print(f"95% VaR:  {cvar_result['VaR_amount']:,.0f} 元 ({cvar_result['VaR_ratio']:.2%})")
print(f"95% CVaR: {cvar_result['CVaR_amount']:,.0f} 元 ({cvar_result['CVaR_ratio']:.2%})")
```

#### 边际VaR与增量VaR

当投资组合包含多个资产时，我们需要了解每个资产对组合总风险的贡献：

- **边际VaR（Marginal VaR）**：增加1单位某资产，组合VaR的变化量
- **增量VaR（Incremental VaR）**：新增或移除某资产，组合VaR的整体变化
- **成分VaR（Component VaR）**：每个资产当前持仓对组合VaR的贡献额

```python
def component_var(positions: np.ndarray, returns: pd.DataFrame, 
                  confidence_level: float = 0.95) -> dict:
    """
    计算成分VaR（每个资产对组合VaR的贡献）
    
    positions : np.ndarray
        各资产的持仓金额
    returns : pd.DataFrame
        各资产的日收益率（列=资产）
    """
    cov_matrix = returns.cov()
    portfolio_vol = np.sqrt(positions.T @ cov_matrix @ positions)
    
    # 组合VaR
    z_score = stats.norm.ppf(1 - confidence_level)
    portfolio_var = z_score * portfolio_vol
    
    # 边际VaR: ∂VaR/∂w_i
    marginal_var = z_score * (cov_matrix @ positions) / portfolio_vol
    
    # 成分VaR: w_i × ∂VaR/∂w_i
    component_var_values = positions * marginal_var
    
    # 验证：成分VaR之和应等于组合VaR
    sum_cvar = component_var_values.sum()
    
    return {
        'portfolio_var': portfolio_var,
        'marginal_var': marginal_var,
        'component_var': component_var_values,
        'cvar_pct': component_var_values / portfolio_var * 100,
        'check_sum': sum_cvar
    }
```

### VaR的回测检验

VaR只是一个模型估计，我们需要检验它是否准确。最常见的检验方法是**Kupiec检验**（失败的频率检验）：

如果我们的VaR是95%置信水平，那么我们预期每天约有5%的概率发生"VaR突破"（实际损失超过VaR）。如果在N天中实际发生了X次突破，我们可以检验X/N是否统计上等于5%。

```python
def var_backtest(returns: pd.Series, var_series: pd.Series, 
                 confidence_level: float = 0.95) -> dict:
    """
    VaR回测：检验VaR估计的准确性
    
    var_series: 每日VaR估计值（正数，表示损失的幅度）
    returns: 实际日收益率
    """
    # 计算突破：实际损失是否超过VaR
    actual_losses = -returns  # 正数表示损失
    violations = actual_losses > var_series
    
    n = len(violations)
    n_violations = violations.sum()
    
    # 预期突破次数
    expected_violations = n * (1 - confidence_level)
    
    # Kupiec检验
    p_expected = 1 - confidence_level
    p_actual = n_violations / n
    
    # 似然比检验统计量
    if n_violations == 0:
        lr = -2 * np.log((1 - p_expected) ** n)
    elif n_violations == n:
        lr = -2 * np.log(p_expected ** n)
    else:
        lr = -2 * np.log(
            (p_expected ** n_violations * (1 - p_expected) ** (n - n_violations)) /
            (p_actual ** n_violations * (1 - p_actual) ** (n - n_violations))
        )
    
    # p值（卡方分布，1自由度）
    p_value = 1 - stats.chi2.cdf(lr, 1)
    
    return {
        'total_days': n,
        'violations': n_violations,
        'violation_rate': f"{p_actual:.2%}",
        'expected_violations': expected_violations,
        'expected_rate': f"{p_expected:.2%}",
        'lr_statistic': lr,
        'p_value': p_value,
        'is_valid': p_value > 0.05  # 5%显著性水平
    }
```

### VaR的局限性

尽管VaR在金融行业被广泛使用，它也存在根本性的局限：

1. **不满足次可加性**：两个资产组合的VaR可能大于各自VaR之和——这违反了合理的风险度量应具备的分散化原则

2. **对尾部风险不敏感**：VaR不提供突破置信水平后损失有多严重的信息

3. **依赖历史数据**：历史模拟法和参数法均假设历史会在未来重复

4. **模型风险**：不同的计算方法可能给出差异巨大的VaR值

5. **正常市场假设**：VaR不适用于极端市场条件（金融危机、闪崩等）

> **VaR应该被如何看待？** VaR是风险管理的起点，而不是终点。它提供了一个标准化的风险量化框架，但不应被孤立使用。一个完整的风险管理体系应当结合VaR、CVaR、压力测试和情景分析等多种工具。

### 总结

| 指标 | 适用场景 | 优点 | 缺点 |
|------|---------|------|------|
| 参数法VaR | 简单线性组合、正态分布近似 | 计算快、简单 | 假设过强、低估尾部风险 |
| 历史模拟法VaR | 大多数场景 | 无分布假设、简单 | 依赖历史数据 |
| 蒙特卡洛VaR | 复杂组合、非线性产品 | 灵活、可处理任何分布 | 计算量大、对模型输入敏感 |
| CVaR | 关注尾部极端风险的场景 | 考虑了极端损失的大小 | 估计更不稳定 |
| 成分VaR | 多资产组合分析 | 可追溯风险来源 | 计算相对复杂 |

最后一句话：**VaR告诉你"大概率"每天最多亏多少，但没有告诉你"小概率"下最坏能亏多少。对于后者，你需要压力测试来回答。**
