## 多因子模型构建

单个因子的预测能力有限且不稳定，多因子模型通过组合多个有效因子，构建更稳健和全面的选股体系。本节介绍多因子模型的构建方法和加权策略。

---

### 一、为什么需要多因子模型

| 问题 | 单因子的局限 | 多因子的优势 |
|------|-------------|-------------|
| 因子轮动 | 单一因子在某些市场环境下失效 | 多个因子互相补充，降低策略失效概率 |
| 信息覆盖 | 只利用一类信息（如仅估值） | 综合价值、动量、质量等多维信息 |
| 拥挤风险 | 单因子容易过度拥挤而衰减 | 多因子分散了信号来源 |
| 稳定性 | IC波动大，回撤剧烈 | 多个因子平滑收益曲线，提升IR |

---

### 二、多因子合成方法

#### 2.1 等权加权

最简单的合成方式：将每个因子标准化后取等权重平均。

```python
def equal_weight_composite(factors_dict):
    """
    等权合成多因子

    参数:
        factors_dict: {因子名称: 因子值DataFrame}
    返回:
        composite: 合成因子值
    """
    composites = []

    for name, factor_df in factors_dict.items():
        # 步骤1：去极值（3倍标准差Winsorize）
        factor_clean = factor_df.copy()
        mean, std = factor_clean.mean(), factor_clean.std()
        factor_clean = factor_clean.clip(mean - 3 * std, mean + 3 * std)

        # 步骤2：标准化（Z-score）
        factor_zscore = (factor_clean - factor_clean.mean()) / factor_clean.std()

        # 步骤3：处理方向（确保高因子值 = 高预期收益）
        factor_zscore = factor_zscore * (1 if factor_is_positive(name) else -1)

        composites.append(factor_zscore)

    # 等权加总
    composite = sum(composites) / len(composites)

    return composite


def factor_is_positive(factor_name):
    """
    判断因子方向：因子值高是否意味着高未来收益

    正值IC因子：因子值越高→预期收益越高（如ROE、动量）
    负值IC因子：因子值越低→预期收益越高（如PE、波动率）
    """
    positive_factors = {'ROE', '动量', '毛利率', '股息率'}
    negative_factors = {'PE', 'PB', '波动率', '资产负债率'}

    if factor_name in positive_factors:
        return True
    elif factor_name in negative_factors:
        return False
    return True
```

#### 2.2 IC加权

根据各因子的历史IC表现来分配权重——IC越稳定、越高的因子获得更大权重：

```python
def ic_weighted_composite(factors_dict, ic_scores, lookback=12):
    """
    IC加权合成因子：历史IC越高的因子权重越大

    参数:
        factors_dict: {因子名称: 因子值DataFrame}
        ic_scores: {因子名称: IC均值}
        lookback: IC计算回溯期（月）
    """
    # 只保留IC为正的因子
    valid_factors = {k: v for k, v in ic_scores.items() if v > 0}

    if not valid_factors:
        raise ValueError("没有IC为正的因子！")

    total_ic = sum(valid_factors.values())
    weights = {name: ic / total_ic for name, ic in valid_factors.items()}

    composite = 0
    for name, factor_df in factors_dict.items():
        if name in weights:
            factor_zscore = (factor_df - factor_df.mean()) / factor_df.std()
            composite += weights[name] * factor_zscore

    return composite, weights
```

#### 2.3 回归加权与Fama-MacBeth方法

Fama-MacBeth回归是学术界最经典的多因子检验方法，分两步进行：

**第一步（时间序列回归）**：对每只股票，用历史数据回归得到其因子暴露Beta：
```
R_it - R_ft = α_i + β_i1 × Factor1_t + β_i2 × Factor2_t + ... + ε_it
```

**第二步（横截面回归）**：在每个截面上，用第一步得到的Beta去解释股票的横截面收益差异：
```
R_i - R_f = λ_0 + λ_1 × β_i1 + λ_2 × β_i2 + ... + u_i
```
其中λ是各因子的风险溢价（因子收益率）。

