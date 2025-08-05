# 图片元数据功能说明

## 功能概述

本功能为ComfyUI Web服务添加了完整的图片元数据记录和查看功能，让用户可以：

1. **自动记录生成参数**：每次生成图片时自动保存prompt、cfg、steps等参数
2. **画廊中预览参数**：在图片画廊中直接查看关键生成参数
3. **详细元数据查看**：点击"参数"按钮查看完整的生成信息

## 功能特性

### 1. 自动元数据记录

- **记录内容**：
  - 任务ID和工作流文件名
  - 所有生成参数（prompt、cfg、steps、seed等）
  - 生成时间和技术信息
  - 原始文件名和输出文件名

- **存储方式**：
  - 图片文件：`result_{unique_id}_{original_name}.png`
  - 元数据文件：`metadata_{unique_id}.json`
  - 两者通过相同的unique_id关联

### 2. 画廊参数预览

在图片画廊中，每张图片会显示：
- 基本信息：生成时间、文件大小、工作流名称
- 关键参数：Prompt（前50字符）、Steps、CFG、Seed、Sampler
- 操作按钮：查看、参数、下载

### 3. 详细元数据查看

点击"参数"按钮可以查看：
- **基本信息**：文件名、工作流、任务ID、创建时间
- **生成参数**：所有用户设置的参数
- **技术信息**：节点ID、子文件夹、图片类型等

## API接口

### 1. 获取图片列表（包含元数据）

```
GET /api/generated-images
```

返回格式：
```json
{
  "success": true,
  "images": [
    {
      "filename": "result_8eb53127_ComfyUI_00013_.png",
      "url": "/outputs/result_8eb53127_ComfyUI_00013_.png",
      "has_metadata": true,
      "workflow": "test-workflow.json",
      "prompt": "一个美丽的风景画，高清，8K",
      "steps": 20,
      "cfg": 7.0,
      "seed": 123456789,
      "sampler": "euler",
      "metadata": { /* 完整元数据 */ }
    }
  ],
  "total": 23
}
```

### 2. 获取单个图片详细元数据

```
GET /api/image-metadata/{filename}
```

返回格式：
```json
{
  "success": true,
  "metadata": {
    "task_id": "test_task_8eb53127",
    "workflow_filename": "test-workflow.json",
    "parameters": {
      "positive_prompt": "一个美丽的风景画，高清，8K",
      "negative_prompt": "模糊，低质量",
      "steps": 20,
      "cfg": 7.0,
      "seed": 123456789,
      "sampler": "euler",
      "width": 512,
      "height": 512
    },
    "created_time": "2025-08-04T20:59:44.711535",
    "node_id": "test_node_1"
  }
}
```

## 元数据文件格式

每个元数据文件（`metadata_{unique_id}.json`）包含：

```json
{
  "task_id": "任务唯一标识",
  "workflow_filename": "工作流文件名",
  "original_filename": "原始文件名",
  "output_filename": "输出文件名",
  "parameters": {
    "positive_prompt": "正面提示词",
    "negative_prompt": "负面提示词",
    "steps": "步数",
    "cfg": "CFG值",
    "seed": "随机种子",
    "sampler": "采样器",
    "width": "宽度",
    "height": "高度"
  },
  "created_time": "创建时间",
  "node_id": "输出节点ID",
  "subfolder": "子文件夹",
  "img_type": "图片类型"
}
```

## 使用方法

### 1. 生成图片

正常使用工作流生成图片，系统会自动记录元数据。

### 2. 查看画廊

访问 `/gallery` 页面：
- 查看所有生成的图片
- 预览关键生成参数
- 点击"参数"按钮查看详细信息

### 3. 程序化访问

使用API接口获取元数据：
```python
import requests

# 获取图片列表
response = requests.get('http://localhost:5000/api/generated-images')
images = response.json()['images']

# 获取详细元数据
for image in images:
    if image['has_metadata']:
        metadata_response = requests.get(f"http://localhost:5000/api/image-metadata/{image['filename']}")
        metadata = metadata_response.json()['metadata']
        print(f"图片: {image['filename']}")
        print(f"Prompt: {metadata['parameters']['positive_prompt']}")
        print(f"Steps: {metadata['parameters']['steps']}")
```

## 兼容性

- **向后兼容**：现有的没有元数据的图片仍然可以正常显示
- **渐进增强**：有元数据的图片会显示额外信息
- **错误处理**：元数据文件损坏或缺失不会影响基本功能

## 技术实现

### 后端实现

1. **修改 `_process_task_outputs` 方法**：
   - 在保存图片时同时保存元数据
   - 生成唯一的ID关联图片和元数据

2. **新增API端点**：
   - `/api/generated-images`：返回图片列表和元数据
   - `/api/image-metadata/{filename}`：返回详细元数据

3. **元数据存储**：
   - JSON格式存储，便于读取和修改
   - 与图片文件同目录，便于管理

### 前端实现

1. **画廊页面增强**：
   - 显示关键参数预览
   - 添加"参数"按钮
   - 实现模态框显示详细元数据

2. **样式优化**：
   - 参数显示区域样式
   - 模态框样式
   - 响应式设计

## 未来扩展

1. **参数复制功能**：一键复制参数到新的生成任务
2. **参数搜索**：按参数值搜索图片
3. **参数统计**：分析参数使用情况
4. **批量操作**：批量查看或导出元数据
5. **参数模板**：保存常用的参数组合 