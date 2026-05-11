## 向量化计算原理

向量化计算（Vectorized Computing）是DolphinDB高性能的核心秘密。与传统的逐行循环（Row-by-Row Loop）不同，向量化计算将整个数组视为一个计算单元，利用CPU的SIMD指令集和内存预取技术，实现数十倍乃至百倍的性能提升。

---

### 一、为什么向量化计算更快

#### 1.1 逐行循环的效率瓶颈

传统Python逐行循环处理100万条数据的典型方式：

```python
# 逐行循环方式 — 性能灾难
results = []
for i in range(len(data)):
    result = data[i] * 2 + 1
    results.append(result)
```

低效原因：
- **解释器开销**：每次迭代都需要Python解释器执行字节码
- **类型检查**：每次操作都要检查变量类型
- **内存碎片**：逐次append导致频繁内存分配
- **无CPU并行**：循环体串行执行，无法利用SIMD

#### 1.2 向量化方式的优势

```python
# 向量化方式 — 一条指令处理整个数组
import numpy as np
results = np.array(data) * 2 + 1
```

高效原因：
- **批量操作**：整个数组作为整体运算，无循环开销
- **编译级速度**：C/C++底层实现，直接操作原始内存
- **SIMD指令**：CPU并行处理多个数据（单指令多数据流）
- **缓存友好**：连续内存访问，充分利用CPU缓存

---

### 二、DolphinDB的向量化执行引擎

DolphinDB从设计之初就采用向量化引擎，所有的SQL操作、函数调用都在向量层面执行：

```sql
// DolphinDB中的向量化操作
// 所有列操作都是向量化的，自动并行

// 例1：简单的向量运算
a = 1..1000000                     // 创建包含100万个元素的向量
b = a * 2 + 1                      // 向量化运算，毫秒级完成
c = log(a) + sqrt(a)               // 多个向量化操作组合

// 例2：SQL中的向量化
select
    symbol,
    date,
    close,
    // 这些窗口函数都是向量化执行的
    mavg(close, 20) as ma_20,      // 整个列的移动平均，一次性计算
    mstd(close, 20) as std_20,     // 整个列的标准差
    (close - mavg(close, 20)) / mstd(close, 20) as zscore
from daily_data
context by symbol
// DolphinDB的执行计划：所有列一次性遍历，在一次扫描中完成所有窗口计算
```

---

### 三、性能对比：循环 vs 向量化

```sql
// DolphinDB中的性能对比：循环 vs 向量化

// ===== 方法1：循环方式（慢） =====
timer(100){
    N = 10000000
    result = array(DOUBLE, N)
    for(i in 0..(N-1)){
        result[i] = sin(i * 0.001) + cos(i * 0.001)
    }
}
// 典型耗时：~2000ms（逐行计算，慢）

// ===== 方法2：向量化方式（快） =====
timer(100){
    N = 10000000
    i = 0..(N-1)
    result = sin(i * 0.001) + cos(i * 0.001)
}
// 典型耗时：~50ms（向量化，快40倍）

// ===== 方法3：利用窗口函数的向量化 =====
timer(100){
    select
        symbol,
        mavg(close, 20) as ma,
        mstd(close, 20) as std
    from daily_data
    context by symbol
}
// 窗口函数全部向量化，一次扫描完成
```

```sql
// 向量化性能实测对比
N = 100000000           // 1亿条数据

timer{
    // 向量化计算：一次处理整个向量
    x = rand(1.0, N)
    y = rand(1.0, N)
    result = exp(-(x^2 + y^2))     // 逐元素向量化运算
}
// 输出: Time elapsed: 523.45 ms

timer{
    // 逐行循环：完全相同的计算
    result = array(DOUBLE, N)
    for(i in 0..(N-1)){
        result[i] = exp(-(rand(1.0, 1)[0]^2 + rand(1.0, 1)[0]^2))
    }
}
// 输出: Time elapsed: 45230.12 ms （慢了约86倍）
```

---

### 四、DolphinDB中的列表 vs 向量

DolphinDB区分两种集合类型：

| 类型 | 存储 | 操作 | 性能 | 用途 |
|------|------|------|------|------|
| **向量（Vector）** | 连续内存、同类型 | 向量化 | 极快 | 数值计算列 |
| **元组（Tuple）/ 列表** | 灵活存储 | 逐元素 | 较慢 | 异构数据收集 |

```sql
// 向量：连续内存，同类型
v = 1..1000000                      // FAST INT VECTOR，连续内存
typeName(v)                         // FAST INT VECTOR

// 元组：可以包含不同类型
t = (1, "hello", 3.14, 2024.01.01)
typeName(t)                         // ANY VECTOR（可以容纳任意类型）

// 数组向量（Array Vector）：向量的向量
av = arrayVector(1..100, 1..100, 1..100)    // 适合存储不规则数据
```

---

### 五、向量化编程的核心原则

| 原则 | 说明 | 反例 |
|------|------|------|
| **用向量替代循环** | 整列一次性操作 | `for(i in 0..N) result[i] = ...` |
| **用函数替代分支** | 使用`iif`、`case when`替代if/else循环 | 在循环中判断条件后赋值 |
| **减少中间变量** | 一条表达式完成计算 | 逐行创建临时变量 |
| **批量读写数据** | 整列读写而非逐行 | 循环中读一行、写一行 |
| **利用内置函数** | 使用DolphinDB提供的向量化函数 | 用循环实现内置函数的功能 |

```sql
// 向量化最佳实践 vs 反模式

// ❌ 反模式：用循环处理数据
result = array(DOUBLE, size(data))
for(i in 0..(size(data)-1)){
    if(data[i] > 0){
        result[i] = log(data[i])
    } else {
        result[i] = -999
    }
}

// ✓ 向量化：用iif一次性处理
result = iif(data > 0, log(data), -999)
```

> **核心理念**：在DolphinDB中，"能用向量就不用循环"是性能的第一要义。向量化不仅让代码运行更快（通常10-100倍），也让代码更简洁、更易读。DolphinDB的所有内置函数——`mavg`、`mstd`、`iif`、`log`等——都经过了向量化优化，在C++层面编译执行，充分利用了现代CPU的并行能力。
