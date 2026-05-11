## 均线交叉策略原理

均线交叉策略（MA Crossover Strategy）是量化交易中最经典的策略之一。它的核心逻辑简洁而强大：用双均线的交叉来捕捉趋势转折点。

### 金叉与死叉

| 信号名称 | 英文 | 条件 | 含义 |
|----------|------|------|------|
| **金叉** | Golden Cross | 短期均线上穿长期均线 | 买入信号，趋势转多 |
| **死叉** | Death Cross | 短期均线下穿长期均线 | 卖出信号，趋势转空 |

> **常见参数组合**：日线级别常用 (5, 20)、(10, 30)、(20, 60)；周线级别常用 (4, 13)、(10, 40)。短期均线控制灵敏度，长期均线控制趋势过滤。

---

### 一、完整策略实现

下面实现一个完整的双均线交叉策略，包含信号生成、回测和绩效评估：

```python
import numpy as np
import pandas as pd
import warnings
warnings.filterwarnings('ignore')


class DualMACrossoverStrategy:
    """
    双均线交叉策略
    
    参数：
        short_window: 短期均线周期
        long_window: 长期均线周期
        ma_type: 均线类型 ('sma' 或 'ema')
        initial_capital: 初始资金
        shares_per_trade: 每次交易股数（简化版，固定股数）
    """
    
    def __init__(self, short_window=5, long_window=20, 
                 ma_type='sma', initial_capital=100000, 
                 position_pct=1.0):
        self.short_window = short_window
        self.long_window = long_window
        self.ma_type = ma_type
        self.initial_capital = initial_capital
        self.position_pct = position_pct
    
    def calculate_ma(self, prices):
        """计算移动平均线"""
        if self.ma_type == 'sma':
            ma_short = prices.rolling(window=self.short_window).mean()
            ma_long = prices.rolling(window=self.long_window).mean()
        elif self.ma_type == 'ema':
            ma_short = prices.ewm(span=self.short_window, adjust=False).mean()
            ma_long = prices.ewm(span=self.long_window, adjust=False).mean()
        else:
            raise ValueError(f"不支持的均线类型: {self.ma_type}")
        return ma_short, ma_long
    
    def generate_signals(self, df):
        """
        生成交易信号
        
        返回值：
            position: 持仓状态 (0=空仓, 1=持多仓)
            signal: 交易信号 (1=买入, -1=卖出, 0=无操作)
        """
        df = df.copy()
        
        # 计算双均线
        df['ma_short'], df['ma_long'] = self.calculate_ma(df['close'])
        
        # 生成持仓状态
        df['position'] = 0
        df.loc[df['ma_short'] > df['ma_long'], 'position'] = 1
        
        # 生成交易信号（持仓状态变化时产生）
        df['signal'] = df['position'].diff().fillna(0)
        
        return df
    
    def backtest(self, df, commission_rate=0.0003, slippage=0.001):
        """
        策略回测
        
        返回：
            包含各列净值曲线的DataFrame
        """
        df = self.generate_signals(df)
        
        # 初始化回测状态
        capital = self.initial_capital
        shares = 0
        position_value = 0
        total_value = []  # 总资产
        daily_returns = []  # 日收益率
        trades = []  # 交易记录
        
        for i in range(len(df)):
            price = df['close'].iloc[i]
            signal = df['signal'].iloc[i]
            
            # 处理交易信号
            if signal == 1 and shares == 0:  # 买入信号且空仓
                # 计算买入股数（含滑点）
                buy_price = price * (1 + slippage)
                shares = int((capital * self.position_pct) / buy_price)
                cost = shares * buy_price * (1 + commission_rate)
                capital -= cost
                trades.append({
                    'date': df.index[i],
                    'type': 'BUY',
                    'price': buy_price,
                    'shares': shares,
                    'cost': cost
                })
                
            elif signal == -1 and shares > 0:  # 卖出信号且持仓
                # 全部卖出（含滑点）
                sell_price = price * (1 - slippage)
                revenue = shares * sell_price * (1 - commission_rate)
                capital += revenue
                trades.append({
                    'date': df.index[i],
                    'type': 'SELL',
                    'price': sell_price,
                    'shares': shares,
                    'revenue': revenue
                })
                shares = 0
            
            # 当日持仓市值
            position_value = shares * price
            total = capital + position_value
            
            total_value.append(total)
            
            # 计算日收益率
            if i > 0:
                daily_ret = (total - total_value[i-1]) / total_value[i-1]
            else:
                daily_ret = 0
            daily_returns.append(daily_ret)
        
        df['total_value'] = total_value
        df['daily_return'] = daily_returns
        df['equity_curve'] = df['total_value'] / self.initial_capital
        
        self.trades = trades
        return df
    
    def performance_summary(self, df, risk_free_rate=0.03):
        """
        计算策略绩效指标
        """
        returns = df['daily_return'].dropna()
        equity = df['equity_curve']
        
        # 总交易天数
        total_days = len(df)
        trading_years = total_days / 252
        
        # 基本收益指标
        total_return = float((equity.iloc[-1] - 1) * 100)
        annual_return = float((equity.iloc[-1] ** (1 / trading_years) - 1) * 100) if trading_years > 0 else 0
        
        # 波动率
        annual_volatility = float(returns.std() * np.sqrt(252) * 100)
        
        # 夏普比率
        excess_returns = returns - risk_free_rate / 252
        sharpe_ratio = float(excess_returns.mean() / returns.std() * np.sqrt(252)) if returns.std() > 0 else 0
        
        # 最大回撤
        cummax = equity.cummax()
        drawdown = (equity - cummax) / cummax
        max_drawdown = float(drawdown.min() * 100)
        max_dd_date = drawdown.idxmin()
        
        # 卡尔玛比率（收益/最大回撤）
        calmar_ratio = float(annual_return / abs(max_drawdown)) if max_drawdown != 0 else 0
        
        # 交易统计
        if hasattr(self, 'trades'):
            buy_trades = [t for t in self.trades if t['type'] == 'BUY']
            sell_trades = [t for t in self.trades if t['type'] == 'SELL']
            total_trades = len(buy_trades)
            
            # 计算每笔交易的盈亏
            trade_pnls = []
            for b, s in zip(buy_trades, sell_trades):
                pnl = s['revenue'] - b['cost']
                trade_pnls.append(pnl)
            
            win_trades = [p for p in trade_pnls if p > 0]
            loss_trades = [p for p in trade_pnls if p <= 0]
            
            win_rate = float(len(win_trades) / len(trade_pnls) * 100) if trade_pnls else 0
            avg_win = float(np.mean(win_trades)) if win_trades else 0
            avg_loss = float(np.mean(loss_trades)) if loss_trades else 0
            profit_factor = float(abs(sum(win_trades) / sum(loss_trades))) if loss_trades and sum(loss_trades) != 0 else float('inf')
        else:
            total_trades = win_rate = avg_win = avg_loss = profit_factor = 0
        
        summary = {
            '总收益率 (%)': round(total_return, 2),
            '年化收益率 (%)': round(annual_return, 2),
            '年化波动率 (%)': round(annual_volatility, 2),
            '夏普比率': round(sharpe_ratio, 2),
            '最大回撤 (%)': round(max_drawdown, 2),
            '最大回撤日期': max_dd_date,
            '卡尔玛比率': round(calmar_ratio, 2),
            '总交易次数': total_trades,
            '胜率 (%)': round(win_rate, 2),
            '平均盈利': round(avg_win, 2),
            '平均亏损': round(avg_loss, 2),
            '盈亏比': round(abs(avg_win / avg_loss), 2) if avg_loss != 0 else 'N/A',
            '盈亏因子': round(profit_factor, 2),
        }
        
        return summary
```

