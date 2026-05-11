## 向量化回测

### 什么是向量化回测

向量化回测（Vectorized Backtesting）是一种利用 pandas 或 NumPy 的向量化运算特性，一次性对整个时间序列数据执行计算的回测方法。相比于事件驱动回测，向量化回测的代码更加简洁，执行速度更快，非常适合策略的早期研究和快速原型开发。

向量化回测的核心思想是：**将交易策略表达为对整个时间序列的数学运算**，而不是逐笔逐日地模拟订单和执行过程。例如，一个简单的双均线策略在向量化回测中只需几行代码即可完成——我们只需要一次性计算所有日期的均线值、生成信号向量、然后与收益率向量相乘即可。

> **向量化回测的优势**：
> - 代码简洁，易于理解和维护
> - 执行速度快，通常比事件驱动方式快10-100倍
> - 适合快速迭代和参数扫描
>
> **向量化回测的局限**：
> - 难以模拟复杂的订单执行逻辑
> - 处理仓位管理、动态止损等比较复杂
> - 难以精确建模交易成本、滑点、市场冲击
> - 通常假设每个时间点按收盘价成交（理想化假设）

### 构建基础向量化回测引擎

让我们从零开始构建一个功能完整的向量化回测引擎。这个引擎将支持：
- 单资产策略回测
- 多种信号生成方式
- 交易成本计算
- 绩效指标报告

#### 步骤1：数据准备与价格处理

```python
import pandas as pd
import numpy as np
from typing import Callable, Dict, Optional

class VectorizedBacktest:
    """
    向量化回测引擎
    支持单资产策略的快速回测
    """
    
    def __init__(self, prices: pd.Series, initial_capital: float = 1000000):
        """
        prices: 价格时间序列（通常使用收盘价），index为日期
        initial_capital: 初始资金
        """
        self.prices = prices.copy()
        self.initial_capital = initial_capital
        self.results = None
        
    def compute_returns(self):
        """计算每日收益率"""
        return self.prices.pct_change()
    
    def compute_log_returns(self):
        """计算对数收益率"""
        return np.log(self.prices / self.prices.shift(1))
```

#### 步骤2：常见技术信号生成

在向量化回测中，信号生成是最核心的环节。下面我们实现几种常见的技术信号：

```python
class SignalGenerator:
    """信号生成器集合"""
    
    @staticmethod
    def sma_crossover(prices: pd.Series, short_window: int = 20, long_window: int = 60):
        """
        简单移动平均线交叉策略
        短期均线上穿长期均线 → 买入信号 (1)
        短期均线下穿长期均线 → 卖出信号 (-1)
        """
        sma_short = prices.rolling(short_window).mean()
        sma_long = prices.rolling(long_window).mean()
        
        signal = pd.Series(0, index=prices.index)
        signal[sma_short > sma_long] = 1
        signal[sma_short <= sma_long] = -1
        
        return signal
    
    @staticmethod
    def momentum(prices: pd.Series, lookback: int = 20, threshold: float = 0.0):
        """
        动量策略
        过去N天的收益率 > 阈值 → 买入
        过去N天的收益率 < -阈值 → 卖出
        """
        momentum_returns = prices.pct_change(lookback)
        
        signal = pd.Series(0, index=prices.index)
        signal[momentum_returns > threshold] = 1
        signal[momentum_returns < -threshold] = -1
        
        return signal
    
    @staticmethod
    def bollinger_bands(prices: pd.Series, window: int = 20, num_std: float = 2.0):
        """
        布林带策略
        价格跌破下轨 → 买入（超卖）
        价格突破上轨 → 卖出（超买）
        """
        sma = prices.rolling(window).mean()
        std = prices.rolling(window).std()
        
        upper_band = sma + num_std * std
        lower_band = sma - num_std * std
        
        signal = pd.Series(0, index=prices.index)
        signal[prices < lower_band] = 1    # 买入信号
        signal[prices > upper_band] = -1   # 卖出信号
        
        return signal
    
    @staticmethod
    def rsi_threshold(prices: pd.Series, period: int = 14, 
                      oversold: float = 30, overbought: float = 70):
        """
        RSI阈值策略
        RSI < 超卖线 → 买入
        RSI > 超买线 → 卖出
        """
        delta = prices.diff()
        gain = delta.clip(lower=0)
        loss = -delta.clip(upper=0)
        
        avg_gain = gain.rolling(period).mean()
        avg_loss = loss.rolling(period).mean()
        
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        
        signal = pd.Series(0, index=prices.index)
        signal[rsi < oversold] = 1
        signal[rsi > overbought] = -1
        
        return signal
```

