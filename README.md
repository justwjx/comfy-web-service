# ComfyUI Web Service

一个移动端友好的ComfyUI工作流Web服务，支持IPv4/IPv6网络优化和通用化工作流适配。

## 🚀 快速开始

### 首次使用
```bash
# 1. 配置环境
./scripts/activate_env.sh

# 2. 启动服务 (IPv4模式，性能优化)
./start.sh
```

### 日常使用
```bash
# 启动服务
./start.sh

# 检查状态
./scripts/ipv6_switch.sh status

# 性能测试
./debug_and_test/scripts/performance_test.sh
```

### 环境变量
- `COMFYUI_HOST`：ComfyUI 服务主机（默认 `localhost`）
- `COMFYUI_PORT`：ComfyUI 服务端口（默认 `8188`）
- `HOST`：本服务监听地址（默认 `::`，即 IPv6 任意地址，兼容 IPv4）
- `PORT`：本服务端口（默认 `5000`）

## 🏗️ 系统架构

### 核心设计理念

本项目采用**通用化参数分类架构**，确保对现有和未来ComfyUI工作流的无缝适配：

#### 📊 参数分类体系
```python
PARAMETER_CATEGORIES = {
    'CORE_GENERATION': 核心采样参数 (steps, cfg, sampler, scheduler, denoise, seed, guidance)
    'OUTPUT_CONTROL': 输出控制参数 (width, height, batch_size, control_mode)
    'CONDITIONING': 条件控制参数 (strength, control_strength, crop)
    'MODEL_RESOURCES': 模型资源参数 (model_path, lora_name, vae_name, clip_name)
    'ADVANCED_SETTINGS': 高级设置参数 (attention, cpu_offload, data_type, device)
    'TEXT_INPUTS': 文本相关参数 (text, positive_prompt, negative_prompt)
    'SPECIALIZED': 专用处理参数 (image, mask, filename_prefix)
}
```

#### 🎛️ UI区域职责
- **🎯 基础生成参数区**：核心采样参数，所有工作流通用
- **🖼️ 输出设置区**：控制生成结果的格式和输出特性  
- **🔧 模型加载器配置区**：模型资源的加载和配置
- **⚙️ 节点参数区**：无法归类到其他区域的节点特定参数

### 🔄 通用化处理机制

#### 1. 自适应工作流检测
```python
# 自动识别工作流类型和特性
analysis = {
    'type': 'text-to-image' | 'image-to-image' | 'inpaint' | 'outpaint',
    'has_text_to_image': bool,
    'has_output_control': bool,  # 检测PrimitiveNode(width/height)
    'model_loaders': {},         # 模型加载器配置
    'output_settings': {}        # 输出控制设置
}
```

#### 2. 智能参数映射
```python
# 通用的模型加载器参数映射
LOADER_PARAM_MAPPING = {
    'StyleModelLoader': {
        'StyleModelApply': {
            'strength': ('strength', 0),
            'strength_type': ('strength_type', 1)
        }
    },
    # ... 更多映射规则
}
```

#### 3. 前端自适应渲染
- **条件显示**：根据工作流特性动态显示相关区域
- **参数过滤**：避免重复显示，确保UI简洁
- **默认值同步**：从工作流JSON提取真实默认值

## 📁 项目结构

```
comfy-web-service/
├── app.py                 # 主应用文件 - 后端逻辑核心
│   ├── analyze_workflow_structure()  # 工作流分析引擎
│   ├── apply_loader_param_mapping()  # 通用参数映射
│   ├── apply_output_settings()       # 输出设置处理
│   └── PARAMETER_CATEGORIES          # 参数分类体系
├── static/js/app.js       # 前端逻辑核心
│   ├── renderOutputSettings()        # 输出设置区域渲染
│   ├── renderGenericNodeParams()     # 通用节点参数渲染
│   ├── generateModelLoaders()        # 模型加载器生成
│   └── collectParameters()           # 参数收集与提交
├── templates/index.html   # 主界面模板
│   ├── outputSettingsSection         # 输出设置区域
│   ├── modelLoadersSection          # 模型加载器区域
│   └── nodeParametersSection        # 节点参数区域
├── workflow/             # 工作流文件目录
│   ├── nunchaku-flux.1-redux-dev.json
│   └── ... (其他工作流)
├── config.py              # 配置文件
├── requirements.txt       # Python依赖
├── start.sh              # 主启动脚本
└── docs/                 # 文档目录
```