### 二、策略参数优化

参数选择直接影响策略表现。下面展示如何进行参数网格搜索：

```python
def parameter_optimization(df, short_range, long_range, 
                            metric='sharpe_ratio', ma_type='sma'):
    """
    均线策略参数网格搜索
    
    参数:
        df: 价格数据
        short_range: 短期均线参数范围
        long_range: 长期均线参数范围
        metric: 优化目标 (sharpe_ratio, total_return, calmar_ratio)
    """
    results = []
    
    for short_w in short_range:
        for long_w in long_range:
            if short_w >= long_w:
                continue
            
            strategy = DualMACrossoverStrategy(
                short_window=short_w,
                long_window=long_w,
                ma_type=ma_type
            )
            
            backtest_result = strategy.backtest(df.copy())
            summary = strategy.performance_summary(backtest_result)
            
            results.append({
                'short_window': short_w,
                'long_window': long_w,
                'sharpe_ratio': summary['夏普比率'],
                'total_return': summary['总收益率 (%)'],
                'max_drawdown': summary['最大回撤 (%)'],
                'win_rate': summary['胜率 (%)'],
                'total_trades': summary['总交易次数']
            })
    
    results_df = pd.DataFrame(results)
    
    # 按选定的指标排序
    results_df = results_df.sort_values(metric, ascending=False)
    
    return results_df


# 参数优化热力图数据
def create_heatmap_data(results_df):
    """
    将参数搜索结果转换为热力图矩阵格式
    """
    pivot = results_df.pivot_table(
        values='sharpe_ratio',
        index='short_window',
        columns='long_window'
    )
    return pivot
```

