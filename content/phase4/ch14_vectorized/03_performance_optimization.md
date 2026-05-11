## 性能优化实践

掌握了向量化计算和函数式编程之后，理解DolphinDB的性能优化技巧能让量化策略的运行速度再上一个台阶。本节将分享在实战中验证过的优化方法和调优策略。

---

### 一、核心优化原则

```
正确的优化顺序：
1. 用向量替代循环                    ← 最重要，收益最大
2. 合理设计分区方案                  ← 决定IO效率
3. 预分配内存，避免动态增长           ← 减少系统调用
4. 选择合适的压缩算法                ← 平衡存储和读取速度
5. 调整系统参数（缓存、线程等）       ← 精细调优
```

---

### 二、替代循环 — 收益最大的优化

```sql
// ===== 优化前：用for循环处理（慢） =====
def slowMethod(data, N){
    result = array(DOUBLE, size(data))
    for(i in 0..(size(data) - 1)){
        // 逐个元素处理
        x = data[i]
        if(x > 0){
            result[i] = log(x) * exp(-x / N) + sin(x / N)
        } else {
            result[i] = 0
        }
    }
    return result
}

// ===== 优化后：全向量化（快10-100倍） =====
def fastMethod(data, N){
    x = data
    result = iif(x > 0, log(x) * exp(-x / N) + sin(x / N), 0)
    return result
}

// ===== 验证性能差异 =====
N = 10000000
data = rand(10.0, N)

timer slowMethod(data, 20)    // ~3500ms
timer fastMethod(data, 20)    // ~45ms（约78倍提升）
```

---

### 三、分区方案设计

分区是DolphinDB性能管理的核心。合理的分区能大幅减少查询时需要扫描的数据量：

```sql
// 分区方案对比

// ❌ 差方案：按股票代码哈希分区
// 问题：查询某只股票的完整时间序列需要扫描所有分区
db = database("dfs://trades_bad", HASH, [SYMBOL, 50])

// ✓ 好方案：日期+股票复合分区
// 优势：时间范围查询只需扫描相关日期分区，股票查询只扫描相关股票分区
db = database("dfs://trades_good", COMPO, [
    database(, VALUE, 2020.01.01..2024.12.31),  // 第一层：日期值分区
    database(, HASH, [SYMBOL, 20])               // 第二层：股票哈希分区
])

// 最优化方案：根据查询模式设计分区
// 日频策略 → 按日期分区（月度/季度）
// 回测场景 → 按日期+股票复合分区
// 高频tick数据 → 按日期+股票+小时分层分区
```

#### 分区设计决策表

| 数据频率 | 时间维度 | 标维度 | 层数 |
|----------|----------|--------|------|
| tick数据 | 按日分区 | HASH 20分区 | 2层 |
| 1分钟线 | 按月分区 | HASH 10分区 | 2层 |
| 日线数据 | 按年分区 | HASH 10分区 | 2层 |
| 财务数据 | VALUE(年份) | 无 | 1层 |

---

### 四、内存与缓存优化

#### 4.1 预分配内存

```sql
// ❌ 动态增长：每次append触发内存重新分配
result = table(10:0, `a`b`c, [INT, DOUBLE, STRING])
for(i in 1..1000000){
    result.append!(table(i as a, rand(1.0) as b, string(i) as c))
}

// ✓ 预分配：一次性分配足量内存
result = table(1000000:0, `a`b`c, [INT, DOUBLE, STRING])
result.append!(table(1..1000000 as a, rand(1.0, 1000000) as b, string(1..1000000) as c))
```

#### 4.2 缓存设置

```sql
// 查看当前内存使用
mem()

// 设置缓存大小（MB）
setMaxMemSize(16384)     // 设置最大内存为16GB

// 查看内存使用详情
select
    name,
    memSize,
    memUsed,
    memAllocated
from mem()

// 清理未使用的内存
clearAllCache()
```

#### 4.3 监控内存使用

```sql
// 监控流引擎的内存使用
def checkMemoryUsage(){
    engineStats = getStreamEngineStat()

    // 找出内存使用最多的引擎
    top_memory = select top 5 name, memoryUsed/1024/1024 as mem_MB
        from engineStats
        order by memoryUsed desc

    // 警告：超过1GB的引擎
    large = select * from engineStats where memoryUsed > 1024*1024*1024
    if(size(large) > 0){
        writeLog("WARNING: Engine memory > 1GB: " + string(large.name))
    }

    return top_memory
}
```

---

### 五、压缩算法选择

DolphinDB支持多种列存储压缩算法，选择合适的压缩算法可显著减少存储空间和IO时间：

| 压缩算法 | 压缩比 | 速度 | 适用场景 |
|----------|--------|------|----------|
| **LZ4** | 中（~3x） | 极快 | 高频查询、实时处理 |
| **DELTA** | 高（~5-10x） | 快 | 有序数据（时间、价格） |
| **ZSTD** | 很高（~8-15x） | 中 | 归档数据、冷数据 |
| **SNAPPY** | 低（~2x） | 极快 | 对延迟极度敏感的场景 |

```sql
// 创建分区表时指定压缩算法
db = database("dfs://trades_compressed")

schema = table(1:0,
    `timestamp`symbol`price`volume`bid`ask,
    [TIMESTAMP, SYMBOL, DOUBLE, LONG, DOUBLE, DOUBLE]
)

// 为不同列选择不同压缩算法
db.createPartitionedTable(
    table=schema,
    tableName="trades",
    partitionColumns=`timestamp`symbol,
    compressMethods={
        timestamp: "delta",       // 有序时间戳用DELTA
        price: "lz4",             // 浮点数用LZ4
        volume: "delta"           // 有序整型用DELTA
    }
)
```

---

### 六、查询优化速查

```sql
// 查询优化技巧汇总

// ✓ 使用分区过滤
select * from trades where date = 2024.01.15   // 只扫描1个分区

// ✓ 使用索引列
select * from trades where symbol = '000001.SZ'  // 走symbol哈希分区

// ✓ 限制返回列
select symbol, close from trades  // 而非 select *

// ✓ 使用context by替代子查询
select mavg(close, 20) from daily_data context by symbol  // 一次扫描

// ✓ 批量操作
data.append!(new_data)  // 而非逐行insert

// ✓ 使用compressed列存储
// ✓ 避免在高频查询中使用UDF（自定义函数），优先使用内置函数
```

> **优化哲学**：性能优化的本质是"减少不必要的计算"。向量化消除了Python层面的循环开销，分区消除了无关数据的扫描，压缩减少了磁盘IO，预分配避免了动态内存分配。这些优化叠加起来，通常能带来10-100倍的综合性能提升。
