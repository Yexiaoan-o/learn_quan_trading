## 配对交易（Pairs Trading）概论

配对交易是统计套利最经典的形式，由Morgan Stanley的量化团队在1980年代首创。其核心思想是：找到两只历史走势高度相关的股票，当它们的价差偏离正常范围时，做多被低估的、做空被高估的，等待价差回归后平仓获利。

### 配对交易的三步法

```
[配对筛选] → [价差建模] → [信号执行]
```

---

### 一、配对筛选 — 寻找"天生一对"

配对筛选的目标是找到具有长期稳定关系的股票对。优质配对通常满足：

1. **同行业**：基本面驱动因素相似
2. **高相关性**：历史价格走势高度一致
3. **协整关系**：统计上存在长期均衡

#### 方法1：相关性筛选

```python
import numpy as np
import pandas as pd
from scipy import stats
from statsmodels.tsa.stattools import coint, adfuller
from sklearn.linear_model import LinearRegression


def correlation_screening(returns_df, top_n=10):
    """
    基于收益率相关性的配对筛选
    
    参数:
        returns_df: 收益率DataFrame (行=日期, 列=股票)
        top_n: 保留的最高相关性对数
    """
    corr_matrix = returns_df.corr()
    
    # 提取上三角（每对只计一次）
    pairs = []
    n = len(corr_matrix.columns)
    
    for i in range(n):
        for j in range(i+1, n):
            stock_a = corr_matrix.columns[i]
            stock_b = corr_matrix.columns[j]
            corr = corr_matrix.iloc[i, j]
            
            pairs.append({
                'stock_a': stock_a,
                'stock_b': stock_b,
                'correlation': corr
            })
    
    pairs_df = pd.DataFrame(pairs)
    pairs_df = pairs_df.sort_values('correlation', ascending=False)
    
    return pairs_df.head(top_n)
```

#### 方法2：协整筛选（更严谨）

相关性高的股票并不一定有协整关系，而协整才是配对交易的真正基础。

```python
def cointegration_screening(price_df, significance=0.05, top_n=10):
    """
    基于协整检验的配对筛选
    
    使用两步法（Engle-Granger方法）：
    步骤1：做OLS回归 Y = α + βX + ε
    步骤2：对残差ε做ADF检验（如果平稳则协整）
    
    参数:
        price_df: 价格DataFrame
        significance: 显著性水平
        top_n: 保留的最佳配对数量
    """
    stocks = price_df.columns
    results = []
    
    for i in range(len(stocks)):
        for j in range(i+1, len(stocks)):
            stock_a, stock_b = stocks[i], stocks[j]
            
            y = price_df[stock_a].dropna()
            x = price_df[stock_b].dropna()
            
            # 对齐数据
            common_idx = y.index.intersection(x.index)
            y = y[common_idx]
            x = x[common_idx]
            
            if len(y) < 100:  # 最少100个数据点
                continue
            
            # Engle-Granger协整检验
            coint_t, p_value, _ = coint(y, x)
            
            if p_value < significance:
                # 计算对冲比率（OLS回归斜率）
                reg = LinearRegression()
                reg.fit(x.values.reshape(-1, 1), y.values)
                hedge_ratio = float(reg.coef_[0])
                
                # 计算价差 = Y - hedge_ratio * X
                spread = y.values - hedge_ratio * x.values
                
                # 价差的平稳性检验
                adf_result = adfuller(spread, autolag='AIC')
                
                # 价差的标准差和均值回复速度
                spread_std = np.std(spread)
                spread_mean = np.mean(spread)
                
                results.append({
                    'stock_a': stock_a,
                    'stock_b': stock_b,
                    'coint_pvalue': p_value,
                    'coint_tstat': coint_t,
                    'hedge_ratio': hedge_ratio,
                    'spread_std': spread_std,
                    'spread_mean': spread_mean,
                    'adf_pvalue': adf_result[1],
                })
    
    results_df = pd.DataFrame(results)
    # 按p值排序（越小越显著）
    results_df = results_df.sort_values('coint_pvalue')
    
    return results_df.head(top_n)
```

