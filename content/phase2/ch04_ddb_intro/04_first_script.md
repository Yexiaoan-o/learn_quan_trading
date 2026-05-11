## 4.1 第一个 DolphinDB 命令

启动 DolphinDB 并通过 Web Console 或 VSCode 连接后，在脚本编辑器中输入以下命令，开始你的 DolphinDB 之旅。

### 基础运算

DolphinDB 支持直接进行数学运算，就像使用计算器一样：

```dolphindb
// 基本算术运算
1 + 1;
// 输出: 2

10 * 3.14;
// 输出: 31.4

pow(2, 10);
// 输出: 1024（2 的 10 次方）
```

> **注意**：DolphinDB 每条语句以**分号 `;`** 或**换行**结束。如果不加分号，也会以换行为分割符。但从代码可读性出发，建议统一使用分号。

```dolphindb
// 多条语句，每行以分号结束
a = 100;
b = 200;
c = a + b;
c;
// 输出: 300
```

### 打印输出

```dolphindb
// print 函数：输出任意类型的数据
print("Hello DolphinDB!");

// 格式化打印
name = "量化交易";
print("欢迎学习" + name);

// 输出变量值
x = 42;
y = x * x;
print("x的平方 = " + string(y));
```

### 向量（数组）运算

DolphinDB 的核心是**向量化运算**——对一整个数组进行批量操作，而非逐个元素循环：

```dolphindb
// 创建向量
prices = 10.5 10.8 11.2 11.0 10.9;
volumes = 1000 1200 800 1500 900;

// 向量运算：无需 for 循环
turnover = prices * volumes;
turnover;
// 输出: [10500, 12960, 8960, 16500, 9810]

// 统计函数
avg(prices);    // 均价
sum(volumes);   // 总成交量
max(prices);    // 最高价
min(prices);    // 最低价
```

向量化运算的性能远高于逐元素循环，这是 DolphinDB 在大数据处理中表现卓越的根本原因。

## 4.2 创建你的第一张表

在 DolphinDB 中，`table` 函数可以快速创建内存表：

```dolphindb
// 创建一张简单的股票日线数据表
kline = table(
    `000001`000001`000002`000002`000003 as sym,
    2024.01.02 2024.01.03 2024.01.02 2024.01.03 2024.01.02 as trade_date,
    15.20 15.67 22.50 22.80 8.35 as open,
    15.85 15.95 23.10 23.20 8.60 as high,
    15.10 15.50 22.20 22.60 8.20 as low,
    15.67 15.72 22.80 22.90 8.55 as close,
    12500000 9800000 5600000 4300000 22000000 as volume
);

// 查看表内容
select * from kline;
```

### 查看表结构

```dolphindb
// 查看表的 schema（结构描述）
schema(kline).colDefs;

// 查看列名
kline.colNames();
// 输出: ["sym","trade_date","open","high","low","close","volume"]

// 查看行数
kline.size();
// 输出: 5
```

| 列名 | 数据类型 | 示例值 |
|------|---------|--------|
| sym | SYMBOL | 000001 |
| trade_date | DATE | 2024.01.02 |
| open | DOUBLE | 15.20 |
| high | DOUBLE | 15.85 |
| low | DOUBLE | 15.10 |
| close | DOUBLE | 15.67 |
| volume | INT | 12500000 |

## 4.3 执行第一个 SQL 查询

DolphinDB 支持标准 SQL 语法，可以对表执行各种查询：

```dolphindb
// 查询 000001 的数据
select * from kline where sym = `000001;

// 计算每只股票的日收益率
select sym, trade_date, 
       (close - open) / open * 100 as daily_return_pct,
       close, volume
from kline
order by sym, trade_date;

// 计算统计信息
select sym,
       avg(close) as avg_close,
       max(close) as max_close,
       min(close) as min_close,
       sum(volume) as total_volume
from kline
group by sym;
```

### SQL 查询结果示例

```
sym     avg_close  max_close  min_close  total_volume
------  ---------  ---------  ---------  ------------
000001  15.695     15.72      15.67      22,300,000
000002  22.85      22.90      22.80      9,900,000
000003  8.55       8.55       8.55       22,000,000
```

## 4.4 脚本文件管理

### 保存脚本

在 VSCode 中将编写好的脚本保存为 `.dos` 文件（DolphinDB Script 的标准扩展名）：

```
my_first_script.dos
```

### 运行脚本

在 VSCode 或 Web Console 中可以通过以下方式运行脚本：

```dolphindb
// 运行指定路径的脚本文件
run("/path/to/script/my_first_script.dos");
```

### 模块化开发

随着代码复杂度增加，良好的文件组织变得重要。推荐的项目结构：

```
project/
├── init.dos              // 初始化脚本（连接、配置）
├── create_tables.dos     // 建库建表脚本
├── import_data.dos       // 数据导入脚本
├── factors/              // 因子计算脚本
│   ├── momentum.dos
│   └── reversal.dos
├── strategies/           // 策略脚本
│   └── ma_crossover.dos
└── utils/                // 工具函数
    └── helper.dos
```

## 4.5 常见问题排查

### 新手常见错误

```dolphindb
// 错误 1：引号混用
sym = "000001;   // 错误：使用了双引号
sym = `000001;    // 正确：SYMBOL 类型用反引号

// 错误 2：忘记分号
a = 1 + 2        // 有时可以，但不规范
a = 1 + 2;       // 规范写法

// 错误 3：整数除法
5 / 2;           // 输出: 2（整数除法截断）
5.0 / 2;         // 输出: 2.5（强制浮点）

// 错误 4：SYMBOL 大小写敏感
select * from t where sym = `000001;   // 正确
select * from t where sym = `000001;   // `000001 ≠ `000002
```

### 变量清除

```dolphindb
// 清除单个变量
undef("x");

// 清除所有用户定义的变量
undef(all=true);

// 清除所有会话变量（恢复初始状态）
clearAllVars();
```

> **学习检查清单**：完成本节后，你应该能够：(1) 启动 DolphinDB 并成功连接；(2) 执行基本的加减乘除运算；(3) 用 `table` 创建一张内存表；(4) 对表执行 SELECT 查询；(5) 理解向量化运算的基本概念。这些是后续所有学习的基础。