## 🎯 核心功能特性

### 1. 🔍 智能工作流分析
- **节点类型检测**：自动识别BasicScheduler、PrimitiveNode、KSampler等
- **参数提取**：从widgets_values提取默认值
- **连接分析**：分析节点间的数据流连接
- **特性标记**：标记工作流支持的功能（文生图、图生图、ControlNet等）

### 2. 🎛️ 通用参数处理
- **分类过滤**：根据PARAMETER_CATEGORIES自动分类参数
- **重复消除**：避免在多个区域重复显示相同参数
- **映射同步**：前端参数变更自动同步到工作流节点

### 3. 🖼️ 输出设置区域（新增）
**适用场景**：检测到width/height的PrimitiveNode时自动显示

**控制选项**：
```javascript
// 与ComfyUI原生PrimitiveNode control_after_generate一致
size_control_mode: {
    'fixed': '固定',      // 每次生成相同
    'increment': '递增',   // 每次自动递增  
    'decrement': '递减',   // 每次自动递减
    'randomize': '随机'    // 每次生成不同
}
```

**参数处理**：
- 自动检测：`analysis['output_settings']['has_output_control'] = true`
- 节点同步：前端修改直接应用到PrimitiveNode的widgets_values
- 重复避免：从节点参数区完全移除width/height相关显示

### 4. 🔧 模型加载器配置
**支持的加载器类型**：
- NunchakuFluxDiTLoader：主模型加载器
- DualCLIPLoader：双CLIP编码器
- VAELoader：VAE模型加载器
- CLIPVisionLoader：视觉CLIP加载器
- StyleModelLoader：风格模型加载器
- NunchakuFluxLoraLoader：LoRA模型加载器

**参数完整性**：
- 所有参数都包含默认值标识和使用说明
- 候选值与ComfyUI原生保持一致
- 支持高级设置（attention、cpu_offload、data_type等）

## 🔄 开发指南

### 添加新工作流支持

1. **放置工作流文件**：将JSON文件放入`workflow/`目录
2. **自动适配**：系统会自动分析节点结构和参数
3. **验证显示**：检查各区域是否正确显示相关参数
4. **特殊处理**：如需特殊逻辑，在对应的处理函数中添加

### 添加新节点类型支持

1. **参数分类**：在`PARAMETER_CATEGORIES`中添加新参数
2. **映射规则**：在`LOADER_PARAM_MAPPING`中添加映射关系（如果是加载器）
3. **过滤规则**：在`excluded_node_types`中添加（如果不需要在节点参数区显示）
4. **前端适配**：在`priorityOrder`和`knownKeys`中添加对应配置

### 调试技巧

```bash
# 查看工作流分析结果
curl -sS http://127.0.0.1:5000/api/analyze-workflow/your-workflow.json | jq '.'

# 检查特定区域数据
curl -sS http://127.0.0.1:5000/api/analyze-workflow/your-workflow.json | jq '.analysis.output_settings'
curl -sS http://127.0.0.1:5000/api/analyze-workflow/your-workflow.json | jq '.analysis.model_loaders'
curl -sS http://127.0.0.1:5000/api/analyze-workflow/your-workflow.json | jq '.analysis.node_groups'
```

## 🌐 访问地址

- 本机默认：`http://127.0.0.1:5000`
- 局域网：`http://<你的主机IP>:5000`
- 可通过 `HOST` / `PORT` 环境变量调整监听地址与端口

## 📚 文档

- [IPv6优化指南](docs/guides/IPV6_OPTIMIZATION_GUIDE.md)
- [脚本使用说明](docs/guides/SCRIPTS_README.md)
- [性能优化文档](docs/performance/)

## 🛠️ 脚本工具

- `start.sh` - 主启动脚本
- `scripts/ipv6_switch.sh` - IPv6模式切换
- `scripts/quick_switch.sh` - 快速切换
- `debug_and_test/scripts/performance_test.sh` - 性能测试（已迁移至调试与测试目录）

### 🧪 调试与测试目录

所有测试相关脚本与页面已统一归档至 `debug_and_test/`：

