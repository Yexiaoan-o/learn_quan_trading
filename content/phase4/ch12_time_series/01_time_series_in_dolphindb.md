## DolphinDB中的时序数据基础

金融数据本质上是时间序列数据——每笔交易、每个价格、每份财报都带有时间戳。DolphinDB作为专为金融时序数据设计的数据平台，提供了丰富的时间类型和时序处理函数。本章将系统介绍DolphinDB中的时序数据类型、时间索引和基础操作。

---

### 一、时间类型概览

DolphinDB提供了多种时间相关数据类型，满足从纳秒级高频数据到年度低频数据的需求：

| 数据类型 | 精度 | 格式示例 | 用途 |
|----------|------|----------|------|
| **DATE** | 日 | 2024.01.15 | 日频数据日期 |
| **MONTH** | 月 | 2024.01M | 月度报告日期 |
| **TIME** | 毫秒 | 14:30:00.000 | 日内时间点 |
| **MINUTE** | 分钟 | 14:30m | 分钟级数据 |
| **SECOND** | 秒 | 14:30:00 | 秒级数据 |
| **TIMESTAMP** | 毫秒 | 2024.01.15T14:30:00.000 | 日+时间的完整时间戳 |
| **NANOTIMESTAMP** | 纳秒 | 2024.01.15T14:30:00.000000001 | 高频交易时间戳 |
| **DATETIME** | 秒 | 2024.01.15T14:30:00 | 日期时间（秒精度） |

```sql
// 时间类型的创建与转换
date1 = 2024.01.15                            // DATE类型
time1 = 14:30:00.500                          // TIME类型（含毫秒）
ts1 = timestamp(2024.01.15T14:30:00.500)      // TIMESTAMP类型
nts1 = nanotimestamp(2024.01.15T14:30:00.500000001)  // NANOTIMESTAMP

// 类型转换函数
dt = date(ts1)                                 // TIMESTAMP → DATE
tm = time(ts1)                                 // TIMESTAMP → TIME
ts = timestamp(date1 + time1)                  // DATE + TIME → TIMESTAMP
```

---

### 二、时序数据的组织方式

DolphinDB中的时序数据通常以时间列作为分区键或排序键进行组织：

```sql
// 创建日频股票数据表
daily_table = table(
    1000:0,
    `symbol`date`open`high`low`close`volume`amount,
    [SYMBOL, DATE, DOUBLE, DOUBLE, DOUBLE, DOUBLE, LONG, DOUBLE]
)

// 按日期范围查询
select * from daily_table
where date between 2024.01.01 : 2024.01.31
    and symbol = '000001.SZ'
order by date
```

#### 2.1 时间范围生成

DolphinDB提供了便捷的时间范围生成函数，适合批量创建交易日历：

```sql
// 生成日期范围
dates = 2024.01.01..2024.12.31                // 日期间隔1天

// 使用 temporalAdd 生成自定义间隔的日期
quarter_dates = temporalAdd(2024.01.01, 0..3 * 3, 'M')   // 季度日期
weekly_dates = temporalAdd(2024.01.01, 0..51 * 7, 'D')   // 每周一

// 使用 dateRange 生成指定时间段
trading_days = dateRange(2024.01.01, 2024.12.31, 'D')
```

---

### 三、时间索引与对齐

在时序数据分析中，经常需要将不同频率的数据对齐到统一的时间轴上：

```sql
// 场景：将分钟级因子信号对齐到日频收益数据
daily_returns = select
    date, symbol, close / prev(close) - 1 as daily_ret
from daily_data
context by symbol

// 使用 asof join 对齐最近的前一个信号
// 将15:00的前一个因子值对齐到当日
aligned = select
    d.date,
    d.symbol,
    d.daily_ret,
    s.factor_value
from aj(daily_returns, factor_signals, `date`symbol)
where d.date = s.date
```

---

### 四、不规则时间序列的处理

金融数据中经常遇到非等间距的观测值——财报公布日、突发事件等。处理不规则时序数据需要特殊方法：

```sql
// 模拟不规则时序数据：财报公布日
// 使用前向填充（forward fill）将季度数据扩展到日频

// 方法1：使用 asof join 将最近的前一期财报数据填充到每日
daily_with_quarterly = select
    d.date,
    d.symbol,
    d.close,
    q.eps,
    q.net_income
from aj(
    daily_data,
    select * from quarterly_financials order by date
    , `symbol`date
)

// 方法2：使用 fill 函数前向填充缺失值
select
    date,
    symbol,
    close,
    fill(eps, 'ffill') as eps_filled    // 前向填充
from merged_data
context by symbol
```

---

### 五、交易时段处理

日内策略需要精确处理交易时段：

```sql
// A股交易时段
// 上午：09:30:00 - 11:30:00
// 下午：13:00:00 - 15:00:00

def isTradingTime(t){
    // 判断是否在A股交易时段内
    morning = time(t) between 09:30:00.000 : 11:30:00.000
    afternoon = time(t) between 13:00:00.000 : 15:00:00.000
    return morning || afternoon
}

// 筛选交易时段内的数据
select * from tick_data
where isTradingTime(timestamp)
    and symbol = '000001.SZ'

// 生成交易日时间轴（去除午休时段）
def generateTradingMinutes(tradingDate){
    morning = temporalAdd(tradingDate + 09:30:00.000, 0..120, 'm')
    afternoon = temporalAdd(tradingDate + 13:00:00.000, 0..120, 'm')
    return morning join afternoon
}

// 按交易时段分组统计
select
    bar(timestamp, 5m) as bar_time,
    first(price) as open,
    max(price) as high,
    min(price) as low,
    last(price) as close,
    sum(volume) as volume
from tick_data
where isTradingTime(timestamp) and symbol = '000001.SZ'
group by bar(timestamp, 5m)
```

---

### 六、时序数据操作实践

#### 6.1 数据填充与插值

```sql
// 线性插值：用前后值的线性组合填充缺失数据
select
    date,
    symbol,
    interpolate(close, 'linear') as close_filled   // 线性插值
from daily_data
context by symbol

// 缺失值处理策略对比
select
    date,
    symbol,
    close as original,
    fill(close, 'ffill') as forward_fill,           // 前向填充
    fill(close, 'bfill') as backward_fill,          // 后向填充
    fill(close, 'nearest') as nearest_fill,         // 最近邻填充
    interpolate(close, 'linear') as linear_interp   // 线性插值
from daily_data
context by symbol
```

#### 6.2 时间窗口过滤

```sql
// 滑动窗口：查询滚动60天内的数据
def rollingWindowStats(tbl, windowSize){
    return select
        date,
        symbol,
        close,
        avg(close) over (rows between windowSize preceding and current row) as ma,
        std(close) over (rows between windowSize preceding and current row) as std
    from tbl
    context by symbol
}
```

> **关键要点**：在DolphinDB中处理时序数据时，最佳实践是：(1) 将时间列设置为分区列以提升查询性能；(2) 使用`context by`进行分组时序操作；(3) 善用`temporalAdd`和`dateRange`生成规范的时间序列；(4) 对于不规则数据，优先使用`aj`（asof join）进行时间对齐。
