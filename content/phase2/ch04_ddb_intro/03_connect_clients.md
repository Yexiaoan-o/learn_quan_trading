## 3.1 可用客户端概览

DolphinDB 提供了多种客户端工具，满足不同使用场景的开发需求：

```
┌───────────────────────────────────────────────────────────┐
│                DolphinDB 客户端生态                         │
│                                                           │
│  ┌──────────────┐  ┌──────────┐  ┌──────────────────────┐ │
│  │ VSCode 插件   │  │ Web Console│  │ Java GUI (DolphinDB │ │
│  │ (推荐首选)     │  │ (浏览器)   │  │ GUI)                 │ │
│  └──────────────┘  └──────────┘  └──────────────────────┘ │
│                                                           │
│  ┌──────────────────────┐  ┌──────────────────────┐      │
│  │ DolphinDB Terminal   │  │ Jupyter Notebook     │      │
│  │ (命令行终端)          │  │ (Python内核支持)      │      │
│  └──────────────────────┘  └──────────────────────┘      │
│                                                           │
│  ┌──────────────────────┐                                │
│  │ Python API / C++ API │  ← 程序化连接                   │
│  │ Java API / C# API    │                                │
│  └──────────────────────┘                                │
└───────────────────────────────────────────────────────────┘
```

| 客户端 | 安装方式 | 优势 | 推荐度 |
|--------|---------|------|--------|
| **VSCode Extension** | VSCode 插件市场搜索 "DolphinDB" | 代码补全、语法高亮、变量监视 | ★★★★★ |
| **Web Console** | 浏览器访问 8848 端口 | 无需安装，即开即用 | ★★★★☆ |
| **Java GUI** | 下载 DolphinDB GUI JAR 文件 | 成熟的桌面客户端 | ★★★☆☆ |
| **DolphinDB Terminal** | 安装包自带 | 轻量，脚本执行 | ★★★☆☆ |
| **Jupyter Notebook** | pip install dolphindb | 可混合 Python 分析 | ★★★★☆ |

### 推荐策略

- **学习期**：Web Console（零安装）→ VSCode Extension（深入学习）
- **开发期**：VSCode Extension（代码编写）+ Web Console（快速验证）
- **生产期**：Python API / C++ API（程序化调用）

## 3.2 Web Console 连接详解

Web Console 是 DolphinDB 最易上手的客户端，零安装，浏览器直接访问。

### 连接步骤

```
步骤 1: 启动 DolphinDB 服务 → 看到日志 "Server started on port 8848"
步骤 2: 打开浏览器 → 输入 http://localhost:8848
步骤 3: 选择登录方式 → 输入账号密码，或选择匿名登录
```

### 登录方式对比

Web Console 提供两种登录模式：

| 特性 | 管理员登录 | 匿名登录（Guest） |
|------|----------|-----------------|
| 默认账号密码 | admin / 123456 | 无需输入 |
| 权限范围 | 完整管理权限 | 受限（只能查询） |
| 能否写数据 | ✓ | ✗（只读） |
| 能否管理数据库 | ✓ | ✗ |
| 适用场景 | 开发和管理 | 仅浏览数据 |

### 登录界面说明

当首次访问 `http://localhost:8848` 时，会看到登录页面：

```
┌─────────────────────────────────┐
│     DolphinDB Web Console       │
│                                 │
│  Username: [   admin    ]       │
│  Password: [  ********  ]       │
│                                 │
│  [  Login  ]  [ Login as Guest ]│
│                                 │
│  ─────────────────────────────  │
│  首次登录默认账户:               │
│  Username: admin                │
│  Password: 123456               │
└─────────────────────────────────┘
```

### 登录后界面

登录成功后进入 Web Console 主界面：

- **左侧**：数据库资源管理器（显示 `dfs://` 下的数据库和表）
- **右侧上部**：脚本编辑器（编写和执行 DolphinDB 脚本）
- **右侧下部**：结果输出区（显示查询结果、变量值、日志信息）

