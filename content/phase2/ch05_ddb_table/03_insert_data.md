## 3.1 INSERT INTO 语句

`INSERT INTO` 是最标准的数据写入方式，适用于将少量或中等规模的数据写入分区表。

### 基本语法

```dolphindb
INSERT INTO tableName VALUES (val1, val2, ...), (val1, val2, ...), ...;
```

### 示例：插入日线数据

```dolphindb
// 加载表句柄
daily_kline = loadTable("dfs://stock_day", "kline_day");

// 单行插入
INSERT INTO daily_kline VALUES
(2024.01.15, `000001, 15.20, 15.85, 15.10, 15.67, 12500000, 195000000.0, 0.03, 15.30, 2.42);

// 多行批量插入
INSERT INTO daily_kline VALUES
(2024.01.15, `000001, 15.20, 15.85, 15.10, 15.67, 12500000, 195000000.0, 0.03, 15.30, 2.42),
(2024.01.15, `000002, 22.50, 23.10, 22.20, 22.80, 5600000, 127000000.0, 0.02, 22.30, 2.24),
(2024.01.15, `000003, 8.35, 8.60, 8.20, 8.55, 22000000, 188000000.0, 0.05, 8.40, 1.79);
```

### 插入内存表

```dolphindb
// 向内存表插入数据
tmp_t = table(
    `sym`price`volume,
    [SYMBOL, DOUBLE, LONG]
);

INSERT INTO tmp_t VALUES
(`000001, 15.67, 12500000),
(`000002, 22.80, 5600000);

select * from tmp_t;
```

## 3.2 append! 函数

`append!` 是将一个表的数据追加到另一个表末尾的高效方法。它比逐行 INSERT INTO 速度快得多，适用于批量数据写入。

```dolphindb
// 语法
destTable.append!(sourceTable);
```

### 用法示例

```dolphindb
// 准备目标表（空表，结构与源数据一致）
target = table(10:0, 
    `trade_date`sym`open`high`low`close`volume,
    [DATE, SYMBOL, DOUBLE, DOUBLE, DOUBLE, DOUBLE, LONG]
);

// 准备源数据
source1 = table(
    2024.01.15 2024.01.16 as trade_date,
    `000001`000001 as sym,
    15.20 15.67 as open,
    15.85 15.95 as high,
    15.10 15.50 as low,
    15.67 15.72 as close,
    12500000 9800000 as volume
);

source2 = table(
    2024.01.15 2024.01.16 as trade_date,
    `000002`000002 as sym,
    22.50 22.80 as open,
    23.10 23.20 as high,
    22.20 22.60 as low,
    22.80 22.90 as close,
    5600000 4300000 as volume
);

// 追加数据
target.append!(source1);
target.append!(source2);

// 查看结果
select * from target order by sym, trade_date;
```

### append! 写入分区表

```dolphindb
// append! 也可以直接向分区表写入
daily_kline = loadTable("dfs://stock_day", "kline_day");
daily_kline.append!(source1);
```

### INSERT INTO vs append! 对比

| 特性 | INSERT INTO | append! |
|------|-----------|---------|
| 写入方式 | 逐行/逐组 VALUES | 整表追加 |
| 速度 | 较慢（逐行处理） | 快（批量操作） |
| 适用数据量 | 少量数据（< 1000行） | 大量数据 |
| 数据格式 | 原始值（val1, val2） | 表对象 |
| 适用场景 | 手工测试、少量插入 | 批量导入、数据同步 |

> **性能建议**：批量数据写入优先使用 `append!`，其性能通常比逐行 INSERT INTO 高出 10-100 倍。

## 3.3 tableInsert 流写入函数

`tableInsert` 是专门为流数据写入设计的函数，返回已写入的行数。它最常见的应用场景是接收实时行情数据：

```dolphindb
// 创建共享流表
share streamTable(100000:0, 
    `sym`time`price`volume`bid`ask,
    [SYMBOL, TIMESTAMP, DOUBLE, LONG, DOUBLE, DOUBLE]
) as tickStream;

// 使用 tableInsert 写入流数据
tableInsert(tickStream, `000001, 2024.01.15 09:30:01.234, 15.67, 1000, 15.66, 15.68);
tableInsert(tickStream, `000002, 2024.01.15 09:30:02.456, 22.80, 500, 22.78, 22.82);

// 查看流表中的数据
select * from tickStream;

// tableInsert 返回已插入的行数
inserted_rows = tableInsert(tickStream, `000003, 2024.01.15 09:30:03.789, 8.55, 2000, 8.54, 8.56);
print("已插入行数: " + string(inserted_rows));
```

### tableInsert vs append!

| 特性 | tableInsert | append! |
|------|-----------|---------|
| 返回值 | 插入行数 | 目标表 |
| 支持批量 | 支持（传入n个参数向量） | 支持（传入表） |
| 流处理 | **专为流表设计** | 不适用流表 |
| 多行插入 | `tableInsert(t, [col1], [col2])` | `t.append!(sourceTable)` |

```dolphindb
// tableInsert 批量写入（通过列向量）
sym_list = `000001`000001`000002;
price_list = 15.67 15.72 22.80;
vol_list = 1000 800 500;

tableInsert(tickStream, 
    sym_list,
    [2024.01.15 09:30:01.234, 2024.01.15 09:31:15.567, 2024.01.15 09:32:45.890],
    price_list,
    vol_list,
    price_list - 0.01,
    price_list + 0.01
);
```

