#!/usr/bin/env bash
# MyTools 启动脚本
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

HOST="${MYTOOLS_HOST:-127.0.0.1}"
PORT="${MYTOOLS_PORT:-8765}"

echo "启动 MyTools (我的工具箱) ..."
echo "访问地址: http://${HOST}:${PORT}"

python -m uvicorn web.main:app --host "$HOST" --port "$PORT" --reload --log-config web/log_config.py
