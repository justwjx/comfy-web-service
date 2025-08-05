#!/bin/bash

# 激活虚拟环境脚本
echo "正在激活虚拟环境..."

# 检查虚拟环境是否存在
if [ ! -d "venv" ]; then
    echo "错误：虚拟环境不存在，请先创建虚拟环境"
    echo "运行命令：python -m venv venv"
    exit 1
fi

# 激活虚拟环境
source venv/bin/activate

echo "虚拟环境已激活！"
echo "当前Python路径: $(which python)"
echo "当前pip路径: $(which pip)"

# 显示当前安装的包
echo "已安装的包："
pip list

echo ""
echo "提示："
echo "- 使用 'deactivate' 命令退出虚拟环境"
echo "- 使用 'pip install -r requirements.txt' 安装依赖"
echo "- 使用 './scripts/start.sh' 启动服务" 