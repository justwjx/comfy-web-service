# ComfyUI Web Service 脚本使用指南

## 脚本概览

本项目包含多个脚本，用于简化环境配置、启动和测试过程。**所有脚本都会自动处理虚拟环境激活**。

## 脚本列表

### 1. `start.sh` - 通用启动脚本（推荐）

**功能**: 自动处理虚拟环境、依赖安装、IPv6配置和应用启动

**使用方法**:
```bash
./start.sh
```

**特点**:
- ✅ 自动创建和激活虚拟环境
- ✅ 自动安装依赖包
- ✅ 默认启用IPv6支持
- ✅ 自动检测系统IPv6支持
- ✅ 端口占用检查
- ✅ 显示所有访问地址

### 2. `start_with_ipv6.sh` - IPv6专用启动脚本

**功能**: 专门用于IPv6服务启动

**使用方法**:
```bash
./start_with_ipv6.sh
```

**特点**:
- ✅ 强制使用IPv6地址 `::`
- ✅ 自动激活虚拟环境
- ✅ 依赖包检查
- ✅ IPv6支持验证

### 3. `activate_env.sh` - 环境配置脚本

**功能**: 仅配置环境，不启动应用

**使用方法**:
```bash
./activate_env.sh
```

**特点**:
- ✅ 创建和激活虚拟环境
- ✅ 安装依赖包
- ✅ 检查IPv6支持
- ✅ 显示后续可用命令

### 4. `test_ipv6.py` - IPv6连接测试脚本

**功能**: 测试IPv6和IPv4连接

**使用方法**:
```bash
# 激活虚拟环境后运行
source venv/bin/activate
python3 test_ipv6.py

# 或指定端口
python3 test_ipv6.py 5000
```

**特点**:
- ✅ 测试系统IPv6支持
- ✅ 测试本地IPv6连接
- ✅ 测试IPv4回退连接
- ✅ 详细的连接状态报告

## 推荐使用流程

### 首次使用

1. **配置环境**:
   ```bash
   ./activate_env.sh
   ```

2. **启动服务**:
   ```bash
   ./start.sh
   ```

3. **测试连接**:
   ```bash
   source venv/bin/activate
   python3 test_ipv6.py
   ```

### 日常使用

直接使用通用启动脚本：
```bash
./start.sh
```

## 环境变量配置

### 通过环境变量自定义配置

```bash
# 使用IPv4
HOST=0.0.0.0 ./start.sh

# 使用自定义端口
PORT=8080 ./start.sh

# 启用调试模式
DEBUG=True ./start.sh

# 组合配置
HOST=:: PORT=8080 DEBUG=True ./start.sh
```

### 通过.env文件配置

```bash
# 复制配置模板
cp env.example .env

# 编辑配置
nano .env
```

## 访问地址

启动成功后，可以通过以下地址访问：

### IPv4地址
- `http://172.16.10.224:5000`
- `http://172.16.10.225:5000`

### IPv6地址
- `http://[2409:8a20:8e25:a261:7656:3cff:feb3:26ed]:5000` (全局地址)
- `http://[fd27:392a:635d:e40:7656:3cff:feb3:26ed]:5000` (ULA地址)
- `http://[::1]:5000` (本地回环)

## 故障排除

### 1. 虚拟环境问题

```bash
# 重新创建虚拟环境
rm -rf venv
./activate_env.sh
```

### 2. 依赖包问题

```bash
# 激活虚拟环境
source venv/bin/activate

# 重新安装依赖
pip install -r requirements.txt
```

### 3. 端口占用问题

```bash
# 查看端口占用
ss -tlnp | grep :5000

# 使用不同端口
PORT=5001 ./start.sh
```

### 4. IPv6连接问题

```bash
# 运行连接测试
source venv/bin/activate
python3 test_ipv6.py
```

## 注意事项

1. **虚拟环境**: 所有脚本都会自动处理虚拟环境，无需手动激活
2. **依赖管理**: 脚本会自动检查并安装必要的依赖包
3. **IPv6支持**: 系统会自动检测IPv6支持并相应配置
4. **端口管理**: 脚本会检查端口占用并提供警告
5. **错误处理**: 脚本包含完整的错误检查和提示

## 脚本权限

确保所有脚本都有执行权限：

```bash
chmod +x *.sh
```

如果遇到权限问题，可以手动添加：

```bash
chmod +x start.sh
chmod +x start_with_ipv6.sh
chmod +x activate_env.sh
``` 