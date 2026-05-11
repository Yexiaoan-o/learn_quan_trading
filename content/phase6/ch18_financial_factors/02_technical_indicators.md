## 常用技术指标计算

### 2.1 技术指标概述

技术指标（Technical Indicators）是量化交易中最基础的工具。它们通过对价格和成交量的数学变换，提取市场趋势、动量、波动等信息，为交易决策提供信号依据。

DolphinDB的TA模块内置了丰富的技术指标计算函数，本章详细介绍最常用的几类指标及其DolphinDB实现。

### 2.2 MACD指标（指数平滑异同移动平均线）

MACD是Gerald Appel于1970年代提出，至今仍是最流行的趋势跟踪指标之一。它由三个部分构成：

- **DIF（快线）**：快线EMA(12) - 慢线EMA(26)
- **DEA（慢线/信号线）**：DIF的EMA(9)
- **MACD柱（Histogram）**：DIF - DEA，反映多空力量变化

```
use ta

// MACD完整计算
macd_result = ta::macd(close, 12, 26, 9)

// 提取三个分量
dif = macd_result[0]     // DIF快线
dea = macd_result[1]     // DEA信号线
hist = macd_result[2]    // MACD柱状图 = 2*(DIF-DEA)（常用2倍缩放）

// 信号判断
signal_buy = cross(dif, dea) and dif > 0       // 零轴上金叉 → 强势买入
signal_sell = cross(dea, dif) and dif < 0      // 零轴下死叉 → 强势卖出
```

> **MACD经典用法**：1) 金叉买入、死叉卖出；2) 零轴上方偏多，下方偏空；3) 背离信号——价格创新高而MACD未创新高为顶背离；价格创新低而MACD未创新低为底背离。

### 2.3 RSI指标（相对强弱指标）

RSI由J. Welles Wilder提出，衡量价格变动的内在强度，取值范围0-100：

计算公式：

$$\text{RSI} = 100 - \frac{100}{1 + \frac{\text{avg\_gain}}{\text{avg\_loss}}}$$

```
use ta

// RSI计算
rsi14 = ta::rsi(close, 14)

// 超买超卖信号
overbought = rsi14 > 70   // RSI>70 超买区域，可能回调
oversold = rsi14 < 30     // RSI<30 超卖区域，可能反弹

// RSI背离检测
// price_making_lower_low and rsi_making_higher_low = 底背离 → 看涨

// 多周期RSI
rsi6 = ta::rsi(close, 6)    // 短周期RSI（灵敏度高）
rsi14 = ta::rsi(close, 14)  // 中周期RSI（标准参数）
rsi24 = ta::rsi(close, 24)  // 长周期RSI（过滤噪音）
```

RSI值解读：

| RSI范围 | 状态 | 交易含义 |
|---------|------|----------|
| 0-20 | 极度超卖 | 强烈反弹预期 |
| 20-30 | 超卖 | 反弹概率大 |
| 30-70 | 正常区间 | 观望或顺势 |
| 70-80 | 超买 | 回调概率大 |
| 80-100 | 极度超买 | 强烈回调预期 |

### 2.4 KDJ指标（随机指标）

KDJ指标由George Lane提出，是随机指标（Stochastic Oscillator）的改良版：

```
use ta

// KDJ计算
kdj_result = ta::kdj(high, low, close, 9, 3, 3)
k = kdj_result[0]  // K值（快速随机值）
d = kdj_result[1]  // D值（K值的移动平均）
j = kdj_result[2]  // J值（3*K - 2*D，最灵敏）

// KDJ手动实现（理解计算原理）
def kdj_manual(high, low, close, n=9, m1=3, m2=3) {
    lowest_low = min(low, n)            // n日最低价
    highest_high = max(high, n)         // n日最高价
    rsv = (close - lowest_low) / (highest_high - lowest_low) * 100  // 未成熟随机值RSV
    k = ema(rsv, m1, 2)                // K = RSV的EMA
    d = ema(k, m2, 2)                  // D = K的EMA
    j = 3 * k - 2 * d                  // J = 3K - 2D
    return (k, d, j)
}
```

> **KDJ信号规则**：K上穿D为金叉（买入），下穿为死叉（卖出）；J>100为超买，J<0为超卖；J线的极端值往往预示着价格转折点。KDJ在震荡市中效果最好，趋势市场中容易过早发出反向信号。

### 2.5 ATR指标（平均真实波幅）

ATR也是Wilder的发明，用于衡量市场波动性而非方向：

