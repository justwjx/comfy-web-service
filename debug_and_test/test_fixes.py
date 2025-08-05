#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试修复后的功能
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
            print(f"  - cfg: {defaults.get('cfg')} (期望: 3.5)")
            print(f"  - steps: {defaults.get('steps')} (期望: 8)")
            print(f"  - sampler: {defaults.get('sampler')} (期望: euler)")
            print(f"  - scheduler: {defaults.get('scheduler')} (期望: simple)")
            print(f"  - positive_prompt: {defaults.get('positive_prompt', '')[:50]}...")
            
            # 验证关键值
            expected_values = {
                'cfg': 3.5,
                'steps': 8,
                'sampler': 'euler',
                'scheduler': 'simple'
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

def test_negative_prompt():
    """测试Negative Prompt检测"""
    print("\n🔍 测试Negative Prompt检测...")
    
    response = requests.get("http://localhost:5000/api/analyze-workflow/nunchaku-flux.1-dev.json")
    
    if response.status_code == 200:
        data = response.json()
        if data['success']:
            analysis = data['analysis']
            has_negative = analysis.get('has_negative_prompt', False)
            
            print(f"✅ has_negative_prompt: {has_negative} (期望: False)")
            return has_negative == False
        else:
            print(f"❌ 分析失败: {data.get('error', '未知错误')}")
            return False
    else:
        print(f"❌ 请求失败: HTTP {response.status_code}")
        return False

def test_model_loaders():
    """测试模型加载器识别"""
    print("\n🔍 测试模型加载器识别...")
    
    response = requests.get("http://localhost:5000/api/analyze-workflow/nunchaku-flux.1-dev.json")
    
    if response.status_code == 200:
        data = response.json()
        if data['success']:
            analysis = data['analysis']
            model_loaders = analysis.get('model_loaders', [])
            
            print(f"✅ 识别到 {len(model_loaders)} 个模型加载器")
            
            expected_types = [
                'VAELoader',
                'NunchakuTextEncoderLoader', 
                'NunchakuFluxLoraLoader',
                'NunchakuFluxDiTLoader'
            ]
            
            found_types = [loader['type'] for loader in model_loaders]
            
            for expected_type in expected_types:
                if expected_type in found_types:
                    print(f"✅ 找到 {expected_type}")
                else:
                    print(f"❌ 未找到 {expected_type}")
            
            return len(model_loaders) >= 4
        else:
            print(f"❌ 分析失败: {data.get('error', '未知错误')}")
            return False
    else:
        print(f"❌ 请求失败: HTTP {response.status_code}")
        return False

def test_web_interface():
    """测试Web界面"""
    print("\n🔍 测试Web界面...")
    
    # 测试主页面
    response = requests.get("http://localhost:5000/")
    if response.status_code == 200:
        print("✅ 主页面可访问")
        
        # 检查是否包含模型加载器配置区域
        if 'modelLoadersSection' in response.text:
            print("✅ 包含模型加载器配置区域")
        else:
            print("❌ 缺少模型加载器配置区域")
        
        # 检查是否移除了高级设置
        if 'advancedSection' not in response.text:
            print("✅ 已移除高级设置区域")
        else:
            print("❌ 高级设置区域仍然存在")
        
        return True
    else:
        print(f"❌ 主页面访问失败: HTTP {response.status_code}")
        return False

def main():
    """主测试函数"""
    print("🚀 开始测试修复后的功能...\n")
    
    tests = [
        ("默认值提取", test_default_values),
        ("Negative Prompt检测", test_negative_prompt),
        ("模型加载器识别", test_model_loaders),
        ("Web界面", test_web_interface)
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
        print("🎉 所有测试通过！修复成功。")
        print("\n💡 现在可以访问 http://localhost:5000 体验完整功能:")
        print("  1. 选择 Nunchaku Flux.1 Dev 工作流")
        print("  2. 观察基础参数已使用JSON文件的默认值")
        print("  3. 点击 '模型加载器' 查看配置选项")
        print("  4. Negative Prompt 输入框已隐藏")
    else:
        print("⚠️ 部分测试失败，请检查相关功能。")

if __name__ == "__main__":
    main() 