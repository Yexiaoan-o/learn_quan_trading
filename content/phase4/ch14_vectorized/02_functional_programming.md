## 函数式编程与高阶函数

DolphinDB不仅支持向量化计算，还融入了函数式编程范式。高阶函数（Higher-Order Functions）和管道操作符使得数据处理代码更加声明式和可组合。

---

### 一、核心高阶函数

高阶函数是指接受函数作为参数，或返回函数作为结果的函数。DolphinDB的核心高阶函数如下：

| 函数 | 行为 | 使用场景 |
|------|------|----------|
| **each** | 对向量每个元素应用函数 | 逐元素变换 |
| **loop** | 对向量每个元素应用函数（支持多输入） | 逐元素计算（多参数） |
| **cross** | 返回两个向量的笛卡尔积应用函数 | 生成配对矩阵 |
| **pivot** | 通过指定的行、列和聚合函数重塑数据 | 透视表转换 |
| **moving** | 在滑动窗口上应用自定义函数 | 自定义窗口计算 |
| **peach** | each的并行版本 | 多核并行处理 |
| **ploop** | loop的并行版本 | 多核并行处理 |

---

### 二、each — 逐元素变换

```sql
// each：对向量的每个元素应用函数

// 基础用法：每个元素平方
result = each(def(x): x^2, 1..5)
// 结果: [1, 4, 9, 16, 25]

// 多参数版本（使用loop）
result = each(def(x, y): x^y, 2..6, 2)
// 结果: 2^2, 3^2, 4^2, 5^2, 6^2 = [4, 9, 16, 25, 36]

// 实际金融应用：计算每只股票的夏普比率
function calcSharpe(ret){
    return avg(ret) / std(ret) * sqrt(252)
}

// 对每只股票的收益率序列计算夏普比率
sharpe_list = each(calcSharpe, returnsBySymbol)
```

---

### 三、cross — 笛卡尔积计算

`cross`是量化因子研究中的利器，尤其适合批量计算股票对之间的相关系数、协整关系等：

```sql
// cross：生成两个向量的笛卡尔积
// cross(func, X, Y)
// 对 X[i] 和 Y[j] 的每一对组合应用 func

// 例1：计算5只股票两两之间的相关系数
stocks = 1..5
result = cross(def(x, y): x + y, stocks, stocks)
// 结果: 5×5 矩阵

// 例2：计算所有股票对的价差
prices_a = [10.5, 20.3, 15.7, 8.9, 12.1]   // 5只股票A
prices_b = [10.2, 20.0, 15.5, 9.1, 12.0]   // 5只股票B

spread_matrix = cross(def(pa, pb): pa - pb, prices_a, prices_b)
// 结果: 5×5的价差矩阵

// 例3：批量计算相关系数（实用场景）
stock_returns = matrix(returns_1, returns_2, returns_3)  // 3只股票的收益率矩阵

corr_func = def(x, y){
    valid = x not NULL and y not NULL
    return corr(x[valid], y[valid])
}

corr_matrix = cross(corr_func, stock_returns, stock_returns)
// 输出: 3×3的相关系数矩阵
```

---

### 四、管道操作符（Pipe Operator）

DolphinDB的管道操作符类似于Unix的`|`，让数据从左到右流经一系列变换：

```sql
// 管道操作符的使用

// 没有管道：嵌套调用，从内向外读（不直观）
result = select avg(price) from (select * from (select ...))

// 使用管道：从左到右读（清晰直观）
result = daily_data
    |> select where symbol = '000001.SZ'
    |> select date, close, volume
    |> select *, mavg(close, 20) as ma_20
    |> select where close > ma_20

// 实际案例：因子计算管道
factor_result = price_data
    // 第1步：过滤有效数据
    |> select where close > 0 and volume > 0
    // 第2步：计算基础指标
    |> select
        symbol,
        date,
        close,
        log(close / prev(close)) as ret,
        mavg(close, 20) as ma_20,
        mstd(close, 20) as std_20
    // 第3步：计算因子值
    |> select
        *,
        (close - ma_20) / std_20 as zscore,
        sum(sign(ret) * volume, 5) as obv_5d
    // 第4步：筛选有效信号
    |> select where abs(zscore) > 2.0
```

---

### 五、匿名函数（Lambda）

DolphinDB使用`def`定义匿名函数（Lambda），在需要"一次性的小函数"时非常方便：

```sql
// Lambda（匿名函数）的多种形式

// 形式1：单行Lambda
square = def(x): x^2
square(5)   // 25

// 形式2：多行Lambda
process = def(x) {
    ma = mavg(x, 20)
    std = mstd(x, 20)
    return (x - ma) / std
}

// 形式3：作为高阶函数的参数
// 对每列应用Lambda计算去均值
result = each(def(col): col - avg(col), data_matrix)

// 形式4：多参数Lambda
calc_ratio = def(a, b): a / b
select each(calc_ratio, price, volume) from data

// 实际金融应用：自定义衰减加权均线
decay_ma = def(price, decay=0.9){
    n = size(price)
    weights = decay pow (0..(n-1))
    weights = weights / sum(weights)
    return sum(price * weights)
}
```

---

### 六、函数式编程技巧

#### 6.1 函数组合

```sql
// 将多个简单函数组合成复杂处理流程

// 定义原子函数
normalize = def(x): (x - avg(x)) / std(x)
winsorize = def(x, nStd=3): iif(x > nStd, nStd, iif(x < -nStd, -nStd, x))

// 函数组合：先缩尾再标准化
standardize = def(x){
    return normalize(winsorize(x))
}

// 复杂的数据预处理流程
prepare_factor = daily_data
    |> select symbol, date, close, volume
    |> select
        *,
        standardize(log(close / prev(close))) as std_ret,
        standardize(volume) as std_vol
```

#### 6.2 函数式 vs 命令式对比

```sql
// ===== 命令式（传统方式）=====
// 意图不清晰，需要解读循环逻辑
results = array(DOUBLE, n)
for(i in 0..(n-1)){
    x = data[i]
    if(x > 0){
        results[i] = log(x)
    } else {
        results[i] = 0
    }
}

// ===== 函数式（声明式）=====
// 意图清晰：对正数取log，非正数返回0
results = iif(data > 0, log(data), 0)

// 更复杂的声明式处理
factor_pipeline = raw_data
    |> select where volume > 0                          // 过滤
    |> select *, mavg(close, 20) as ma                  // 计算
    |> select *, (close - ma) / ma as momentum          // 变换
    |> select *, iif(momentum > 0.1, 1, 0) as signal   // 判断
```

> **编程哲学**：函数式编程强调"做什么"而非"怎么做"。`each`、`cross`等高阶函数让代码更关注业务逻辑而非实现细节。管道操作符让数据变换步骤一目了然，显著提升了代码的可维护性。
