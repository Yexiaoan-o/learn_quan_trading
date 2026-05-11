## 回测配置与准备

### 2.1 配置概述

在DolphinDB中运行回测之前，需要进行一系列的准备工作：数据准备、策略定义和回测环境配置。这些步骤是确保回测结果准确可靠的基础。

DolphinDB回测引擎使用一个字典（Dictionary）来统一管理所有配置参数，包括时间范围、资金参数、费率设置等。策略逻辑则以函数形式定义，注册到回测引擎中。

### 2.2 数据准备

#### 2.2.1 价格数据

回测需要的基础数据主要包括：

| 数据类型 | 字段 | 说明 |
|----------|------|------|
| 日线数据 | TradeDate, Symbol, Open, High, Low, Close, Volume | 日频回测必需 |
| 分钟数据 | 同理，粒度到分钟 | 分钟频回测必需 |
| 复权因子 | AdjFactor | 计算后复权价格 |

确保数据满足以下条件：

- **完整性**：所有交易日的数据不能缺失
- **准确性**：价格不应出现极端异常值
- **一致性**：所有标的的数据格式和时间范围一致
- **复权处理**：使用后复权价格避免分红拆股影响

数据建议存储在DolphinDB分布式数据库中：

```
dfs://market_data/
├── daily_bar/          -- 日线行情
├── minute_bar/         -- 分钟行情
└── adj_factor/         -- 复权因子
```

#### 2.2.2 交易时间配置

回测引擎需要知道有效的交易时间段，以正确模拟交易行为：

```python
// 交易时间配置
tradeTime = [
    ["09:30:00.000", "11:30:00.000"],  // 上午连续竞价
    ["13:00:00.000", "15:00:00.000"]   // 下午连续竞价
]
```

### 2.3 策略定义函数

策略逻辑通过定义特定的事件处理函数来实现。DolphinDB回测引擎支持两种主要的行情事件：

#### 2.3.1 onBar处理函数

`onBar` 函数在每个Bar结束时触发，适用于日频或分钟频的策略：

```
def strategy(context){
    // context 包含当前行情和历史数据
    bar = context.bar           // 当前Bar数据
    portfolio = context.portfolio  // 当前持仓信息

    // 策略逻辑示例：双均线交叉
    close = context.getPrices("close", 60)  // 获取最近60根Bar的收盘价
    ma_fast = avg(close.tail(20))           // 快线MA20
    ma_slow = avg(close.tail(60))           // 慢线MA60

    if (ma_fast > ma_slow) {
        // 金叉，买入信号
        if (portfolio.position == 0) {
            context.buy(bar.close, 100)     // 买入100股
        }
    }
    else {
        // 死叉，卖出信号
        if (portfolio.position > 0) {
            context.sell(bar.close, portfolio.position)  // 平仓
        }
    }
}
```

> **context对象**：是回测引擎传递给策略的上下文，提供了访问行情、持仓、下订单等所有必需功能。

#### 2.3.2 onTick处理函数

`onTick` 函数在每一笔行情更新时触发，适用于高频策略：

```
def tickStrategy(context){
    tick = context.tick
    // 基于逐笔数据的策略逻辑
    if (tick.price > context.bidPrice) {
        context.sell(tick.price, 100)
    }
}
```

### 2.4 回测配置参数

完整的配置通过一个键值对字典来设置：

