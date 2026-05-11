# 量化交易学习平台

从零开始系统学习量化交易与 DolphinDB 数据库的交互式学习平台。

## 快速开始

```bash
pip install -r requirements.txt
python main.py
```

浏览器访问 **http://127.0.0.1:8000**

## 平台功能

- **知识讲解** — 6 阶段 19 章，从金融市场基础到 DolphinDB 实战
- **在线习题** — 选择题 / 判断题 / 代码填空 / 编程题，4 种题型
- **自动评分** — 即时判分 + 答案解析
- **学习进度** — 自动保存章节完成状态、习题成绩、学习时长
- **仪表盘** — 完成率、正确率、阶段进度可视化
- **学习笔记** — 每章可记录笔记
- **书签收藏** — 标记重点章节
- **全文搜索** — 支持中文关键词搜索
- **暗色模式** — 一键切换

## 课程路线

| 阶段 | 章节 | 内容 |
|------|------|------|
| 阶段一 | Ch1-Ch3 | 量化交易概述、Python 数据分析基础、金融市场知识 |
| 阶段二 | Ch4-Ch7 | DolphinDB 安装、建库建表、SQL 查询、编程语言 |
| 阶段三 | Ch8-Ch11 | 策略概论、均线/动量策略、均值回归、因子分析 |
| 阶段四 | Ch12-Ch14 | DolphinDB 时序处理、流计算、向量化编程 |
| 阶段五 | Ch15-Ch17 | 回测框架、风险管理、DolphinDB 回测引擎 |
| 阶段六 | Ch18-Ch19 | 金融因子实战、端到端综合案例 |

## 技术栈

| 层级 | 技术 |
|------|------|
| 后端 | Python 3 + FastAPI + SQLite |
| 前端 | Jinja2 模板 + 原生 HTML/CSS/JS |
| 内容 | Markdown + JSON 习题定义 |

## 项目结构

```
learn_quan_trading/
├── main.py              # FastAPI 入口
├── config.py            # 配置 & 课程章节定义
├── requirements.txt     # Python 依赖
├── content/             # 课程内容（Markdown + 习题 JSON）
│   ├── phase1/          # 阶段一（零基础入门）
│   ├── phase2/          # 阶段二（DolphinDB 入门）
│   ├── phase3/          # 阶段三（策略基础）
│   ├── phase4/          # 阶段四（DolphinDB 进阶）
│   ├── phase5/          # 阶段五（回测与风控）
│   └── phase6/          # 阶段六（综合实践）
├── database/
│   └── init_db.py       # SQLite 数据库初始化
├── services/
│   ├── content_service.py   # 课程内容加载 & Markdown 渲染
│   ├── grading_service.py   # 习题评分引擎
│   └── progress_service.py  # 进度、笔记、书签管理
├── routers/
│   ├── content.py       # 课程页面路由
│   ├── exercises.py     # 习题页面 & 提交 API
│   ├── progress.py      # 进度追踪 API
│   ├── notes.py         # 笔记 & 书签 API
│   └── search.py        # 全文搜索
├── templates/           # Jinja2 模板
│   ├── base.html        # 基础布局
│   ├── index.html       # 学习仪表盘
│   ├── chapter.html     # 章节阅读页
│   ├── exercise.html    # 习题练习页
│   ├── progress.html    # 学习进度页
│   ├── notes.html       # 学习笔记页
│   └── search.html      # 搜索结果页
└── static/
    ├── css/style.css    # 样式（含暗色模式）
    └── js/app.js        # 前端交互
```

## 数据持久化

所有学习数据自动保存在 `database/learning.db`（SQLite），包括：

- 章节阅读进度
- 习题作答记录 & 得分
- 学习笔记
- 书签
- 学习时长统计

删除该文件即可重置所有学习进度。
