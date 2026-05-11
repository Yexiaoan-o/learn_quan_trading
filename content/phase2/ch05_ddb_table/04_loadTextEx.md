## 4.1 loadTextEx 概述

`loadTextEx` 是 DolphinDB 中最强大的 CSV/文本数据导入函数，它能将 CSV 文件直接加载到分区表中，是量化数据工程师最常用的数据导入工具。

```
┌─────────────────────────────────────────────────────┐
│              loadTextEx 数据导入流程                    │
│                                                     │
│  CSV 文件  ──→  读取 ──→  解析  ──→  分区  ──→  写入  │
│  (本地/NFS)      Header    Schema    Partition   dfs://
│                                                     │
└─────────────────────────────────────────────────────┘
```

### 语法

```dolphindb
loadTextEx(dbHandle, tableName, partitionColumns, filename, 
           [delimiter], [schema], [skipRows], [arrayDelimiter], ...);
```

### 参数说明

| 参数 | 必需 | 说明 |
|------|------|------|
| dbHandle | ✓ | 数据库句柄（database 函数返回值） |
| tableName | ✓ | 目标表名称（字符串） |
| partitionColumns | ✓ | 分区列名（字符串向量） |
| filename | ✓ | CSV 文件路径 |
| delimiter | 可选 | 分隔符，默认为逗号 `,` |
| schema | 可选 | 自定义 Schema 表 |
| skipRows | 可选 | 跳过开头的行数（忽略标题行） |

## 4.2 基础导入示例

### 准备 CSV 文件

假设有一个股票日线数据的 CSV 文件 `stock_2024.csv`：

```csv
trade_date,sym,open,high,low,close,volume
2024-01-02,000001,15.20,15.85,15.10,15.67,12500000
2024-01-02,000002,22.50,23.10,22.20,22.80,5600000
2024-01-02,000003,8.35,8.60,8.20,8.55,22000000
2024-01-03,000001,15.67,15.95,15.50,15.72,9800000
2024-01-03,000002,22.80,23.20,22.60,22.90,4300000
```

### 导入代码

```dolphindb
// Step 1: 获取数据库句柄
db = database("dfs://stock_day");

// Step 2: 使用 loadTextEx 导入 CSV 文件
loadTextEx(db, `kline_day, `trade_date`sym, 
           "/data/stock_2024.csv");
```

执行上述代码后：
1. DolphinDB 自动读取 CSV 文件，根据 Header 行推断列名和数据类型
2. 按 `trade_date` 和 `sym` 两个分区列将数据路由到对应分区
3. 数据持久化写入 `dfs://stock_day` 数据库的 `kline_day` 表中

### 验证导入结果

```dolphindb
t = loadTable("dfs://stock_day", "kline_day");
select count(*) from t;        // 查看总行数
select top 10 * from t;       // 查看前10行
```

## 4.3 手动指定 Schema

自动推断可能出错（如日期格式识别错误、整数误判为长整数等），推荐手动指定 Schema 以确保数据类型精确匹配：

```dolphindb
// 定义 Schema 表（只有列定义，无数据行）
schema_table = table(
    array(SYMBOL, 0) as name,
    array(SYMBOL, 0) as type
);

// 逐列定义类型
schema_table.append!(table(
    `trade_date`sym`open`high`low`close`volume as name,
    `DATE`SYMBOL`DOUBLE`DOUBLE`DOUBLE`DOUBLE`LONG as type
));

// 使用自定义 schema 导入
loadTextEx(dbHandle=db, 
           tableName=`kline_day,
           partitionColumns=`trade_date`sym,
           filename="/data/stock_2024.csv",
           schema=schema_table);
```

### Schema 中可指定的类型

在 Schema 表中，列类型（type 列）必须使用 DolphinDB 识别的类型字符串（大写）：

```
INT, LONG, SHORT, CHAR, BOOL, FLOAT, DOUBLE, 
DATE, MONTH, TIME, MINUTE, SECOND, DATETIME, 
TIMESTAMP, NANOTIME, NANOTIMESTAMP, 
SYMBOL, STRING, BLOB, UUID, IPADDR
```

> **特殊类型注意**：日期时间类字段在 CSV 中必须为 DolphinDB 可识别的格式（如 `2024.01.15`），否则导入会失败或类型错误。如 CSV 格式不匹配（如 `2024-01-15`），需先用脚本对 CSV 做预处理。

## 4.4 批量导入与性能优化

### 批量导入多个文件

```dolphindb
// 导入一个目录下的所有 CSV 文件
file_dir = "/data/stock_csv/";
files = files(file_dir);   // 获取文件列表
db = database("dfs://stock_day");

