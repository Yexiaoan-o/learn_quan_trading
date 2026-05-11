## 混合编程范式

DolphinDB最大的特色之一是支持**多范式混合编程**——在同一段代码中融合SQL查询、向量化计算、函数式编程和命令式脚本。这种灵活性让量化策略的编写既高效又富有表现力。本章将展示如何在实际金融计算中融汇多种范式。

---

### 一、DolphinDB的多范式融合

```
┌─────────────────────────────────────────────────────┐
│                  DolphinDB 编程范式                   │
├─────────────┬───────────────┬───────────────────────┤
│  SQL查询    │  向量化计算    │  函数式编程            │
│  (声明式)   │  (高性能)     │  (可组合)              │
├─────────────┴───────────────┴───────────────────────┤
│              混合编程 = 各取所长                      │
│  SQL获取数据 → 向量化高效变换 → 函数式灵活应用         │
└─────────────────────────────────────────────────────┘
```

每种范式都有其最适合的场景：

| 范式 | 最适合 | 不擅长 |
|------|--------|--------|
| **SQL** | 数据筛选、分组聚合、窗口计算 | 复杂控制流、递归 |
| **向量化** | 整列数值运算、统计计算 | 逐行逻辑判断 |
| **函数式** | 数据变换管道、批量apply | 状态管理 |
| **命令式** | 复杂的控制流、状态机 | 大批量数据循环 |

---

### 二、混合编程实战案例

#### 案例1：完整的因子研究流程

```sql
// 混合范式：因子计算 → 分组分析 → 结果可视化

def comprehensiveFactorAnalysis(
    priceTable, factorTable, holdingPeriod=20
){
    // ===== 第1步：SQL获取数据并做窗口计算（SQL + 向量化）=====
    base_data = select
        date,
        symbol,
        close,
        mavg(close, 60) as ma_60,
        mstd(close, 60) as std_60,
        // 向量化Z-score计算
        (close - mavg(close, 60)) / mstd(close, 60) as zscore,
        // 向量化动量计算
        log(close / move(close, holdingPeriod)) as fwd_return
    from priceTable
    context by symbol

    // ===== 第2步：使用aj对齐因子值（SQL）=====
    aligned = select
        b.date,
        b.symbol,
        b.zscore,
        b.fwd_return
    from aj(
        base_data as b,
        factorTable as f,
        `symbol`date
    )

    // ===== 第3步：函数式分层分析 =====
    // 定义分层计算函数
    quantileAnalysis = def(tbl, nQ=5){
        update tbl set quantile = rank(zscore) * nQ \ count(*) + 1
            context by date

        return select
            quantile,
            avg(fwd_return) as avg_return,
            std(fwd_return) as std_return,
            avg(fwd_return) / std(fwd_return) * sqrt(252) as sharpe,
            sum(fwd_return > 0) * 1.0 / count(*) as win_rate,
            count(*) as stock_count
        from tbl
        group by quantile
        order by quantile
    }

    return quantileAnalysis(aligned)
}
```

#### 案例2：批量策略回测 + 结果聚合

```sql
// 混合范式：批量对多只股票回测

def batchBacktest(symbols, priceData, strategyFunc){
    // ===== 第1步：SQL筛选数据 =====
    all_prices = select * from priceData
        where symbol in symbols
        order by symbol, date

    // ===== 第2步：函数式并行回测 =====
    // 使用peach并行执行回测
    results = peach(def(sym){
        // 命令式：提取单只股票的数据
        stock_data = select * from all_prices where symbol = sym

        // 调用策略函数计算信号（策略内部可混用SQL/向量化）
        signal_data = strategyFunc(stock_data)

        // 向量化计算收益统计
        rets = signal_data.daily_ret
        sharpe = avg(rets) / std(rets) * sqrt(252)          // 向量化
        max_dd = min(cumprod(1 + rets) / cummax(cumprod(1 + rets)) - 1)  // 向量化
        annual_ret = (cumprod(1 + rets).last()) pow (252.0 / size(rets)) - 1

        // 返回结构化结果
        return {
            symbol: sym,
            sharpe: sharpe,
            max_drawdown: max_dd,
            annual_return: annual_ret,
            win_rate: sum(rets > 0) * 1.0 / size(rets)
        }
    }, symbols)

    // ===== 第3步：SQL聚合结果 =====
    return select
        symbol,
        sharpe,
        max_drawdown,
        annual_return,
        win_rate
    from table(results)
    order by sharpe desc
}
```