#### 步骤3：构建完整的回测引擎

```python
class VectorizedBacktest:
    """完整的向量化回测引擎"""
    
    def __init__(self, prices: pd.Series, initial_capital: float = 1000000):
        self.prices = prices.copy()
        self.initial_capital = initial_capital
        self.results = None
        self.trade_log = None
        
    def run(self, signal_func: Callable, **signal_params):
        """
        执行向量化回测
        
        signal_func: 信号生成函数，接受prices和额外参数，返回信号序列
            信号值约定：1=全仓做多, -1=全仓做空, 0=空仓
        signal_params: 传递给信号函数的额外参数
        """
        # 生成信号（使用shift(1)避免前视偏差：今天的信号明天才能执行）
        raw_signals = signal_func(self.prices, **signal_params)
        signals = raw_signals.shift(1).fillna(0)
        
        # 计算每日收益率
        daily_returns = self.prices.pct_change()
        
        # 策略收益率 = 持仓信号 × 市场收益率
        # shift(1)：今天开盘时的仓位决定今天的盈亏
        strategy_returns = signals * daily_returns
        
        # 计算净值曲线
        strategy_net_value = (1 + strategy_returns).cumprod() * self.initial_capital
        buy_hold_net_value = (1 + daily_returns).cumprod() * self.initial_capital
        
        self.results = pd.DataFrame({
            'price': self.prices,
            'signal': signals,
            'daily_return': daily_returns,
            'strategy_return': strategy_returns,
            'strategy_net_value': strategy_net_value,
            'buy_hold_net_value': buy_hold_net_value
        })
        
        # 生成交易记录
        self._generate_trade_log(signals)
        
        return self.results
    
    def _generate_trade_log(self, signals: pd.Series):
        """从信号序列生成交易记录"""
        trades = []
        position = 0  # 当前仓位
        entry_price = None
        entry_date = None
        
        for date, signal in signals.items():
            price = self.prices[date]
            
            if signal != position:  # 仓位发生变化
                # 先平仓（如果有持仓）
                if position != 0 and entry_price is not None:
                    trades.append({
                        'entry_date': entry_date,
                        'exit_date': date,
                        'entry_price': entry_price,
                        'exit_price': price,
                        'direction': 'LONG' if position == 1 else 'SHORT',
                        'return': (price / entry_price - 1) * position
                    })
                
                # 再开新仓
                if signal != 0:
                    entry_price = price
                    entry_date = date
                else:
                    entry_price = None
                    entry_date = None
                
                position = signal
        
        # 处理回测结束时的持仓
        if position != 0 and entry_price is not None:
            last_date = signals.index[-1]
            last_price = self.prices[last_date]
            trades.append({
                'entry_date': entry_date,
                'exit_date': last_date,
                'entry_price': entry_price,
                'exit_price': last_price,
                'direction': 'LONG' if position == 1 else 'SHORT',
                'return': (last_price / entry_price - 1) * position
            })
        
        self.trade_log = pd.DataFrame(trades)
    
    def performance_summary(self) -> Dict:
        """生成回测绩效摘要"""
        if self.results is None:
            raise ValueError("请先调用 run() 执行回测")
        
        r = self.results
        sr = r['strategy_return'].dropna()
        trading_days = 252
        
        # 基础收益
        total_ret = (r['strategy_net_value'].iloc[-1] / self.initial_capital - 1) * 100
        ann_ret = ((r['strategy_net_value'].iloc[-1] / self.initial_capital) 
                   ** (trading_days / len(sr)) - 1) * 100
        ann_vol = sr.std() * np.sqrt(trading_days) * 100
        
        # 风险调整收益
        sharpe = (sr.mean() / sr.std()) * np.sqrt(trading_days) if sr.std() > 0 else 0
        
        # 最大回撤
        net_values = r['strategy_net_value']
        rolling_max = net_values.expanding().max()
        drawdowns = (net_values - rolling_max) / rolling_max
        max_dd = drawdowns.min() * 100
        
        # 交易统计
        trades = self.trade_log
        if trades is not None and len(trades) > 0:
            num_trades = len(trades)
            win_rate = (trades['return'] > 0).sum() / num_trades * 100
            profit_factor = (trades['return'][trades['return'] > 0].sum() / 
                           abs(trades['return'][trades['return'] < 0].sum()))
            avg_return = trades['return'].mean() * 100
        else:
            num_trades = 0
            win_rate = 0
            profit_factor = 0
            avg_return = 0
        
        return {
            '总收益率 (%)': f"{total_ret:.2f}",
            '年化收益率 (%)': f"{ann_ret:.2f}",
            '年化波动率 (%)': f"{ann_vol:.2f}",
            '夏普比率': f"{sharpe:.3f}",
            '最大回撤 (%)': f"{max_dd:.2f}",
            '交易次数': num_trades,
            '胜率 (%)': f"{win_rate:.2f}",
            '盈利因子': f"{profit_factor:.3f}",
            '平均交易收益 (%)': f"{avg_return:.2f}"
        }
```

