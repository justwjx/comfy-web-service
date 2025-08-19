#!/usr/bin/env python3
import json

# 读取工作流文件
with open('workflow/nunchaku-flux.1-kontext-dev.json', 'r', encoding='utf-8') as f:
    workflow_data = json.load(f)

# 查找LoadImageOutput节点
for node in workflow_data.get('nodes', []):
    if node.get('type') == 'LoadImageOutput':
        node_id = node.get('id')
        widgets_values = node.get('widgets_values', [])
        print(f"LoadImageOutput 节点 {node_id}:")
        print(f"  widgets_values: {widgets_values}")
        if widgets_values and len(widgets_values) > 0:
            default_image = widgets_values[0]
            print(f"  默认图像: '{default_image}'")
            print(f"  类型: {type(default_image)}")
            print(f"  长度: {len(default_image) if isinstance(default_image, str) else 'N/A'}")
            print(f"  包含方括号: {'[' in default_image if isinstance(default_image, str) else False}")
        print() 