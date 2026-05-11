## 1.1 为什么 NumPy 是量化计算的基础

NumPy（Numerical Python）是 Python 科学计算的核心库。在量化交易中，几乎所有数值计算都离不开 NumPy。它的核心优势在于向量化运算（Vectorized Operations）——一次操作可以作用于整个数组，而无需编写显式的 Python 循环。

### NumPy 为量化交易解决的问题

| 场景 | 纯Python方式 | NumPy方式 | 性能差异 |
|------|-------------|-----------|----------|
| 对数收益率计算 | 逐元素循环 `math.log()` | `np.log(close/close.shift())` | ~50x 快 |
| 协方差矩阵 | 双重for循环 | `np.cov(returns.T)` | ~100x 快 |
| 滚动窗口计算 | for循环 + 手动切片 | 配合Pandas rolling | ~10x 快 |

> **向量化思维**：在量化交易中，培养"向量化思维"至关重要。与其思考"如何对每一项数据做计算"，不如思考"如何对整个数组一次性做计算"。这种思维对于学习 DolphinDB（其核心就是向量化引擎）也至关重要。

## 1.2 创建 NumPy 数组

```python
import numpy as np

# === 从列表创建数组 ===
prices = np.array([10.5, 11.2, 10.8, 11.5, 12.0])
print(prices)        # [10.5 11.2 10.8 11.5 12. ]
print(prices.dtype)  # float64

# === 创建特定形状的数组 ===
# 创建10只股票、5天的价格矩阵
price_matrix = np.array([
    [10.0, 10.5, 10.3, 11.0, 10.8],  # 股票A
    [25.0, 24.5, 25.2, 26.0, 25.8],  # 股票B
    [50.0, 51.0, 50.5, 52.0, 51.5],  # 股票C
    ...
])
print(price_matrix.shape)  # (3, 5)  = 3只股票 × 5天

# === 特殊数组创建 ===
zeros_arr = np.zeros(5)         # 全零数组 [0. 0. 0. 0. 0.]
ones_arr = np.ones((3, 4))      # 全一数组 3行×4列
arrange_arr = np.arange(0, 1, 0.1)  # 等差数列 [0. 0.1 ... 0.9]
linspace_arr = np.linspace(0, 1, 11) # 等间距 [0. 0.1 ... 1.0]
random_arr = np.random.randn(252)    # 标准正态分布 252个值
```

### 数组的基本属性

```python
arr = np.array([[1, 2, 3], [4, 5, 6]])

print(arr.ndim)    # 2  —— 维度数（2维）
print(arr.shape)   # (2, 3) —— 形状（2行3列）
print(arr.size)    # 6  —— 总元素数
print(arr.dtype)   # int64 —— 数据类型
print(arr.itemsize) # 8  —— 每个元素的字节数
print(arr.nbytes)  # 48 —— 总字节数
```

## 1.3 NumPy 核心运算

### 向量化运算——NumPy的灵魂

```python
import numpy as np

# 假设有两只股票5天的收盘价
stock_a = np.array([100, 101, 102, 103, 104])
stock_b = np.array([50, 51, 49, 52, 50])

# === 逐元素运算（向量化） ===
sum_prices = stock_a + stock_b       # [150, 152, 151, 155, 154]
diff_prices = stock_a - stock_b      # [50, 50, 53, 51, 54]
ratio = stock_a / stock_b            # [2.0, 1.98, 2.08, 1.98, 2.08]

# === 数学函数运算 ===
log_price = np.log(stock_a)          # 对数变换
sqrt_price = np.sqrt(stock_a)        # 开方
exp_price = np.exp(stock_a)          # 指数变换

# === 条件筛选（布尔索引） ===
# 找出stock_a中价格大于102的日期
condition = stock_a > 102
print(stock_a[condition])            # [103, 104]

# 复杂条件
condition = (stock_a > 101) & (stock_b < 51)
print(np.where(condition))           # 返回满足条件的索引
```

### 关键的统计运算

```python
returns = np.array([0.01, -0.02, 0.03, -0.01, 0.02, 0.01, -0.005])

# === 基础统计 ===
print(f'均值: {np.mean(returns):.4f}')        # 日均收益率
print(f'中位数: {np.median(returns):.4f}')
print(f'标准差: {np.std(returns):.4f}')        # 波动率基础
print(f'方差: {np.var(returns):.6f}')
print(f'最小值: {np.min(returns):.4f}')        # 最大单日亏损
print(f'最大值: {np.max(returns):.4f}')        # 最大单日收益
print(f'总和: {np.sum(returns):.4f}')          # 累计收益率

# === 累积运算 ===
cum_returns = np.cumprod(1 + returns)  # 累积净值
print(f'净值曲线: {cum_returns}')

# === 排序 ===
sorted_returns = np.sort(returns)
print(f'最差的5%收益（VaR）: {np.percentile(returns, 5):.4f}')
```