- `debug_and_test/scripts/`：Shell 测试脚本（如 `performance_test.sh`）
- `debug_and_test/python_tests/`：Python 测试脚本（如 `test_ipv6.py`）
- `debug_and_test/html_tests/`：前端调试/测试页面（如 `test_prompt_manager_simple.html`、`debug_prompt_manager.html`）

注意：若文档或历史命令中仍出现 `scripts/performance_test.sh` 或根目录 `performance_test.sh`，请改用：

```bash
./debug_and_test/scripts/performance_test.sh
```

## 📡 API 路由简表（核心）

- `GET /api/workflows`：获取可用工作流列表
- `GET /api/workflow/<filename>`：获取指定工作流 JSON 详情
- `POST /api/run`：运行工作流（支持参数与图像输入）
- `GET /api/status/<task_id>`：查询任务状态
- `GET /api/tasks`：获取任务列表
- `GET /api/comfyui/status`：ComfyUI 健康检查
- `GET /api/system-resources`：系统资源信息
- `POST /api/clean-vram`：释放显存
- `POST /api/upload`：上传图片/遮罩（保存至 `outputs/uploaded` 或 `outputs/masks`）
- `GET /api/images`：列出可用图片（uploaded/generated 两类，供图片选择弹窗使用）
- `POST /api/delete-image`：删除单张图片（用于选择器/画廊）
- `POST /api/delete-images`：批量删除图片（用于选择器/画廊）
- `GET /api/generated-images`：列出生成的图片
- `GET /api/image-metadata/<filename>`：获取图片关联元数据
- `GET /api/workflow-stats`：获取工作流使用统计（最近使用/最热）
- `GET /api/analyze-workflow/<filename>`：分析工作流结构特性
- `GET /outputs/<path>`：静态访问生成产物

调试/演示页面：`/`、`/gallery`、`/prompt-manager`、`/debug` 等

图片选择弹窗与画廊说明：
- 选择器依赖：`GET /api/images` 拉取数据、`POST /api/upload` 上传、`GET /outputs/<path>` 读取缩略、以及删除接口。
- 画廊/元数据依赖：`GET /api/generated-images`、`GET /api/image-metadata/<filename>`。

## 📂 输出目录

- 统一使用 `outputs/` 存放运行产物（图片、元数据、上传内容、遮罩等）
- 运行统计 `workflow_stats.json` 也位于 `outputs/`（兼容迁移旧路径 `output/` 与项目根目录）

## ⚡ 性能特性

- ✅ IPv4专用模式 (0.0007秒响应时间)
- ✅ 自动虚拟环境管理
- ✅ 智能网络模式切换
- ✅ 完整的性能监控工具
- ✅ 通用化工作流适配引擎
- ✅ 智能参数分类和去重
- ✅ 实时工作流分析和UI适配

## 🚨 重要注意事项

### 代码修改自动重载
- app.py支持自动重载，修改后无需手动重启
- 前端文件修改后需要强制刷新（Ctrl+F5）或等待缓存失效

### 参数映射逻辑
- 新增参数应优先考虑归类到现有分类体系
- 避免硬编码特定节点处理，优先使用通用映射规则
- 保持向前兼容，新功能不应影响现有工作流

### UI设计原则
- 条件显示：只在需要时显示相关区域
- 避免重复：确保同一参数不在多个区域重复出现
- 用户友好：提供默认值标识和参数说明

## 📝 许可证

本项目基于MIT许可证开源。

## 🧾 版本更新

### v0.9.0-cleanup（当前稳定点）

- 清理：移除历史备份脚本，避免搜索/编辑干扰；统一以 `outputs/` 为产物目录。
- Prompt系统：`PromptTemplates` 改为可选依赖，缺失时不阻塞初始化。
- 图片选择：恢复并完善选择器全流程（`loadImages`/`renderImageTabs`/上传/删除/预览）。
- 导航与注入：提示词管理器“应用到主界面”带上 `workflow`、`positive`、`negative` 参数；配置页出现回填横幅与撤销。
- 快捷提示词：新增“最近使用/最常用”分组；收藏/自定义变更实时反映。
- 分类/徽章管理：新增隐藏与别名配置，并在管理器与配置页间联动。

如需查看历史版本变更，请参考 `docs/` 目录下的各项说明与记录。