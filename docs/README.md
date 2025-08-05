# ComfyUI 移动端Web服务

一个移动端友好的ComfyUI工作流选择和执行界面，支持直接在手机或平板上运行ComfyUI工作流。

## 功能特点

- 📱 **移动端优化** - 完全响应式设计，完美适配手机和平板
- 🚀 **一键运行** - 简单点击即可执行ComfyUI工作流
- 📊 **实时状态** - 实时显示工作流执行进度和状态
- 🔍 **智能搜索** - 快速搜索和筛选工作流
- 💫 **现代界面** - 优美的现代化用户界面
- ⚡ **高性能** - 异步处理，支持多任务并发

## 快速开始

### 1. 环境要求

- Python 3.7+
- ComfyUI已安装并配置
- 现代浏览器

### 2. 安装和配置

```bash
# 克隆或下载项目
cd comfy-web-service

# 使用启动脚本自动设置环境
./start.sh setup

# 或手动设置
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 3. 配置环境

```bash
# 复制配置文件
cp env.example .env

# 编辑配置文件，设置你的ComfyUI路径
nano .env
```

重要配置项：
```env
# 设置你的ComfyUI安装路径
COMFYUI_PATH=/path/to/your/ComfyUI

# 设置服务端口（可选）
PORT=5000

# 设置主机地址（可选）
HOST=0.0.0.0
```

### 4. 添加工作流

将你的ComfyUI工作流JSON文件放入 `workflow/` 目录：

```bash
cp your-workflow.json workflow/
```

支持的文件格式：
- `.json` - ComfyUI导出的工作流文件

### 5. 启动服务

```bash
# 开发模式启动
./start.sh dev

# 或生产模式启动
./start.sh production

# 或直接运行Python文件
python app.py
```

### 6. 访问界面

打开浏览器访问：`http://localhost:5000`

在手机上访问：`http://你的服务器IP:5000`

## 项目结构

```
comfy-web-service/
├── app.py                 # 主应用文件
├── config.py             # 配置文件
├── requirements.txt      # Python依赖
├── start.sh             # 启动脚本
├── env.example          # 环境配置示例
├── README.md            # 说明文档
├── workflow/            # 工作流目录
│   ├── *.json          # ComfyUI工作流文件
├── templates/           # HTML模板
│   └── index.html      # 主页面
├── static/             # 静态资源
│   ├── css/
│   │   └── style.css   # 样式文件
│   └── js/
│       └── app.js      # 前端逻辑
└── output/             # 输出目录
```

## 使用说明

### 添加新工作流

1. 在ComfyUI中创建和测试你的工作流
2. 使用ComfyUI的"Save"功能保存为JSON文件
3. 将JSON文件复制到 `workflow/` 目录
4. 刷新Web界面即可看到新的工作流

### 运行工作流

1. 在Web界面中浏览可用的工作流
2. 点击工作流卡片查看详细信息
3. 点击"运行工作流"按钮
4. 确认运行后等待执行完成
5. 查看实时执行状态和输出结果

### 移动端优化功能

- **触摸友好** - 大按钮设计，适合手指操作
- **响应式布局** - 自适应各种屏幕尺寸
- **滑动操作** - 支持滑动和触摸手势
- **离线提示** - 网络状态检测和提示
- **PWA支持** - 可安装为桌面应用

## API接口

### 获取工作流列表
```http
GET /api/workflows
```

### 运行工作流
```http
POST /api/run
Content-Type: application/json

{
    "filename": "your-workflow.json"
}
```

### 查询任务状态
```http
GET /api/status/{task_id}
```

### 获取所有任务
```http
GET /api/tasks
```

## 配置选项

| 环境变量 | 默认值 | 说明 |
|---------|--------|------|
| HOST | 0.0.0.0 | 服务器绑定地址 |
| PORT | 5000 | 服务器端口 |
| DEBUG | False | 调试模式 |
| COMFYUI_PATH | /path/to/ComfyUI | ComfyUI安装路径 |
| COMFYUI_OUTPUT_DIR | ./output | 输出目录 |
| MAX_CONCURRENT_TASKS | 3 | 最大并发任务数 |
| TASK_TIMEOUT | 3600 | 任务超时时间（秒） |

## 故障排除

### 常见问题

1. **工作流不显示**
   - 检查 `workflow/` 目录是否存在
   - 确认JSON文件格式正确
   - 查看服务器日志

2. **无法运行工作流**
   - 检查ComfyUI路径配置
   - 确认ComfyUI依赖已安装
   - 检查权限设置

3. **移动端显示异常**
   - 确保使用现代浏览器
   - 检查网络连接
   - 尝试刷新页面

### 日志查看

```bash
# 查看应用日志
tail -f comfy-web-service.log

# 查看启动日志
./start.sh dev 2>&1 | tee startup.log
```

## 开发说明

### 本地开发

```bash
# 开发模式启动（自动重载）
./start.sh dev

# 或直接使用Flask
export FLASK_ENV=development
export FLASK_APP=app.py
flask run --host=0.0.0.0 --port=5000
```

### 生产部署

```bash
# 生产模式启动
./start.sh production

# 或使用PM2
pm2 start app.py --interpreter python3 --name comfy-web-service

# 或使用systemd服务
sudo systemctl start comfy-web-service
```

### Docker部署

```dockerfile
# Dockerfile示例
FROM python:3.9-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
EXPOSE 5000

CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:5000", "app:app"]
```

## 许可证

MIT License

## 贡献

欢迎提交Issue和Pull Request！

## 支持

如果遇到问题，请：

1. 查看本文档的故障排除部分
2. 查看项目Issues
3. 提交新的Issue描述问题

---

*Created with ❤️ for ComfyUI community*