# 硬编码地址修复说明

## 🐛 问题描述

您发现了一个重要问题：脚本中的访问地址是硬编码的，这会导致在不同网络环境下脚本无法正确显示访问地址。

### 原始硬编码地址
```bash
# ipv6_switch.sh
echo "  http://172.16.10.224:5000"
echo "  http://172.16.10.225:5000"
echo "IPv6: http://[2409:8a20:8e25:a261:7656:3cff:feb3:26ed]:5000"

# performance_test.sh
time_result=$(curl -4 -s -o /dev/null -w "%{time_total}" http://172.16.10.224:5000 2>/dev/null)
time_result=$(curl -6 -s -o /dev/null -w "%{time_total}" http://[2409:8a20:8e25:a261:7656:3cff:feb3:26ed]:5000 2>/dev/null)
```

## ✅ 修复方案

### 1. 动态地址获取函数

创建了通用的网络地址获取函数：

```bash
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
```

### 2. 访问地址显示函数

```bash
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
```

## 🔧 修复的脚本

### 1. `docs/scripts/ipv6_switch.sh`
- ✅ 添加动态地址获取功能
- ✅ 替换硬编码地址显示
- ✅ 支持多网络接口

### 2. `docs/scripts/quick_switch.sh`
- ✅ 添加动态地址获取功能
- ✅ 替换硬编码地址显示
- ✅ 保持交互式体验

### 3. `docs/scripts/performance_test.sh`
- ✅ 添加动态地址获取功能
- ✅ 替换硬编码测试地址
- ✅ 智能选择测试地址

## 🎯 修复效果

### 修复前
```bash
$ ./ipv6_switch.sh ipv4
✓ 已切换到IPv4专用模式
访问地址:
  http://172.16.10.224:5000
  http://172.16.10.225:5000
```

### 修复后
```bash
$ ./ipv6_switch.sh ipv4
✓ 已切换到IPv4专用模式
访问地址:
  IPv4: http://172.16.10.224:5000
  IPv4: http://172.16.10.225:5000
  IPv6: http://[2409:8a20:8e25:a261:fe18:5ca:5913:c5ea]:5000
  IPv6: http://[2409:8a20:8e25:a261:7656:3cff:feb3:26ed]:5000
  IPv6: http://[fd27:392a:635d:e40:363d:e13c:64f4:209a]:5000
  IPv6: http://[fd27:392a:635d:e40:7656:3cff:feb3:26ed]:5000
  IPv6: http://[fd27:392a:635d:e40:c7dc:ecc4:eac1:f0d1]:5000
  IPv6: http://[fd27:392a:635d:e40:ec6:ccff:fe99:8e80]:5000
```

## 🚀 优势

1. **动态适应**: 自动检测所有可用的网络接口
2. **多接口支持**: 支持多个IPv4和IPv6地址
3. **环境无关**: 在不同网络环境下都能正常工作
4. **智能过滤**: 自动过滤本地回环和链路本地地址
5. **端口配置**: 支持通过环境变量配置端口

## 📝 使用方式

### 环境变量配置
```bash
# 自定义端口
export PORT=8080
./ipv6_switch.sh status

# 自定义主机
export HOST=0.0.0.0
./ipv6_switch.sh restart
```

### 脚本使用
```bash
# 查看状态和地址
./ipv6_switch.sh status

# 切换模式
./ipv6_switch.sh ipv4
./ipv6_switch.sh dual

# 性能测试
./performance_test.sh

# 快速切换
./quick_switch.sh
```

## 🎉 总结

通过这次修复，脚本现在能够：

✅ **动态获取网络地址** - 不再依赖硬编码  
✅ **支持多网络接口** - 显示所有可用地址  
✅ **环境自适应** - 在不同网络环境下正常工作  
✅ **智能地址过滤** - 自动排除无效地址  
✅ **配置灵活** - 支持环境变量配置  

现在脚本具有更好的可移植性和适应性！🎯 