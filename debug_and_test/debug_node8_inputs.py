#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import os

def debug_node8_inputs():
    """检查节点8的输入是否正确"""
    workflow_file = "workflow/nunchaku-flux.1-dev.json"
    with open(workflow_file, 'r', encoding='utf-8') as f:
        workflow_data = json.load(f)
    
    print("=== 检查节点8的输入 ===")
    
    # 找到节点8
    nodes = workflow_data.get('nodes', [])
    node8 = None
    for node in nodes:
        if node.get('id') == 8:
            node8 = node
            break
    
    if not node8:
        print("节点8不存在")
        return
    
    print(f"节点8类型: {node8.get('type')}")
    print(f"节点8输入: {node8.get('inputs')}")
    
    # 检查节点8的输入连接
    links = workflow_data.get('links', [])
    link_mapping = {}
    for link in links:
        if len(link) >= 4:
            link_id = link[0]
            from_node_id = link[1]
            from_output_index = link[2]
            link_mapping[link_id] = (from_node_id, from_output_index)
    
    print(f"链接映射: {link_mapping}")
    
    # 检查节点8的输入
    ui_inputs = node8.get('inputs', [])
    if isinstance(ui_inputs, list):
        for input_item in ui_inputs:
            if isinstance(input_item, dict):
                input_name = input_item.get('name', '')
                if 'link' in input_item:
                    link_id = input_item['link']
                    print(f"输入 {input_name} 连接到 link_id: {link_id}")
                    if link_id in link_mapping:
                        from_node_id, from_output_index = link_mapping[link_id]
                        print(f"  源节点: {from_node_id}, 输出索引: {from_output_index}")
                        
                        # 检查源节点是否存在
                        source_node = None
                        for node in nodes:
                            if node.get('id') == from_node_id:
                                source_node = node
                                break
                        
                        if source_node:
                            print(f"  源节点类型: {source_node.get('type')}")
                        else:
                            print(f"  警告: 源节点 {from_node_id} 不存在!")
                    else:
                        print(f"  警告: link_id {link_id} 不在链接映射中")
    
    # 模拟API格式转换
    print("\n=== 模拟API格式转换 ===")
    api_node = {
        'class_type': 'VAEDecode',
        'inputs': {}
    }
    
    if isinstance(ui_inputs, list):
        for input_item in ui_inputs:
            if isinstance(input_item, dict):
                input_name = input_item.get('name', '')
                if 'link' in input_item:
                    link_id = input_item['link']
                    if link_id in link_mapping:
                        from_node_id, from_output_index = link_mapping[link_id]
                        api_node['inputs'][input_name] = from_node_id
                        print(f"API输入 {input_name}: {from_node_id}")
                    else:
                        api_node['inputs'][input_name] = link_id
                        print(f"API输入 {input_name}: {link_id} (使用link_id)")
    
    print(f"转换后的API节点: {api_node}")
    
    # 检查节点13和节点10是否存在
    print("\n=== 检查依赖节点 ===")
    node13 = None
    node10 = None
    for node in nodes:
        if node.get('id') == 13:
            node13 = node
        elif node.get('id') == 10:
            node10 = node
    
    if node13:
        print(f"节点13存在: {node13.get('type')}")
    else:
        print("节点13不存在!")
    
    if node10:
        print(f"节点10存在: {node10.get('type')}")
    else:
        print("节点10不存在!")
    
    # 检查这些节点是否有widgets_values
    if node13:
        print(f"节点13的widgets_values: {node13.get('widgets_values')}")
    if node10:
        print(f"节点10的widgets_values: {node10.get('widgets_values')}")

if __name__ == "__main__":
    debug_node8_inputs() 