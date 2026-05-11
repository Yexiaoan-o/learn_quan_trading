## DolphinDB因子计算与因子库

DolphinDB为量化因子研究提供了丰富的内置因子库和高效的计算工具。用户既可以直接调用业界标准因子库（如国泰君安191因子、WorldQuant 101因子），也可以利用强大的向量化函数自定义因子计算。本章将介绍DolphinDB中的常用因子模块及其使用方法。

---

### 一、DolphinDB内置因子库

#### 1.1 国泰君安191因子（gtja191Alpha）

国泰君安证券研究所发布的191个Alpha因子是国内量化界最经典的因子集合，DolphinDB将其完整实现：

```sql
// 加载国泰君安191 Alpha因子模块
use gtja191Alpha

// 计算第1号因子：Alpha001
// 计算公式：(-1 * CORR(RANK(DELTA(LOG(VOLUME), 1)), RANK(((CLOSE - OPEN) / OPEN)), 6))
alpha001 = gtja191Alpha::alpha001(open, high, low, close, volume, amount, vwap, cap, returns)

// 批量计算多个因子
alpha002 = gtja191Alpha::alpha002(open, high, low, close, volume, amount, vwap, cap, returns)
alpha003 = gtja191Alpha::alpha003(open, high, low, close, volume, amount, vwap, cap, returns)

// 对全市场股票批量计算因子
select
    symbol,
    date,
    gtja191Alpha::alpha001(open, high, low, close, volume, amount, vwap, cap, returns) as alpha_001,
    gtja191Alpha::alpha010(open, high, low, close, volume, amount, vwap, cap, returns) as alpha_010,
    gtja191Alpha::alpha020(open, high, low, close, volume, amount, vwap, cap, returns) as alpha_020
from daily_data
context by symbol
```

#### 1.2 WorldQuant 101因子（wq101alpha）

WorldQuant发布的101个公式化Alpha因子也是业界标准，DolphinDB同样提供了完整实现：

```sql
// 加载WorldQuant 101 Alpha因子模块
use wq101alpha

// 计算WQ Alpha #1
// 买入排名前20%的股票
alpha001 = wq101alpha::alpha001(open, high, low, close, volume, amount, vwap, cap, returns)

// 计算WQ Alpha #38（经典动量-反转组合因子）
alpha038 = wq101alpha::alpha038(open, high, low, close, volume, amount, vwap, cap, returns)

// 批量计算示例
select
    symbol,
    date,
    wq101alpha::alpha001(open, high, low, close, volume, amount, vwap, cap, returns) as wq_001,
    wq101alpha::alpha038(open, high, low, close, volume, amount, vwap, cap, returns) as wq_038,
    wq101alpha::alpha101(open, high, low, close, volume, amount, vwap, cap, returns) as wq_101
from daily_data
context by symbol
```

---

### 二、技术分析模块（ta）

`ta`模块提供了丰富的技术指标函数，适合快速构建技术因子：

```sql
use ta

// MACD指标
select
    symbol,
    date,
    close,
    ta::macd(close, 12, 26, 9) as MACD,          // MACD柱（DIF - DEA）
    ta::diff(close, 12, 26) as DIF,               // 快慢线差值
    ta::dea(close, 12, 26, 9) as DEA,             // 信号线
    ta::rsi(close, 14) as RSI,                    // 相对强弱指标
    ta::kdj(high, low, close, 9, 3, 3) as KDJ_K, // KDJ指标K值
    ta::boll(close, 20, 2) as BOLL_MID            // 布林带中轨
from daily_data
context by symbol
```

**ta模块常用函数速查**：

| 函数 | 参数 | 说明 |
|------|------|------|
| `ta::macd(close, 12, 26, 9)` | 快速EMA, 慢速EMA, 信号线周期 | MACD柱 |
| `ta::rsi(close, 14)` | 价格, 周期 | 相对强弱指标(0-100) |
| `ta::boll(close, 20, 2)` | 价格, 周期, 标准差倍数 | 布林带中轨 |
| `ta::kdj(high, low, close, 9, 3, 3)` | 高, 低, 收, 周期, 平滑1, 平滑2 | KDJ指标的K值 |
| `ta::atr(high, low, close, 14)` | 高, 低, 收, 周期 | 平均真实波幅 |
| `ta::obv(close, volume)` | 价格, 成交量 | 能量潮指标 |

---

### 三、自定义因子计算

DolphinDB的向量化函数使自定义因子计算效率极高：

