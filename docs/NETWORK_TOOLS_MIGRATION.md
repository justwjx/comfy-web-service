# 网络工具迁移说明

## 迁移概述

网络工具已从项目目录 `comfy-web-service/network_tools/` 移动到主目录的独立文件夹 `~/network_tools/`，使其成为独立的项目工具。

## 迁移原因

1. **独立性**: 网络工具是系统级工具，不依赖于特定的项目
2. **可重用性**: 可以在任何项目中或系统级别使用
3. **维护性**: 独立管理，不影响项目结构
4. **访问性**: 从任何位置都可以访问

## 迁移内容

### 移动的文件
- `enhanced_gateway_switch.sh` - 网关切换脚本
- `advanced_network_setup.sh` - 高级网络设置脚本
- `gateway_config.conf` - 网关配置文件
- `fix_network_routing.sh` - 网络路由修复脚本
- `network_debug.sh` - 网络调试脚本
- `ssh_connection_info.txt` - SSH连接信息

### 更新的配置
- 更新了 `~/.bashrc` 中的别名路径
- 清理了重复的别名定义
- 确保所有脚本都有执行权限

## 别名配置

```bash
# 在 ~/.bashrc 中的配置
alias gw1="~/network_tools/enhanced_gateway_switch.sh 1"
alias gw2="~/network_tools/enhanced_gateway_switch.sh 2"
alias gwstatus="~/network_tools/enhanced_gateway_switch.sh status"
```

## 使用方法

### 网络命令
```bash
# 查看网络状态
gwstatus

# 切换到网关1
gw1

# 切换到网关2
gw2
```

### 直接访问
```bash
# 进入网络工具目录
cd ~/network_tools

# 查看所有工具
ls -la

# 运行特定脚本
./advanced_network_setup.sh
./network_debug.sh
```

## 验证

迁移后，所有网络命令都应该正常工作：

```bash
# 测试网络状态命令
gwstatus

# 应该显示当前网络状态，包括：
# - 接口信息
# - 网关配置
# - 当前路由状态
# - 策略路由规则
# - 网络连接测试
```

**验证结果:**
- ✅ `gwstatus` 命令正常工作
- ✅ `gw1` 和 `gw2` 别名正确配置
- ✅ 脚本路径指向 `~/network_tools/`
- ✅ 所有网络工具文件完整且可执行

## 注意事项

1. **路径依赖**: 别名现在指向 `~/network_tools/` 目录
2. **权限**: 所有脚本都已设置执行权限
3. **配置**: 网关配置文件保持在 `~/network_tools/gateway_config.conf`
4. **独立性**: 网络工具现在是完全独立的，不依赖于任何特定项目

## 恢复方法

如果需要恢复网络工具到项目目录：

```bash
# 1. 创建项目目录
mkdir -p comfy-web-service/network_tools

# 2. 移动文件
mv ~/network_tools/* comfy-web-service/network_tools/

# 3. 更新别名
sed -i 's|~/network_tools/enhanced_gateway_switch.sh|~/comfy-web-service/network_tools/enhanced_gateway_switch.sh|g' ~/.bashrc

# 4. 重新加载配置
source ~/.bashrc
```

## 总结

网络工具已成功迁移到主目录的独立文件夹，保持了所有功能的完整性，同时提高了工具的独立性和可重用性。 