#### 方法3：距离法（简化版）

```python
def distance_screening(price_df, top_n=10):
    """
    基于标准化价格距离的配对筛选
    
    计算两只股票标准化价格的欧氏距离，距离越小越适合配对
    """
    # 标准化价格（归一化，消除量纲差异）
    normalized = (price_df - price_df.min()) / (price_df.max() - price_df.min())
    
    stocks = normalized.columns
    results = []
    
    for i in range(len(stocks)):
        for j in range(i+1, len(stocks)):
            a, b = stocks[i], stocks[j]
            
            # 计算标准化价格的欧氏距离
            diff = normalized[a] - normalized[b]
            sum_sq_diff = (diff ** 2).sum()
            
            # 距离的稳定性（距离变动越小越好）
            dist_vol = diff.std()
            
            results.append({
                'stock_a': a,
                'stock_b': b,
                'ssd': sum_sq_diff,
                'distance_vol': dist_vol,
                'score': sum_sq_diff + dist_vol  # 综合得分：越小越好
            })
    
    results_df = pd.DataFrame(results)
    return results_df.sort_values('score').head(top_n)
```

---

### 二、价差建模

确定了配对后，需要对价差进行建模来确定交易信号。

```python
class PairsTradingModel:
    """
    配对交易模型
    
    参数:
        prices_a: 股票A的价格序列
        prices_b: 股票B的价格序列
        lookback: 用于估计参数的滚动窗口
    """
    
    def __init__(self, prices_a, prices_b, lookback=120):
        self.prices_a = prices_a
        self.prices_b = prices_b
        self.lookback = lookback
        
    def estimate_hedge_ratio(self):
        """
        估计对冲比率（滚动窗口）
        
        通过对 rolling(window) 内的数据做 OLS 回归
        Y_a = α + β * Y_b + ε
        
        β 即为对冲比率
        """
        # 对齐索引
        common_idx = self.prices_a.index.intersection(self.prices_b.index)
        a = self.prices_a[common_idx]
        b = self.prices_b[common_idx]
        
        self.hedge_ratios = pd.Series(index=common_idx, dtype=float)
        self.intercepts = pd.Series(index=common_idx, dtype=float)
        
        for i in range(self.lookback, len(common_idx)):
            y = a.iloc[i-self.lookback:i].values
            x = b.iloc[i-self.lookback:i].values
            
            # OLS回归
            X = np.column_stack([np.ones(len(x)), x])
            coef = np.linalg.lstsq(X, y, rcond=None)[0]
            
            self.hedge_ratios.iloc[i] = coef[1]
            self.intercepts.iloc[i] = coef[0]
    
    def calculate_spread(self):
        """
        计算价差序列
        spread = A - hedge_ratio * B
        """
        common_idx = self.prices_a.index.intersection(self.prices_b.index)
        
        self.spread = pd.Series(index=common_idx, dtype=float)
        
        for i in range(self.lookback, len(common_idx)):
            idx = common_idx[i]
            self.spread[i] = (self.prices_a[idx] - 
                              self.hedge_ratios[idx] * self.prices_b[idx])
    
    def calculate_zscore(self, window=20):
        """
        计算价差的Z-score
        
        Z-score = (spread - rolling_mean(spread)) / rolling_std(spread)
        """
        rolling_mean = self.spread.rolling(window).mean()
        rolling_std = self.spread.rolling(window).std()
        
        self.zscore = (self.spread - rolling_mean) / rolling_std
        
        return self.zscore
    
    def generate_signals(self, entry_threshold=2.0, exit_threshold=0.5):
        """
        生成交易信号
        
        当Z-score超过entry_threshold时入场
        当Z-score回到exit_threshold以内时出场
        """
        signals = pd.Series(0, index=self.zscore.index)
        positions = pd.Series(0, index=self.zscore.index)
        
        in_position = False
        position_sign = 0
        
        for i in range(len(signals)):
            z = self.zscore.iloc[i]
            
            if not in_position:
                if z > entry_threshold:
                    # 价差过高：A高估，B低估 → 做空A，做多B（空spread）
                    signals.iloc[i] = -1
                    positions.iloc[i] = -1
                    in_position = True
                    position_sign = -1
                elif z < -entry_threshold:
                    # 价差过低：A低估，B高估 → 做多A，做空B（多spread）
                    signals.iloc[i] = 1
                    positions.iloc[i] = 1
                    in_position = True
                    position_sign = 1
            
            else:
                # 检查出场条件
                if position_sign > 0 and z >= -exit_threshold:
                    # 多头spread，价差回归了
                    signals.iloc[i] = 0
                    positions.iloc[i] = 0
                    in_position = False
                elif position_sign < 0 and z <= exit_threshold:
                    # 空头spread，价差回归了
                    signals.iloc[i] = 0
                    positions.iloc[i] = 0
                    in_position = False
                elif abs(z) > entry_threshold * 1.5:
                    # 止损：价差继续扩大
                    signals.iloc[i] = 0
                    positions.iloc[i] = 0
                    in_position = False
                else:
                    positions.iloc[i] = positions.iloc[i-1]
        
        return signals, positions
```

