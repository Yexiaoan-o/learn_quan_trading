## DolphinDB实现均值回归策略

在DolphinDB中实现均值回归策略，可以充分利用其强大的向量化计算引擎和内置的移动窗口函数，大幅简化代码复杂度并提升执行效率。本章将介绍如何在DolphinDB中实现布林带策略、Z-score信号生成以及配对交易的协整检验。

---

### 一、DolphinDB中的布林带计算

布林带是最经典的均值回归指标之一，其核心是移动均值和移动标准差的计算。DolphinDB提供了高效的`mavg`和`mstd`函数，可直接在SQL语句中完成整个计算流程。

#### 1.1 基本布林带计算

```sql
// 布林带三条线的计算
// 假设 daily_data 表中包含 symbol, date, close 字段

select
    symbol,
    date,
    close,
    mavg(close, 20) as bb_mid,                                    // 中轨：20日移动均线
    mavg(close, 20) + 2 * mstd(close, 20) as bb_upper,            // 上轨：中轨 + 2倍标准差
    mavg(close, 20) - 2 * mstd(close, 20) as bb_lower,            // 下轨：中轨 - 2倍标准差
    (close - mavg(close, 20)) / mstd(close, 20) as bb_zscore       // Z-score偏离度
from daily_data
where symbol = '000001.SZ'
order by date
```

#### 1.2 增强型布林带指标

除了基本的三条线，还可以在同一个查询中计算%b指标和带宽指标：

```sql
// 增强型布林带指标：包含%b和带宽
select
    symbol,
    date,
    close,
    mavg(close, 20) as bb_mid,
    mavg(close, 20) + 2 * mstd(close, 20) as bb_upper,
    mavg(close, 20) - 2 * mstd(close, 20) as bb_lower,
    // %b：价格在布林带中的相对位置
    (close - (mavg(close, 20) - 2 * mstd(close, 20))) /
        (4 * mstd(close, 20)) as bb_pct_b,
    // 带宽：衡量波动率水平
    (4 * mstd(close, 20)) / mavg(close, 20) as bb_bandwidth,
    // Z-score
    (close - mavg(close, 20)) / mstd(close, 20) as zscore
from daily_data
where symbol = '000001.SZ'
```

> **提示**：%b指标在布林带宽度为0（即mstd(close, 20) = 0）时会产生除零错误。在实际应用中，可以通过`iif(mstd(close, 20) == 0, 0.5, ...)`添加保护逻辑。

#### 1.3 布林带均值回归策略信号

```sql
// 完整的布林带策略信号生成
// 买入信号：价格跌破下轨（超跌）
// 卖出信号：价格突破上轨（超涨）
// 平仓信号：价格回归中轨

select
    symbol,
    date,
    close,
    mavg(close, 20) as bb_mid,
    mavg(close, 20) + 2 * mstd(close, 20) as bb_upper,
    mavg(close, 20) - 2 * mstd(close, 20) as bb_lower,
    case
        when close <= mavg(close, 20) - 2 * mstd(close, 20) then 1       // 超跌买入
        when close >= mavg(close, 20) + 2 * mstd(close, 20) then -1      // 超涨卖出
        else 0
    end as bb_signal,
    (close - mavg(close, 20)) / mstd(close, 20) as zscore
from daily_data
where symbol = '000001.SZ'
```

---

### 二、Z-score均值回归信号

Z-score是均值回归策略中最核心的信号指标，它量化了当前价格偏离历史均值的程度。统计学上，如果数据近似服从正态分布，那么约有95%的观测值会落在±2个标准差范围内。

#### 2.1 单标的Z-score计算

```sql
// Z-score均值回归信号
// Z-score = (price - moving_avg(price, N)) / moving_std(price, N)

select
    symbol,
    date,
    close,
    mavg(close, 60) as ma_60,                    // 60日均线作为长期均值
    mstd(close, 60) as std_60,                    // 60日标准差
    (close - mavg(close, 60)) / mstd(close, 60) as zscore_60,   // 60日Z-score

    // 多层次信号判断
    case
        when (close - mavg(close, 60)) / mstd(close, 60) < -2.0 then '强买入'
        when (close - mavg(close, 60)) / mstd(close, 60) < -1.5 then '弱买入'
        when (close - mavg(close, 60)) / mstd(close, 60) > 2.0 then '强卖出'
        when (close - mavg(close, 60)) / mstd(close, 60) > 1.5 then '弱卖出'
        else '观望'
    end as signal_level
from daily_data
where symbol = '000001.SZ'
order by date
```

#### 2.2 自定义函数实现Z-score策略

DolphinDB支持用户自定义函数，可以将均值回归逻辑封装为可复用的函数：

```sql
// 定义一个函数：计算均值回归信号
def meanReversionSignal(price, window, entryThreshold, exitThreshold){
    ma = mavg(price, window)
    std = mstd(price, window)
    zscore = (price - ma) / std

    // 生成信号：1=做多(超跌), -1=做空(超涨), 0=平仓(回归)
    signal = iif(zscore < -entryThreshold, 1,
             iif(zscore > entryThreshold, -1,
             iif(abs(zscore) < exitThreshold, 0, 0)))

    // 返回结果表
    return table(zscore as zscore, signal as signal, ma as ma, std as std)
}

// 调用自定义函数
t = select * from daily_data where symbol = '000001.SZ' order by date
result = meanReversionSignal(t.close, 60, 2.0, 0.5)
```

---

### 三、配对交易的协整检验

配对交易需要在DolphinDB中进行协整检验，以确定两只股票之间是否存在稳定的长期均衡关系。

#### 3.1 计算价差和对冲比率

