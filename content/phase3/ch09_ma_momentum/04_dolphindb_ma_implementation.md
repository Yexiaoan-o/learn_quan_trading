## DolphinDB中的均线策略实现

DolphinDB 是一个高性能的分布式时序数据库，专门为金融数据分析和量化交易设计。其内置的向量化函数和SQL引擎使得均线策略的实现非常简洁高效。

### DolphinDB的核心优势

| 特性 | 说明 | 对均线策略的意义 |
|------|------|-----------------|
| 向量化计算 | 整列操作而非逐行循环 | 一次性计算整列的移动平均 |
| 内存列式存储 | 按列存储，CPU缓存友好 | 大容量数据的均线计算极快 |
| 流数据引擎 | 内置实时流计算框架 | 实时均线信号毫不费力 |
| 分布式扩展 | 自动数据分片和并行计算 | 数千只股票同时计算均线 |

---

### 一、DolphinDB中的移动平均函数

#### `mavg` — 移动平均

DolphinDB 提供了多种移动窗口函数，`mavg` 是最基础的：

```sql
-- DolphinDB 语法：mavg(X, window)

-- 示例1：计算单只股票的5日、20日均线
t = table(
    2024.01.01 + 0..99 as tradeDate,
    rand(50.0, 100) + 100.0 as close
)

-- 使用 mavg 计算移动平均
select 
    tradeDate,
    close,
    mavg(close, 5) as ma_5,
    mavg(close, 20) as ma_20
from t
```

#### `wma` — 加权移动平均

```sql
-- 加权移动平均：wma(X, window, [weights])
-- 默认使用线性递减权重

select 
    tradeDate,
    close,
    wma(close, 10) as wma_10
from t
```

#### `ema` — 指数移动平均

```sql
-- 指数移动平均：ema(X, window)
-- 平滑因子 alpha = 2/(window+1)

select 
    tradeDate,
    close,
    ema(close, 5) as ema_5,
    ema(close, 20) as ema_20
from t
```

### 二、DolphinDB SQL中的均线策略实现

下面展示如何在 DolphinDB 中完整实现一个双均线交叉策略：

```sql
-- ==========================================
-- DolphinDB双均线交叉策略
-- ==========================================

-- 1. 创建模拟的股票日线数据表
n = 252  -- 一年的交易日
tradeDate = 2024.01.01 + 0..(n-1)
close = 100.0 + cumsum(rand(0.5, n) - 0.2)  -- 带趋势的随机游走
volume = rand(1000000.0, n) + 500000.0

t = table(tradeDate as date, close, volume)

-- 2. 计算均线和信号
result = select 
    date,
    close,
    -- 计算双均线
    mavg(close, 5) as ma_5,
    mavg(close, 20) as ma_20,
    -- 生成持仓信号: 短 > 长 时持仓
    iif(mavg(close, 5) > mavg(close, 20), 1, 0) as position
from t

-- 3. 生成交易信号（持仓变化即为交易信号）
result = select 
    date,
    close,
    ma_5,
    ma_20,
    position,
    -- 信号 = 当日持仓 - 前日持仓
    position - prev(position) as signal
from result

-- 4. 仅保留有信号的交易日
signal_days = select date, close, signal 
from result 
where signal != 0

select * from signal_days
```

### 三、多股票批量计算

DolphinDB 的向量化设计使得同时计算多只股票的均线非常简单：

```sql
-- 创建多只股票的日线数据
n_symbols = 100
n_days = 252

dates = take(2024.01.01 + 0..(n_days-1), n_symbols)
symbols = take("A" + string(1..n_symbols), n_days).sort()
close = rand(150.0, n_symbols * n_days) + 50.0
volume = rand(10000000.0, n_symbols * n_days) + 1000000.0

stock_daily = table(dates as date, symbols as symbol, close, volume)

-- 按股票分组计算均线
result = select
    date,
    symbol,
    close,
    mavg(close, 5) as ma_5,
    mavg(close, 20) as ma_20,
    mavg(close, 60) as ma_60,
    -- 多周期均线排列关系
    iif(mavg(close, 5) > mavg(close, 20) 
        and mavg(close, 20) > mavg(close, 60), 1, 0) as bullish_alignment,
    iif(mavg(close, 5) < mavg(close, 20) 
        and mavg(close, 20) < mavg(close, 60), 1, 0) as bearish_alignment
from stock_daily
context by symbol  -- 按股票代码分组计算
```

### 四、使用 `moving` 函数进行高级窗口计算

