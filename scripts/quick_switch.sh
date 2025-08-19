#!/bin/bash

# ComfyUI Web Service 快速切换脚本

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

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

echo -e "${BLUE}=== ComfyUI Web Service 快速切换 ===${NC}"
echo ""

# 显示当前状态
echo -e "${YELLOW}当前状态:${NC}"
if [ -f ".env" ]; then
    HOST_CONFIG=$(grep "^HOST=" ".env" | cut -d'=' -f2)
else
    HOST_CONFIG="::"
fi

case "$HOST_CONFIG" in
    "::")
        echo -e "${GREEN}✓ 双栈模式 (IPv4 + IPv6)${NC}"
        ;;
    "0.0.0.0")
        echo -e "${YELLOW}⚠ IPv4专用模式${NC}"
        ;;
    *)
        echo -e "${RED}✗ 未知模式${NC}"
        ;;
esac

echo ""
echo "选择要切换的模式:"
echo "1) IPv4专用模式 (推荐 - 性能优化)"
echo "2) 双栈模式 (IPv4 + IPv6)"
echo "3) 查看当前状态"
echo "4) 退出"
echo ""

read -p "请输入选择 (1-4): " choice

case $choice in
    1)
        echo -e "${YELLOW}切换到IPv4专用模式...${NC}"
        ./ipv6_switch.sh ipv4
        echo ""
        echo -e "${YELLOW}重启服务以应用配置...${NC}"
        ./ipv6_switch.sh restart
        echo ""
        echo -e "${GREEN}✓ 已切换到IPv4专用模式${NC}"
        show_access_addresses
        ;;
    2)
        echo -e "${YELLOW}切换到双栈模式...${NC}"
        ./ipv6_switch.sh dual
        echo ""
        echo -e "${YELLOW}重启服务以应用配置...${NC}"
        ./ipv6_switch.sh restart
        echo ""
        echo -e "${GREEN}✓ 已切换到双栈模式${NC}"
        show_access_addresses
        ;;
    3)
        ./ipv6_switch.sh status
        ;;
    4)
        echo "退出"
        exit 0
        ;;
    *)
        echo -e "${RED}无效选择${NC}"
        exit 1
        ;;
esac 