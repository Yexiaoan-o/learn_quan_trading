## 动量策略（Momentum Strategy）概述

动量策略是量化投资中最经典的因子策略之一。它的核心思想来自诺贝尔经济学奖得主Eugene Fama和Kenneth French的研究：资产价格存在动量效应——过去表现好的资产在未来一段时间内倾向于继续表现好，过去表现差的资产倾向于继续表现差。

### 动量效应的理论基础

动量效应的存在挑战了有效市场假说（EMH），学术界提出了以下解释：

| 理论解释 | 核心观点 |
|----------|----------|
| 反应不足 | 投资者对新信息的反应不够迅速，导致价格调整缓慢 |
| 过度反应 | 正反馈交易者追涨杀跌，导致价格延续趋势 |
| 行为偏差 | 锚定效应、处置效应等行为偏差导致价格动量 |
| 风险补偿 | 动量收益是对承担某种系统性风险的补偿 |

---

### 一、动量因子的计算

#### 基础动量因子

动量因子最常见的计算方式是过去N个月的累积收益率（跳过最近1个月以避免短期反转效应）。

```python
import numpy as np
import pandas as pd
from scipy import stats


def calculate_momentum_factor(prices, lookback_months=12, skip_months=1):
    """
    计算动量因子
    
    使用过去lookback_months个月的收益率（跳过最近skip_months个月）
    这是学术界最标准的动量因子定义（Jegadeesh & Titman, 1993）
    
    参数:
        prices: DataFrame, 行=日期, 列=股票代码, 值=价格
        lookback_months: 回看月数 (默认12)
        skip_months: 跳过最近月数 (默认1)
    """
    # 对于日频数据，转换为月频
    monthly_prices = prices.resample('M').last()
    
    # 计算动量 = 当前价格 / lookback_months个月前的价格 - 1
    # 跳过最近skip_months个月
    skipped_prices = monthly_prices.shift(skip_months)
    past_prices = monthly_prices.shift(lookback_months + skip_months)
    
    momentum = skipped_prices / past_prices - 1
    
    return momentum


def calculate_momentum_multiple_windows(prices, windows=[1, 3, 6, 12]):
    """
    计算多个时间窗口的动量因子
    
    返回每个窗口的动量和综合动量得分
    """
    momentums = {}
    
    for w in windows:
        momentums[f'mom_{w}m'] = prices.pct_change(21 * w)  # 约21个交易日/月
        
    momentum_df = pd.DataFrame(momentums)
    
    # 综合动量得分（多个窗口的平均排名）
    rank_df = momentum_df.rank(axis=1, pct=True)
    momentum_df['composite_momentum'] = rank_df.mean(axis=1)
    
    return momentum_df
```

#### 残差动量因子

残差动量剥离了市场Beta的影响，更纯粹地捕捉个股的特质动量。

```python
def calculate_residual_momentum(prices, market_prices, 
                                  lookback=252, window=60):
    """
    计算残差动量（特质动量）
    
    步骤：
    1. 对每只股票，用市场收益回归
    2. 残差即为特质收益
    3. 计算特质收益的动量
    
    参数:
        prices: 个股价格
        market_prices: 市场指数价格
        lookback: 回归窗口
        window: 动量计算窗口
    """
    returns = prices.pct_change().dropna()
    market_returns = market_prices.pct_change().dropna()
    
    residuals = pd.DataFrame(index=returns.index, columns=returns.columns)
    
    for stock in returns.columns:
        # 与市场收益做滚动回归
        common_idx = returns.index.intersection(market_returns.index)
        stock_ret = returns.loc[common_idx, stock]
        mkt_ret = market_returns.loc[common_idx]
        
        for t in range(lookback, len(stock_ret)):
            y = stock_ret.iloc[t-lookback:t].values
            X = np.column_stack([np.ones(lookback), mkt_ret.iloc[t-lookback:t].values])
            
            beta = np.linalg.lstsq(X, y, rcond=None)[0]
            pred = X[-1] @ beta
            residuals.iloc[t, returns.columns.get_loc(stock)] = y[-1] - pred
    
    # 计算残差的动量
    residual_momentum = residuals.rolling(window).sum()
    
    return residual_momentum
```

