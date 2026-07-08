#!/usr/bin/env bash
# MyTools 启动脚本
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

HOST="${MYTOOLS_HOST:-127.0.0.1}"
PORT="${MYTOOLS_PORT:-8765}"
CONDA_ENV="${MYTOOLS_CONDA_ENV:-spider_base}"

# 优先使用 spider_base（或 MYTOOLS_CONDA_ENV 指定的 conda 环境）
if [[ -n "${CONDA_PREFIX:-}" && "$(basename "$CONDA_PREFIX")" == "$CONDA_ENV" ]]; then
  PYTHON="python"
elif [[ -x "/opt/anaconda3/envs/${CONDA_ENV}/bin/python" ]]; then
  PYTHON="/opt/anaconda3/envs/${CONDA_ENV}/bin/python"
elif [[ -x "${HOME}/anaconda3/envs/${CONDA_ENV}/bin/python" ]]; then
  PYTHON="${HOME}/anaconda3/envs/${CONDA_ENV}/bin/python"
elif [[ -x "${HOME}/miniconda3/envs/${CONDA_ENV}/bin/python" ]]; then
  PYTHON="${HOME}/miniconda3/envs/${CONDA_ENV}/bin/python"
else
  PYTHON="python"
  echo "警告: 未找到 conda 环境 ${CONDA_ENV}，将使用当前 python: $(command -v python)" >&2
fi

echo "启动 MyTools (我的工具箱) ..."
echo "Python: $($PYTHON --version 2>&1) [$($PYTHON -c 'import sys; print(sys.executable)')]"
echo "访问地址: http://${HOST}:${PORT}"

exec "$PYTHON" web/main.py
