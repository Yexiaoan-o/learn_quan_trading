## DolphinDB窗口函数详解

窗口函数（Window Functions）是时序数据分析的核心工具。DolphinDB提供了丰富的移动窗口和滚动窗口函数，可在SQL中直接调用，性能远超逐行循环的实现方式。

---

### 一、移动窗口函数速查

DolphinDB的移动窗口函数统一以`m`为前缀（Moving），接受一个向量和一个窗口大小参数：

| 函数 | 功能 | 示例 |
|------|------|------|
| **mavg(X, window)** | 移动平均 | `mavg(close, 20)` |
| **msum(X, window)** | 移动求和 | `msum(volume, 5)` |
| **mstd(X, window)** | 移动标准差 | `mstd(returns, 60)` |
| **mmin(X, window)** | 移动最小值 | `mmin(low, 20)` |
| **mmax(X, window)** | 移动最大值 | `mmax(high, 20)` |
| **mbeta(Y, X, window)** | 移动Beta系数 | `mbeta(ret, mkt_ret, 252)` |
| **mcorr(Y, X, window)** | 移动相关系数 | `mcorr(stock_a, stock_b, 60)` |
| **mrank(X, ascending, window)** | 移动排名 | `mrank(close, true, 60)` |
| **mprod(X, window)** | 移动乘积 | `mprod(1+ret, 252)`累乘收益 |
| **mcount(X, window)** | 移动非空计数 | `mcount(close, 20)` |
| **mmed(X, window)** | 移动中位数 | `mmed(close, 20)` |

---

### 二、移动窗口函数实战

#### 2.1 基本移动均线系统

```sql
// 多周期移动均线计算
select
    symbol,
    date,
    close,
    mavg(close, 5) as ma_5,          // 5日均线
    mavg(close, 10) as ma_10,        // 10日均线
    mavg(close, 20) as ma_20,        // 20日均线
    mavg(close, 60) as ma_60,        // 60日均线
    mavg(close, 120) as ma_120,      // 120日均线（半年线）
    mavg(close, 250) as ma_250       // 250日均线（年线）
from daily_data
where symbol = '000001.SZ'
order by date
```

#### 2.2 波动率与风险管理

```sql
// 滚动波动率和相关系数
select
    symbol,
    date,
    close,
    // 20日历史波动率（对数收益率）
    mstd(log(close / prev(close)), 20) * sqrt(252) as vol_20d_annual,
    // 60日最大回撤
    close / mmax(close, 60) - 1 as drawdown_60d,
    // 与市场指数的滚动Beta
    mbeta(log(close / prev(close)), log(market_close / prev(market_close)), 252) as beta_252d,
    // 与同行业股票的滚动相关系数
    mcorr(log(close / prev(close)), log(peer_close / prev(peer_close)), 60) as corr_60d
from daily_data
where symbol = '000001.SZ'
```

#### 2.3 量价关系分析

```sql
// 基于窗口函数的量价指标
select
    symbol,
    date,
    close,
    volume,
    // 5日平均成交量
    mavg(volume, 5) as avg_vol_5,
    // 当日成交量相对于20日均量的比值
    volume / mavg(volume, 20) as volume_ratio,
    // 20日价格排名（1=最低价位置, 20=最高价位置）
    mrank(close, true, 20) as price_rank_20,
    // 5日最高价和最低价范围
    (mmax(high, 5) - mmin(low, 5)) / close as range_5d_pct,
    // OBV的5日变化
    msum(sign(close - prev(close)) * volume, 5) as obv_5d
from daily_data
where symbol = '000001.SZ'
```

---

### 三、移动窗口 vs 扩展窗口

DolphinDB支持两种窗口模式：

| 窗口类型 | 行为 | 函数示例 | 使用场景 |
|----------|------|----------|----------|
| **移动窗口** | 固定大小窗口向后滑动 | `mavg(close, 20)` | 技术指标（均线等） |
| **扩展窗口** | 窗口从起点不断扩大到当前行 | `cumavg(close)` | 累计统计 |

```sql
// 对比移动窗口和扩展窗口
select
    symbol,
    date,
    close,
    // === 移动窗口：固定窗口大小 ===
    mavg(close, 20) as moving_avg_20,       // 始终是最近20条数据的均值
    mstd(close, 20) as moving_std_20,

    // === 扩展窗口：从起始位置累计 ===
    cumavg(close) as cumulative_avg,         // 从数据起点到当前位置的累计均值
    cumstd(close) as cumulative_std,         // 累计标准差
    cummax(close) as all_time_high,          // 历史最高价
    cummin(close) as all_time_low            // 历史最低价
from daily_data
where symbol = '000001.SZ'
context by symbol
order by date
```

---

### 四、滚动窗口的高级用法

#### 4.1 自定义窗口函数

```sql
// 使用 moving 函数自定义窗口计算
// moving(func, X, window)：对每个窗口应用自定义函数

// 例1：计算窗口内的收益偏度
select
    symbol,
    date,
    close,
    moving(def(x): skew(x), log(close / prev(close)), 60) as return_skew_60d
from daily_data
context by symbol

// 例2：计算窗口内正收益比例
select
    symbol,
    date,
    returns,
    moving(def(x): sum(x > 0) * 1.0 / size(x), returns, 20) as positive_ratio
from daily_data
context by symbol
```

#### 4.2 延迟窗口（Lag Window）

```sql
// move函数：将向量向后平移k个位置（用于因子研究中的前视偏差防止）
select
    symbol,
    date,
    close,
    move(close, 1) as close_lag1,                        // T-1日收盘价
    move(close, 5) as close_lag5,                        // T-5日收盘价
    (close - move(close, 1)) / move(close, 1) as ret,   // (T日 - T-1日) / T-1日
    // 动量计算：使用move避免前视偏差
    (close - move(close, 20)) / move(close, 20) as momentum_20d
from daily_data
context by symbol
order by date
```

---

### 五、窗口函数的性能考量

```sql
// 一次查询中高效计算多个窗口统计量
// 基础版本：多次扫描数据（较差）
result = select
    mavg(close, 5) as ma_5,
    mavg(close, 20) as ma_20,
    mavg(close, 60) as ma_60
from data

// 优化版本：尽量在一次扫描中完成所有计算
select
    symbol,
    date,
    close,
    volume,
    // 批量窗口计算（DolphinDB内部优化为一次扫描）
    mavg(close, 5) as ma_5,
    mavg(close, 10) as ma_10,
    mavg(close, 20) as ma_20,
    mavg(close, 60) as ma_60,
    mstd(close, 20) as std_20,
    mbeta(close, market_close, 60) as beta_60,
    mcorr(close, volume, 20) as corr_pv_20
from daily_data
context by symbol
```

| 优化技巧 | 说明 |
|----------|------|
| **合并查询** | 多个窗口函数放在同一条SELECT中，DolphinDB内部会优化为一次数据扫描 |
| **合理窗口大小** | 窗口过大（>1000）会增加内存使用，仅在有明确需求时使用大窗口 |
| **分区计算** | 按symbol分区后，每个分区的窗口计算独立进行，可并行加速 |
| **避免嵌套** | `mavg(mavg(close, 5), 10)`需要计算内层和外层两次，尽量拆分为两步 |

> **核心思想**：DolphinDB的窗口函数通过向量化引擎实现，一个`mavg(close, 20)`的执行时间与窗口大小和序列长度几乎无关（算法复杂度O(n)）。这是传统Python逐行循环（O(n*window)）所无法比拟的。在实际应用中，应该充分利用窗口函数，用一行SQL替代几十行的Python循环代码。
