## 流数据处理基础

流数据处理（Stream Processing）是DolphinDB区别于传统数据库的核心能力之一。在量化交易中，行情数据是持续不断到达的，流处理引擎可以在数据到达的第一时间完成计算，无需等待数据"落库"。

---

### 一、流处理 vs 批处理

| 维度 | 批处理（Batch） | 流处理（Stream） |
|------|----------------|-----------------|
| 数据形态 | 静态的历史数据（"水库"） | 动态的实时数据（"河流"） |
| 处理方式 | 全量扫描后计算 | 逐条到达、增量计算 |
| 延迟 | 分钟到小时级 | 毫秒级到亚毫秒级 |
| 典型场景 | 盘后因子计算、策略回测 | 实时行情处理、在线信号生成 |
| 核心组件 | SQL查询引擎 | 流数据引擎（Stream Engine） |

---

### 二、发布-订阅模型（Pub-Sub）

DolphinDB的流处理基于经典的**发布-订阅（Publish-Subscribe）模型**：

```
发布者(Publisher)               流数据表                  订阅者(Subscriber)
┌──────────┐     写入      ┌──────────────┐    监听      ┌──────────────┐
│ 行情数据源 │  ─────────→  │  streamTable  │  ─────────→  │  流计算引擎   │
└──────────┘               └──────────────┘              └──────────────┘
                                                          │
                                                          ↓
                                                    ┌──────────────┐
                                                    │  结果输出表   │
                                                    └──────────────┘
```

三个核心概念：
- **发布者**：将数据写入流表的进程或API
- **流表**：内存中的数据缓冲池，支持高并发写入
- **订阅者**：监听流表的数据消费者，收到新数据后执行处理函数

---

### 三、流表的基本操作

#### 3.1 创建流表

```sql
// 创建流数据表（streamTable）
// 语法：streamTable(capacity:0, schema)
tickStream = streamTable(1000000:0,
    `timestamp`symbol`price`volume`bid`ask,
    [TIMESTAMP, SYMBOL, DOUBLE, LONG, DOUBLE, DOUBLE]
)

// 对比：流表 vs 普通表
// 普通内存表 — 静态，完整扫描
normalTable = table(1000000:0,
    `timestamp`symbol`price,
    [TIMESTAMP, SYMBOL, DOUBLE]
)

// 流表 — 动态，只响应增量数据
streamTable1 = streamTable(1000000:0,
    `timestamp`symbol`price,
    [TIMESTAMP, SYMBOL, DOUBLE]
)

// 共享流表（多session可访问）
share streamTable(1000000:0,
    `timestamp`symbol`price`volume,
    [TIMESTAMP, SYMBOL, DOUBLE, LONG]
) as sharedTickStream
```

#### 3.2 订阅流表

```sql
// 订阅流表
// subscribeTable(tableName, actionName, handler, msgAsTable, batchSize, throttle)
subscribeTable(
    tableName="sharedTickStream",        // 订阅的表名
    actionName="price_alert",            // 订阅任务名（唯一）
    handler=priceMonitor,                // 数据处理函数
    msgAsTable=true,                     // 以表形式传递消息
    batchSize=100,                       // 批量处理100条
    throttle=0.1                         // 最大延迟0.1秒
)

// handler 函数示例
def priceMonitor(msg){
    // msg 是流表中新到达的数据（表或tuple）
    alerts = select
        timestamp,
        symbol,
        price
    from msg
    where price > 50.0              // 过滤条件：价格超过50

    if(size(alerts) > 0){
        // 将告警数据写入另一个输出表
        outputTable.append!(alerts)
    }
}
```

---

### 四、完整的流处理示例

```sql
// ===== 步骤1：创建输入流表和输出表 =====
share streamTable(1000000:0,
    `timestamp`symbol`price`volume`bid`ask`bidSize`askSize,
    [TIMESTAMP, SYMBOL, DOUBLE, LONG, DOUBLE, DOUBLE, LONG, LONG]
) as inputStream

// 输出表：存储计算结果
outputTable = table(1000000:0,
    `timestamp`symbol`vwap`total_volume`spread_bps,
    [TIMESTAMP, SYMBOL, DOUBLE, LONG, DOUBLE]
)

// ===== 步骤2：定义handler处理函数 =====
def processTicks(msg){
    // 计算VWAP和买卖价差
    result = select
        last(timestamp) as timestamp,
        symbol,
        sum(price * volume) / sum(volume) as vwap,
        sum(volume) as total_volume,
        avg((ask - bid) / ((ask + bid) / 2)) * 10000 as spread_bps
    from msg
    group by symbol

    // 追加到输出表
    outputTable.append!(result)
}

// ===== 步骤3：设置订阅 =====
subscribeTable(
    tableName="inputStream",
    actionName="vwap_calc",
    handler=processTicks,
    msgAsTable=true,
    batchSize=500,
    throttle=1.0
)

// ===== 步骤4：模拟数据流入 =====
// 实际环境中，数据由行情网关（API）持续写入
for(i in 1..100){
    inputStream.append!(table(
        take(now(), 10) as timestamp,
        take(`000001`600036, 10) as symbol,
        rand(10.0, 10) + 30 as price,
        rand(10000, 10) as volume,
        rand(10.0, 10) + 29.5 as bid,
        rand(10.0, 10) + 30.5 as ask,
        rand(100000, 10) as bidSize,
        rand(100000, 10) as askSize
    ))
    sleep(100)   // 模拟数据到达间隔
}

// ===== 步骤5：查看结果 =====
select * from outputTable order by timestamp desc limit 20
```

---

### 五、订阅管理

```sql
// 查看所有订阅
getSubscribers()

// 获取某个流表的订阅信息
getSubscribers("inputStream")

// 取消订阅
unsubscribeTable(tableName="inputStream", actionName="vwap_calc")

// 取消表的所有订阅
unsubscribeTable(tableName="inputStream")
```

---

### 六、流表特性总结

| 特性 | 说明 | 优势 |
|------|------|------|
| **内存驻留** | 数据保存在内存中，不写盘 | 写入速度极快（百万条/秒级） |
| **发布-订阅** | 多消费者模式 | 一份数据可被多个引擎同时处理 |
| **批量投递** | batchSize控制每批处理条数 | 平衡延迟和吞吐 |
| **节流控制** | throttle控制最大等待时间 | 避免数据稀疏时长时间不触发 |
| **持久化可选** | enableTablePersistence可持久化到磁盘 | 防止宕丢数据 |

```sql
// 开启流表持久化（防宕机丢数据）
enableTablePersistence(
    table=inputStream,
    cacheSize=1000000,          // 内存缓存大小
    retentionMinutes=1440,      // 保留时间（分钟）
    syncMode=1                  // 同步模式（1=同步写盘）
)
```

> **核心概念**：流处理的本质是"有状态的增量计算"。与批处理不同，流处理引擎需要维护一个内部状态（如累计值、滑动窗口），每来一条新数据就增量更新，而非重新全量计算。这就是为什么DolphinDB的流引擎可以实现亚毫秒级延迟。
