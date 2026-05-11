## 事件驱动回测

### 事件驱动回测概述

事件驱动回测（Event-Driven Backtesting）是一种模拟真实交易系统中事件流转的架构方法。与向量化回测不同，事件驱动回测通过显式的事件循环（Event Loop）来处理市场数据的逐条到达、策略信号的生成与执行、订单的生命周期管理、以及投资组合的实时更新。它更接近真实的量化交易系统的运行方式，能够进行更精细、更真实的模拟。

> **事件驱动 vs 向量化**：
> 
> 如果把向量化回测比作用计算器对整列数据做批量运算，那么事件驱动回测就像是逐笔逐笔地按照时间顺序处理——每次只看到一个时间点的数据，做出决策，然后等待下一个时间点。这种"一次只看一步"的方式消除了许多向量化回测中难以避免的假设，但也带来了更高的复杂度和更慢的运行速度。

### 事件驱动回测的核心组件

事件驱动回测系统由以下核心组件构成：

| 组件 | 职责 | 说明 |
|------|------|------|
| **事件队列（Event Queue）** | 按时间顺序管理所有待处理事件 | 是事件驱动系统的"心脏" |
| **数据处理器（Data Handler）** | 提供历史市场和基本面数据 | 确保数据按正确的时间顺序提供 |
| **策略引擎（Strategy）** | 根据市场数据生成交易信号 | 策略的"大脑" |
| **投资组合（Portfolio）** | 跟踪持仓、现金和净值 | 反映当前的资金状态 |
| **执行处理器（Execution Handler）** | 模拟订单的执行过程 | 处理订单发送、成交、滑点等 |
| **性能分析器（Performance）** | 计算策略的各项绩效指标 | 回测完成后的分析工具 |

#### 事件类型

在事件驱动回测中，所有行为都通过"事件"来传递和通信：

```python
from enum import Enum
from abc import ABC, abstractmethod
from typing import List, Optional
from datetime import datetime
import pandas as pd
import numpy as np

class EventType(Enum):
    """事件类型枚举"""
    MARKET = 'MARKET'        # 市场数据事件
    SIGNAL = 'SIGNAL'        # 策略信号事件
    ORDER = 'ORDER'          # 订单事件
    FILL = 'FILL'            # 成交事件
    PORTFOLIO = 'PORTFOLIO'  # 组合更新事件


class Event(ABC):
    """事件基类"""
    def __init__(self, event_type: EventType):
        self.type = event_type
        self.timestamp = None


class MarketEvent(Event):
    """市场数据事件——每次新的行情数据到达"""
    def __init__(self):
        super().__init__(EventType.MARKET)
        self.symbol = None
        self.datetime = None
        self.open = None
        self.high = None
        self.low = None
        self.close = None
        self.volume = None


class SignalEvent(Event):
    """策略信号事件——策略根据分析决定交易方向"""
    def __init__(self, symbol: str, datetime: pd.Timestamp, 
                 signal_type: str, strength: float = 1.0):
        super().__init__(EventType.SIGNAL)
        self.symbol = symbol
        self.datetime = datetime
        self.signal_type = signal_type  # 'LONG', 'SHORT', 'EXIT'
        self.strength = strength  # 信号强度，用于确定仓位比例


class OrderEvent(Event):
    """订单事件——将信号转化为具体订单"""
    def __init__(self, symbol: str, order_type: str, quantity: int, 
                 direction: str, datetime: pd.Timestamp):
        super().__init__(EventType.ORDER)
        self.symbol = symbol
        self.order_type = order_type  # 'MARKET', 'LIMIT'
        self.quantity = quantity
        self.direction = direction    # 'BUY', 'SELL'
        self.datetime = datetime
        self.order_id = None


class FillEvent(Event):
    """成交事件——订单被执行"""
    def __init__(self, symbol: str, datetime: pd.Timestamp,
                 quantity: int, direction: str, fill_price: float, 
                 commission: float, order_id: str):
        super().__init__(EventType.FILL)
        self.symbol = symbol
        self.datetime = datetime
        self.quantity = quantity
        self.direction = direction
        self.fill_price = fill_price
        self.commission = commission
        self.order_id = order_id
        
    def calculate_value(self) -> float:
        """计算成交金额（包含手续费）"""
        direction_multiplier = 1 if self.direction == 'BUY' else -1
        return self.fill_price * self.quantity * direction_multiplier - self.commission
```

