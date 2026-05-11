## 仓位管理的核心意义

仓位管理（Position Sizing）是量化交易中决定"每次交易投入多少资金"的科学。许多交易者只关注"何时买卖"，却忽视"买卖多少"，这往往是盈利策略变成亏损策略的根本原因。

> **关键认知**：入场时机决定你能不能赚钱，仓位大小决定你能赚多少或亏多少。优秀的仓位管理可以让一个普通策略变得稳健，糟糕的仓位管理可以让一个优秀策略血本无归。

### 仓位管理的基本要素

| 要素 | 说明 |
|------|------|
| 账户权益 (Equity) | 账户当前总价值 |
| 风险预算 (Risk Budget) | 单笔交易愿承受的最大亏损比例 |
| 波动率 (Volatility) | 标的资产的价格波动程度 |
| 相关性 (Correlation) | 多个持仓之间的相关关系 |
| 流动性 (Liquidity) | 标的资产的交易量，决定最大可持仓 |

### 一、等权重法

等权重法是最简单的仓位分配方法：将总资金平均分配到每笔交易或每个标的上。

```python
def equal_weight_position(total_capital, n_positions, price, max_position_pct=1.0):
    """
    等权重仓位计算
    
    参数:
        total_capital: 总资金
        n_positions: 持仓数量
        price: 当前价格
        max_position_pct: 最大仓位比例（默认100%，即满仓）
    """
    position_value = (total_capital / n_positions) * max_position_pct
    shares = int(position_value / price)
    
    return {
        'shares': shares,
        'position_value': shares * price,
        'weight': 1.0 / n_positions * max_position_pct
    }


def equal_weight_rebalance(holdings, prices, total_capital, target_weights=None):
    """
    等权重再平衡
    当持仓偏离目标权重时，计算需要调整的股数
    
    参数:
        holdings: 当前持仓股数字典 {'AAPL': 100, 'GOOG': 50}
        prices: 当前价格字典 {'AAPL': 150.0, 'GOOG': 2800.0}
        total_capital: 总资金
        target_weights: 目标权重（默认为等权重）
    """
    n = len(holdings)
    if target_weights is None:
        target_weights = {sym: 1/n for sym in holdings}
    
    orders = {}
    for symbol in holdings:
        current_value = holdings[symbol] * prices[symbol]
        target_value = total_capital * target_weights[symbol]
        diff_value = target_value - current_value
        diff_shares = int(diff_value / prices[symbol])
        
        if diff_shares != 0:
            orders[symbol] = diff_shares  # 正数为买入，负数为卖出
    
    return orders
```

等权重法的优缺点：

| 优点 | 缺点 |
|------|------|
| 实现简单，容易理解 | 不考虑各资产的波动特性 |
| 天然具有分散化效果 | 高波动资产和低波动资产承担相同权重 |
| 定期再平衡有"低买高卖"效果 | 未利用收益信号的信息 |

---

### 二、凯利公式 (Kelly Criterion)

凯利公式是约翰·凯利于1956年提出的资金管理公式，旨在最大化长期资金的几何增长率。

#### 基础凯利公式

对于简单的二元结果（赢或输）的赌局：

```
f* = (p * b - q) / b
```

其中：
- f*：应投入资金的最优比例
- p：胜率（获胜的概率）
- b：赔率（获胜时的收益/亏损时的损失）
- q：亏损概率 = 1 - p

