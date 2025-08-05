#!/bin/bash

# ComfyUI Web服务优化版启动脚本
# 版本: 2.0.0

echo "🚀 ComfyUI Web服务优化版启动脚本"
echo "=================================="

# 检查Python环境
if ! command -v python3 &> /dev/null; then
    echo "❌ 错误: 未找到Python3，请先安装Python3"
    exit 1
fi

# 检查虚拟环境
if [ ! -d "venv" ]; then
    echo "📦 创建虚拟环境..."
    python3 -m venv venv
fi

# 激活虚拟环境
echo "🔧 激活虚拟环境..."
source venv/bin/activate

# 安装依赖
echo "📥 检查并安装依赖..."
pip install -r requirements.txt

# 检查ComfyUI服务
echo "🔍 检查ComfyUI服务状态..."
if curl -s http://localhost:8188 > /dev/null 2>&1; then
    echo "✅ ComfyUI服务正在运行 (端口8188)"
else
    echo "⚠️  警告: ComfyUI服务未运行"
    echo "   请确保ComfyUI在端口8188上运行"
    echo "   启动命令: python main.py --listen 0.0.0.0 --port 8188"
fi

# 设置环境变量
export FLASK_ENV=development
export FLASK_DEBUG=1

# 启动Web服务
echo "🌐 启动ComfyUI Web服务..."
echo "   访问地址: http://localhost:5000"
echo "   测试页面: http://localhost:5000/test_optimized.html"
echo "   按 Ctrl+C 停止服务"
echo ""

python app.py 