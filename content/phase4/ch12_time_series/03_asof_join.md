## ASOF Join — 时间序列精确对齐

ASOF Join（近似时间连接）是时序数据库中最强大的连接方式之一。在金融量化领域，经常需要将两个时间序列按"最接近的前一条记录"进行对齐——而ASOF Join正是为此而生的。

---

### 一、什么是ASOF Join

标准的关系型数据库的JOIN只支持精确匹配，但在时序场景中，精确匹配往往不现实：

```
问题场景：将每日9:30发布的因子信号对齐到当日的逐笔交易数据
         → 因子信号的时间戳(9:30) ≠ 逐笔交易的时间戳(9:30:00.123)
         → 需要找到 ≤ 交易时间的最接近的因子信号
```

ASOF Join的逻辑：对于左表的每一条记录，在右表中找到**时间 ≤ 左表时间，且最接近**的那条记录。

```
左表（交易）              右表（因子信号）           ASOF JOIN 结果
T1: 09:30:05               S1: 09:29:59            T1 ← S1 (09:29:59 ≤ 09:30:05)
T2: 09:30:15               S2: 09:30:10            T2 ← S2 (09:30:10 ≤ 09:30:15，比S1更近)
T3: 09:30:25                                      T3 ← S2 (09:30:10 ≤ 09:30:25)
```

---

### 二、ASOF Join 语法

DolphinDB中的`aj`（Asof Join）函数语法简洁高效：

```sql
// aj 基本语法
aj(leftTable, rightTable, matchingCols, [rightSuffix])

// 参数说明：
// leftTable:   左表（驱动表）
// rightTable:  右表（被查询表）
// matchingCols: 匹配列，最后一个列必须是时间列（升序）
```

#### 2.1 基础用法

```sql
// 示例：将每日因子信号对齐到日频收益
daily_returns = select date, symbol, close / prev(close) - 1 as ret
    from daily_data context by symbol

factor_signals = select date, symbol, factor_value
    from factor_table

// ASOF Join：按symbol匹配，按date查找最近的前一条因子信号
aligned = select
    ret.date,
    ret.symbol,
    ret.ret,
    sig.factor_value
from aj(
    daily_returns as ret,
    factor_signals as sig,
    `symbol`date
)
```

---

### 三、金融场景实战应用

#### 3.1 因子信号对齐（最常见场景）

在因子研究中，必须严格避免"前视偏差"（Look-Ahead Bias）——不能用今天的因子信号去预测已经发生的收益。

```sql
// 正确做法：使用aj将T日的因子信号对齐到T+1日的收益
// 因子信号日期为T → 应对齐到T+1到T+N的收益

def prepareFactorData(factor_table, price_table, forward_days){
    // 步骤1：生成未来收益序列
    future_returns = select
        date,
        symbol,
        log(move(close, forward_days) / close) as fwd_return   // T+forward_days的收益
    from price_table
    context by symbol

    // 步骤2：用aj将因子对齐到未来收益的起始日
    return select
        f.date,
        f.symbol,
        f.fwd_return,
        fac.factor_value
    from aj(
        future_returns as f,
        factor_table as fac,
        `symbol`date
    )
    where fac.factor_value != NULL
}
```

#### 3.2 逐笔交易对齐行情快照

```sql
// 将逐笔成交数据对齐到最近的前一条行情快照
// trades: 逐笔成交（含成交价、成交量、时间戳）
// quotes: 行情快照（含买一价、卖一价、时间戳）

aligned_ticks = select
    t.timestamp,
    t.symbol,
    t.price as trade_price,
    t.volume as trade_volume,
    q.bid1,
    q.ask1,
    // 判断成交方向
    iif(t.price >= q.ask1, '主动买入',
    iif(t.price <= q.bid1, '主动卖出', '中性')) as direction,
    // 计算有效价差
    (q.ask1 - q.bid1) / ((q.ask1 + q.bid1) / 2) * 10000 as spread_bps
from aj(
    select * from trades where date = 2024.01.15 order by timestamp as t,
    select * from quotes where date = 2024.01.15 order by timestamp as q,
    `symbol`timestamp
)
```

#### 3.3 财务数据前向填充

```sql
// 将季度财务数据填充到每日（前向填充）
// 每只股票只有4个季度报告日，但需要每日都有财务数据

daily_with_financials = select
    d.date,
    d.symbol,
    d.close,
    f.eps,
    f.net_income,
    f.total_assets,
    // 利用aj自动找到最近的前一期财报
    f.eps / d.close as earnings_yield   // 盈利收益率
from aj(
    select * from daily_data order by date as d,
    select * from quarterly_financials order by date as f,
    `symbol`date
)
```

---

### 四、ASOF Join 进阶用法

#### 4.1 窗口ASOF Join（wj）

```sql
// wj (window join)：在指定时间窗口内做ASOF Join
// 比aj多一个窗口范围参数

// 示例：只对齐前5分钟内的行情快照（超过5分钟不匹配）
aligned = select * from wj(
    trades,
    quotes,
    -5m:0,                    // 窗口：[-5分钟, 0]（只往前看5分钟）
    <price, volume>,
    `symbol`timestamp
)
```

#### 4.2 与计算列结合

```sql
// aj结果直接用于计算
select
    date,
    symbol,
    close,
    signal_value,
    // 基于对齐后的信号计算仓位
    iif(signal_value > 0, close, NULL) as entry_price,
    close / move(close, 1) - 1 as daily_ret,
    // 使用对齐后的信号值做条件判断
    iif(signal_value > 0 and signal_value > prev(signal_value), close, NULL) as breakout_price
from aj(
    daily_data,
    signal_data,
    `symbol`date
)
```

#### 4.3 多表级联ASOF Join

```sql
// 场景：将逐笔成交 → 对齐行情快照 → 对齐因子信号
step1 = select
    t.timestamp, t.symbol, t.price, t.volume,
    q.bid1, q.ask1
from aj(trades, quotes, `symbol`timestamp)

step2 = select
    s1.timestamp, s1.symbol, s1.price, s1.volume,
    s1.bid1, s1.ask1,
    f.factor_value
from aj(
    step1 as s1,
    factor_signals as f,
    `symbol`timestamp
)
```

---

### 五、性能与最佳实践

| 注意点 | 说明 |
|--------|------|
| **右表必须排序** | aj要求右表按匹配列排序（特别是最后一个时间列），否则结果错误 |
| **分区表支持** | DolphinDB 2.0+支持分区表的aj操作，效率极高 |
| **内存控制** | 大数据量的aj建议分批处理，避免全表加载内存 |
| **与SQL配合** | aj返回的是表，可在外层继续用SQL筛选、聚合和计算 |

> **核心价值**：ASOF Join是量化研究中"防止前视偏差"的关键工具。通过`aj`将T日的因子值精确对齐到T+1及以后的收益，确保回测的严谨性。这是手工编程最易出错的地方，而DolphinDB的一个函数调用即可完美解决。
