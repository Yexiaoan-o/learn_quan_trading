## 3.1 context by 是什么？

`context by` 是 DolphinDB 独有的 SQL 子句，专为**时序数据的分组窗口计算**设计。它与 GROUP BY 最大的区别在于：**context by 保留原始行的顺序和数量，不合并行**。

```
┌───────────────────────────────────────────────────────┐
│           GROUP BY vs CONTEXT BY                    │
│                                                       │
│  GROUP BY：                                     │
│  ┌────┬────┐   ┌───────┐       ┌────┬──────┐        │
│  │sym │val │ → │ 聚合  │  →    │sym │avg   │        │
│  │ A  │ 1  │   └───────┘       │ A  │ 2.5  │        │
│  │ A  │ 4  │                   │ B  │ 6.0  │        │
│  │ B  │ 5  │                   └────┴──────┘        │
│  │ B  │ 7  │                  （行数减少）              │
│  └────┴────┘                                        │
│                                                       │
│  CONTEXT BY：                                   │
│  ┌────┬────┐   ┌──────────────┐  ┌────┬──────┐     │
│  │sym │val │ → │  窗口计算     │  →  │sym │cumsum│     │
│  │ A  │ 1  │   └──────────────┘  │ A  │  1   │     │
│  │ A  │ 4  │                     │ A  │  5   │     │
│  │ B  │ 5  │                     │ B  │  5   │     │
│  │ B  │ 7  │                     │ B  │  12  │     │
│  └────┴────┘                     └────┴──────┘     │
│                              （行数保持不变）           │
└───────────────────────────────────────────────────────┘
```

### 语法

```dolphindb
SELECT column, [aggregateFunction(column), ...]
FROM table
[WHERE condition]
CONTEXT BY groupKey
[HAVING condition]
[LIMIT n];
```

## 3.2 为什么要用 context by？

量化交易中，大量计算需要在**分组内部逐行进行**，同时保持原始行的时序：

- 计算每只股票的**逐日累计收益率**
- 计算每只股票的**滚动窗口指标**（如过去 20 日最高价）
- 获取每只股票**最近 N 天的数据**
- 计算每个行业内的**排名**（rank）

这些需求用 GROUP BY 无法直接完成（GROUP BY 会把组内行压缩为一行），而 context by 完美解决了这个问题。

```dolphindb
// GROUP BY：只能得到每组的汇总值
select sym, avg(close) from t 
group by sym;

// CONTEXT BY：保留每一行，在组内计算
select sym, trade_date, close,
       cumsum(close) as cum_close,           // 组内累计和
       rank(close) as rank_in_group,          // 组内排名
       avg(close) as group_avg                // 组内平均值（每行重复）
from t
context by sym;
```

## 3.3 核心用法示例

### 示例 1：组内排名与筛选

```dolphindb
t = loadTable("dfs://stock_day", "kline_day");

// 获取每只股票成交量最大的3个交易日
select sym, trade_date, volume
from t
where trade_date between 2024.01.01:2024.06.30
context by sym
order by volume desc
limit 5;
// limit 在 context by 中表示"每组取前5条"
```

### 示例 2：获取每组的最后 N 条记录

```dolphindb
// 使用负数 limit：取每组最后 2 条
select sym, trade_date, close, volume
from t
context by sym
limit -2;
// 每组返回最后 2 行（按原始顺序），常用于快速查看最新数据
```

### 示例 3：组内累计计算

```dolphindb
// 计算每只股票收盘价的累计变化
select sym, trade_date, close,
       cumsum(close) as cum_sum,              // 累计和
       cummax(close) as cum_max,              // 滚动最大值
       cummin(close) as cum_min               // 滚动最小值
from t
context by sym;
```

### 示例 4：组内排名

```dolphindb
// 计算每只股票每天在其自身历史中的价格排位
select sym, trade_date, close,
       rank(close) as close_rank,             // 组内排名
       dense_rank(close) as close_dense_rank  // 组内密集排名
from t
where trade_date between 2024.01.01:2024.06.30
context by sym;
```

### 示例 5：mavg 等滚动函数

```dolphindb
// 计算每只股票的 5 日、10 日、20 日移动平均线
select sym, trade_date, close,
       mavg(close, 5) as ma5,                 // 5日均线
       mavg(close, 10) as ma10,               // 10日均线
       mavg(close, 20) as ma20                 // 20日均线
from t
context by sym;
```

## 3.4 context by + HAVING

HAVING 在 context by 中用于过滤组：

```dolphindb
// 只保留有超过 200 个交易日的股票的数据
select sym, trade_date, close
from t
context by sym
having count(close) >= 200;
// 只返回交易日数 >= 200 的股票的所有行

// 只保留组内最大值满足条件的组
select sym, trade_date, close
from t
context by sym
having max(close) > 50.0;
// 返回最高价 > 50 的股票的所有日数据
```

## 3.5 context by vs GROUP BY 对比总结

| 特性 | GROUP BY | CONTEXT BY |
|------|----------|------------|
| 输出行数 | 每组一行 | 与输入行数相同 |
| 列值 | 必须是聚合结果或分组键 | 可以是原始列值 + 聚合值 |
| 时序保留 | 否（无序） | 是（保持原始顺序） |
| 组内排序 | 不可控 | 可通过 ORDER BY 控制 |
| LIMIT 行为 | 限制总行数 | 限制每组行数 |
| 典型场景 | 汇总统计、每日报告 | 时序分析、因子计算、信号生成 |

### 选择指南

```
需要降低维度的"报告式"分析？
  → 使用 GROUP BY
  例：每只股票的平均收益率、每个行业的股票数量

需要保持数据维度的"信号式"计算？  
  → 使用 CONTEXT BY
  例：每只股票的移动平均线、滚动波动率、组内排名
```

## 3.6 量化实战：用 context by 构建信号

```dolphindb
// 案例：构建一个简单的"相对强弱"信号
// 逻辑：当日涨幅高于其 20 日平均涨幅 1.5 倍标准差时，标记为强势
t = loadTable("dfs://stock_day", "kline_day");

result = select 
    sym,
    trade_date,
    close,
    pre_close,
    (close - pre_close) / pre_close * 100 as daily_return,
    avg((close - pre_close) / pre_close * 100) as avg_return_20,
    std((close - pre_close) / pre_close * 100) as std_return_20,
    iif(
        (close - pre_close) / pre_close * 100 > 
            avg((close - pre_close) / pre_close * 100) + 
            1.5 * std((close - pre_close) / pre_close * 100), 
        1, 0
    ) as signal_strong
from t
where trade_date between 2024.01.01:2024.06.30
context by sym;

// 查看信号统计
select month(trade_date) as month,
       sum(signal_strong) as signal_count,
       avg(signal_strong) * 100 as signal_ratio_pct
from result
group by month;
```

> **context by 是 DolphinDB 中最重要的扩展 SQL 特性之一**。在量化因子计算中，几乎每一个因子（动量、反转、波动率、结构化信号等）都依赖 context by 实现分组内的滑窗计算。如果只能掌握一个进阶 SQL 特性，那就是 context by。
