## 模拟撮合引擎

### 4.1 撮合引擎概述

模拟撮合引擎（Simulated Matching Engine）是回测系统中最关键的组件之一。它决定了订单如何成交、以什么价格成交、在什么时间成交，直接影响回测结果与真实交易的吻合程度。

在DolphinDB回测引擎中，撮合引擎负责接收策略发出的订单指令，在下一个时间周期到来时，根据当时的行情数据判断订单的成交情况。

> **撮合精度的意义**：一个过于乐观的撮合模型会让回测收益率虚高30%以上，导致策略在实盘中表现远逊于回测——这是"回测陷阱"的主要原因之一。

### 4.2 订单类型

DolphinDB回测引擎支持多种订单类型，每种类型有不同的撮合规则：

#### 4.2.1 市价单（Market Order）

市价单以当前市场价格立即成交，不指定具体价格：

```
// 市价买入
context.buy(0, 1000)  // 价格参数传0表示市价

// 市价卖出
context.sell(0, 500)  // 平仓
```

**撮合规则**：
- `nextBar`模式：以下一根Bar的开盘价成交
- `thisBar`模式：以当前Bar的收盘价成交
- 市价单通常能够全部成交（除非市场无对手盘）

#### 4.2.2 限价单（Limit Order）

限价单指定最高买入价或最低卖出价，只有在市场价格达到或优于指定价格时才成交：

```
// 限价买入：最高买价 10.50
context.buy(10.50, 1000)

// 限价卖出：最低卖价 12.00
context.sell(12.00, 500)
```

**撮合规则**：
- **买单**：当前Bar的最低价 ≤ 限价即触发成交，成交价取限价与最高价中的较小值
- **卖单**：当前Bar的最高价 ≥ 限价即触发成交，成交价取限价与最低价中的较大值
- 如果当前Bar价格未触及限价，订单保持挂单状态

```
// 限价单撮合逻辑示例
def matchLimitOrder(order, bar) {
    if (order.side == "BUY") {
        if (bar.Low <= order.price) {
            fillPrice = min(bar.High, order.price)
            return (True, fillPrice)  // 成交
        }
    }
    else if (order.side == "SELL") {
        if (bar.High >= order.price) {
            fillPrice = max(bar.Low, order.price)
            return (True, fillPrice)  // 成交
        }
    }
    return (False, NULL)  // 未成交，继续挂单
}
```

#### 4.2.3 止损单（Stop Order）

止损单是一种条件单，当价格突破某个阈值时激活为市价单：

- **止损买单**：价格涨到触发价以上时激活（通常用于追涨或空头平仓）
- **止损卖单**：价格跌到触发价以下时激活（通常用于止损保护）

```
// 止损卖单：当价格跌破9.50时触发卖出
context.stopSell(9.50, 1000)

// 止损买单：当价格涨破11.00时触发买入
context.stopBuy(11.00, 1000)
```

### 4.3 市场冲击模拟

在真实交易中，大额订单会对市场价格产生冲击（Market Impact），导致实际成交价偏离理论价格。DolphinDB回测引擎支持市场冲击建模。

#### 4.3.1 线性冲击模型

假设冲击成本与订单量成正比：

$$\text{Slippage} = k \times \frac{\text{OrderQty}}{\text{AvgDailyVolume}}$$

其中 $k$ 是冲击系数，通常每股约0.1-1.0个基点。

```
// 市场冲击参数配置
config["impactModel"] = "linear"
config["impactCoeff"] = 0.5    // 冲击系数
```

#### 4.3.2 平方根冲击模型

更符合实际的市场冲击模型是平方根模型：

$$\text{Slippage} = k \times \sqrt{\frac{\text{OrderQty}}{\text{AvgDailyVolume}}} \times \sigma$$

其中$\sigma$是日波动率。这个模型反映了"小订单也有一定冲击，大订单冲击边际递减"的现象。

### 4.4 延迟模拟

交易延迟（Latency）从信号产生到订单执行之间的时间差。包括：

| 延迟类型 | 典型值 | 说明 |
|----------|--------|------|
| 网络延迟 | 1-50ms | 机房到交易所的网络传输 |
| 系统延迟 | 1-10ms | 系统内部处理时间 |
| 撮合延迟 | <1ms | 交易所内部撮合时间 |

在回测中的延迟模拟：