// 遍历导入
for(file in files) {
    if(file.endsWith(".csv")) {
        print("正在导入: " + file);
        loadTextEx(db, `kline_day, `trade_date`sym,
                   file_dir + file);
    }
}
```

### 性能优化技巧

| 优化策略 | 说明 | 效果 |
|---------|------|------|
| 按分区列拆分 CSV | 每个 CSV 只包含一个分区的数据 | 避免数据跨节点搬运 |
| 分批导入 | 大数据集拆成多个小 CSV 分批导入 | 减少内存峰值 |
| 并行导入 | 多线程/多 session 同时导入不同分区 | 充分利用多核 |
| 关闭事务日志 | 导入时设置 `atomic='false'` | 写入速度提升 |
| 预排序 CSV | 数据按分区列预先排序 | 减少排序开销 |

```dolphindb
// 关闭原子写入以提高批量导入速度
loadTextEx(dbHandle=db,
           tableName=`kline_day,
           partitionColumns=`trade_date`sym,
           filename="/data/stock_2024.csv",
           atomic='false');   // 关闭事务，提高速度
```

### 性能对比参考

| 数据量 | 单线程导入 | 优化后导入（多线程+预分区） |
|--------|----------|--------------------------|
| 100万行 | ~8秒 | ~2秒 |
| 1000万行 | ~80秒 | ~15秒 |
| 1亿行 | ~15分钟 | ~2分钟 |

> 以上时间为参考值，实际性能取决于硬件配置（CPU、磁盘IO、内存）和数据复杂程度。

## 4.5 完整实战：导入股票日线数据

以下是一个完整的股票数据导入流水线：

```dolphindb
// ═══════════════════════════════════════════
// 完整的数据导入流水线
// ═══════════════════════════════════════════

// 1. 创建数据库（如果不存在）
if(!existsDatabase("dfs://stock_day")) {
    CREATE DATABASE "dfs://stock_day"
    PARTITIONED BY VALUE(2010.01M..2025.01M), HASH([SYMBOL, 20])
    ENGINE='OLAP';
}

// 2. 定义 Schema
schema_tbl = table(
    `trade_date`sym`open`high`low`close`volume`amount as name,
    `DATE`SYMBOL`DOUBLE`DOUBLE`DOUBLE`DOUBLE`LONG`DOUBLE as type
);

// 3. 创建表（如果未存在）
db = database("dfs://stock_day");
tables_in_db = db.tableNames();
if(!`kline_day in tables_in_db) {
    CREATE TABLE db.kline_day (
        trade_date  DATE,
        sym         SYMBOL,
        open        DOUBLE,
        high        DOUBLE,
        low         DOUBLE,
        close       DOUBLE,
        volume      LONG,
        amount      DOUBLE
    )
    PARTITIONED BY trade_date, sym;
}

// 4. 导入 CSV 文件
loadTextEx(dbHandle=db,
           tableName=`kline_day,
           partitionColumns=`trade_date`sym,
           filename="/data/stock_day_2024.csv",
           schema=schema_tbl);

// 5. 验证数据
t = loadTable("dfs://stock_day", "kline_day");

print("──── 数据导入完成 ────");
print("总行数: " + string(select count(*) from t));
print("股票数量: " + string(exec count(distinct sym) from t));
print("日期范围: " + string(exec min(trade_date) from t) + 
      " 至 " + string(exec max(trade_date) from t));
print("示例数据:");
select top 5 * from t order by trade_date, sym;

// 6. 检查每只股票的数据完整性
select sym, 
       count(*) as records,
       min(trade_date) as start_date,
       max(trade_date) as end_date
from t
group by sym
limit 10;
```

### 常见导入错误排查

| 错误现象 | 可能原因 | 解决方案 |
|---------|---------|---------|
| "表已存在" | CREATE TABLE 重复执行 | 添加 `if` 判断是否已存在 |
| "类型不匹配" | CSV 字段类型与 Schema 不符 | 检查并修正 Schema 定义 |
| "分区列不在表中" | partitionColumns 写错了列名 | 核对 CSV 列名与分区列名 |
| "超出分区范围" | 数据值不在分区定义范围内 | 扩大分区范围或添加边界值 |
| "内存不足" | 单次导入数据量过大 | 分批导入或增加 maxMemSize |

> **最佳实践**：建议先在小样本（如 1000行）CSV 上测试导入流程，确认 Schema、分区、数据类型全部正确后，再批量导入全量数据。这可以避免数小时的大数据导入因类型错误而失败重来。