```python
def kelly_criterion(win_prob, win_loss_ratio):
    """
    基础凯利公式
    
    参数:
        win_prob: 胜率 (0-1)
        win_loss_ratio: 盈亏比（平均盈利/平均亏损）
    
    返回:
        最优投资比例 f*
    """
    # f* = (p * b - (1-p)) / b = p - (1-p)/b
    f_star = win_prob - (1 - win_prob) / win_loss_ratio
    
    return f_star


def kelly_example():
    """
    凯利公式示例
    """
    # 场景1：胜率60%，盈亏比2:1
    f1 = kelly_criterion(0.6, 2.0)
    print(f"胜率60%, 盈亏比2:1 -> 凯利比例 = {f1:.2%}")
    # 输出: 40%
    
    # 场景2：胜率50%，盈亏比3:1
    f2 = kelly_criterion(0.5, 3.0)
    print(f"胜率50%, 盈亏比3:1 -> 凯利比例 = {f2:.2%}")
    # 输出: 33.3%
    
    # 场景3：胜率30%，盈亏比5:1
    f3 = kelly_criterion(0.3, 5.0)
    print(f"胜率30%, 盈亏比5:1 -> 凯利比例 = {f3:.2%}")
    # 输出: 16%

    # 注意：当f*为负数时，说明不应该参与这个"赌局"
    f4 = kelly_criterion(0.3, 1.5)
    print(f"胜率30%, 盈亏比1.5:1 -> 凯利比例 = {f4:.2f}")
    # 输出: -16.67%
```

#### 连续结果的凯利公式

对于股票等连续收益的资产，使用均值-方差的近似：

```python
def continuous_kelly(expected_return, volatility, risk_free_rate=0.03):
    """
    连续结果的凯利公式
    适用于股票等连续收益分布的资产
    
    参数:
        expected_return: 预期年化收益率
        volatility: 年化波动率
        risk_free_rate: 无风险利率
    
    返回:
        最优杠杆倍数（f* = 超额收益 / 方差）
    """
    excess_return = expected_return - risk_free_rate
    # f* = (mu - r) / sigma^2
    f_star = excess_return / (volatility ** 2)
    
    return f_star
```

#### 分数凯利 (Fractional Kelly)

实践中通常不会使用完整的凯利比例，因为：

1. 输入参数（胜率、赔率）存在估计误差
2. 全凯利可能导致令人不适的大幅回撤
3. 实际分布可能不符合假设

```python
def fractional_kelly(f_star, fraction=0.5, max_leverage=2.0):
    """
    分数凯利：使用凯利比例的一部分
    
    参数:
        f_star: 原始凯利比例
        fraction: 使用的比例 (常用0.5, 即"半凯利")
        max_leverage: 最大杠杆限制
    """
    f_fractional = f_star * fraction
    # 确保不超过最大杠杆且不为负
    return min(max(f_fractional, 0), max_leverage)


# 半凯利示例
# 原始凯利建议投入40%，使用半凯利则只投入20%
half_kelly = fractional_kelly(0.40, fraction=0.5)
print(f"半凯利比例: {half_kelly:.2%}")  # 20%
```

> **凯利公式的关键限制**：凯利公式假设你知道胜率和赔率的真实值，但在现实中我们只能估计。使用分数凯利（1/2凯利或1/4凯利）是更稳健的做法。半凯利通常能将回撤降低约75%，而仅"损失"约25%的长期收益。

---

### 三、基于风险的仓位管理

基于风险的仓位管理是最专业的方法：根据止损距离和波动率来确定仓位大小。

#### 方法1：固定比例风险模型

每笔交易只承担账户权益的固定百分比作为风险。

```python
def fixed_fractional_position(account_equity, risk_per_trade, 
                                entry_price, stop_loss_price):
    """
    固定比例风险模型
    
    每笔交易的风险 = 账户权益 × 风险比例
    仓位大小 = 风险金额 / 每股风险
    
    参数:
        account_equity: 账户权益
        risk_per_trade: 每笔交易的风险比例 (如0.02 = 2%)
        entry_price: 入场价格
        stop_loss_price: 止损价格
    """
    risk_amount = account_equity * risk_per_trade
    risk_per_share = abs(entry_price - stop_loss_price)
    
    if risk_per_share == 0:
        return 0
    
    shares = int(risk_amount / risk_per_share)
    position_value = shares * entry_price
    
    return {
        'shares': shares,
        'position_value': position_value,
        'risk_amount': risk_amount,
        'position_pct': position_value / account_equity
    }


# 示例
result = fixed_fractional_position(
    account_equity=1000000,     # 100万
    risk_per_trade=0.02,        # 每笔交易风险2%
    entry_price=50.0,           # 买入价50
    stop_loss_price=48.0        # 止损价48
)
# 输出：可买10000股，持仓价值500000，风险20000
```

