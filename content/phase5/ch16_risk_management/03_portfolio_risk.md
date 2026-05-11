## 组合风险管理

### 引言

前面两章我们学习了单个策略的风险度量。但在实际量化交易中，通常同时运行多个策略、持有多个资产。组合风险管理（Portfolio Risk Management）正是研究如何在这些策略和资产之间进行有效的风险配置，以达到整体风险与收益的最优平衡。

> **核心思想**：不要把鸡蛋放在一个篮子里。组合风险管理的精髓在于利用资产之间不完全相关（甚至负相关）的特性，在控制整体风险的同时获取分散化的收益流。

本章将深入讨论马科维茨均值-方差优化框架、有效前沿的概念，以及如何在实践中应用这些理论工具。

### 均值-方差优化的理论基础

#### 马科维茨的洞见

1952年，哈里·马科维茨（Harry Markowitz）在他的博士论文中提出了均值-方差优化（Mean-Variance Optimization, MVO）框架，这一工作后来为他赢得了诺贝尔经济学奖。马科维茨的核心洞见是：

1. 投资者关心的不是单个资产的风险和收益，而是**整个投资组合**的期望收益和风险
2. 资产之间的**相关性**是决定组合风险的关键因素——资产之间的相关性越低，组合的风险越低
3. 存在一条"有效前沿"——在这条线上的所有组合，给定风险水平下收益最高，或给定收益水平下风险最低

#### 数学框架

设有 $n$ 个资产，权重向量 $w = (w_1, w_2, ..., w_n)^T$，满足 $\sum w_i = 1$（也不考虑做空的情况）。

- **组合期望收益率**：$\mu_p = w^T \mu = \sum_{i=1}^n w_i \mu_i$
- **组合方差**：$\sigma_p^2 = w^T \Sigma w = \sum_{i=1}^n \sum_{j=1}^n w_i w_j \sigma_{ij}$

其中 $\mu$ 是资产的期望收益率向量，$\Sigma$ 是协方差矩阵。

**优化目标**（两种等价形式）：
1. $\min_w w^T \Sigma w$，subject to $w^T \mu = \mu_{target}$，$\sum w_i = 1$
2. $\max_w w^T \mu$，subject to $w^T \Sigma w = \sigma^2_{target}$，$\sum w_i = 1$

### Python实现：协方差矩阵与有效前沿

#### 准备数据与计算协方差矩阵

```python
import pandas as pd
import numpy as np
from scipy.optimize import minimize
import matplotlib.pyplot as plt

class PortfolioOptimizer:
    """投资组合优化器"""
    
    def __init__(self, returns: pd.DataFrame):
        """
        returns: 多资产的收益率DataFrame（列=资产，行=日期）
        """
        self.returns = returns
        self.n_assets = returns.shape[1]
        self.asset_names = returns.columns.tolist()
        
        # 年化收益率 (252个交易日)
        self.mean_returns = returns.mean() * 252
        # 年化协方差矩阵
        self.cov_matrix = returns.cov() * 252
        
    def portfolio_return(self, weights: np.ndarray) -> float:
        """计算组合年化期望收益率"""
        return np.dot(weights, self.mean_returns)
    
    def portfolio_volatility(self, weights: np.ndarray) -> float:
        """计算组合年化波动率"""
        return np.sqrt(np.dot(weights.T, np.dot(self.cov_matrix, weights)))
    
    def portfolio_sharpe(self, weights: np.ndarray, risk_free_rate: float = 0.03) -> float:
        """计算组合夏普比率"""
        ret = self.portfolio_return(weights)
        vol = self.portfolio_volatility(weights)
        return (ret - risk_free_rate) / vol if vol > 0 else 0
```

#### 构建有效前沿

有效前沿的构建通常通过求解不同目标收益率下的最小方差组合来完成：

