#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import os

def convert_ui_to_api_format(ui_workflow):
    """将UI格式的workflow转换为API格式"""
    try:
        api_workflow = {
            'prompt': {},
            'extra_data': {
                'extra_pnginfo': {
                    'workflow': ui_workflow
                }
            }
        }
        
        # 将UI格式的nodes转换为API格式
        nodes = ui_workflow.get('nodes', [])
        print(f"总共有 {len(nodes)} 个节点")
        
        for node in nodes:
            node_id = str(node.get('id', ''))
            node_type = node.get('type', '')
            print(f"处理节点 {node_id}: {node_type}")
            
            if node_id:
                # 创建API格式的节点
                api_node = {
                    'class_type': node_type,  # UI的type转换为API的class_type
                    'inputs': {}
                }
                
                # 处理inputs - UI格式中inputs是数组
                ui_inputs = node.get('inputs', [])
                if isinstance(ui_inputs, list):
                    for input_item in ui_inputs:
                        if isinstance(input_item, dict):
                            input_name = input_item.get('name', '')
                            if 'link' in input_item:
                                # 这是连接，保持link ID
                                api_node['inputs'][input_name] = input_item['link']
                            elif 'value' in input_item:
                                # 这是值
                                api_node['inputs'][input_name] = input_item['value']
                            else:
                                # 直接值
                                api_node['inputs'][input_name] = input_item
                elif isinstance(ui_inputs, dict):
                    # 兼容旧格式
                    for input_name, input_data in ui_inputs.items():
                        if isinstance(input_data, dict) and 'link' in input_data:
                            # 这是连接，保持link ID
                            api_node['inputs'][input_name] = input_data['link']
                        elif isinstance(input_data, dict) and 'value' in input_data:
                            # 这是值
                            api_node['inputs'][input_name] = input_data['value']
                        else:
                            # 直接值
                            api_node['inputs'][input_name] = input_data
                
                # 处理PrimitiveNode等特殊节点，它们可能有widgets_values但没有inputs
                widgets_values = node.get('widgets_values', [])
                if widgets_values and not api_node['inputs']:
                    # 对于PrimitiveNode，将widgets_values作为inputs
                    if node_type == 'PrimitiveNode':
                        # PrimitiveNode通常只有一个值
                        if len(widgets_values) > 0:
                            api_node['inputs']['value'] = widgets_values[0]
                            print(f"  PrimitiveNode {node_id} 设置 value: {widgets_values[0]}")
                    else:
                        # 其他节点可能有多个widgets_values
                        for i, value in enumerate(widgets_values):
                            api_node['inputs'][f'value_{i}'] = value
                
                api_workflow['prompt'][node_id] = api_node
                print(f"  节点 {node_id} 转换完成，inputs: {list(api_node['inputs'].keys())}")
        
        print(f"转换完成，API workflow包含 {len(api_workflow.get('prompt', {}))} 个节点")
        return api_workflow
        
    except Exception as e:
        print(f"转换UI格式到API格式失败: {e}")
        return None

# 测试转换
if __name__ == "__main__":
    # 读取workflow文件
    workflow_file = "workflow/nunchaku-flux.1-dev.json"
    with open(workflow_file, 'r', encoding='utf-8') as f:
        workflow_data = json.load(f)
    
    print("开始转换workflow...")
    api_workflow = convert_ui_to_api_format(workflow_data)
    
    if api_workflow:
        print("\n转换成功！")
        print(f"API workflow包含的节点:")
        for node_id, node_data in api_workflow.get('prompt', {}).items():
            print(f"  {node_id}: {node_data.get('class_type', 'unknown')}")
        
        # 检查是否包含PrimitiveNode
        primitive_nodes = [node_id for node_id, node_data in api_workflow.get('prompt', {}).items() 
                          if node_data.get('class_type') == 'PrimitiveNode']
        print(f"\nPrimitiveNode节点: {primitive_nodes}")
    else:
        print("转换失败！") 