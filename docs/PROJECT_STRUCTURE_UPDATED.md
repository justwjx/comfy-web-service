# ComfyUI Web Service 项目结构 (更新版)

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
├── 📁 scripts/               # 脚本目录 (统一管理)
│   ├── ipv6_switch.sh        # IPv6切换脚本
│   ├── quick_switch.sh       # 快速切换脚本
│   ├── performance_test.sh   # 性能测试脚本
│   ├── activate_env.sh       # 环境激活脚本
│   ├── start_service.sh      # 服务启动脚本
│   ├── stop_service.sh       # 服务停止脚本
│   ├── start_optimized.sh    # 优化启动脚本
│   ├── reorganize_scripts.sh # 脚本整理工具
│   └── start.sh              # 通用启动脚本
│
├── 📁 docs/                  # 文档目录 (分类管理)
│   ├── README.md             # 文档主页
│   ├── SERVICE_README.md     # 服务说明
│   ├── SUMMARY.md            # 项目总结
│   ├── ORGANIZATION_SUMMARY.md # 组织总结
│   ├── DIRECTORY_STRUCTURE.md # 目录结构说明
│   ├── NETWORK_TOOLS_MIGRATION.md # 网络工具迁移
│   │
│   ├── 📁 features/          # 功能文档
│   │   ├── FEATURES.md
│   │   ├── actual_seed_feature.md
│   │   └── metadata_feature.md
│   │
│   ├── 📁 fixes/             # 修复文档
│   │   ├── FIXES_SUMMARY.md
│   │   ├── SEED_FIX_SUMMARY.md
│   │   ├── DEFAULT_VALUES_FIX_SUMMARY.md
│   │   ├── HARDCODED_ADDRESS_FIX.md
│   │   └── metadata_fix.md
│   │
│   ├── 📁 optimization/      # 优化文档
│   │   ├── OPTIMIZATION_README.md
│   │   ├── OPTIMIZATION_SUMMARY.md
│   │   └── display_optimization.md
│   │
│   ├── 📁 guides/            # 使用指南
│   └── 📁 performance/       # 性能相关
│
├── 📁 debug_and_test/        # 调试和测试目录 (分类管理)
│   ├── 📁 python_tests/      # Python测试文件 (29个)
│   ├── 📁 html_tests/        # HTML测试文件 (10个)
│   └── 📁 image_tests/       # 图片测试文件 (2个)
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
    ├── ipv6_switch.sh -> scripts/ipv6_switch.sh
    ├── quick_switch.sh -> scripts/quick_switch.sh
    ├── performance_test.sh -> scripts/performance_test.sh
    └── activate_env.sh -> scripts/activate_env.sh
```

## 🎯 整理成果

### ✅ 脚本文件整理
- **统一位置**: 所有脚本文件移动到 `scripts/` 目录
- **功能分类**: 启动、停止、网络、性能测试等脚本分类管理
- **保持可用**: 通过符号链接保持根目录脚本的可用性
- **权限设置**: 所有脚本都有执行权限

### ✅ 文档文件整理
- **功能分类**: 按功能分为 features/、fixes/、optimization/ 等目录
- **清晰结构**: 每个目录都有明确的用途
- **易于查找**: 相关文档集中存放

### ✅ 测试文件整理
- **类型分类**: Python测试、HTML测试、图片测试分别存放
- **数量统计**: 
  - Python测试文件: 29个
  - HTML测试文件: 10个
  - 图片测试文件: 2个

### ✅ 清理工作
- 删除重复的符号链接
- 移除失效的脚本文件
- 清理docs目录中的脚本符号链接

## 🚀 使用方式

### 启动服务
```bash
./start.sh                    # 使用根目录符号链接
# 或
./scripts/start.sh            # 直接使用scripts目录
```

### 网络管理
```bash
./ipv6_switch.sh status       # 查看IPv6状态
./quick_switch.sh             # 快速网络切换
```

### 性能测试
```bash
./performance_test.sh         # 运行性能测试
```

### 环境管理
```bash
./activate_env.sh             # 激活Python环境
```

## 📊 文件统计

- **脚本文件**: 9个 (统一在scripts/目录)
- **文档文件**: 按功能分类，共15个主要文档
- **测试文件**: 41个 (按类型分类)
- **核心文件**: 6个 (保留在根目录)

## 🎉 优化效果

1. **结构清晰**: 文件按功能和类型分类，易于维护
2. **保持可用**: 符号链接确保脚本仍然可用
3. **文档完整**: 所有文档都有明确的位置和分类
4. **易于扩展**: 新文件可以按类别添加到相应目录
5. **便于查找**: 相关文件集中存放，提高查找效率

## 📝 维护建议

1. **新脚本**: 添加到 `scripts/` 并创建符号链接到根目录
2. **新文档**: 按类型添加到相应的docs子目录
3. **新测试**: 按类型添加到debug_and_test的相应子目录
4. **日志文件**: 自动保存到 `logs/` 目录
5. **临时文件**: 使用 `temp/` 目录

项目现在具有清晰的结构和良好的可维护性！🎯 