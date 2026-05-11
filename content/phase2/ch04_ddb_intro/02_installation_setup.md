## 2.1 下载 DolphinDB

### 官方下载渠道

DolphinDB 提供社区版（免费）和商业版（授权）两个版本。对于学习和非商业用途，社区版完全满足需求。

| 版本 | 适用场景 | 限制 |
|------|---------|------|
| 社区版（Community） | 学习、个人项目 | 单节点，部分高级功能受限 |
| 商业版（Enterprise） | 企业生产环境 | 需购买License，集群部署 |

**下载地址**：访问 DolphinDB 官网下载对应操作系统的安装包。通常提供 Linux（.zip/.tar.gz）和 Windows（.zip）两个版本。

### 下载前检查系统环境

最低配置要求：

| 组件 | 最低要求 | 推荐配置 |
|------|---------|---------|
| 操作系统 | Linux (CentOS 7+, Ubuntu 18.04+) / Windows 10+ | Linux 生产部署 |
| 内存 | 4 GB | 16 GB+ |
| 磁盘 | 20 GB 可用空间 | SSD，500GB+ |
| JDK | 1.8+（仅控制节点需要） | JDK 11 |

> **Windows 用户注意**：社区版 Windows 版适合学习和测试。生产环境的 DolphinDB 集群建议部署在 Linux 系统上。

## 2.2 安装与目录结构

### Linux 安装

```bash
# 1. 解压安装包
unzip dolphindb_linux64_v2.00.xx.zip -d /opt/

# 2. 查看目录结构
cd /opt/dolphindb
ls -la
```

### Windows 安装

Windows 安装非常简单，直接解压 ZIP 包到目标目录（如 `D:\dolphindb`）即可。双击 `dolphindb.exe` 即可启动服务器。

### 安装后目录结构

```
dolphindb/
├── dolphindb          # Linux 可执行文件 (Windows: dolphindb.exe)
├── server/            # 服务器配置文件目录
│   ├── dolphindb.cfg  # 主配置文件
│   ├── dolphindb.lic  # License 文件
│   └── log/           # 日志目录
├── plugins/           # 插件目录（如 Kafka、MySQL 等）
├── modules/           # 模块目录
├── scripts/           # 脚本目录
├── data/              # 数据存储目录（启动后生成）
└── licenses/          # License 存放目录
```

关键文件说明：

| 文件/目录 | 作用 |
|----------|------|
| `dolphindb` | 服务器启动程序（Linux 可执行） |
| `dolphindb.exe` | 服务器启动程序（Windows） |
| `dolphindb.cfg` | 节点配置（端口、数据路径、内存等） |
| `dolphindb.lic` | 授权文件，控制使用期限和功能范围 |
| `data/` | 数据库文件实际存储位置 |

## 2.3 License 类型

DolphinDB 启动时需要 License 文件。不同 License 支持的功能和节点数不同：

| License 类型 | 获取方式 | 有效期 | 节点数 | 适用场景 |
|-------------|---------|--------|--------|---------|
| 社区版（Community） | 官网自助申请 | 1年，可续 | 单节点（≤8核） | 学习、开发 |
| 试用版（Trial） | 联系商务 | 1-3个月 | 可多节点 | 企业评估 |
| 商业版（Commercial） | 购买获得 | 按合同 | 按合同 | 生产部署 |

### 申请社区 License

1. 访问 DolphinDB 官网，进入 License 申请页面
2. 填写机器信息（主机名、MAC地址、CPU核心数）
3. 提交后，License 文件发送到注册邮箱
4. 将 `dolphindb.lic` 放到 `server/` 目录下

```bash
# Linux 获取主机名和 MAC 地址
hostname
ifconfig  # 或 ip addr
```

> **如果 License 配置错误**，启动时会报错："Failed to read the license file"。请检查：(1) License 文件路径是否正确；(2) License 中的 MAC 地址是否与当前机器一致；(3) License 是否过期。

## 2.4 启动服务

### Linux 启动

```bash
# 切换到 DolphinDB 安装目录
cd /opt/dolphindb

# 前台启动（CTRL+C 停止）
./dolphindb

# 后台启动
nohup ./dolphindb -console 0 > dolphindb.log 2>&1 &

# 指定配置文件启动
./dolphindb -config /path/to/dolphindb.cfg
```

### Windows 启动

在 Windows 上，直接双击 `dolphindb.exe` 即可启动。或通过命令行：

```powershell
# Windows 命令行启动
dolphindb.exe

# 指定配置文件
dolphindb.exe -config dolphindb.cfg
```

### 启动成功标志

当看到以下日志输出时，说明服务启动成功：

```
[2024-01-01 10:00:00] Server started on port 8848
[2024-01-01 10:00:00] The web console is available at http://localhost:8848
```

**默认端口：8848**。这个端口号容易记忆——8848 是珠穆朗玛峰的海拔高度（米），也寓意 DolphinDB 是时序数据库领域的"登峰之作"。

> 如果端口 8848 被占用，可以在 `dolphindb.cfg` 中修改 `port` 参数为其他端口。

## 2.5 配置文件基础

`dolphindb.cfg` 是 DolphinDB 的核心配置文件，常见配置项如下：

```ini
# dolphindb.cfg 关键配置项

# 节点名称（集群中唯一标识）
nodeName=node1

# 服务端口
localSite=localhost:8848

# 数据存储路径
volumes=D:/dolphindb/data

# 最大内存使用限制（GB）
maxMemSize=8

# 分布式计算工作节点数
workerNum=4

# 日志级别（INFO/DEBUG/WARNING/ERROR）
logLevel=INFO

# 是否允许流数据的持久化
persistenceDir=D:/dolphindb/persistence

# Web Console 允许的最大连接数
webWorkerNum=4

# 定时任务调度器
scheduleInSecond=false
```

| 配置项 | 说明 | 默认值 |
|-------|------|--------|
| `localSite` | 节点地址和端口 | localhost:8848 |
| `volumes` | 数据存储卷（可多路径分号分隔） | 空（使用安装目录） |
| `maxMemSize` | 进程最大内存（GB），超限会触发自动清理 | 系统内存的 80% |
| `workerNum` | 并行计算线程数 | CPU 核心数-1 |
| `webWorkerNum` | Web 控制台并发处理数 | 4 |

### 单机模式最小配置

对于学习目的，最简单的配置仅需一行：

```ini
localSite=localhost:8848
```

其他参数使用默认值即可正常启动和运行。在后续深入学习分布式集群部署时，再逐步了解和调整更多配置项。

### 停止服务

```bash
# Linux: CTRL+C（前台模式）或 kill 进程
kill $(pgrep dolphindb)

# 或通过 Web Console 执行
quit;
```

> **安全提示**：DolphinDB 默认不需要认证即可访问。在生产环境中，务必配置访问密码和 IP 白名单，避免数据泄露。