```python
def generate_efficient_frontier(self, n_points: int = 50, 
                                 risk_free_rate: float = 0.03):
    """
    生成有效前沿的数据点
    
    方法：对一系列目标收益率，求解最小方差组合
    """
    # 确定收益率范围
    min_ret = self.mean_returns.min()
    max_ret = self.mean_returns.max()
    
    # 等权重组合作为基准
    equal_weights = np.ones(self.n_assets) / self.n_assets
    
    # 计算全局最小方差组合(GMV)
    gmv_weights, gmv_ret, gmv_vol = self.minimum_variance_portfolio()
    
    # 目标收益率范围（从GMV稍低到最高收益率的1.2倍）
    target_returns = np.linspace(
        max(gmv_ret - 0.02, min_ret), 
        max_ret * 1.1, 
        n_points
    )
    
    frontier = []
    for target in target_returns:
        result = self.optimize_for_return(target)
        if result and result[2] > 0:
            frontier.append({
                'volatility': result[2],
                'return': result[1],
                'sharpe': (result[1] - risk_free_rate) / result[2]
            })
    
    return pd.DataFrame(frontier)

def minimum_variance_portfolio(self):
    """计算全局最小方差组合（Global Minimum Variance）"""
    n = self.n_assets
    
    # 目标函数：最小化方差
    def objective(w):
        return self.portfolio_volatility(w)
    
    # 约束条件：权重之和为1
    constraints = [{'type': 'eq', 'fun': lambda w: np.sum(w) - 1}]
    # 权重边界（不允许做空）
    bounds = [(0, 1) for _ in range(n)]
    # 初始猜测（等权重）
    init_guess = np.ones(n) / n
    
    result = minimize(objective, init_guess, method='SLSQP',
                      bounds=bounds, constraints=constraints)
    
    if result.success:
        w = result.x
        return w, self.portfolio_return(w), self.portfolio_volatility(w)
    return None, None, None

def optimize_for_return(self, target_return: float):
    """
    给定目标收益率，求解最小方差组合
    """
    n = self.n_assets
    
    def objective(w):
        return self.portfolio_volatility(w)
    
    constraints = [
        {'type': 'eq', 'fun': lambda w: np.sum(w) - 1},
        {'type': 'eq', 'fun': lambda w: self.portfolio_return(w) - target_return}
    ]
    bounds = [(0, 1) for _ in range(n)]
    init_guess = np.ones(n) / n
    
    result = minimize(objective, init_guess, method='SLSQP',
                      bounds=bounds, constraints=constraints)
    
    if result.success:
        w = result.x
        return w, self.portfolio_return(w), self.portfolio_volatility(w)
    return None, None, None
```

#### 最大夏普比率组合与切线组合

有效前沿上最重要的两个点：

1. **最大夏普比率组合**（Tangency Portfolio）：有效前沿与资本配置线（CAL）的切点
2. **全局最小方差组合**（GMV）：有效前沿最左端的点

```python
def max_sharpe_portfolio(self, risk_free_rate: float = 0.03):
    """
    计算最大夏普比率组合
    """
    n = self.n_assets
    
    # 目标函数：最大化夏普比率（转化为最小化负夏普比率）
    def neg_sharpe(w):
        return -self.portfolio_sharpe(w, risk_free_rate)
    
    constraints = [{'type': 'eq', 'fun': lambda w: np.sum(w) - 1}]
    bounds = [(0, 1) for _ in range(n)]
    init_guess = np.ones(n) / n
    
    result = minimize(neg_sharpe, init_guess, method='SLSQP',
                      bounds=bounds, constraints=constraints)
    
    if result.success:
        w = result.x
        return {
            'weights': dict(zip(self.asset_names, w)),
            'return': self.portfolio_return(w),
            'volatility': self.portfolio_volatility(w),
            'sharpe': self.portfolio_sharpe(w, risk_free_rate)
        }
    return None
```

### 完整示例：有效前沿可视化

```python
def plot_efficient_frontier(optimizer):
    """绘制有效前沿"""
    # 生成有效前沿数据
    frontier = generate_efficient_frontier_data(optimizer)
    
    # 计算关键组合
    gmv_weights, gmv_ret, gmv_vol = optimizer.minimum_variance_portfolio()
    msr = optimizer.max_sharpe_portfolio()
    
    fig, ax = plt.subplots(figsize=(12, 8))
    
    # 有效前沿曲线
    ax.plot(frontier['volatility'] * 100, frontier['return'] * 100, 
            'b-', linewidth=2, label='有效前沿')
    
    # 单个资产
    for i, name in enumerate(optimizer.asset_names):
        vol = np.sqrt(optimizer.cov_matrix.iloc[i, i]) * 100
        ret = optimizer.mean_returns.iloc[i] * 100
        ax.scatter(vol, ret, marker='o', s=100, label=name)
        ax.annotate(name, (vol, ret), textcoords="offset points", xytext=(0,10))
    
    # GMV组合
    ax.scatter(gmv_vol * 100, gmv_ret * 100, marker='*', s=200, 
               color='green', label='全局最小方差组合', zorder=5)
    
    # 最大夏普比率组合
    if msr:
        ax.scatter(msr['volatility'] * 100, msr['return'] * 100, marker='*', 
                   s=200, color='red', label='最大夏普比率组合', zorder=5)
    
    ax.set_xlabel('年化波动率 (%)')
    ax.set_ylabel('年化收益率 (%)')
    ax.set_title('马科维茨有效前沿')
    ax.legend()
    ax.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.show()

def generate_efficient_frontier_data(optimizer, n_points=100):
    """
    生成有效前沿的所有数据点
    """
    # 计算最小和最大收益
    gmv_weights, gmv_ret, gmv_vol = optimizer.minimum_variance_portfolio()
    
    # 目标收益率
    target_rets = np.linspace(
        gmv_ret,
        optimizer.mean_returns.max() * 1.05,
        n_points
    )
    
    data = []
    for tar in target_rets:
        w, ret, vol = optimizer.optimize_for_return(tar)
        if ret and vol:
            data.append({'volatility': vol, 'return': ret})
    
    return pd.DataFrame(data)

# 使用示例（需要使用实际资产数据）
# 假设我们有4个资产的收益率数据
np.random.seed(42)
dates = pd.date_range('2018-01-01', '2022-12-31', freq='B')
n = len(dates)

# 生成模拟的4个资产收益率
assets_returns = pd.DataFrame({
    '股票A': np.random.normal(0.0008, 0.018, n),
    '债券B': np.random.normal(0.0003, 0.005, n),
    '黄金C': np.random.normal(0.0004, 0.012, n),
    '房地产D': np.random.normal(0.0006, 0.015, n)
}, index=dates)

optimizer = PortfolioOptimizer(assets_returns)
```

