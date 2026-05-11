## 1.1 SELECT 基本语法

DolphinDB 的 SQL 查询语法与标准 SQL 高度兼容，同时扩展了许多时序分析特性。最基本的查询语句如下：

```dolphindb
SELECT [column1, column2, ...]
FROM tableName
[WHERE condition]
[ORDER BY column [ASC|DESC]]
[LIMIT n];
```

### 简单查询示例

```dolphindb
// 加载日线行情表
t = loadTable("dfs://stock_day", "kline_day");

// 查询全部列
select * from t;

// 查询指定的几列
select trade_date, sym, close, volume from t;

// 只查询前10行
select top 10 * from t;

// 使用 LIMIT 限制返回行数
select * from t limit 100;
```

### 列运算与别名

在 SELECT 中可以执行列运算并赋予别名：

```dolphindb
// 计算涨跌幅、振幅、成交额
select 
    trade_date,
    sym,
    close,
    pre_close,
    (close - pre_close) / pre_close * 100 as change_pct,     // 涨跌幅 (%)
    (high - low) / pre_close * 100 as amplitude,              // 振幅 (%)
    volume,
    volume * close as amount                                   // 成交额
from t
where trade_date >= 2024.01.01;
```

### SELECT 子句中的聚合函数

```dolphindb
// 统计查询：一次性获取多个统计量
select 
    count(*) as records,
    avg(close) as avg_close,
    max(close) as max_close,
    min(close) as min_close,
    sum(volume) as total_volume,
    std(close) as close_std
from t
where trade_date between 2024.01.01:2024.01.31;
```

## 1.2 WHERE 条件过滤

WHERE 子句支持丰富的条件组合，是量化查询中最常用的数据筛选方式。

### 比较运算符

| 运算符 | 说明 | 示例 |
|--------|------|------|
| `=` / `==` | 等于 | `sym == '000001` |
| `!=` / `<>` | 不等于 | `sym != '000001` |
| `>` | 大于 | `close > 20.0` |
| `<` | 小于 | `close < 10.0` |
| `>=` | 大于等于 | `volume >= 1000000` |
| `<=` | 小于等于 | `turnover <= 0.05` |

### 逻辑组合

```dolphindb
// AND：同时满足多个条件
select * from t 
where trade_date = 2024.01.15 
  and close > 10.0 
  and volume > 5000000;

// OR：满足任一条件
select * from t 
where sym = `000001 or sym = `000002 or sym = `000003;

// NOT：条件取反
select * from t 
where not sym in (`000001, `000002);

// 混合使用：使用括号明确优先级
select * from t
where (trade_date between 2024.01.01:2024.01.31)
  and (close > 20.0 or volume > 10000000);
```

### IN 和 BETWEEN

这两个运算符在量化查询中非常高频：

```dolphindb
// IN：属于指定集合
select * from t 
where sym in (`000001, `000002, `000003, `000004, `000005);

// 与子查询结合：选取成交量前10的股票
select * from t
where sym in (
    select sym from t 
    where trade_date = 2024.01.15 
    order by volume desc 
    limit 10
);

// BETWEEN：在某个区间内（闭区间，包含边界）
select * from t
where close between 10.0:20.0;

// 等价于
select * from t
where close >= 10.0 and close <= 20.0;

// BETWEEN 也适用于日期
select * from t
where trade_date between 2024.01.01:2024.03.31;
```

### 字符串模糊匹配

```dolphindb
// LIKE：模式匹配（% 表示任意字符序列）
select * from t where sym like "0000%";     // 以 0000 开头
select * from t where sym like "%001";      // 以 001 结尾

// 注意：SYMBOL 类型的字符串比较需要使用具体匹配
// LIKE 主要用于 STRING 类型
```

## 1.3 结果排序与分页

### ORDER BY

```dolphindb
// 按收盘价降序排列（涨得最多的在前面）
select trade_date, sym, close, 
       (close - pre_close) / pre_close * 100 as change_pct
from t
where trade_date = 2024.01.15
order by change_pct desc;

// 多列排序：先按日期升序，再按成交量降序
select trade_date, sym, volume, close
from t
order by trade_date asc, volume desc;

// 默认升序（ASC 可省略）
select * from t order by trade_date, sym;
```

### LIMIT 和 TOP

```dolphindb
// LIMIT：限制返回行数（配合 OFFSET 可做分页）
select * from t limit 20;                // 前20行
select * from t limit 20 offset 100;     // 跳过前100行，取20行

// TOP：DolphinDB 特有的简洁语法
select top 10 * from t order by volume desc;    // 取前10行

// top 可与 limit 互换，但 top 只能放在 select 后面
```

### 实用的 Top-N 查询

```dolphindb
// 每日涨幅前5的股票
select top 5 trade_date, sym, 
       (close - pre_close) / pre_close * 100 as change_pct
from t
where trade_date = 2024.01.15
order by change_pct desc;

// 成交量最大的10只股票
select top 10 sym, sum(volume) as total_vol
from t
where trade_date between 2024.01.01:2024.01.31
group by sym
order by total_vol desc;
```

## 1.4 算术表达式与条件列

DolphinDB SELECT 支持创建计算列：

```dolphindb
select
    trade_date,
    sym,
    close,
    // 计算列1：典型价格（Typical Price）
    (high + low + close) / 3 as typical_price,
    // 计算列2：价格范围（日内波动区间）
    high - low as price_range,
    // 计算列3：对数收益率（相对于前一个交易日的收益率不能用这种方式计算）
    // 计算列4：条件列（用 iif 或 case when）
    iif(close > pre_close, "上涨", "下跌") as direction
from t
where trade_date >= 2024.01.01;
```

### iif 条件函数

```dolphindb
// iif(condition, trueValue, falseValue)：向量化三元表达式
select
    sym,
    close,
    iif(close > 20.0, "高价股", iif(close > 10.0, "中价股", "低价股")) as price_level
from t
where trade_date = 2024.01.15;
```

## 1.5 DISTINCT 去重

```dolphindb
// 查询某天有哪些股票有交易记录
select distinct sym from t where trade_date = 2024.01.15;

// 查询数据库中有哪些股票
select distinct sym from t;

// 查看数据覆盖的日期范围
select min(trade_date) as start_date, 
       max(trade_date) as end_date,
       count(distinct trade_date) as trading_days,
       count(distinct sym) as stock_count
from t;
```

> **SELECT 查询性能警告**：在没有分区的普通内存表上，`select * from table` 会返回全部数据。但在分布式分区表上，`select *` 虽然语法正确，却可能触发全表扫描严重影响性能。**生产环境中务必为 SELECT 添加有效的 WHERE 条件**，让 DolphinDB 的分区裁剪机制发挥作用，只扫描相关分区。
