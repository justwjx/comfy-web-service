#!/bin/bash

# ComfyUI Web服务停止脚本
# 使用方法: ./stop_service.sh

echo "🛑 停止ComfyUI Web服务..."

# 查找并停止所有app.py进程
PIDS=$(pgrep -f "python3 app.py")

if [ -z "$PIDS" ]; then
    echo "ℹ️  没有找到运行中的ComfyUI Web服务"
    exit 0
fi

echo "找到以下进程:"
echo "$PIDS"

# 停止进程
for PID in $PIDS; do
    echo "停止进程 $PID..."
    kill $PID
done

# 等待进程完全停止
sleep 2

# 检查是否还有进程在运行
REMAINING=$(pgrep -f "python3 app.py")
if [ -n "$REMAINING" ]; then
    echo "⚠️  强制停止剩余进程..."
    pkill -9 -f "python3 app.py"
fi

echo "✅ 服务已停止"

# 检查端口是否释放
if lsof -i :5000 > /dev/null 2>&1; then
    echo "⚠️  端口5000仍被占用，可能需要手动检查"
else
    echo "✅ 端口5000已释放"
fi 