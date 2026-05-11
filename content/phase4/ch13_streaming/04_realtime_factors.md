## 实时因子计算

量化因子的实时计算是量化交易中最具挑战性的任务之一——既要保证计算逻辑的历史一致性，又要满足低延迟的实时性要求。DolphinDB的"流批统一"特性使得同一套因子代码可以在历史回测和实盘交易中共用。

---

### 一、流批统一（Stream-Batch Unification）

DolphinDB的核心设计原则之一是**同一套代码同时适用于批处理和流处理**：

```
                    ┌─────────────────────┐
相同的因子计算逻辑    │  def calculateMACD() │
                    └─────────────────────┘
                           │         │
                    历史回测│         │实盘交易
                          ▼         ▼
                    ┌──────────┐ ┌──────────────┐
                    │ SQL查询   │ │ 响应式状态引擎 │
                    │ (批处理)  │ │ (流处理)      │
                    └──────────┘ └──────────────┘
```

```sql
// 同一套MACD计算逻辑

// ========== 历史回测（批处理） ==========
def macdBatch(data){
    return select
        symbol,
        date,
        close,
        ema(close, 12) - ema(close, 26) as DIF,
        ema(ema(close, 12) - ema(close, 26), 9) as DEA,
        2 * (ema(close, 12) - ema(close, 26) - ema(ema(close, 12) - ema(close, 26), 9)) as MACD
    from data
    context by symbol
}

// ========== 实盘交易（流处理） ==========
macdStreamEngine = createReactiveStateEngine(
    name="macd_live",
    metrics=[
        <close>,
        <ema(close, 12) - ema(close, 26) as DIF>,
        <ema(ema(close, 12) - ema(close, 26), 9) as DEA>,
        <2 * (ema(close, 12) - ema(close, 26) - ema(ema(close, 12) - ema(close, 26), 9)) as MACD>
    ],
    dummyTable=tickStream,
    outputTable=macdLiveResult,
    keyColumn=`symbol
)
```

---

### 二、实时MACD因子部署

```sql
// 完整的实时MACD因子部署流程

// 步骤1：创建输入输出
share streamTable(1000000:0,
    `timestamp`symbol`close,
    [TIMESTAMP, SYMBOL, DOUBLE]
) as priceStream

macdOutput = table(1000000:0,
    `timestamp`symbol`DIF`DEA`MACD`signal,
    [TIMESTAMP, SYMBOL, DOUBLE, DOUBLE, DOUBLE, INT]
)

// 步骤2：创建MACD引擎（含信号判断）
macdEngine = createReactiveStateEngine(
    name="macd_with_signal",
    metrics=[
        <ema(close, 12) - ema(close, 26) as DIF>,
        <ema(ema(close, 12) - ema(close, 26), 9) as DEA>,
        <2 * (ema(close, 12) - ema(close, 26) - ema(ema(close, 12) - ema(close, 26), 9)) as MACD>,
        // 实时信号：金叉买入，死叉卖出
        <case
            when prev(ema(close, 12) - ema(close, 26)) < prev(ema(ema(close, 12) - ema(close, 26), 9))
                 and (ema(close, 12) - ema(close, 26)) > ema(ema(close, 12) - ema(close, 26), 9)
            then 1                    // 金叉
            when prev(ema(close, 12) - ema(close, 26)) > prev(ema(ema(close, 12) - ema(close, 26), 9))
                 and (ema(close, 12) - ema(close, 26)) < ema(ema(close, 12) - ema(close, 26), 9)
            then -1                   // 死叉
            else 0
        end as signal>
    ],
    dummyTable=priceStream,
    outputTable=macdOutput,
    keyColumn=`symbol
)

subscribeTable(tableName="priceStream", actionName="macd_live", handler=macdEngine, msgAsTable=true)
```

---

### 三、实时复合因子计算

多因子合成在流处理中的实现：

```sql
// 实时多因子合成引擎
share streamTable(1000000:0,
    `timestamp`symbol`close`volume`high`low,
    [TIMESTAMP, SYMBOL, DOUBLE, LONG, DOUBLE, DOUBLE]
) as priceVolumeStream

