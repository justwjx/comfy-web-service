#!/bin/bash

# ComfyUI Web Service 脚本重新整理

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}=== ComfyUI Web Service 脚本重新整理 ===${NC}"
echo ""

# 1. 移动docs/scripts中的脚本到根目录scripts
echo -e "${YELLOW}移动脚本文件到根目录scripts目录...${NC}"

# 确保scripts目录存在
mkdir -p scripts

# 移动有用的脚本
if [ -f "docs/scripts/ipv6_switch.sh" ]; then
    mv docs/scripts/ipv6_switch.sh scripts/
    echo "✓ 移动 ipv6_switch.sh 到 scripts/"
fi

if [ -f "docs/scripts/performance_test.sh" ]; then
    mv docs/scripts/performance_test.sh scripts/
    echo "✓ 移动 performance_test.sh 到 scripts/"
fi

if [ -f "docs/scripts/quick_switch.sh" ]; then
    mv docs/scripts/quick_switch.sh scripts/
    echo "✓ 移动 quick_switch.sh 到 scripts/"
fi

if [ -f "docs/scripts/activate_env.sh" ]; then
    mv docs/scripts/activate_env.sh scripts/
    echo "✓ 移动 activate_env.sh 到 scripts/"
fi

# 2. 清理重复和失效的脚本
echo -e "${YELLOW}清理重复和失效的脚本...${NC}"

# 删除docs/scripts目录（已移动的脚本）
if [ -d "docs/scripts" ]; then
    rm -rf docs/scripts
    echo "✓ 删除 docs/scripts 目录"
fi

# 删除根目录的重复脚本
if [ -f "start_with_ipv6.sh" ]; then
    rm start_with_ipv6.sh
    echo "✓ 删除重复的 start_with_ipv6.sh"
fi

# 删除根目录的符号链接
if [ -L "ipv6_switch.sh" ]; then
    rm ipv6_switch.sh
    echo "✓ 删除符号链接 ipv6_switch.sh"
fi

if [ -L "quick_switch.sh" ]; then
    rm quick_switch.sh
    echo "✓ 删除符号链接 quick_switch.sh"
fi

if [ -L "performance_test.sh" ]; then
    rm performance_test.sh
    echo "✓ 删除符号链接 performance_test.sh"
fi

if [ -L "activate_env.sh" ]; then
    rm activate_env.sh
    echo "✓ 删除符号链接 activate_env.sh"
fi

# 3. 分析scripts目录中的脚本
echo -e "${YELLOW}分析scripts目录中的脚本...${NC}"

# 检查scripts目录中的脚本
cd scripts
echo "scripts目录中的脚本:"
ls -la *.sh 2>/dev/null || echo "没有找到.sh脚本"

# 检查重复功能
echo ""
echo -e "${BLUE}脚本功能分析:${NC}"

# 检查start相关脚本
start_scripts=($(ls start*.sh 2>/dev/null))
if [ ${#start_scripts[@]} -gt 0 ]; then
    echo "启动脚本: ${start_scripts[*]}"
    # 保留最完整的启动脚本，删除重复的
    if [ ${#start_scripts[@]} -gt 1 ]; then
        echo "⚠ 发现多个启动脚本，建议保留功能最完整的"
    fi
fi

# 检查stop相关脚本
stop_scripts=($(ls stop*.sh 2>/dev/null))
if [ ${#stop_scripts[@]} -gt 0 ]; then
    echo "停止脚本: ${stop_scripts[*]}"
fi

cd ..

# 4. 创建新的符号链接到根目录
echo -e "${YELLOW}创建新的符号链接...${NC}"

# 创建主要脚本的符号链接
if [ -f "scripts/ipv6_switch.sh" ]; then
    ln -sf "scripts/ipv6_switch.sh" "ipv6_switch.sh"
    echo "✓ 创建符号链接: ipv6_switch.sh -> scripts/ipv6_switch.sh"
fi

if [ -f "scripts/quick_switch.sh" ]; then
    ln -sf "scripts/quick_switch.sh" "quick_switch.sh"
    echo "✓ 创建符号链接: quick_switch.sh -> scripts/quick_switch.sh"
fi

if [ -f "scripts/performance_test.sh" ]; then
    ln -sf "scripts/performance_test.sh" "performance_test.sh"
    echo "✓ 创建符号链接: performance_test.sh -> scripts/performance_test.sh"
fi

if [ -f "scripts/activate_env.sh" ]; then
    ln -sf "scripts/activate_env.sh" "activate_env.sh"
    echo "✓ 创建符号链接: activate_env.sh -> scripts/activate_env.sh"
fi

# 5. 给所有脚本添加执行权限
echo -e "${YELLOW}设置脚本执行权限...${NC}"
chmod +x scripts/*.sh 2>/dev/null
echo "✓ 设置scripts目录下所有脚本的执行权限"

# 6. 验证脚本可用性
echo -e "${YELLOW}验证脚本可用性...${NC}"

# 测试主要脚本
if [ -f "scripts/ipv6_switch.sh" ]; then
    if ./scripts/ipv6_switch.sh help >/dev/null 2>&1; then
        echo "✓ ipv6_switch.sh 可用"
    else
        echo "✗ ipv6_switch.sh 不可用"
    fi
fi

if [ -f "scripts/performance_test.sh" ]; then
    if bash -n scripts/performance_test.sh; then
        echo "✓ performance_test.sh 语法正确"
    else
        echo "✗ performance_test.sh 语法错误"
    fi
fi

if [ -f "scripts/quick_switch.sh" ]; then
    if bash -n scripts/quick_switch.sh; then
        echo "✓ quick_switch.sh 语法正确"
    else
        echo "✗ quick_switch.sh 语法错误"
    fi
fi

# 7. 显示最终结构
echo ""
echo -e "${BLUE}=== 最终脚本结构 ===${NC}"
echo ""
echo "根目录脚本 (符号链接):"
ls -la *.sh 2>/dev/null | grep -E "^l" || echo "没有符号链接"

echo ""
echo "scripts目录脚本:"
ls -la scripts/*.sh 2>/dev/null || echo "scripts目录中没有脚本"

echo ""
echo -e "${GREEN}✓ 脚本重新整理完成！${NC}"
echo ""
echo -e "${BLUE}主要改进:${NC}"
echo "  ✅ 统一脚本位置到 scripts/ 目录"
echo "  ✅ 清理重复和失效的脚本"
echo "  ✅ 保持根目录符号链接的可用性"
echo "  ✅ 验证脚本功能"
echo ""
echo -e "${YELLOW}现在可以使用以下命令:${NC}"
echo "  ./start.sh                    # 启动服务"
echo "  ./ipv6_switch.sh status       # 查看状态"
echo "  ./performance_test.sh         # 性能测试"
echo "  ./quick_switch.sh             # 快速切换"
echo "  ./activate_env.sh             # 激活环境" 