```
use ta

// ATR计算
atr14 = ta::atr(high, low, close, 14)

// ATR止损设置
multiplier = 2.0
stop_long = close - multiplier * atr14   // 多头止损价
stop_short = close + multiplier * atr14  // 空头止损价

// 真实波幅（TR）的原始计算
tr1 = high - low                              // 当日波幅
tr2 = abs(high - close[move, 1])              // 当日最高价与昨日收盘价的差距
tr3 = abs(low - close[move, 1])               // 当日最低价与昨日收盘价的差距
true_range = max(tr1, max(tr2, tr3))          // 三者取最大
atr_manual = ema(true_range, 14, 2)           // TR的EMA即为ATR
```

ATR的实际应用场景：
- **止损设定**：止损距离 = N × ATR（海龟交易法则的核心）
- **仓位管理**：波动大时降低仓位，波动小时增加仓位
- **市场筛选**：过滤波动过低的横盘市场

### 2.6 OBV指标（能量潮）

OBV（On-Balance Volume）由Joseph Granville提出，用成交量的累积变化来验证价格趋势：

```
use ta

// OBV计算
obv = ta::obv(close, volume)

// 手动实现OBV
def obv_manual(close, volume) {
    n = size(close)
    obv_arr = array(DOUBLE, n, 0)
    for (i in 1:(n-1)) {
        if (close[i] > close[i-1])
            obv_arr[i] = obv_arr[i-1] + volume[i]
        else if (close[i] < close[i-1])
            obv_arr[i] = obv_arr[i-1] - volume[i]
        else
            obv_arr[i] = obv_arr[i-1]
    }
    return obv_arr
}
```

> **OBV验证原则**：价格创新高时OBV也应创新高（量价配合），否则是顶背离信号；价格创新低时OBV也应创新低，否则是底背离信号。

### 2.7 CCI指标（商品通道指数）

CCI由Donald Lambert提出，用于识别价格的周期性波动，适合用于超买超卖判断：

```
use ta

// CCI计算
cci20 = ta::cci(high, low, close, 20)

// 典型价格 TP = (High + Low + Close) / 3
// CCI = (TP - MA(TP, N)) / (0.015 * meanDeviation(TP, N))

// 信号规则
cci_overbought = cci20 > 100   // CCI > +100 超买
cci_oversold = cci20 < -100    // CCI < -100 超卖
cci_extreme_buy = cci20 < -200  // 极度超卖，强反弹信号
```

### 2.8 布林带（Bollinger Bands）

布林带由John Bollinger提出，集成了趋势跟踪和波动率测量：

```
use ta

// 布林带计算
bb = ta::bollingerBands(close, 20, 2)
upper_band = bb[0]   // 上轨 = MA20 + 2*σ
middle_band = bb[1]  // 中轨 = MA20
lower_band = bb[2]   // 下轨 = MA20 - 2*σ

// 带宽（衡量波动率）
band_width = (upper_band - lower_band) / middle_band * 100

// %B（价格在带内的相对位置）
pct_b = (close - lower_band) / (upper_band - lower_band)
```

> **布林带使用**：价格触碰上轨为超买信号，触碰下轨为超卖信号；带宽收窄（Squeeze）预示大幅波动即将来临；价格沿某一轨道运行代表强劲趋势。

### 2.9 综合指标面板

在实际策略开发中，通常一次性计算多个指标形成"指标面板"：

```
use ta

// 批量计算技术指标
indicatorPanel = select
    TradeDate, Symbol,
    close, volume,
    ta::macd(close, 12, 26, 9)[0] as dif,
    ta::macd(close, 12, 26, 9)[1] as dea,
    ta::macd(close, 12, 26, 9)[2] as macd_hist,
    ta::rsi(close, 14) as rsi14,
    ta::atr(high, low, close, 14) as atr14,
    ta::bollingerBands(close, 20, 2)[0] as bb_upper,
    ta::bollingerBands(close, 20, 2)[2] as bb_lower,
    ta::cci(high, low, close, 20) as cci20,
    ta::obv(close, volume) as obv
from dailyTable
context by Symbol
```

> **注意事项**：因子计算时注意使用 `context by Symbol` 确保每个股票独立计算，避免跨股票的数据混淆。

### 2.10 指标使用注意事项

1. **参数敏感**：不同参数会带来截然不同的信号，需通过参数优化或经验确定
2. **滞后性**：所有指标都是基于历史数据，本质上滞后于价格，不要指望完美预测
3. **市场适应性**：同一参数在牛熊市中表现迥异，需要分市场环境评估
4. **多重验证**：永远不要依赖单一指标做决策，至少结合2-3个指标相互验证
5. **防止过拟合**：不要在回测数据上反复调参直到完美，必须在样本外数据上验证
