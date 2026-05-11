## 4.1 两种范式的定位

DolphinDB 将 SQL 和脚本编程整合在一起，在同一个脚本文件中，你可以自由切换这两种计算范式：

```
┌─────────────────────────────────────────────────────┐
│            SQL 擅长                                   │
│  • 数据检索和过滤（WHERE）                             │
│  • 聚合和分组统计（GROUP BY）                          │
│  • 透视表转换（PIVOT BY）                              │
│  • 表连接（JOIN）                                     │
│  • 数据重排（ORDER BY）                               │
│  → 特点：声明式，告诉系统"要什么"而非"怎么做"             │
├─────────────────────────────────────────────────────┤
│           脚本编程擅长                                 │
│  • 复杂数学计算（矩阵运算、优化等）                      │
│  • 条件逻辑和状态机                                    │
│  • 参数扫描和网格搜索                                  │
│  • 迭代算法（收敛计算）                                │
│  • 文件操作和外部API调用                               │
│  → 特点：命令式，精确控制每一步的执行过程                  │
└─────────────────────────────────────────────────────┘
```

### 选择决策树

```
你需要做什么？
│
├── 从大表中抽取/过滤/汇总数据？
│   → 使用 SQL（SELECT-FROM-WHERE-GROUP BY）
│
├── 对已有数据进行复杂的逐元素数学变换？
│   → 使用向量化脚本/si
│
├── 编写策略的回测逻辑（状态追踪）？
│   → 使用脚本（for 循环 + if-else）
│
├── 计算各种技术指标和因子？
│   → SQL（CONTEXT BY + 窗口函数）优先，复杂逻辑再用脚本
│
└── 需要两者的结果协同？
    → 混合使用：SQL 查询获取数据 → 脚本处理逻辑 → 结果写回
```

## 4.2 混合使用案例

### 案例 1：先 SQL 取数据，再脚本计算

```dolphindb
t = loadTable("dfs://stock_day", "kline_day");

// Step 1: SQL 获取数据子集
data = select trade_date, sym, close, volume, pre_close
       from t
       where trade_date between 2024.01.01:2024.03.31
         and sym in (`000001, `000002, `000003);

// Step 2: 脚本做复杂计算
// 计算每只股票的价格动量（20日累计收益率排名）
result = select trade_date, sym, close
         from data
         context by sym;

// 计算收益率矩阵（用 pivot by 转为宽格式）
ret_matrix = select trade_date, 
             ratios(close) - 1 as daily_ret
             from data
             pivot by sym;

// 在脚本中对矩阵做更复杂的计算
// 例如：PCA 分解、协方差矩阵收缩等
```

### 案例 2：在 SQL 中嵌入向量化计算

```dolphindb
// 在 SELECT 子句中直接使用向量化函数
select 
    trade_date,
    sym,
    close,
    // 向量化计算收益率
    ratios(close) - 1 as daily_return,
    // 向量化计算振幅
    (high - low) / pre_close as amplitude,
    // 向量化 + 条件判断
    iif(volume > mavg(volume, 20) * 1.5, "放量", "正常") as volume_flag
from t
context by sym;
```

### 案例 3：完整策略信号生成（混合范式）

```dolphindb
// ═══════════════════════════════════════
// 双均线突破策略信号生成
// ═══════════════════════════════════════

