#!/bin/bash

# ComfyUI Web Service IPv6切换脚本

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 配置文件路径
CONFIG_FILE=".env"

# 获取网络地址
get_network_addresses() {
    # 获取IPv4地址
    local ipv4_addresses=()
    while IFS= read -r line; do
        if [[ $line =~ inet[[:space:]]+([0-9]+\.[0-9]+\.[0-9]+\.[0-9]+) ]]; then
            local ip="${BASH_REMATCH[1]}"
            if [[ $ip != "127.0.0.1" ]]; then
                ipv4_addresses+=("$ip")
            fi
        fi
    done < <(ip addr show | grep -E "inet ")

    # 获取IPv6地址
    local ipv6_addresses=()
    while IFS= read -r line; do
        if [[ $line =~ inet6[[:space:]]+([0-9a-fA-F:]+) ]]; then
            local ip="${BASH_REMATCH[1]}"
            if [[ $ip != "::1" && $ip != fe80:* ]]; then
                ipv6_addresses+=("$ip")
            fi
        fi
    done < <(ip addr show | grep -E "inet6 ")

    # 返回结果
    echo "ipv4:${ipv4_addresses[*]}"
    echo "ipv6:${ipv6_addresses[*]}"
}

# 显示访问地址
show_access_addresses() {
    local addresses
    addresses=$(get_network_addresses)
    
    local ipv4_line=$(echo "$addresses" | grep "^ipv4:")
    local ipv6_line=$(echo "$addresses" | grep "^ipv6:")
    
    local port=${PORT:-5000}
    
    echo "访问地址:"
    
    # 显示IPv4地址
    if [[ $ipv4_line =~ ipv4:(.+) ]]; then
        local ipv4_addrs="${BASH_REMATCH[1]}"
        if [[ -n $ipv4_addrs ]]; then
            for ip in $ipv4_addrs; do
                echo "  IPv4: http://$ip:$port"
            done
        fi
    fi
    
    # 显示IPv6地址
    if [[ $ipv6_line =~ ipv6:(.+) ]]; then
        local ipv6_addrs="${BASH_REMATCH[1]}"
        if [[ -n $ipv6_addrs ]]; then
            for ip in $ipv6_addrs; do
                echo "  IPv6: http://[$ip]:$port"
            done
        fi
    fi
}

# 显示当前状态
show_status() {
    echo -e "${BLUE}=== 当前IPv6配置状态 ===${NC}"
    
    if [ -f "$CONFIG_FILE" ]; then
        HOST_CONFIG=$(grep "^HOST=" "$CONFIG_FILE" | cut -d'=' -f2)
    else
        HOST_CONFIG="::"
    fi
    
    case "$HOST_CONFIG" in
        "::")
            echo -e "${GREEN}✓ 当前模式: 双栈模式 (IPv4 + IPv6)${NC}"
            echo "   配置: HOST=::"
            ;;
        "0.0.0.0")
            echo -e "${YELLOW}⚠ 当前模式: IPv4专用模式${NC}"
            echo "   配置: HOST=0.0.0.0"
            ;;
        "::1")
            echo -e "${BLUE}ℹ 当前模式: IPv6本地模式${NC}"
            echo "   配置: HOST=::1"
            ;;
        *)
            echo -e "${RED}✗ 当前模式: 未知${NC}"
            ;;
    esac
    
    echo ""
    echo -e "${BLUE}=== 服务状态 ===${NC}"
    if ss -tlnp | grep -q ":5000 "; then
        echo -e "${GREEN}✓ 服务正在运行${NC}"
        ss -tlnp | grep ":5000"
    else
        echo -e "${RED}✗ 服务未运行${NC}"
    fi
}

# 切换到IPv4专用模式
switch_to_ipv4() {
    echo -e "${YELLOW}切换到IPv4专用模式...${NC}"
    
    # 创建或更新.env文件
    if [ ! -f "$CONFIG_FILE" ]; then
        cp env.example "$CONFIG_FILE"
    fi
    
    # 更新HOST配置
    sed -i 's/^HOST=.*/HOST=0.0.0.0/' "$CONFIG_FILE"
    
    echo -e "${GREEN}✓ 已切换到IPv4专用模式${NC}"
    show_access_addresses
}

# 切换到双栈模式
switch_to_dual() {
    echo -e "${YELLOW}切换到双栈模式...${NC}"
    
    # 创建或更新.env文件
    if [ ! -f "$CONFIG_FILE" ]; then
        cp env.example "$CONFIG_FILE"
    fi
    
    # 更新HOST配置
    sed -i 's/^HOST=.*/HOST=::/' "$CONFIG_FILE"
    
    echo -e "${GREEN}✓ 已切换到双栈模式${NC}"
    show_access_addresses
}

# 重启服务
restart_service() {
    echo -e "${YELLOW}重启服务以应用新配置...${NC}"
    
    # 停止当前服务
    pkill -f "python.*app.py" 2>/dev/null
    sleep 2
    
    # 检查虚拟环境
    if [ ! -d "venv" ]; then
        echo -e "${RED}✗ 虚拟环境不存在${NC}"
        return 1
    fi
    
    # 激活虚拟环境并启动服务
    source venv/bin/activate
    
    # 读取当前配置
    if [ -f "$CONFIG_FILE" ]; then
        export HOST=$(grep "^HOST=" "$CONFIG_FILE" | cut -d'=' -f2)
    else
        export HOST="::"
    fi
    export PORT=5000
    export DEBUG=False
    
    echo "启动服务: HOST=$HOST, PORT=$PORT"
    
    # 后台启动服务
    nohup python3 app.py > app.log 2>&1 &
    
    # 等待服务启动
    sleep 3
    
    # 检查服务状态
    if ss -tlnp | grep -q ":5000 "; then
        echo -e "${GREEN}✓ 服务启动成功${NC}"
    else
        echo -e "${RED}✗ 服务启动失败${NC}"
    fi
}

# 显示帮助信息
show_help() {
    echo -e "${BLUE}ComfyUI Web Service IPv6切换脚本${NC}"
    echo ""
    echo "用法: $0 [选项]"
    echo ""
    echo "选项:"
    echo "  status, s     显示当前状态"
    echo "  ipv4, 4       切换到IPv4专用模式 (推荐)"
    echo "  dual, d       切换到双栈模式"
    echo "  restart, r    重启服务"
    echo "  help, h       显示此帮助信息"
    echo ""
    echo "示例:"
    echo "  $0 status      # 查看当前状态"
    echo "  $0 ipv4        # 切换到IPv4模式"
    echo "  $0 restart     # 重启服务"
}

# 主函数
case "${1:-status}" in
    "status"|"s")
        show_status
        ;;
    "ipv4"|"4")
        switch_to_ipv4
        ;;
    "dual"|"d")
        switch_to_dual
        ;;
    "restart"|"r")
        restart_service
        ;;
    "help"|"h"|"-h"|"--help")
        show_help
        ;;
    *)
        echo -e "${RED}错误: 未知选项 '$1'${NC}"
        echo "使用 '$0 help' 查看帮助信息"
        exit 1
        ;;
esac