### 事件循环——系统的"心脏"

事件循环是事件驱动回测的核心执行机制。它的工作方式是持续从事件队列中取出最早的事件并处理，直到所有事件都被处理完毕：

```python
import heapq
from collections import deque

class EventQueue:
    """按时间排序的事件队列"""
    def __init__(self):
        self._queue = []
        self._counter = 0  # 用于在时间相同时保持插入顺序
    
    def put(self, event: Event):
        """将事件加入队列"""
        timestamp = event.timestamp if event.timestamp else pd.Timestamp.min
        heapq.heappush(self._queue, (timestamp, self._counter, event))
        self._counter += 1
    
    def get(self) -> Optional[Event]:
        """获取下一个待处理事件"""
        if self._queue:
            return heapq.heappop(self._queue)[2]
        return None
    
    def is_empty(self) -> bool:
        return len(self._queue) == 0
    
    def __len__(self):
        return len(self._queue)
```

### 历史数据处理器

数据处理器负责按照时间顺序逐条提供历史数据。这是防止前视偏差的关键组件——策略在每个时间点只能"看到"当前和过去的数据。

```python
class HistoricCSVDataHandler:
    """
    历史数据处理器
    从DataFrame中按时间顺序逐条提供数据，模拟实时数据流
    """
    def __init__(self, data: pd.DataFrame):
        """
        data: 多列DataFrame，index为datetime，包含所需的行情数据
        """
        self.data = data.sort_index()
        self.symbol_list = list(data.columns.get_level_values(0).unique()) if isinstance(data.columns, pd.MultiIndex) else ['DEFAULT']
        
        # 当前状态
        self.current_idx = 0
        self.current_data = None
        self.continue_backtest = True
        
        # 起始时间索引（跳过初始NaN）
        self.start_idx = 0
        
    def get_latest_bars(self, symbol: str, N: int = 1) -> pd.DataFrame:
        """获取最近N条K线数据"""
        if self.current_idx == 0:
            return pd.DataFrame()
        
        # 获取当前日期之前的所有数据
        available_data = self.data.iloc[max(0, self.current_idx - N):self.current_idx]
        return available_data
    
    def update_bars(self) -> Optional[MarketEvent]:
        """推进到下一个时间点的数据，生成MarketEvent"""
        if self.current_idx >= len(self.data):
            self.continue_backtest = False
            return None
        
        # 获取当前时间点的数据
        row = self.data.iloc[self.current_idx]
        current_dt = self.data.index[self.current_idx]
        
        # 创建MarketEvent
        event = MarketEvent()
        event.timestamp = current_dt
        event.datetime = current_dt
        event.symbol = 'DEFAULT'
        
        # 填充OHLCV数据
        if isinstance(row, pd.Series):
            event.open = row.get('open', None)
            event.high = row.get('high', None)
            event.low = row.get('low', None)
            event.close = row.get('close', None)
            event.volume = row.get('volume', None)
        
        self.current_idx += 1
        return event
```

### 策略类——交易逻辑的容器

策略类从数据处理器接收市场数据，经过分析后产生SignalEvent：

