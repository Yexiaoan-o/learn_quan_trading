## 2.1 期货合约基础

期货（Futures）是一种标准化的远期合约，约定在未来的某个特定时间，以约定的价格买卖一定数量的某种资产。与股票不同，期货合约有明确的到期日。

### 期货合约的关键要素

| 要素 | 说明 | 示例（沪深300股指期货IF） |
|------|------|--------------------------|
| 标的资产 | 合约买卖的基础资产 | 沪深300指数 |
| 合约乘数 | 每个指数点的价值 | 300元/点 |
| 合约月份 | 可交易的到期月份 | 当月、下月及随后两个季月 |
| 最小变动价位 | 最小价格变动单位 | 0.2点（=60元） |
| 最后交易日 | 合约到期日 | 合约月份第三个周五 |
| 交割方式 | 如何完成履约 | 现金交割 |
| 交易所 | 交易场所 | 中国金融期货交易所（CFFEX） |
| 保证金比例 | 初始保证金 | 约12% |

### 期货的双向交易

```python
# 期货的双向交易特性
"""
股票交易：
  只能买涨（做多）→ 先买后卖 → 赚差价

期货交易：
  可以做多 → 先买后卖 → 赚差价（看涨）
  可以做空 → 先卖后买 → 赚差价（看跌）
"""

class FuturesPosition:
    """期货持仓模拟"""
    def __init__(self, symbol, side, entry_price, quantity, multiplier):
        """
        symbol: 合约代码，如 'IF2406'
        side: 'long' 或 'short'
        entry_price: 开仓价格
        quantity: 手数
        multiplier: 合约乘数
        """
        self.symbol = symbol
        self.side = side
        self.entry_price = entry_price
        self.quantity = quantity
        self.multiplier = multiplier
    
    def calculate_pnl(self, current_price):
        """计算浮动盈亏"""
        if self.side == 'long':
            return (current_price - self.entry_price) * self.quantity * self.multiplier
        else:
            return (self.entry_price - current_price) * self.quantity * self.multiplier

# 示例：做多1手IF，做空1手IC
long_if = FuturesPosition('IF2406', 'long', 3500, 1, 300)
short_ic = FuturesPosition('IC2406', 'short', 5200, 1, 200)

# 计算盈亏
print(f"IF做多盈亏: {long_if.calculate_pnl(3550):.0f}元")   # 15000元
print(f"IC做空盈亏: {short_ic.calculate_pnl(5100):.0f}元")  # 20000元
```

## 2.2 保证金与杠杆

杠杆是期货交易最显著的特征——也是最大的双刃剑。

### 保证金制度

```python
# 保证金计算示例
"""
保证金 = 合约价值 × 保证金比例
合约价值 = 当前价格 × 合约乘数 × 手数
杠杆倍数 = 1 / 保证金比例
"""

def calculate_margin(price, multiplier, quantity, margin_rate):
    """计算期货保证金"""
    contract_value = price * multiplier * quantity
    margin = contract_value * margin_rate
    leverage = 1 / margin_rate
    return {
        '合约价值': f'{contract_value:,.0f}元',
        '保证金': f'{margin:,.0f}元', 
        '杠杆倍数': f'{leverage:.1f}倍'
    }

# 沪深300股指期货
print("=== 沪深300股指期货 (IF) ===")
print(f"价格=3500点, 乘数=300元/点, 1手")
result = calculate_margin(3500, 300, 1, 0.12)
for k, v in result.items():
    print(f"{k}: {v}")

# 输出：
# 合约价值: 1,050,000元
# 保证金: 126,000元
# 杠杆倍数: 8.3倍
```

### 杠杆的双面性

```
                   做多1手IF，保证金126,000元
                   ┌────────────────────────────┐
                   │  价格上涨1% → 盈利10,500元   │
                   │  收益率 = 10,500/126,000     │
                   │  = 8.3%（杠杆放大！）         │
                   │                             │
                   │  价格下跌1% → 亏损10,500元    │
                   │  亏损率 = 8.3%               │
                   │  (8次连续1%亏损即爆仓)        │
                   └────────────────────────────┘
```

> **杠杆的核心危险**：杠杆不改变策略的期望收益，只放大了波动。一个期望收益为0的策略，加100倍杠杆也不会变成正期望收益。它只是让随机波动变得更加致命。

## 2.3 期货的分类

| 类别 | 标的 | 代表品种 | 交易所 | 适合策略 |
|------|------|----------|--------|----------|
| 股指期货 | 股票指数 | IF(沪深300)、IC(中证500)、IM(中证1000) | CFFEX | 市场中性、指数增强 |
| 国债期货 | 国债 | T(10年)、TF(5年)、TS(2年) | CFFEX | 利率套利 |
| 商品期货 | 实物商品 | 螺纹钢、原油、黄金、大豆 | SHFE/DCE/CZCE/INE | CTA趋势跟踪 |
| 外汇期货 | 汇率 | EUR/USD、USD/CNY | CME等 | 宏观对冲 |

