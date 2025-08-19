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
                
                # 处理widgets_values - 这些是节点的参数值
                widgets_values = node.get('widgets_values', [])
                if widgets_values:
                    # 根据节点类型处理widgets_values
                    if node_type == 'PrimitiveNode':
                        # PrimitiveNode通常只有一个值
                        if len(widgets_values) > 0:
                            api_node['inputs']['value'] = widgets_values[0]
                    elif node_type == 'SaveImage':
                        # SaveImage: [filename_prefix, filename_suffix]
                        if len(widgets_values) >= 1:
                            api_node['inputs']['filename_prefix'] = widgets_values[0]
                        if len(widgets_values) >= 2:
                            api_node['inputs']['filename_suffix'] = widgets_values[1]
                    elif node_type == 'KSampler':
                        # KSampler: [seed, seed_mode, steps, cfg, sampler, scheduler, denoise]
                        if len(widgets_values) >= 1:
                            api_node['inputs']['seed'] = widgets_values[0]
                        if len(widgets_values) >= 2:
                            api_node['inputs']['seed_mode'] = widgets_values[1]
                        if len(widgets_values) >= 3:
                            api_node['inputs']['steps'] = widgets_values[2]
                        if len(widgets_values) >= 4:
                            api_node['inputs']['cfg'] = widgets_values[3]
                        if len(widgets_values) >= 5:
                            api_node['inputs']['sampler_name'] = widgets_values[4]
                        if len(widgets_values) >= 6:
                            api_node['inputs']['scheduler'] = widgets_values[5]
                        if len(widgets_values) >= 7:
                            api_node['inputs']['denoise'] = widgets_values[6]
                    elif node_type == 'EmptyLatentImage' or node_type == 'EmptySD3LatentImage':
                        # EmptyLatentImage: [width, height, batch_size]
                        if len(widgets_values) >= 1:
                            api_node['inputs']['width'] = widgets_values[0]
                        if len(widgets_values) >= 2:
                            api_node['inputs']['height'] = widgets_values[1]
                        if len(widgets_values) >= 3:
                            api_node['inputs']['batch_size'] = widgets_values[2]
                    elif node_type == 'VAELoader':
                        # VAELoader: [vae_name]
                        if len(widgets_values) >= 1:
                            api_node['inputs']['vae_name'] = widgets_values[0]
                    elif node_type == 'KSamplerSelect':
                        # KSamplerSelect: [sampler_name]
                        if len(widgets_values) >= 1:
                            api_node['inputs']['sampler_name'] = widgets_values[0]
                    else:
                        # 其他节点，按索引添加
                        for i, value in enumerate(widgets_values):
                            api_node['inputs'][f'value_{i}'] = value
                
                api_workflow['prompt'][node_id] = api_node
                print(f"  节点 {node_id} 转换完成，inputs: {list(api_node['inputs'].keys())}")
        
        print(f"转换完成，API workflow包含 {len(api_workflow.get('prompt', {}))} 个节点")
        return api_workflow
        
    except Exception as e:
        print(f"转换UI格式到API格式失败: {e}")
        import traceback
        traceback.print_exc()
        return None

# 测试转换
if __name__ == "__main__":
    # 读取workflow文件
    workflow_file = "workflow/nunchaku-flux.1-schnell.json"
    with open(workflow_file, 'r', encoding='utf-8') as f:
        workflow_data = json.load(f)
    
    print("开始转换workflow...")
    api_workflow = convert_ui_to_api_format(workflow_data)
    
    if api_workflow:
        print("\n转换成功！")
        print(f"API workflow包含的节点:")
        for node_id, node_data in api_workflow.get('prompt', {}).items():
            print(f"  {node_id}: {node_data.get('class_type', 'unknown')}")
        
        # 检查SaveImage节点
        save_image_nodes = [node_id for node_id, node_data in api_workflow.get('prompt', {}).items() 
                           if node_data.get('class_type') == 'SaveImage']
        print(f"\nSaveImage节点: {save_image_nodes}")
        for node_id in save_image_nodes:
            node_data = api_workflow['prompt'][node_id]
            print(f"  SaveImage {node_id} inputs: {node_data['inputs']}")
    else:
        print("转换失败！") 