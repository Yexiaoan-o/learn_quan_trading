## Alpha与Beta的基本概念

在量化投资中，Alpha和Beta是两个最基础也最重要的收益分解概念。理解它们之间的关系，是构建专业量化策略的基石。

### 什么是Beta？

**Beta（β）** 衡量投资组合相对于市场基准（通常是大盘指数）的系统性风险暴露程度，即"市场给你的收益"。

Beta的计算公式：

```
β = Cov(R_p, R_m) / Var(R_m)
```

其中：
- Cov(R_p, R_m)：投资组合收益率与市场收益率之间的协方差
- Var(R_m)：市场收益率的方差

**Beta的解读：**

| Beta值 | 含义 | 说明 |
|--------|------|------|
| β = 1 | 与市场同步波动 | 市场涨1%，组合也涨1% |
| β > 1 | 比市场波动更大 | 进攻型资产，如科技股 |
| 0 < β < 1 | 比市场波动更小 | 防御型资产，如公用事业 |
| β = 0 | 与市场无关 | 如现金或无风险资产 |
| β < 0 | 与市场反向波动 | 对冲工具，如做空ETF |

### 什么是Alpha？

**Alpha（α）** 衡量投资组合超越市场基准的超额收益，即"你凭能力赚的收益"。Alpha是CAPM模型中不能被市场风险解释的那部分收益。

CAPM（资本资产定价模型）的基本公式：

```
R_p - R_f = α + β × (R_m - R_f) + ε
```

其中：
- R_p：投资组合收益率
- R_f：无风险利率
- R_m：市场收益率
- α：超额收益（Alpha）
- β：系统性风险暴露（Beta）
- ε：随机误差项（期望值为0）

> **核心思想**：CAPM告诉我们，一个资产的预期收益应当等于无风险利率加上对该资产承担的系统性风险的补偿。任何超出这个"公平"补偿的收益就是Alpha。

### Alpha和Beta的计算实践

```python
import numpy as np
import pandas as pd
from scipy import stats

def calculate_alpha_beta(portfolio_returns, market_returns, risk_free_rate=0.03):
    """
    计算投资组合的Alpha和Beta
    
    参数:
        portfolio_returns: 组合日收益率序列
        market_returns: 市场日收益率序列
        risk_free_rate: 年化无风险利率 (默认3%)
    """
    # 日化无风险利率
    rf_daily = risk_free_rate / 252
    
    # 超额收益
    portfolio_excess = portfolio_returns - rf_daily
    market_excess = market_returns - rf_daily
    
    # 确保数据对齐
    common_idx = portfolio_excess.index.intersection(market_excess.index)
    y = portfolio_excess[common_idx].values
    X = market_excess[common_idx].values
    
    # 线性回归：y = alpha + beta * X
    X_with_const = np.column_stack([np.ones(len(X)), X])
    
    # 使用OLS估计
    beta_matrix = np.linalg.inv(X_with_const.T @ X_with_const) @ X_with_const.T @ y
    alpha_daily = beta_matrix[0]
    beta = beta_matrix[1]
    
    # 年化Alpha
    alpha_annual = alpha_daily * 252
    
    # 计算统计量
    residuals = y - (alpha_daily + beta * X)
    
    # R-squared（由Beta解释的收益比例）
    ss_total = np.sum((y - y.mean()) ** 2)
    ss_residual = np.sum(residuals ** 2)
    r_squared = 1 - (ss_residual / ss_total)
    
    # Alpha的t统计量（检验Alpha是否显著不为0）
    n = len(y)
    se_alpha = np.sqrt(ss_residual / (n - 2) / np.sum((X_with_const[:, 0] - X_with_const[:, 0].mean()) ** 2))
    # 更准确的Alpha标准误
    X_var = np.cov(X_with_const.T)
    se_matrix = np.sqrt(ss_residual / (n - 2) * np.linalg.inv(X_with_const.T @ X_with_const))
    t_stat_alpha = alpha_daily / se_matrix[0, 0]
    
    # 信息比率
    tracking_error = np.std(residuals) * np.sqrt(252)
    information_ratio = alpha_annual / tracking_error if tracking_error != 0 else 0
    
    return {
        'alpha_daily': alpha_daily,
        'alpha_annual': alpha_annual,
        'beta': beta,
        'r_squared': r_squared,
        't_stat_alpha': t_stat_alpha,
        'information_ratio': information_ratio,
        'tracking_error': tracking_error,
        'residuals': residuals
    }


def rolling_alpha_beta(portfolio_returns, market_returns, window=252):
    """
    计算滚动窗口的Alpha和Beta
    用于观察Alpha和Beta的时变特性
    """
    rolling_betas = []
    rolling_alphas = []
    dates = []
    
    for i in range(window, len(portfolio_returns) + 1):
        port_slice = portfolio_returns.iloc[i-window:i]
        mkt_slice = market_returns.iloc[i-window:i]
        
        result = calculate_alpha_beta(port_slice, mkt_slice)
        rolling_betas.append(result['beta'])
        rolling_alphas.append(result['alpha_annual'])
        dates.append(portfolio_returns.index[i-1])
    
    return pd.DataFrame({
        'date': dates,
        'beta': rolling_betas,
        'alpha': rolling_alphas
    }).set_index('date')
```

