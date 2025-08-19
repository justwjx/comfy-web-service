#!/bin/bash

# ComfyUI Web Service 通用启动脚本

echo "=== ComfyUI Web Service 启动脚本 ==="

# 检查虚拟环境
if [ ! -d "venv" ]; then
    echo "✗ 虚拟环境不存在，正在创建..."
    python3 -m venv venv
    if [ $? -ne 0 ]; then
        echo "✗ 虚拟环境创建失败"
        exit 1
    fi
    echo "✓ 虚拟环境创建成功"
fi

# 激活虚拟环境
echo "激活虚拟环境..."
source venv/bin/activate

# 检查依赖包
echo "检查依赖包..."
if ! python3 -c "import flask" 2>/dev/null; then
    echo "✗ 依赖包未安装，正在安装..."
    pip install -r requirements.txt
    if [ $? -ne 0 ]; then
        echo "✗ 依赖包安装失败"
        exit 1
    fi
    echo "✓ 依赖包安装成功"
else
    echo "✓ 依赖包已安装"
fi

# 设置环境变量
HOST=${HOST:-"::"}  # 默认使用IPv6
PORT=${PORT:-5000}
DEBUG=${DEBUG:-False}

echo "配置信息:"
echo "  HOST: $HOST"
echo "  PORT: $PORT"
echo "  DEBUG: $DEBUG"

# 检查IPv6支持
if [ "$HOST" = "::" ]; then
    if python3 -c "import socket; print('IPv6支持:', socket.has_ipv6)" | grep -q "True"; then
        echo "✓ 系统支持IPv6"
    else
        echo "✗ 系统不支持IPv6，切换到IPv4"
        HOST="0.0.0.0"
    fi
fi

# 检查端口是否被占用
if ss -tlnp | grep -q ":${PORT} "; then
    echo "警告: 端口 ${PORT} 已被占用"
    echo "请停止占用该端口的进程或修改PORT环境变量"
    exit 1
fi

# 导出环境变量
export HOST
export PORT
export DEBUG

# 显示访问地址
echo ""
echo "=== 服务启动信息 ==="
if [ "$HOST" = "::" ]; then
    echo "IPv6模式启动:"
    echo "  IPv4访问: http://172.16.10.224:${PORT}"
    echo "  IPv6访问: http://[2409:8a20:8e25:a261:7656:3cff:feb3:26ed]:${PORT}"
    echo "  IPv6访问: http://[fd27:392a:635d:e40:7656:3cff:feb3:26ed]:${PORT}"
else
    echo "IPv4模式启动:"
    echo "  IPv4访问: http://172.16.10.224:${PORT}"
fi
echo ""

# 启动应用
echo "正在启动应用..."
python3 app.py 