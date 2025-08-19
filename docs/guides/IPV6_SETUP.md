# ComfyUI Web Service IPv6配置指南

## 概述

本指南将帮助您配置ComfyUI Web Service以支持IPv6访问，特别是针对172.16.10.224接口。

## 系统要求

- Linux系统（已确认支持IPv6）
- Python 3.x
- Flask框架

## 配置步骤

### 1. 验证IPv6支持

```bash
# 检查系统IPv6支持
python3 -c "import socket; print('IPv6支持:', socket.has_ipv6)"

# 查看网络接口IPv6地址
ip addr show | grep -E "inet6"
```

### 2. 修改应用配置

应用已更新为默认使用IPv6地址 `::`，这将同时支持IPv4和IPv6连接。

#### 环境变量配置

创建 `.env` 文件：

```bash
# 复制环境变量示例
cp env.example .env

# 编辑配置文件
nano .env
```

确保以下配置：

```env
# 服务器配置
HOST=::          # IPv6 (同时支持IPv4和IPv6)
PORT=5000
DEBUG=False
```

### 3. 启动应用

#### 方法1：使用通用启动脚本（推荐）

```bash
# 使用通用启动脚本（自动处理虚拟环境和IPv6）
./start.sh
```

#### 方法2：使用IPv6专用启动脚本

```bash
# 使用IPv6专用启动脚本
./start_with_ipv6.sh
```

#### 方法3：手动启动（需要先激活虚拟环境）

```bash
# 激活虚拟环境
source venv/bin/activate

# 设置环境变量并启动
export HOST="::"
export PORT=5000
python3 app.py
```

### 4. 防火墙配置

#### Ubuntu/Debian (ufw)

```bash
# 允许IPv6端口5000
sudo ufw allow 5000/tcp

# 检查防火墙状态
sudo ufw status
```

#### CentOS/RHEL (firewalld)

```bash
# 允许端口5000
sudo firewall-cmd --permanent --add-port=5000/tcp
sudo firewall-cmd --reload

# 检查防火墙状态
sudo firewall-cmd --list-all
```

#### iptables (手动配置)

```bash
# 允许IPv6端口5000
sudo ip6tables -A INPUT -p tcp --dport 5000 -j ACCEPT

# 保存规则
sudo ip6tables-save > /etc/iptables/rules.v6
```

### 5. 测试连接

#### 使用测试脚本

```bash
# 运行IPv6连接测试
python3 test_ipv6.py

# 指定端口测试
python3 test_ipv6.py 5000
```

#### 手动测试

```bash
# 测试IPv6连接
curl -6 http://[2409:8a20:8e25:a261:7656:3cff:feb3:26ed]:5000

# 测试IPv4连接
curl -4 http://172.16.10.224:5000

# 测试本地IPv6
curl -6 http://[::1]:5000
```

## 访问地址

配置完成后，您可以通过以下地址访问服务：

### IPv4地址
- `http://172.16.10.224:5000`
- `http://172.16.10.225:5000`

### IPv6地址
- `http://[2409:8a20:8e25:a261:7656:3cff:feb3:26ed]:5000` (全局地址)
- `http://[fd27:392a:635d:e40:7656:3cff:feb3:26ed]:5000` (ULA地址)
- `http://[::1]:5000` (本地回环)

## 故障排除

### 1. 连接被拒绝

**问题**: 无法通过IPv6连接到服务

**解决方案**:
```bash
# 检查服务是否正在监听IPv6
ss -tlnp | grep :5000

# 应该看到类似输出：
# LISTEN 0 128 [::]:5000 [::]:* users:(("python",pid=xxx,fd=6))
```

### 2. 防火墙阻止连接

**问题**: 防火墙阻止IPv6连接

**解决方案**:
```bash
# 检查IPv6防火墙规则
sudo ip6tables -L

# 临时允许所有IPv6连接（仅用于测试）
sudo ip6tables -P INPUT ACCEPT
```

### 3. 网络接口问题

**问题**: IPv6地址不可用

**解决方案**:
```bash
# 重新启用IPv6
sudo sysctl -w net.ipv6.conf.all.disable_ipv6=0
sudo sysctl -w net.ipv6.conf.default.disable_ipv6=0

# 重启网络服务
sudo systemctl restart networking
```

### 4. 应用启动失败

**问题**: 应用无法绑定到IPv6地址

**解决方案**:
```bash
# 检查端口是否被占用
ss -tlnp | grep :5000

# 杀死占用端口的进程
sudo kill -9 <PID>

# 或者使用不同端口
export PORT=5001
python3 app.py
```

## 性能优化

### 1. 启用IPv6优化

```bash
# 优化IPv6性能
sudo sysctl -w net.ipv6.conf.all.optimistic_dad=1
sudo sysctl -w net.ipv6.conf.default.optimistic_dad=1
```

### 2. 持久化配置

```bash
# 编辑sysctl配置
sudo nano /etc/sysctl.conf

# 添加以下行
net.ipv6.conf.all.optimistic_dad=1
net.ipv6.conf.default.optimistic_dad=1

# 应用配置
sudo sysctl -p
```

## 安全注意事项

1. **防火墙配置**: 确保只开放必要的端口
2. **访问控制**: 考虑添加身份验证机制
3. **日志监控**: 监控IPv6连接日志
4. **定期更新**: 保持系统和依赖包更新

## 监控和日志

### 查看连接日志

```bash
# 查看应用日志
tail -f comfy-web-service.log

# 查看系统连接
ss -tlnp | grep :5000

# 查看IPv6连接统计
cat /proc/net/sockstat6
```

## 总结

通过以上配置，您的ComfyUI Web Service现在应该能够：

1. ✅ 同时支持IPv4和IPv6连接
2. ✅ 通过172.16.10.224接口的IPv6地址访问
3. ✅ 提供稳定的网络服务
4. ✅ 支持多客户端并发访问

如果遇到任何问题，请参考故障排除部分或运行测试脚本进行诊断。 