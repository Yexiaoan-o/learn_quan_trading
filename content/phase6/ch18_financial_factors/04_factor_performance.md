## 因子绩效评估

### 4.1 因子评估概述

因子计算完成后，需要对因子的选股能力和预测效果进行系统评估。只有在历史上表现出稳定预测能力的因子，才值得纳入策略模型。

因子绩效评估的核心问题是：**该因子能否将未来收益率高的股票与未来收益率低的股票区分开来？**

### 4.2 IC分析（信息系数）

IC（Information Coefficient）是衡量因子预测能力的最核心指标。

#### 4.2.1 Rank IC

Rank IC计算因子值与未来收益率排名之间的秩相关系数（Spearman Rank Correlation）：

$$\text{Rank IC}_t = \text{corr}(\text{rank}(factor_t), \text{rank}(return_{t+1}))$$

```
// Rank IC计算
def calculateRankIC(factor, forwardReturn, tradeDate) {
    // factor: 因子值向量
    // forwardReturn: 未来一期收益率向量
    // 计算每个截面的秩相关系数
    result = select
        corr(rank(factor), rank(forwardReturn)) as RankIC
    from table(tradeDate, factor, forwardReturn)
    group by tradeDate
    return result
}

// 使用示例
factorTable = select
    Symbol, TradeDate,
    close / move(close, 20) - 1 as mom20,
    move(close, 1) / close - 1 as forwardReturn
from dailyTable
context by Symbol

ic_result = calculateRankIC(factorTable.mom20, factorTable.forwardReturn, factorTable.TradeDate)
```

#### 4.2.2 IC评估指标体系

计算整个回看期的IC统计量：

```
// IC统计量
ic_mean = avg(ic_result.RankIC)          // IC均值（反映平均预测能力）
ic_std = std(ic_result.RankIC)           // IC标准差（反映预测稳定性）
ic_ir = ic_mean / ic_std                 // IC信息比（最重要指标）
ic_win_rate = sum(ic_result.RankIC > 0) / size(ic_result)  // IC胜率

// IC累积曲线
ic_cumsum = cumsum(ic_result.RankIC)     // IC累计值应持续上升
```

IC评价标准：

| IC指标 | 优秀 | 良好 | 一般 | 无效 |
|--------|:---:|:---:|:---:|:---:|
| |IC Mean| > 0.05 | 0.03-0.05 | 0.01-0.03 | < 0.01 |
| ICIR | > 1.0 | 0.5-1.0 | 0.25-0.5 | < 0.25 |
| IC胜率 | > 60% | 55%-60% | 50%-55% | < 50% |

> **ICIR（Information Coefficient IR）**是评估因子质量的最重要单一指标。ICIR > 0.5 的因子具有较强的稳健预测能力。

### 4.3 分位数收益分析

分位数收益分析将股票按因子值分为若干组（通常是5组或10组），考察各组未来收益的分化程度。

```
// 分位数分组收益分析
def quantileAnalysis(factor, forwardReturn, nGroups=5) {
    // 在截面上按因子值大小排序分组
    factorRank = rank(factor) / size(factor)  // 0-1之间
    group = ceil(factorRank * nGroups)        // 分组编号 1-nGroups

    // 计算每组的平均未来收益
    groupReturn = select
        avg(forwardReturn) as avgReturn,
        group as Quantile
    from table(factor, forwardReturn, group)
    group by group

    // Top - Bottom 收益差
    topReturn = groupReturn[groupReturn.Quantile == nGroups].avgReturn[0]
    bottomReturn = groupReturn[groupReturn.Quantile == 1].avgReturn[0]
    spread = topReturn - bottomReturn

    return (groupReturn, spread)
}
```

**理想的分组收益形态**：各组收益应呈现明显的单调递增（或递减），即因子值越高收益越高（或越低）。Top组和Bottom组的收益差（Spread）越大，因子区分度越好。

### 4.4 因子换手率（Turnover）

因子换手率衡量多空组合的股票变动频率，换手率过高意味着交易成本大、策略不稳定。

