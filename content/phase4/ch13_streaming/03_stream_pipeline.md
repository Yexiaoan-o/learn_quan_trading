## 流处理管道（Pipeline）

单个流引擎的能力有限，复杂的量化策略通常需要多个流引擎**级联**（串联）工作，形成流处理管道。DolphinDB允许将多个引擎的输出-输入串联起来，构建端到端的实时计算链路。

---

### 一、什么是流处理管道

```
  行情数据源                                   最终输出
      │                                           ↑
      ▼                                           │
┌──────────┐    ┌──────────────┐    ┌──────────┐  │
│ 流表A     │ →  │ 引擎1        │ →  │ 引擎2     │ ─┘
│(原始tick) │    │(时间序列引擎) │    │(横截面引擎)│
└──────────┘    └──────────────┘    └──────────┘
                      │                   │
                      ▼                   ▼
                5分钟K线表          实时因子排名表
```

数据流动方向：**流表 → 引擎1 → 中间表/流表 → 引擎2 → 输出表**

---

### 二、级联管道示例：实时K线 → 因子计算 → 排名

```sql
// ===== 第1级：原始tick → 5分钟K线（时间序列引擎）=====
share streamTable(1000000:0,
    `timestamp`symbol`price`volume,
    [TIMESTAMP, SYMBOL, DOUBLE, LONG]
) as tickStream

klineOutput = table(1000000:0,
    `timestamp`symbol`open`high`low`close`volume`tick_count,
    [TIMESTAMP, SYMBOL, DOUBLE, DOUBLE, DOUBLE, DOUBLE, LONG, INT]
)

klineEngine = createTimeSeriesEngine(
    name="kline_5m",
    windowSize=300,                     // 5分钟 = 300秒
    step=300,
    metrics=[
        <first(price)>,
        <max(price)>,
        <min(price)>,
        <last(price)>,
        <sum(volume)>,
        <count(*)>
    ],
    dummyTable=tickStream,
    outputTable=klineOutput,
    timeColumn=`timestamp,
    keyColumn=`symbol,
    useSystemTime=false
)

subscribeTable(
    tableName="tickStream",
    actionName="kline_engine_sub",
    handler=klineEngine,
    msgAsTable=true,
    batchSize=100
)

// ===== 第2级：K线 → 技术因子计算（响应式状态引擎）=====
factorOutput = table(1000000:0,
    `timestamp`symbol`close`ma_20`zscore`momentum,
    [TIMESTAMP, SYMBOL, DOUBLE, DOUBLE, DOUBLE, DOUBLE]
)

factorEngine = createReactiveStateEngine(
    name="factor_calc",
    metrics=[
        <close>,
        <mavg(close, 20) as ma_20>,
        <(close - mavg(close, 20)) / mstd(close, 20) as zscore>,
        <close / mavg(close, 20) - 1 as momentum>
    ],
    dummyTable=klineOutput,            // 输入是K线的schema
    outputTable=factorOutput,
    keyColumn=`symbol
)

subscribeTable(
    tableName="klineOutput",           // 注意：订阅的是普通表，需要用getStreamEngine语法
    actionName="factor_engine_sub",
    handler=factorEngine,
    msgAsTable=true
)

// ===== 第3级：因子值 → 横截面排名（横截面引擎）=====
rankingOutput = table(1000000:0,
    `timestamp`symbol`zscore`zscore_rank`momentum`momentum_rank,
    [TIMESTAMP, SYMBOL, DOUBLE, INT, DOUBLE, INT]
)

rankingEngine = createCrossSectionalEngine(
    name="factor_ranking",
    metrics=[
        <zscore>,
        <rank(zscore, false) as zscore_rank>,
        <momentum>,
        <rank(momentum, false) as momentum_rank>
    ],
    dummyTable=factorOutput,
    outputTable=rankingOutput,
    keyColumn=`timestamp,
    triggeringPattern=`keyCount,
    triggeringInterval=4000
)

subscribeTable(
    tableName="factorOutput",
    actionName="ranking_engine_sub",
    handler=rankingEngine,
    msgAsTable=true
)
```

---

### 三、使用 streamFilter 进行数据分流

```sql
// 将tick数据按条件分流到不同的下游管道
// 场景：主板数据走管道A，创业板数据走管道B

// 主板A股管道
share streamTable(1000000:0,
    `timestamp`symbol`price`volume,
    [TIMESTAMP, SYMBOL, DOUBLE, LONG]
) as mainBoardStream

// 创业板管道
share streamTable(1000000:0,
    `timestamp`symbol`price`volume,
    [TIMESTAMP, SYMBOL, DOUBLE, LONG]
) as gemStream

// 数据分流函数
def tickRouter(msg){
    mainBoardData = select * from msg where symbol like "000%" or symbol like "600%"
    gemData = select * from msg where symbol like "300%"

    if(size(mainBoardData) > 0)
        mainBoardStream.append!(mainBoardData)
    if(size(gemData) > 0)
        gemStream.append!(gemData)
}

subscribeTable(
    tableName="tickStream",
    actionName="router",
    handler=tickRouter,
    msgAsTable=true
)

// 然后各自订阅主板和创业板流表，挂载不同的策略引擎
```

---

### 四、流处理管道的可视化

虽然DolphinDB不直接提供可视化编排，但可以通过数据流日志清晰地追踪管道状态：

```sql
// 查看所有活跃的流引擎
getStreamEngineStat()

// 查看特定引擎的状态
getStreamEngineStat().TSECount           // 各引擎处理的消息数
getStreamEngineStat().memoryUsed         // 引擎内存使用量

// 获取管道的整体监控数据
def monitorPipeline(){
    stats = getStreamEngineStat()
    return select
        name,
        user,
        status,
        memUsed,
        numRows,
        lastEventTime
    from stats
    order by lastEventTime desc
}

monitorPipeline()
```

---

### 五、流数据处理最佳实践

| 实践 | 说明 | 收益 |
|------|------|------|
| **分级解耦** | 每级引擎专注单一功能 | 便于调试、复用和维护 |
| **批量处理** | 设置合理的batchSize（100-1000） | 平衡延迟和吞吐量 |
| **节流控制** | 设置throttle避免空转 | 减少CPU浪费 |
| **持久化中间状态** | 关键节点开启表持久化 | 防止宕机数据丢失 |
| **资源隔离** | 不同管线使用独立流表 | 避免相互影响 |
| **监控告警** | 定期检查引擎状态和积压 | 及时发现问题 |

```sql
// 流管道监控示例
def checkPipelineHealth(){
    stats = getStreamEngineStat()

    // 检查是否有引擎停止
    stopped = select * from stats where status != 'OK'
    if(size(stopped) > 0){
        // 记录告警日志
        writeLog("WARNING: Some engines stopped: " + string(stopped.name))
    }

    // 检查积压（处理队列中的消息数）
    overloaded = select * from stats where queueDepth > 10000
    if(size(overloaded) > 0){
        writeLog("WARNING: Queue overloaded for engines: " + string(overloaded.name))
    }

    return stats
}
```

> **核心思想**：流处理管道就像工厂的流水线——每个工位（引擎）只做一件事，但做得极快极好。原始数据从流水线入口进入，经过时间对齐 → 因子计算 → 横截面排名 → 信号生成 → 风险管理等多个工位后，变成可执行的交易指令。级联管道使得每级都可以独立优化和复用。