```sql
-- DolphinDB的moving函数支持自定义窗口计算
-- 可以定义更复杂的均线变体

-- 1. Hull Moving Average (HMA) — 减少滞后的均线
def calcHMA(price, period) {
    halfPeriod = floor(period / 2)
    sqrtPeriod = floor(sqrt(period))
    // HMA = WMA(2 * WMA(n/2) - WMA(n), sqrt(n))
    wma1 = wma(price, halfPeriod) * 2
    wma2 = wma(price, period)
    return wma(wma1 - wma2, sqrtPeriod)
}

select date, close, calcHMA(close, 20) as hma_20 from t

-- 2. 均线斜率计算
select 
    date,
    close,
    ma_20 = mavg(close, 20),
    // 斜率 = (当前MA - 5天前MA) / 5
    ma_slope = (mavg(close, 20) - mavg(close, 20)[5]) / 5.0
from t

-- 3. 均线交叉检测
select
    date,
    close,
    ma_5 = mavg(close, 5),
    ma_20 = mavg(close, 20),
    // 金叉: 前日MA5 <= MA20 且 当日MA5 > MA20
    golden_cross = iif(mavg(close, 5) > mavg(close, 20) 
                       and prev(mavg(close, 5)) <= prev(mavg(close, 20)), 1, 0),
    // 死叉: 前日MA5 >= MA20 且 当日MA5 < MA20
    death_cross = iif(mavg(close, 5) < mavg(close, 20) 
                      and prev(mavg(close, 5)) >= prev(mavg(close, 20)), 1, 0)
from t
```

### 五、使用 DolphinDB 自定义函数封装策略

```sql
-- 封装双均线策略为函数
def dualMACrossover(symbol_data, short_window, long_window, ma_type="sma") {
    /*
    symbol_data: 单只股票的数据表，含 date, close 列
    short_window: 短期均线参数
    long_window: 长期均线参数
    ma_type: 均线类型，"sma" 或 "ema"
    */
    
    if (ma_type == "sma") {
        ma_short = mavg(symbol_data.close, short_window)
        ma_long = mavg(symbol_data.close, long_window)
    } else if (ma_type == "ema") {
        ma_short = ema(symbol_data.close, short_window)
        ma_long = ema(symbol_data.close, long_window)
    }
    
    position = iif(ma_short > ma_long, 1, 0)
    signal = position - prev(position)
    
    return table(
        symbol_data.date as date,
        symbol_data.close as close,
        ma_short as ma_short,
        ma_long as ma_long,
        position as position,
        signal as signal
    )
}

-- 调用自定义策略函数
strategy_result = dualMACrossover(
    select date, close from stock_daily where symbol = "A1",
    short_window = 5,
    long_window = 20,
    ma_type = "ema"
)

-- 查看最新信号
select top 20 * from strategy_result
```

### 六、DolphinDB 中的增量计算

对于流数据处理，DolphinDB 支持增量式的均线计算：

```sql
-- 使用流数据引擎进行实时均线计算
// 定义输出表
share streamTable(100:0, `symbol`date`close`ma_5`ma_20, 
                  [SYMBOL, DATE, DOUBLE, DOUBLE, DOUBLE]) as maOutput

// 定义时间序列引擎
tsEngine = createTimeSeriesEngine(
    name="maEngine",
    windowSize=20,     // 窗口大小
    step=1,            // 计算步长
    metrics=[
        <close>,              // 原始价格
        <mavg(close, 5)>,    // 5日均线
        <mavg(close, 20)>    // 20日均线
    ],
    dummyTable=table(100:0, `symbol`date`close, 
                     [SYMBOL, DATE, DOUBLE]),
    outputTable=maOutput,
    timeColumn=`date,
    keyColumn=`symbol
)

// 订阅流数据并推到引擎
subscribeTable(
    tableName="streamData",
    actionName="calcMA",
    handler=tsEngine,
    msgAsTable=true
)
```

### 七、性能对比

```sql
-- DolphinDB中均线计算的性能示例
-- 1000只股票、10年日线数据（约250万行）

timer {
    result = select
        symbol,
        date,
        close,
        mavg(close, 5) as ma_5,
        mavg(close, 20) as ma_20,
        mavg(close, 60) as ma_60,
        mavg(close, 120) as ma_120
    from stock_daily
    context by symbol
}

-- 在DolphinDB中，上述计算通常在毫秒级完成
-- 而Python pandas处理同样的数据通常需要数秒到数十秒
```

> **关键对比**：DolphinDB 的向量化均线计算比 Python pandas 快 10-100 倍，这是因为：（1）C++ 底层实现，避免了 Python 解释器开销；（2）列式存储使 CPU 缓存效率最大化；（3）内置的 `context by` 分组避免了 Python 中 groupby-apply 的开销。

### 八、Python 调用 DolphinDB 实现策略

```python
import dolphindb as ddb

# 连接 DolphinDB 服务器
s = ddb.session()
s.connect("localhost", 8848, "admin", "123456")

# 在DolphinDB中运行均线策略脚本
script = '''
n = 252
tradeDate = 2024.01.01 + 0..(n-1)
close = 100.0 + cumsum(rand(0.5, n) - 0.2)
t = table(tradeDate as date, close)

result = select 
    date,
    close,
    mavg(close, 5) as ma_5,
    mavg(close, 20) as ma_20
from t
'''

# 执行脚本并获取结果
result = s.run(script)
print(result)
```

> **学习建议**：熟练掌握 DolphinDB 的 `mavg`、`ema`、`wma` 函数和 `context by` 分组语法，是高效实现均线策略的基础。建议先在单只股票上验证逻辑，再扩展到多股票批量计算。