```sql
// 配对交易的价差计算
// 假设 stock_a 和 stock_b 是两个股票的价格表

// 步骤1：合并两只股票的价格数据
prices = select a.date as date, a.close as close_a, b.close as close_b
    from daily_data as a
    left join daily_data as b
    on a.date = b.date
    where a.symbol = '000001.SZ' and b.symbol = '600036.SH'

// 步骤2：计算滚动对冲比率（使用最小二乘法）
// hedge_ratio = mbeta(close_a, close_b, 120) — 以close_b为自变量

select
    date,
    close_a,
    close_b,
    // 滚动回归的Beta系数即为对冲比率
    mbeta(close_a, close_b, 120) as hedge_ratio,
    // 价差 = A - hedge_ratio * B
    close_a - mbeta(close_a, close_b, 120) * close_b as spread,
    // 价差的Z-score（用于产生交易信号）
    (close_a - mbeta(close_a, close_b, 120) * close_b -
     mavg(close_a - mbeta(close_a, close_b, 120) * close_b, 60)) /
     mstd(close_a - mbeta(close_a, close_b, 120) * close_b, 60) as spread_zscore
from prices
order by date
```

#### 3.2 配对交易信号生成

```sql
// 配对交易信号：基于价差Z-score
def pairTradingSignal(spreadZscore, entryZ, exitZ){
    // 当spread的Z-score超过entryZ时，价差偏离过大，入场
    // 当spread的Z-score回到exitZ以内时，价差回归，出场

    signal = array(INT, size(spreadZscore))
    position = 0

    for(i in 0..(size(spreadZscore)-1)){
        if(position == 0){
            if(spreadZscore[i] > entryZ){
                // 价差过高：A相对B高估 → 做空A，做多B（做空价差）
                signal[i] = -1
                position = -1
            } else if(spreadZscore[i] < -entryZ){
                // 价差过低：A相对B低估 → 做多A，做空B（做多价差）
                signal[i] = 1
                position = 1
            }
        } else {
            // 检查出场条件
            if((position > 0 and spreadZscore[i] >= -exitZ) or
               (position < 0 and spreadZscore[i] <= exitZ)){
                signal[i] = 0
                position = 0
            }
        }
    }
    return signal
}

// 生成配对交易信号
spreadData = select
    date,
    close_a - mbeta(close_a, close_b, 120) * close_b as spread,
    (close_a - mbeta(close_a, close_b, 120) * close_b -
     mavg(close_a - mbeta(close_a, close_b, 120) * close_b, 60)) /
     mstd(close_a - mbeta(close_a, close_b, 120) * close_b, 60) as zscore
from prices

// 添加信号列
update spreadData set signal = pairTradingSignal(spreadData.zscore, 2.0, 0.5)
```

---

### 四、多股票批量均值回归策略

在实际量化交易中，通常需要对全市场股票同时运行均值回归策略。DolphinDB的分组计算能力使这一任务非常高效：

```sql
// 全市场布林带策略信号（按股票分组计算）
select
    symbol,
    date,
    close,
    mavg(close, 20) as ma_20,
    mstd(close, 20) as std_20,
    mavg(close, 20) + 2 * mstd(close, 20) as bb_upper,
    mavg(close, 20) - 2 * mstd(close, 20) as bb_lower,
    (close - mavg(close, 20)) / mstd(close, 20) as zscore,
    // 综合评分：结合偏离度和波动率
    abs((close - mavg(close, 20)) / mstd(close, 20)) *
    (mstd(close, 20) / mavg(close, 20)) as reversion_score
from daily_data
where date >= 2020.01.01
context by symbol    // 按股票分组，每组独立计算
order by date
```

#### 4.1 筛选最强均值回归信号

```sql
// 在每个交易日，选出Z-score偏离最大的前10只股票
reversion_signals = select
    symbol,
    date,
    close,
    (close - mavg(close, 60)) / mstd(close, 60) as zscore
from daily_data
context by symbol

// 按日期和Z-score绝对值降序排列
top_signals = select top 10 symbol, date, zscore
    from reversion_signals
    context by date
    having abs(zscore) > 1.5
    order by abs(zscore) desc
```

---

### 五、性能优化建议

在DolphinDB中运行均值回归策略时，以下优化可以显著提升性能：

| 优化措施 | 说明 | 效果 |
|----------|------|------|
| **分区表存储** | 按日期分区，按symbol分桶 | 查询只扫描相关分区，速度提升10-100倍 |
| **物化中间结果** | 将频繁使用的移动均线预先计算并存储 | 避免重复计算 |
| **pipeline并行** | 使用`ploop`或`peach`并行处理多股票 | 充分利用多核CPU |
| **控制窗口大小** | 过大的窗口（>500）会降低性能 | 在满足策略需求的前提下使用合适窗口 |

```sql
// 使用高阶函数peach并行处理多股票
symbols = exec distinct symbol from daily_data

def calculateBollingerForSymbol(sym){
    return select
        symbol,
        date,
        close,
        mavg(close, 20) as bb_mid,
        mavg(close, 20) + 2 * mstd(close, 20) as bb_upper,
        mavg(close, 20) - 2 * mstd(close, 20) as bb_lower,
        (close - mavg(close, 20)) / mstd(close, 20) as zscore
    from daily_data
    where symbol = sym
    order by date
}

// 并行计算所有股票的布林带
results = ploop(calculateBollingerForSymbol, symbols)
```

> **核心要点**：DolphinDB的向量化计算引擎和分组处理能力使得均值回归策略的实现异常简洁。通过`mavg`和`mstd`函数，一行代码即可完成布林带的计算；通过`context by`语法，能在一次查询中完成全市场所有股票的分组策略计算。这是传统逐行循环的Python所无法比拟的性能优势。
