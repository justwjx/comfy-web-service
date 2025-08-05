#!/bin/bash

# ComfyUI Web服务启动脚本
# 使用方法: ./start_service.sh

echo "🚀 启动ComfyUI Web服务..."

# 检查是否已经在运行
if lsof -i :5000 > /dev/null 2>&1; then
    echo "❌ 端口5000已被占用，请先停止现有服务"
    echo "使用以下命令停止服务:"
    echo "  pkill -f 'python3 app.py'"
    exit 1
fi

# 激活虚拟环境并启动服务
cd "$(dirname "$0")/.."
source venv/bin/activate

# 使用nohup启动服务，输出重定向到日志文件
nohup python3 app.py > app.log 2>&1 &

# 获取进程ID
PID=$!
echo "✅ 服务已启动，进程ID: $PID"
echo "📝 日志文件: app.log"
echo "🌐 访问地址: http://localhost:5000"
echo ""
echo "停止服务命令:"
echo "  kill $PID"
echo "或"
echo "  pkill -f 'python3 app.py'" 