### 黑-利特曼模型（Black-Litterman）

马科维茨MVO一个主要的问题是输入敏感——对期望收益率的微小变化，最优权重可能发生剧烈变化。此外，MVO经常建议"极端"的权重分配（高度集中）。

**黑-利特曼（Black-Litterman）模型**是MVO的一种改进，它：

1. 以市场均衡权重（市值权重）为起点
2. 允许投资者将自己的主观观点融入模型
3. 输出"后验"期望收益率——市场均衡与主观观点的加权平均

```python
def black_litterman(market_weights: np.ndarray, cov_matrix: np.ndarray,
                    risk_aversion: float = 2.5,
                    views_P: np.ndarray = None, views_Q: np.ndarray = None,
                    views_omega: np.ndarray = None) -> np.ndarray:
    """
    简化的Black-Litterman模型
    
    Parameters:
    -----------
    market_weights : 市场均衡权重（如市值权重）
    cov_matrix : 协方差矩阵
    risk_aversion : 风险厌恶系数 (2.5为标准值)
    views_P : K×N的"pick矩阵"，每行定义一个观点的资产选择
    views_Q : K维向量，每个观点的期望超额收益
    views_omega : K×K的对角矩阵，观点的置信度
    
    Returns:
    --------
    posterior_returns : 后验期望收益率
    posterior_weights : 后验最优权重
    """
    # 隐含均衡收益率: π = λ × Σ × w_market
    pi = risk_aversion * cov_matrix @ market_weights
    
    if views_P is None or views_Q is None:
        # 没有主观观点，直接使用均衡收益率
        posterior_returns = pi
    else:
        # 后验收益率
        tau = 0.05  # 均衡收益的不确定性参数
        
        if views_omega is None:
            # 默认：观点的不确定性与均衡收益率的不确定性同比例
            views_omega = np.diag(np.diag(views_P @ (tau * cov_matrix) @ views_P.T))
        
        # Black-Litterman公式
        middle = np.linalg.inv(
            np.linalg.inv(tau * cov_matrix) + 
            views_P.T @ np.linalg.inv(views_omega) @ views_P
        )
        
        posterior_returns = middle @ (
            np.linalg.inv(tau * cov_matrix) @ pi + 
            views_P.T @ np.linalg.inv(views_omega) @ views_Q
        )
    
    # 使用后验收益率计算最优权重
    n = len(posterior_returns)
    inv_cov = np.linalg.inv(cov_matrix)
    posterior_weights = inv_cov @ posterior_returns / risk_aversion
    posterior_weights = posterior_weights / posterior_weights.sum()
    # Clip以确保非负
    posterior_weights = np.clip(posterior_weights, 0, 1)
    posterior_weights = posterior_weights / posterior_weights.sum()
    
    return posterior_returns, posterior_weights
```

### 风险平价策略

风险平价（Risk Parity）是另一种重要的组合构建方法，它追求的不是等权重，而是**等风险贡献**——每个资产对组合总风险的贡献相等。

```python
def risk_parity_weights(cov_matrix: np.ndarray) -> np.ndarray:
    """
    计算风险平价权重（各资产的风险贡献相等）
    
    cov_matrix : 协方差矩阵
    """
    n = cov_matrix.shape[0]
    
    def risk_budget_objective(weights):
        # 组合波动率
        portfolio_var = weights.T @ cov_matrix @ weights
        portfolio_vol = np.sqrt(portfolio_var)
        
        # 边际风险贡献
        marginal_contrib = cov_matrix @ weights
        
        # 风险贡献
        risk_contrib = weights * marginal_contrib / portfolio_vol
        
        # 目标：各资产风险贡献相等 → 最小化风险贡献的方差
        target_contrib = portfolio_vol / n
        error = np.sum((risk_contrib - target_contrib) ** 2)
        
        return error
    
    constraints = [{'type': 'eq', 'fun': lambda w: np.sum(w) - 1}]
    bounds = [(0, 1) for _ in range(n)]
    init_guess = np.ones(n) / n
    
    result = minimize(risk_budget_objective, init_guess, method='SLSQP',
                      bounds=bounds, constraints=constraints)
    
    return result.x if result.success else init_guess
```

