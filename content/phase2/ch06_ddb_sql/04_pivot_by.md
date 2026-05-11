## 4.1 pivot by 是什么？

`pivot by` 是 DolphinDB 的交叉表（Cross-Tabulation）功能，它将数据从"长格式"（long format）重塑为"宽格式"（wide format），常用于数据透视分析。在金融量化场景中，pivot by 是把"三维数据"降维展示的核心工具。

```
输入（长格式）：                       输出（宽格式/透视表）：
┌──────────┬─────┬───────┬──────┐    ┌──────────┬───────┬───────┬───────┐
│TradeDate │ Sym │Close  │Volume│    │TradeDate │ AAPL  │ MSFT  │ GOOGL │
├──────────┼─────┼───────┼──────┤    ├──────────┼───────┼───────┼───────┤
│2024-01-02│AAPL │185.50 │58M   │    │2024-01-02│185.50 │376.04 │140.10 │
│2024-01-02│MSFT │376.04 │22M   │ →  │2024-01-03│184.25 │374.60 │141.20 │
│2024-01-02│GOOGL│140.10 │30M   │    │2024-01-04│186.30 │376.80 │142.50 │
│2024-01-03│AAPL │184.25 │55M   │    └──────────┴───────┴───────┴───────┘
│2024-01-03│MSFT │374.60 │20M   │
│2024-01-03│GOOGL│141.20 │28M   │
└──────────┴─────┴───────┴──────┘
```

### 语法

```dolphindb
SELECT rowColumn, valueColumn
FROM table
PIVOT BY pivotColumn
[WHERE condition];
```

三个核心角色：

| 角色 | 参数 | 说明 |
|------|------|------|
| **行维度** | rowColumn | 透视表的行标签（如日期） |
| **列维度** | pivotColumn | 透视表的列标签（如股票代码） |
| **值** | valueColumn | 透视表单元格中填充的值（如收盘价） |

## 4.2 基础示例

### 示例 1：收盘价透视表

```dolphindb
t = loadTable("dfs://stock_day", "kline_day");

// 将收盘价数据转为"日期 × 股票"的矩阵
select trade_date, close from t
where trade_date between 2024.01.01:2024.01.10
pivot by sym;
```

输出结果：

```
trade_date   000001  000002  000003
------------ ------- ------- -------
2024.01.02   15.67   22.80   8.55
2024.01.03   15.72   22.90   8.60
2024.01.04   15.30   21.50   8.45
...
```

### 示例 2：成交额透视表

```dolphindb
// 计算成交额
select trade_date, close * volume as amount from t
where trade_date between 2024.01.01:2024.01.10
pivot by sym;
```

## 4.3 多值列透视

当需要同时透视多个值列时，可以用逗号分隔：

```dolphindb
// 同时透视收盘价和成交量
select trade_date, close, volume from t
where trade_date between 2024.01.01:2024.01.10
pivot by sym;

// 结果会自动生成：000001_close, 000001_volume, 000002_close, 000002_volume, ...
```

### 多值透视的结果列命名

```
trade_date    000001_close  000001_volume  000002_close  000002_volume
------------  ------------  -------------  ------------  -------------
2024.01.02    15.67         12500000       22.80         5600000
```

列名自动格式为：`{pivotColumnValue}_{valueColumnName}`。

## 4.4 pivot by 的 HAVING 条件

HAVING 可以过滤透视结果中的列：

```dolphindb
// 只显示 2024 年 1 月份日均成交量 > 1000 万的股票
select trade_date, close from t
where trade_date between 2024.01.01:2024.01.31
pivot by sym
having avg(close) > 10.0;
```

## 4.5 量化实战应用

### 实战 1：构建收益率矩阵

收益率矩阵是量化分析中最常见的数据结构之一，是 CAPM、多因子模型、协方差矩阵计算的基础：

```dolphindb
t = loadTable("dfs://stock_day", "kline_day");

// 计算每只股票的日收益率，并转为矩阵
returns = select 
    trade_date, 
    (close - pre_close) / pre_close as daily_return
from t
where trade_date between 2024.01.01:2024.06.30
pivot by sym;

// returns 现在是一个 "日期 × 股票" 的收益率矩阵
// 可以直接用于：
// 1. 计算协方差矩阵
// 2. 计算各股票间的相关系数
// 3. 做 PCA 分解
```

### 实战 2：构建限价指令簿快照

```dolphindb
// 假设有一张 tick 表，每个时间点有多档报价
snapshot = select time, 
          bid1 / (bid1 + ask1) as imbalance
from tick_table
pivot by sym;
```

### 实战 3：监视多股票技术指标

```dolphindb
// 计算各股票是否触发金叉信号（MA5 上穿 MA20），转为矩阵格式
signals = select 
    trade_date,
    iif(mavg(close, 5) > mavg(close, 20) 
        and mavg(close, 5)[1] <= mavg(close, 20)[1], 1, 0) as golden_cross
from t
context by sym
pivot by sym;
```

## 4.6 pivot by 与其他子句的组合

pivot by 可以灵活地与 WHERE、GROUP BY、CONTEXT BY 等子句组合：

```dolphindb
// 组合示例：先按行业分组，再透视
// 假设表中有 industry 列
select industry, sym, avg(close) as avg_close
from t
where trade_date between 2024.01.01:2024.01.31
group by industry, sym
pivot by sym;

// CONTEXT BY + PIVOT BY 组合
select trade_date, 
       mavg(close, 5) as ma5
from t
context by sym
pivot by sym;
```

### pivot by 的限制与注意事项

| 限制 | 说明 | 应对方法 |
|------|------|---------|
| 数据粒度必须唯一 | 同一行+列组合不能有多个值 | 先用 GROUP BY 聚合 |
| 列数量限制 | pivot 后的列数 = 不同 pivotColumn 值的数量 × 值列数 | 控制 pivotColumn 的基数 |
| 内存消耗 | 宽表可能占用大量内存 | 限制参与 pivot 的数据范围 |
| 需先排序 | pivot by 需要数据按 pivotColumn 排序（自动完成） | 无需手动干预 |

```dolphindb
// 错误示例：数据不唯一
// 如果同一 trade_date 同一 sym 有多条记录，会报错
select trade_date, close from t pivot by sym;
// → 需要先确保数据粒度正确

// 正确做法：确保唯一性
select trade_date, close from t 
where trade_date = 2024.01.15
pivot by sym;
// 每日每股票一条记录 → 唯一
```

> **pivot by 的本质**：它将"键值对"型数据重塑为矩阵型数据。在量化分析中，收益率矩阵、协方差矩阵、因子敞口矩阵等的构建都依赖这种透视操作。pivot by 是连接"表存储"和"矩阵计算"两套数据范式的桥梁。
