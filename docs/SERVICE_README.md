# ComfyUI Web服务管理

## 概述

这个项目提供了一个Web界面来管理和运行ComfyUI工作流。服务可以在后台持续运行，即使终端窗口关闭。

## 快速开始

### 1. 启动服务

```bash
./start_service.sh
```

这将：
- 检查端口5000是否被占用
- 激活Python虚拟环境
- 在后台启动Web服务
- 显示进程ID和访问地址

### 2. 停止服务

```bash
./stop_service.sh
```

这将：
- 查找所有运行中的app.py进程
- 优雅地停止这些进程
- 确认端口已释放

## 服务管理

### 检查服务状态

```bash
# 检查端口占用
lsof -i :5000

# 检查进程
ps aux | grep python3 | grep app.py

# 检查服务响应
curl http://localhost:5000/api/comfyui/status
```

### 查看日志

```bash
# 实时查看日志
tail -f app.log

# 查看最新日志
tail -20 app.log
```

### 手动管理

如果脚本无法正常工作，可以手动管理：

```bash
# 启动服务
nohup python3 app.py > app.log 2>&1 &

# 停止服务
pkill -f "python3 app.py"

# 强制停止
pkill -9 -f "python3 app.py"
```

## 访问地址

- **Web界面**: http://localhost:5000
- **API状态**: http://localhost:5000/api/comfyui/status
- **工作流列表**: http://localhost:5000/api/workflows

## 注意事项

1. **端口冲突**: 如果端口5000被占用，服务将无法启动
2. **虚拟环境**: 确保已安装所有依赖：`pip install -r requirements.txt`
3. **ComfyUI**: 确保ComfyUI服务在端口8188上运行
4. **权限**: 确保脚本有执行权限：`chmod +x *.sh`

## 故障排除

### 端口被占用
```bash
# 查找占用端口的进程
lsof -i :5000

# 停止占用进程
kill <PID>
```

### 服务无法启动
```bash
# 检查日志
tail -f app.log

# 检查依赖
source venv/bin/activate
python3 -c "import flask; print('Flask OK')"
```

### 服务无响应
```bash
# 重启服务
./stop_service.sh
./start_service.sh
``` 