#### 步骤4：运行回测示例

```python
# 生成模拟数据
np.random.seed(42)
dates = pd.date_range('2018-01-01', '2023-12-31', freq='B')
n = len(dates)

# 模拟具有趋势和波动的价格
trend = np.linspace(0, 0.5, n)
noise = np.random.randn(n).cumsum() * 0.15
prices = 100 * np.exp(trend + noise)
price_series = pd.Series(prices, index=dates)

# 创建回测引擎
bt = VectorizedBacktest(price_series, initial_capital=1000000)

# 使用双均线策略进行回测
results = bt.run(SignalGenerator.sma_crossover, short_window=20, long_window=60)

# 打印绩效摘要
summary = bt.performance_summary()
print("=" * 40)
print("向量化回测绩效报告")
print("=" * 40)
for key, value in summary.items():
    print(f"{key}: {value}")

# 查看前几笔交易
if bt.trade_log is not None and len(bt.trade_log) > 0:
    print("\n" + "=" * 40)
    print("最近交易记录")
    print("=" * 40)
    print(bt.trade_log.head(10).to_string())
```

### 进阶：加入交易成本

真实世界中的交易成本不可忽视。我们需要在向量化回测中加入交易成本模型：

```python
class VectorizedBacktestWithCosts(VectorizedBacktest):
    """带交易成本的向量化回测引擎"""
    
    def __init__(self, prices: pd.Series, initial_capital: float = 1000000,
                 commission_rate: float = 0.0003,  # 万三手续费
                 slippage_rate: float = 0.0001,     # 万一滑点
                 stamp_duty_rate: float = 0.001):   # 千一印花税（仅卖出）
        super().__init__(prices, initial_capital)
        self.commission_rate = commission_rate
        self.slippage_rate = slippage_rate
        self.stamp_duty_rate = stamp_duty_rate
    
    def run(self, signal_func: Callable, **signal_params):
        """
        执行考虑交易成本的向量化回测
        """
        # 生成信号
        raw_signals = signal_func(self.prices, **signal_params)
        signals = raw_signals.shift(1).fillna(0)
        
        # 计算仓位变化（交易信号变化时产生交易成本）
        position_change = signals.diff().fillna(0)
        
        # 计算每日收益率
        daily_returns = self.prices.pct_change()
        
        # 基础策略收益率
        base_strategy_returns = signals * daily_returns
        
        # 计算交易成本
        # 成本 = 仓位变化绝对值 × (手续费率 + 滑点)
        # 卖出时加印花税
        buy_trades = (position_change > 0).astype(float)
        sell_trades = (position_change < 0).astype(float)
        
        # 买入成本（手续费 + 滑点）
        buy_cost = buy_trades * (self.commission_rate + self.slippage_rate)
        # 卖出成本（手续费 + 滑点 + 印花税）
        sell_cost = sell_trades * (self.commission_rate + self.slippage_rate + self.stamp_duty_rate)
        
        total_cost = buy_cost + sell_cost
        
        # 扣除交易成本后的策略收益率
        strategy_returns = base_strategy_returns - total_cost
        
        # 计算净值曲线
        strategy_net_value = (1 + strategy_returns).cumprod() * self.initial_capital
        
        self.results = pd.DataFrame({
            'price': self.prices,
            'signal': signals,
            'daily_return': daily_returns,
            'base_strategy_return': base_strategy_returns,
            'transaction_cost': total_cost,
            'strategy_return': strategy_returns,
            'strategy_net_value': strategy_net_value
        })
        
        self._generate_trade_log(signals)
        return self.results
```