## 3.4 生成测试数据

在开发和测试阶段，通常需要大量的模拟数据。DolphinDB 提供了便捷的数据生成函数：

### rand 函数

```dolphindb
// rand(X, count): 从X中随机抽取count个值
rand(100.0, 10);                          // 10个 [0,100] 之间的随机小数
rand(100, 10);                            // 10个 [0,99] 之间的随机整数
rand(`A`B`C, 10);                        // 10个随机符号（从A、B、C中抽取）

// 生成股票代码
syms = rand(`000001`000002`000003`000004`000005, 1000);

// 生成随机价格
prices = rand(50.0, 1000) + 10.0;        // [10, 60] 范围内的随机价格
```

### take 函数

```dolphindb
// take(X, n): 循环取X的元素，生成长度为n的序列
take(`A`B`C, 7);    // 输出: [`A, `B, `C, `A, `B, `C, `A]
take(1..5, 10);      // 输出: [1,2,3,4,5,1,2,3,4,5]

// 生成固定的股票代码序列
syms = take(`000001`000002`000003, 300);
```

### 综合示例：生成1000股票、250天的模拟日线数据

```dolphindb
// 参数设定
n_stocks = 1000;
n_days = 250;

// 生成股票代码
syms = take(rand(`A`B`C`D`E, n_stocks), n_stocks * n_days);

// 生成日期
dates = take(2022.01.01..2022.12.31, n_stocks * n_days);

// 生成模拟价格：起始价格随机，后续加入小幅波动
opens = 10.0 + rand(40.0, n_stocks * n_days);
highs = opens * (1.0 + rand(0.05, n_stocks * n_days));
lows = opens * (1.0 - rand(0.05, n_stocks * n_days));
closes = opens * (1.0 + rand(0.1, n_stocks * n_days) - 0.05);
volumes = rand(10000000, n_stocks * n_days) + 1000000;

// 组装为表
sim_data = table(dates as trade_date, syms as sym, 
                 opens, highs, lows, closes, volumes);

// 查看生成的数据
select top 5 * from sim_data;
print("共生成 " + string(sim_data.size()) + " 行模拟数据");
```

> 使用 `rand` 生成的模拟数据**不保留真实金融数据的统计特性**（如收益率分布、波动率聚集等），仅用于功能测试和代码调试。正式回测必须使用真实市场数据。
