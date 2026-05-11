## 2.1 基础 CREATE TABLE 语法

在数据库创建完成后，下一步是创建分区表。DolphinDB 的分区表需要指定分区列和各列的数据类型。

```dolphindb
CREATE TABLE [dbHandle.] tableName (
    columnName columnType,
    columnName columnType,
    ...
)
[partitioned by partitionColumn1, partitionColumn2, ...];
```

### 完整示例：创建日线行情表

```dolphindb
// 获取数据库句柄
db = database("dfs://stock_day");

// 创建分区表
CREATE TABLE db.kline_day (
    trade_date  DATE,
    sym         SYMBOL,
    open        DOUBLE,
    high        DOUBLE,
    low         DOUBLE,
    close       DOUBLE,
    volume      LONG,
    amount      DOUBLE,
    turnover    DOUBLE,
    pre_close   DOUBLE,
    change_pct  DOUBLE
)
PARTITIONED BY trade_date, sym;
```

> 分区列（`PARTITIONED BY`）中的字段必须在列定义中出现，且必须与数据库的分区方案匹配。

## 2.2 常用数据类型大全

DolphinDB 为金融量化场景设计了丰富的数据类型：

### 数值类型

| 类型 | 字节 | 范围/精度 | 量化中的典型用途 |
|------|------|----------|----------------|
| BOOL | 1 | true / false | 信号标志（买入/不买入） |
| CHAR | 1 | -128 ~ 127 | 交易市场编码 |
| SHORT | 2 | -32768 ~ 32767 | 盘中序号、档位 |
| INT | 4 | -2³¹ ~ 2³¹-1 | 成交量、成交笔数 |
| LONG | 8 | -2⁶³ ~ 2⁶³-1 | 成交额（分）、超大成交量 |
| FLOAT | 4 | 约7位有效数字 | 不推荐（精度不够） |
| DOUBLE | 8 | 约15位有效数字 | **价格、收益率、因子值** |

### 时间和日期类型

| 类型 | 格式示例 | 精度 | 主要用途 |
|------|---------|------|---------|
| DATE | 2024.01.15 | 天 | 日线交易日期 |
| MONTH | 2024.01M | 月 | 月度报告期 |
| TIME | 09:30:00.000 | 毫秒 | 日内时间点 |
| MINUTE | 09:30m | 分钟 | 分钟聚合 |
| SECOND | 09:30:00 | 秒 | 秒级行情 |
| DATETIME | 2024.01.15 09:30:00 | 秒 | 精确时间戳 |
| TIMESTAMP | 2024.01.15 09:30:00.000 | 毫秒 | **Tick时间戳（推荐）** |
| NANOTIME | 09:30:00.000000000 | 纳秒 | 纳秒级时间 |
| NANOTIMESTAMP | (纳秒时间戳) | 纳秒 | 超高频回测 |

### 字符串和其他类型

| 类型 | 说明 | 存储方式 | 适用场景 |
|------|------|---------|---------|
| **SYMBOL** | 枚举类型字符串 | 内部映射为整数ID | **股票代码、交易所名（推荐）** |
| STRING | 普通字符串 | 原始字符串存储 | 备注、描述文本 |
| UUID | 通用唯一标识符 | 16字节 | 交易订单ID |
| IPADDR | IP地址 | 4字节 | 客户端来源 |
| INT128 | 128位整数 | 16字节 | 数据类型标识 |
| BLOB | 二进制大对象 | 变长 | 二进制序列化数据 |

### 复合数据类型

| 类型 | 说明 | 示例 |
|------|------|------|
| ANY | 任意类型，动态类型 | 可用于柔性表设计 |

### 类型选型建议

```
价格系列（open/high/low/close/pre_close）→ DOUBLE
成交量 → LONG（A股日成交量可达数亿股）
成交额 → DOUBLE（日成交额可达数百亿元）
股票代码 → SYMBOL（性能最优，比 STRING 快 3-5 倍）
日期 → DATE
精确时间戳 → TIMESTAMP（毫秒足够覆盖 Tick 级别）
```

> **SYMBOL vs STRING**：SYMBOL 是 DolphinDB 的特色设计。它将字符串映射为整数 ID 存储，在 join、group by、where 过滤等场景中性能远超 STRING。量化交易中，股票代码唯一且重复使用，完美匹配 SYMBOL 的设计理念。

## 2.3 查看表结构

### schema 函数

```dolphindb
// 查看表的完整结构信息
schema(loadTable("dfs://stock_day", "kline_day"));

// 只看列定义（最常用）
schema(loadTable("dfs://stock_day", "kline_day")).colDefs;

// 输出示例
name        type   typeInt  comment
----------  -----  -------  -------
trade_date  DATE   6        
sym         SYMBOL 18        
open        DOUBLE 16        
high        DOUBLE 16        
low         DOUBLE 16       
close       DOUBLE 16        
volume      LONG   5         
amount      DOUBLE 16        
```

### 其他表信息查询

```dolphindb
t = loadTable("dfs://stock_day", "kline_day");

// 获取列名
t.colNames();

// 获取列类型
t.colTypes();

// 获取行数
t.size();

// 查看前5行数据
select top 5 * from t;
```

## 2.4 loadTable 的用法

`loadTable` 用于加载分布式数据库中的表，返回一个**表句柄**（table handle），后续的查询都通过该句柄进行：

```dolphindb
// 语法
loadTable(databasePath, tableName)

// 示例
daily_kline = loadTable("dfs://stock_day", "kline_day");

// 通过句柄查询
select * from daily_kline where trade_date = 2024.01.15;
```

| 函数 | 用途 | 是否持久化 | 使用场景 |
|------|------|----------|---------|
| `table()` | 创建内存表 | 否（重启消失） | 临时数据、测试 |
| `CREATE TABLE` | 创建分区表 | 是（dfs://） | 正式生产表 |
| `loadTable()` | 加载已有表（返回句柄） | 表自身持久化 | 查询和分析 |

### loadTable 与内存表

```dolphindb
// loadTable 只获取句柄，不加载数据到内存
t = loadTable("dfs://stock_day", "kline_day");

// 如果需要把数据加载到内存
t_mem = select * from t;   // 查询结果在内存中
```

> `loadTable()` 不会将全表数据加载到内存，它只是一个"表的引用"。只有在执行查询时，DolphinDB 才会根据查询条件扫描相关分区。这是大数据环境下的标准做法，避免内存溢出。

## 2.5 修改和删除表

```dolphindb
// 删除表中的所有数据（保留表结构）
delete from loadTable("dfs://stock_day", "kline_day");

// 删除整张表（不可恢复）
dropTable("dfs://stock_day", "kline_day");

// 添加列（OLAP 引擎支持）
addColumn(
    loadTable("dfs://stock_day", "kline_day"),
    `new_col_name,
    [DOUBLE]
);

// 替换列
replaceColumn(
    loadTable("dfs://stock_day", "kline_day"),
    `old_col_name,
    `new_col_name,
    [DOUBLE]
);
```

> **生产环境操作表结构需要谨慎**。添加列操作在 OLAP 引擎中支持，但 TSDB 引擎可能有限制。大规模更改表结构在生产环境中应避免在服务高峰期执行。
