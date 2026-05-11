## 流数据处理引擎

DolphinDB提供了多种内置流数据引擎，每种针对特定的计算模式进行了优化。这些引擎内部维护增量状态，无需用户在handler中手动管理累积变量。

---

### 一、流引擎总览

| 引擎名称 | 创建函数 | 计算模式 | 典型用途 |
|----------|----------|----------|----------|
| **时间序列引擎** | `createTimeSeriesEngine` | 滚动窗口聚合 | 实时K线、移动均线 |
| **横截面引擎** | `createCrossSectionalEngine` | 横截面排名/分组 | 实时因子排名、行业中性化 |
| **响应式状态引擎** | `createReactiveStateEngine` | 有状态增量计算 | 实时MACD、自定义指标 |
| **异常检测引擎** | `createAnomalyDetectionEngine` | 统计异常检测 | 异常价格监控、风控预警 |
| **回放引擎** | `createReplayEngine` | 历史数据回放 | 策略回测、仿真测试 |

---

### 二、时间序列引擎（Time Series Engine）

最常用的流引擎，在流数据上实现滚动窗口计算——等价于批处理中的`mavg`、`mstd`等窗口函数，但是以增量方式实现。

```sql
// 创建时间序列引擎
tsEngine = createTimeSeriesEngine(
    name="ts_kline_1min",           // 引擎名称
    windowSize=60,                   // 窗口大小
    step=1,                          // 计算步长
    metrics=[
        <first(price)>,              // 开盘价
        <max(price)>,                // 最高价
        <min(price)>,                // 最低价
        <last(price)>,               // 收盘价
        <sum(volume)>,               // 成交量
        <avg(price * volume) / avg(volume)>  // VWAP
    ],
    dummyTable=tickStream,           // 用于推断schema的模板表
    outputTable=resultTable,         // 输出表
    timeColumn=`timestamp,           // 时间列
    keyColumn=`symbol,               // 分组键
    useSystemTime=false,             // 使用数据时间而非系统时间
    fill=[0.0, 0.0, 0.0, 0.0, 0, 0.0]
)

// 订阅流表到时间序列引擎
subscribeTable(
    tableName="inputStream",
    actionName="tsEngineAction",
    handler=tsEngine,                // handler直接指向引擎
    msgAsTable=true,
    batchSize=1
)
```

#### 时间序列引擎参数详解

| 参数 | 说明 | 常见配置 |
|------|------|----------|
| `windowSize` | 窗口大小（按记录数或时间长度） | K线用1-60，均线用20-250 |
| `step` | 计算步长 | 1=每条新数据都计算，60=每分钟计算 |
| `useSystemTime` | false用数据自带时间戳，true用系统时间 | 回放历史用false，实时用true |
| `keyColumn` | 分组键 | 按symbol分组计算 |
| `metrics` | 聚合函数列表 | 支持DolphinDB所有聚合函数 |

---

### 三、横截面引擎（Cross-Sectional Engine）

在实时流数据上完成横截面（cross-sectional）计算——在同一时间点对所有股票做排名、分位数、标准化等操作。

```sql
// 创建横截面引擎：实时计算因子排名
csEngine = createCrossSectionalEngine(
    name="factor_ranking",
    metrics=[
        <rank(factor_value, false) as factor_rank>,                         // 因子排名
        <(factor_value - avg(factor_value)) / std(factor_value) as zscore>, // 标准化
        <percentileRank(factor_value) as pct_rank>                          // 百分位排名
    ],
    dummyTable=factorStream,
    outputTable=rankedFactorTable,
    keyColumn=`date,              // 横截面的时间标识
    triggeringPattern=`keyCount,  // 触发模式：等所有股票到齐
    triggeringInterval=4000       // 期望到达的股票数量
)

// 横截面引擎的触发模式
// keyCount: 等待所有分组键到齐后才计算（适合每日因子排名）
// interval: 按时间间隔触发（适合实时排名，容忍缺失）
```

**横截面引擎的核心价值**：在实时环境中，不同股票的行情到达时间可能有几毫秒的差异。横截面引擎会自动等待所有股票数据到齐（或达到时间窗口）后，一次性计算所有股票的排名，确保排名的一致性。

```sql
// 实时行业中性化（横截面引擎应用）
csIndustryNeutral = createCrossSectionalEngine(
    name="industry_neutral",
    metrics=[
        // 行业分组内标准化
        <(factor_value - avg(factor_value)) / std(factor_value)>,
        // 行业中性化排名
        <rank(factor_value, false)>
    ],
    dummyTable=factorStream,
    outputTable=neutralFactorTable,
    keyColumn=`date`industry,
    triggeringPattern=`keyCount,
    triggeringInterval=4000
)
```

---

### 四、响应式状态引擎（Reactive State Engine）

最灵活的流引擎，适用于需要维护内部状态的自定义计算（如EMA递推、布林带宽度变化等）：

```sql
// 创建响应式状态引擎：计算实时MACD
reactiveEngine = createReactiveStateEngine(
    name="macd_stream",
    metrics=[
        // 使用streaming函数计算MACD
        <ema(close, 12)>,
        <ema(close, 26)>,
        <ema(close, 12) - ema(close, 26) as DIF>,
        <ema(ema(close, 12) - ema(close, 26), 9) as DEA>,
        <2 * (ema(close, 12) - ema(close, 26) - ema(ema(close, 12) - ema(close, 26), 9)) as MACD>
    ],
    dummyTable=tickStream,
    outputTable=macdResultTable,
    keyColumn=`symbol
)

// 响应式状态引擎 vs 时间序列引擎
// 时间序列引擎：固定窗口/步长，窗口一到就计算
// 响应式状态引擎：维护内部状态，逐条增量更新，不依赖窗口边界
```

---

### 五、异常检测引擎

用于实时监控市场异常：

```sql
// 创建异常检测引擎
anomalyEngine = createAnomalyDetectionEngine(
    name="price_anomaly",
    metrics=[
        // 价格偏离移动均线超过3个标准差
        <abs(price - mavg(price, 60)) > 3 * mstd(price, 60)>,
        // 单笔成交量超过历史均值的5倍
        <volume > 5 * avg(volume)>,
        // 价格单笔跳动超过2%
        <abs(price / prev(price) - 1) > 0.02>
    ],
    dummyTable=tickStream,
    outputTable=anomalyTable,
    keyColumn=`symbol,
    windowSize=300          // 异常检测参考的历史窗口
)

// 异常检测引擎的处理逻辑
// 每个条件返回true/false，true表示触发异常
// 可以同时监控多个维度的异常
```

---

### 六、引擎选择指南

```
需要什么样的流计算？
│
├─ 滚动窗口聚合（K线、均线）→ 时间序列引擎
│
├─ 横截面排名/分组 → 横截面引擎
│
├─ 自定义状态维护（EMA递推等）→ 响应式状态引擎
│
├─ 风控监控/异常检测 → 异常检测引擎
│
└─ 历史数据回放 → 回放引擎
```

| 引擎类型 | 延迟 | 复杂度 | 适用规模 |
|----------|------|--------|----------|
| 时间序列引擎 | ~1ms | 低 | 万级股票×分钟级 |
| 横截面引擎 | ~5ms | 中 | 全市场4000+股票 |
| 响应式状态引擎 | <1ms | 高 | 千级股票×毫秒级 |
| 异常检测引擎 | ~2ms | 中 | 全市场监控 |

> **配置要点**：`dummyTable`参数用于推断输出表的schema，它必须与实际流入数据的表结构一致（列名和类型相同）。如果schema不匹配，引擎将无法正确初始化和运行。