### 多策略并行回测

向量化回测的一大优势是可以轻松地对多种策略同时回测和比较：

```python
def compare_strategies(prices: pd.Series, strategies: Dict[str, tuple]):
    """
    并行比较多个策略
    
    strategies: 策略名称 -> (信号函数, 参数字典) 的映射
    """
    bt = VectorizedBacktest(prices)
    comparison = pd.DataFrame(index=prices.index)
    
    performance = {}
    
    for name, (signal_func, params) in strategies.items():
        results = bt.run(signal_func, **params)
        # 将净值归一化到100以便比较
        comparison[name] = results['strategy_net_value'] / bt.initial_capital * 100
        performance[name] = bt.performance_summary()
    
    # 加入买入持有策略作为基准
    comparison['Buy & Hold'] = results['buy_hold_net_value'] / bt.initial_capital * 100
    
    return comparison, performance

# 使用示例
strategies_to_compare = {
    'MA_10_30': (SignalGenerator.sma_crossover, {'short_window': 10, 'long_window': 30}),
    'MA_20_60': (SignalGenerator.sma_crossover, {'short_window': 20, 'long_window': 60}),
    'MA_50_200': (SignalGenerator.sma_crossover, {'short_window': 50, 'long_window': 200}),
    'MOM_20': (SignalGenerator.momentum, {'lookback': 20}),
    'MOM_60': (SignalGenerator.momentum, {'lookback': 60}),
    'BB_20': (SignalGenerator.bollinger_bands, {'window': 20}),
}

comparison_df, perf_dict = compare_strategies(price_series, strategies_to_compare)

print("\n策略比较结果：")
for name, perf in perf_dict.items():
    print(f"\n{name}:")
    print(f"  年化收益: {perf['年化收益率 (%)']}%, 夏普: {perf['夏普比率']}, 最大回撤: {perf['最大回撤 (%)']}%")
```

### 参数扫描与优化

向量化回测的速度优势使其非常适合进行参数扫描——系统性地测试多种参数组合以找到最优配置。但必须注意避免过度优化。

```python
def parameter_sweep(prices: pd.Series, short_windows: list, long_windows: list):
    """
    参数扫描：测试双均线策略的不同参数组合
    """
    results_list = []
    
    for short in short_windows:
        for long in long_windows:
            if short >= long:
                continue
                
            bt = VectorizedBacktest(prices)
            bt.run(SignalGenerator.sma_crossover, short_window=short, long_window=long)
            perf = bt.performance_summary()
            
            results_list.append({
                'short_window': short,
                'long_window': long,
                'annual_return': float(perf['年化收益率 (%)']),
                'sharpe': float(perf['夏普比率']),
                'max_dd': float(perf['最大回撤 (%)']),
                'num_trades': perf['交易次数'],
                'win_rate': float(perf['胜率 (%)']),
                'profit_factor': float(perf['盈利因子'])
            })
    
    results_df = pd.DataFrame(results_list)
    return results_df

# 运行参数扫描
sweep_results = parameter_sweep(
    price_series,
    short_windows=[5, 10, 20, 30],
    long_windows=[30, 50, 60, 100, 200]
)

print("参数扫描结果（按夏普比率排序）：")
print(sweep_results.sort_values('sharpe', ascending=False).head(10).to_string())

# 查找最优参数组合
best_sharpe = sweep_results.loc[sweep_results['sharpe'].idxmax()]
print(f"\n最优组合（按夏普比率）: 短期={int(best_sharpe['short_window'])}, 长期={int(best_sharpe['long_window'])}")
print(f"夏普比率: {best_sharpe['sharpe']:.3f}, 年化收益: {best_sharpe['annual_return']:.2f}%")
```

