#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import os

def debug_node13():
    """检查节点13的详细信息"""
    workflow_file = "workflow/nunchaku-flux.1-dev.json"
    with open(workflow_file, 'r', encoding='utf-8') as f:
        workflow_data = json.load(f)
    
    print("=== 检查节点13 ===")
    
    # 找到节点13
    nodes = workflow_data.get('nodes', [])
    node13 = None
    for node in nodes:
        if node.get('id') == 13:
            node13 = node
            break
    
    if not node13:
        print("节点13不存在")
        return
    
    print(f"节点13类型: {node13.get('type')}")
    print(f"节点13输入: {node13.get('inputs')}")
    print(f"节点13输出: {node13.get('outputs')}")
    print(f"节点13widgets_values: {node13.get('widgets_values')}")
    
    # 检查节点13的输入连接
    links = workflow_data.get('links', [])
    link_mapping = {}
    for link in links:
        if len(link) >= 4:
            link_id = link[0]
            from_node_id = link[1]
            from_output_index = link[2]
            link_mapping[link_id] = (from_node_id, from_output_index)
    
    print(f"链接映射: {link_mapping}")
    
    # 检查节点13的输入
    ui_inputs = node13.get('inputs', [])
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
        'class_type': 'SamplerCustomAdvanced',
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

if __name__ == "__main__":
    debug_node13() 