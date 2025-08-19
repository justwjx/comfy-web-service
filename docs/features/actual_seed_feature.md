# 实际种子值记录功能

## 问题背景

用户反馈了一个重要问题：当用户设置seed为-1时，ComfyUI会自动生成一个随机种子，但我们的元数据只记录了用户输入的-1，而没有记录实际使用的具体种子值。这导致用户无法准确重现生成结果。

## 问题分析

### 原始问题
- 用户设置seed为-1（随机种子）
- ComfyUI自动生成具体种子值（如：794018202952262）
- 元数据只记录用户输入的-1
- 用户无法知道实际使用的种子值

### 技术原因
1. **工作流结构**：nunchaku-flux.1-dev.json使用RandomNoise节点生成噪声
2. **种子传递**：用户设置的seed通过RandomNoise节点的widgets_values传递
3. **历史记录**：ComfyUI历史记录中保存了实际执行的节点参数

## 解决方案

### 1. 提取实际种子值

添加了`_extract_actual_seed`方法，从ComfyUI历史记录中提取实际使用的种子值：

```python
def _extract_actual_seed(self, task_info, parameters):
    """从ComfyUI历史记录中提取实际使用的种子值"""
    try:
        # 获取prompt数据，包含实际执行的节点信息
        prompt_data = task_info.get('prompt', [])
        if not prompt_data or len(prompt_data) < 3:
            return None
        
        # prompt_data[2]包含节点配置
        nodes_config = prompt_data[2]
        
        # 查找RandomNoise节点
        for node_id, node_data in nodes_config.items():
            if node_data.get('class_type') == 'RandomNoise':
                # 检查inputs中的noise_seed
                inputs = node_data.get('inputs', {})
                if 'noise_seed' in inputs:
                    actual_seed = inputs['noise_seed']
                    logger.info(f"找到RandomNoise节点 {node_id} 的实际种子值: {actual_seed}")
                    return actual_seed
        
        # 如果没有找到RandomNoise节点，尝试查找其他可能的种子节点
        # 比如KSampler节点
        for node_id, node_data in nodes_config.items():
            if node_data.get('class_type') == 'KSampler':
                inputs = node_data.get('inputs', {})
                if 'seed' in inputs:
                    actual_seed = inputs['seed']
                    logger.info(f"找到KSampler节点 {node_id} 的实际种子值: {actual_seed}")
                    return actual_seed
        
        logger.warning("未找到包含种子值的节点")
        return None
        
    except Exception as e:
        logger.error(f"提取实际种子值时发生错误: {e}")
        return None
```

### 2. 更新元数据存储

在`_process_task_outputs`方法中，添加实际种子值的提取和存储：

```python
# 从ComfyUI历史记录中提取实际种子值
actual_seed = self._extract_actual_seed(task_info, parameters)

# 更新参数中的种子值
if actual_seed is not None:
    parameters['actual_seed'] = actual_seed
    # 如果用户设置的是-1，也记录用户输入
    if parameters.get('seed') == -1:
        parameters['user_seed'] = -1
```

### 3. 前端显示优化

#### 画廊预览
在画廊中，当用户设置seed为-1时，显示格式为：`-1 → 794018202952262`

#### 详细元数据
在元数据模态框中，分别显示：
- **用户设置种子**：-1
- **实际使用种子**：794018202952262

## 元数据格式

### 修复前
```json
{
  "parameters": {
    "seed": -1
  }
}
```

### 修复后
```json
{
  "parameters": {
    "seed": -1,
    "user_seed": -1,
    "actual_seed": 794018202952262
  }
}
```

## 功能特性

### 1. 智能种子识别
- 自动识别RandomNoise和KSampler节点
- 提取实际使用的种子值
- 兼容不同的工作流结构

### 2. 用户友好显示
- 画廊中直观显示种子变化：`-1 → 794018202952262`
- 详细元数据中分别显示用户设置和实际使用值
- 保持向后兼容性

### 3. 错误处理
- 找不到种子节点时记录警告日志
- 提取失败时不影响基本功能
- 优雅降级处理

## 测试验证

### 测试结果
```
种子信息:
  用户设置种子: -1
  实际使用种子: 794018202952262
  原始种子字段: -1
✅ 成功提取到实际种子值！
```

### API验证
```bash
curl -s "http://localhost:5000/api/generated-images" | jq '.images[0] | {seed, actual_seed: .metadata.parameters.actual_seed, user_seed: .metadata.parameters.user_seed}'
```

返回结果：
```json
{
  "seed": -1,
  "actual_seed": 794018202952262,
  "user_seed": -1
}
```

## 影响范围

### 新生成的图片
- 自动记录实际种子值
- 在画廊中正确显示
- 支持详细查看

### 现有图片
- 需要手动更新元数据或重新生成
- 不影响基本功能使用

## 使用场景

### 1. 随机种子重现
用户设置seed为-1后，可以：
- 查看实际使用的种子值
- 使用该种子值重现相同结果
- 记录完整的生成参数

### 2. 参数分析
- 分析种子值对生成结果的影响
- 比较不同种子值的生成效果
- 建立参数数据库

### 3. 工作流优化
- 记录最佳种子值
- 优化参数组合
- 提高生成效率

## 技术细节

### ComfyUI历史记录结构
```json
{
  "prompt": [
    24,
    "prompt_id",
    {
      "25": {
        "class_type": "RandomNoise",
        "inputs": {
          "noise_seed": 794018202952262
        }
      }
    }
  ]
}
```

### 种子值来源
1. **用户输入**：通过UI设置的seed值
2. **ComfyUI生成**：当seed为-1时自动生成
3. **历史记录**：从执行历史中提取实际值

## 总结

通过实现实际种子值记录功能，我们解决了以下问题：

1. **准确性**：记录实际使用的种子值，而不是用户输入
2. **可重现性**：用户可以准确重现生成结果
3. **完整性**：提供完整的参数信息
4. **用户体验**：直观显示种子值变化

这个功能确保了元数据的准确性和完整性，为用户提供了更好的生成体验。 