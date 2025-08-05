# 目录结构说明

## 项目根目录

```
comfy-web-service/
├── app.py                 # 主应用程序文件
├── config.py              # 配置文件
├── requirements.txt       # Python依赖包
├── env.example           # 环境变量示例
├── app.log               # 应用程序日志
├── gallery.html          # 图片画廊页面
├── test.html             # 测试页面
├── __pycache__/          # Python缓存目录
├── venv/                 # Python虚拟环境
├── templates/            # Flask模板目录
├── static/               # 静态文件目录
├── workflow/             # ComfyUI工作流文件
├── outputs/              # 生成的图片输出目录
├── debug_and_test/       # 调试和测试文件
├── docs/                 # 文档目录
├── scripts/              # 启动脚本目录
└── 其他核心文件...
```

## 子目录详细说明

### debug_and_test/
包含所有用于调试和测试的文件：

**Python测试文件:**
- `test_*.py` - 各种功能测试脚本
- `debug_*.py` - 调试脚本
- `demo_features.py` - 功能演示脚本

**HTML测试文件:**
- `test_*.html` - 前端测试页面
- `debug.html` - 调试页面

**测试图片:**
- `test_*.png` - 测试用的图片文件

### docs/
包含项目相关的所有文档：

- `README.md` - 项目主要说明文档
- `SERVICE_README.md` - 服务说明文档
- `SEED_FIX_SUMMARY.md` - 种子参数修复总结
- `SUMMARY.md` - 项目总结文档
- `OPTIMIZATION_README.md` - 优化说明文档
- `FIXES_SUMMARY.md` - 修复总结文档

### scripts/
包含各种启动和管理脚本：

- `start_service.sh` - 启动ComfyUI Web服务
- `stop_service.sh` - 停止服务
- `start_optimized.sh` - 优化启动脚本
- `start.sh` - 通用启动脚本

### 网络工具 (独立项目)
网络工具已移动到主目录的独立文件夹：`~/network_tools/`

**包含文件:**
- `enhanced_gateway_switch.sh` - 网关切换脚本（支持 gw1、gw2、gwstatus 命令）
- `advanced_network_setup.sh` - 高级网络设置脚本
- `gateway_config.conf` - 网关配置文件
- `fix_network_routing.sh` - 网络路由修复脚本
- `network_debug.sh` - 网络调试脚本
- `ssh_connection_info.txt` - SSH连接信息

**网络命令别名:**
- `gw1` - 切换到网关1
- `gw2` - 切换到网关2  
- `gwstatus` - 显示网络状态

## 使用说明

### 启动服务
```bash
# 使用脚本目录中的启动脚本
./scripts/start_service.sh
```

### 查看文档
```bash
# 查看项目文档
cat docs/README.md

# 查看修复总结
cat docs/SEED_FIX_SUMMARY.md
```

### 运行测试
```bash
# 进入测试目录
cd debug_and_test

# 运行测试脚本
python3 test_original_conversion.py
```

### 网络工具
```bash
# 查看网络状态
gwstatus

# 切换到网关1
gw1

# 切换到网关2
gw2

# 进入网络工具目录
cd ~/network_tools

# 运行网络设置脚本
./advanced_network_setup.sh
```

## 注意事项

1. **主程序文件**: `app.py` 是核心应用程序，不要移动
2. **配置文件**: `config.py` 和 `env.example` 保持在工作根目录
3. **日志文件**: `app.log` 会持续更新，保持在工作根目录
4. **虚拟环境**: `venv/` 目录包含Python依赖，不要删除
5. **输出目录**: `outputs/` 包含生成的图片，定期清理
6. **缓存目录**: `__pycache__/` 可以安全删除，会自动重建

## 清理建议

- 定期清理 `outputs/` 目录中的旧图片
- 删除 `__pycache__/` 目录以释放空间
- 清理 `app.log` 文件以控制日志大小
- 定期检查 `debug_and_test/` 目录，删除不再需要的测试文件 