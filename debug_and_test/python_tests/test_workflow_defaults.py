#!/usr/bin/env python3
"""
测试工作流默认值提取
验证所有工作流的基础参数默认值是否正确从JSON文件中提取
"""

import os
import json
import sys

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import analyze_workflow_structure

def test_workflow_defaults():
    """测试所有工作流的默认值提取"""
    workflow_dir = "workflow"
    
    if not os.path.exists(workflow_dir):
        print(f"错误: 工作流目录不存在: {workflow_dir}")
        return
    
    workflow_files = [f for f in os.listdir(workflow_dir) if f.endswith('.json')]
    
    print("=" * 80)
    print("工作流默认值测试报告")
    print("=" * 80)
    
    all_passed = True
    
    for workflow_file in sorted(workflow_files):
        print(f"\n📁 测试工作流: {workflow_file}")
        print("-" * 60)
        
        try:
            # 读取工作流文件
            with open(os.path.join(workflow_dir, workflow_file), 'r', encoding='utf-8') as f:
                workflow_data = json.load(f)
            
            # 分析工作流
            analysis = analyze_workflow_structure(workflow_data)
            
            # 显示提取的默认值
            defaults = analysis.get('default_values', {})
            print(f"✅ 提取的默认值:")
            print(f"   宽度: {defaults.get('width', 'N/A')}")
            print(f"   高度: {defaults.get('height', 'N/A')}")
            print(f"   步数: {defaults.get('steps', 'N/A')}")
            print(f"   CFG: {defaults.get('cfg', 'N/A')}")
            print(f"   种子: {defaults.get('seed', 'N/A')}")
            print(f"   采样器: {defaults.get('sampler', 'N/A')}")
            print(f"   正面提示词: {defaults.get('positive_prompt', 'N/A')[:50]}...")
            print(f"   负面提示词: {defaults.get('negative_prompt', 'N/A')[:50]}...")
            
            # 验证关键参数
            issues = []
            
            # 检查尺寸参数
            if defaults.get('width') == 1024 and defaults.get('height') == 1024:
                print("✅ 尺寸参数: 1024x1024 (符合预期)")
            elif defaults.get('width') == 512 and defaults.get('height') == 512:
                print("⚠️  尺寸参数: 512x512 (可能是旧版本)")
            else:
                print(f"❌ 尺寸参数: {defaults.get('width')}x{defaults.get('height')} (需要检查)")
                issues.append("尺寸参数异常")
            
            # 检查CFG参数
            cfg = defaults.get('cfg')
            if cfg == 1.0 or cfg == 2.5 or cfg == 7.0:
                print(f"✅ CFG参数: {cfg} (合理范围)")
            else:
                print(f"❌ CFG参数: {cfg} (需要检查)")
                issues.append("CFG参数异常")
            
            # 检查步数参数
            steps = defaults.get('steps')
            if steps and 1 <= steps <= 100:
                print(f"✅ 步数参数: {steps} (合理范围)")
            else:
                print(f"❌ 步数参数: {steps} (需要检查)")
                issues.append("步数参数异常")
            
            # 检查是否有图像输入
            image_inputs = analysis.get('image_inputs', [])
            if image_inputs:
                print(f"✅ 图像输入: {len(image_inputs)} 个")
                for img_input in image_inputs:
                    print(f"   - {img_input.get('name', 'Unknown')} ({img_input.get('type', 'Unknown')})")
            else:
                print("ℹ️  图像输入: 无")
            
            # 检查模型加载器
            model_loaders = analysis.get('model_loaders', [])
            if model_loaders:
                print(f"✅ 模型加载器: {len(model_loaders)} 个")
                for loader in model_loaders:
                    print(f"   - {loader.get('name', 'Unknown')} ({loader.get('type', 'Unknown')})")
            else:
                print("ℹ️  模型加载器: 无")
            
            if issues:
                print(f"❌ 发现问题: {', '.join(issues)}")
                all_passed = False
            else:
                print("✅ 所有参数正常")
                
        except Exception as e:
            print(f"❌ 测试失败: {e}")
            all_passed = False
    
    print("\n" + "=" * 80)
    if all_passed:
        print("🎉 所有工作流测试通过!")
    else:
        print("⚠️  部分工作流存在问题，请检查上述报告")
    print("=" * 80)

def test_specific_workflow(workflow_name):
    """测试特定工作流"""
    workflow_path = os.path.join("workflow", workflow_name)
    
    if not os.path.exists(workflow_path):
        print(f"错误: 工作流文件不存在: {workflow_path}")
        return
    
    print(f"🔍 详细测试工作流: {workflow_name}")
    print("=" * 60)
    
    try:
        with open(workflow_path, 'r', encoding='utf-8') as f:
            workflow_data = json.load(f)
        
        # 查找相关节点
        nodes = workflow_data.get('nodes', [])
        
        print("📋 节点分析:")
        
        # 查找尺寸相关节点
        size_nodes = []
        for node in nodes:
            node_type = node.get('type', '')
            if 'EmptyLatentImage' in node_type or 'EmptySD3LatentImage' in node_type or 'PrimitiveNode' in node_type:
                size_nodes.append(node)
        
        if size_nodes:
            print(f"✅ 找到 {len(size_nodes)} 个尺寸相关节点:")
            for node in size_nodes:
                node_type = node.get('type', '')
                node_id = node.get('id', '')
                widgets_values = node.get('widgets_values', [])
                title = node.get('title', '')
                
                print(f"   - 节点ID: {node_id}")
                print(f"     类型: {node_type}")
                if title:
                    print(f"     标题: {title}")
                print(f"     参数值: {widgets_values}")
        else:
            print("❌ 未找到尺寸相关节点")
        
        # 查找KSampler节点
        sampler_nodes = []
        for node in nodes:
            node_type = node.get('type', '')
            if 'KSampler' in node_type:
                sampler_nodes.append(node)
        
        if sampler_nodes:
            print(f"\n✅ 找到 {len(sampler_nodes)} 个采样器节点:")
            for node in sampler_nodes:
                node_id = node.get('id', '')
                widgets_values = node.get('widgets_values', [])
                
                print(f"   - 节点ID: {node_id}")
                print(f"     参数值: {widgets_values}")
                if len(widgets_values) >= 7:
                    print(f"     种子: {widgets_values[0]}")
                    print(f"     步数: {widgets_values[2]}")
                    print(f"     CFG: {widgets_values[3]}")
                    print(f"     采样器: {widgets_values[4]}")
        else:
            print("\n❌ 未找到采样器节点")
        
        # 分析工作流
        analysis = analyze_workflow_structure(workflow_data)
        defaults = analysis.get('default_values', {})
        
        print(f"\n📊 提取的默认值:")
        print(f"   宽度: {defaults.get('width', 'N/A')}")
        print(f"   高度: {defaults.get('height', 'N/A')}")
        print(f"   步数: {defaults.get('steps', 'N/A')}")
        print(f"   CFG: {defaults.get('cfg', 'N/A')}")
        print(f"   种子: {defaults.get('seed', 'N/A')}")
        print(f"   采样器: {defaults.get('sampler', 'N/A')}")
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        # 测试特定工作流
        workflow_name = sys.argv[1]
        test_specific_workflow(workflow_name)
    else:
        # 测试所有工作流
        test_workflow_defaults() 