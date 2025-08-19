# ComfyUI Web Service 脚本列表

## 📋 脚本概览

本项目包含以下脚本，所有脚本都支持虚拟环境自动激活：

| 脚本名称 | 功能描述 | 推荐使用场景 |
|---------|---------|-------------|
| `start.sh` | 通用启动脚本 | 日常启动服务 |
| `ipv6_switch.sh` | IPv6模式切换 | 网络模式管理 |
| `quick_switch.sh` | 快速交互切换 | 用户友好切换 |
| `performance_test.sh` | 性能测试 | 性能监控和对比 |
| `activate_env.sh` | 环境配置 | 首次设置 |

## 🚀 快速开始

### 首次使用
```bash
# 1. 配置环境
./activate_env.sh

# 2. 启动服务 (IPv4模式)
./start.sh
```

### 日常使用
```bash
# 启动服务
./start.sh

# 检查状态
./ipv6_switch.sh status

# 性能测试
./performance_test.sh
```

## 📖 详细说明

### 1. `start.sh` - 通用启动脚本
**功能**: 自动处理虚拟环境、依赖安装、IPv6配置和应用启动

**特点**:
- ✅ 自动创建和激活虚拟环境
- ✅ 自动安装依赖包
- ✅ 默认启用IPv4模式 (性能优化)
- ✅ 自动检测系统支持
- ✅ 端口占用检查
- ✅ 显示所有访问地址

**使用方法**:
```bash
./start.sh
```

### 2. `ipv6_switch.sh` - IPv6切换脚本
**功能**: 在IPv4专用模式和双栈模式之间切换

**特点**:
- ✅ 支持IPv4专用模式 (推荐)
- ✅ 支持双栈模式 (IPv4 + IPv6)
- ✅ 自动重启服务
- ✅ 状态检查和显示

**使用方法**:
```bash
./ipv6_switch.sh status    # 查看状态
./ipv6_switch.sh ipv4      # 切换到IPv4模式
./ipv6_switch.sh dual      # 切换到双栈模式
./ipv6_switch.sh restart   # 重启服务
./ipv6_switch.sh help      # 查看帮助
```

### 3. `quick_switch.sh` - 快速切换脚本
**功能**: 提供交互式菜单进行模式切换

**特点**:
- ✅ 用户友好的交互界面
- ✅ 一键完成切换和重启
- ✅ 显示当前状态和访问地址

**使用方法**:
```bash
./quick_switch.sh
```

### 4. `performance_test.sh` - 性能测试脚本
**功能**: 测试和对比IPv4/IPv6性能

**特点**:
- ✅ 多次测试取平均值
- ✅ 性能对比分析
- ✅ 智能建议

**使用方法**:
```bash
./performance_test.sh
```

### 5. `activate_env.sh` - 环境配置脚本
**功能**: 配置Python虚拟环境和依赖

**特点**:
- ✅ 自动创建虚拟环境
- ✅ 安装依赖包
- ✅ 检查IPv6支持
- ✅ 显示后续可用命令

**使用方法**:
```bash
./activate_env.sh
```

## 🎯 使用建议

### 生产环境
```bash
# 推荐使用IPv4专用模式
./ipv6_switch.sh ipv4
./ipv6_switch.sh restart

# 定期性能测试
./performance_test.sh
```

### 开发环境
```bash
# 可以使用双栈模式进行测试
./ipv6_switch.sh dual
./ipv6_switch.sh restart
```

### 故障排除
```bash
# 检查状态
./ipv6_switch.sh status

# 重新配置环境
./activate_env.sh

# 重新启动
./start.sh
```

## 📊 性能对比

### IPv4专用模式 (推荐)
- 响应时间: 0.0007秒
- 连接稳定性: 优秀
- 网络性能: 最佳

### 双栈模式
- IPv4响应时间: 0.0007秒
- IPv6响应时间: 较慢 (有重传)
- 连接稳定性: IPv4优秀，IPv6一般

## 🔧 脚本权限

确保所有脚本都有执行权限：
```bash
chmod +x *.sh
```

## 📝 注意事项

1. **虚拟环境**: 所有脚本都会自动处理虚拟环境
2. **依赖管理**: 脚本会自动检查并安装必要的依赖包
3. **配置持久化**: 配置更改会保存到 `.env` 文件
4. **服务重启**: 切换模式后需要重启服务才能生效
5. **性能优化**: 建议在生产环境使用IPv4专用模式

## 🎉 总结

通过这些脚本，您可以：
- ✅ 轻松管理IPv6/IPv4网络模式
- ✅ 获得最佳的网络性能
- ✅ 简化服务启动和管理
- ✅ 监控和优化服务性能

现在您可以享受高性能、易管理的ComfyUI Web Service！ 