---

### 二、动量因子的排名与分组

计算出动量因子后，需要对股票进行排名和分组：

```python
def construct_momentum_portfolios(momentum_values, n_groups=10):
    """
    根据动量因子构建分组组合
    
    参数:
        momentum_values: Series或数组，各股票的动量值
        n_groups: 分组数量 (默认10组)
    
    返回:
        groups: 每只股票所属的组号 (1=最低动量, n_groups=最高动量)
    """
    # 使用百分位排名
    percentiles = pd.qcut(momentum_values, q=n_groups, labels=False, 
                           duplicates='drop') + 1
    
    return percentiles


def top_bottom_portfolio(momentum_values, top_pct=0.2, bottom_pct=0.2):
    """
    构建多空组合：做多前top_pct的股票，做空后bottom_pct的股票
    
    返回:
        long_stocks: 做多股票列表
        short_stocks: 做空股票列表
    """
    n = len(momentum_values)
    sorted_mom = momentum_values.sort_values()
    
    n_short = int(n * bottom_pct)
    n_long = int(n * top_pct)
    
    short_stocks = sorted_mom.index[:n_short].tolist()
    long_stocks = sorted_mom.index[-n_long:].tolist()
    
    return long_stocks, short_stocks
```

---

### 三、动量策略的组合构建

```python
class MomentumStrategy:
    """
    动量策略实现
    
    支持两种加权方式：
    1. 等权 - 入选股票等权重
    2. 动加权 - 按动量值加权
    """
    
    def __init__(self, lookback=252, n_stocks=20, rebalance_freq=21,
                 weighting='equal', use_residual=False):
        self.lookback = lookback
        self.n_stocks = n_stocks
        self.rebalance_freq = rebalance_freq
        self.weighting = weighting
        self.use_residual = use_residual
    
    def select_stocks(self, prices, current_date):
        """
        选股：选取动量最强的n_stocks只股票
        
        参数:
            prices: 历史价格DataFrame
            current_date: 当前调仓日期
        """
        # 获取截止到current_date的价格数据
        hist_prices = prices.loc[:current_date]
        
        if len(hist_prices) < self.lookback:
            return None
        
        # 计算动量（过去lookback个交易日的收益率）
        start_prices = hist_prices.iloc[-self.lookback]
        end_prices = hist_prices.iloc[-1]
        momentum = (end_prices / start_prices - 1)
        
        # 剔除NaN
        momentum = momentum.dropna()
        
        # 选取动量最强的n_stocks只
        top_stocks = momentum.nlargest(self.n_stocks)
        
        return top_stocks
    
    def calculate_weights(self, momentum_values):
        """
        计算持仓权重
        """
        if self.weighting == 'equal':
            weights = pd.Series(1.0 / len(momentum_values), 
                               index=momentum_values.index)
        elif self.weighting == 'momentum':
            # 动量值归一化为权重
            min_val = momentum_values.min()
            max_val = momentum_values.max()
            if max_val > min_val:
                norm_values = (momentum_values - min_val) / (max_val - min_val)
            else:
                norm_values = pd.Series(0.5, index=momentum_values.index)
            weights = norm_values / norm_values.sum()
        elif self.weighting == 'rank':
            # 排名加权：排名越高权重越大
            ranks = momentum_values.rank(ascending=True)
            weights = ranks / ranks.sum()
        else:
            raise ValueError(f"不支持的加权方式: {self.weighting}")
        
        return weights
    
    def run_backtest(self, prices, start_date=None, end_date=None):
        """
        动量策略回测
        """
        if start_date is None:
            start_date = prices.index[self.lookback]
        if end_date is None:
            end_date = prices.index[-1]
        
        # 生成调仓日期
        rebalance_dates = prices.loc[start_date:end_date].index[::self.rebalance_freq]
        
        portfolio_values = []
        holdings_log = []
        
        for i, rebalance_date in enumerate(rebalance_dates):
            # 选股
            selected = self.select_stocks(prices, rebalance_date)
            
            if selected is None or len(selected) == 0:
                continue
            
            # 计算权重
            weights = self.calculate_weights(selected)
            
            # 记录持仓
            holdings_log.append({
                'date': rebalance_date,
                'stocks': selected.index.tolist(),
                'weights': weights.to_dict()
            })
        
        # 计算组合净值
        # (简化处理，实际回测需要逐日计算)
        
        return holdings_log
```

