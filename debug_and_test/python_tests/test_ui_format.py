#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试UI格式workflow处理
"""

import json
import os
import sys

def test_workflow_format():
    """测试workflow格式"""
    print("🔍 测试workflow格式...")
    
    workflow_dir = "workflow"
    if not os.path.exists(workflow_dir):
        print("❌ workflow目录不存在")
        return
    
    # 获取第一个workflow文件
    workflow_files = [f for f in os.listdir(workflow_dir) if f.endswith('.json')]
    if not workflow_files:
        print("❌ 没有找到workflow文件")
        return
    
    test_file = workflow_files[0]
    filepath = os.path.join(workflow_dir, test_file)
    
    print(f"📋 测试文件: {test_file}")
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            workflow_data = json.load(f)
        
        # 检查格式
        print("✅ 文件加载成功")
        
        # 检查nodes格式
        nodes = workflow_data.get('nodes', [])
        print(f"   节点数量: {len(nodes)}")
        
        if nodes:
            first_node = nodes[0]
            print(f"   第一个节点ID: {first_node.get('id')}")
            print(f"   第一个节点类型: {first_node.get('type')}")
            print(f"   是否有class_type: {'class_type' in first_node}")
            
            # 检查是否是UI格式
            if 'type' in first_node and not 'class_type' in first_node:
                print("✅ 确认是UI格式workflow")
                
                # 查找KSampler节点
                ksampler_nodes = [n for n in nodes if 'KSampler' in n.get('type', '')]
                if ksampler_nodes:
                    ksampler = ksampler_nodes[0]
                    print(f"   找到KSampler节点: {ksampler.get('id')}")
                    print(f"   widgets_values: {ksampler.get('widgets_values', [])}")
                
                # 查找CLIPTextEncode节点
                clip_nodes = [n for n in nodes if 'CLIPTextEncode' in n.get('type', '')]
                if clip_nodes:
                    clip = clip_nodes[0]
                    print(f"   找到CLIPTextEncode节点: {clip.get('id')}")
                    print(f"   inputs: {clip.get('inputs', {})}")
                
                # 查找EmptyLatentImage节点
                latent_nodes = [n for n in nodes if 'EmptyLatentImage' in n.get('type', '')]
                if latent_nodes:
                    latent = latent_nodes[0]
                    print(f"   找到EmptyLatentImage节点: {latent.get('id')}")
                    print(f"   widgets_values: {latent.get('widgets_values', [])}")
                
            else:
                print("❌ 不是UI格式workflow")
        
    except Exception as e:
        print(f"❌ 测试失败: {str(e)}")

def test_conversion():
    """测试格式转换"""
    print("\n🔄 测试格式转换...")
    
    # 模拟UI格式的workflow
    ui_workflow = {
        "nodes": [
            {
                "id": 1,
                "type": "KSampler",
                "widgets_values": [20, 7.0, "euler", "normal", -1],
                "inputs": {}
            },
            {
                "id": 2,
                "type": "CLIPTextEncode",
                "inputs": {
                    "text": "a beautiful landscape"
                }
            },
            {
                "id": 3,
                "type": "EmptyLatentImage",
                "widgets_values": [512, 512],
                "inputs": {}
            }
        ]
    }
    
    # 模拟转换函数
    def convert_ui_to_api_format(ui_workflow):
        api_workflow = {
            'prompt': {},
            'extra_data': {
                'extra_pnginfo': {
                    'workflow': ui_workflow
                }
            }
        }
        
        nodes = ui_workflow.get('nodes', [])
        for node in nodes:
            node_id = str(node.get('id', ''))
            if node_id:
                api_node = {
                    'class_type': node.get('type', ''),
                    'inputs': {}
                }
                
                ui_inputs = node.get('inputs', {})
                for input_name, input_data in ui_inputs.items():
                    if isinstance(input_data, dict) and 'link' in input_data:
                        api_node['inputs'][input_name] = input_data['link']
                    elif isinstance(input_data, dict) and 'value' in input_data:
                        api_node['inputs'][input_name] = input_data['value']
                    else:
                        api_node['inputs'][input_name] = input_data
                
                api_workflow['prompt'][node_id] = api_node
        
        return api_workflow
    
    try:
        api_workflow = convert_ui_to_api_format(ui_workflow)
        print("✅ 格式转换成功")
        print(f"   API格式节点数: {len(api_workflow['prompt'])}")
        
        for node_id, node in api_workflow['prompt'].items():
            print(f"   节点 {node_id}: {node['class_type']}")
        
    except Exception as e:
        print(f"❌ 转换失败: {str(e)}")

def main():
    """主函数"""
    print("🧪 UI格式workflow测试")
    print("=" * 50)
    
    test_workflow_format()
    test_conversion()
    
    print("\n" + "=" * 50)
    print("🎉 测试完成")

if __name__ == "__main__":
    main() 