---

### 三、管道 + 函数组合模式

将管道操作符与自定义函数组合，可以构建高度可读的数据处理流程：

```sql
// 因子数据处理管道
def prepareFactorData(raw_data){
    return raw_data
        // SQL筛选
        |> select where close > 0 and volume > 0
        |> select where date between 2020.01.01 : 2024.12.31
        // 向量化计算
        |> select
            *,
            log(close / prev(close)) as log_ret,
            mavg(close, 20) as ma_20,
            mstd(close, 60) as std_60
        // 向量化因子生成
        |> select
            *,
            (close - ma_20) / std_60 as zscore,                    // 均值回归因子
            log(close / move(close, 252)) as momentum_annual,      // 年动量
            sum(sign(log_ret) * volume, 5) as obv_5d              // OBV变化
        // 函数式变换
        |> each(def(col):
            (col - avg(col)) / std(col), [zscore, momentum_annual, obv_5d]
        )
}
```

---

### 四、状态管理的混合方式

有些量化计算需要维护跨周期的状态（如EMA递推、累计值）：

```sql
// 混合方式：SQL获取数据 + 命令式管理状态 + 向量化计算
def calculateAdaptiveSignal(data){
    // SQL：获取基础数据
    base = select
        symbol, date, close, volume,
        mavg(close, 20) as ma,
        mstd(close, 20) as std
    from data
    context by symbol
    order by symbol, date

    // 命令式：维护自适应阈值状态
    update base set adaptive_threshold = 2.0

    symbols = exec distinct symbol from base
    for(sym in symbols){
        // 针对每只股票：如果近期信号频率过高，动态扩大阈值
        sym_data = select * from base where symbol = sym

        lookback = 60
        signal_count = msum(abs(sym_data.zscore) > sym_data.adaptive_threshold, lookback)

        // 向量化：整列调整阈值
        adjusted = iif(signal_count > lookback / 3,
            2.5,          // 信号太多 → 调高阈值
            2.0           // 保持默认
        )

        update base set adaptive_threshold = adjusted where symbol = sym
    }

    // 向量化生成最终信号
    update base set signal = iif(
        (close - ma) / std < -adaptive_threshold, 1,
        iif((close - ma) / std > adaptive_threshold, -1, 0)
    )

    return base
}
```

---

### 五、范式选择的决策指南

```
开始编写代码
    │
    ├─ 是数据筛选/分组聚合？ ───────→ 用 SQL
    │
    ├─ 是整列数值运算？ ────────────→ 用向量化
    │
    ├─ 是需要对每个元素/组应用函数？ ─→ 用函数式（each/peach）
    │
    ├─ 是复杂控制流/状态机？ ───────→ 用命令式（if/for/while）
    │
    └─ 是数据串联变换？ ────────────→ 用管道操作符
```

| 场景 | 推荐范式组合 | 理由 |
|------|-------------|------|
| 因子计算 | SQL + 向量化 | SQL获取数据，整列窗口计算 |
| 策略回测 | SQL + 函数式 | SQL筛选数据，peach并行回测 |
| 数据清洗 | SQL + 管道 | SQL过滤，管道串联多个清洗步骤 |
| 实时监控 | 命令式 + 向量化 | 命令式管理状态，向量化做信号计算 |
| 报告生成 | SQL + 函数式 | SQL聚合统计，函数式做格式化 |

> **核心思想**：没有一种范式能解决所有问题。优秀的DolphinDB代码应当是**各范式的和谐交响**——SQL负责"取什么数据"，向量化负责"怎么算得快"，函数式负责"如何复用逻辑"，命令式负责"如何处理特殊情况"。掌握这种混合编程思维，才能真正发挥DolphinDB的全部威力。