```python
def fama_macbeth_regression(returns_df, factor_betas, n_lags=60):
    """
    简化的Fama-MacBeth回归

    参数:
        returns_df: 股票收益率DataFrame
        factor_betas: 因子暴露DataFrame（行=日期，列=股票）
    """
    lambda_series = []

    dates = sorted(returns_df.index)
    for t, date in enumerate(dates):
        # 横截面回归：ret = λ0 + Σ λ_k × beta_k
        returns = returns_df.loc[date]
        X_data = []

        for k, beta_df in enumerate(factor_betas):
            if date in beta_df.index:
                X_data.append(beta_df.loc[date].values)

        if not X_data:
            continue

        X = np.column_stack([np.ones(len(X_data[0]))] + X_data)
        y = returns.values

        valid = ~np.isnan(y)
        for col in range(X.shape[1]):
            valid = valid & ~np.isnan(X[:, col])

        if valid.sum() < 20:
            continue

        coef = np.linalg.lstsq(X[valid], y[valid], rcond=None)[0]
        lambda_series.append([date] + list(coef))

    columns = ['date'] + [f'lambda_{k}' for k in range(len(factor_betas) + 1)]
    lambda_df = pd.DataFrame(lambda_series, columns=columns).set_index('date')

    # 计算各因子风险溢价的均值和t值
    for col in lambda_df.columns:
        mean_lambda = lambda_df[col].mean() * 252
        t_stat = lambda_df[col].mean() / \
                 (lambda_df[col].std() / np.sqrt(len(lambda_df)))
        print(f"{col}: 年化λ={mean_lambda:.4f}, t值={t_stat:.2f}")

    return lambda_df
```

> **Fama-MacBeth方法的意义**：它不仅给出各因子的预期收益贡献，还提供了统计检验（t值），帮助我们判断哪些因子真正具有显著的风险溢价。

---

### 三、因子相关性管理

多因子建模中，因子之间的高度相关性（共线性）是一大挑战：如果两个因子高度相关，合并它们不会增加新信息，反而会增加噪声。

```python
def factor_correlation_matrix(factors_dict):
    """
    计算因子间的相关性矩阵
    """
    factor_names = list(factors_dict.keys())
    n = len(factor_names)
    corr_matrix = np.zeros((n, n))

    for i in range(n):
        for j in range(n):
            f1 = factors_dict[factor_names[i]].values.flatten()
            f2 = factors_dict[factor_names[j]].values.flatten()

            valid = ~(np.isnan(f1) | np.isnan(f2))
            corr_matrix[i, j] = np.corrcoef(f1[valid], f2[valid])[0, 1]

    return pd.DataFrame(corr_matrix, index=factor_names, columns=factor_names)


def select_uncorrelated_factors(factors_dict, max_corr=0.7):
    """
    选择相关性较低的因子子集，避免共线性

    贪心算法：从IC最高的因子开始，逐个加入低相关的因子
    """
    corr = factor_correlation_matrix(factors_dict)
    selected = []
    remaining = list(factors_dict.keys())

    while remaining:
        candidate = remaining.pop(0)
        # 检查与已选因子的相关性
        is_uncorrelated = all(
            abs(corr.loc[candidate, s]) < max_corr for s in selected
        )
        if is_uncorrelated:
            selected.append(candidate)

    return selected
```

### 四、多因子策略架构

```
                        ┌─────────────┐
   财务数据 ──────────→ │  价值因子    │ ──┐
                        └─────────────┘   │
                        ┌─────────────┐   │    ┌──────────┐    ┌──────────┐
   价量数据 ──────────→ │  动量因子    │ ──┼──→ │ 因子合成  │ ─→ │ 选股信号  │
                        └─────────────┘   │    └──────────┘    └──────────┘
                        ┌─────────────┐   │
   质量数据 ──────────→ │  质量因子    │ ──┘
                        └─────────────┘
```

> **构建原则**：多因子模型的质量取决于三个要素——(1) 每个单因子本身的有效性（IC显著为正），(2) 因子之间的低相关性（提供独立信息），(3) 加权方式的合理性（反映因子真实预测能力）。切忌堆砌大量高相关因子，看起来热闹，实际上是"虚假的多样化"。