```python
class Strategy(ABC):
    """策略基类"""
    def __init__(self, data_handler, event_queue):
        self.data_handler = data_handler
        self.event_queue = event_queue
        self.symbol_list = data_handler.symbol_list
        self.invested = False
    
    @abstractmethod
    def calculate_signals(self, event: MarketEvent):
        """计算交易信号"""
        pass


class MovingAverageCrossStrategy(Strategy):
    """双均线交叉策略"""
    def __init__(self, data_handler, event_queue, short_window=20, long_window=60):
        super().__init__(data_handler, event_queue)
        self.short_window = short_window
        self.long_window = long_window
        self.bought = False
    
    def calculate_signals(self, event: MarketEvent):
        """计算双均线交叉信号"""
        if event.type != EventType.MARKET:
            return
        
        symbol = event.symbol
        bars = self.data_handler.get_latest_bars(symbol, N=self.long_window + 1)
        
        if bars is None or len(bars) < self.long_window:
            return  # 数据不足，无法计算
        
        # 获取close列（假设数据结构中有close列）
        if 'close' in bars.columns:
            close_prices = bars['close']
        else:
            return
        
        # 计算均线值（使用历史数据，避免前视偏差）
        short_sma = close_prices.iloc[-self.short_window:].mean()
        long_sma = close_prices.iloc[-self.long_window:].mean()
        
        dt = event.datetime
        
        # 生成信号
        if short_sma > long_sma and not self.bought:
            # 金叉——买入信号
            signal = SignalEvent(symbol, dt, 'LONG', 1.0)
            self.event_queue.put(signal)
            self.bought = True
        
        elif short_sma < long_sma and self.bought:
            # 死叉——卖出信号
            signal = SignalEvent(symbol, dt, 'EXIT', 1.0)
            self.event_queue.put(signal)
            self.bought = False
```

### 投资组合管理

投资组合跟踪所有持仓、现金余额和净值变化，并根据成交事件更新状态：

```python
class Portfolio:
    """投资组合管理"""
    def __init__(self, data_handler, event_queue, initial_capital=1000000.0):
        self.data_handler = data_handler
        self.event_queue = event_queue
        self.initial_capital = initial_capital
        
        # 资产状态
        self.cash = initial_capital
        self.positions = {}      # {symbol: quantity}
        self.total_commission = 0.0
        self.total_slippage = 0.0
        
        # 历史记录
        self.equity_curve = []   # [(datetime, total_value)]
        self.trade_history = []  # 每笔交易的记录
        
    def update_on_fill(self, fill_event: FillEvent):
        """根据成交事件更新投资组合"""
        symbol = fill_event.symbol
        quantity = fill_event.quantity
        direction = fill_event.direction
        
        # 更新持仓
        if symbol not in self.positions:
            self.positions[symbol] = 0
        
        if direction == 'BUY':
            self.positions[symbol] += quantity
            self.cash -= (fill_event.fill_price * quantity + fill_event.commission)
        else:  # SELL
            self.positions[symbol] -= quantity
            self.cash += (fill_event.fill_price * quantity - fill_event.commission)
        
        self.total_commission += fill_event.commission
        
        # 记录交易
        self.trade_history.append({
            'datetime': fill_event.datetime,
            'symbol': symbol,
            'direction': direction,
            'quantity': quantity,
            'price': fill_event.fill_price,
            'commission': fill_event.commission,
            'position_after': self.positions[symbol],
            'cash_after': self.cash
        })
    
    def update_market_value(self, datetime, market_prices: dict):
        """按市值更新投资组合总价值"""
        total_value = self.cash
        for symbol, quantity in self.positions.items():
            if symbol in market_prices:
                total_value += quantity * market_prices[symbol]
        
        self.equity_curve.append((datetime, total_value))
        return total_value
    
    def current_total_value(self, market_prices: dict) -> float:
        """计算当前总资产"""
        total = self.cash
        for symbol, qty in self.positions.items():
            if symbol in market_prices and market_prices[symbol]:
                total += qty * market_prices[symbol]
        return total
    
    def get_position(self, symbol: str) -> int:
        """获取指定标的的持仓量"""
        return self.positions.get(symbol, 0)
```

### 执行处理器——模拟订单执行

执行处理器负责将订单事件转化为实际的成交事件，这里可以建模滑点、手续费和其他执行细节：