---

### 三、配对交易的回测与风险管理

```python
def pairs_trading_backtest(prices_a, prices_b, hedge_ratios, 
                            signals, initial_capital=100000):
    """
    配对交易回测
    """
    common_idx = prices_a.index.intersection(prices_b.index)
    
    capital = initial_capital
    pos_a = 0  # 股票A持仓
    pos_b = 0  # 股票B持仓
    
    portfolio_values = []
    daily_pnl = []
    
    for i in range(len(common_idx)):
        idx = common_idx[i]
        signal = signals.loc[idx]
        pa = prices_a.loc[idx]
        pb = prices_b.loc[idx]
        hr = hedge_ratios.loc[idx] if idx in hedge_ratios.index else 1.0
        
        if signal == 1 and pos_a == 0:
            # 开多spread：买入A，卖出B
            # 标准化仓位：对冲数量比
            capital_per_leg = capital * 0.5
            pos_a = capital_per_leg / pa      # 买入A的股数
            pos_b = -(capital_per_leg) / pb    # 卖出B的股数（负数表示空头）
            
            # 调整B的仓位以匹配对冲比率
            # 使组合市值中性: pos_a * pa = hr * abs(pos_b) * pb
            pos_b = -(pos_a * pa) / (hr * pb) * pb / pb  # 保持金额匹配
            
        elif signal == -1 and pos_a == 0:
            # 开空spread：卖出A，买入B
            capital_per_leg = capital * 0.5
            pos_a = -(capital_per_leg) / pa
            pos_b = (capital_per_leg) / pb
            
        elif signal == 0 and pos_a != 0:
            # 平仓
            pnl_a = pos_a * pa
            pnl_b = pos_b * pb
            capital += pnl_a + pnl_b
            pos_a = 0
            pos_b = 0
        
        # 每日组合价值 = 现金 + 持仓市值
        pv = capital + pos_a * pa + pos_b * pb
        portfolio_values.append(pv)
        
        if i > 0:
            daily_pnl.append(pv - portfolio_values[i-2])
    
    return portfolio_values, daily_pnl
```

---

### 四、配对交易的风险

| 风险类型 | 描述 | 应对措施 |
|----------|------|----------|
| **基本面变化** | 一只股票发生重大基本面变化，协整关系破裂 | 定期重新筛选配对，设置最大持仓期限 |
| **流动性风险** | 做空的股票可能难以借到 | 只交易高流动性的股票 |
| **模型风险** | 对冲比率不稳定 | 定期重新估计（每日或每周） |
| **发散风险** | 价差持续扩大不回归 | 强制止损（如3个标准差） |

> **配对交易的核心智慧**：配对交易本质上在赌"历史会重演"——过去协整的两只股票未来也会协整。但这个假设可能被基本面的突变打破。因此，专业交易者在价差偏离加大时会加仓（平均法），但绝不无限加仓。设定总体的风险上限，是配对交易生存的关键。
