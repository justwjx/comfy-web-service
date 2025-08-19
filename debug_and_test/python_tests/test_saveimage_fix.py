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
        
        # 构建链接映射：link_id -> (from_node_id, from_output_index)
        links = ui_workflow.get('links', [])
        link_mapping = {}
        for link in links:
            if len(link) >= 4:
                link_id = link[0]
                from_node_id = link[1]
                from_output_index = link[2]
                link_mapping[link_id] = (from_node_id, from_output_index)
        
        print(f"链接映射: {link_mapping}")
        
        # 将UI格式的nodes转换为API格式
        nodes = ui_workflow.get('nodes', [])
        print(f"原始节点数量: {len(nodes)}")
        
        # 节点类型映射：UI格式 -> API格式
        type_mapping = {
            'PrimitiveNode': 'PrimitiveInt',  # UI的PrimitiveNode -> API的PrimitiveInt
        }
        
        for node in nodes:
            node_id = str(node.get('id', ''))
            node_type = node.get('type', '')
            print(f"处理节点 {node_id}: {node_type}")
            
            if not node_id:
                print(f"  跳过节点 {node_id}: 没有ID")
                continue  # 跳过没有ID的节点
            
            # 创建API格式的节点
            api_class_type = type_mapping.get(node_type, node_type)
            
            api_node = {
                'class_type': api_class_type,  # 使用映射后的类型
                'inputs': {}
            }
            
            # 处理inputs - UI格式中inputs是数组
            ui_inputs = node.get('inputs', [])
            if isinstance(ui_inputs, list):
                for input_item in ui_inputs:
                    if isinstance(input_item, dict):
                        input_name = input_item.get('name', '')
                        if 'link' in input_item:
                            # 这是连接，使用链接映射找到正确的节点ID
                            link_id = input_item['link']
                            if link_id in link_mapping:
                                from_node_id, from_output_index = link_mapping[link_id]
                                # 对于SaveImage节点的images参数，需要特殊处理
                                if node_type == 'SaveImage' and input_name == 'images':
                                    api_node['inputs'][input_name] = [from_node_id, from_output_index]
                                    print(f"  SaveImage节点 {node_id} 的images参数设置为: {api_node['inputs'][input_name]}")
                                else:
                                    api_node['inputs'][input_name] = from_node_id
                            else:
                                # 如果找不到映射，保持link ID（兼容性）
                                api_node['inputs'][input_name] = link_id
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
            print(f"  节点 {node_id} 的widgets_values: {widgets_values}")
            if widgets_values:
                # 根据节点类型处理widgets_values
                if node.get('type') == 'PrimitiveNode':
                    # PrimitiveNode -> PrimitiveInt，需要value参数
                    if len(widgets_values) > 0:
                        api_node['inputs']['value'] = widgets_values[0]
                elif node.get('type') == 'SaveImage':
                    # SaveImage: [filename_prefix, filename_suffix]
                    if len(widgets_values) >= 1:
                        api_node['inputs']['filename_prefix'] = widgets_values[0]
                    if len(widgets_values) >= 2:
                        api_node['inputs']['filename_suffix'] = widgets_values[1]
                elif node.get('type') == 'KSampler':
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
                elif node.get('type') == 'EmptyLatentImage' or node.get('type') == 'EmptySD3LatentImage':
                    # EmptyLatentImage: [width, height, batch_size]
                    if len(widgets_values) >= 1:
                        api_node['inputs']['width'] = widgets_values[0]
                    if len(widgets_values) >= 2:
                        api_node['inputs']['height'] = widgets_values[1]
                    if len(widgets_values) >= 3:
                        api_node['inputs']['batch_size'] = widgets_values[2]
                elif node.get('type') == 'VAELoader':
                    # VAELoader: [vae_name]
                    if len(widgets_values) >= 1:
                        api_node['inputs']['vae_name'] = widgets_values[0]
                elif node.get('type') == 'KSamplerSelect':
                    # KSamplerSelect: [sampler_name]
                    if len(widgets_values) >= 1:
                        api_node['inputs']['sampler_name'] = widgets_values[0]
                else:
                    # 其他节点，按索引添加
                    for i, value in enumerate(widgets_values):
                        api_node['inputs'][f'value_{i}'] = value
            
            # 确保所有节点都被添加到API workflow中，即使没有widgets_values
            api_workflow['prompt'][node_id] = api_node
            print(f"  添加节点 {node_id} 到API workflow")
        
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
        
        # 检查所有节点
        print(f"\n转换后的节点数量: {len(api_workflow.get('prompt', {}))}")
        print("所有节点ID:")
        for node_id in sorted(api_workflow.get('prompt', {}).keys(), key=int):
            node_data = api_workflow['prompt'][node_id]
            print(f"  节点 {node_id}: {node_data.get('class_type', 'Unknown')}")
        
        # 检查SaveImage节点
        save_image_nodes = [node_id for node_id, node_data in api_workflow.get('prompt', {}).items() 
                           if node_data.get('class_type') == 'SaveImage']
        print(f"\nSaveImage节点: {save_image_nodes}")
        for node_id in save_image_nodes:
            node_data = api_workflow['prompt'][node_id]
            print(f"  SaveImage {node_id} inputs: {node_data['inputs']}")
            
            # 检查images参数
            if 'images' in node_data['inputs']:
                images_value = node_data['inputs']['images']
                print(f"    images参数值: {images_value} (类型: {type(images_value)})")
                
                # 检查这个值是否对应一个有效的节点
                if isinstance(images_value, list) and len(images_value) > 0:
                    target_node_id = images_value[0]
                    if str(target_node_id) in api_workflow['prompt']:
                        target_node = api_workflow['prompt'][str(target_node_id)]
                        print(f"    目标节点 {target_node_id}: {target_node['class_type']}")
                    else:
                        print(f"    警告: 节点 {target_node_id} 不存在!")
                        print(f"    可用的节点ID: {list(api_workflow['prompt'].keys())}")
                elif str(images_value) in api_workflow['prompt']:
                    target_node = api_workflow['prompt'][str(images_value)]
                    print(f"    目标节点 {images_value}: {target_node['class_type']}")
                else:
                    print(f"    警告: 节点 {images_value} 不存在!")
    else:
        print("转换失败！") 