### 四、动量策略的风险管理

动量策略存在"动量崩溃"风险——在市场剧烈反转时动量策略会遭受重大损失。

```python
def momentum_crash_protection(returns, vol_threshold=0.4, 
                                momentum_threshold=0.15):
    """
    动量崩溃保护
    
    检测条件：
    1. 高波动率环境
    2. 动量因子的极端历史表现
    
    当检测到危险信号时，降低动量因子的权重
    """
    # 计算近期波动率
    recent_vol = returns.rolling(21).std() * np.sqrt(252)
    
    # 计算动量的极端程度
    momentum_strategy_ret = returns.mean(axis=1)  # 多空组合日收益
    rolling_mom = momentum_strategy_ret.rolling(63).sum()  # 过去3个月累计
    
    # 危险信号
    high_vol = recent_vol > vol_threshold
    extreme_momentum = abs(rolling_mom) > momentum_threshold
    
    # 仓位缩放因子（0到1之间）
    scale_factor = pd.Series(1.0, index=returns.index)
    scale_factor[high_vol | extreme_momentum] = 0.5
    scale_factor[high_vol & extreme_momentum] = 0.0  # 完全平仓
    
    return scale_factor
```

### 五、动量策略绩效评估

```python
def evaluate_momentum_performance(portfolio_returns, benchmark_returns=None):
    """
    动量策略绩效评估
    """
    n_days = len(portfolio_returns)
    n_years = n_days / 252
    
    # 累计收益
    cumulative = (1 + portfolio_returns).cumprod()
    
    # 年化指标
    annual_return = float(cumulative.iloc[-1] ** (1/n_years) - 1)
    annual_vol = float(portfolio_returns.std() * np.sqrt(252))
    sharpe = float(annual_return / annual_vol) if annual_vol > 0 else 0
    
    # 最大回撤
    rolling_max = cumulative.cummax()
    drawdown = (cumulative - rolling_max) / rolling_max
    max_dd = float(drawdown.min())
    
    # 超额收益（如果有基准）
    if benchmark_returns is not None:
        excess = portfolio_returns - benchmark_returns
        tracking_error = float(excess.std() * np.sqrt(252))
        info_ratio = float(excess.mean() / excess.std() * np.sqrt(252))
    else:
        tracking_error = None
        info_ratio = None
    
    return {
        '年化收益率': f'{annual_return:.2%}',
        '年化波动率': f'{annual_vol:.2%}',
        '夏普比率': f'{sharpe:.2f}',
        '最大回撤': f'{max_dd:.2%}',
        '跟踪误差': f'{tracking_error:.2%}' if tracking_error else 'N/A',
        '信息比率': f'{info_ratio:.2f}' if info_ratio else 'N/A',
    }
```

> **动量策略的核心经验**：动量效应在全球主要市场中普遍存在，但并非每月都能盈利。理解动量策略何时表现最好（市场缓慢上升阶段）和最差（市场急速反转阶段）同样重要。大多数专业量化基金将动量作为多因子体系中的一个因子，而不是唯一的策略依据。
