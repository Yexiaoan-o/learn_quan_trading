## 3.1 内置函数概述

DolphinDB 内置了超过 **2000** 个函数，覆盖数学统计、时间序列、数据操作、字符串处理等多个领域。你不需要记住所有函数——学会查找和组合使用才是关键。

### 函数分类速查

| 类别 | 典型函数 | 说明 |
|------|---------|------|
| 数学函数 | `abs`, `sqrt`, `log`, `exp`, `sin`, `cos` | 基础数学运算 |
| 统计函数 | `avg`, `sum`, `std`, `corr`, `cov`, `beta` | 统计聚合与分布 |
| 窗口函数 | `mavg`, `mstd`, `mcorr`, `mrank` | 滑动窗口计算 |
| 排序/排名 | `rank`, `dense_rank`, `cumrank` | 排名计算 |
| 序列函数 | `deltas`, `ratios`, `pct_change`, `cumsum`, `cumprod` | 序列变换 |
| 时间函数 | `year`, `month`, `dayOfWeek`, `temporalAdd` | 时间提取与操作 |
| 字符串 | `strlen`, `substr`, `replace`, `split`, `regexFind` | 字符串处理 |
| 类型转换 | `int`, `double`, `string`, `date`, `symbol` | 类型互转 |
| 高阶函数 | `each`, `loop`, `cross`, `reduce`, `byRow` | 将函数应用于集合 |
| 聚合函数 | `wsum`, `wavg`, `firstNot`, `lastNot` | 分组聚合 |

### 查找函数的方法

```dolphindb
// 1. 查看所有函数
functions();                  // 返回所有函数名列表

// 2. 按关键字搜索函数
functions(true).keys();       // 返回所有包含特定关键字的函数

// 3. 查看函数帮助
help(avg);                    // 查看 avg 函数的用法

// 4. 在 DolphinDB 手册中搜索
// docs.dolphindb.cn
```

## 3.2 用户自定义函数

### def 语法

```dolphindb
def functionName(param1, param2, ...) {
    // 函数体
    return result;
}
```

### 基础示例

```dolphindb
// 计算涨跌幅
def calcReturn(close, preClose) {
    return (close - preClose) / preClose * 100;
}

// 调用
r = calcReturn(15.67, 15.30);
print("涨跌幅: " + string(r) + "%");

// 向量化调用（自动，无需修改函数）
closes = 15.67 22.80 8.55;
pre_closes = 15.30 22.30 8.40;
returns = calcReturn(closes, pre_closes);
// returns: [2.418, 2.242, 1.786]
```

### 多参数函数

```dolphindb
// 计算波动率（多种方法）
def calcVolatility(prices, method="close") {
    if(method == "close") {
        rets = ratios(prices) - 1;          // 收盘价收益率
    } else if(method == "parkinson") {
        // Parkinson 波动率估计（基于 OHLC）
        hi = prices.high;
        lo = prices.low;
        rets = log(hi / lo) / (2 * sqrt(log(2.0)));
    } else {
        error("未知波动率计算方法: " + method);
    }
    return std(rets) * sqrt(252);           // 年化
}

// 调用
vol = calcVolatility(t, method="parkinson");
```

### 默认参数值

```dolphindb
// 带默认参数的函数
def movingAverageCrossover(prices, shortPeriod=5, longPeriod=20) {
    ma_short = mavg(prices, shortPeriod);
    ma_long = mavg(prices, longPeriod);
    return ma_short > ma_long and ma_short.prev() <= ma_long.prev();
}

// 可以使用默认参数
signal = movingAverageCrossover(closes);

// 或覆盖默认参数
signal = movingAverageCrossover(closes, shortPeriod=10, longPeriod=30);
```

## 3.3 匿名函数（Lambda）

匿名函数（Lambda）适合临时使用、无需命名的简短逻辑：