```dolphindb
// 登录后在编辑器中输入以下命令测试连接
print("Hello DolphinDB! 连接成功！")

// 查看当前用户
currentUser();

// 查看 server 版本信息
version();
```

> **务必修改默认密码**：生产环境中 `admin/123456` 是非常危险的安全隐患。使用 `changePwd("新密码")` 命令修改管理员密码。

## 3.3 VSCode 插件（推荐）

VSCode 插件是 DolphinDB 开发的首选工具，提供专业 IDE 级别的体验。

### 安装步骤

1. 在 VSCode 中打开扩展市场（Ctrl+Shift+X）
2. 搜索 **DolphinDB**
3. 点击安装 "DolphinDB" 官方插件
4. 安装完成后，VSCode 左侧出现 DolphinDB 图标

### 连接配置

安装插件后，创建连接配置：

```json
// 在 VSCode 设置中配置 DolphinDB 连接
{
    "dolphindb.connections": [
        {
            "name": "本地服务",
            "host": "localhost",
            "port": 8848,
            "username": "admin",
            "password": "123456"
        }
    ]
}
```

| 功能 | 说明 |
|------|------|
| 语法高亮 | DolphinDB 关键字、函数、类型自动着色 |
| 代码补全 | 输入函数名时自动提示（如 `select`、`loadTable` 等） |
| 变量监视 | 查看当前会话中所有变量及其值和类型 |
| 执行选定 | 选中代码按 Ctrl+Enter 执行，结果直接显示 |
| 多文件管理 | 管理 `.dos` 脚本文件（DolphinDB 脚本扩展名） |

### VSCode 插件 vs Web Console

| 维度 | VSCode 插件 | Web Console |
|------|-----------|-------------|
| 代码编辑体验 | 优秀（语法高亮+补全+大纲） | 基础 |
| 多文件管理 | 支持 | 不支持 |
| 版本控制 | 集成 Git | 无 |
| 启动成本 | 需要安装 VSCode + 插件 | 浏览器即用 |
| 性能 | 良好 | 良好 |
| 适合场景 | 系统开发、项目编码 | 临时查询、演示 |

## 3.4 Jupyter Notebook 连接

对于 Python 用户，DolphinDB 提供了 Python API，可以在 Jupyter Notebook 中连接和操作 DolphinDB。

```python
# 安装 DolphinDB Python API
# pip install dolphindb

import dolphindb as ddb

# 创建连接
s = ddb.session()
s.connect("localhost", 8848, "admin", "123456")

# 执行 DolphinDB 脚本
result = s.run("""
    t = table(1..5 as id, rand(100.0, 5) as value)
    select * from t
""")
print(result)

# 也可以通过 SQL 直接查询
stock_data = s.run("select top 10 * from loadTable('dfs://market', 'kline_day')")
print(stock_data)
```

### Jupyter 使用场景

Jupyter Notebook 特别适合：
- 将 DolphinDB 查询结果与 Python 的可视化库（Matplotlib、Plotly）结合
- 数据分析/研究报告的编写
- DolphinDB 不擅长的机器学习和统计建模（利用 Python 生态）

> Jupyter Notebook 的 DolphinDB 内核目前功能有限，建议通过 Python API 间接使用，而非完全替代原生脚本。

## 3.5 多客户端协作工作流

实际开发中的典型工作流：

```
1. VSCode 编写策略脚本    → 保存 .dos 文件
2. Web Console 快速调试   → 验证小段代码逻辑
3. Jupyter 可视化分析     → 将结果图表化展示
4. Python API 实盘调用    → 生产环境自动化执行
```

> **最佳实践**：将策略的核心计算逻辑放在 DolphinDB 中执行（利用其高性能），将策略的调度、可视化和非时间敏感的计算放在 Python 中处理。两端通过 DolphinDB Python API 进行数据流转。
