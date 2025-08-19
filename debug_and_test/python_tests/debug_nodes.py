#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json

# 读取workflow文件
workflow_file = "workflow/nunchaku-flux.1-schnell.json"
with open(workflow_file, 'r', encoding='utf-8') as f:
    workflow_data = json.load(f)

nodes = workflow_data.get('nodes', [])
print(f"总共有 {len(nodes)} 个节点")

for i, node in enumerate(nodes):
    node_id = node.get('id', '')
    node_type = node.get('type', '')
    print(f"节点 {i}: ID={node_id}, 类型={node_type}")
    
    if not node_id:
        print(f"  警告: 节点 {i} 没有ID!")
    elif str(node_id) == '':
        print(f"  警告: 节点 {i} ID为空字符串!") 