## 2.1 变量与赋值

### 变量声明

DolphinDB 的变量是**动态类型**的，声明时无需指定类型，类型由赋值内容自动推断：

```dolphindb
x = 100;                    // x 自动成为 INT 类型
x = 3.14;                   // x 重新赋值为 DOUBLE 类型（类型可变）
x = `000001;                // x 变为 SYMBOL 类型
```

### 全局变量 vs 局部变量

DolphinDB 使用 `=` 和 `= ` 来区分变量作用域：

```dolphindb
// 全局变量：使用 =（注意 = 后面没有空格）
global_var = 100;

// 局部变量：使用  =（注意 = 后面有空格）
local_var = 200;

// 在函数内部
def myFunc() {
    x = 10;        // x 前有空白 → 局部变量
    y = 20;        // y 前没有空白 → 若 global_var 未定义则为局部变量
    return x + y;
}

// 显式声明
global_x = 100;             // 明确全局（可在任何位置访问）
local_y = 200;              // 明确局部（仅当前作用域）
```

> **区分规则记忆**：`=` 前有空格 → 局部变量（仅在当前 {} 内有效）；`=` 前没有空格 → 全局变量（全局可访问）。这是 DolphinDB 独特且容易混淆的设计，建议在代码中统一使用 `= ` 风格来减少命名冲突。

### 变量信息查询

```dolphindb
// 列出所有已定义的变量
objs();

// 列出所有用户定义的变量
objs(true);

// 删除变量
undef("x");

// 删除所有变量
undef(all=true);
```

## 2.2 条件语句：if-else

### 基本语法

```dolphindb
if(condition) {
    // 条件为真时执行
} else if(anotherCondition) {
    // 另一个条件为真时执行
} else {
    // 以上条件都不满足时执行
}
```

### 示例

```dolphindb
price = 15.50;
signal = 1;   // 1=买入, -1=卖出, 0=持有

if(signal == 1) {
    action = "买入";
    quantity = 1000;
} else if(signal == -1) {
    action = "卖出";
    quantity = 500;
} else {
    action = "持有";
    quantity = 0;
}

print("操作: " + action + ", 数量: " + string(quantity));
```

### 向量化的条件判断

DolphinDB 提供了 `iif` 函数和 `case when` 语句来对向量进行条件判断，性能远优于循环：

```dolphindb
// iif(condition, trueResult, falseResult)
prices = 15.50 22.80 8.35 45.00 12.30;
level = iif(prices > 30, "高价", iif(prices > 10, "中价", "低价"));
// level: ["中价", "中价", "低价", "高价", "中价"]

// 等价于 for 循环写法（不推荐，性能差）
level2 = array(STRING, size(prices));
for(i in 0:size(prices)) {
    if(prices[i] > 30) level2[i] = "高价";
    else if(prices[i] > 10) level2[i] = "中价";
    else level2[i] = "低价";
}
```

### 三元运算符

```dolphindb
x = 10;
y = 20;
max_val = x > y ? x : y;     // 如果 x>y，取x；否则取y
// max_val = 20

// 向量化三元运算
a = 10 25 5 30;
b = 15 15 15 15;
c = a > b ? a : b;            // [15, 25, 15, 30]
```

## 2.3 循环语句

### for 循环

Python 程序员最容易上手的方式——遍历序列：

```dolphindb
// 遍历范围 i in start:end（注意：end 不包含）
for(i in 0:10) {
    print("i = " + string(i));
}
// 输出 i = 0, 1, 2, ..., 9

// 遍历序列
stocks = `AAPL`MSFT`GOOGL`AMZN;
for(sym in stocks) {
    print("正在处理: " + string(sym));
}

// for 循环索引访问 + 范围
n = size(prices);
for(i in 0:n) {
    print(string(i) + " : " + string(prices[i]));
}
```

### 数值 for 循环

```dolphindb
// 从 1 到 10（步长为1）
for(i in 1:11) { print(i); }      // 1, 2, ..., 10

// 带步长
for(i in 1.0:10.0 step 0.5) { print(i); }  // 1, 1.5, 2.0, ...
```

### do-while 循环

```dolphindb
// do { ... } while(condition);
x = 1;
sum = 0;
do {
    sum = sum + x;
    x = x + 1;
} while(x <= 10);
print(sum);   // 55
```

> **循环使用建议**：在 DolphinDB 中，**应优先使用向量化操作替代显式循环**。向量化操作在底层以 C++ 执行，比解释器执行的 for 循环快 100-1000 倍。只有在逻辑过于复杂无法向量化时，才退而使用 for 循环。

### 循环 vs 向量化对比

```dolphindb
// 场景：计算 1000 万个数每个是否有因子 3
n = 10000000;
values = rand(100000, n);

// 方式1：for 循环（不推荐）
timer {
    result = array(BOOL, n);
    for(i in 0:n) {
        result[i] = values[i] % 3 == 0;
    }
};
// 耗时：约 1-3 秒

// 方式2：向量化（推荐）
timer {
    result = values % 3 == 0;
};
// 耗时：约 0.05 秒  → 快 20-60 倍
```

## 2.4 其他控制流

### switch-case

```dolphindb
signal = 1;
switch(signal) {
    case 1: print("买入信号"); break;
    case -1: print("卖出信号"); break;
    default: print("无信号");
}
```

### break 与 continue

```dolphindb
// break：跳出循环
for(i in 0:100) {
    if(i > 5) break;
    print(i);
}
// 输出: 0, 1, 2, 3, 4, 5

// continue：跳过当前迭代
for(i in 0:10) {
    if(i % 2 == 0) continue;
    print(i);
}
// 输出: 1, 3, 5, 7, 9
```

## 2.5 实用控制流模式

### 模式 1：条件累积

```dolphindb
// 统计涨跌幅超过 5% 的天数
returns = 0.02 -0.06 0.07 -0.03 0.051 0.01;
count = 0;
for(ret in returns) {
    if(abs(ret) > 0.05) count = count + 1;
}
// 等价向量化写法：
// count = sum(abs(returns) > 0.05);
```

### 模式 2：状态机遍历

```dolphindb
// 追踪持仓状态（逻辑复杂时必须用循环）
prices = 10.0 10.5 9.8 10.2 11.0;
signal = 1 0 0 -1 0;
position = 0;
trade_log = table(array(SYMBOL, 0) as action, 
                  array(DOUBLE, 0) as price);
for(i in 0:size(prices)) {
    if(signal[i] == 1 && position == 0) {
        position = 1;
        trade_log.append!(table("买入" as action, prices[i] as price));
    } else if(signal[i] == -1 && position == 1) {
        position = 0;
        trade_log.append!(table("卖出" as action, prices[i] as price));
    }
}
select * from trade_log;
```
