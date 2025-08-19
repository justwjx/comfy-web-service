#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import os

def convert_ui_workflow_to_api_format(ui_wf: dict, object_info: dict) -> dict:
    """使用你提供的原始转换逻辑"""
    api_prompt = {}
    nodes_by_id = {str(n['id']): n for n in ui_wf.get('nodes', [])}
    primitive_values = {nid: n['widgets_values'][0] for nid, n in nodes_by_id.items() if n.get('type') == 'PrimitiveNode' and n.get('widgets_values')}
    NODE_TYPES_TO_IGNORE = ["PrimitiveNode", "Note", "MarkdownNote"]

    for node_id, node in nodes_by_id.items():
        if node.get('type') in NODE_TYPES_TO_IGNORE: continue
        node_type = node.get('type')
        api_node = {"class_type": node_type, "inputs": {}}
        
        if node_type in object_info and 'inputs' in object_info[node_type]:
            for category in ['required', 'optional']:
                for name, props in object_info[node_type]['input'].get(category, {}).items():
                    if isinstance(props, list) and len(props) > 1 and 'default' in props[1]:
                        api_node['inputs'][name] = props[1]['default']
        
        if node_type in WIDGET_INDEX_MAP and 'widgets_values' in node:
            for w_name, w_idx in WIDGET_INDEX_MAP[node_type].items():
                if w_idx >= 0 and len(node['widgets_values']) > w_idx:
                    value = node['widgets_values'][w_idx]
                    # 清理模型名称中的状态标记
                    if isinstance(value, str):
                        # 移除 "✅" 和 "❌ (文件不存在)" 标记
                        cleaned_value = value.replace(' ✅', '').replace(' ❌ (文件不存在)', '')
                        api_node['inputs'][w_name] = cleaned_value
                    else:
                        api_node['inputs'][w_name] = value
        
        if 'inputs' in node:
            for i, input_data in enumerate(node['inputs']):
                if input_data.get('link') is not None:
                    for link in ui_wf.get('links', []):
                        if str(link[3]) == node_id and link[4] == i:
                            src_id, src_slot, in_name = str(link[1]), link[2], input_data['name']
                            api_node['inputs'][in_name] = primitive_values.get(src_id, [src_id, src_slot])
                            break
        api_prompt[node_id] = api_node
    return api_prompt

# 简化的WIDGET_INDEX_MAP
WIDGET_INDEX_MAP = {
    "CLIPTextEncode": {"text": 0},
    "LoadImage": {"image": 0},
    "LoadImageOutput": {"image": 0},
    "SaveImage": {"filename_prefix": 0},
    "KSampler": {"seed": 0, "steps": 2, "cfg": 3, "sampler_name": 4, "scheduler": 5, "denoise": 6},
    "KSamplerAdvanced": {"add_noise":0, "noise_seed": 1, "steps": 3, "cfg": 4, "sampler_name": 5, "scheduler": 6},
    "KSamplerSelect": {"sampler_name": 0},
    "EmptyLatentImage": {"width": 0, "height": 1, "batch_size": 2},
    "EmptySD3LatentImage": {"width": 0, "height": 1, "batch_size": 2},
    "NunchakuFluxDiTLoader": {"model_path": 0, "cache_threshold": 1, "attention": 2, "cpu_offload": 3, "device_id": 4, "data_type": 5, "i_2_f_mode": 6},
    "CheckpointLoaderSimple": {"ckpt_name": 0},
    "VAELoader": {"vae_name": 0},
    "LoraLoader": {"lora_name": 0, "strength_model": 1},
    "NunchakuFluxLoraLoader": {"lora_name": 0, "lora_strength": 1},
    "NunchakuTextEncoderLoader": {"model_type": 0, "text_encoder1": 1, "text_encoder2": 2, "t5_min_length": 3, "use_4bit_t5": 4, "int4_model": 5},
    "ControlNetApplyAdvanced": {"strength": 0},
    "ControlNetLoader": {"control_net_name": 0},
    "DepthAnythingPreprocessor": {"resolution": 1},
    "BasicScheduler": {"scheduler": 0, "steps": 1, "denoise": 2},
    "FluxGuidance": {"guidance": 0},
    "ModelSamplingFlux": {"max_shift": 0, "base_shift": 1, "width": 2, "height": 3},
    "RandomNoise": {"noise_seed": 0},
    "PrimitiveNode": {"value": 0},
    "ImageStitch": {"direction": 0, "match_image_size": 1, "spacing_width": 2, "spacing_color": 3, "image1": -1, "image2": -1},
    "DualCLIPLoader": {"clip_name1": 0, "clip_name2": 1, "type": 2},
}

if __name__ == "__main__":
    # 读取workflow文件
    workflow_file = "workflow/nunchaku-flux.1-dev.json"
    with open(workflow_file, 'r', encoding='utf-8') as f:
        workflow_data = json.load(f)
    
    print("使用原始转换逻辑...")
    
    # 模拟object_info（简化版）
    object_info = {}
    
    api_workflow = convert_ui_workflow_to_api_format(workflow_data, object_info)
    
    if api_workflow:
        print(f"\n转换成功！包含 {len(api_workflow)} 个节点")
        
        # 检查节点8
        if '8' in api_workflow:
            print(f"节点8存在: {api_workflow['8']}")
        else:
            print("节点8不存在!")
        
        # 检查SaveImage节点
        save_image_nodes = [node_id for node_id, node_data in api_workflow.items() 
                           if node_data.get('class_type') == 'SaveImage']
        print(f"SaveImage节点: {save_image_nodes}")
        for node_id in save_image_nodes:
            node_data = api_workflow[node_id]
            print(f"  SaveImage {node_id}: {node_data}")
            if 'images' in node_data.get('inputs', {}):
                images_value = node_data['inputs']['images']
                print(f"    images参数: {images_value} (类型: {type(images_value)})")
    else:
        print("转换失败！") 