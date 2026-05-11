## 1.1 DolphinDB 是什么？

DolphinDB 是由浙江智臾科技有限公司开发的新一代高性能分布式时序数据库与计算平台。它专为金融、物联网等领域的海量时序数据处理而设计，将数据库、分布式计算和编程语言深度整合到一个系统中，一个平台解决金融量化交易的存储、分析、实时计算三大核心需求。

```
┌─────────────────────────────────────────────────────────────┐
│                    DolphinDB 统一平台                         │
│                                                             │
│  ┌───────────┐   ┌───────────────┐   ┌───────────────────┐  │
│  │ 分布式数据库 │   │  分布式计算引擎  │   │  多范式编程语言     │  │
│  │            │   │               │   │                   │  │
│  │ • 时序存储  │   │ • 批量计算      │   │ • 向量化编程        │  │
│  │ • 列式存储  │   │ • 流式计算      │   │ • SQL 查询         │  │
│  │ • 分区管理  │   │ • 事件驱动      │   │ • 函数式编程       │  │
│  │ • 多引擎   │   │ • Map-Reduce  │   │ • 命令式编程       │  │
│  └───────────┘   └───────────────┘   └───────────────────┘  │
│                                                             │
│  ┌───────────────────────────────────────────────────────┐  │
│  │              核心应用场景                                │  │
│  │  • 量化交易回测  • 实时行情处理  • 因子计算              │  │
│  │  • 风险管理      • 交易复盘      • 市场微观结构分析       │  │
│  └───────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

### 为什么量化交易需要 DolphinDB？

传统的量化交易技术栈通常涉及多种工具的拼接：Python 做策略、MySQL 存基础数据、HDF5 存行情数据、Redis 做缓存——这种"胶水架构"存在数据搬迁开销大、实时性差、维护成本高等问题。DolphinDB 将这些功能整合到单一系统中：

| 传统方案痛点 | DolphinDB 解决方案 |
|------------|------------------|
| 数据在多个系统间拷贝，延迟高 | 库内计算，数据不动，代码动 |
| Python 逐行循环速度慢 | 向量化执行，性能提升数百倍 |
| 缺乏原生流处理能力 | 内置流数据框架，实时响应 |
| 海量历史数据查询缓慢 | 分区+列存+索引，万亿级数据秒级查询 |
| 策略代码和数据分散管理 | 策略、数据、调度统一管理 |

## 1.2 分布式架构概述

DolphinDB 采用对等架构（Peer-to-Peer），集群中每个节点角色对等，无单点故障。

```
  ┌─────────────────────────────────────────────┐
  │              DolphinDB 集群架构                │
  │                                              │
  │   ┌─────────┐     ┌─────────┐               │
  │   │ Controller│◄───┤ Controller│ (高可用)      │
  │   │ 控制节点   │     │  (备)    │              │
  │   └────┬────┘     └─────────┘               │
  │        │                                     │
  │   ┌────┴────┬────────┬────────┐              │
  │   ▼         ▼        ▼        ▼              │
  │ ┌─────┐ ┌─────┐ ┌─────┐ ┌─────┐            │
  │ │Data │ │Data │ │Data │ │Agent│            │
  │ │Node │ │Node │ │Node │ │Node │            │
  │ └─────┘ └─────┘ └─────┘ └─────┘            │
  │  数据节点  数据节点  数据节点  计算节点         │
  └─────────────────────────────────────────────┘
```

| 节点类型 | 功能 | 数量 |
|---------|------|------|
| 控制节点（Controller） | 管理集群元数据、协调节点 | 1主+N备 |
| 数据节点（Data Node） | 存储数据、执行查询 | 可水平扩展 |
| 代理节点（Agent） | 辅助任务调度、定时任务 | 按需部署 |
| 计算节点（Compute Node） | 仅计算不存储，纯计算资源 | 按需部署 |

关键特性：
- **分区并行**：数据按分区键水平切分，多数据节点并行扫描
- **就近计算**：计算尽可能在数据所在的节点执行，减少网络传输
- **流表订阅**：流数据可被多订阅者实时消费，支持发布-订阅模式

## 1.3 多模型存储引擎

DolphinDB 针对不同的数据特征和业务场景，提供了多种存储引擎：

| 存储引擎 | 全称 | 适用场景 | 核心优势 |
|---------|------|---------|---------|
| **TSDB** | Time Series Database | 高频行情数据、IoT传感器 | 高压缩比、时序排序、快速区间查询 |
| **OLAP** | Online Analytical Processing | 常规结构化分析 | 标准列式存储，通用性强 |
| **PKEY** | Primary Key DB | 需要主键唯一约束的数据 | 支持 UPSERT、按主键快速定位 |
| **IMOLTP** | In-Memory OLTP | 需要事务支持的实时数据 | 行级事务、ACID 支持 |
| **VECTORDB** | Vector Database | 向量相似性搜索 | AI/ML 特征存储与检索 |

### 引擎选型指南

```dolphindb
// 各引擎典型建库语句示例

