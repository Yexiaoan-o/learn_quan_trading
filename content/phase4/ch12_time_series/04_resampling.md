## 时序数据重采样

在量化交易中，经常需要将数据从一个时间频率转换到另一个——将tick级数据聚合成分钟K线、将日线数据降采样为周线、或将月度数据上采样到日频。DolphinDB提供了多种灵活的重采样工具。

---

### 一、重采样的基本概念

```
降采样（Downsampling）   上采样（Upsampling）
   高频 → 低频              低频 → 高频
   tick → 1分钟K线          季报 → 日频数据
   1分钟 → 5分钟K线          年报 → 月频数据
```

量化交易中最常见的操作是**从tick数据生OLC K线**（降采样）：

```sql
// 从tick（逐笔成交）数据生成1分钟K线
select
    bar(timestamp, 1m) as bar_time,
    first(price) as open,
    max(price) as high,
    min(price) as low,
    last(price) as close,
    sum(volume) as volume,
    sum(amount) as amount,
    count(*) as tick_count
from tick_data
where symbol = '000001.SZ' and date = 2024.01.15
group by bar(timestamp, 1m)
```

---

### 二、bar函数 — 时间桶聚合

`bar`函数是DolphinDB中最核心的重采样函数，它将时间戳向下取整到指定时间桶的边界：

```sql
// bar函数基础用法
// bar(timestamp, interval) — 将时间戳对齐到指定周期的整点

ts = [09:30:05, 09:30:45, 09:31:15, 09:31:50, 09:35:10]

bar(ts, 1m)      // 结果: [09:30m, 09:30m, 09:31m, 09:31m, 09:35m]
bar(ts, 5m)      // 结果: [09:30m, 09:30m, 09:30m, 09:30m, 09:35m]
bar(ts, 10m)     // 结果: [09:30m, 09:30m, 09:30m, 09:30m, 09:30m]

// bar支持的周期单位
// ms(毫秒), s(秒), m(分钟), H(小时), D(天), W(周), M(月), Q(季度), Y(年)
```

#### 2.1 生成多频率K线

```sql
// 从1分钟tick数据同时生成5分钟、15分钟、30分钟K线
// 使用 array vector 高效存储多级K线

minute_ticks = select
    timestamp,
    bar(timestamp, 5m) as bar_5m,
    bar(timestamp, 15m) as bar_15m,
    bar(timestamp, 30m) as bar_30m,
    price,
    volume
from tick_data
where date = 2024.01.15 and symbol = '000001.SZ'


// 生成5分钟K线
kline_5m = select
    bar_5m as datetime,
    first(price) as open,
    max(price) as high,
    min(price) as low,
    last(price) as close,
    sum(volume) as volume
from minute_ticks
group by bar_5m
order by bar_5m

// 也可在一次查询中生成多个频率的K线（利用context by）
select
    bar(timestamp, 5m) as bar_5m,
    bar(timestamp, 15m) as bar_15m,
    price as px,
    volume as vol
from tick_data
```

#### 2.2 自定义开始时间

```sql
// A股开盘时间是09:30，但bar默认从00:00开始对齐
// 使用 bar 的 offset 参数或自行调整

// 方法1：减去开盘时间后再做bar
select
    bar(timestamp - 09:30:00.000, 5m) + 09:30:00.000 as bar_time,
    first(price) as open,
    max(price) as high,
    min(price) as low,
    last(price) as close,
    sum(volume) as volume
from tick_data
where symbol = '000001.SZ'
group by bar(timestamp - 09:30:00.000, 5m)
order by bar_time
```

---

### 三、窗口连接 (wj) — 高级重采样

`wj`（Window Join）比`bar`+`group by`更灵活，适合需要在窗口内自定义聚合逻辑的场景：

```sql
// 场景：计算每个5分钟窗口内的VWAP（成交量加权平均价）

// 定义聚合函数
metrics = <[
    sum(volume) as total_volume,
    sum(price * volume) as turnover,
    sum(price * volume) / sum(volume) as vwap,
    max(price) as high,
    min(price) as low
]>

// wj: 左表提供时间窗口边界，右表提供数据
left_table = table(
    temporalAdd(2024.01.15T09:30:00.000, 0..47 * 5 * 60000, 'ms') as timestamp
)

result = wj(
    left_table,
    tick_data,
    -5m:-1,                // 窗口范围为 [当前时间-5分钟, 当前时间-1毫秒]
    metrics,
    `symbol`timestamp
)
```

---

### 四、灵活的分组重采样

#### 4.1 按自定义规则分组

```sql
// 按交易时段分组：上午盘 vs 下午盘
select
    symbol,
    iif(time(timestamp) < 12:00:00.000, '上午', '下午') as session,
    first(price) as open,
    max(price) as high,
    min(price) as low,
    last(price) as close,
    sum(volume) as volume,
    sum(amount) as amount
from tick_data
where date = 2024.01.15
group by symbol, iif(time(timestamp) < 12:00:00.000, '上午', '下午')
```

#### 4.2 成交量K线（Volume Bars）

```sql
// 成交量K线：每当累计成交量达到指定阈值时生成一根K线
// 例如：每成交100万股生成一根K线
def volumeBars(tick_data, vol_threshold){
    update tick_data set cum_vol = cumsum(volume) context by symbol
    update tick_data set vbar = floor(cum_vol / vol_threshold) context by symbol

    return select
        symbol,
        first(vbar) as bar_index,
        first(timestamp) as start_time,
        last(timestamp) as end_time,
        first(price) as open,
        max(price) as high,
        min(price) as low,
        last(price) as close,
        sum(volume) as volume,
        sum(amount) as amount,
        count(*) as tick_count
    from tick_data
    group by symbol, vbar
}
```

---

### 五、上采样与填充策略

从低频到高频的上采样通常需要填充策略：

```sql
// 将季度财报数据上采样到日频（前向填充）
quarterly = select date, symbol, eps, roe from quarterly_data
daily = select distinct date, symbol from daily_data

// 用aj实现前向填充（找到最近的前一期财报）
daily_filled = select
    d.date,
    d.symbol,
    q.eps,
    q.roe
from aj(
    daily as d,
    quarterly as q,
    `symbol`date
)

// 前向填充后，EPS和ROE在整个季度内保持不变
// T期12月31日报的EPS，会在T+1期1月1日~3月30日的数据中都填充该EPS值
```

---

### 六、重采样策略对比

| 方法 | 适用场景 | 优点 | 缺点 |
|------|----------|------|------|
| **bar + group by** | 生成标准K线 | 简单直观、性能好 | 灵活性有限 |
| **wj (Window Join)** | 自定义窗口聚合 | 灵活、支持复杂聚合 | 语法相对复杂 |
| **aj (ASOF Join)** | 上采样（前向填充） | 精确控制对齐逻辑 | 仅做对齐，不做聚合 |

> **实践建议**：对于90%的重采样需求，`bar` + `group by`就足够了。当需要非标准的聚合逻辑（如VWAP、时间加权平均）时，再考虑使用`wj`。上采样对齐数据时，`aj`是首选工具。
