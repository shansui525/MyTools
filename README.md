# MyTools（我的工具箱）

多功能在线工具集合，基于 Python + FastAPI 构建，可独立运行。

## 功能特点

- **配置驱动**：通过 `config/tools.json` 配置可用工具，前端自动展示
- **前后端分离**：Web 负责展示，Python 后端提供独立 API 完成实际功能
- **独立运行**：无需外部依赖，一条命令即可启动

## 快速开始

```bash
# 安装依赖
pip install -r requirements.txt

# 启动服务
bash run.sh
# 或
python -m uvicorn web.main:app --host 127.0.0.1 --port 8765 --reload --log-config web/log_config.py
```

浏览器访问 http://127.0.0.1:8765

## 当前工具

| 工具 | 说明 |
|------|------|
| Excel 文件对比 | 对比两个 Excel 文件差异，支持直接对比和主键对比 |

## 添加新工具

1. 在 `modules/` 下创建功能模块
2. 在 `web/routers/` 下创建 API 路由
3. 在 `web/static/tools/` 下创建前端页面
4. 在 `config/tools.json` 中注册工具

## 项目结构

```
MyTools/
├── config/tools.json      # 工具配置
├── modules/               # 功能模块（核心业务逻辑）
├── web/
│   ├── main.py            # FastAPI 入口
│   ├── routers/           # API 路由
│   └── static/            # 前端静态文件
├── requirements.txt
└── run.sh
```

## 环境变量

| 变量 | 默认值 | 说明 |
|------|--------|------|
| MYTOOLS_HOST | 127.0.0.1 | 监听地址 |
| MYTOOLS_PORT | 8765 | 监听端口 |