// TSDB：高频行情数据
CREATE DATABASE "dfs://market_tsdb"
ENGINE = 'TSDB'
PARTITIONED BY VALUE(2020.01.01..2025.01.01), HASH([SYMBOL, 20]);

// OLAP：日频因子数据
CREATE DATABASE "dfs://factor_olap"
ENGINE = 'OLAP'
PARTITIONED BY VALUE(2020.01.01..2025.01.01), VALUE(["行业1", "行业2", "行业3"]);

// PKEY：基本面数据（需要按股票代码唯一）
CREATE DATABASE "dfs://fundamental_pkey"
ENGINE = 'PKEY'
PARTITIONED BY HASH([SYMBOL, 4]);
```

> **选择建议**：量化交易场景中，Tick 级行情数据优先用 TSDB（高压缩+快查询），分钟级/日级数据可用 OLAP，基本面数据需要 UPSERT 操作时选 PKEY。不要求一库一引擎，可根据数据特性混用。

## 1.4 批量计算与流处理

DolphinDB 同时支持批量计算和流式计算，这是其区别于传统关系型数据库的重要特征。

### 批量计算（Batch Computing）

适合处理历史数据的离线分析、回测、因子计算等：

```dolphindb
// 批量计算：计算所有股票过去20日收益率均值
select sym, avg(return) as avg_ret
from loadTable("dfs://market", "kline_day")
where date between 2024.01.01:2024.12.31
group by sym, month(date) context by sym;
```

### 流处理（Stream Processing）

适合实时行情处理、实时风险监控、实时信号生成等：

```dolphindb
// 流处理：订阅实时行情，计算每分钟VWAP
share streamTable(1000:0, `sym`time`price`volume, 
    [SYMBOL, TIMESTAMP, DOUBLE, LONG]) as tickStream;

// 定义流计算规则
metrics = <[time, avg(price), sum(volume)]>;
result = table(1000:0, `time`avgPrice`totalVol, 
    [TIMESTAMP, DOUBLE, LONG]);

// 订阅流表
subscribeTable(tableName="tickStream", actionName="vwap_calc", 
    offset=-1, handler=calcVWAP{metrics, result}, msgAsTable=true);
```

### 批流一体

DolphinDB 最大的特点是批流一体——同一套 SQL 语法和计算函数，既可用于历史数据的离线分析，也可用于实时数据的在线流处理。策略从"回测"切换到"实盘"时，无需重写计算逻辑，真正实现了"一份代码，批流两用"。

## 1.5 多范式编程语言

DolphinDB 内置了一门完整的编程语言，支持多种编程范式：

| 范式 | 特点 | 示例 |
|------|------|------|
| 向量化编程 | 操作整个向量而非元素循环 | `price * volume` |
| SQL 查询 | 兼容标准 SQL 语法 + 扩展 | `select ... group by ...` |
| 函数式编程 | 高阶函数、lambda 表达式 | `each(f, x)` |
| 命令式编程 | 变量、循环、条件分支 | `for/if-else/while` |
| 元编程 | 运行时动态生成代码 | `funcByName("sum")` |

```dolphindb
// 多范式混合示例：计算平均成交额并过滤
def calcAvgTurnover(data, minTurnover) {
    // 向量化计算成交额（价格 × 成交量）
    turnover = data.close * data.volume;
    
    // SQL 过滤和聚合
    result = select sym, avg(turnover) as avg_turnover
             from data
             where sym in ["000001", "000002", "000003"]
             group by sym
             having avg(turnover) > minTurnover;
    
    return result;
}
```

> **学习重点**：在量化交易场景中，**向量化编程 + SQL** 是最常用、最高效的组合。DolphinDB 脚本与 Python 语法有所不同，需要花时间适应，但一旦掌握了向量化思维，你会发现它的简洁和高效远超预期。