def generateSignal(short_period, long_period) {
    t = loadTable("dfs://stock_day", "kline_day");
    
    // SQL: 提取数据并计算均线
    data = select
        trade_date, sym, close,
        mavg(close, short_period) as ma_short,
        mavg(close, long_period) as ma_long,
        close > mavg(close, long_period) as above_long,
        volume
    from t
    where trade_date >= 2024.01.01
    context by sym;
    
    // SQL: 生成金叉/死叉信号
    signals = select
        trade_date, sym, close,
        iif(ma_short > ma_long and ma_short.prev() <= ma_long.prev(), 1,
            iif(ma_short < ma_long and ma_short.prev() >= ma_long.prev(), -1, 0)
        ) as crossover_signal
    from data
    context by sym;
    
    // 脚本: 根据信号模拟持仓（状态机，SQL不擅长）
    holdings = dict(SYMBOL, INT);
    trade_records = table(100000:0, 
        `trade_date`sym`action`price`quantity,
        [DATE, SYMBOL, SYMBOL, DOUBLE, INT]
    );
    
    dates = exec distinct trade_date from signals order by trade_date;
    for(date_ in dates) {
        today_signals = select * from signals where trade_date = date_;
        for(i in 0:today_signals.rows()) {
            sym_ = today_signals.sym[i];
            sig_ = today_signals.crossover_signal[i];
            price_ = today_signals.close[i];
            
            current_hold = holdings[sym_] ? holdings[sym_] : 0;
            
            if(sig_ == 1 && current_hold == 0) {
                // 金叉买入
                qty = 1000;
                holdings[sym_] = qty;
                trade_records.append!(
                    table(date_ as trade_date, sym_ as sym, 
                          "BUY" as action, price_ as price, qty as quantity)
                );
            } else if(sig_ == -1 && current_hold > 0) {
                // 死叉卖出
                qty = current_hold;
                holdings[sym_] = 0;
                trade_records.append!(
                    table(date_ as trade_date, sym_ as sym,
                          "SELL" as action, price_ as price, qty as quantity)
                );
            }
        }
    }
    
    return trade_records;
}

// 执行策略
trades = generateSignal(5, 20);
select count(*) as total_trades, 
       sum(iif(action == "BUY", quantity, 0)) as total_buy_qty
from trades;
```

## 4.3 性能对比与选择

### 同一任务的不同实现方式

```dolphindb
// 任务：计算每只股票过去20日的平均成交量
t = loadTable("dfs://stock_day", "kline_day");

// 方式1: 纯 SQL（最优）
timer {
    result = select sym, trade_date, mavg(volume, 20) as avg_vol_20
             from t
             context by sym;
};
// 速度：★★★★★ （最快，全部在引擎内完成）

// 方式2: SQL + 脚本混合
timer {
    data = select sym, trade_date, volume from t context by sym;
    result = select sym, trade_date, 
             each({v -> mean(v[max(0, size(v)-20):size(v)])}, 
                  cumPositive(volume)) as avg_vol_20
             from data;
};
// 速度：★★★☆☆ (有数据在SQL和脚本间传递的开销)

// 方式3: 纯脚本（不推荐）
timer {
    // 需要手动模拟窗口计算……
};
// 速度：★☆☆☆☆（最慢，失去了分区优势）
```

### 优化原则

| 原则 | 说明 |
|------|------|
| **计算下沉** | 尽可能让 SQL 引擎做聚合/过滤，而非将全量数据拉到脚本层 |
| **分区利用** | SQL 能自动利用分区裁剪，脚本需手动实现 |
| **向量化为先** | 无论哪种方式，优先向量化而非逐元素循环 |
| **最小数据传输** | 从 SQL 到脚本只传递必要的数据列和行 |
| **SQL优先，脚本兜底** | 能用 SQL 表达的逻辑用 SQL，SQL 表达不了再用脚本 |

## 4.4 混合范式的边界

### 用 SQL 的场景

```dolphindb
// 大数据量过滤 → 分区裁剪
select * from t where trade_date = 2024.01.15;   // 只扫描一个分区

// 分组聚合 → 高效的在引擎内完成
select sym, avg(close) from t group by sym;

// 窗口计算 → mavg, mstd 等函数高度优化
select sym, mavg(close, 20) from t context by sym;
```

### 用脚本的场景

```dolphindb
// 迭代算法（如 Newton-Raphson 求根）
def newtonRaphson(f, df, x0, tolerance=1e-6, maxIter=100) {
    x = x0;
    for(i in 1:maxIter) {
        x_new = x - f(x) / df(x);
        if(abs(x_new - x) < tolerance) return x_new;
        x = x_new;
    }
    return x;
}

// 复杂的状态追踪（如持仓管理、订单管理）
// 这类逻辑几乎必须用循环 + 条件判断实现

// 外部系统交互（文件读写、网络请求）
```

### 不应混用的反例

```dolphindb
// ❌ 反例：在 SQL 中嵌套复杂逻辑
select sym, {x -> ... 复杂lambda ...}(close) from t;
// 虽然可能语法正确，但可读性极差，难以维护

// ✓ 正确做法：SQL 取数据 → 脚本计算 → 组装结果
data = select sym, close from t context by sym;
result = scriptComplexLogic(data);
```

## 4.5 总结

| 场景 | 推荐范式 | 原因 |
|------|---------|------|
| 查询某天数据 | SQL | 分区裁剪，速度快 |
| 计算日均成交量 | SQL (GROUP BY) | 聚合优化 |
| 计算移动平均 | SQL (CONTEXT BY) | 窗口函数已优化 |
| 收益率矩阵 | SQL (PIVOT BY) | 转置高效 |
| 协方差矩阵 | 脚本 | 数学库支持 |
| 持仓管理 | 脚本 (for循环) | 状态追踪 |
| 参数优化 | 脚本 | 循环迭代 |
| 可视化导出 | SQL + 脚本 | 先查后度 |

> **核心理念**：DolphinDB 的真正威力来自 **SQL + 脚本的无缝融合**，而非单一范式的独奏。优秀量化开发者既能用 SQL 精准快速地取数，也能用脚本编写灵活精细的逻辑。两者结合，才能发挥 DolphinDB 的最大生产力。
