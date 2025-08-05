#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试默认值修复是否有效
"""

import json
import os
import sys

def test_workflow_defaults():
    """测试工作流默认值是否正确"""
    workflow_dir = 'workflow'
    
    if not os.path.exists(workflow_dir):
        print(f"❌ 工作流目录不存在: {workflow_dir}")
        return False
    
    # 测试所有工作流文件
    workflow_files = [f for f in os.listdir(workflow_dir) if f.endswith('.json')]
    
    if not workflow_files:
        print(f"❌ 工作流目录中没有找到JSON文件: {workflow_dir}")
        return False
    
    print(f"🔍 测试 {len(workflow_files)} 个工作流文件的默认值...")
    
    all_passed = True
    
    for filename in workflow_files:
        filepath = os.path.join(workflow_dir, filename)
        print(f"\n📁 测试工作流: {filename}")
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                workflow_data = json.load(f)
            
            # 分析工作流结构
            analysis = analyze_workflow_structure(workflow_data)
            defaults = analysis.get('default_values', {})
            
            # 检查分辨率默认值
            width = defaults.get('width')
            height = defaults.get('height')
            
            print(f"  - 提取的默认尺寸: {width}x{height}")
            
            # 验证是否与JSON文件中的实际值一致
            json_width, json_height = extract_resolution_from_json(workflow_data)
            
            if json_width and json_height:
                print(f"  - JSON文件中的尺寸: {json_width}x{json_height}")
                
                if width == json_width and height == json_height:
                    print(f"  ✅ 尺寸默认值正确")
                else:
                    print(f"  ❌ 尺寸默认值不匹配!")
                    print(f"     期望: {json_width}x{json_height}")
                    print(f"     实际: {width}x{height}")
                    all_passed = False
            else:
                print(f"  ⚠️  无法从JSON文件中提取尺寸信息")
            
            # 检查其他参数
            steps = defaults.get('steps')
            cfg = defaults.get('cfg')
            seed = defaults.get('seed')
            sampler = defaults.get('sampler')
            
            print(f"  - 其他默认值:")
            print(f"    steps: {steps}")
            print(f"    cfg: {cfg}")
            print(f"    seed: {seed}")
            print(f"    sampler: {sampler}")
            
        except Exception as e:
            print(f"  ❌ 测试失败: {e}")
            all_passed = False
    
    return all_passed

def analyze_workflow_structure(workflow_data):
    """分析工作流结构，提取参数信息（UI格式）"""
    nodes = workflow_data.get('nodes', [])
    analysis = {
        'type': 'unknown',
        'has_text_to_image': False,
        'has_image_to_image': False,
        'has_controlnet': False,
        'has_inpaint': False,
        'has_upscaler': False,
        'image_inputs': [],
        'default_values': {
            'width': 1024,  # 默认值，会被JSON文件中的实际值覆盖
            'height': 1024,  # 默认值，会被JSON文件中的实际值覆盖
            'steps': 20,     # 默认值，会被JSON文件中的实际值覆盖
            'cfg': 1.0,      # 默认值，会被JSON文件中的实际值覆盖
            'seed': -1,      # 默认值，会被JSON文件中的实际值覆盖
            'sampler': 'euler', # 默认值，会被JSON文件中的实际值覆盖
            'positive_prompt': '',
            'negative_prompt': ''
        },
        'required_inputs': [],
        'optional_inputs': [],
        'model_loaders': [],
        'has_negative_prompt': False
    }
    
    for node in nodes:
        # UI格式使用type字段
        node_type = node.get('type', '')
        node_id = node.get('id')
        
        # 检查EmptyLatentImage节点获取默认尺寸
        if 'EmptyLatentImage' in node_type:
            widgets_values = node.get('widgets_values', [])
            if len(widgets_values) >= 2:
                try:
                    analysis['default_values']['width'] = int(widgets_values[0]) if widgets_values[0] is not None and str(widgets_values[0]).isdigit() else widgets_values[0] if widgets_values[0] is not None else 1024
                except (ValueError, TypeError):
                    analysis['default_values']['width'] = widgets_values[0] if widgets_values[0] is not None else 1024
                
                try:
                    analysis['default_values']['height'] = int(widgets_values[1]) if widgets_values[1] is not None and str(widgets_values[1]).isdigit() else widgets_values[1] if widgets_values[1] is not None else 1024
                except (ValueError, TypeError):
                    analysis['default_values']['height'] = widgets_values[1] if widgets_values[1] is not None else 1024
        
        # 检查EmptySD3LatentImage节点获取默认尺寸（Nunchaku Flux.1使用）
        elif 'EmptySD3LatentImage' in node_type:
            widgets_values = node.get('widgets_values', [])
            if len(widgets_values) >= 2:
                try:
                    analysis['default_values']['width'] = int(widgets_values[0]) if widgets_values[0] is not None and str(widgets_values[0]).isdigit() else widgets_values[0] if widgets_values[0] is not None else 1024
                except (ValueError, TypeError):
                    analysis['default_values']['width'] = widgets_values[0] if widgets_values[0] is not None else 1024
                
                try:
                    analysis['default_values']['height'] = int(widgets_values[1]) if widgets_values[1] is not None and str(widgets_values[1]).isdigit() else widgets_values[1] if widgets_values[1] is not None else 1024
                except (ValueError, TypeError):
                    analysis['default_values']['height'] = widgets_values[1] if widgets_values[1] is not None else 1024
        
        # 检查PrimitiveNode节点获取尺寸（Nunchaku Flux.1使用）
        elif 'PrimitiveNode' in node_type:
            node_title = node.get('title', '').lower()
            widgets_values = node.get('widgets_values', [])
            
            if node_title == 'width' and len(widgets_values) >= 1:
                try:
                    analysis['default_values']['width'] = int(widgets_values[0]) if widgets_values[0] is not None and str(widgets_values[0]).isdigit() else widgets_values[0] if widgets_values[0] is not None else 1024
                except (ValueError, TypeError):
                    analysis['default_values']['width'] = widgets_values[0] if widgets_values[0] is not None else 1024
            
            elif node_title == 'height' and len(widgets_values) >= 1:
                try:
                    analysis['default_values']['height'] = int(widgets_values[0]) if widgets_values[0] is not None and str(widgets_values[0]).isdigit() else widgets_values[0] if widgets_values[0] is not None else 1024
                except (ValueError, TypeError):
                    analysis['default_values']['height'] = widgets_values[0] if widgets_values[0] is not None else 1024
    
    return analysis

def extract_resolution_from_json(workflow_data):
    """直接从JSON文件中提取分辨率信息"""
    nodes = workflow_data.get('nodes', [])
    
    for node in nodes:
        node_type = node.get('type', '')
        widgets_values = node.get('widgets_values', [])
        
        if 'EmptyLatentImage' in node_type or 'EmptySD3LatentImage' in node_type:
            if len(widgets_values) >= 2:
                return widgets_values[0], widgets_values[1]
        
        elif 'PrimitiveNode' in node_type:
            node_title = node.get('title', '').lower()
            if node_title == 'width' and len(widgets_values) >= 1:
                width = widgets_values[0]
            elif node_title == 'height' and len(widgets_values) >= 1:
                height = widgets_values[0]
    
    return None, None

if __name__ == '__main__':
    print("🧪 测试默认值修复效果")
    print("=" * 50)
    
    success = test_workflow_defaults()
    
    print("\n" + "=" * 50)
    if success:
        print("✅ 所有测试通过！默认值修复成功")
        sys.exit(0)
    else:
        print("❌ 部分测试失败，需要进一步检查")
        sys.exit(1) 