### 矩阵运算——多资产组合计算

```python
# 3只股票的日收益率矩阵（5天）
returns = np.array([
    [ 0.01, -0.02,  0.01,  0.03, -0.01],  # 股票A
    [ 0.02, -0.01, -0.03,  0.01,  0.02],  # 股票B
    [-0.01,  0.02,  0.01, -0.02,  0.01]   # 股票C
])  # shape: (3, 5)

# 计算协方差矩阵（每只股票是一行，需要转置）
cov_matrix = np.cov(returns)  # 3×3的协方差矩阵
print('协方差矩阵:\n', cov_matrix)

# 计算相关系数矩阵
corr_matrix = np.corrcoef(returns)
print('相关系数矩阵:\n', corr_matrix)

# 等权组合的收益和波动率
weights = np.array([0.33, 0.33, 0.34])  # 组合权重
portfolio_returns = weights @ returns    # 矩阵乘法：组合每日收益
avg_return = np.mean(portfolio_returns)
portfolio_vol = np.sqrt(weights @ cov_matrix @ weights)
print(f'组合年化波动率: {portfolio_vol * np.sqrt(252):.4f}')
```

> **矩阵乘法的金融意义**：`weights @ returns` 计算的是每日组合收益——这是量化投资组合计算最基本的操作。理解向量的矩阵乘法和广播机制，是掌握 NumPy 和 DolphinDB 向量化计算的关键。

## 1.4 广播机制（Broadcasting）

广播是 NumPy 最强大的特性之一，允许对形状不同的数组进行运算。

```python
# 广播示例1：单个净值 × 各资产权重
nav = np.array([1000000])               # 总资产净值
weights = np.array([0.3, 0.3, 0.4])    # 3个资产的权重
allocation = nav * weights              # 广播：每个资产分配的资金
print(allocation)  # [300000. 300000. 400000.]

# 广播示例2：每只股票的日收益率减去市场平均收益率
stock_returns = np.array([[0.01, 0.02, 0.015],
                           [-0.01, 0.03, -0.005],
                           [0.02, -0.01, 0.01]])  # 3只股票 × 3天

market_returns = np.mean(stock_returns, axis=0)  # 每天的市场平均收益
excess_returns = stock_returns - market_returns   # 广播：超额收益矩阵
print('超额收益:\n', excess_returns)

# 广播示例3：将一维数组与二维数组组合
# 3只股票的收盘价和5天的涨跌幅
close_prices = np.array([100, 200, 50]).reshape(3, 1)  # (3, 1)
daily_returns = np.array([0.01, -0.02, 0.015, 0.03, -0.01])  # (5,)
price_paths = close_prices * (1 + daily_returns)  # 广播：(3,1) × (5,) → (3,5)
print('价格路径:\n', price_paths)
```

### 广播规则口诀

> **广播三原则**：1) 从最后一维开始对齐维度；2) 维度为1的轴会被拉伸到匹配另一数组；3) 缺失的维度用1补齐后广播。牢记——shape不兼容时会报错。

## 1.5 量化交易中的 NumPy 实战

### 场景1：计算收益率矩阵

```python
def calculate_returns_matrix(close_prices):
    """
    从收盘价矩阵计算收益率矩阵
    
    参数:
    close_prices: shape (n_stocks, n_days)
    
    返回:
    returns: shape (n_stocks, n_days-1)
    """
    # 简单收益率 = (P_t - P_{t-1}) / P_{t-1}
    returns = np.diff(close_prices, axis=1) / close_prices[:, :-1]
    return returns

# 对数收益率（常用于金融计算，因为对数收益率可加性更好）
def log_returns(close_prices):
    """对数收益率 = ln(P_t / P_{t-1}) = ln(P_t) - ln(P_{t-1})"""
    return np.diff(np.log(close_prices), axis=1)
```

### 场景2：最大回撤计算