```python
class SimulatedExecutionHandler:
    """模拟订单执行处理器"""
    def __init__(self, event_queue, data_handler, 
                 commission_rate=0.0003, 
                 slippage_model='fixed',
                 slippage_bps=1.0):
        """
        commission_rate: 手续费率
        slippage_model: 滑点模型 ('fixed' 或 'percentage')
        slippage_bps: 滑点数（基点，1 bps = 0.01%）
        """
        self.event_queue = event_queue
        self.data_handler = data_handler
        self.commission_rate = commission_rate
        self.slippage_model = slippage_model
        self.slippage_bps = slippage_bps
        self.fill_counter = 0  # 用于生成订单ID
    
    def execute_order(self, order_event: OrderEvent, current_price: float) -> FillEvent:
        """执行订单，产生成交事件"""
        dt = order_event.datetime
        symbol = order_event.symbol
        
        # 计算滑点
        if order_event.direction == 'BUY':
            fill_price = current_price * (1 + self.slippage_bps / 10000)
        else:
            fill_price = current_price * (1 - self.slippage_bps / 10000)
        
        # 计算手续费
        trade_value = fill_price * order_event.quantity
        commission = trade_value * self.commission_rate
        
        # 确保最小手续费
        commission = max(commission, 5.0)  # 最低5元手续费
        
        # 产生成交事件
        self.fill_counter += 1
        order_id = f"ORD_{self.fill_counter:06d}"
        
        fill_event = FillEvent(
            symbol=symbol,
            datetime=dt,
            quantity=order_event.quantity,
            direction=order_event.direction,
            fill_price=fill_price,
            commission=commission,
            order_id=order_id
        )
        
        return fill_event
```

### 组装：完整的事件驱动回测引擎

将所有组件组装在一起，形成完整的事件驱动回测引擎：

