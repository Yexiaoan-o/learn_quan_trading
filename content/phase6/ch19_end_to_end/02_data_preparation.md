## 数据准备

### 2.1 数据获取

首先，使用akshare库获取A股历史日线数据。以贵州茅台（600519.SH）为例：

```python
import akshare as ak
import pandas as pd
import numpy as np

# 获取个股日线历史数据
def fetch_stock_daily(symbol, start_date, end_date):
    """
    从akshare获取个股日线数据
    symbol: 股票代码，如 '600519'
    start_date: 起始日期 '20150101'
    end_date: 结束日期 '20231231'
    """
    df = ak.stock_zh_a_hist(
        symbol=symbol,
        period="daily",
        start_date=start_date,
        end_date=end_date,
        adjust="qfq"  # 前复权
    )
    return df

# 获取茅台数据
df_raw = fetch_stock_daily('600519', '20150101', '20231231')
print(f"原始数据形状: {df_raw.shape}")
print(df_raw.head())
print(f"\n数据列: {df_raw.columns.tolist()}")
```

> **复权说明**：`qfq`表示前复权（向前复权），即以当前价格为基准调整历史价格。前复权保持当前价格不变，历史价格按分红拆股比例调整，是回测中最常用的复权方式。

### 2.2 数据标准化

将数据列重命名为统一的英文列名，便于后续处理：

```python
# 标准化列名
column_mapping = {
    '日期': 'date',
    '开盘': 'open',
    '收盘': 'close',
    '最高': 'high',
    '最低': 'low',
    '成交量': 'volume',
    '成交额': 'amount',
    '振幅': 'amplitude',
    '涨跌幅': 'pct_chg',
    '涨跌额': 'change',
    '换手率': 'turnover'
}
df = df_raw.copy()
df.rename(columns=column_mapping, inplace=True)

# 转换日期格式
df['date'] = pd.to_datetime(df['date'])

# 按日期排序
df.sort_values('date', inplace=True)
df.reset_index(drop=True, inplace=True)

# 选取关键列
key_cols = ['date', 'open', 'high', 'low', 'close', 'volume', 'amount', 'turnover']
df = df[key_cols]

print(f"标准化后数据形状: {df.shape}")
print(df.head())
```

### 2.3 数据质量检查

在进入回测之前，必须进行严格的数据质量检查：

```python
def data_quality_check(df):
    """全面的数据质量检查"""
    report = {}

    # 1. 缺失值检查
    report['missing_values'] = df.isnull().sum().to_dict()
    report['total_missing'] = df.isnull().sum().sum()

    # 2. 重复日期检查
    report['duplicate_dates'] = df['date'].duplicated().sum()

    # 3. 日期连续性检查
    df_date = df.set_index('date')
    full_range = pd.date_range(df_date.index.min(), df_date.index.max(), freq='B')  # 交易日
    report['missing_dates'] = len(full_range.difference(df_date.index))
    report['total_trading_days'] = len(full_range)
    report['actual_days'] = len(df)

    # 4. 价格有效性检查
    report['price_negative'] = (df[['open','high','low','close']] <= 0).any().any()
    report['high_lt_low'] = (df['high'] < df['low']).sum()
    report['close_not_in_range'] = ((df['close'] < df['low']) | (df['close'] > df['high'])).sum()

    # 5. 异常值检查（单日涨跌幅超过涨跌停限制）
    df['returns'] = df['close'].pct_change()
    report['extreme_returns'] = (abs(df['returns']) > 0.11).sum()  # 略超涨跌停
    report['zero_volume'] = (df['volume'] <= 0).sum()

    # 6. 打印报告
    print("=" * 40)
    print("         数据质量检查报告           ")
    print("=" * 40)
    print(f"总交易日数: {report['actual_days']}")
    print(f"缺失日期数: {report['missing_dates']}")
    print(f"重复日期数: {report['duplicate_dates']}")
    print(f"总缺失值:   {report['total_missing']}")
    print(f"负价格检测: {report['price_negative']}")
    print(f"High<Low:    {report['high_lt_low']}")
    print(f"极端涨跌:   {report['extreme_returns']}")
    print(f"零成交量:   {report['zero_volume']}")
    print("=" * 40)

    return report

quality_report = data_quality_check(df)
```

### 2.4 数据清洗

根据质量检查结果，进行必要的数据清洗：

```python
def clean_data(df):
    """数据清洗处理"""
    df_clean = df.copy()

    # 1. 移除重复日期
    df_clean = df_clean.drop_duplicates(subset=['date'], keep='first')

    # 2. 设置日期为索引
    df_clean.set_index('date', inplace=True)

    # 3. 填充缺失交易日（前向填充）
    full_idx = pd.date_range(df_clean.index.min(), df_clean.index.max(), freq='B')
    df_clean = df_clean.reindex(full_idx)
    df_clean.fillna(method='ffill', inplace=True)
    df_clean.dropna(inplace=True)  # 移除开头可能的缺失

    # 4. 确保价格列数据类型为float64
    price_cols = ['open', 'high', 'low', 'close']
    df_clean[price_cols] = df_clean[price_cols].astype(np.float64)

    # 5. 成交量数据类型转换
    df_clean['volume'] = df_clean['volume'].astype(np.int64)

    print(f"清洗前数据行数: {len(df)}")
    print(f"清洗后数据行数: {len(df_clean)}")
    return df_clean

df_clean = clean_data(df)
```

### 2.5 DolphinDB数据存储

在Python端完成数据清洗后，将数据导入DolphinDB以实现高性能计算环境：

```
// ----- DolphinDB端：创建数据库和表 -----

// 1. 创建分布式数据库
dbDate = database("", VALUE, 2015.01.01..2026.01.01)
dbSymbol = database("", HASH, [SYMBOL, 10])
db = database("dfs://stock_daily", COMPO, [dbDate, dbSymbol])

// 2. 创建数据表结构
schema = table(
    1:0,
    `TradeDate`Symbol`Open`High`Low`Close`Volume`Amount`Turnover,
    [DATE, SYMBOL, DOUBLE, DOUBLE, DOUBLE, DOUBLE, LONG, DOUBLE, DOUBLE]
)

// 3. 创建分区表
db.createPartitionedTable(
    schema,
    `daily_bar,
    `TradeDate`Symbol
)

// 4. 从CSV导入数据（Python端导出CSV后）
// loadTextEx(
//     dbHandle=db,
//     tableName=`daily_bar,
//     partitionColumns=`TradeDate`Symbol,
//     filename="/data/stock_daily_600519.csv",
//     format=","
// )
```

### 2.6 数据准备小结

经过以上步骤，我们完成了：

| 步骤 | 操作 | 验证方式 |
|------|------|----------|
| 1. 数据获取 | 通过akshare获取日线数据 | 查看记录数和列名 |
| 2. 标准化 | 列名统一为英文 | 检查列名列表 |
| 3. 质量检查 | 缺失值、异常值检测 | 质量报告输出 |
| 4. 数据清洗 | 去重、补缺、类型转换 | 对比清洗前后行数 |
| 5. DolphinDB存储 | 创建数据库和分区表 | 查询表记录数 |

> **数据是量化交易的基石**。花在数据准备上的时间永远不会浪费。一个数据上的小错误，可能导致回测结果出现巨大偏差。严谨的数据准备是专业量化研究者的基本素养。
