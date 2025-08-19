#!/usr/bin/env python3
"""
独立的工作流默认值测试脚本
不依赖Flask模块，直接测试默认值提取逻辑
"""

import os
import json
import sys

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
            'steps': 20,
            'cfg': 1.0,  # 默认值，会被JSON文件中的实际值覆盖
            'seed': -1,
            'sampler': 'euler',
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
        
        # 检查文生图
        if 'KSampler' in node_type:
            analysis['has_text_to_image'] = True
            analysis['type'] = 'text-to-image'
            
            # 提取默认参数 - UI格式中参数在widgets_values中
            # UI格式KSampler: [seed, seed_mode, steps, cfg, sampler, scheduler, denoise]
            widgets_values = node.get('widgets_values', [])
            if widgets_values and len(widgets_values) >= 7:
                # 安全转换数值
                try:
                    analysis['default_values']['seed'] = int(widgets_values[0]) if widgets_values[0] is not None and str(widgets_values[0]).replace('-', '').isdigit() else -1
                except (ValueError, TypeError):
                    analysis['default_values']['seed'] = -1
                
                try:
                    analysis['default_values']['steps'] = int(widgets_values[2]) if widgets_values[2] is not None and str(widgets_values[2]).isdigit() else 20
                except (ValueError, TypeError):
                    analysis['default_values']['steps'] = 20
                
                try:
                    analysis['default_values']['cfg'] = float(widgets_values[3]) if widgets_values[3] is not None and str(widgets_values[3]).replace('.', '').replace('-', '').isdigit() else 1.0
                except (ValueError, TypeError):
                    analysis['default_values']['cfg'] = 1.0
                
                analysis['default_values']['sampler'] = str(widgets_values[4]) if widgets_values[4] is not None else 'euler'
                analysis['default_values']['scheduler'] = str(widgets_values[5]) if widgets_values[5] is not None else 'normal'
        
        # 检查KSamplerSelect（Nunchaku Flux.1使用）
        elif 'KSamplerSelect' in node_type:
            analysis['has_text_to_image'] = True
            analysis['type'] = 'text-to-image'
            
            # KSamplerSelect只有sampler_name参数
            widgets_values = node.get('widgets_values', [])
            if widgets_values and len(widgets_values) >= 1:
                analysis['default_values']['sampler'] = str(widgets_values[0]) if widgets_values[0] is not None else 'euler'
        
        # 检查CheckpointLoader
        elif 'CheckpointLoader' in node_type:
            analysis['has_text_to_image'] = True
            analysis['type'] = 'text-to-image'
        
        # 检查图生图
        elif 'LoadImage' in node_type or 'ImageLoader' in node_type:
            analysis['has_image_to_image'] = True
            if not analysis['has_text_to_image']:
                analysis['type'] = 'image-to-image'
            
            analysis['image_inputs'].append({
                'node_id': node_id,
                'type': 'image',
                'required': True,
                'name': '输入图像',
                'description': '选择要处理的图像'
            })
        
        # 检查ControlNet
        elif 'ControlNet' in node_type:
            analysis['has_controlnet'] = True
            analysis['type'] = 'controlnet'
            
            analysis['image_inputs'].append({
                'node_id': node_id,
                'type': 'controlnet',
                'required': True,
                'name': 'ControlNet图像',
                'description': '选择ControlNet控制图像'
            })
        
        # 检查修复
        elif 'Inpaint' in node_type:
            analysis['has_inpaint'] = True
            analysis['type'] = 'inpaint'
            
            analysis['image_inputs'].append({
                'node_id': node_id,
                'type': 'inpaint',
                'required': True,
                'name': '修复图像',
                'description': '选择要修复的图像'
            })
        
        # 检查超分辨率
        elif 'Upscale' in node_type or 'Upscaler' in node_type:
            analysis['has_upscaler'] = True
        
        # 检查BasicScheduler节点获取steps和scheduler
        elif 'BasicScheduler' in node_type:
            widgets_values = node.get('widgets_values', [])
            if len(widgets_values) >= 3:
                analysis['default_values']['scheduler'] = str(widgets_values[0]) if widgets_values[0] is not None else 'simple'
                try:
                    analysis['default_values']['steps'] = int(widgets_values[1]) if widgets_values[1] is not None and str(widgets_values[1]).isdigit() else 20
                except (ValueError, TypeError):
                    analysis['default_values']['steps'] = 20
        
        # 检查FluxGuidance节点获取cfg值
        elif 'FluxGuidance' in node_type:
            widgets_values = node.get('widgets_values', [])
            if len(widgets_values) >= 1:
                try:
                    analysis['default_values']['cfg'] = float(widgets_values[0]) if widgets_values[0] is not None and str(widgets_values[0]).replace('.', '').replace('-', '').isdigit() else 2.5
                except (ValueError, TypeError):
                    analysis['default_values']['cfg'] = 2.5
        
        # 检查EmptyLatentImage节点获取默认尺寸
        elif 'EmptyLatentImage' in node_type:
            widgets_values = node.get('widgets_values', [])
            if len(widgets_values) >= 2:
                try:
                    analysis['default_values']['width'] = int(widgets_values[0]) if widgets_values[0] is not None and str(widgets_values[0]).isdigit() else 1024
                except (ValueError, TypeError):
                    analysis['default_values']['width'] = 1024
                
                try:
                    analysis['default_values']['height'] = int(widgets_values[1]) if widgets_values[1] is not None and str(widgets_values[1]).isdigit() else 1024
                except (ValueError, TypeError):
                    analysis['default_values']['height'] = 1024
        
        # 检查EmptySD3LatentImage节点获取默认尺寸（Nunchaku Flux.1使用）
        elif 'EmptySD3LatentImage' in node_type:
            widgets_values = node.get('widgets_values', [])
            if len(widgets_values) >= 2:
                try:
                    analysis['default_values']['width'] = int(widgets_values[0]) if widgets_values[0] is not None and str(widgets_values[0]).isdigit() else 1024
                except (ValueError, TypeError):
                    analysis['default_values']['width'] = 1024
                
                try:
                    analysis['default_values']['height'] = int(widgets_values[1]) if widgets_values[1] is not None and str(widgets_values[1]).isdigit() else 1024
                except (ValueError, TypeError):
                    analysis['default_values']['height'] = 1024
        
        # 检查PrimitiveNode节点获取尺寸（Nunchaku Flux.1使用）
        elif 'PrimitiveNode' in node_type:
            node_title = node.get('title', '').lower()
            widgets_values = node.get('widgets_values', [])
            
            if node_title == 'width' and len(widgets_values) >= 1:
                try:
                    analysis['default_values']['width'] = int(widgets_values[0]) if widgets_values[0] is not None and str(widgets_values[0]).isdigit() else 1024
                except (ValueError, TypeError):
                    analysis['default_values']['width'] = 1024
            
            elif node_title == 'height' and len(widgets_values) >= 1:
                try:
                    analysis['default_values']['height'] = int(widgets_values[0]) if widgets_values[0] is not None and str(widgets_values[0]).isdigit() else 1024
                except (ValueError, TypeError):
                    analysis['default_values']['height'] = 1024
        
        # 检查CLIPTextEncode节点获取默认提示词
        elif 'CLIPTextEncode' in node_type:
            # 检查是否有默认文本 - UI格式中文本在widgets_values中
            widgets_values = node.get('widgets_values', [])
            if widgets_values and len(widgets_values) > 0:
                text_value = widgets_values[0]
                if isinstance(text_value, str) and text_value.strip():
                    # 根据节点标题判断是正面还是负面提示词
                    node_title = node.get('title', '').lower()
                    if 'negative' in node_title or 'neg' in node_title:
                        analysis['default_values']['negative_prompt'] = text_value
                        analysis['has_negative_prompt'] = True
                    else:
                        analysis['default_values']['positive_prompt'] = text_value
    
    # 根据分析结果确定需要的参数
    if analysis['has_text_to_image']:
        analysis['required_inputs'].append('positive_prompt')
        analysis['optional_inputs'].extend(['negative_prompt', 'width', 'height', 'steps', 'cfg', 'seed', 'sampler'])
    
    return analysis

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
            width = defaults.get('width')
            height = defaults.get('height')
            if width == 1024 and height == 1024:
                print("✅ 尺寸参数: 1024x1024 (标准尺寸)")
            elif width == 512 and height == 512:
                print("⚠️  尺寸参数: 512x512 (可能是旧版本)")
            elif width and height and 256 <= width <= 2048 and 256 <= height <= 2048:
                print(f"✅ 尺寸参数: {width}x{height} (合理范围)")
            else:
                print(f"❌ 尺寸参数: {width}x{height} (需要检查)")
                issues.append("尺寸参数异常")
            
            # 检查CFG参数
            cfg = defaults.get('cfg')
            if cfg and 0.1 <= cfg <= 50.0:  # 扩大CFG的合理范围
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