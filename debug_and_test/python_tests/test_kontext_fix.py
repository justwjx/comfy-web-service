#!/usr/bin/env python3
import json
import sys
import os

# 添加当前目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

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
            'width': 1024,
            'height': 1024,
            'steps': 20,
            'cfg': 1.0,
            'seed': -1,
            'sampler': 'euler',
            'positive_prompt': '',
            'negative_prompt': ''
        },
        'required_inputs': [],
        'optional_inputs': [],
        'model_loaders': [],
        'controlnet_configs': [],
        'has_negative_prompt': False
    }
    
    for node in nodes:
        node_type = node.get('type', '')
        node_id = node.get('id')
        
        # 检查LoadImageOutput（Kontext工作流中的图像输入）
        if 'LoadImageOutput' in node_type:
            analysis['has_image_to_image'] = True
            if not analysis['has_text_to_image']:
                analysis['type'] = 'image-to-image'
            
            # 检查是否有默认图像值
            widgets_values = node.get('widgets_values', [])
            has_default_image = False
            if widgets_values and len(widgets_values) > 0:
                default_image = widgets_values[0]
                print(f"LoadImageOutput 节点 {node_id} 默认图像值: '{default_image}'")
                # 如果默认图像不是空的，且不是占位符，则认为这个输入是可选的
                if (isinstance(default_image, str) and 
                    default_image.strip() and 
                    not default_image.startswith('Choose') and
                    not default_image.startswith('Select') and
                    not default_image.startswith('No image') and
                    default_image != '' and
                    '[' in default_image):  # 包含方括号的通常是默认图像文件名
                    has_default_image = True
                    print(f"LoadImageOutput 节点 {node_id} 识别为可选输入")
            
            # 对于Kontext工作流，需要分析连接到ImageStitch的顺序
            # 第一个连接到ImageStitch的image1输入的LoadImageOutput节点是必须的
            # 第二个连接到image2的是可选的
            existing_image_inputs = [n for n in analysis['image_inputs'] if n.get('type') == 'image']
            
            # 检查这个节点是否连接到ImageStitch的image1输入
            is_first_input = False
            if len(existing_image_inputs) == 0:
                # 第一个LoadImageOutput节点，检查它是否连接到ImageStitch的image1
                links = workflow_data.get('links', [])
                for link in links:
                    if len(link) >= 6 and link[1] == node_id and link[4] == 0:  # 连接到image1输入
                        is_first_input = True
                        break
            
            # 检查默认图像是否是示例图像
            is_example_image = False
            if has_default_image and widgets_values and len(widgets_values) > 0:
                default_image = widgets_values[0]
                # 如果默认图像文件名包含示例相关的关键词，认为是示例图像
                if any(keyword in default_image.lower() for keyword in ['example', 'demo', 'sample', 'test', 'pikachu', 'yarn']):
                    is_example_image = True
                    print(f"LoadImageOutput 节点 {node_id} 识别为示例图像")
            
            # 确定是否可选
            # 如果有默认图像且是示例图像，则这个输入是可选的
            # 如果是第一个输入且不是示例图像，则这个输入是必须的
            is_optional = (has_default_image and is_example_image) or len(existing_image_inputs) > 0
            if is_first_input and not is_example_image:
                is_optional = False
            
            analysis['image_inputs'].append({
                'node_id': node_id,
                'type': 'image',
                'required': not is_optional,  # 如果有默认图像或是第二个图像，则不是必需的
                'name': f'输入图像 {len(existing_image_inputs) + 1}',
                'description': f'选择要处理的图像{" (可选)" if is_optional else " (必需)"}'
            })
    
    return analysis

def test_kontext_workflow():
    """测试Kontext工作流的图像输入分析"""
    try:
        # 加载工作流文件
        with open('workflow/nunchaku-flux.1-kontext-dev.json', 'r', encoding='utf-8') as f:
            workflow_data = json.load(f)
        
        # 分析工作流结构
        analysis = analyze_workflow_structure(workflow_data)
        
        print("=== Kontext工作流图像输入分析 ===")
        print(f"工作流类型: {analysis['type']}")
        print(f"图像输入数量: {len(analysis['image_inputs'])}")
        print()
        
        for i, inp in enumerate(analysis['image_inputs'], 1):
            print(f"图像输入 {i}:")
            print(f"  节点ID: {inp['node_id']}")
            print(f"  名称: {inp['name']}")
            print(f"  类型: {inp['type']}")
            print(f"  必需: {inp['required']}")
            print(f"  描述: {inp['description']}")
            print()
        
        # 验证结果
        if len(analysis['image_inputs']) == 2:
            first_input = analysis['image_inputs'][0]
            second_input = analysis['image_inputs'][1]
            
            print("=== 验证结果 ===")
            if first_input['required'] and not second_input['required']:
                print("✅ 修复成功: 第一个图像输入是必需的，第二个是可选的")
            else:
                print("❌ 修复失败: 图像输入的必需性设置不正确")
                print(f"   第一个输入必需: {first_input['required']}")
                print(f"   第二个输入必需: {second_input['required']}")
        else:
            print(f"❌ 预期有2个图像输入，实际有{len(analysis['image_inputs'])}个")
            
    except Exception as e:
        print(f"测试失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_kontext_workflow() 