```sql
// ===== 例1：自定义动量因子 =====
select
    symbol,
    date,
    close,
    // 12-1个月动量（跳过最近1个月）
    returns(move(close, 21), 230) as momentum_12m1,
    // 短期反转因子（最近5日收益反转）
    -1 * returns(close, 5) as reversal_5d,
    // 波动率调整动量
    returns(move(close, 21), 230) / mstd(returns(close, 1), 252) as vol_adj_momentum
from daily_data
context by symbol


// ===== 例2：自定义质量因子（需要财务数据）=====
// 假设 fundamentals 表包含净利润、净资产、总资产等字段
select
    symbol,
    date,
    net_income / total_equity as roe,
    (revenue - cost) / revenue as gross_margin,
    total_liabilities / total_assets as debt_ratio,
    // 综合质量得分（等权）
    (
        (net_income / total_equity - avg(net_income / total_equity)) / std(net_income / total_equity) +
        ((revenue - cost) / revenue - avg((revenue - cost) / revenue)) / std((revenue - cost) / revenue) -
        (total_liabilities / total_assets - avg(total_liabilities / total_assets)) / std(total_liabilities / total_assets)
    ) / 3 as quality_score
from fundamentals
context by date
```

---

### 四、因子表现评估

在DolphinDB中进行因子评估，可以高效计算IC、分层收益等指标：

```sql
// 计算因子的Rank IC序列（按日期）
def calculateDailyIC(factorTable, returnTable){
    // 合并因子值和未来收益
    joined = select
        f.date as date,
        f.symbol as symbol,
        f.factor_value as factor,
        r.fwd_return_5d as fwd_ret
    from factorTable as f
    left join returnTable as r
    on f.date = r.date and f.symbol = r.symbol

    // 按日期分组计算Rank IC（Spearman）
    daily_ic = select
        date,
        corr(rank(factor), rank(fwd_ret)) as rank_ic
    from joined
    group by date
    having count(*) >= 20

    return daily_ic
}

// 计算IC统计量
daily_ic = calculateDailyIC(factor_data, return_data)
select
    avg(rank_ic) as ic_mean,
    std(rank_ic) as ic_std,
    avg(rank_ic) / std(rank_ic) as icir,
    sum(iif(rank_ic > 0, 1, 0)) * 1.0 / count(*) as ic_pos_ratio,
    avg(rank_ic) / std(rank_ic) * sqrt(count(*)) as t_stat
from daily_ic


// 分层回测：按因子值分成5组
def quantileReturns(factorTable, returnTable, nQuantiles=5){
    joined = select
        f.date as date,
        f.symbol as symbol,
        f.factor_value as factor,
        r.fwd_return_20d as fwd_ret
    from factorTable as f
    left join returnTable as r
    on f.date = r.date and f.symbol = r.symbol

    // 计算因子分位数
    update joined set quantile = rank(factor) * nQuantiles \ count(*) + 1
        context by date

    // 各组平均收益
    quantile_rets = select
        date,
        quantile,
        avg(fwd_ret) as avg_return
    from joined
    group by date, quantile

    return quantile_rets
}
```

---

### 五、因子库应用最佳实践

| 场景 | 推荐方法 | 说明 |
|------|----------|------|
| **初步因子探索** | 使用 `ta` 模块 | 快速构建MACD、RSI、布林带等经典技术因子 |
| **专业因子研究** | 使用 `gtja191Alpha` 或 `wq101alpha` | 系统化因子库，有严谨的数学公式支撑 |
| **自定义因子** | 直接编写SQL | 灵活组合`mavg`、`mstd`、`mrank`等窗口函数 |
| **因子回测** | 联合Python生态 | DolphinDB计算因子 → Python做IC分析和回测可视化 |

```sql
// 混合使用内置因子库和自定义因子
use ta
use gtja191Alpha

select
    symbol,
    date,
    // 内置技术因子
    ta::rsi(close, 14) as rsi_14,
    ta::macd(close, 12, 26, 9) as macd,
    // 国泰君安因子
    gtja191Alpha::alpha001(open, high, low, close, volume, amount, vwap, cap, returns) as gtja_001,
    // 自定义因子
    (close - mavg(close, 60)) / mstd(close, 60) as zscore_60,
    returns(move(close, 21), 230) as momentum_12m1
from daily_data
context by symbol
```

> **核心优势**：在DolphinDB中，因子计算可以直接在数据库层面完成，避免了"从数据库取数 → Python计算 → 写回数据库"的数据搬运开销。对于全市场4000+股票、10年日频数据的因子计算，DolphinDB通常在秒级完成，而传统Python方案可能需要数十分钟。
