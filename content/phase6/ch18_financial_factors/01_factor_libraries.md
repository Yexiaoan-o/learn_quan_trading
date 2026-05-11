## DolphinDB因子库概述

### 1.1 因子库简介

DolphinDB内置了多个专业的金融因子计算模块，覆盖技术指标、阿尔法因子和运行维护等核心功能。这些模块由DolphinDB官方或社区贡献，经过性能优化和正确性验证，可以直接在策略开发中调用。

通过内置因子库，开发者无需从零实现复杂的指标计算，大幅提升策略开发效率：

```
// 加载因子模块
use ta
use gtja191Alpha

// 直接调用模块中的函数
macd_result = ta::macd(close, 12, 26, 9)  // 一行代码完成MACD计算
```

### 1.2 TA模块（技术分析）

TA（Technical Analysis）模块是DolphinDB最常用的因子模块，包含60多种技术分析指标，覆盖五大类别：

| 类别 | 指标数量 | 代表指标 |
|------|:---:|------|
| 趋势指标 | 15+ | MACD, ADX, SAR, SuperTrend |
| 震荡指标 | 20+ | RSI, KDJ, CCI, Williams %R |
| 均线指标 | 10+ | SMA, EMA, WMA, HMA, KAMA |
| 波动指标 | 8+ | ATR, Bollinger Bands, Donchian |
| 量价指标 | 10+ | OBV, MFI, VWAP, AD |

**使用方式**：

```
use ta  // 加载TA模块

// 基本用法
rsi14 = ta::rsi(close, 14)                    // RSI(14)
macd = ta::macd(close, 12, 26, 9)             // MACD标准参数
bb = ta::bollingerBands(close, 20, 2)         // 布林带(20,2)
sma20 = ta::sma(close, 20)                    // 简单移动平均
ema20 = ta::ema(close, 20)                    // 指数移动平均
```

### 1.3 MyTT模块（麦语言指标）

MyTT（My Technical Tools）模块实现了中文量化社区"麦语言"体系的技术指标，为熟悉通达信、文华财经等平台的用户提供了熟悉的计算接口：

```
use mytt

// 麦语言风格指标
ma20 = mytt::ma(close, 20)              // 简单移动平均
hhv20 = mytt::hhv(high, 20)             // 20日最高价
llv20 = mytt::llv(low, 20)              // 20日最低价
cross = mytt::cross(ma5, ma20)          // 均线交叉信号
barslast = mytt::barslast(condition)    // 上次条件成立以来的Bar数
ref = mytt::ref(close, 1)              // 前一日收盘价
```

MyTT模块的特点：
- 函数命名与通达信、文华财经高度一致
- 适合将传统交易系统的公式直接迁移到DolphinDB
- 覆盖了A股技术分析中最常用的工具函数

### 1.4 GTJA191Alpha模块（国泰君安191因子）

GTJA191Alpha模块是基于国泰君安证券研究所发布的《基于短周期量价数据的多因子选股策略》研报，实现了著名的191个Alpha因子。

这些因子的核心思路是从股价的量价关系中挖掘超额收益信号：

```
use gtja191Alpha

// 调用Alpha001因子（日内反转因子）
alpha001 = gtja191Alpha::alpha001(open, close, volume)

// Alpha002因子
alpha002 = gtja191Alpha::alpha002(open, high, low, close, volume, returns)

// 批量计算多个因子
factors = select
    gtja191Alpha::alpha001(open, close, volume) as alpha001,
    gtja191Alpha::alpha002(open, high, low, close, volume, returns) as alpha002,
    gtja191Alpha::alpha003(high, volume) as alpha003
from dailyData
context by Symbol
```

**191因子涵盖的因子类型**：
- 反转类因子（短期反转、日内反转）
- 动量类因子（价格动量、成交量动量）
- 波动类因子（波动率变化、振幅）
- 相关性因子（价量相关、行业相关）
- 流动性因子（换手率变化、成交量变化）

### 1.5 WQ101Alpha模块（WorldQuant 101因子）

WQ101Alpha模块实现了WorldQuant发布的101个公式化Alpha因子，是全球量化投资领域的经典参考：

```
use wq101alpha

// Alpha001: 年初至今收益排名
alpha001 = wq101alpha::alpha001(close, returns)

// Alpha006: 成交量与收益率相关性
alpha006 = wq101alpha::alpha006(open, volume)
```

> **注意**：WorldQuant的因子公式是基于美股市场开发的，在A股市场使用时需要验证有效性和做适当调整。

### 1.6 OPS模块（运维工具）

OPS模块与因子计算直接相关，提供了因子维护和管理的基础功能：

| 功能 | 说明 | 示例 |
|------|------|------|
| 数据更新 | 每日自动更新因子值 | `ops::updateFactors()` |
| 异常监控 | 检测因子值的异常波动 | `ops::checkFactorQuality()` |
| 版本管理 | 追踪因子计算逻辑变化 | `ops::factorVersion()` |
| 性能监控 | 监控因子计算耗时 | `ops::performanceLog()` |

### 1.7 模块加载与依赖管理

在使用因子模块前，需要在脚本开头进行模块声明：

```
// 加载所需因子模块
use ta               // 技术分析指标
use gtja191Alpha     // 国泰君安191因子
use wq101alpha       // WorldQuant 101因子
use mytt             // 麦语言指标

// 也可以按需加载，避免命名冲突
use ta as ta_module
use gtja191Alpha as gtja

// 带命名空间的调用
rsi14 = ta_module::rsi(close, 14)
alpha01 = gtja::alpha001(open, close, volume)
```

### 1.8 因子库性能优势

DolphinDB因子库的性能优势显著：

| 对比维度 | 传统Python实现 | DolphinDB因子库 | 提升倍数 |
|----------|:---:|:---:|:---:|
| 单股MACD | ~5ms | <0.1ms | 50x+ |
| 500股MACD | ~2s | <0.05s | 40x+ |
| 191因子全量(500股) | ~30s+ | <0.5s | 60x+ |
| WorldQuant 101因子 | ~60s+ | <1s | 60x+ |

性能优势源于：
1. **C++底层实现**：所有因子计算函数均用C++编写
2. **向量化计算**：充分利用DolphinDB的向量化引擎
3. **内存优化**：避免不必要的数据拷贝
4. **分布式并行**：多标的计算自动并行化

> **最佳实践**：因子探索阶段可以用Python快速验证想法，但正式的回测和生产环境建议使用DolphinDB因子库，以发挥性能优势。两者可以通过DolphinDB Python API无缝集成。