```python
class EventDrivenBacktester:
    """事件驱动回测引擎"""
    
    def __init__(self, data_handler, strategy, portfolio, execution_handler, event_queue):
        self.data_handler = data_handler
        self.strategy = strategy
        self.portfolio = portfolio
        self.execution_handler = execution_handler
        self.event_queue = event_queue
        
        self.signals_count = 0
        self.orders_count = 0
        self.fills_count = 0
    
    def run(self):
        """
        执行事件驱动回测的主循环
        """
        print("开始事件驱动回测...")
        
        # 1. 初始化：将所有市场数据事件加入队列
        while self.data_handler.continue_backtest:
            market_event = self.data_handler.update_bars()
            if market_event:
                self.event_queue.put(market_event)
        
        print(f"共加载 {len(self.event_queue)} 个市场数据点")
        
        # 2. 主事件循环
        step = 0
        while not self.event_queue.is_empty():
            event = self.event_queue.get()
            
            if event.type == EventType.MARKET:
                # 市场数据到达 → 策略分析
                self.strategy.calculate_signals(event)
                
                # 更新投资组合市值（按当前收盘价）
                prices = {}
                if event.close:
                    prices[event.symbol] = event.close
                self.portfolio.update_market_value(event.datetime, prices)
            
            elif event.type == EventType.SIGNAL:
                # 策略产生信号 → 生成订单
                self.signals_count += 1
                symbol = event.symbol
                
                if event.signal_type == 'LONG':
                    # 计算可买入股数（假设全仓买入）
                    current_price = event.close if hasattr(event, 'close') else 100
                    if current_price and current_price > 0:
                        # 考虑手续费后每手约买多少股（以100股为1手）
                        shares_per_lot = 100
                        lots = int(self.portfolio.cash / (current_price * shares_per_lot * 
                                 (1 + self.execution_handler.commission_rate)))
                        quantity = lots * shares_per_lot
                    else:
                        quantity = 0
                    
                    order = OrderEvent(symbol, 'MARKET', quantity, 'BUY', event.datetime)
                    self.event_queue.put(order)
                    self.orders_count += 1
                
                elif event.signal_type == 'EXIT':
                    # 清仓
                    quantity = self.portfolio.get_position(symbol)
                    if quantity > 0:
                        order = OrderEvent(symbol, 'MARKET', quantity, 'SELL', event.datetime)
                        self.event_queue.put(order)
                        self.orders_count += 1
            
            elif event.type == EventType.ORDER:
                # 订单等待执行 → 模拟成交
                symbol = event.symbol
                dt = event.datetime
                
                # 获取当前市场价格
                bars = self.data_handler.get_latest_bars(symbol, N=1)
                if bars is not None and len(bars) > 0 and 'close' in bars.columns:
                    current_price = bars['close'].iloc[-1]
                else:
                    current_price = 100
                
                # 执行订单
                fill = self.execution_handler.execute_order(event, current_price)
                self.event_queue.put(fill)
                self.fills_count += 1
            
            elif event.type == EventType.FILL:
                # 成交确认 → 更新投资组合
                self.portfolio.update_on_fill(event)
            
            step += 1
        
        print(f"回测完成！共处理 {step} 个事件")
        print(f"信号: {self.signals_count}, 订单: {self.orders_count}, 成交: {self.fills_count}")
    
    def generate_report(self) -> Dict:
        """生成回测报告"""
        if not self.portfolio.equity_curve:
            return {'error': '无回测数据'}
        
        # 净值曲线
        equity_df = pd.DataFrame(
            self.portfolio.equity_curve, 
            columns=['datetime', 'equity']
        )
        equity_df.set_index('datetime', inplace=True)
        equity_df['returns'] = equity_df['equity'].pct_change()
        
        # 计算绩效指标
        daily_returns = equity_df['returns'].dropna()
        trading_days = 252
        
        total_return_pct = ((equity_df['equity'].iloc[-1] / self.portfolio.initial_capital) - 1) * 100
        ann_return = ((equity_df['equity'].iloc[-1] / self.portfolio.initial_capital) ** 
                      (trading_days / len(daily_returns)) - 1) * 100
        ann_vol = daily_returns.std() * np.sqrt(trading_days) * 100
        
        sharpe = (daily_returns.mean() / daily_returns.std()) * np.sqrt(trading_days) if daily_returns.std() > 0 else 0
        
        # 最大回撤
        rolling_max = equity_df['equity'].expanding().max()
        drawdowns = (equity_df['equity'] - rolling_max) / rolling_max
        max_dd = drawdowns.min() * 100
        
        # 交易统计
        trades = self.portfolio.trade_history
        trade_count = len(trades)
        
        report = {
            '初始资金': self.portfolio.initial_capital,
            '最终净值': equity_df['equity'].iloc[-1],
            '总收益率 (%)': f"{total_return_pct:.2f}",
            '年化收益率 (%)': f"{ann_return:.2f}",
            '年化波动率 (%)': f"{ann_vol:.2f}",
            '夏普比率': f"{sharpe:.3f}",
            '最大回撤 (%)': f"{max_dd:.2f}",
            '交易次数': trade_count,
            '总手续费': f"{self.portfolio.total_commission:.2f}",
        }
        
        return report
```

### 完整回测示例

```python
def run_event_driven_backtest_demo():
    """事件驱动回测完整示例"""
    # 生成模拟数据
    np.random.seed(42)
    dates = pd.date_range('2018-01-01', '2022-12-31', freq='B')
    n = len(dates)
    
    # 模拟价格
    trend = np.linspace(0, 0.4, n)
    noise = np.random.randn(n).cumsum() * 0.12
    prices = 100 * np.exp(trend + noise)
    
    # 构建DataFrame
    df = pd.DataFrame({
        'open': prices * (1 + np.random.randn(n) * 0.003),
        'high': prices * (1 + abs(np.random.randn(n) * 0.005)),
        'low': prices * (1 - abs(np.random.randn(n) * 0.005)),
        'close': prices,
        'volume': np.random.randint(500000, 5000000, n)
    }, index=dates)
    
    # 创建事件队列
    event_queue = EventQueue()
    
    # 创建数据处理器
    data_handler = HistoricCSVDataHandler(df)
    
    # 创建策略
    strategy = MovingAverageCrossStrategy(
        data_handler, event_queue, 
        short_window=20, long_window=60
    )
    
    # 创建投资组合
    portfolio = Portfolio(data_handler, event_queue, initial_capital=1000000)
    
    # 创建执行处理器
    execution_handler = SimulatedExecutionHandler(
        event_queue, data_handler,
        commission_rate=0.0003,
        slippage_bps=1.0
    )
    
    # 创建回测引擎
    backtester = EventDrivenBacktester(
        data_handler, strategy, portfolio, execution_handler, event_queue
    )
    
    # 运行回测
    backtester.run()
    
    # 生成报告
    report = backtester.generate_report()
    
    print("\n" + "=" * 50)
    print("事件驱动回测绩效报告")
    print("=" * 50)
    for key, value in report.items():
        print(f"{key}: {value}")
    
    return backtester, report

# 运行示例
backtester, report = run_event_driven_backtest_demo()
```