```dolphindb
// 语法：{ param -> expression }

// 基础 Lambda
square = { x -> x * x };
square(5);    // 25

// 多参数 Lambda
add = { x, y -> x + y };
add(3, 5);    // 8

// 配合高阶函数使用（最常见的 Lambda 场景）
prices = 15.0 22.0 8.0 45.0 12.0;

// each：对每个元素应用 Lambda
each({x -> iif(x > 20, "高", "低")}, prices);
// 输出: ["低", "高", "低", "高", "低"]

// cross：计算两两组合
each({x, y -> x + y}, [1.0, 2.0, 3.0], [0.1, 0.2]);
// 输出: [1.1, 1.2, 2.1, 2.2, 3.1, 3.2]
```

## 3.4 高阶函数

高阶函数接受函数作为参数，是函数式编程的核心：

### each：逐元素操作

```dolphindb
// each(func, vector)：对向量的每个元素应用函数
prices = 10.5 11.0 9.5 12.0;
each({x -> round(x, 1)}, prices);    // 四舍五入到1位小数
```

### loop：替代 for 循环

```dolphindb
// 计算因子值（每个 i 对应一个交易日窗口）
def calcFactor(i, data) {
    window = data[i-20 : i];          // 过去20日窗口
    return avg(window.close);
}
factors = loop(calcFactor{, t}, 20:200);
```

### reduce：累积计算

```dolphindb
// reduce(func, vector)：从左到右累积
reduce({a, b -> a + b}, 1 2 3 4 5);    // 15（1+2+3+4+5）
reduce({a, b -> a * b}, 1 2 3 4 5);    // 120（1×2×3×4×5）
```

### byRow：逐行计算

```dolphindb
// 对表的每一行应用函数
t = table(1..5 as a, 6..10 as b);
result = byRow({row -> row.a + row.b}, t);
// result: [7, 9, 11, 13, 15]
```

## 3.5 函数组合与模块化

### 函数嵌套与组合

```dolphindb
// 简单嵌套
result = avg(log(abs(returns + 1)));

// 管道式写法（DolphinDB 不原生支持，但可以通过变量实现）
def pipeline(x) {
    step1 = log(x + 1);
    step2 = abs(step1);
    step3 = avg(step2);
    return step3;
}
```

### 将函数组织为模块

```dolphindb
// 在文件 myutils.dos 中定义工具函数
// myutils.dos:
// def normalize(x) { return (x - avg(x)) / std(x); }
// def winsorize(x, limit=0.01) { ... }
// def zscore(x) { return (x - avg(x)) / std(x); }

// 在其他脚本中导入
use myutils;              // 导入模块
n = normalize(returns);   // 调用模块函数
```

> **函数命名建议**：(1) 使用驼峰式命名（如 `calcVolume`）或下划线式（如 `calc_volume`）；(2) 函数名用动词开头（get、calc、compute、update、find）；(3) 避免与内置函数重名。

## 3.6 常见函数的量化应用速查

```dolphindb
// 收益率计算
daily_return = ratios(close) - 1;                  // 日收益率
log_return = log(close / close.prev());             // 对数收益率

// 波动率
rolling_vol = mstd(log_return, 20) * sqrt(252);   // 20日滚动年化波动率

// 相关系数
corr_series = mcorr(returns_a, returns_b, 60);     // 60日滚动相关系数

// 排名
cross_rank = rank(returns);                         // 横截面排名
time_rank = mrank(close, true, 250);               // 250日时序排名

// 技术指标
ma = mavg(close, 20);                               // 20日均线
atr = mavg(max(high - low, max(high - pre_close, pre_close - low)), 14);  // ATR
rsi = 100 - 100 / (1 + mavg(iif(close > pre_close, close - pre_close, 0), 14) 
                   / mavg(iif(close < pre_close, pre_close - close, 0), 14));  // RSI

// 去极值
winsorized = iif(x > percentile(x, 99), percentile(x, 99),
                 iif(x < percentile(x, 1), percentile(x, 1), x));
```
