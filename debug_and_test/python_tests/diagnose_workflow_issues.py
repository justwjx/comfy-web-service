#!/usr/bin/env python3
"""
诊断工作流执行问题
"""

import json
import requests
import time
import os

def check_comfyui_status():
    """检查ComfyUI状态"""
    print("🔍 检查ComfyUI状态...")
    
    try:
        response = requests.get("http://localhost:5000/api/comfyui/status")
        if response.status_code == 200:
            data = response.json()
            if data.get('success') and data.get('connected'):
                print("✅ ComfyUI连接正常")
                system_info = data.get('system_info', {})
                print(f"   - ComfyUI版本: {system_info.get('comfyui_version', 'unknown')}")
                print(f"   - Python版本: {system_info.get('python_version', 'unknown')}")
                print(f"   - PyTorch版本: {system_info.get('pytorch_version', 'unknown')}")
                return True
            else:
                print("❌ ComfyUI连接失败")
                return False
        else:
            print(f"❌ 无法获取ComfyUI状态: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ 检查ComfyUI状态时出错: {e}")
        return False

def check_workflow_file():
    """检查工作流文件"""
    print("\n📁 检查工作流文件...")
    
    workflow_file = "../workflow/nunchaku-flux.1-kontext-dev.json"
    if os.path.exists(workflow_file):
        print(f"✅ 工作流文件存在: {workflow_file}")
        
        try:
            with open(workflow_file, 'r', encoding='utf-8') as f:
                workflow_data = json.load(f)
            
            nodes = workflow_data.get('nodes', [])
            print(f"   - 节点数量: {len(nodes)}")
            
            # 检查关键节点
            load_image_nodes = [n for n in nodes if n.get('type') == 'LoadImageOutput']
            image_stitch_nodes = [n for n in nodes if n.get('type') == 'ImageStitch']
            
            print(f"   - LoadImageOutput节点: {len(load_image_nodes)}")
            print(f"   - ImageStitch节点: {len(image_stitch_nodes)}")
            
            return True
        except Exception as e:
            print(f"❌ 读取工作流文件时出错: {e}")
            return False
    else:
        print(f"❌ 工作流文件不存在: {workflow_file}")
        return False

def check_image_files():
    """检查图像文件"""
    print("\n🖼️  检查图像文件...")
    
    uploaded_dir = "../outputs/uploaded"
    if os.path.exists(uploaded_dir):
        files = os.listdir(uploaded_dir)
        image_files = [f for f in files if f.lower().endswith(('.png', '.jpg', '.jpeg', '.webp'))]
        
        print(f"✅ 上传目录存在: {uploaded_dir}")
        print(f"   - 图像文件数量: {len(image_files)}")
        
        for img_file in image_files[:5]:  # 显示前5个文件
            file_path = os.path.join(uploaded_dir, img_file)
            file_size = os.path.getsize(file_path)
            print(f"   - {img_file} ({file_size} bytes)")
        
        return len(image_files) > 0
    else:
        print(f"❌ 上传目录不存在: {uploaded_dir}")
        return False

def test_workflow_analysis():
    """测试工作流分析"""
    print("\n🔍 测试工作流分析...")
    
    try:
        response = requests.get("http://localhost:5000/api/analyze-workflow/nunchaku-flux.1-kontext-dev.json")
        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                analysis = data.get('analysis', {})
                image_inputs = analysis.get('image_inputs', [])
                
                print(f"✅ 工作流分析成功")
                print(f"   - 图像输入节点: {len(image_inputs)}")
                
                for input_node in image_inputs:
                    node_id = input_node.get('node_id')
                    name = input_node.get('name')
                    required = input_node.get('required')
                    status = "必需" if required else "可选"
                    print(f"   - 节点{node_id}: {name} ({status})")
                
                return True
            else:
                print("❌ 工作流分析失败")
                return False
        else:
            print(f"❌ 工作流分析请求失败: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ 工作流分析测试出错: {e}")
        return False

def test_simple_workflow_execution():
    """测试简单的工作流执行"""
    print("\n🧪 测试简单的工作流执行...")
    
    # 使用最简单的测试数据
    test_data = {
        "filename": "nunchaku-flux.1-kontext-dev.json",
        "parameters": {
            "positive_prompt": "a simple test"
        },
        "selected_images": {}
    }
    
    try:
        print("📤 发送工作流执行请求...")
        response = requests.post("http://localhost:5000/api/run", json=test_data, timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            print(f"📊 响应状态码: {response.status_code}")
            print(f"📊 响应内容: {json.dumps(result, indent=2, ensure_ascii=False)}")
            
            if result.get('success'):
                task_id = result.get('task_id')
                print(f"✅ 工作流执行请求成功，任务ID: {task_id}")
                
                # 检查任务状态
                time.sleep(2)
                status_response = requests.get(f"http://localhost:5000/api/status/{task_id}")
                if status_response.status_code == 200:
                    status_data = status_response.json()
                    print(f"📊 任务状态: {json.dumps(status_data, indent=2, ensure_ascii=False)}")
                    return True
                else:
                    print(f"❌ 获取任务状态失败: {status_response.status_code}")
                    return False
            else:
                print(f"❌ 工作流执行请求失败: {result.get('error', '未知错误')}")
                return False
        else:
            print(f"❌ HTTP请求失败: {response.status_code}")
            print(f"📊 响应内容: {response.text}")
            return False
    except Exception as e:
        print(f"❌ 测试过程中出错: {e}")
        return False

def check_comfyui_logs():
    """检查ComfyUI日志"""
    print("\n📋 检查ComfyUI日志...")
    
    # 这里可以添加检查ComfyUI日志的逻辑
    # 由于我们无法直接访问ComfyUI的日志，我们通过API来检查
    print("ℹ️  无法直接访问ComfyUI日志，但可以通过API状态检查")
    return True

def main():
    """主函数"""
    print("🚀 开始诊断工作流执行问题\n")
    
    # 运行诊断
    checks = [
        ("ComfyUI状态", check_comfyui_status),
        ("工作流文件", check_workflow_file),
        ("图像文件", check_image_files),
        ("工作流分析", test_workflow_analysis),
        ("简单工作流执行", test_simple_workflow_execution),
        ("ComfyUI日志", check_comfyui_logs)
    ]
    
    results = []
    for check_name, check_func in checks:
        try:
            result = check_func()
            results.append((check_name, result))
        except Exception as e:
            print(f"❌ {check_name}检查时出错: {e}")
            results.append((check_name, False))
    
    print("\n" + "="*50)
    print("📋 诊断总结:")
    
    all_passed = True
    for check_name, result in results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"   {check_name}: {status}")
        if not result:
            all_passed = False
    
    print("\n" + "="*50)
    if all_passed:
        print("🎉 所有检查通过！工作流应该能正常执行")
    else:
        print("❌ 发现问题，需要进一步排查")
        print("\n💡 建议:")
        print("   1. 检查ComfyUI是否正在运行")
        print("   2. 检查工作流文件是否完整")
        print("   3. 检查图像文件是否存在")
        print("   4. 检查网络连接")
        print("   5. 查看ComfyUI的错误日志")

if __name__ == "__main__":
    main() 