#!/bin/bash

# ComfyUI Web服务启动脚本
# 使用方法: ./start.sh

echo "🚀 启动ComfyUI Web服务..."

# 检查是否已经在运行
if lsof -i :5000 > /dev/null 2>&1; then
    echo "❌ 端口5000已被占用，请先停止现有服务"
    echo "使用以下命令停止服务:"
    echo "  ./stop.sh"
    exit 1
fi

# 切换到项目根目录
cd "$(dirname "$0")/.."

# 激活虚拟环境
if [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
    echo "✅ 虚拟环境已激活"
else
    echo "⚠️  虚拟环境不存在，请先创建: python3 -m venv venv"
    exit 1
fi

# 检查依赖
if [ -f "requirements.txt" ]; then
    echo "📦 检查依赖包..."
    pip install -r requirements.txt > /dev/null 2>&1
    echo "✅ 依赖包检查完成"
fi

# 使用nohup启动服务，输出重定向到日志文件
echo "🌐 启动服务..."
nohup python3 app.py > app.log 2>&1 &

# 获取进程ID
PID=$!
echo "✅ 服务已启动，进程ID: $PID"
echo "📝 日志文件: app.log"
echo "🌐 访问地址: http://localhost:5000"
echo ""
echo "停止服务命令:"
echo "  ./stop.sh"
echo "或"
echo "  kill $PID" 