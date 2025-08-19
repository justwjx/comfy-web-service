# ComfyUI Web服务连接检查和进度监控改进

## 问题描述

用户反馈在ComfyUI后端未启动或未连接成功时，发起任务时没有任何提示，只会看到进度条卡在0%。另外，进度条没有实时反馈后端的实际进度。

## 解决方案

### 1. 连接状态检查

#### 前端改进 (`static/js/app.js`)
- 在 `startGeneration()` 方法中添加了ComfyUI连接状态检查
- 在发起任务前先调用 `/api/comfyui/status` 检查后端连接
- 如果连接失败，显示详细的错误信息和解决建议

```javascript
// 先检查ComfyUI连接状态
try {
    const statusResponse = await fetch('/api/comfyui/status');
    const statusData = await statusResponse.json();
    
    if (!statusData.success || !statusData.connected) {
        const errorMsg = statusData.error || 'ComfyUI后端未连接';
        alert(`无法连接到ComfyUI后端：${errorMsg}\n\n请确保：\n1. ComfyUI服务已启动\n2. 服务地址配置正确\n3. 网络连接正常`);
        return;
    }
} catch (error) {
    console.error('检查ComfyUI状态失败:', error);
    alert('无法检查ComfyUI连接状态，请确保后端服务正常运行');
    return;
}
```

#### 后端改进 (`app.py`)
- 在 `run_workflow()` 函数中添加了连接状态检查
- 如果ComfyUI未连接，立即返回503错误状态
- 改进了任务状态初始化，提供更详细的状态信息

```python
# 先检查ComfyUI连接状态
if not runner.check_comfyui_status():
    return jsonify({
        'success': False, 
        'error': 'ComfyUI服务未运行或无法连接，请确保ComfyUI后端已启动'
    }), 503
```

### 2. 实时进度监控

#### 后端进度监控改进 (`app.py`)
- 修改了 `_monitor_workflow_progress()` 方法，提供更详细的进度信息
- 增加了 `_get_detailed_progress()` 方法获取实际执行进度
- 增加了 `_get_queue_position()` 方法获取排队位置
- 提高了监控频率（从2秒改为1秒）
- 添加了详细的状态消息

```python
def _get_detailed_progress(self, prompt_id, client_id):
    """获取详细的执行进度"""
    try:
        # 尝试获取执行状态
        execution_response = requests.get(f"{COMFYUI_API_URL}/executing", timeout=5)
        if execution_response.status_code == 200:
            execution_data = execution_response.json()
            
            # 检查是否有正在执行的节点
            if execution_data.get('node') and execution_data.get('prompt_id') == prompt_id:
                return 50  # 基础进度
            
            # 检查历史记录中的进度
            history_response = requests.get(f"{COMFYUI_API_URL}/history/{prompt_id}", timeout=5)
            if history_response.status_code == 200:
                history_data = history_response.json()
                if prompt_id in history_data:
                    task_info = history_data[prompt_id]
                    outputs = task_info.get('outputs', {})
                    
                    # 根据输出节点数量估算进度
                    if outputs:
                        return 90  # 有输出表示任务接近完成
                    else:
                        return 60  # 没有输出但任务在运行中
        
        return 50  # 默认进度
        
    except Exception as e:
        logger.error(f"获取详细进度失败: {e}")
        return 50
```

#### 前端进度显示改进 (`static/js/app.js`)
- 修改了 `monitorTask()` 方法，支持显示详细状态消息
- 增加了预计剩余时间显示
- 优化了错误处理和超时处理

```javascript
// 更新状态信息，包含详细消息
if (taskStatus) {
    let statusText = status;
    if (message) {
        statusText += ` - ${message}`;
    }
    taskStatus.textContent = statusText;
}

// 更新预计剩余时间
if (taskRemaining) {
    if (status === 'pending') {
        taskRemaining.textContent = '等待中...';
    } else if (status === 'running') {
        if (progress < 30) {
            taskRemaining.textContent = '预计 2-3 分钟';
        } else if (progress < 70) {
            taskRemaining.textContent = '预计 1-2 分钟';
        } else {
            taskRemaining.textContent = '即将完成';
        }
    } else {
        taskRemaining.textContent = '-';
    }
}
```

### 3. 错误处理改进

#### 错误显示改进
- 改进了 `showTaskError()` 方法，提供更详细的错误信息
- 根据错误类型提供相应的解决建议
- 优化了错误信息的格式显示

#### CSS样式改进 (`static/css/style.css`)
- 改进了 `.error-content` 样式，支持多行文本显示
- 添加了左边框和更好的视觉提示

```css
.error-content {
  background: rgba(239, 68, 68, 0.1);
  padding: 16px;
  border-radius: var(--border-radius);
  color: var(--error-color);
  font-family: monospace;
  font-size: 14px;
  line-height: 1.6;
  white-space: pre-line;
  border-left: 4px solid #ef4444;
}
```

### 4. 测试工具

创建了 `test_connection.py` 测试脚本，用于验证：
- ComfyUI服务连接状态
- Web服务连接状态
- 队列状态
- 提供详细的诊断信息

## 使用说明

### 启动服务
1. 确保ComfyUI后端服务已启动
2. 启动Web服务：`python3 app.py`
3. 访问 http://localhost:5000

### 测试连接
运行测试脚本检查连接状态：
```bash
python3 test_connection.py
```

### 错误处理
当遇到连接问题时，系统会显示：
1. 明确的错误信息
2. 具体的解决建议
3. 详细的诊断信息

## 改进效果

1. **连接检查**：在发起任务前自动检查ComfyUI连接状态
2. **实时反馈**：进度条现在反映实际的执行进度
3. **详细状态**：显示任务状态、排队位置、预计时间等
4. **错误提示**：提供明确的错误信息和解决建议
5. **用户体验**：减少了用户困惑，提高了操作效率

## 技术细节

- 使用ComfyUI的 `/system_stats`、`/queue`、`/executing`、`/history` API
- 实现了更精确的进度估算算法
- 改进了错误处理和日志记录
- 优化了前端状态更新频率 