```
// 创建配置字典
config = dict(STRING, ANY)

// ---------- 基础参数 ----------
config["startTime"] = 2020.01.01           // 回测开始日期
config["endTime"] = 2023.12.31             // 回测结束日期
config["freq"] = "D"                       // 数据频率: D=日线, 1m=分钟, 1s=秒
config["symbols"] = ["000001.SZ","600000.SH"]  // 回测标的列表

// ---------- 资金参数 ----------
config["initCapital"] = 1000000.0          // 初始资金（元）
config["stake"] = 100                      // 每笔交易股数

// ---------- 费率参数 ----------
config["commission"] = 0.0003              // 手续费率（万分之三）
config["minCommission"] = 5.0              // 最低手续费（元）
config["stampTax"] = 0.001                 // 印花税（千分之一）——卖出收取
config["slippage"] = 0.0001                // 滑点比例（万分之一）
config["slippageModel"] = "fixed"          // 滑点模型: fixed固定, proportional比例, random随机

// ---------- 撮合参数 ----------
config["fillMode"] = "nextBar"             // 撮合方式: nextBar下一根Bar成交, thisBar当前Bar成交
config["orderType"] = "market"             // 默认订单类型: market市价, limit限价

// ---------- 输出参数 ----------
config["outputTrades"] = true              // 是否输出交易明细
config["outputEquity"] = true              // 是否输出净值序列
```

### 2.5 常见配置参数详解

#### 2.5.1 滑点模型

滑点（Slippage）模拟真实交易中无法按理想价格成交的现象：

| 模型类型 | 说明 | 示例（买入方向） |
|----------|------|-----------------|
| fixed | 固定滑点比例 | 成交价 = 理论价 × (1 + slippage) |
| sqrt | 开方模型 | 成交价 = 理论价 × (1 + slippage × √(订单量/日均量)) |
| custom | 自定义滑点函数 | 用户自行定义滑点计算逻辑 |

#### 2.5.2 撮合方式对比

| 撮合方式 | 工作机制 | 是否使用未来信息 | 适用场景 |
|----------|----------|:---:|----------|
| nextBar | 在下根Bar以开盘价成交 | 否 | 保守回测，贴近实际 |
| thisBar | 在当前Bar以收盘价成交 | 部分 | 乐观回测，理想情况 |
| VWAP | 按成交量加权均价成交 | 可能 | 大资金回测 |

> **风险提示**：`thisBar`撮合方式可能引入"未来函数"偏差，导致回测结果虚高。建议使用`nextBar`进行保守评估。

#### 2.5.3 手续费与税费设置

A股市场实际交易成本包括：

```
买入成本 = 成交金额 × 佣金费率（最低5元）
卖出成本 = 成交金额 × 佣金费率（最低5元） + 成交金额 × 印花税（0.1%）
```

### 2.6 策略验证清单

在正式运行回测之前，对照以下清单确保配置无误：

- [ ] 数据范围覆盖回测区间加上足够的"预热期"（如MA60需要60天）
- [ ] 所有标的数据格式一致，无日期跳空
- [ ] 价格已做后复权处理
- [ ] 佣金费率和印花税与实际交易一致
- [ ] 滑点设置合理（建议不低于万分之一）
- [ ] 撮合方式选择nextBar避免使用未来信息
- [ ] 初始资金设置合理，考虑一手资金门槛
- [ ] 策略代码中无语法错误和逻辑漏洞

### 2.7 配置示例：完整策略设定

以下是一个完整的日频策略配置示例：

```
// 策略定义
def dualMATrend(context){
    close = context.getPrices("close", 120)
    ma20 = avg(close.tail(20))
    ma60 = avg(close.tail(60))
    pos = context.portfolio.position
    price = context.bar.close

    if (ma20 > ma60 && pos <= 0) {
        if (pos < 0) context.buy(price, abs(pos))  // 先平空
        context.buy(price, 100)                     // 开多
    }
    else if (ma20 < ma60 && pos >= 0) {
        if (pos > 0) context.sell(price, pos)       // 平多
        context.shortSell(price, 100)               // 开空
    }
}

// 配置参数
config = dict(STRING, ANY)
config["startTime"] = 2020.01.01
config["endTime"] = 2023.12.31
config["freq"] = "D"
config["symbols"] = ("000001.SZ", "600000.SH")
config["initCapital"] = 1000000.0
config["commission"] = 0.0003
config["minCommission"] = 5.0
config["stampTax"] = 0.001
config["slippage"] = 0.0001
config["fillMode"] = "nextBar"
config["strategy"] = dualMATrend
```
