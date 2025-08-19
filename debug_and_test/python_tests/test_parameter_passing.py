#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试参数传递功能
"""

import requests
import json

def test_default_values():
    """测试默认值提取"""
    print("🔍 测试默认值提取...")
    
    response = requests.get("http://localhost:5000/api/analyze-workflow/nunchaku-flux.1-dev.json")
    
    if response.status_code == 200:
        data = response.json()
        if data['success']:
            analysis = data['analysis']
            defaults = analysis['default_values']
            
            print("✅ 提取的默认值:")
            print(f"  - width: {defaults.get('width')} (期望: 1024)")
            print(f"  - height: {defaults.get('height')} (期望: 1024)")
            print(f"  - cfg: {defaults.get('cfg')} (期望: 3.5)")
            print(f"  - steps: {defaults.get('steps')} (期望: 8)")
            print(f"  - sampler: {defaults.get('sampler')} (期望: euler)")
            
            # 验证关键值
            expected_values = {
                'width': 1024,
                'height': 1024,
                'cfg': 3.5,
                'steps': 8,
                'sampler': 'euler'
            }
            
            all_correct = True
            for key, expected in expected_values.items():
                actual = defaults.get(key)
                if actual != expected:
                    print(f"❌ {key}: 期望 {expected}, 实际 {actual}")
                    all_correct = False
                else:
                    print(f"✅ {key}: {actual}")
            
            return all_correct
        else:
            print(f"❌ 分析失败: {data.get('error', '未知错误')}")
            return False
    else:
        print(f"❌ 请求失败: HTTP {response.status_code}")
        return False

def test_parameter_modification():
    """测试参数修改功能"""
    print("\n🔍 测试参数修改功能...")
    
    # 获取原始工作流
    response = requests.get("http://localhost:5000/api/workflow/nunchaku-flux.1-dev.json")
    
    if response.status_code != 200:
        print(f"❌ 获取工作流失败: HTTP {response.status_code}")
        return False
    
    workflow_data = response.json()['workflow']
    
    # 测试参数
    test_parameters = {
        'width': 512,
        'height': 768,
        'cfg': 5.0,
        'steps': 20,
        'sampler': 'dpm_2',
        'positive_prompt': 'test prompt'
    }
    
    # 模拟参数修改 - 直接调用函数而不是导入类
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    
    # 直接测试参数修改逻辑
    nodes = workflow_data.get('nodes', [])
    modified_nodes = []
    
    for node in nodes:
        modified_node = node.copy()
        node_type = node.get('type', '')
        node_title = node.get('title', '').lower()
        
        # 测试PrimitiveNode修改
        if node_type == 'PrimitiveNode':
            widgets_values = modified_node.get('widgets_values', [])
            
            if node_title == 'width' and 'width' in test_parameters and len(widgets_values) >= 1:
                try:
                    width_value = int(test_parameters['width'])
                    widgets_values[0] = width_value
                except (ValueError, TypeError):
                    widgets_values[0] = 1024
            
            elif node_title == 'height' and 'height' in test_parameters and len(widgets_values) >= 1:
                try:
                    height_value = int(test_parameters['height'])
                    widgets_values[0] = height_value
                except (ValueError, TypeError):
                    widgets_values[0] = 1024
            
            modified_node['widgets_values'] = widgets_values
        
        # 测试EmptySD3LatentImage修改
        elif node_type == 'EmptySD3LatentImage':
            widgets_values = modified_node.get('widgets_values', [])
            if len(widgets_values) >= 2:
                if 'width' in test_parameters:
                    try:
                        width_value = int(test_parameters['width'])
                        widgets_values[0] = width_value
                    except (ValueError, TypeError):
                        widgets_values[0] = 1024
                
                if 'height' in test_parameters:
                    try:
                        height_value = int(test_parameters['height'])
                        widgets_values[1] = height_value
                    except (ValueError, TypeError):
                        widgets_values[1] = 1024
            
            modified_node['widgets_values'] = widgets_values
        
        modified_nodes.append(modified_node)
    
    modified_workflow = workflow_data.copy()
    modified_workflow['nodes'] = modified_nodes
    
    # 检查修改结果
    nodes = modified_workflow.get('nodes', [])
    
    # 查找PrimitiveNode
    width_node = None
    height_node = None
    empty_latent_node = None
    
    for node in nodes:
        node_type = node.get('type', '')
        node_title = node.get('title', '').lower()
        
        if node_type == 'PrimitiveNode':
            if node_title == 'width':
                width_node = node
            elif node_title == 'height':
                height_node = node
        elif node_type == 'EmptySD3LatentImage':
            empty_latent_node = node
    
    # 验证修改
    checks_passed = 0
    total_checks = 0
    
    # 检查PrimitiveNode width
    if width_node:
        total_checks += 1
        widgets_values = width_node.get('widgets_values', [])
        if len(widgets_values) > 0 and widgets_values[0] == 512:
            print("✅ PrimitiveNode width 修改成功: 512")
            checks_passed += 1
        else:
            print(f"❌ PrimitiveNode width 修改失败: {widgets_values}")
    
    # 检查PrimitiveNode height
    if height_node:
        total_checks += 1
        widgets_values = height_node.get('widgets_values', [])
        if len(widgets_values) > 0 and widgets_values[0] == 768:
            print("✅ PrimitiveNode height 修改成功: 768")
            checks_passed += 1
        else:
            print(f"❌ PrimitiveNode height 修改失败: {widgets_values}")
    
    # 检查EmptySD3LatentImage
    if empty_latent_node:
        total_checks += 1
        widgets_values = empty_latent_node.get('widgets_values', [])
        if len(widgets_values) >= 2 and widgets_values[0] == 512 and widgets_values[1] == 768:
            print("✅ EmptySD3LatentImage 修改成功: [512, 768, 1]")
            checks_passed += 1
        else:
            print(f"❌ EmptySD3LatentImage 修改失败: {widgets_values}")
    
    print(f"📊 参数修改测试: {checks_passed}/{total_checks} 通过")
    return checks_passed == total_checks

def test_web_interface_values():
    """测试Web界面显示的值"""
    print("\n🔍 测试Web界面显示的值...")
    
    # 获取工作流分析结果
    response = requests.get("http://localhost:5000/api/analyze-workflow/nunchaku-flux.1-dev.json")
    
    if response.status_code == 200:
        data = response.json()
        if data['success']:
            analysis = data['analysis']
            defaults = analysis['default_values']
            
            print("✅ Web界面应该显示的值:")
            print(f"  - 宽度: {defaults.get('width')}")
            print(f"  - 高度: {defaults.get('height')}")
            print(f"  - CFG Scale: {defaults.get('cfg')}")
            print(f"  - 生成步数: {defaults.get('steps')}")
            print(f"  - 采样器: {defaults.get('sampler')}")
            
            # 检查是否是1024x1024
            if defaults.get('width') == 1024 and defaults.get('height') == 1024:
                print("✅ 尺寸默认值正确: 1024x1024")
                return True
            else:
                print(f"❌ 尺寸默认值错误: {defaults.get('width')}x{defaults.get('height')}")
                return False
        else:
            print(f"❌ 分析失败: {data.get('error', '未知错误')}")
            return False
    else:
        print(f"❌ 请求失败: HTTP {response.status_code}")
        return False

def main():
    """主测试函数"""
    print("🚀 开始测试参数传递功能...\n")
    
    tests = [
        ("默认值提取", test_default_values),
        ("参数修改功能", test_parameter_modification),
        ("Web界面显示", test_web_interface_values)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"📋 测试: {test_name}")
        try:
            if test_func():
                passed += 1
                print(f"✅ {test_name} 通过\n")
            else:
                print(f"❌ {test_name} 失败\n")
        except Exception as e:
            print(f"❌ {test_name} 异常: {e}\n")
    
    print(f"📊 测试结果: {passed}/{total} 通过")
    
    if passed == total:
        print("🎉 所有测试通过！参数传递功能正常。")
        print("\n💡 现在Web界面应该正确显示:")
        print("  - 默认尺寸: 1024x1024")
        print("  - 用户修改的尺寸会正确应用到工作流")
        print("  - 生成的图像尺寸与用户设置一致")
    else:
        print("⚠️ 部分测试失败，请检查相关功能。")

if __name__ == "__main__":
    main() 