#### 方法2：波动率调整的头寸规模

根据市场波动率动态调整仓位，波动大时减仓，波动小时加仓。

```python
def volatility_adjusted_position(account_equity, risk_per_trade,
                                   price, volatility, 
                                   atr_multiplier=2.0):
    """
    基于波动率的仓位管理
    
    参数:
        account_equity: 账户权益
        risk_per_trade: 每笔交易风险比例
        price: 当前价格
        volatility: 日波动率（如ATR）
        atr_multiplier: ATR倍数用于设定止损距离
    """
    risk_amount = account_equity * risk_per_trade
    stop_distance = volatility * atr_multiplier
    risk_per_share = stop_distance
    
    if risk_per_share == 0:
        return 0
    
    shares = int(risk_amount / risk_per_share)
    
    # 确保不会超过仓位上限
    max_position_value = account_equity * 0.25  # 单一标的上限25%
    actual_shares = min(shares, int(max_position_value / price))
    
    return {
        'shares': actual_shares,
        'position_value': actual_shares * price,
        'stop_distance': stop_distance,
        'risk_amount': risk_amount
    }
```

#### 方法3：目标波动率模型

维持组合的整体波动率在目标水平。

```python
def target_volatility_sizing(signal_strength, price, equity,
                               target_volatility=0.15, 
                               asset_volatility=0.25):
    """
    目标波动率仓位管理
    
    使组合的波动率维持在目标水平
    
    参数:
        signal_strength: 信号强度（-1到1）
        price: 当前价格
        equity: 账户权益
        target_volatility: 目标年化波动率
        asset_volatility: 资产年化波动率
    """
    # 如果波动率低于目标，可以加杠杆
    # 如果波动率高于目标，需要降杠杆
    leverage = target_volatility / asset_volatility
    
    # 限制杠杆范围
    leverage = max(0, min(leverage, 3.0))
    
    # 根据信号强度调整
    adjusted_leverage = leverage * abs(signal_strength)
    
    position_value = equity * adjusted_leverage
    shares = int(position_value / price)
    
    return {
        'shares': shares,
        'position_value': shares * price,
        'leverage': adjusted_leverage
    }
```

---

### 四、组合层面的仓位管理

当同时持有多个标的时，需要考虑组合层面的风险。

```python
def portfolio_variance_sizing(returns_df, risk_aversion=1.0, max_weight=0.1):
    """
    基于组合方差的仓位优化（均值-方差模型简化版）
    
    参数:
        returns_df: 各资产的历史日收益率DataFrame
        risk_aversion: 风险厌恶系数
        max_weight: 单一资产最大权重
    """
    # 计算协方差矩阵
    cov_matrix = returns_df.cov() * 252  # 年化协方差
    
    # 简化：使用风险平价近似
    # 各资产的边际风险贡献应该相等
    n = len(returns_df.columns)
    vols = returns_df.std() * np.sqrt(252)
    
    # 风险平价的近似解：权重 ∝ 1/波动率
    inv_vols = 1.0 / vols
    raw_weights = inv_vols / inv_vols.sum()
    
    # 应用权重上限
    weights = np.minimum(raw_weights, max_weight)
    weights = weights / weights.sum()
    
    return dict(zip(returns_df.columns, weights))
```

### 仓位管理的经验法则

| 法则 | 说明 |
|------|------|
| **2%规则** | 单笔交易损失不超过总资金的2% |
| **6%规则** | 当月累计亏损达6%时停止交易 |
| **分散化规则** | 单一标的仓位不超过总资金的10-20% |
| **流动性规则** | 单日交易量不超过该股日均成交量的5-10% |
| **相关性规则** | 组合内高相关性资产总仓位需控制 |

> **实战建议**：对于初学者，建议从固定比例风险模型（2%风险规则）开始，这是最容易理解和执行的方法。当你积累了更多经验和数据后，可以逐步引入波动率调整和目标波动率模型。永远不要在"感觉好"的时候突然放大仓位——这是交易账户毁灭的最常见原因。
