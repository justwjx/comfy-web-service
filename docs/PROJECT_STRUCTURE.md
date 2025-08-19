# ComfyUI Web Service 项目结构

## 📁 整理后的项目结构

```
comfy-web-service/
├── 📄 核心文件
│   ├── app.py                 # 主应用文件 (108KB)
│   ├── config.py              # 配置文件
│   ├── requirements.txt       # Python依赖
│   ├── start.sh              # 主启动脚本
│   ├── .env                  # 环境变量配置
│   └── README.md             # 项目说明
│
├── 📁 docs/                  # 文档目录
│   ├── 📁 guides/            # 使用指南
│   │   ├── IPV6_OPTIMIZATION_GUIDE.md
│   │   ├── IPV6_SETUP.md
│   │   ├── IPV6_SUCCESS.md
│   │   ├── SCRIPTS_README.md
│   │   └── SCRIPTS_LIST.md
│   │
│   ├── 📁 scripts/           # 脚本文件
│   │   ├── ipv6_switch.sh
│   │   ├── quick_switch.sh
│   │   ├── performance_test.sh
│   │   ├── activate_env.sh
│   │   └── start_with_ipv6.sh
│   │
│   └── 📁 performance/       # 性能相关
│       ├── test_ipv6.py
│       ├── MOBILE_OPTIMIZATION.md
│       ├── CONNECTION_IMPROVEMENTS.md
│       └── NODE_ID_OPTIMIZATION.md
│
├── 📁 logs/                  # 日志目录
│   └── app.log              # 应用日志
│
├── 📁 outputs/               # 输出文件目录
├── 📁 static/                # 静态文件
├── 📁 templates/             # 模板文件
├── 📁 workflow/              # 工作流文件
├── 📁 venv/                  # Python虚拟环境
├── 📁 temp/                  # 临时文件目录
│
└── 🔗 符号链接 (保持脚本可用性)
    ├── ipv6_switch.sh -> docs/scripts/ipv6_switch.sh
    ├── quick_switch.sh -> docs/scripts/quick_switch.sh
    ├── performance_test.sh -> docs/scripts/performance_test.sh
    └── activate_env.sh -> docs/scripts/activate_env.sh
```

## 🎯 整理成果

### ✅ 文件分类整理
- **脚本文件**: 移动到 `docs/scripts/` 目录
- **使用指南**: 移动到 `docs/guides/` 目录  
- **性能文档**: 移动到 `docs/performance/` 目录
- **日志文件**: 移动到 `logs/` 目录

### ✅ 清理工作
- 删除 `__pycache__/` 目录
- 删除 `.specstory/` 目录
- 清理临时文件

### ✅ 保持可用性
- 创建符号链接，保持脚本在根目录可用
- 更新主README文件
- 更新.gitignore文件

## 🚀 使用方式

### 启动服务
```bash
./start.sh
```

### 查看状态
```bash
./ipv6_switch.sh status
```

### 性能测试
```bash
./performance_test.sh
```

### 快速切换
```bash
./quick_switch.sh
```

## 📊 文件统计

- **总文件数**: 约30个文件
- **脚本文件**: 5个 (整理到docs/scripts/)
- **文档文件**: 9个 (整理到docs/guides/和docs/performance/)
- **核心文件**: 6个 (保留在根目录)
- **目录**: 8个

## 🎉 优化效果

1. **结构清晰**: 文件按功能分类，易于维护
2. **保持可用**: 符号链接确保脚本仍然可用
3. **文档完整**: 所有文档都有明确的位置
4. **易于扩展**: 新文件可以按类别添加到相应目录

## 📝 维护建议

1. **新脚本**: 添加到 `docs/scripts/` 并创建符号链接
2. **新文档**: 按类型添加到 `docs/guides/` 或 `docs/performance/`
3. **日志文件**: 自动保存到 `logs/` 目录
4. **临时文件**: 使用 `temp/` 目录

项目现在具有清晰的结构和良好的可维护性！🎯 