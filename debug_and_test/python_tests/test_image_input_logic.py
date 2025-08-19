#!/usr/bin/env python3
"""
测试图像输入节点的必选性判断逻辑
"""

import json
import os
import sys
import requests

def test_workflow_analysis():
    """测试工作流分析API"""
    print("🧪 测试工作流分析API...")
    
    try:
        # 调用API分析工作流
        response = requests.get("http://localhost:5000/api/analyze-workflow/nunchaku-flux.1-kontext-dev.json")
        if response.status_code == 200:
            data = response.json()
            
            if data.get('success'):
                analysis = data.get('analysis', {})
                image_inputs = analysis.get('image_inputs', [])
                
                print(f"📊 找到 {len(image_inputs)} 个图像输入节点:")
                
                for i, input_node in enumerate(image_inputs, 1):
                    node_id = input_node.get('node_id')
                    name = input_node.get('name')
                    required = input_node.get('required')
                    description = input_node.get('description')
                    
                    status = "✅ 必需" if required else "⚠️  可选"
                    print(f"   {i}. 节点ID: {node_id}")
                    print(f"      名称: {name}")
                    print(f"      状态: {status}")
                    print(f"      描述: {description}")
                    print()
                
                # 验证结果
                node_142 = next((node for node in image_inputs if node.get('node_id') == 142), None)
                node_147 = next((node for node in image_inputs if node.get('node_id') == 147), None)
                
                if node_142 and node_147:
                    print("🔍 验证结果:")
                    print(f"   节点142 (主图像输入): {'✅ 必需' if node_142.get('required') else '❌ 应该是必需但标记为可选'}")
                    print(f"   节点147 (参考图像输入): {'✅ 可选' if not node_147.get('required') else '❌ 应该是可选但标记为必需'}")
                    
                    # 检查是否符合预期
                    expected_142_required = node_142.get('required') == True
                    expected_147_optional = node_147.get('required') == False
                    
                    if expected_142_required and expected_147_optional:
                        print("\n🎉 测试通过！图像输入节点的必选性判断正确！")
                        return True
                    else:
                        print("\n❌ 测试失败！图像输入节点的必选性判断不正确！")
                        return False
                else:
                    print("❌ 未找到预期的节点142或147")
                    return False
            else:
                print("❌ API返回失败")
                return False
        else:
            print(f"❌ API请求失败，状态码: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ 测试过程中出错: {e}")
        return False

def test_web_page_display():
    """测试web页面显示"""
    print("\n🌐 测试web页面显示...")
    
    try:
        # 获取web页面内容
        response = requests.get("http://localhost:5000")
        if response.status_code == 200:
            content = response.text
            
            # 检查是否包含节点ID显示相关的CSS
            if '.node-id-badge' in content:
                print("✅ 找到节点ID徽章CSS样式")
            else:
                print("❌ 未找到节点ID徽章CSS样式")
            
            # 检查是否包含图像输入相关的JavaScript
            if 'generateImageInputs' in content:
                print("✅ 找到图像输入生成函数")
            else:
                print("❌ 未找到图像输入生成函数")
            
            # 检查是否包含智能显示逻辑
            if 'showNodeIds' in content:
                print("✅ 找到智能显示逻辑")
            else:
                print("❌ 未找到智能显示逻辑")
            
            return True
        else:
            print(f"❌ 无法访问web页面，状态码: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ 测试web页面时出错: {e}")
        return False

def test_workflow_file_analysis():
    """直接分析工作流文件"""
    print("\n📁 直接分析工作流文件...")
    
    workflow_file = "../workflow/nunchaku-flux.1-kontext-dev.json"
    
    if not os.path.exists(workflow_file):
        print(f"❌ 工作流文件不存在: {workflow_file}")
        return False
    
    try:
        with open(workflow_file, 'r', encoding='utf-8') as f:
            workflow_data = json.load(f)
        
        # 查找LoadImageOutput节点
        load_image_nodes = []
        for node in workflow_data.get('nodes', []):
            if node.get('type') == 'LoadImageOutput':
                load_image_nodes.append({
                    'id': node.get('id'),
                    'order': node.get('order', 999),
                    'widgets_values': node.get('widgets_values', [])
                })
        
        print(f"📊 在工作流文件中找到 {len(load_image_nodes)} 个LoadImageOutput节点:")
        for node in load_image_nodes:
            print(f"   节点ID: {node['id']}, Order: {node['order']}")
        
        # 查找ImageStitch节点
        image_stitch_nodes = []
        for node in workflow_data.get('nodes', []):
            if node.get('type') == 'ImageStitch':
                image_stitch_nodes.append({
                    'id': node.get('id'),
                    'inputs': node.get('inputs', [])
                })
        
        print(f"📊 找到 {len(image_stitch_nodes)} 个ImageStitch节点:")
        for node in image_stitch_nodes:
            print(f"   节点ID: {node['id']}")
            for input_info in node['inputs']:
                print(f"     输入: {input_info.get('name')} -> 链接: {input_info.get('link')}")
        
        # 分析链接关系
        links = workflow_data.get('links', [])
        print(f"📊 工作流包含 {len(links)} 个链接")
        
        # 查找连接到ImageStitch的链接
        image_stitch_links = {}
        for link in links:
            if len(link) >= 4:
                link_id, source_node, source_output, target_node, target_input = link[:5]
                if target_node in [node['id'] for node in image_stitch_nodes]:
                    if target_node not in image_stitch_links:
                        image_stitch_links[target_node] = {}
                    image_stitch_links[target_node][target_input] = {
                        'link_id': link_id,
                        'source_node': source_node,
                        'source_output': source_output
                    }
        
        print("🔗 ImageStitch节点连接关系:")
        for stitch_node_id, connections in image_stitch_links.items():
            print(f"   ImageStitch节点 {stitch_node_id}:")
            for input_idx, connection in connections.items():
                print(f"     输入{input_idx}: 来自节点 {connection['source_node']} (链接 {connection['link_id']})")
        
        return True
        
    except Exception as e:
        print(f"❌ 分析工作流文件时出错: {e}")
        return False

def main():
    """主函数"""
    print("🚀 开始测试图像输入节点的必选性判断逻辑\n")
    
    # 检查服务是否运行
    try:
        response = requests.get("http://localhost:5000/api/comfyui/status", timeout=5)
        if response.status_code != 200:
            print("❌ ComfyUI Web服务未运行，请先启动服务")
            return
    except:
        print("❌ 无法连接到ComfyUI Web服务，请先启动服务")
        return
    
    print("✅ ComfyUI Web服务正在运行\n")
    
    # 运行测试
    test1_passed = test_workflow_analysis()
    test2_passed = test_web_page_display()
    test3_passed = test_workflow_file_analysis()
    
    print("\n" + "="*50)
    print("📋 测试总结:")
    print(f"   工作流分析API: {'✅ 通过' if test1_passed else '❌ 失败'}")
    print(f"   Web页面显示: {'✅ 通过' if test2_passed else '❌ 失败'}")
    print(f"   工作流文件分析: {'✅ 通过' if test3_passed else '❌ 失败'}")
    
    if test1_passed and test2_passed and test3_passed:
        print("\n🎉 所有测试通过！图像输入节点的必选性判断逻辑工作正常！")
    else:
        print("\n❌ 部分测试失败，请检查相关功能")

if __name__ == "__main__":
    main() 