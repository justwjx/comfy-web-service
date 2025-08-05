# Comfy Web Service

一个基于Python的Web服务项目。

> 项目作者：justwjx (wjx@msn.cn)

## 项目结构

```
comfy-web-service/
├── app.py              # 主应用入口文件
├── config.py           # 配置文件
├── requirements.txt    # Python依赖包
├── env.example         # 环境变量示例
├── scripts/            # 脚本文件
│   ├── start.sh       # 启动脚本
│   ├── stop.sh        # 停止脚本
│   └── demo_new_features.py  # 演示脚本
├── docs/              # 文档
│   ├── FEATURES.md
│   ├── OPTIMIZATION_SUMMARY.md
│   └── DEFAULT_VALUES_FIX_SUMMARY.md
├── debug_and_test/    # 调试和测试文件
├── logs/              # 日志文件
├── outputs/           # 输出文件
├── static/            # 静态资源
├── templates/         # 前端模板
├── workflow/          # 工作流相关
└── venv/              # Python虚拟环境
```

## 快速开始

1. 激活虚拟环境：
   ```bash
   source venv/bin/activate
   ```

2. 安装依赖：
   ```bash
   pip install -r requirements.txt
   ```

3. 启动服务：
   ```bash
   ./scripts/start.sh
   ```

4. 停止服务：
   ```bash
   ./scripts/stop.sh
   ```

## 环境配置

复制 `env.example` 为 `.env` 并根据需要修改配置：
```bash
cp env.example .env
```

## 开发

- 测试文件请放在 `debug_and_test/` 目录
- 日志文件会自动保存到 `logs/` 目录
- 文档更新请放在 `docs/` 目录 