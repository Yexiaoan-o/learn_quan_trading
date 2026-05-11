## 执行回测与结果分析

### 3.1 启动回测

在DolphinDB中，配置好策略和参数后，调用回测引擎的API即可启动回测：

```
// 定义并初始化回测引擎
engine = backtest::createEquityBacktestEngine(config)

// 设置数据源
engine.setData(
    select * from loadTable("dfs://market_data", "daily_bar")
    where Symbol in config["symbols"]
    and TradeDate between config["startTime"]:config["endTime"]
)

// 运行回测
result = engine.run()

// 回测运行后，result包含了完整的回测结果对象
```

回测执行时间取决于：
- 标的数量（多则耗时更长）
- 数据频率（Tick>分钟>日线）
- 策略复杂度（因子计算越多越慢）
- 时间跨度（越长越慢）

DolphinDB得益于C++内核和并行计算能力，对于大多数日频策略，上千只标的十年数据的回测通常在几分钟内完成。

### 3.2 回测输出结果

回测完成后，`result` 对象包含以下核心输出：

#### 3.2.1 净值曲线（Equity Curve）

净值曲线是回测分析中最重要的输出，记录每个交易日的账户总资产变化：

```
// 获取净值序列
equity = result.equity

// 格式: 每天一条记录
// Date         Equity
// 2020.01.02   1,000,500.00
// 2020.01.03   1,001,200.00
// 2020.01.06   998,000.00
// ...
```

#### 3.2.2 交易列表（Trade List）

记录每一笔成交的交易明细：

| 字段 | 说明 | 示例 |
|------|------|------|
| TradeTime | 成交时间 | 2020.03.15 09:35:00 |
| Symbol | 标的代码 | 000001.SZ |
| Side | 买卖方向 | BUY / SELL |
| Price | 成交价格 | 12.50 |
| Quantity | 成交数量 | 1000 |
| Commission | 手续费 | 3.75 |
| PnL | 逐笔盈亏 | 500.00 |

#### 3.2.3 每日盈亏（Daily P&L）

```
// 获取每日盈亏
dailyPnl = result.dailyPnl

// Date         DailyReturn  CumulativeReturn
// 2020.01.02   0.0050       0.0050
// 2020.01.03   -0.0020      0.0030
// 2020.01.06   0.0080       0.0110
```

### 3.3 性能报告

DolphinDB回测引擎可以自动生成全面的性能分析报告。以下是关键指标的计算方法：

#### 3.3.1 总收益率

总收益率衡量整个回测期间的累计收益：

$$\text{Total Return} = \frac{\text{Final Equity} - \text{Initial Capital}}{\text{Initial Capital}} \times 100\%$$

```
// 计算总收益率
totalReturn = (result.equity.last().Equity - config["initCapital"]) / config["initCapital"] * 100
```

#### 3.3.2 年化收益率

将总收益转换为年度等值收益率：

$$\text{Annual Return} = \left(\frac{\text{Final Equity}}{\text{Initial Capital}}\right)^{\frac{252}{N}} - 1$$

其中N为交易天数。

```
nDays = size(result.equity)
annualReturn = (pow(result.equity.last().Equity / config["initCapital"], 252.0 / nDays) - 1) * 100
```

#### 3.3.3 夏普比率（Sharpe Ratio）

夏普比率衡量每单位风险所获得的超额回报：

$$\text{Sharpe Ratio} = \frac{\text{mean(DailyReturn)} - r_f}{\text{std(DailyReturn)}} \times \sqrt{252}$$

中国市场中通常取无风险利率 $r_f$ 为年化2%-3%。

```
// 计算夏普比率
dailyReturns = result.dailyPnl.DailyReturn
rf = 0.03 / 252  // 无风险日利率
sharpe = (avg(dailyReturns) - rf) / std(dailyReturns) * sqrt(252)
```

基准评价标准：

| 夏普比率 | 评价等级 | 说明 |
|----------|----------|------|
| < 0 | 较差 | 收益低于无风险利率 |
| 0 - 0.5 | 一般 | 勉强跑赢无风险 |
| 0.5 - 1.0 | 良好 | 有明显超额收益 |
| 1.0 - 2.0 | 优秀 | 风险收益比合理 |
| > 2.0 | 卓越 | 极低风险高回报（警惕过拟合） |