```
// 设置延迟（以数据周期为单位）
config["delay"] = 1  // 延迟1根Bar执行

// 这意味着在Bar T产生的信号，将在Bar T+1才执行订单
```

> **延迟设置对结果的影响**：将延迟从0改为1根Bar，可能让高频策略的收益率从15%骤降至-5%。延迟模拟是真实回测的关键环节。

### 4.5 部分成交（Partial Fill）处理

真实市场中，订单可能由于以下原因部分成交：

- 限价单价格触及但对手盘不足
- 市场流动性不足
- 价格穿越太快，成交量不够

#### 4.5.1 流动性限制

```
// 设置单Bar最大成交量限制
config["maxFillRatio"] = 0.1  // 单Bar最多成交日均量的10%
config["maxPositionPct"] = 0.01  // 单一持仓不超过总股本的1%
```

#### 4.5.2 部分成交的处理逻辑

```
def fillOrder(order, bar) {
    maxFillVol = bar.Volume * config["maxFillRatio"]
    actualVol = min(order.remainingQty, maxFillVol)
    order.remainingQty -= actualVol

    if (order.remainingQty == 0) {
        order.status = "FILLED"       // 完全成交
    }
    else {
        order.status = "PARTIALLY_FILLED"  // 部分成交
    }
    return (actualVol, order)
}
```

### 4.6 撮合引擎配置汇总

完整的撮合相关参数设置：

```
// 撮合引擎核心配置
config["fillMode"] = "nextBar"           // 撮合周期
config["orderType"] = "market"           // 默认订单类型
config["slippage"] = 0.0002              // 滑点0.02%
config["slippageModel"] = "fixed"        // 滑点模型
config["impactModel"] = "linear"         // 市场冲击模型
config["impactCoeff"] = 0.5              // 冲击系数
config["delay"] = 1                      // 执行延迟
config["maxFillRatio"] = 0.1             // 最大成交比例
config["allowPartialFill"] = true        // 是否允许部分成交
```

### 4.7 真实模拟注意事项

#### 4.7.1 涨跌停限制

A股市场有±10%的涨跌停限制（科创板和创业板为±20%）。回测时需要考虑涨跌停板可能导致的无法成交：

```
// 检查涨跌停
def checkPriceLimit(bar, prevClose) {
    upperLimit = prevClose * 1.10
    lowerLimit = prevClose * 0.90
    if (bar.close >= upperLimit) return "hit_upper"  // 涨停无法买入
    if (bar.close <= lowerLimit) return "hit_lower"  // 跌停无法卖出
    return "normal"
}
```

#### 4.7.2 T+1制度

A股实行T+1交易制度（当天买入的股票次日才能卖出），回测时需要遵守此规则：

```
// 买入时记录持仓天数
portfolio.holdDays[order.symbol] = 0

// onBar中更新持仓天数
for (symbol in portfolio.holdings) {
    portfolio.holdDays[symbol] += 1
}

// 卖出检查
if (portfolio.holdDays[symbol] < 1) {
    // 当日买入已成交大量筹码，次日才能卖出
    rejectSell("T+1限制")
}
```

#### 4.7.3 最小交易单位

A股以手（100股）为最小交易单位，买卖都必须是100股的整数倍：

```
// 交易单位处理
lotSize = 100
adjustedQty = (orderQty / lotSize) \ lotSize * lotSize  // 整数除法后取整
if (adjustedQty < lotSize) adjustedQty = 0               // 不足一手不交易
```

### 4.8 回测与实盘的差异来源

即使最精密的回测引擎，也无法完全模拟真实市场的复杂性。需要理解以下关键差异：

| 差异来源 | 回测中 | 实盘中 | 应对方法 |
|----------|--------|--------|----------|
| 流动性 | 假设充足 | 可能不足 | 设置流动性限制 |
| 交易成本 | 简化模型 | 含隐形成本 | 保守设置滑点 |
| 信号延迟 | 即时或无延迟 | 真实延迟 | 设置合理延迟 |
| 市场冲击 | 忽略或简化 | 真实存在 | 启用冲击模型 |
| 制度限制 | 可能忽略 | T+1等 | 代码中模拟制度 |
| 心理因素 | 无影响 | 大幅影响 | — |

> **核心原则**：宁可让回测结果差一点（保守估计），也不要让回测结果虚高。保守的回测结果在实盘中往往更可靠。