```
// 计算因子换手率
def calculateTurnover(factor, tradeDate, nGroups=5) {
    // 对每个截面分组
    quantiles = select
        Symbol, TradeDate,
        floor((rank(factor) - 1) / (count(factor) / nGroups)) as group
    from table(tradeDate, Symbol, factor)
    context by TradeDate

    // 计算相邻日期Top组持仓的变动比例
    topStocks = select Symbol from quantiles where group == nGroups

    // 计算持仓重叠率
    turnover_by_date = select
        // 新进入减去退出（简化计算）
        1 - corr(rank(factor), rank(move(factor, 1))) / 2 as turnover
    from table(tradeDate, factor)
    group by tradeDate
    return avg(turnover_by_date.turnover)
}
```

换手率解读：

| 换手率 | 含义 | 实际影响 |
|--------|------|----------|
| < 20%/月 | 低换手 | 交易成本低，策略稳定 |
| 20%-50%/月 | 中换手 | 可接受，需考虑交易成本 |
| 50%-80%/月 | 高换手 | 扣除成本后收益可能大幅缩水 |
| > 80%/月 | 极高换手 | 实盘可行性存疑 |

### 4.5 因子衰减分析

因子衰减分析考察因子预测能力的持续性——因子对多长时间的收益率有预测能力？

```
// 因子衰减分析（Decay Analysis）
def factorDecay(factor, close, tradeDate, maxLag=20) {
    decay_ics = array(DOUBLE, maxLag, 0.0)
    for (lag in 1:maxLag) {
        forwardReturn = move(close, lag) / close - 1
        ic = corr(rank(factor), rank(forwardReturn))
        decay_ics[lag - 1] = ic
    }
    return decay_ics
}
// 绘制IC随滞后期的衰减曲线
// IC应在前几期较高，随滞后期延长而衰减
```

> **衰减曲线的用途**：IC衰减快的因子适合短期策略；IC衰减慢的因子适合中长期策略。如果IC在前3天内快速衰减至零，说明该因子仅适合日度换仓策略。

### 4.6 因子相关性矩阵

计算多个因子之间的相关性，避免选择高度相关的冗余因子。高度相关的因子组合不会带来增量信息。

```
// 因子相关性矩阵
def factorCorrelationMatrix(factors, tradeDate) {
    factorNames = factors.keys()
    n = size(factorNames)
    corrMatrix = matrix(DOUBLE, n, n)

    for (i in 0:(n-1)) {
        for (j in 0:(n-1)) {
            ic_val = select
                corr(rank(factors[factorNames[i]]), rank(factors[factorNames[j]]))
            from table(tradeDate, factors)
            group by tradeDate
            corrMatrix[i, j] = avg(ic_val[1])  // 取均值
        }
    }
    return (corrMatrix, factorNames)
}
```

因子相关性管理原则：

| 相关性范围 | 关系 | 建议 |
|------------|------|------|
| |r| > 0.8 | 高度相关 | 只保留IC更高的那个 |
| 0.5 < |r| < 0.8 | 中度相关 | 可通过正交化处理 |
| |r| < 0.5 | 低相关 | 可同时保留使用 |

### 4.7 综合评估报告

将所有评估指标汇总，形成因子评估报告：

```
// 生成因子评估报告
def factorEvaluationReport(factor, forwardReturn, tradeDate) {
    // IC统计
    ic_result = select
        corr(rank(factor), rank(forwardReturn)) as RankIC
    from table(tradeDate, factor, forwardReturn)
    group by tradeDate

    report = dict(STRING, ANY)
    report["IC_Mean"] = avg(ic_result.RankIC)
    report["IC_Std"] = std(ic_result.RankIC)
    report["ICIR"] = report["IC_Mean"] / report["IC_Std"]
    report["IC_WinRate"] = sum(ic_result.RankIC > 0) * 1.0 / size(ic_result)
    report["IC_tStat"] = report["IC_Mean"] / (report["IC_Std"] / sqrt(size(ic_result)))

    // 分位数分析
    nGroups = 5
    // ... 分位数组收益计算

    return report
}

// 打印因子评估报告
print("=============== 因子评估报告 ===============")
print("IC均值:    " + report["IC_Mean"])
print("ICIR:      " + report["ICIR"])
print("IC胜率:    " + report["IC_WinRate"])
print("IC t统计量:" + report["IC_tStat"])
print("=============================================")
```

> **总结**：一个合格因子的标准——|IC均值| > 0.03，ICIR > 0.5，IC胜率 > 55%，分组收益单调性好，换手率适中。如果因子通过以上所有检验，则可以纳入策略模型。
