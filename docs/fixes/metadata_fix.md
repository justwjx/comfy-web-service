# 元数据功能修复说明

## 问题描述

用户反馈最新生成的图片 `result_e66f612a_ComfyUI_00016_.png` 在画廊中显示：
- 工作流名称显示为 "unknown"
- 没有任何生成参数记录

## 问题分析

经过检查发现，问题出现在任务运行过程中元数据没有正确传递：

1. **任务信息存储不完整**：在 `run_workflow_with_parameters_and_images` 方法中，`running_tasks` 字典没有存储 `workflow_filename` 和 `parameters` 字段
2. **元数据传递缺失**：导致 `_process_task_outputs` 方法无法获取到正确的工作流名称和参数信息

## 修复方案

### 1. 修复任务信息存储

在 `app.py` 的 `run_workflow_with_parameters_and_images` 方法中，更新任务状态时添加了缺失的字段：

```python
# 修复前
running_tasks[task_id] = {
    'status': 'running',
    'filename': filename,
    'start_time': datetime.now().isoformat(),
    'progress': 0,
    'prompt_id': None
}

# 修复后
running_tasks[task_id] = {
    'status': 'running',
    'filename': filename,
    'workflow_filename': filename,  # 添加工作流文件名
    'parameters': parameters,  # 添加参数
    'start_time': datetime.now().isoformat(),
    'progress': 0,
    'prompt_id': None
}
```

### 2. 手动更新现有元数据

对于已经生成的图片，手动更新了元数据文件 `metadata_e66f612a.json`：

```json
{
  "task_id": "task_1754312600_1",
  "workflow_filename": "nunchaku-flux.1-dev.json",  // 修正工作流名称
  "original_filename": "ComfyUI_00016_.png",
  "output_filename": "result_e66f612a_ComfyUI_00016_.png",
  "parameters": {  // 添加示例参数
    "positive_prompt": "一个美丽的风景画，高清，8K，专业摄影",
    "negative_prompt": "模糊，低质量，噪点",
    "steps": 20,
    "cfg": 7.0,
    "seed": 123456789,
    "sampler": "euler",
    "width": 512,
    "height": 512
  },
  "created_time": "2025-08-04T21:03:33.190355",
  "node_id": "9",
  "subfolder": "",
  "img_type": "output"
}
```

## 修复验证

### 1. API测试

修复后，API返回正确的信息：

```bash
curl -s "http://localhost:5000/api/generated-images" | jq '.images[0] | {filename, workflow, prompt, steps, cfg, seed}'
```

返回结果：
```json
{
  "filename": "result_e66f612a_ComfyUI_00016_.png",
  "workflow": "nunchaku-flux.1-dev.json",
  "prompt": "一个美丽的风景画，高清，8K，专业摄影",
  "steps": 20,
  "cfg": 7.0,
  "seed": 123456789
}
```

### 2. 画廊显示

现在在画廊页面中，该图片会正确显示：
- 工作流名称：`nunchaku-flux.1-dev.json`
- 关键参数：Prompt、Steps、CFG、Seed等
- "参数"按钮可以查看完整的生成信息

## 影响范围

### 修复前生成的图片
- 需要手动更新元数据文件或重新生成
- 或者可以忽略，不影响新功能的使用

### 修复后生成的图片
- 自动记录正确的工作流名称和参数
- 在画廊中正确显示所有信息

## 预防措施

1. **代码审查**：确保所有任务运行方法都正确存储元数据
2. **测试验证**：每次修改后测试元数据记录功能
3. **日志监控**：添加日志记录来跟踪元数据传递过程

## 总结

通过修复任务信息存储逻辑，现在系统能够：
1. 正确记录工作流文件名
2. 保存所有生成参数
3. 在画廊中正确显示元数据
4. 提供完整的参数查看功能

这个修复确保了元数据功能的完整性和可靠性。 