### 再平衡策略

在实际操作中，组合权重会随市场价格变化而漂移，需要定期再平衡：

```python
class PortfolioRebalancer:
    """投资组合再平衡器"""
    
    @staticmethod
    def calendar_rebalance(current_weights: np.ndarray, target_weights: np.ndarray,
                           prices: np.ndarray, portfolio_value: float,
                           max_turnover: float = 1.0):
        """
        定期再平衡（日历再平衡）
        
        max_turnover: 最大换手率限制
        """
        current_values = current_weights * portfolio_value
        target_values = target_weights * portfolio_value
        trades = target_values - current_values
        
        # 计算换手率
        turnover = abs(trades).sum() / portfolio_value / 2
        
        if turnover > max_turnover:
            # 如果换手率超过限制，按比例缩减
            trades = trades * (max_turnover / turnover)
        
        return trades
    
    @staticmethod
    def threshold_rebalance(current_weights: np.ndarray, target_weights: np.ndarray,
                            threshold: float = 0.05):
        """
        阈值再平衡：仅当实际权重偏离目标超过阈值时才调仓
        """
        deviations = abs(current_weights - target_weights)
        trade_mask = deviations > threshold
        
        trades = np.where(trade_mask, target_weights - current_weights, 0)
        
        return trades
```

### 组合风险监控

在组合运行期间，持续监控风险指标至关重要：

```python
class PortfolioRiskMonitor:
    """组合风险监控"""
    
    def __init__(self, returns_history: pd.DataFrame, current_weights: np.ndarray):
        self.returns_history = returns_history
        self.weights = current_weights
        self.cov_matrix = returns_history.cov() * 252
    
    def calculate_current_risk(self) -> dict:
        """计算当前组合的风险指标"""
        port_vol = np.sqrt(self.weights.T @ self.cov_matrix @ self.weights)
        port_ret = (self.returns_history.mean() * 252) @ self.weights
        
        # 边际VaR
        z_99 = 2.33  # 99%置信水平
        marginal_var = z_99 * (self.cov_matrix @ self.weights) / port_vol
        component_var = self.weights * marginal_var
        
        # 最大5个风险贡献者
        risk_contributions = pd.Series(component_var, index=self.returns_history.columns)
        top_contributors = risk_contributions.nlargest(5)
        
        # 分散化比率
        asset_vols = np.sqrt(np.diag(self.cov_matrix))
        weighted_avg_vol = np.dot(self.weights, asset_vols)
        diversification_ratio = weighted_avg_vol / port_vol if port_vol > 0 else 1
        
        return {
            'portfolio_volatility': port_vol,
            'portfolio_return': port_ret,
            'diversification_ratio': diversification_ratio,
            'top_risk_contributors': top_contributors.to_dict(),
            'total_risk': component_var.sum(),
            'risk_concentration': (risk_contributions.max() / component_var.sum())
        }
    
    def stress_test(self, scenarios: dict) -> dict:
        """
        压力测试
        
        scenarios: {场景名称: 收益率冲击向量}
        例如: {'market_crash': np.array([-0.08, -0.02, -0.03, -0.05])}
        """
        results = {}
        for name, shocks in scenarios.items():
            pnl = np.dot(self.weights, shocks)
            results[name] = {
                'pnl_pct': pnl * 100,
                'pnl_is_breach': abs(pnl) > 0.10  # 是否超过10%阈值
            }
        return results
```

### 总结

组合风险管理是一门将理论化为实践的艺术。从马科维茨的均值-方差框架到现代的风险平價策略，核心原则始终不变：

1. **分散化是降低风险的最有效手段**——但必须选择相关性低的资产
2. **不要只看收益率**——高收益往往以高风险为代价
3. **关注相关性**——在危机时期，资产之间的相关性往往会上升，削弱分散化效果
4. **定期再平衡**——组合权重会随时间漂移，需要定期检查和调整
5. **保持警惕**——历史数据有其局限性，需要对极端情景保持敬畏

> **最后的忠告**：没有任何模型能够完美预测未来。组合风险管理不是追求完美的数学最优解，而是在不完全信息的基础上做出稳健、可执行的决策。保持组合的简单性和可解释性，往往比追求理论上的最优更重要。