#### 3.3.4 最大回撤（Max Drawdown）

最大回撤是净值曲线上从峰值到谷底的最大跌幅：

$$\text{Drawdown} = \frac{\text{Current Equity} - \text{Peak Equity}}{\text{Peak Equity}}$$

```
// 计算最大回撤
equityValues = result.equity.Equity
peak = equityValues[0]
maxDD = 0.0
for (v in equityValues) {
    if (v > peak) peak = v
    dd = (v - peak) / peak
    if (dd < maxDD) maxDD = dd
}
maxDrawdown = maxDD * 100  // 转为百分比
```

> **关键关联**：夏普比率和最大回撤共同使用才能全面评估策略。高夏普比率加极大回撤可能意味着策略在极端行情下有爆仓风险。

### 3.4 结果可视化

虽然DolphinDB本身可以绘制图表，但通常将回测结果导出到Python进行更灵活的可视化：

```
// 将结果导出为表
t = table(result.equity.Date as date, result.equity.Equity as equity)
// 可通过Python API读取，或保存为CSV
saveText(t, "/data/equity_curve.csv")
```

Python端的可视化代码：

```python
import matplotlib.pyplot as plt
import pandas as pd

# 读取回测结果
equity = pd.read_csv('equity_curve.csv')
equity['date'] = pd.to_datetime(equity['date'])
equity.set_index('date', inplace=True)

# 净值曲线
fig, axes = plt.subplots(2, 1, figsize=(12, 8))
equity['equity'].plot(ax=axes[0], title='净值曲线')
axes[0].set_ylabel('账户净值')

# 回撤曲线
cummax = equity['equity'].cummax()
drawdown = (equity['equity'] - cummax) / cummax * 100
drawdown.plot(ax=axes[1], title='回撤曲线', color='red', fill=True)
axes[1].set_ylabel('回撤(%)')

plt.tight_layout()
plt.show()
```

### 3.5 回测结果解读与调试

#### 3.5.1 关键问题排查

当回测结果与预期不符时，从以下角度排查：

| 问题现象 | 可能原因 | 检查方向 |
|----------|----------|----------|
| 收益过高 | 未来函数 | 检查撮合方式、数据使用 |
| 收益过低 | 手续费过高 | 检查佣金和滑点设置 |
| 交易过多 | 信号过于频繁 | 增加信号过滤条件 |
| 无交易 | 条件未满足 | 检查信号逻辑和数据 |
| 夏普极高(>3) | 过拟合 | 分样本外验证 |

#### 3.5.2 分年度分析

将回测结果按年份分组分析，检查策略在不同市场环境下的表现稳定性：

```
// 分年度统计
yearlyStats = select
    year(date) as year,
    sum(dailyReturn) as cumulativeReturn,
    avg(dailyReturn) * 252 as annualizedReturn,
    std(dailyReturn) * sqrt(252) as annualizedVol
from dailyReturns
group by year
order by year
```

如果策略在某一年大幅亏损而其他年份盈利，需要分析该年是否出现了策略失效的特殊市场环境。

### 3.6 回测报告输出模板

一份完整的回测报告应包含以下内容：

```
================== 回测绩效报告 ==================
回测区间:    2020.01.01 - 2023.12.31
初始资金:    1,000,000.00 元
最终净值:    1,450,000.00 元
----------------------------------------------
总收益率:    45.00%
年化收益率:  9.73%
夏普比率:    1.12
最大回撤:    -15.30%
年化波动率:  12.50%
----------------------------------------------
总交易次数:  156 次
胜率:        48.72%
盈亏比:      1.85
平均持仓天数: 12.3 天
----------------------------------------------
策略名称:    双均线趋势跟踪
标的数量:    50 只
数据频率:    日线
==================================================
```

> **经验之谈**：不要只看总收益率。年化收益率超过20%且夏普比率超过2的策略，很大概率存在过拟合或未来函数问题。真实市场中，年化10%-15%且夏普在0.8-1.5已经是非常优秀的策略。
