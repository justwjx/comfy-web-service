#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import os
import sys

# 添加当前目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import WorkflowRunner

# 测试转换
if __name__ == "__main__":
    # 读取workflow文件
    workflow_file = "workflow/nunchaku-flux.1-schnell.json"
    with open(workflow_file, 'r', encoding='utf-8') as f:
        workflow_data = json.load(f)
    
    print("开始直接测试转换函数...")
    
    # 创建WorkflowRunner实例
    runner = WorkflowRunner()
    
    # 直接调用转换函数
    api_workflow = runner.convert_ui_to_api_format(workflow_data)
    
    if api_workflow:
        print(f"\n转换成功！API workflow包含 {len(api_workflow.get('prompt', {}))} 个节点")
        
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
            
            # 检查images参数
            if 'images' in node_data['inputs']:
                images_value = node_data['inputs']['images']
                print(f"    images参数值: {images_value} (类型: {type(images_value)})")
                
                # 检查这个值是否对应一个有效的节点
                if str(images_value) in api_workflow['prompt']:
                    target_node = api_workflow['prompt'][str(images_value)]
                    print(f"    目标节点 {images_value}: {target_node['class_type']}")
                else:
                    print(f"    警告: 节点 {images_value} 不存在!")
    else:
        print("转换失败！") 