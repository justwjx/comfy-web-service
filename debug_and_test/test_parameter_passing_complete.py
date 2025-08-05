#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
全面测试参数传递是否正确
"""

import json
import os
import sys
import requests
import time

def test_parameter_passing():
    """测试参数传递是否正确"""
    print("🧪 测试参数传递功能")
    print("=" * 60)
    
    # 测试服务器是否运行
    try:
        response = requests.get('http://localhost:5000/api/workflows', timeout=5)
        if response.status_code != 200:
            print("❌ 服务器未运行或无法访问")
            return False
    except Exception as e:
        print(f"❌ 无法连接到服务器: {e}")
        return False
    
    print("✅ 服务器连接正常")
    
    # 获取工作流列表
    try:
        response = requests.get('http://localhost:5000/api/workflows')
        workflows = response.json()
        
        if not workflows.get('success'):
            print("❌ 获取工作流列表失败")
            return False
        
        workflow_list = workflows.get('workflows', [])
        if not workflow_list:
            print("❌ 没有找到工作流")
            return False
        
        print(f"📁 找到 {len(workflow_list)} 个工作流")
        
    except Exception as e:
        print(f"❌ 获取工作流列表失败: {e}")
        return False
    
    # 测试第一个工作流
    test_workflow = workflow_list[0]
    filename = test_workflow['filename']
    
    print(f"\n🔍 测试工作流: {filename}")
    
    # 获取工作流详情
    try:
        response = requests.get(f'http://localhost:5000/api/analyze-workflow/{filename}')
        analysis = response.json()
        
        if not analysis.get('success'):
            print("❌ 获取工作流分析失败")
            return False
        
        workflow_analysis = analysis.get('analysis', {})
        defaults = workflow_analysis.get('default_values', {})
        
        print(f"📊 工作流分析结果:")
        print(f"  - 类型: {workflow_analysis.get('type', 'unknown')}")
        print(f"  - 默认尺寸: {defaults.get('width')}x{defaults.get('height')}")
        print(f"  - 默认步数: {defaults.get('steps')}")
        print(f"  - 默认CFG: {defaults.get('cfg')}")
        print(f"  - 默认采样器: {defaults.get('sampler')}")
        
    except Exception as e:
        print(f"❌ 获取工作流分析失败: {e}")
        return False
    
    # 测试参数传递
    test_parameters = {
        'width': 512,
        'height': 512,
        'steps': 30,
        'cfg': 7.5,
        'seed': 12345,
        'sampler': 'dpmpp_2m',
        'positive_prompt': 'test positive prompt',
        'negative_prompt': 'test negative prompt'
    }
    
    print(f"\n🧪 测试参数传递:")
    for key, value in test_parameters.items():
        print(f"  - {key}: {value}")
    
    # 提交任务
    try:
        task_data = {
            'filename': filename,
            'parameters': test_parameters
        }
        
        response = requests.post('http://localhost:5000/api/run', json=task_data)
        result = response.json()
        
        if not result.get('success'):
            print(f"❌ 提交任务失败: {result.get('error', '未知错误')}")
            return False
        
        task_id = result.get('task_id')
        print(f"✅ 任务提交成功，任务ID: {task_id}")
        
    except Exception as e:
        print(f"❌ 提交任务失败: {e}")
        return False
    
    # 等待任务完成（最多等待30秒）
    print(f"\n⏳ 等待任务完成...")
    max_wait = 30
    wait_time = 0
    
    while wait_time < max_wait:
        try:
            response = requests.get(f'http://localhost:5000/api/status/{task_id}')
            status = response.json()
            
            if status.get('success'):
                task = status.get('task', {})
                task_status = task.get('status')
                progress = task.get('progress', 0)
                
                print(f"  - 状态: {task_status}, 进度: {progress}%")
                
                if task_status == 'completed':
                    print("✅ 任务完成")
                    
                    # 检查输出
                    outputs = task.get('outputs', {})
                    if outputs:
                        print(f"📸 生成了 {len(outputs)} 个输出")
                        for output_type, output_data in outputs.items():
                            print(f"  - {output_type}: {len(output_data)} 个文件")
                    else:
                        print("⚠️  没有输出文件")
                    
                    return True
                
                elif task_status == 'failed':
                    error = task.get('error', '未知错误')
                    print(f"❌ 任务失败: {error}")
                    return False
            
            time.sleep(2)
            wait_time += 2
            
        except Exception as e:
            print(f"❌ 检查任务状态失败: {e}")
            return False
    
    print(f"❌ 任务超时（等待了{max_wait}秒）")
    return False

def test_default_values_consistency():
    """测试默认值一致性"""
    print("\n🔍 测试默认值一致性")
    print("=" * 60)
    
    workflow_dir = 'workflow'
    if not os.path.exists(workflow_dir):
        print(f"❌ 工作流目录不存在: {workflow_dir}")
        return False
    
    workflow_files = [f for f in os.listdir(workflow_dir) if f.endswith('.json')]
    
    all_consistent = True
    
    for filename in workflow_files:
        filepath = os.path.join(workflow_dir, filename)
        print(f"\n📁 检查工作流: {filename}")
        
        try:
            # 从JSON文件直接读取
            with open(filepath, 'r', encoding='utf-8') as f:
                workflow_data = json.load(f)
            
            # 从API获取分析结果
            response = requests.get(f'http://localhost:5000/api/analyze-workflow/{filename}')
            if not response.status_code == 200:
                print(f"  ❌ API请求失败")
                all_consistent = False
                continue
            
            analysis = response.json()
            if not analysis.get('success'):
                print(f"  ❌ API分析失败")
                all_consistent = False
                continue
            
            api_defaults = analysis.get('analysis', {}).get('default_values', {})
            
            # 从JSON文件提取默认值
            json_width, json_height = extract_resolution_from_json(workflow_data)
            
            if json_width and json_height:
                print(f"  - JSON文件尺寸: {json_width}x{json_height}")
                print(f"  - API提取尺寸: {api_defaults.get('width')}x{api_defaults.get('height')}")
                
                if json_width == api_defaults.get('width') and json_height == api_defaults.get('height'):
                    print(f"  ✅ 尺寸一致")
                else:
                    print(f"  ❌ 尺寸不一致!")
                    all_consistent = False
            else:
                print(f"  ⚠️  无法从JSON文件提取尺寸")
            
        except Exception as e:
            print(f"  ❌ 检查失败: {e}")
            all_consistent = False
    
    return all_consistent

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
    print("🧪 全面测试参数传递功能")
    print("=" * 60)
    
    # 测试1: 参数传递
    test1_passed = test_parameter_passing()
    
    # 测试2: 默认值一致性
    test2_passed = test_default_values_consistency()
    
    print("\n" + "=" * 60)
    print("📊 测试结果总结:")
    print(f"  - 参数传递测试: {'✅ 通过' if test1_passed else '❌ 失败'}")
    print(f"  - 默认值一致性测试: {'✅ 通过' if test2_passed else '❌ 失败'}")
    
    if test1_passed and test2_passed:
        print("\n🎉 所有测试通过！参数传递功能正常")
        sys.exit(0)
    else:
        print("\n❌ 部分测试失败，需要进一步检查")
        sys.exit(1) 