### 向量化回测的注意事项

#### 1. 前视偏差保护

在向量化回测中，保护前视偏差的关键操作是 `shift(1)`：

```python
# 重点：信号需要shift才能避免前视偏差
# 例如：今日收盘后计算出信号，实际交易发生在下一个交易日

# 错误做法（存在前视偏差）：
# daily_returns = prices.pct_change()
# strategy_returns = signals * daily_returns  # 当日信号使用当日收益率

# 正确做法：
daily_returns = prices.pct_change()
strategy_returns = signals.shift(1) * daily_returns  # 昨天的信号决定今天的仓位
```

#### 2. NaN处理

在计算技术指标时，初期会存在NaN值。需要正确处理这些缺失值：

```python
# 方法1：删除NaN值
signals_clean = signals.dropna()
returns_clean = strategy_returns.dropna()

# 方法2：用特定值填充
signals_filled = signals.fillna(0)     # 没有信号时保持空仓
returns_filled = strategy_returns.fillna(0)  # 没有策略收益时记为0

# 方法3：前向填充
signals_ffill = signals.fillna(method='ffill').fillna(0)
```

#### 3. 交易频率控制

向量化回测中策略可能产生过于频繁的信号，增加交易成本。可以通过以下方式控制：

```python
def smooth_signals(signals: pd.Series, min_holding_period: int = 5):
    """
    平滑信号：要求仓位变化后至少持有min_holding_period天
    """
    smoothed = signals.copy()
    last_change = -9999
    
    for i in range(1, len(smoothed)):
        if smoothed.iloc[i] != smoothed.iloc[i-1]:
            if i - last_change < min_holding_period:
                # 距离上次变化太近，忽略本次信号变化
                smoothed.iloc[i] = smoothed.iloc[i-1]
            else:
                last_change = i
    
    return smoothed
```

### 向量化回测 vs 事件驱动回测

| 特性 | 向量化回测 | 事件驱动回测 |
|------|-----------|-------------|
| 实现复杂度 | 低，几行代码即可 | 高，需要完整的事件循环 |
| 执行速度 | 快 | 较慢 |
| 精度 | 中等（理想化假设） | 高（可精确建模） |
| 交易成本建模 | 简单近似 | 可以精确建模 |
| 仓位管理 | 基础 | 灵活复杂 |
| 多资产支持 | 可以但复杂 | 天然支持 |
| 适用阶段 | 策略初筛、快速迭代 | 策略验证、准实盘准备 |
| 订单类型 | 通常只支持市价单 | 支持多种订单类型 |
| 事件处理 | 不支持 | 支持（分红、除权、停牌等） |

> **最佳实践**：使用向量化回测进行策略的初步筛选和快速迭代，当策略在向量化回测中表现符合预期后，再将策略移植到事件驱动回测系统中进行更精细的验证。

### 总结

向量化回测是量化交易者手中最高效的"瑞士军刀"。它利用pandas的向量化运算能力，让我们能够以极快的速度测试交易想法。在本章中，我们构建了一个从基础到进阶的向量化回测引擎，包括：

1. 信号生成器（多种技术指标）
2. 回测引擎核心（信号到收益的转换）
3. 交易成本模型
4. 多策略比较框架
5. 参数扫描工具

向量化回测的结果可以作为策略是否值得进一步研究的初步判断。下一章中，我们将学习事件驱动回测——一种更精细但也更复杂的回测方法。
