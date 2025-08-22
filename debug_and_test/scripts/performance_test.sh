#!/bin/bash

# ComfyUI Web Service 性能对比测试脚本

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

# 获取测试地址
get_test_addresses() {
    local addresses
    addresses=$(get_network_addresses)
    
    local ipv4_line=$(echo "$addresses" | grep "^ipv4:")
    local ipv6_line=$(echo "$addresses" | grep "^ipv6:")
    
    local port=${PORT:-5000}
    
    # 获取第一个IPv4地址
    if [[ $ipv4_line =~ ipv4:(.+) ]]; then
        local ipv4_addrs="${BASH_REMATCH[1]}"
        if [[ -n $ipv4_addrs ]]; then
            TEST_IPV4_ADDR=$(echo $ipv4_addrs | awk '{print $1}')
        fi
    fi
    
    # 获取第一个IPv6地址
    if [[ $ipv6_line =~ ipv6:(.+) ]]; then
        local ipv6_addrs="${BASH_REMATCH[1]}"
        if [[ -n $ipv6_addrs ]]; then
            TEST_IPV6_ADDR=$(echo $ipv6_addrs | awk '{print $1}')
        fi
    fi
}

echo -e "${BLUE}=== ComfyUI Web Service 性能对比测试 ===${NC}"
echo ""

# 检查服务是否运行
if ! ss -tlnp | grep -q ":5000 "; then
    echo -e "${RED}✗ 服务未运行，请先启动服务${NC}"
    exit 1
fi

# 获取测试地址
get_test_addresses

# 检查是否有可用的测试地址
if [ -z "$TEST_IPV4_ADDR" ]; then
    echo -e "${RED}✗ 未找到可用的IPv4地址${NC}"
    exit 1
fi

# 测试次数
TEST_COUNT=5

echo -e "${YELLOW}开始性能测试 (每个测试重复 $TEST_COUNT 次)...${NC}"
echo ""

# IPv4性能测试
echo -e "${BLUE}=== IPv4性能测试 ===${NC}"
echo "测试地址: http://$TEST_IPV4_ADDR:5000"
ipv4_times=()
for i in $(seq 1 $TEST_COUNT); do
    echo -n "测试 $i/$TEST_COUNT: "
    time_result=$(curl -4 -s -o /dev/null -w "%{time_total}" http://$TEST_IPV4_ADDR:5000 2>/dev/null)
    ipv4_times+=($time_result)
    echo "${time_result}s"
done

# 计算IPv4平均时间
ipv4_sum=0
for time in "${ipv4_times[@]}"; do
    ipv4_sum=$(echo "$ipv4_sum + $time" | bc -l)
done
ipv4_avg=$(echo "scale=4; $ipv4_sum / $TEST_COUNT" | bc -l)

echo ""
echo -e "${GREEN}IPv4平均响应时间: ${ipv4_avg}s${NC}"

# 检查当前模式
if [ -f ".env" ]; then
    HOST_CONFIG=$(grep "^HOST=" ".env" | cut -d'=' -f2)
else
    HOST_CONFIG="::"
fi

# 如果是双栈模式，测试IPv6性能
if [ "$HOST_CONFIG" = "::" ] && [ -n "$TEST_IPV6_ADDR" ]; then
    echo ""
    echo -e "${BLUE}=== IPv6性能测试 ===${NC}"
    echo "测试地址: http://[$TEST_IPV6_ADDR]:5000"
    ipv6_times=()
    for i in $(seq 1 $TEST_COUNT); do
        echo -n "测试 $i/$TEST_COUNT: "
        time_result=$(curl -6 -s -o /dev/null -w "%{time_total}" http://[$TEST_IPV6_ADDR]:5000 2>/dev/null)
        if [ $? -eq 0 ]; then
            ipv6_times+=($time_result)
            echo "${time_result}s"
        else
            echo "失败"
        fi
    done
    
    # 计算IPv6平均时间
    if [ ${#ipv6_times[@]} -gt 0 ]; then
        ipv6_sum=0
        for time in "${ipv6_times[@]}"; do
            ipv6_sum=$(echo "$ipv6_sum + $time" | bc -l)
        done
        ipv6_avg=$(echo "scale=4; $ipv6_sum / ${#ipv6_times[@]}" | bc -l)
        
        echo ""
        echo -e "${GREEN}IPv6平均响应时间: ${ipv6_avg}s${NC}"
        
        # 性能对比
        echo ""
        echo -e "${BLUE}=== 性能对比 ===${NC}"
        if (( $(echo "$ipv4_avg < $ipv6_avg" | bc -l) )); then
            improvement=$(echo "scale=2; (($ipv6_avg - $ipv4_avg) / $ipv6_avg) * 100" | bc -l)
            echo -e "${GREEN}✓ IPv4比IPv6快 ${improvement}%${NC}"
        else
            improvement=$(echo "scale=2; (($ipv4_avg - $ipv6_avg) / $ipv4_avg) * 100" | bc -l)
            echo -e "${YELLOW}⚠ IPv6比IPv4快 ${improvement}%${NC}"
        fi
    else
        echo -e "${RED}✗ IPv6测试失败${NC}"
    fi
else
    echo ""
    echo -e "${YELLOW}当前为IPv4专用模式，跳过IPv6测试${NC}"
fi

echo ""
echo -e "${BLUE}=== 测试完成 ===${NC}"
echo "建议:"
if [ "$HOST_CONFIG" = "0.0.0.0" ]; then
    echo -e "${GREEN}✓ 当前为IPv4专用模式，性能已优化${NC}"
elif [ "$HOST_CONFIG" = "::" ]; then
    if (( $(echo "$ipv4_avg < $ipv6_avg" | bc -l) )); then
        echo -e "${YELLOW}⚠ 建议切换到IPv4专用模式以获得更好性能${NC}"
        echo "  运行: ./ipv6_switch.sh ipv4"
    else
        echo -e "${GREEN}✓ 当前双栈模式性能良好${NC}"
    fi
fi 