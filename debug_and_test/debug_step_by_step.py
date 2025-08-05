#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import sys
import os

# 添加当前目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import WorkflowRunner

# 测试转换
if __name__ == "__main__":
    # 读取workflow文件
    workflow_file = "workflow/nunchaku-flux.1-schnell.json"
    with open(workflow_file, 'r', encoding='utf-8') as f:
        workflow_data = json.load(f)
    
    print("开始逐步调试转换函数...")
    
    # 创建WorkflowRunner实例
    runner = WorkflowRunner()
    
    # 手动执行转换步骤
    api_workflow = {
        'prompt': {},
        'extra_data': {
            'extra_pnginfo': {
                'workflow': workflow_data
            }
        }
    }
    
    # 构建链接映射：link_id -> (from_node_id, from_output_index)
    links = workflow_data.get('links', [])
    link_mapping = {}
    for link in links:
        if len(link) >= 4:
            link_id = link[0]
            from_node_id = link[1]
            from_output_index = link[2]
            link_mapping[link_id] = (from_node_id, from_output_index)
    
    print(f"链接映射: {link_mapping}")
    
    # 将UI格式的nodes转换为API格式
    nodes = workflow_data.get('nodes', [])
    print(f"总共有 {len(nodes)} 个节点")
    
    for i, node in enumerate(nodes):
        node_id = str(node.get('id', ''))
        node_type = node.get('type', '')
        print(f"\n处理节点 {i}: ID={node_id}, 类型={node_type}")
        
        if not node_id:
            print("  跳过: 没有ID")
            continue
        
        # 创建API格式的节点
        type_mapping = {
            'PrimitiveNode': 'PrimitiveInt',
        }
        
        api_class_type = type_mapping.get(node_type, node_type)
        
        api_node = {
            'class_type': api_class_type,
            'inputs': {}
        }
        
        print(f"  创建API节点: {api_class_type}")
        
        # 处理inputs
        ui_inputs = node.get('inputs', [])
        print(f"  UI inputs: {ui_inputs}")
        
        if isinstance(ui_inputs, list):
            for input_item in ui_inputs:
                if isinstance(input_item, dict):
                    input_name = input_item.get('name', '')
                    if 'link' in input_item:
                        link_id = input_item['link']
                        if link_id in link_mapping:
                            from_node_id, from_output_index = link_mapping[link_id]
                            api_node['inputs'][input_name] = from_node_id
                            print(f"    设置连接 {input_name}: {link_id} -> {from_node_id}")
                        else:
                            api_node['inputs'][input_name] = link_id
                            print(f"    设置连接 {input_name}: {link_id} (未找到映射)")
                    elif 'value' in input_item:
                        api_node['inputs'][input_name] = input_item['value']
                        print(f"    设置值 {input_name}: {input_item['value']}")
                    else:
                        api_node['inputs'][input_name] = input_item
                        print(f"    设置直接值 {input_name}: {input_item}")
        
        # 处理widgets_values
        widgets_values = node.get('widgets_values', [])
        if widgets_values:
            print(f"  widgets_values: {widgets_values}")
            
            if node_type == 'PrimitiveNode':
                if len(widgets_values) > 0:
                    api_node['inputs']['value'] = widgets_values[0]
                    print(f"    设置PrimitiveNode value: {widgets_values[0]}")
            elif node_type == 'SaveImage':
                if len(widgets_values) >= 1:
                    api_node['inputs']['filename_prefix'] = widgets_values[0]
                if len(widgets_values) >= 2:
                    api_node['inputs']['filename_suffix'] = widgets_values[1]
                print(f"    设置SaveImage参数: {api_node['inputs']}")
            elif node_type == 'KSampler':
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
                if len(widgets_values) >= 1:
                    api_node['inputs']['width'] = widgets_values[0]
                if len(widgets_values) >= 2:
                    api_node['inputs']['height'] = widgets_values[1]
                if len(widgets_values) >= 3:
                    api_node['inputs']['batch_size'] = widgets_values[2]
            elif node_type == 'VAELoader':
                if len(widgets_values) >= 1:
                    api_node['inputs']['vae_name'] = widgets_values[0]
            elif node_type == 'KSamplerSelect':
                if len(widgets_values) >= 1:
                    api_node['inputs']['sampler_name'] = widgets_values[0]
            else:
                for i, value in enumerate(widgets_values):
                    api_node['inputs'][f'value_{i}'] = value
                    print(f"    设置value_{i}: {value}")
        
        api_workflow['prompt'][node_id] = api_node
        print(f"  节点 {node_id} 转换完成，inputs: {api_node['inputs']}")
    
    print(f"\n转换完成，API workflow包含 {len(api_workflow.get('prompt', {}))} 个节点")
    
    # 列出所有节点
    for node_id, node_data in api_workflow.get('prompt', {}).items():
        print(f"  节点 {node_id}: {node_data.get('class_type', 'unknown')}")
    
    # 检查SaveImage节点
    save_image_nodes = [node_id for node_id, node_data in api_workflow.get('prompt', {}).items() 
                       if node_data.get('class_type') == 'SaveImage']
    print(f"\nSaveImage节点: {save_image_nodes}")
    for node_id in save_image_nodes:
        node_data = api_workflow['prompt'][node_id]
        print(f"  SaveImage {node_id} inputs: {node_data['inputs']}")
        
        if 'images' in node_data['inputs']:
            images_value = node_data['inputs']['images']
            print(f"    images参数值: {images_value} (类型: {type(images_value)})")
            
            if str(images_value) in api_workflow['prompt']:
                target_node = api_workflow['prompt'][str(images_value)]
                print(f"    目标节点 {images_value}: {target_node['class_type']}")
            else:
                print(f"    警告: 节点 {images_value} 不存在!") 