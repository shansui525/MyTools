# MyTools（我的工具箱）

多功能在线工具集合，基于 Python + FastAPI 构建，可在本地独立运行。

**当前版本：v1.1.1**

仓库地址：[github.com/shansui525/MyTools](https://github.com/shansui525/MyTools)

## 功能特点

- **配置驱动**：通过 `config/tools.json` 注册工具，首页自动展示
- **前后端分离**：静态 Web 页面 + 独立 API 路由，业务逻辑在 `modules/` 中
- **本地优先**：默认监听 `127.0.0.1`，数据保存在本地 `data/` 目录，不提交 Git
- **即开即用**：安装依赖后一条命令启动

## 快速开始

```bash
# 克隆项目
git clone https://github.com/shansui525/MyTools.git
cd MyTools

# 安装依赖（推荐使用 conda 环境）
conda activate spider_base   # 或任意 Python 3.9+ 环境
pip install -r requirements.txt

# 启动服务
bash run.sh
# 或
python web/main.py
```

浏览器访问 http://127.0.0.1:8765

> `run.sh` 默认使用 conda 环境 `spider_base`（可通过环境变量 `MYTOOLS_CONDA_ENV` 修改）。若未找到该环境，则回退到当前 `python`。

## 工具列表

### 对比工具

| 工具 | 说明 |
|------|------|
| Excel 文件对比 | 对比两个 Excel 差异，支持指定工作表、直接对比与主键对比；差异高亮，含差异索引与摘要 |
| 文本对比 | 对比两段文本或文件，差异行与字符高亮；差异摘要汇总，点击行号跳转查看 |

### 格式化

| 工具 | 说明 |
|------|------|
| JSON 格式化 | JSON 格式化、压缩、校验，支持上传文件与键名排序 |
| SQL 格式化 | SQL 缩进美化，支持标准 / Hive / Spark 方言，关键字高亮，输入/输出行号，基于 sqlglot 的语法检查，错误行号可点击跳转 |
| Excel 转 Markdown | Excel 表格转压缩 Markdown，分隔符最短 |
| Word 转 Markdown | Word 文档转 Markdown，保留标题、段落、列表与表格 |

### 开发工具

| 工具 | 说明 |
|------|------|
| curl 转 requests | 将 curl / bash 命令转换为 Python requests 代码 |
| SQLite 查询 | 链接本地 SQLite 文件，或新建临时库导入 CSV/Excel 为临时表；浏览元数据、执行 SQL、结果全屏查看，自动保存历史 |
| 加解密实验室 | 对称/非对称/国密算法与 Base64 等编码，附带 Python / JavaScript 示例 |
| 定时调度器 | Cron 定时执行 Python 脚本，支持多任务与执行日志 |

### 日常工具

| 工具 | 说明 |
|------|------|
| 密码管理器 | AES-256 加密存储账号密码，支持 JSON / CSV / 加密备份导出 |
| Markdown 转 PDF | Markdown 转 PDF，支持代码块、表格与中文排版 |
| 年历 | 3×4 年历排版，标注节日，支持自定义事件，可导出图片 / PDF |
| RSS 订阅管理 | 管理 RSS 订阅源，内置 60 个预设数据源，并发检测可用性，点击查看文章 |
| 工作记录与报告 | 每日录入工作内容，大模型生成周报 / 月报 / 季报 / 年报，支持保存、编辑与随时查看 |

## 项目结构

```
MyTools/
├── config/
│   ├── tools.json              # 工具注册与分组配置
│   └── rss_feed_presets.json   # RSS 内置预设订阅源
├── data/                       # 运行时数据（Git 忽略，首次运行自动创建）
├── modules/                    # 核心业务逻辑
├── web/
│   ├── main.py                 # FastAPI 入口
│   ├── routers/                # API 路由
│   └── static/                 # 前端页面与静态资源
├── requirements.txt
├── run.sh                      # 启动脚本（默认 spider_base 环境）
└── .gitignore
```

## 添加新工具

1. 在 `modules/` 下实现功能模块
2. 在 `web/routers/` 下添加 API 路由，并在 `web/main.py` 中注册
3. 在 `web/static/tools/` 下创建前端页面
4. 在 `config/tools.json` 中注册工具（`id`、`route`、`api_prefix` 等）

## 环境变量

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `MYTOOLS_HOST` | `127.0.0.1` | 监听地址 |
| `MYTOOLS_PORT` | `8765` | 监听端口 |
| `MYTOOLS_CONDA_ENV` | `spider_base` | `run.sh` 优先使用的 conda 环境名 |
| `MYTOOLS_LLM_API_BASE` | — | 大模型 API 地址（OpenAI 兼容） |
| `MYTOOLS_LLM_API_KEY` | — | 大模型 API Key |
| `MYTOOLS_LLM_MODEL` | `gpt-4o-mini` | 大模型名称 |

## 数据与隐私

以下文件保存在本地 `data/` 目录，已在 `.gitignore` 中排除，不会上传到 Git：

- 密码管理器数据库（`password_vault.db`）
- SQLite 连接注册表、查询历史与 CSV/Excel 导入临时数据（`sqlite_imports/`）
- RSS 订阅源列表（`rss_feeds.json`）
- 工作记录与报告（`work_report.json`，含每日记录与已保存报告）
- 定时任务配置与执行日志
- 日历事件等用户数据

## 技术栈

- **后端**：FastAPI、Uvicorn
- **数据处理**：Pandas、OpenPyXL、sqlparse、sqlglot、mammoth
- **安全**：cryptography、gmssl
- **调度**：APScheduler
- **RSS**：feedparser
- **前端**：原生 HTML / CSS / JavaScript

## 版本历史

### v1.1.1（2026-07-09）

**增强**

- **工作记录与报告**：生成的周报 / 月报 / 季报 / 年报可保存至本地，支持编辑后再次保存，左侧列表随时查看历史报告
- **SQL 格式化**：表/别名解析忽略大小写，减少误报；语法检查结果支持点击行号跳转至输入区对应位置
- **文本对比**：对比结果下方增加差异摘要（删除 / 新增 / 修改行数与明细），点击 `A:行号 ↔ B:行号` 可跳转至结果区并高亮差异行

---

### v1.1.0（2026-07-08）

**初始发布**

| 分类 | 工具 |
|------|------|
| 对比 | Excel 文件对比、文本对比 |
| 格式化 | JSON 格式化、SQL 格式化、Excel / Word 转 Markdown |
| 开发 | curl 转 requests、SQLite 查询、加解密实验室、定时调度器 |
| 日常 | 密码管理器、Markdown 转 PDF、年历 |

**新增**

- **RSS 订阅管理**：订阅源增删改查、内置 60 个预设数据源批量导入、并发检测可用性、SSE 流式推送状态、文章列表浏览
- **工作记录与报告**：每日工作条目录入、大模型生成周报 / 月报 / 季报 / 年报（支持 OpenAI 兼容 API）

**增强**

- **SQL 格式化**：输入 / 输出行号栏；引入 sqlglot 三层语法检查（词法 → 语法解析 → 语义），替代正则枚举规则；支持标准 / Hive / Spark 方言
- **SQLite 查询**：新建临时库或链接已有 `.db` 后导入 CSV / Excel 为临时表；表名取自文件名；结果区比例优化与全屏查看；临时库命名显示为「临时库 MM-DD HH:MM:SS #xxxx」
- **启动脚本**：`run.sh` 默认使用 conda 环境 `spider_base`，可通过 `MYTOOLS_CONDA_ENV` 覆盖

**修复**

- `run.sh` 改为直接执行 `python web/main.py`，避免 uvicorn 字符串导入时 `log_config` 加载失败
- RSS 订阅管理：状态检测 SSE 接口改为异步实现，修复打开 RSS 页时并发检测大量源阻塞 uvicorn 单 worker、导致全站其他页面无响应的问题

**文档**

- 补全 README：全部工具说明、项目结构、环境变量、数据隐私与版本历史

**清理**

- 移除未引用的 SQLite 旧实现模块（`import_tables.py`、`sessions.py`，已由 `import_store.py` 替代）

**依赖**

- 新增 `sqlglot>=25.0.0`

**架构**

- 配置驱动工具注册（`config/tools.json`）
- FastAPI + 静态前端，业务逻辑在 `modules/`
- 本地 `data/` 目录持久化，Git 忽略敏感与用户数据
