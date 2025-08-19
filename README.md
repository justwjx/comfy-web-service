# ComfyUI Web Service

一个移动端友好的ComfyUI工作流Web服务，支持IPv4/IPv6网络优化和通用化工作流适配。

## 🚀 快速开始

### 首次使用
```bash
# 1. 配置环境
./docs/scripts/activate_env.sh

# 2. 启动服务 (IPv4模式，性能优化)
./start.sh
```

### 日常使用
```bash
# 启动服务
./start.sh

# 检查状态
./docs/scripts/ipv6_switch.sh status

# 性能测试
./docs/scripts/performance_test.sh
```

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

- IPv4: `http://172.16.10.224:5000`
- IPv4: `http://172.16.10.225:5000`

## 📚 文档

- [IPv6优化指南](docs/guides/IPV6_OPTIMIZATION_GUIDE.md)
- [脚本使用说明](docs/guides/SCRIPTS_README.md)
- [性能优化文档](docs/performance/)

## 🛠️ 脚本工具

- `start.sh` - 主启动脚本
- `docs/scripts/ipv6_switch.sh` - IPv6模式切换
- `docs/scripts/quick_switch.sh` - 快速切换
- `docs/scripts/performance_test.sh` - 性能测试

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

### v0.2.x（当前）

- 归档：将项目根目录下的测试文件归档至 `archive/tests_root/`，保持根目录整洁。
- 忽略规则：
  - 新增 `.dockerignore`，避免归档与输出目录进入容器构建上下文。
  - 更新 `.gitignore`/`.dockerignore`：统一以 `outputs/` 为主目录，兼容旧 `output/`。
- 前端：持续优化 `static/js/app.js` 的自适应渲染与参数分类逻辑，输出设置区更稳健。
- 文档与结构：新增/完善 `docs/PROJECT_STRUCTURE*.md` 等结构化文档，补充特性、优化与指南分类目录。
- 脚本：整合启动与网络切换脚本（`start.sh`、`scripts/ipv6_switch.sh`、`scripts/quick_switch.sh` 等），提升日常运维效率。
- 工作流：补充示例工作流（如 `workflow/nunchaku-flux.1-outpaint.json`）。

如需查看历史版本变更，请参考 `docs/` 目录下的各项说明与记录。