### 事件驱动回测的进阶话题

#### 动态止损

在事件驱动框架中实现动态止损非常自然，可以在每次接收到市场数据时检查：

```python
class StrategyWithStopLoss(Strategy):
    """带止损的策略"""
    def __init__(self, data_handler, event_queue, stop_loss_pct=0.05):
        super().__init__(data_handler, event_queue)
        self.stop_loss_pct = stop_loss_pct
        self.entry_prices = {}  # {symbol: entry_price}
    
    def check_stop_loss(self, event: MarketEvent):
        """检查是否需要触发止损"""
        symbol = event.symbol
        current_price = event.close
        
        if symbol in self.entry_prices:
            entry_price = self.entry_prices[symbol]
            pnl_pct = (current_price - entry_price) / entry_price
            
            if pnl_pct <= -self.stop_loss_pct:
                # 触发止损
                signal = SignalEvent(symbol, event.datetime, 'EXIT', 1.0)
                self.event_queue.put(signal)
                del self.entry_prices[symbol]
                return True
        
        return False
```

#### 仓位管理

事件驱动框架中可以灵活实现各种仓位管理策略：

```python
class PositionSizer:
    """仓位管理模块"""
    
    @staticmethod
    def fixed_fraction(portfolio_value, price, fraction=1.0):
        """固定比例仓位"""
        capital = portfolio_value * fraction
        return int(capital / price / 100) * 100  # 取整手
    
    @staticmethod
    def kelly_criterion(portfolio_value, price, win_rate, win_loss_ratio):
        """凯利公式仓位"""
        f = win_rate - ((1 - win_rate) / win_loss_ratio)
        f = max(0, min(f, 0.25))  # 限制最大仓位25%
        capital = portfolio_value * f
        return int(capital / price / 100) * 100
    
    @staticmethod
    def volatility_targeting(portfolio_value, price, volatility, target_vol=0.15):
        """波动率目标仓位管理"""
        if volatility == 0:
            return 0
        leverage = target_vol / volatility
        effective_leverage = min(leverage, 3.0)  # 限制杠杆
        capital = portfolio_value * effective_leverage
        return int(capital / price / 100) * 100
```

### 性能优化考虑

事件驱动回测通常比向量化回测慢得多，以下是一些优化策略：

1. **最小化Python函数调用**：将热点代码（如信号计算）用向量化方式批量预计算
2. **延迟事件生成**：不需要为每个时间点都创建MarketEvent，可以按需创建
3. **使用Cython/Numba**：对计算密集型部分使用编译优化
4. **减少不必要的数据拷贝**：传递引用而非深拷贝
5. **批量处理**：将多个相同的操作合并为一次处理

### 总结

事件驱动回测是进行精细策略验证的利器。它的优势在于：

1. **高仿真度**：模拟了真实交易系统的运作方式
2. **灵活建模**：可以精确建模滑点、手续费、订单类型等
3. **易于扩展**：添加新的事件类型或新的组件非常简单
4. **无前视偏差**：天然避免了前视偏差问题

但它也有明显的缺点：
1. **速度慢**：事件循环逐条处理，比向量化慢很多
2. **代码复杂**：组件多，调试困难
3. **内存消耗大**：所有事件保持在队列中

**建议的工作流程**：向量化回测用于快速筛选策略想法 → 事件驱动回测用于最终验证和精细化分析 → 实盘模拟（纸交易） → 小资金实盘 → 正式实盘。