### Python 获取期货数据

```python
import pandas as pd
import akshare as ak

# 获取沪深300股指期货主力连续合约数据
futures_df = ak.futures_main_sina(symbol="IF0")
print(futures_df.head())

# 获取螺纹钢期货数据
rb_df = ak.futures_zh_daily_sina(symbol="RB0")
print(rb_df.head())
```

## 2.4 期权基础

期权（Option）赋予持有者在特定时间以特定价格买入或卖出标的资产的权利，而非义务。

### 期权的核心要素

| 要素 | 说明 | 示例 |
|------|------|------|
| 标的资产 | 期权对应的基础资产 | 沪深300ETF |
| 行权价（Strike） | 约定买卖的价格 | 3.50元 |
| 到期日 | 权利的有效期 | 2024年6月28日 |
| 权利金（Premium） | 购买期权的价格 | 0.15元/份 |
| 合约单位 | 每张合约对应的资产数量 | 10,000份 |

### 看涨期权与看跌期权

```python
def call_option_payoff(stock_price, strike_price, premium):
    """
    看涨期权（Call Option）买方收益
    
    买入看涨期权：
    - 标的涨过行权价+权利金 → 盈利
    - 标的未涨过行权价    → 最大亏损=权利金
    """
    intrinsic_value = max(stock_price - strike_price, 0)
    return intrinsic_value - premium

def put_option_payoff(stock_price, strike_price, premium):
    """
    看跌期权（Put Option）买方收益
    
    买入看跌期权：
    - 标的跌过行权价-权利金 → 盈利
    - 标的未跌破行权价    → 最大亏损=权利金
    """
    intrinsic_value = max(strike_price - stock_price, 0)
    return intrinsic_value - premium

# 示例：买入看涨期权，行权价100，权利金3
print("=== 看涨期权买方收益 ===")
for price in [90, 95, 100, 103, 105, 110, 115]:
    payoff = call_option_payoff(price, 100, 3)
    print(f"股价={price:3d}  收益={payoff:3d}")
# 股价= 90  收益= -3  (最大亏损)
# 股价=103  收益=  0  (盈亏平衡点)
# 股价=110  收益=  7  (盈利)
# 股价=115  收益= 12  (盈利放大)
```

### 四种基本期权策略

| 策略 | 操作 | 适用观点 | 最大盈利 | 最大亏损 |
|------|------|----------|----------|----------|
| 买入看涨 | Buy Call | 强烈看涨 | 无限 | 权利金 |
| 卖出看涨 | Sell Call | 不看涨/小幅看跌 | 权利金 | 无限 |
| 买入看跌 | Buy Put | 强烈看跌 | 行权价-权利金 | 权利金 |
| 卖出看跌 | Sell Put | 不看跌/小幅看涨 | 权利金 | 行权价-权利金 |

> **期权与量化交易**：期权为量化策略提供了丰富的工具箱——波动率交易、套利、风险对冲都离不开期权。期权的非线性收益结构使得传统线性因子模型在此处可能失效，需要更复杂的数学模型（如Black-Scholes、随机波动率模型等）。

## 2.5 跨市场套利视角

期货和现货之间、不同到期月份的期货合约之间存在着套利机会，这是量化交易的重要收益来源。

```
期现套利（Cash-Futures Arbitrage）：

当 IF2406（期货）价格 > 沪深300指数（现货） + 持有成本
  → 卖空期货 + 买入现货 → 到期日价格收敛 → 获利

跨期套利（Calendar Spread）：

当 IF2406 价格 vs IF2409 价格的价差偏离正常范围
  → 做多低估合约 + 做空高估合约 → 价差回归 → 获利
```

```python
def calculate_basis(futures_price, spot_price, risk_free_rate=0.03, days_to_expiry=30):
    """
    计算期货的理论基差
    
    期货理论价格 = 现货价格 × e^(r × t)
    基差 = 期货实际价格 - 期货理论价格
    正基差→期货高估→做空期货做多现货（正向套利）
    """
    import numpy as np
    time = days_to_expiry / 365
    theoretical_futures = spot_price * np.exp(risk_free_rate * time)
    basis = futures_price - theoretical_futures
    return basis
```

> **套利的终极限制**：完美的套利机会在现实市场中很少存在。即使出现了理论套利机会，实际执行时还要考虑交易成本、冲击成本、资金成本和卖空限制。量化交易者不是在寻找"完美的套利"，而是在寻找"扣除所有成本后仍有正收益的机会"。
