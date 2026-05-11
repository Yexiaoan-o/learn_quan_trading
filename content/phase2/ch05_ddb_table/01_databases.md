## 1.1 分布式数据库概述

在 DolphinDB 中，所有持久化的分布式数据都存储在 `dfs://` 前缀路径下（DFS = Distributed File System，分布式文件系统）。创建数据库前需要理解几个核心概念：

```
┌────────────────────────────────────────────────┐
│          DolphinDB 数据库层级关系                  │
│                                                │
│   dfs:// (分布式文件系统根路径)                    │
│   ├── dfs://stock_db       ← 数据库             │
│   │   ├── kline_day        ← 分区表             │
│   │   │   ├── Partition 1  ← 分区（物理分块）     │
│   │   │   ├── Partition 2                     │
│   │   │   └── Partition N                     │
│   │   └── kline_minute     ← 另一张分区表         │
│   └── dfs://factor_db      ← 另一个数据库         │
└────────────────────────────────────────────────┘
```

**库（Database）**是存放表的容器，**表（Table）**根据分区规则被切分为多个**分区（Partition）**，每个分区对应物理磁盘上的一个存储单元。分区的核心价值在于：当执行查询时，系统只需扫描"相关分区"而非全表，实现海量数据的秒级检索。

## 1.2 分区类型详解

DolphinDB 支持多种分区方式，不同分区适用于不同场景：

### VALUE 分区（值分区）

按单个列的离散值进行分区，适合低基数列（如年份、月份）：

```dolphindb
// 按交易日期分区，每个分区装3个月的数据
CREATE DATABASE "dfs://stock_value"
PARTITIONED BY VALUE(2019.01.01..2024.01.01, 3)   // 每3个月一个分区
ENGINE='OLAP';
```

### RANGE 分区（范围分区）

按值的范围区间进行分区，适合连续数值（如价格区间）：

```dolphindb
// 按价格区间分区
CREATE DATABASE "dfs://stock_range"
PARTITIONED BY RANGE([0.00, 10.00, 20.00, 50.00, 100.00, 999.99])
ENGINE='OLAP';
```

### HASH 分区（哈希分区）

按哈希值均匀分布数据，适合字符串高基数列（如股票代码），保证各分区数据量均匀：

```dolphindb
// 按股票代码哈希到4个分区
CREATE DATABASE "dfs://stock_hash"
PARTITIONED BY HASH([SYMBOL, 4])
ENGINE='OLAP';
```

### LIST 分区（列表分区）

按一个预定义的列表进行分区，适合按分类字段分区（如行业）：

```dolphindb
// 按行业列表分区
CREATE DATABASE "dfs://stock_list"
PARTITIONED BY LIST([`银行`保险`券商, `电子`计算机`通信, `医药`食品])
ENGINE='OLAP';
```

### COMPO 分区（复合分区）

**最常用的分区方式**，将两个或以上的分区策略组合使用：

```dolphindb
// 时间 + 股票代码 复合分区（股票量化最常用模式）
CREATE DATABASE "dfs://stock_market"
PARTITIONED BY VALUE(2019.01M..2024.01M), HASH([SYMBOL, 20])
ENGINE='OLAP';
```

### 分区策略对比

| 分区类型 | 适用列 | 适用场景 | 注意事项 |
|---------|--------|---------|---------|
| VALUE | 低基数离散值 | 日期（年/月/季）、枚举类型 | 取值范围需预先确定 |
| RANGE | 连续数值 | 价格区间、市值范围 | 区间划分需均衡数据量 |
| HASH | 高基数字符串/整数 | 股票代码、用户ID | 等量分配，但查询效率稍低 |
| LIST | 分类标签 | 行业、板块、交易所 | 手动分组，灵活但维护成本高 |
| COMPO | 多列组合 | 日期+代码、行业+日期 | **量化主流方案** |

## 1.3 存储引擎选择：OLAP vs TSDB

创建数据库时必须指定引擎类型，两种引擎的核心区别：

| 维度 | OLAP | TSDB |
|------|------|------|
| 数据排序 | 无强制排序 | 按sortKey排序存储 |
| 索引支持 | 基础分区过滤 | sortKey + 分区双重过滤 |
| 压缩比 | 中等（列式压缩） | 高（排序+列式压缩） |
| 查询性能 | 适合大范围扫描 | 适合时间区间精准查询 |
| 写入性能 | 较高 | 排序开销略高 |
| 去重 | 不支持 | 支持 sortKey 去重 |
| 适用场景 | 日频数据、因子库 | Tick 行情、K线数据 |

```dolphindb
// OLAP 引擎建库
CREATE DATABASE "dfs://daily_olap"
PARTITIONED BY VALUE(2019.01.01..2024.01.01), HASH([SYMBOL, 10])
ENGINE='OLAP';

// TSDB 引擎建库（需指定 sortKey）
CREATE DATABASE "dfs://tick_tsdb"
PARTITIONED BY VALUE(2024.01M..2024.12M), HASH([SYMBOL, 20])
ENGINE='TSDB';
```

> **选型原则**：Tick 级别/分钟级别的超高频数据选 TSDB，日频及以上的低频数据选 OLAP。如果数据量小于千万行级别，两种引擎的性能差异可忽略不计。

## 1.4 数据库路径规范

DolphinDB 使用三种路径前缀：

| 路径前缀 | 含义 | 示例 |
|---------|------|------|
| `dfs://` | 分布式文件系统（数据持久化） | `dfs://stock_market` |
| (无前缀) | 内存数据库（重启后消失） | 直接 `table()` 创建 |
| `TMP://` | 临时内存分区表 | `TMP://temp_table` |

> **生产环境必须使用 `dfs://` 前缀**，否则重启 DolphinDB 后数据将丢失。`dfs://` 下的数据会持久化到磁盘。

## 1.5 实用建库示例

### 完整的日线行情数据库

```dolphindb
// Step 1: 清理可能已存在的同名库
if(existsDatabase("dfs://stock_day"))
    dropDatabase("dfs://stock_day");

// Step 2: 创建数据库
CREATE DATABASE "dfs://stock_day"
PARTITIONED BY VALUE(2019.01M..2024.12M), HASH([SYMBOL, 10])
ENGINE='OLAP';

// Step 3: 查看库信息
database("dfs://stock_day");

// Step 4: 查看分区方案
database("dfs://stock_day").partitionSchema;
// 输出: ["VALUE", "HASH"]
//        VALUE: 2019.01M..2024.12M
//        HASH: SYMBOL,10 个分区
```

### 管理命令

```dolphindb
// 列出所有 dfs 数据库
listDatabases();

// 检查数据库是否存在
existsDatabase("dfs://stock_day");

// 查看数据库引擎类型
database("dfs://stock_day").engine;

// 删除数据库（慎用！数据不可恢复）
dropDatabase("dfs://temp_db");
```

> **注意**：`dropDatabase()` 会**物理删除**磁盘上的所有数据，操作不可逆。生产环境中务必确认无误后再执行。
