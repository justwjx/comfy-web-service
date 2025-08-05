#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试新功能的脚本
"""

import requests
import json

def test_workflow_analysis():
    """测试工作流分析功能"""
    print("🔍 测试工作流分析功能...")
    
    # 测试Nunchaku Flux.1 Dev工作流
    response = requests.get("http://localhost:5000/api/analyze-workflow/nunchaku-flux.1-dev.json")
    
    if response.status_code == 200:
        data = response.json()
        if data['success']:
            analysis = data['analysis']
            
            print(f"✅ 工作流类型: {analysis['type']}")
            print(f"✅ 是否有negative prompt: {analysis['has_negative_prompt']}")
            print(f"✅ 模型加载器数量: {len(analysis['model_loaders'])}")
            
            # 检查模型加载器
            for loader in analysis['model_loaders']:
                print(f"  📦 {loader['name']} ({loader['type']})")
                for param_name, param_value in loader['parameters'].items():
                    print(f"    - {param_name}: {param_value}")
            
            return True
        else:
            print(f"❌ 分析失败: {data.get('error', '未知错误')}")
            return False
    else:
        print(f"❌ 请求失败: HTTP {response.status_code}")
        return False

def test_workflow_list():
    """测试工作流列表功能"""
    print("\n📋 测试工作流列表功能...")
    
    response = requests.get("http://localhost:5000/api/workflows")
    
    if response.status_code == 200:
        data = response.json()
        if data['success']:
            workflows = data['workflows']
            print(f"✅ 找到 {len(workflows)} 个工作流")
            
            # 查找Nunchaku Flux.1 Dev工作流
            for workflow in workflows:
                if 'nunchaku-flux.1-dev' in workflow['filename']:
                    print(f"✅ 找到目标工作流: {workflow['name']}")
                    return True
            
            print("❌ 未找到目标工作流")
            return False
        else:
            print(f"❌ 获取工作流列表失败: {data.get('error', '未知错误')}")
            return False
    else:
        print(f"❌ 请求失败: HTTP {response.status_code}")
        return False

def test_server_status():
    """测试服务器状态"""
    print("\n🖥️ 测试服务器状态...")
    
    response = requests.get("http://localhost:5000/api/comfyui/status")
    
    if response.status_code == 200:
        data = response.json()
        print(f"✅ ComfyUI状态: {data.get('status', 'unknown')}")
        return True
    else:
        print(f"❌ 无法获取服务器状态: HTTP {response.status_code}")
        return False

def main():
    """主测试函数"""
    print("🚀 开始测试新功能...\n")
    
    tests = [
        test_server_status,
        test_workflow_list,
        test_workflow_analysis
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        try:
            if test():
                passed += 1
        except Exception as e:
            print(f"❌ 测试异常: {e}")
    
    print(f"\n📊 测试结果: {passed}/{total} 通过")
    
    if passed == total:
        print("🎉 所有测试通过！新功能正常工作。")
    else:
        print("⚠️ 部分测试失败，请检查相关功能。")

if __name__ == "__main__":
    main() 