### 收益归因分析

理解了Alpha和Beta之后，我们可以对任意策略的收益进行归因分解：

```python
def performance_attribution(portfolio_returns, factor_returns, factor_names):
    """
    多因子收益归因分析
    
    参数:
        portfolio_returns: 组合收益率序列
        factor_returns: 因子收益率DataFrame (各列是一个因子)
        factor_names: 因子名称列表
    """
    # 对齐数据
    common_idx = portfolio_returns.index.intersection(factor_returns.index)
    y = portfolio_returns[common_idx].values
    X = factor_returns.loc[common_idx, factor_names].values
    
    # 添加常数项（Alpha）
    X = np.column_stack([np.ones(len(y)), X])
    
    # OLS回归
    coef = np.linalg.inv(X.T @ X) @ X.T @ y
    alpha = coef[0] * 252  # 年化Alpha
    exposures = coef[1:]   # 各因子暴露（Beta）
    
    # 各因子的收益贡献
    factor_contributions = {}
    for i, name in enumerate(factor_names):
        daily_contrib = X[:, i+1] * exposures[i]
        annual_contrib = np.mean(daily_contrib) * 252
        factor_contributions[name] = {
            'exposure': exposures[i],
            'annual_contribution': annual_contrib
        }
    
    total_factor_return = sum(
        fc['annual_contribution'] for fc in factor_contributions.values()
    )
    total_return = np.mean(y) * 252
    
    return {
        'total_annual_return': total_return,
        'alpha': alpha,
        'factor_returns': total_factor_return,
        'factor_details': factor_contributions,
        'unexplained': total_return - alpha - total_factor_return
    }
```

### Alpha的四种类型

在实际量化投资中，Alpha可以细分为多种类型：

| Alpha类型 | 来源 | 特点 | 持续性 |
|-----------|------|------|--------|
| **纯Alpha** | 选股/择时能力 | 与市场和因子无关的收益 | 最稀缺 |
| **因子Alpha** | 因子暴露 | 通过配置特定因子获取超额收益 | 取决于因子持续性 |
| **统计Alpha** | 统计关系 | 配对交易、统计套利等 | 可能衰减 |
| **结构Alpha** | 市场结构 | 利用交易规则、市场微观结构 | 随市场演化 |

### 市场中性组合

实现Alpha收益的一种常见方法是通过构建市场中性组合来"剥离"Beta：

```python
def build_market_neutral_portfolio(long_portfolio, short_portfolio, 
                                     long_beta, short_beta, 
                                     target_beta=0.0):
    """
    构建市场中性组合
    
    原理：通过调整多空比例，使组合整体Beta为0
    """
    # 要使组合Beta = w_long * long_beta - w_short * short_beta = target_beta
    # w_long + w_short = 1
    
    # 解方程组
    # target_beta = w_long * long_beta - (1 - w_long) * short_beta
    # target_beta = w_long * long_beta - short_beta + w_long * short_beta
    # target_beta + short_beta = w_long * (long_beta + short_beta)
    
    w_long = (target_beta + short_beta) / (long_beta + short_beta) if (long_beta + short_beta) != 0 else 0.5
    w_long = max(0, min(1, w_long))  # 约束在0-1之间
    w_short = 1 - w_long
    
    # 验证组合Beta
    portfolio_beta = w_long * long_beta - w_short * short_beta
    
    return {
        'long_weight': w_long,
        'short_weight': w_short,
        'portfolio_beta': portfolio_beta
    }
```

### 信息比率与Alpha的关系

**信息比率（Information Ratio, IR）** 是衡量Alpha质量的核心指标：

```
IR = Alpha / Tracking Error = (R_p - R_b) / σ(R_p - R_b)
```

| IR范围 | 评价 |
|--------|------|
| IR < 0 | Alpha为负，跑输基准 |
| 0 < IR < 0.5 | 平庸水平 |
| 0.5 < IR < 1.0 | 良好水平 |
| IR > 1.0 | 优秀水平 |

> **投资智慧**：在业界，IR > 0.5的策略已属不错，IR > 1.0的策略相当优秀。大多数专业基金经理的IR在0.3-0.8之间。对于一个量化策略，追求高IR比追求高Alpha更有意义，因为IR同时考虑了收益和风险。

### 常见误区

1. **高Alpha但低t值**：可能是运气，不是能力。应关注Alpha的统计显著性。
2. **忽略Beta的变化**：Beta不是常数，它会随市场环境变化。使用滚动Beta估计更合理。
3. **幸存者偏差**：只看成功的策略，忽略了大量失败的尝试。
4. **把市场收益当Alpha**：在牛市中简单的做多策略收益很高，但那不是Alpha，只是Beta。
