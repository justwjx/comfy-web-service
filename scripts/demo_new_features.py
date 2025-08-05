#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
演示新功能的脚本
"""

import requests
import json
import time

def print_header(title):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")

def print_section(title):
    print(f"\n{'-'*40}")
    print(f"  {title}")
    print(f"{'-'*40}")

def demo_workflow_analysis():
    """演示工作流分析功能"""
    print_section("1. 工作流分析功能演示")
    
    # 分析Nunchaku Flux.1 Dev工作流
    response = requests.get("http://localhost:5000/api/analyze-workflow/nunchaku-flux.1-dev.json")
    
    if response.status_code == 200:
        data = response.json()
        if data['success']:
            analysis = data['analysis']
            
            print(f"✅ 工作流类型: {analysis['type']}")
            print(f"✅ 是否有negative prompt: {analysis['has_negative_prompt']}")
            print(f"✅ 模型加载器数量: {len(analysis['model_loaders'])}")
            
            print("\n📦 检测到的模型加载器:")
            for i, loader in enumerate(analysis['model_loaders'], 1):
                print(f"  {i}. {loader['name']} ({loader['type']})")
                for param_name, param_value in loader['parameters'].items():
                    print(f"     - {param_name}: {param_value}")
        else:
            print(f"❌ 分析失败: {data.get('error', '未知错误')}")
    else:
        print(f"❌ 请求失败: HTTP {response.status_code}")

def demo_negative_prompt_detection():
    """演示Negative Prompt检测功能"""
    print_section("2. Negative Prompt检测功能演示")
    
    # 测试多个工作流
    workflows_to_test = [
        "nunchaku-flux.1-dev.json",
        "nunchaku-flux.1-canny.json",
        "nunchaku-flux.1-redux-dev.json"
    ]
    
    for workflow in workflows_to_test:
        try:
            response = requests.get(f"http://localhost:5000/api/analyze-workflow/{workflow}")
            if response.status_code == 200:
                data = response.json()
                if data['success']:
                    analysis = data['analysis']
                    status = "✅ 有" if analysis['has_negative_prompt'] else "❌ 无"
                    print(f"{status} Negative Prompt - {workflow}")
                else:
                    print(f"❓ 分析失败 - {workflow}")
            else:
                print(f"❓ 请求失败 - {workflow}")
        except Exception as e:
            print(f"❓ 异常 - {workflow}: {e}")

def demo_model_loaders():
    """演示模型加载器识别功能"""
    print_section("3. 模型加载器识别功能演示")
    
    response = requests.get("http://localhost:5000/api/analyze-workflow/nunchaku-flux.1-dev.json")
    
    if response.status_code == 200:
        data = response.json()
        if data['success']:
            analysis = data['analysis']
            
            print("🔍 支持的模型加载器类型:")
            loader_types = set(loader['type'] for loader in analysis['model_loaders'])
            for loader_type in sorted(loader_types):
                print(f"  - {loader_type}")
            
            print(f"\n📊 当前工作流包含 {len(analysis['model_loaders'])} 个模型加载器:")
            for loader in analysis['model_loaders']:
                print(f"  📦 {loader['name']}")
                print(f"     类型: {loader['type']}")
                print(f"     参数数量: {len(loader['parameters'])}")
                print(f"     节点ID: {loader['node_id']}")

def demo_web_interface():
    """演示Web界面功能"""
    print_section("4. Web界面功能演示")
    
    print("🌐 访问以下URL来体验新功能:")
    print("  主页面: http://localhost:5000")
    print("  测试页面: http://localhost:5000/test_frontend")
    print("  图片画廊: http://localhost:5000/gallery")
    
    print("\n📋 使用步骤:")
    print("  1. 打开主页面 http://localhost:5000")
    print("  2. 选择 'Nunchaku Flux.1 Dev' 工作流")
    print("  3. 点击 '开始配置' 按钮")
    print("  4. 观察以下变化:")
    print("     - Negative Prompt 输入框已隐藏")
    print("     - 点击 '模型加载器' 导航选项")
    print("     - 查看模型加载器配置界面")
    
    print("\n🎯 新功能亮点:")
    print("  ✅ 自适应Negative Prompt显示")
    print("  ✅ 完整的模型加载器参数配置")
    print("  ✅ 响应式设计，支持移动端")
    print("  ✅ 实时参数验证和错误提示")

def main():
    """主演示函数"""
    print_header("ComfyUI Web Service 新功能演示")
    
    print("🚀 开始演示新功能...")
    
    # 检查服务状态
    try:
        response = requests.get("http://localhost:5000/api/workflows", timeout=5)
        if response.status_code != 200:
            print("❌ 服务未正常运行，请先启动服务")
            return
    except Exception as e:
        print(f"❌ 无法连接到服务: {e}")
        print("请确保服务正在运行: python app.py")
        return
    
    # 运行演示
    demo_workflow_analysis()
    demo_negative_prompt_detection()
    demo_model_loaders()
    demo_web_interface()
    
    print_header("演示完成")
    print("🎉 新功能演示完成！")
    print("💡 请访问Web界面体验完整功能")

if __name__ == "__main__":
    main() 