#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import os

def debug_node8():
    """专门调试节点8的问题"""
    workflow_file = "workflow/nunchaku-flux.1-dev.json"
    with open(workflow_file, 'r', encoding='utf-8') as f:
        workflow_data = json.load(f)
    
    print("=== 调试节点8问题 ===")
    
    # 检查原始workflow中的节点8
    nodes = workflow_data.get('nodes', [])
    node8 = None
    for node in nodes:
        if node.get('id') == 8:
            node8 = node
            break
    
    if node8:
        print(f"节点8存在: {node8.get('type')}")
        print(f"节点8的inputs: {node8.get('inputs')}")
        print(f"节点8的widgets_values: {node8.get('widgets_values')}")
    else:
        print("节点8不存在于原始workflow中")
        return
    
    # 检查链接
    links = workflow_data.get('links', [])
    print(f"\n链接数量: {len(links)}")
    
    # 找到指向节点8的链接
    links_to_8 = []
    for link in links:
        if len(link) >= 4 and link[3] == 8:  # link[3]是目标节点ID
            links_to_8.append(link)
    
    print(f"指向节点8的链接: {links_to_8}")
    
    # 找到从节点8出发的链接
    links_from_8 = []
    for link in links:
        if len(link) >= 4 and link[1] == 8:  # link[1]是源节点ID
            links_from_8.append(link)
    
    print(f"从节点8出发的链接: {links_from_8}")
    
    # 模拟转换过程
    print("\n=== 模拟转换过程 ===")
    
    # 构建链接映射
    link_mapping = {}
    for link in links:
        if len(link) >= 4:
            link_id = link[0]
            from_node_id = link[1]
            from_output_index = link[2]
            link_mapping[link_id] = (from_node_id, from_output_index)
    
    print(f"链接映射: {link_mapping}")
    
    # 检查SaveImage节点
    save_image_node = None
    for node in nodes:
        if node.get('type') == 'SaveImage':
            save_image_node = node
            break
    
    if save_image_node:
        print(f"\nSaveImage节点ID: {save_image_node.get('id')}")
        print(f"SaveImage节点inputs: {save_image_node.get('inputs')}")
        
        # 检查SaveImage节点的images输入
        ui_inputs = save_image_node.get('inputs', [])
        if isinstance(ui_inputs, list):
            for input_item in ui_inputs:
                if isinstance(input_item, dict) and input_item.get('name') == 'images':
                    if 'link' in input_item:
                        link_id = input_item['link']
                        print(f"SaveImage的images连接到link_id: {link_id}")
                        if link_id in link_mapping:
                            from_node_id, from_output_index = link_mapping[link_id]
                            print(f"  对应的源节点: {from_node_id}, 输出索引: {from_output_index}")
                        else:
                            print(f"  警告: link_id {link_id} 不在链接映射中")

if __name__ == "__main__":
    debug_node8() 