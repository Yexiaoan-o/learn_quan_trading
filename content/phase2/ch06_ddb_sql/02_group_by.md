## 2.1 GROUP BY 基础

GROUP BY 是数据分析中最核心的操作之一，它将数据按指定列分组，然后对每组执行聚合计算。在量化交易中，GROUP BY 的使用频率极高：

```dolphindb
SELECT groupKeyCol1, groupKeyCol2, ..., aggFunc(valueCol)
FROM tableName
WHERE condition
GROUP BY groupKeyCol1, groupKeyCol2, ...
[HAVING filterCondition]
[ORDER BY ...];
```

### 基本分组示例

```dolphindb
t = loadTable("dfs://stock_day", "kline_day");

// 按股票代码分组，计算每只股票的平均收盘价
select sym, avg(close) as avg_close
from t
where trade_date between 2024.01.01:2024.01.31
group by sym;
```

## 2.2 聚合函数详解

DolphinDB 提供了丰富的内置聚合函数，以下是量化分析中最常用的：

### 常用聚合函数表

| 函数 | 说明 | 量化场景 |
|------|------|---------|
| `avg(x)` | 算术平均值 | 均价、均量 |
| `sum(x)` | 求和 | 总成交额、总成交量 |
| `count(x)` | 计数 | 交易日数、样本数 |
| `max(x)` | 最大值 | 最高价（N日内最值） |
| `min(x)` | 最小值 | 最低价（N日内最值） |
| `std(x)` | 样本标准差 | 波动率计算 |
| `var(x)` | 样本方差 | 波动率分析 |
| `first(x)` | 第一个值 | 期初价格 |
| `last(x)` | 最后一个值 | 期末价格 |
| `med(x)` | 中位数 | 排除极端值 |
| `skew(x)` | 偏度 | 收益率分布分析 |
| `kurtosis(x)` | 峰度 | 肥尾风险衡量 |
| `percentile(x, p)` | 百分位数 | 分位数回测 |

### 多聚合函数组合

```dolphindb
// 一次性计算多个聚合指标
select 
    sym,
    count(close) as trading_days,         // 交易天数
    avg(close) as avg_close,              // 均价
    avg(volume) as avg_volume,            // 均量
    min(close) as min_close,              // 最低价
    max(close) as max_close,              // 最高价
    std(close) as vol_price,              // 价格波动
    first(close) as first_close,          // 期初价
    last(close) as last_close             // 期末价
from t
where trade_date between 2024.01.01:2024.06.30
group by sym;
```

### 计算收益率和风险指标

```dolphindb
// 按股票分组，计算期间收益率和风险指标
select
    sym,
    count(close) as n_days,
    first(close) as start_price,
    last(close) as end_price,
    (last(close) - first(close)) / first(close) * 100 as period_return,   // 期间收益率
    max(close) / min(close) - 1 as max_drawdown_approx,                    // 近似最大回撤
    std(close) / avg(close) as cv                                           // 变异系数
from t
where trade_date between 2024.01.01:2024.06.30
group by sym
order by period_return desc;
```

## 2.3 多键分组

GROUP BY 可以使用多个分组键，形成多维度分析：

```dolphindb
// 按日期 + 行业分组（假设有 industry 列）
select 
    trade_date,
    industry,
    avg(close) as avg_close,
    sum(volume) as total_volume
from t
where trade_date >= 2024.01.01
group by trade_date, industry
order by trade_date, industry;

// 按时段（早盘/午盘/尾盘）+ 股票代码分组
select
    sym,
    iif(hour(time) < 11, "早盘", 
        iif(hour(time) < 14, "午盘", "尾盘")) as session,
    avg(price) as avg_price,
    sum(volume) as total_vol
from tick_table
group by sym, session;
```

## 2.4 HAVING 子句

HAVING 对聚合结果进行过滤，与 WHERE 的区分：

- **WHERE**：在分组**之前**过滤原始行
- **HAVING**：在分组**之后**过滤分组结果

```dolphindb
// WHERE vs HAVING 对比

// WHERE 过滤：只纳入成交量 > 500万 的行参与计算
select sym, avg(close) as avg_close
from t
where volume > 5000000
group by sym;

// HAVING 过滤：计算完所有分组后，只保留交易天数 >= 20 的组
select sym, count(*) as trading_days, avg(close) as avg_close
from t
where trade_date between 2024.01.01:2024.01.31
group by sym
having trading_days >= 20;

// WHERE + HAVING 结合使用
select sym, 
       count(*) as trading_days, 
       avg(close) as avg_close,
       sum(volume) as total_vol
from t
where trade_date between 2024.01.01:2024.06.30   // 限定时间范围
group by sym
having trading_days >= 100 and avg_close > 10.0;  // 过滤交易天数少和低价股
```

### HAVING 实用案例

```dolphindb
// 找出成交量最活跃的股票（日均成交量 > 1000万股）
select 
    sym, 
    count(*) as days,
    avg(volume) as avg_daily_vol,
    avg(close) as avg_close
from t
where trade_date between 2024.01.01:2024.06.30
group by sym
having avg(volume) > 10000000
order by avg_daily_vol desc
limit 20;

// 找出异常波动的股票（日波动率 > 5%）
select 
    sym,
    trade_date,
    (high - low) / pre_close * 100 as daily_range
from t
where trade_date between 2024.01.01:2024.06.30
    and (high - low) / pre_close > 0.05
order by daily_range desc
limit 50;
```

## 2.5 分组计算的性能优化

| 优化策略 | 说明 |
|---------|------|
| **分区裁剪** | WHERE 条件尽可能匹配分区键，减少扫描分区数 |
| **使用 SYMBOL** | 分组键使用 SYMBOL 类型，避免 STRING 的字符串比较 |
| **预计算哈希** | 对固定的分组查询，考虑预聚合 |
| **减少列数** | SELECT 中只选需要的列，减少 IO |

```dolphindb
// 不良写法：全表扫描 + 大数据量
select sym, avg(close) from t group by sym;

// 良好写法：添加分区键过滤
select sym, avg(close) 
from t 
where trade_date >= 2024.01.01   // 利用分区裁剪
group by sym;
```

> **GROUP BY 是将 SQL 从"描述型查询"升级为"分析型查询"的关键**。在量化分析中，几乎所有的因子计算、回测统计、绩效分析都离不开 GROUP BY。熟练掌握聚合函数和多维分组是量化数据处理的基本功。