compositeOutput = table(1000000:0,
    `timestamp`symbol`momentum`volatility`volume_ratio`composite_score,
    [TIMESTAMP, SYMBOL, DOUBLE, DOUBLE, DOUBLE, DOUBLE]
)

compositeEngine = createReactiveStateEngine(
    name="composite_factor",
    metrics=[
        // 因子1：短期动量（5日收益率）
        <close / move(close, 5) - 1 as momentum>,
        // 因子2：波动率（20日标准差）
        <mstd(log(close / prev(close)), 20) * sqrt(252) as volatility>,
        // 因子3：量比（5日均量 / 20日均量）
        <mavg(volume, 5) / mavg(volume, 20) as volume_ratio>,
        // 综合得分：因子标准化后等权加总
        // 注：在流引擎中使用window函数实现标准化
        <(
            (close / move(close, 5) - 1 - mavg(close / move(close, 5) - 1, 20)) / mstd(close / move(close, 5) - 1, 20)
            + (mavg(volume, 5) / mavg(volume, 20) - mavg(mavg(volume, 5) / mavg(volume, 20), 20))
              / mstd(mavg(volume, 5) / mavg(volume, 20), 20)
            - (mstd(log(close / prev(close)), 20) * sqrt(252) - mavg(mstd(log(close / prev(close)), 20) * sqrt(252), 20))
              / mstd(mstd(log(close / prev(close)), 20) * sqrt(252), 20)
        ) / 3 as composite_score>
    ],
    dummyTable=priceVolumeStream,
    outputTable=compositeOutput,
    keyColumn=`symbol
)
```

---

### 四、流处理中的因子状态管理

实时因子计算的一个关键挑战是状态管理——引擎需要记住之前的状态来递推新值：

```sql
// 演示：实现一个需要跨数据批次维护状态的因子

// 自定义状态引擎：记录每只股票的历史最高价
def createHighWaterMarkEngine(streamTable, outputTable){
    // 使用字典存储状态
    highWaterMarks = dict(STRING, DOUBLE)

    def handler(msg){
        result = select
            last(timestamp) as timestamp,
            symbol,
            close,
            iif(close > highWaterMarks[symbol], close, highWaterMarks[symbol]) as high_water_mark,
            iif(close > highWaterMarks[symbol], true, false) as new_high
        from msg
        context by symbol

        // 更新历史最高价
        for(row in result){
            sym = row.symbol
            if(row.new_high)
                highWaterMarks[sym] = row.close
        }

        outputTable.append!(result)
    }

    subscribeTable(tableName=streamTable, actionName="high_water", handler=handler, msgAsTable=true)
}
```

---

### 五、实盘因子部署模式

```
部署架构：

┌─────────────┐     ┌───────────────┐     ┌──────────────┐     ┌────────────┐
│  行情网关     │ ──→ │ 流表(原始tick)  │ ──→ │ 因子计算引擎  │ ──→ │ 因子输出表  │
│  (API接入)   │     │               │     │              │     │            │
└─────────────┘     └───────────────┘     └──────────────┘     └────────────┘
                                                                    │
                                                                    ▼
                                                              ┌────────────┐
                                                              │  交易信号表  │
                                                              └────────────┘
```

部署检查清单：

| 检查项 | 说明 | 验证方法 |
|--------|------|----------|
| 因子一致性 | 流结果 = 批结果 | 回放历史数据对比输出 |
| 延迟 | p99延迟 < 目标值 | 记录引擎处理时间戳差 |
| 状态正确性 | 递推计算无误 | 断点续传后对比全量重算 |
| 容错 | 异常恢复后状态不丢失 | 模拟断网重连测试 |
| 资源 | 内存/CPU在预算内 | getStreamEngineStat()监控 |

> **部署策略**：实际生产环境中，先在历史数据上用批处理模式验证因子逻辑的正确性和预测能力，确认有效后再切换到流模式部署。因子逻辑一旦在批处理中验证通过，流处理中只需切换引擎类型即可——这就是"流批统一"带来的工程效率提升。