```python
def max_drawdown(returns):
    """
    计算策略的最大回撤
    
    算法：
    1. 计算累计净值曲线
    2. 计算滚动历史最高净值
    3. 当前回撤 = (当前净值 - 历史最高) / 历史最高
    4. 最大回撤 = 所有回撤中的最小值
    """
    cum_returns = np.cumprod(1 + returns)
    running_max = np.maximum.accumulate(cum_returns)
    drawdown = (cum_returns - running_max) / running_max
    return np.min(drawdown)

# 测试
sample_returns = np.random.randn(252) * 0.01  # 模拟一年日收益
mdd = max_drawdown(sample_returns)
print(f'最大回撤: {mdd:.2%}')
```

### 场景3：信号生成与回测

```python
def backtest_signal(prices, signals):
    """
    简单回测函数
    
    参数:
    prices: 收盘价数组
    signals: 仓位信号（1=多头, 0=空仓, -1=空头）
    
    返回:
    策略日收益率
    """
    # 计算每日收益率
    daily_returns = np.diff(prices) / prices[:-1]
    
    # 信号需要滞后一天（今天产生信号，明天执行）
    strategy_returns = signals[:-1] * daily_returns
    
    return strategy_returns

# 模拟简单回测
prices = np.array([100, 101, 99, 102, 103, 105, 104, 106, 108, 107])
signals = np.array([0, 1, 1, 0, 1, 0, 0, 1, 1, 1])  # 0/1仓位

strategy_ret = backtest_signal(prices, signals)
cum_ret = np.cumprod(1 + strategy_ret) - 1
print(f'策略累计收益: {cum_ret[-1]:.2%}')
```

### 场景4：蒙特卡洛模拟

```python
def monte_carlo_simulation(start_price, mu, sigma, n_days, n_simulations):
    """
    股票价格的蒙特卡洛模拟
    
    假设价格服从几何布朗运动：
    dS = μS dt + σS dW
    
    参数:
    start_price: 初始价格
    mu: 年化预期收益率
    sigma: 年化波动率
    n_days: 模拟天数
    n_simulations: 模拟次数
    """
    dt = 1 / 252  # 日时间步长
    # 生成随机项：形状为 (n_simulations, n_days)
    random_walk = np.random.randn(n_simulations, n_days)
    
    # 价格路径模拟（向量化计算）
    returns = (mu - 0.5 * sigma**2) * dt + sigma * np.sqrt(dt) * random_walk
    price_paths = start_price * np.cumprod(1 + returns, axis=1)
    
    return price_paths

# 运行模拟
sims = monte_carlo_simulation(100, 0.10, 0.25, 252, 1000)
final_prices = sims[:, -1]
print(f'模拟终值均值: {np.mean(final_prices):.2f}')
print(f'模拟终值标准差: {np.std(final_prices):.2f}')
```

> **蒙特卡洛方法在量化中的价值**：蒙特卡洛模拟是最重要的风险分析工具之一——通过模拟成千上万种可能的路径，你可以获得对策略极端风险的直观认识。与其依赖一个点估计（如"预期收益15%"），不如理解收益的整个分布和尾部风险。

## 1.6 NumPy 的最佳实践

| 实践 | 说明 |
|------|------|
| 避免for循环 | 能用向量化操作就不用循环 |
| 预分配数组 | 用 `np.zeros(n)` 而非 `list.append()` |
| 理解axis参数 | `axis=0` 按行聚合，`axis=1` 按列聚合 |
| 注意数据类型 | float64 精度高但占内存，float32 有时足够 |
| 使用视图而非拷贝 | `arr[:10]` 是视图（不复制），`arr[[0,1,2]]` 是花式索引（复制） |

### 常见陷阱

```python
# 陷阱1：整数除法
a = np.array([1, 2, 3])
b = a / 2          # [0.5, 1.0, 1.5] —— Python 3 OK
# 在 Python 2 中会是 [0, 1, 1]

# 陷阱2：花式索引返回拷贝
arr = np.array([1, 2, 3, 4])
sub = arr[[0, 2]]   # sub 是拷贝
sub[0] = 999        # 不影响 arr

# 陷阱3：NaN处理
returns = np.array([0.01, np.nan, -0.02, 0.03])
print(np.mean(returns))  # nan —— 错误！
print(np.nanmean(returns))  # 0.0067 —— 正确
```

> **学习建议**：NumPy 是 Pandas 和 DolphinDB 向量化计算的基础。熟练使用 NumPy，将帮助你更快地理解 Pandas 的数据操作和 DolphinDB 的向量化引擎。建议花足够的时间掌握 NumPy 的向量化思维。