### 三、策略改进与常见问题

#### 问题1：震荡市的频繁交易

均线交叉策略最大的问题是在震荡市中产生大量假信号，导致反复亏损。

**解决方案：添加过滤条件**

```python
def generate_signals_with_filter(self, df, adx_threshold=25):
    """
    带ADX过滤的信号生成
    只在趋势明确的市况下交易
    """
    df = self.generate_signals(df)
    
    # 计算ADX（衡量趋势强度）
    df['adx'] = calculate_adx(df, period=14)
    
    # 过滤：只在ADX > 阈值时允许信号
    df['signal_filtered'] = df['signal']
    df.loc[df['adx'] < adx_threshold, 'signal_filtered'] = 0
    
    return df


def calculate_adx(df, period=14):
    """计算ADX指标"""
    high, low, close = df['high'], df['low'], df['close']
    
    # True Range
    tr1 = high - low
    tr2 = abs(high - close.shift(1))
    tr3 = abs(low - close.shift(1))
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    
    # +DM, -DM
    up_move = high - high.shift(1)
    down_move = low.shift(1) - low
    
    plus_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0)
    minus_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0)
    
    # Smoothed
    atr = tr.rolling(period).mean()
    plus_di = 100 * pd.Series(plus_dm).rolling(period).mean() / atr
    minus_di = 100 * pd.Series(minus_dm).rolling(period).mean() / atr
    
    # ADX
    dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di)
    adx = dx.rolling(period).mean()
    
    return adx
```

#### 问题2：滞后性导致的错过最佳入场点

均线本身具有滞后性，交叉信号往往出现在趋势已经走了一段之后。

**解决方案：使用交叉预警**

```python
def early_warning_system(df, short_window=5, long_window=20, 
                           warning_pct=0.01):
    """
    交叉预警系统
    当短线靠近长线时提前发出预警
    """
    df = df.copy()
    ma_short = df['close'].rolling(short_window).mean()
    ma_long = df['close'].rolling(long_window).mean()
    
    # 计算两线之间的距离（百分比）
    distance = abs(ma_short - ma_long) / ma_long
    
    # 预警条件：两线距离 < 阈值
    df['warning'] = distance < warning_pct
    
    # 接近交叉时增加关注
    df['approaching_cross'] = False
    df.loc[distance < warning_pct * 2, 'approaching_cross'] = True
    
    return df
```

#### 问题3：单一参数组不够稳健

**解决方案：多组合信号确认**

```python
def multi_timeframe_confirm(df, ma_pairs=[(5,20), (10,50), (20,100)]):
    """
    多时间框架信号确认
    多个均线组合同时看多/看空时才算有效信号
    """
    df = df.copy()
    
    signals = pd.DataFrame(index=df.index)
    for i, (short, long) in enumerate(ma_pairs):
        ma_s = df['close'].rolling(short).mean()
        ma_l = df['close'].rolling(long).mean()
        signals[f'signal_{i}'] = np.where(ma_s > ma_l, 1, -1)
    
    # 取多数意见
    signal_sum = signals.sum(axis=1)
    n_confirm = len(ma_pairs) // 2 + 1  # 至少需要半数以上确认
    
    df['confirmed_signal'] = 0
    df.loc[signal_sum >= n_confirm, 'confirmed_signal'] = 1
    df.loc[signal_sum <= -n_confirm, 'confirmed_signal'] = -1
    
    return df
```

> **策略改进总结**：均线交叉策略虽然简单，但通过合理的改进（趋势过滤、交叉预警、多周期确认、止损止盈），可以大幅提升其稳健性。关键在于理解它擅长和局限的市场环境——它在趋势市场中表现良好，在震荡市场中容易出现回撤。
