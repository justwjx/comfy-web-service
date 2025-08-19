#!/bin/bash

# ComfyUI Web Service 虚拟环境激活脚本

echo "=== ComfyUI Web Service 环境配置 ==="

# 检查虚拟环境是否存在
if [ ! -d "venv" ]; then
    echo "✗ 虚拟环境不存在，正在创建..."
    python3 -m venv venv
    if [ $? -eq 0 ]; then
        echo "✓ 虚拟环境创建成功"
    else
        echo "✗ 虚拟环境创建失败"
        exit 1
    fi
fi

# 激活虚拟环境
echo "激活虚拟环境..."
source venv/bin/activate

# 检查依赖包
echo "检查依赖包..."
if ! python3 -c "import flask" 2>/dev/null; then
    echo "✗ 依赖包未安装，正在安装..."
    pip install -r requirements.txt
    if [ $? -eq 0 ]; then
        echo "✓ 依赖包安装成功"
    else
        echo "✗ 依赖包安装失败"
        exit 1
    fi
else
    echo "✓ 依赖包已安装"
fi

# 检查IPv6支持
echo "检查IPv6支持..."
if python3 -c "import socket; print('IPv6支持:', socket.has_ipv6)" | grep -q "True"; then
    echo "✓ 系统支持IPv6"
else
    echo "✗ 系统不支持IPv6"
fi

echo "=== 环境配置完成 ==="
echo "现在可以运行以下命令："
echo "  ./start_with_ipv6.sh    # 启动IPv6服务"
echo "  python3 test_ipv6.py    # 测试IPv6连接"
echo "  python3 app.py          # 直接启动应用" 