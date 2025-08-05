#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ComfyUI工作流Web服务
移动端友好的workflow选择和执行界面
"""

import os
import json
import logging
import uuid
import requests
from datetime import datetime
from flask import Flask, render_template, jsonify, request, send_from_directory
from flask_cors import CORS
from werkzeug.utils import secure_filename
import threading
import queue
import time

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

# 配置
WORKFLOW_DIR = os.path.join(os.path.dirname(__file__), 'workflow')
COMFYUI_HOST = os.getenv('COMFYUI_HOST', 'localhost')
COMFYUI_PORT = int(os.getenv('COMFYUI_PORT', 8188))
COMFYUI_API_URL = f"http://{COMFYUI_HOST}:{COMFYUI_PORT}"
HOST = os.getenv('HOST', '0.0.0.0')
PORT = int(os.getenv('PORT', 5000))

# 全局变量存储运行状态
running_tasks = {}
task_queue = queue.Queue()

# WIDGET_INDEX_MAP - 节点类型到widget索引的映射
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

class WorkflowRunner:
    """工作流执行器"""
    
    def __init__(self):
        self.is_running = False
        
    def get_workflows(self):
        """获取所有可用的workflow"""
        workflows = []
        if not os.path.exists(WORKFLOW_DIR):
            logger.error(f"Workflow目录不存在: {WORKFLOW_DIR}")
            return workflows
            
        for filename in os.listdir(WORKFLOW_DIR):
            if filename.endswith('.json'):
                filepath = os.path.join(WORKFLOW_DIR, filename)
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        workflow_data = json.load(f)
                    
                    # 提取workflow信息
                    workflow_info = {
                        'filename': filename,
                        'name': filename.replace('.json', '').replace('-', ' ').title(),
                        'id': workflow_data.get('id', ''),
                        'revision': workflow_data.get('revision', 0),
                        'node_count': len(workflow_data.get('nodes', [])),
                        'description': self.get_workflow_description(filename),
                        'file_size': f"{os.path.getsize(filepath) / 1024:.1f} KB"
                    }
                    workflows.append(workflow_info)
                except Exception as e:
                    logger.error(f"读取workflow文件错误 {filename}: {str(e)}")
                    
        return sorted(workflows, key=lambda x: x['name'])
    
    def _extract_description(self, workflow_data):
        """从workflow数据中提取描述信息"""
        return "ComfyUI 工作流"  # 基础描述，会被 get_workflow_description 方法覆盖
    
    def get_workflow_description(self, filename):
        """根据文件名生成更有意义的描述"""
        filename_lower = filename.lower()
        
        # 基于文件名的描述映射
        if 'schnell' in filename_lower:
            return "🚀 FLUX.1 Schnell - 超快速图像生成模型，适合快速原型设计和预览"
        elif 'redux' in filename_lower:
            return "🎨 FLUX.1 Redux - 图像变换和风格迁移，将现有图像转换为新风格"
        elif 'kontext' in filename_lower and 'turbo' in filename_lower:
            return "⚡ FLUX.1 Kontext Turbo LoRA - 加速版上下文感知生成，支持LoRA微调"
        elif 'kontext' in filename_lower:
            return "🧠 FLUX.1 Kontext - 上下文感知的智能图像生成"
        elif 'fill' in filename_lower and 'removal' in filename_lower:
            return "🔧 FLUX.1 Fill + 智能移除 - 图像修复和不想要元素的智能移除"
        elif 'fill' in filename_lower:
            return "🖌️ FLUX.1 Fill - 智能图像修复和补全缺失区域"
        elif 'dev' in filename_lower and 'qencoder' in filename_lower:
            return "💻 FLUX.1 Dev + 量化编码器 - 开发版本，优化内存使用"
        elif 'dev' in filename_lower and 'pulid' in filename_lower:
            return "👤 FLUX.1 Dev + PuLID - 面部身份保持的图像生成"
        elif 'dev' in filename_lower and 'controlnet' in filename_lower and 'upscaler' in filename_lower:
            return "📈 FLUX.1 Dev + ControlNet 放大器 - 可控的高质量图像放大"
        elif 'dev' in filename_lower and 'controlnet' in filename_lower and 'union' in filename_lower:
            return "🎯 FLUX.1 Dev + ControlNet Union Pro - 多种控制条件的精确图像生成"
        elif 'dev' in filename_lower:
            return "🛠️ FLUX.1 Dev - 开发者版本，高质量图像生成的完整功能"
        elif 'depth' in filename_lower and 'lora' in filename_lower:
            return "🏔️ FLUX.1 深度 + LoRA - 基于深度图的3D感知图像生成"
        elif 'depth' in filename_lower:
            return "📐 FLUX.1 深度控制 - 使用深度图控制图像的3D结构"
        elif 'canny' in filename_lower and 'lora' in filename_lower:
            return "✏️ FLUX.1 边缘 + LoRA - 基于边缘检测的精确线条控制生成"
        elif 'canny' in filename_lower:
            return "🖍️ FLUX.1 边缘控制 - 使用Canny边缘检测控制图像轮廓"
        else:
            return "🤖 FLUX.1 工作流 - AI图像生成工作流"
    
    def check_comfyui_status(self):
        """检查ComfyUI服务状态"""
        try:
            response = requests.get(f"{COMFYUI_API_URL}/system_stats", timeout=5)
            return response.status_code == 200
        except Exception as e:
            logger.error(f"检查ComfyUI状态失败: {e}")
            return False
    
    def run_workflow(self, filename, task_id):
        """使用ComfyUI API运行workflow（原始方法，保持兼容性）"""
        return self.run_workflow_with_parameters(filename, task_id, {})
    
    def run_workflow_with_parameters(self, filename, task_id, parameters):
        """使用ComfyUI API运行workflow，支持参数修改"""
        return self.run_workflow_with_parameters_and_images(filename, task_id, parameters, {})
    
    def run_workflow_with_parameters_and_images(self, filename, task_id, parameters, selected_images):
        """使用ComfyUI API运行workflow，支持参数修改和图像输入"""
        filepath = os.path.join(WORKFLOW_DIR, filename)
        
        if not os.path.exists(filepath):
            return {'success': False, 'error': f'文件不存在: {filename}'}
        
        # 检查ComfyUI服务状态
        if not self.check_comfyui_status():
            return {'success': False, 'error': 'ComfyUI服务未运行或无法连接'}
        
        try:
            # 读取workflow文件
            with open(filepath, 'r', encoding='utf-8') as f:
                workflow_data = json.load(f)
            
            # 更新任务状态
            running_tasks[task_id] = {
                'status': 'running',
                'filename': filename,
                'workflow_filename': filename,  # 添加工作流文件名
                'parameters': parameters,  # 添加参数
                'start_time': datetime.now().isoformat(),
                'progress': 0,
                'prompt_id': None
            }
            
            # 修改工作流参数和图像输入
            modified_workflow = self.modify_workflow_with_parameters_and_images(workflow_data, parameters, selected_images)
            
            # 将UI格式转换为API格式
            api_workflow = self.convert_ui_to_api_format(modified_workflow)
            if not api_workflow:
                error_msg = "转换workflow格式失败"
                logger.error(error_msg)
                running_tasks[task_id].update({
                    'status': 'failed',
                    'end_time': datetime.now().isoformat(),
                    'error': error_msg
                })
                return {'success': False, 'error': error_msg}
            
            # 调试：检查转换后的workflow
            logger.info(f"转换后的API workflow包含 {len(api_workflow.get('prompt', {}))} 个节点")
            for node_id, node_data in api_workflow.get('prompt', {}).items():
                logger.info(f"节点 {node_id}: {node_data.get('class_type', 'unknown')}")
            
            # 特别检查节点8
            if '8' in api_workflow.get('prompt', {}):
                logger.info(f"节点8存在: {api_workflow['prompt']['8']}")
            else:
                logger.error("节点8不存在于API workflow中！")
                logger.error(f"可用的节点ID: {list(api_workflow.get('prompt', {}).keys())}")
            
            # 检查SaveImage节点
            save_image_nodes = [node_id for node_id, node_data in api_workflow.get('prompt', {}).items() 
                               if node_data.get('class_type') == 'SaveImage']
            for node_id in save_image_nodes:
                node_data = api_workflow['prompt'][node_id]
                logger.info(f"SaveImage节点 {node_id}: {node_data}")
                if 'images' in node_data.get('inputs', {}):
                    images_value = node_data['inputs']['images']
                    logger.info(f"SaveImage节点 {node_id} 的images参数: {images_value} (类型: {type(images_value)})")
            
            # 生成客户端ID
            client_id = str(uuid.uuid4())
            
            # 准备API请求数据
            prompt_data = {
                "prompt": api_workflow['prompt'],
                "client_id": client_id
            }
            
            # 调试：显示发送给ComfyUI的数据
            logger.info(f"发送给ComfyUI的prompt_data中的节点: {list(prompt_data['prompt'].keys())}")
            if '8' in prompt_data['prompt']:
                logger.info(f"prompt_data中节点8存在: {prompt_data['prompt']['8']}")
            else:
                logger.error("prompt_data中节点8不存在！")
            
            # 发送到ComfyUI API
            logger.info(f"发送修改后的workflow到ComfyUI: {filename}")
            response = requests.post(
                f"{COMFYUI_API_URL}/prompt", 
                json=prompt_data,
                timeout=30
            )
            
            if response.status_code == 200:
                result_data = response.json()
                prompt_id = result_data.get('prompt_id')
                
                running_tasks[task_id].update({
                    'prompt_id': prompt_id,
                    'client_id': client_id,
                    'progress': 10
                })
                
                logger.info(f"Workflow提交成功, prompt_id: {prompt_id}")
                
                # 启动状态监控
                self._monitor_workflow_progress(task_id, prompt_id, client_id)
                
                result = {'success': True, 'prompt_id': prompt_id}
            else:
                error_msg = f"ComfyUI API错误: {response.status_code} - {response.text}"
                logger.error(error_msg)
                running_tasks[task_id].update({
                    'status': 'failed',
                    'end_time': datetime.now().isoformat(),
                    'error': error_msg
                })
                result = {'success': False, 'error': error_msg}
                
        except Exception as e:
            error_msg = str(e)
            logger.error(f"执行workflow失败: {error_msg}")
            running_tasks[task_id].update({
                'status': 'failed',
                'end_time': datetime.now().isoformat(),
                'error': error_msg
            })
            result = {'success': False, 'error': error_msg}
        
        return result
    
    def modify_workflow_with_parameters(self, workflow_data, parameters):
        """根据用户参数修改工作流"""
        return self.modify_workflow_with_parameters_and_images(workflow_data, parameters, {})
    
    def modify_workflow_with_parameters_and_images(self, workflow_data, parameters, selected_images):
        """根据用户参数和图像输入修改工作流（UI格式）"""
        try:
            nodes = workflow_data.get('nodes', [])
            modified_nodes = []
            
            for node in nodes:
                modified_node = node.copy()
                # UI格式使用type字段，API格式使用class_type字段
                node_type = node.get('type', '')  # UI格式
                node_id = node.get('id', '')
                
                # 根据节点类型修改参数
                if node_type == 'KSampler':
                    # 修改KSampler参数 - UI格式中参数在widgets_values中
                    widgets_values = modified_node.get('widgets_values', [])
                    # 处理种子参数 - KSampler的seed在widgets_values[0]
                    if 'seed' in parameters and parameters['seed'] != '-1' and len(widgets_values) > 0:
                        try:
                            seed_value = int(parameters['seed'])
                            # 确保seed值不小于0
                            if seed_value < 0:
                                seed_value = 0
                            widgets_values[0] = seed_value
                        except (ValueError, TypeError):
                            # 如果转换失败，使用默认值0而不是-1
                            widgets_values[0] = 0
                    # 处理采样器参数
                    if 'sampler' in parameters and len(widgets_values) > 4:
                        widgets_values[4] = parameters['sampler']
                    modified_node['widgets_values'] = widgets_values
                
                elif 'KSamplerSelect' in node_type:
                    # 修改KSamplerSelect参数 - 只有sampler_name参数
                    widgets_values = modified_node.get('widgets_values', [])
                    # 处理采样器参数
                    if 'sampler' in parameters and len(widgets_values) > 0:
                        widgets_values[0] = parameters['sampler']
                    modified_node['widgets_values'] = widgets_values
                
                elif 'RandomNoise' in node_type:
                    # 修改随机种子 - UI格式中seed在widgets_values中
                    widgets_values = modified_node.get('widgets_values', [])
                    if 'seed' in parameters and parameters['seed'] != '-1':
                        try:
                            seed_value = int(parameters['seed'])
                            # 确保seed值不小于0，因为ComfyUI要求noise_seed >= 0
                            if seed_value < 0:
                                seed_value = 0
                            widgets_values[0] = seed_value
                        except (ValueError, TypeError):
                            # 如果转换失败，使用默认值0而不是-1
                            widgets_values[0] = 0
                    modified_node['widgets_values'] = widgets_values
                
                elif 'BasicScheduler' in node_type:
                    # 修改调度器参数 - UI格式中参数在widgets_values中
                    widgets_values = modified_node.get('widgets_values', [])
                    if len(widgets_values) >= 3:
                        if 'scheduler' in parameters:
                            widgets_values[0] = parameters['scheduler']
                        if 'steps' in parameters:
                            try:
                                widgets_values[1] = int(parameters['steps'])
                            except (ValueError, TypeError):
                                widgets_values[1] = 20
                        if 'denoise' in parameters:
                            try:
                                widgets_values[2] = float(parameters['denoise'])
                            except (ValueError, TypeError):
                                widgets_values[2] = 1.0
                    modified_node['widgets_values'] = widgets_values
                
                elif 'FluxGuidance' in node_type:
                    # 修改CFG参数 - UI格式中CFG在widgets_values中
                    widgets_values = modified_node.get('widgets_values', [])
                    if 'cfg' in parameters and len(widgets_values) > 0:
                        try:
                            widgets_values[0] = float(parameters['cfg'])
                        except (ValueError, TypeError):
                            widgets_values[0] = 7.0
                    modified_node['widgets_values'] = widgets_values
                
                elif 'CLIPTextEncode' in node_type:
                    # 修改提示词 - UI格式中文本在widgets_values中
                    widgets_values = modified_node.get('widgets_values', [])
                    # 根据节点标题判断是正面还是负面提示词
                    node_title = node.get('title', '').lower()
                    if 'negative' in node_title or 'neg' in node_title:
                        if 'negative_prompt' in parameters and parameters['negative_prompt']:
                            if len(widgets_values) > 0:
                                widgets_values[0] = parameters['negative_prompt']
                    else:
                        if 'positive_prompt' in parameters and parameters['positive_prompt']:
                            if len(widgets_values) > 0:
                                widgets_values[0] = parameters['positive_prompt']
                
                elif 'PrimitiveNode' in node_type:
                    # 修改PrimitiveNode的尺寸参数
                    node_title = node.get('title', '').lower()
                    widgets_values = modified_node.get('widgets_values', [])
                    
                    if node_title == 'width' and 'width' in parameters and len(widgets_values) >= 1:
                        try:
                            width_value = int(parameters['width'])
                            widgets_values[0] = width_value
                        except (ValueError, TypeError):
                            # 使用JSON文件中的原始值作为默认值
                            widgets_values[0] = widgets_values[0] if widgets_values[0] is not None else 1024
                    
                    elif node_title == 'height' and 'height' in parameters and len(widgets_values) >= 1:
                        try:
                            height_value = int(parameters['height'])
                            widgets_values[0] = height_value
                        except (ValueError, TypeError):
                            # 使用JSON文件中的原始值作为默认值
                            widgets_values[0] = widgets_values[0] if widgets_values[0] is not None else 1024
                    
                    modified_node['widgets_values'] = widgets_values
                
                elif 'EmptySD3LatentImage' in node_type:
                    # 修改EmptySD3LatentImage的尺寸参数
                    widgets_values = modified_node.get('widgets_values', [])
                    if len(widgets_values) >= 2:
                        if 'width' in parameters:
                            try:
                                width_value = int(parameters['width'])
                                widgets_values[0] = width_value
                            except (ValueError, TypeError):
                                # 使用JSON文件中的原始值作为默认值
                                widgets_values[0] = widgets_values[0] if widgets_values[0] is not None else 1024
                        
                        if 'height' in parameters:
                            try:
                                height_value = int(parameters['height'])
                                widgets_values[1] = height_value
                            except (ValueError, TypeError):
                                # 使用JSON文件中的原始值作为默认值
                                widgets_values[1] = widgets_values[1] if widgets_values[1] is not None else 1024
                    
                    modified_node['widgets_values'] = widgets_values
                
                # 处理模型加载器节点
                elif 'NunchakuTextEncoderLoader' in node_type:
                    widgets_values = modified_node.get('widgets_values', [])
                    model_loaders = parameters.get('model_loaders', {})
                    
                    if len(widgets_values) >= 6:
                        # 模型类型
                        param_key = f'model_type_{node_id}'
                        if param_key in model_loaders:
                            widgets_values[0] = model_loaders[param_key]
                        
                        # 文本编码器1
                        param_key = f'text_encoder1_{node_id}'
                        if param_key in model_loaders and len(widgets_values) > 1:
                            widgets_values[1] = model_loaders[param_key]
                        
                        # 文本编码器2
                        param_key = f'text_encoder2_{node_id}'
                        if param_key in model_loaders and len(widgets_values) > 2:
                            widgets_values[2] = model_loaders[param_key]
                        
                        # T5最小长度
                        param_key = f't5_min_length_{node_id}'
                        if param_key in model_loaders and len(widgets_values) > 3:
                            try:
                                widgets_values[3] = int(model_loaders[param_key])
                            except (ValueError, TypeError):
                                widgets_values[3] = 512
                        
                        # 使用4bit T5
                        param_key = f'use_4bit_t5_{node_id}'
                        if param_key in model_loaders and len(widgets_values) > 4:
                            widgets_values[4] = model_loaders[param_key]
                        
                        # INT4模型
                        param_key = f'int4_model_{node_id}'
                        if param_key in model_loaders and len(widgets_values) > 5:
                            widgets_values[5] = model_loaders[param_key]
                    
                    modified_node['widgets_values'] = widgets_values
                
                elif 'NunchakuFluxDiTLoader' in node_type:
                    widgets_values = modified_node.get('widgets_values', [])
                    model_loaders = parameters.get('model_loaders', {})
                    
                    if len(widgets_values) >= 7:
                        # 模型路径
                        param_key = f'model_path_{node_id}'
                        if param_key in model_loaders:
                            widgets_values[0] = model_loaders[param_key]
                        
                        # 缓存阈值
                        param_key = f'cache_threshold_{node_id}'
                        if param_key in model_loaders and len(widgets_values) > 1:
                            try:
                                widgets_values[1] = int(model_loaders[param_key])
                            except (ValueError, TypeError):
                                widgets_values[1] = 0
                        
                        # 注意力机制
                        param_key = f'attention_{node_id}'
                        if param_key in model_loaders and len(widgets_values) > 2:
                            widgets_values[2] = model_loaders[param_key]
                        
                        # CPU卸载
                        param_key = f'cpu_offload_{node_id}'
                        if param_key in model_loaders and len(widgets_values) > 3:
                            widgets_values[3] = model_loaders[param_key]
                        
                        # 设备ID
                        param_key = f'device_id_{node_id}'
                        if param_key in model_loaders and len(widgets_values) > 4:
                            try:
                                widgets_values[4] = int(model_loaders[param_key])
                            except (ValueError, TypeError):
                                widgets_values[4] = 0
                        
                        # 数据类型
                        param_key = f'data_type_{node_id}'
                        if param_key in model_loaders and len(widgets_values) > 5:
                            widgets_values[5] = model_loaders[param_key]
                        
                        # I2F模式
                        param_key = f'i_2_f_mode_{node_id}'
                        if param_key in model_loaders and len(widgets_values) > 6:
                            widgets_values[6] = model_loaders[param_key]
                    
                    modified_node['widgets_values'] = widgets_values
                
                elif 'NunchakuFluxLoraLoader' in node_type:
                    widgets_values = modified_node.get('widgets_values', [])
                    model_loaders = parameters.get('model_loaders', {})
                    
                    if len(widgets_values) >= 2:
                        # LoRA名称
                        param_key = f'lora_name_{node_id}'
                        if param_key in model_loaders:
                            widgets_values[0] = model_loaders[param_key]
                        
                        # LoRA强度
                        param_key = f'lora_strength_{node_id}'
                        if param_key in model_loaders and len(widgets_values) > 1:
                            try:
                                widgets_values[1] = float(model_loaders[param_key])
                            except (ValueError, TypeError):
                                widgets_values[1] = 1.0
                    
                    modified_node['widgets_values'] = widgets_values
                
                elif 'VAELoader' in node_type:
                    widgets_values = modified_node.get('widgets_values', [])
                    model_loaders = parameters.get('model_loaders', {})
                    
                    if len(widgets_values) >= 1:
                        # VAE名称
                        param_key = f'vae_name_{node_id}'
                        if param_key in model_loaders:
                            widgets_values[0] = model_loaders[param_key]
                    
                    modified_node['widgets_values'] = widgets_values
                
                elif 'DualCLIPLoader' in node_type:
                    widgets_values = modified_node.get('widgets_values', [])
                    model_loaders = parameters.get('model_loaders', {})
                    
                    if len(widgets_values) >= 3:
                        # CLIP名称1
                        param_key = f'clip_name1_{node_id}'
                        if param_key in model_loaders:
                            widgets_values[0] = model_loaders[param_key]
                        
                        # CLIP名称2
                        param_key = f'clip_name2_{node_id}'
                        if param_key in model_loaders and len(widgets_values) > 1:
                            widgets_values[1] = model_loaders[param_key]
                        
                        # CLIP类型
                        param_key = f'clip_type_{node_id}'
                        if param_key in model_loaders and len(widgets_values) > 2:
                            widgets_values[2] = model_loaders[param_key]
                    
                    modified_node['widgets_values'] = widgets_values
                    modified_node['widgets_values'] = widgets_values
                
                elif 'EmptyLatentImage' in node_type or 'EmptySD3LatentImage' in node_type:
                    # 修改图像尺寸 - UI格式中尺寸在widgets_values中
                    widgets_values = modified_node.get('widgets_values', [])
                    if 'width' in parameters and 'height' in parameters and len(widgets_values) >= 2:
                        try:
                            widgets_values[0] = int(parameters['width'])
                        except (ValueError, TypeError):
                            # 使用JSON文件中的原始值作为默认值
                            widgets_values[0] = widgets_values[0] if widgets_values[0] is not None else 1024
                        try:
                            widgets_values[1] = int(parameters['height'])
                        except (ValueError, TypeError):
                            # 使用JSON文件中的原始值作为默认值
                            widgets_values[1] = widgets_values[1] if widgets_values[1] is not None else 1024
                        modified_node['widgets_values'] = widgets_values
                
                # 处理ControlNet配置节点
                elif 'ControlNetLoader' in node_type:
                    widgets_values = modified_node.get('widgets_values', [])
                    controlnet_configs = parameters.get('controlnet_configs', {})
                    
                    if len(widgets_values) >= 1:
                        # ControlNet模型名称
                        param_key = f'control_net_name_{node_id}'
                        if param_key in controlnet_configs:
                            widgets_values[0] = controlnet_configs[param_key]
                    
                    modified_node['widgets_values'] = widgets_values
                
                elif 'ControlNetApplyAdvanced' in node_type:
                    widgets_values = modified_node.get('widgets_values', [])
                    controlnet_configs = parameters.get('controlnet_configs', {})
                    
                    if len(widgets_values) >= 3:
                        # ControlNet强度
                        param_key = f'strength_{node_id}'
                        if param_key in controlnet_configs:
                            try:
                                widgets_values[0] = float(controlnet_configs[param_key])
                            except (ValueError, TypeError):
                                widgets_values[0] = 1.0
                        
                        # 开始百分比
                        param_key = f'start_percent_{node_id}'
                        if param_key in controlnet_configs:
                            try:
                                widgets_values[1] = float(controlnet_configs[param_key])
                            except (ValueError, TypeError):
                                widgets_values[1] = 0.0
                        
                        # 结束百分比
                        param_key = f'end_percent_{node_id}'
                        if param_key in controlnet_configs:
                            try:
                                widgets_values[2] = float(controlnet_configs[param_key])
                            except (ValueError, TypeError):
                                widgets_values[2] = 1.0
                    
                    modified_node['widgets_values'] = widgets_values
                
                elif 'SetUnionControlNetType' in node_type:
                    widgets_values = modified_node.get('widgets_values', [])
                    controlnet_configs = parameters.get('controlnet_configs', {})
                    
                    if len(widgets_values) >= 1:
                        # 联合类型
                        param_key = f'union_type_{node_id}'
                        if param_key in controlnet_configs:
                            widgets_values[0] = controlnet_configs[param_key]
                    
                    modified_node['widgets_values'] = widgets_values
                
                # 处理图像输入节点
                elif 'LoadImage' in node_type or 'ImageLoader' in node_type:
                    if str(node_id) in selected_images:
                        image_info = selected_images[str(node_id)]
                        image_path = image_info.get('path', '')
                        
                        # 构建完整的图像路径
                        output_dir = os.path.join(os.path.dirname(__file__), 'outputs')
                        full_image_path = os.path.join(output_dir, image_path)
                        
                        if os.path.exists(full_image_path):
                            # 修改图像路径 - UI格式中widgets_values包含图像文件名
                            widgets_values = modified_node.get('widgets_values', [])
                            if len(widgets_values) > 0:
                                # 提取文件名
                                image_filename = os.path.basename(image_path)
                                widgets_values[0] = image_filename
                                modified_node['widgets_values'] = widgets_values
                                logger.info(f"设置图像输入 {node_id}: {image_filename}")
                        else:
                            logger.warning(f"图像文件不存在: {full_image_path}")
                
                modified_nodes.append(modified_node)
            
            # 返回修改后的工作流
            modified_workflow = workflow_data.copy()
            modified_workflow['nodes'] = modified_nodes
            
            # 添加调试日志
            modified_params = []
            for param_name, param_value in parameters.items():
                if param_value and str(param_value).strip():
                    modified_params.append(f"{param_name}: {param_value}")
            
            if modified_params:
                logger.info(f"工作流参数修改完成: {modified_params}")
            
            return modified_workflow
            
        except Exception as e:
            logger.error(f"修改工作流参数失败: {e}")
            # 如果修改失败，返回原始工作流
            return workflow_data
    
    def convert_ui_to_api_format(self, ui_workflow):
        """将UI格式的workflow转换为API格式"""
        try:
            # 使用你提供的原始转换逻辑
            api_prompt = {}
            nodes_by_id = {str(n['id']): n for n in ui_workflow.get('nodes', [])}
            primitive_values = {nid: n['widgets_values'][0] for nid, n in nodes_by_id.items() if n.get('type') == 'PrimitiveNode' and n.get('widgets_values')}
            NODE_TYPES_TO_IGNORE = ["PrimitiveNode", "Note", "MarkdownNote"]

            for node_id, node in nodes_by_id.items():
                if node.get('type') in NODE_TYPES_TO_IGNORE: continue
                node_type = node.get('type')
                api_node = {"class_type": node_type, "inputs": {}}
                
                # 处理widgets_values
                if node_type in WIDGET_INDEX_MAP and 'widgets_values' in node:
                    for w_name, w_idx in WIDGET_INDEX_MAP[node_type].items():
                        if w_idx >= 0 and len(node['widgets_values']) > w_idx:
                            value = node['widgets_values'][w_idx]
                            # 清理模型名称中的状态标记
                            if isinstance(value, str):
                                # 移除 "✅" 和 "❌ (文件不存在)" 标记
                                cleaned_value = value.replace(' ✅', '').replace(' ❌ (文件不存在)', '')
                                # 修正文件名不匹配问题
                                if cleaned_value == 'flux1-turbo-alpha.safetensors':
                                    cleaned_value = 'flux.1-turbo-alpha.safetensors'
                                api_node['inputs'][w_name] = cleaned_value
                            else:
                                api_node['inputs'][w_name] = value
                    
                    # 添加调试日志
                    if node_type in ['CLIPTextEncode', 'RandomNoise', 'FluxGuidance', 'BasicScheduler']:
                        logger.info(f"节点 {node_id} ({node_type}) 转换结果: {api_node['inputs']}")
                
                # 处理inputs连接
                if 'inputs' in node:
                    for i, input_data in enumerate(node['inputs']):
                        if input_data.get('link') is not None:
                            for link in ui_workflow.get('links', []):
                                # 支持新格式：links = [link_id, src_node_id, src_slot, dst_node_id, dst_slot, type]
                                # 支持旧格式：links = [link_id, src_node_id, src_slot, dst_node_id]
                                if len(link) >= 4:
                                    if len(link) == 6:  # 新格式
                                        link_id, src_id, src_slot, dst_id, dst_slot, link_type = link
                                        if str(dst_id) == node_id and dst_slot == i:
                                            in_name = input_data['name']
                                            api_node['inputs'][in_name] = primitive_values.get(str(src_id), [str(src_id), src_slot])
                                            break
                                    else:  # 旧格式
                                        link_id, src_id, src_slot, dst_id = link
                                        if str(dst_id) == node_id and i == 0:  # 旧格式假设dst_slot为0
                                            in_name = input_data['name']
                                            api_node['inputs'][in_name] = primitive_values.get(str(src_id), [str(src_id), src_slot])
                                            break
                api_prompt[node_id] = api_node
            
            api_workflow = {
                'prompt': api_prompt,
                'extra_data': {
                    'extra_pnginfo': {
                        'workflow': ui_workflow
                    }
                }
            }
            
            return api_workflow
            
        except Exception as e:
            logger.error(f"转换UI格式到API格式失败: {e}")
            return None
    
    def _monitor_workflow_progress(self, task_id, prompt_id, client_id):
        """监控workflow执行进度"""
        def monitor():
            try:
                while True:
                    time.sleep(2)  # 每2秒检查一次
                    
                    if task_id not in running_tasks:
                        break
                    
                    # 检查队列状态
                    try:
                        queue_response = requests.get(f"{COMFYUI_API_URL}/queue", timeout=10)
                        if queue_response.status_code == 200:
                            queue_data = queue_response.json()
                            
                            # 检查是否在执行队列中
                            running_queue = queue_data.get('queue_running', [])
                            pending_queue = queue_data.get('queue_pending', [])
                            
                            found_in_running = any(item[1] == prompt_id for item in running_queue)
                            found_in_pending = any(item[1] == prompt_id for item in pending_queue)
                            
                            if found_in_running:
                                running_tasks[task_id].update({
                                    'status': 'running',
                                    'progress': 50
                                })
                            elif found_in_pending:
                                running_tasks[task_id].update({
                                    'status': 'pending',
                                    'progress': 20
                                })
                            else:
                                # 任务完成或失败 - 检查历史记录
                                self._check_task_completion(task_id, prompt_id)
                                break
                    except Exception as e:
                        logger.error(f"监控进度失败: {e}")
                        time.sleep(5)  # 出错时等待更长时间
                        
            except Exception as e:
                logger.error(f"监控线程异常: {e}")
                if task_id in running_tasks:
                    running_tasks[task_id].update({
                        'status': 'failed',
                        'end_time': datetime.now().isoformat(),
                        'error': f"监控失败: {str(e)}"
                    })
        
        # 在后台线程中运行监控
        monitor_thread = threading.Thread(target=monitor)
        monitor_thread.daemon = True
        monitor_thread.start()
    
    def _check_task_completion(self, task_id, prompt_id):
        """检查任务完成状态并处理输出"""
        try:
            history_response = requests.get(f"{COMFYUI_API_URL}/history/{prompt_id}", timeout=10)
            if history_response.status_code != 200:
                logger.warning(f"无法获取任务历史记录: {prompt_id}")
                running_tasks[task_id].update({
                    'status': 'completed',
                    'end_time': datetime.now().isoformat(),
                    'progress': 100,
                    'output': "任务可能已完成，但无法获取详细信息"
                })
                return
                
            history_data = history_response.json()
            if prompt_id not in history_data:
                logger.warning(f"任务 {prompt_id} 不在历史记录中")
                running_tasks[task_id].update({
                    'status': 'completed',
                    'end_time': datetime.now().isoformat(),
                    'progress': 100,
                    'output': "任务完成但记录缺失"
                })
                return
            
            task_info = history_data[prompt_id]
            task_status = task_info.get('status', {})
            
            # 检查任务状态
            if task_status.get('status_str') == 'error':
                # 处理错误状态
                messages = task_status.get('messages', [])
                user_error_msg = '工作流执行失败，请查看服务器日志'
                error_msg_detail = '未知错误'
                for msg_type, msg_data in messages:
                    if msg_type == 'execution_error':
                        raw_error = msg_data.get('exception_message', '未知错误')
                        node_type = msg_data.get('node_type', '未知节点')
                        node_id = msg_data.get('node_id', '未知')
                        error_msg_detail = f"节点 {node_id} ({node_type}): {raw_error}"
                        break
                
                # 只在服务器日志中记录详细错误，不直接返回给前端
                logger.error(f"任务 {prompt_id} 执行失败: {error_msg_detail}")
                running_tasks[task_id].update({
                    'status': 'failed',
                    'end_time': datetime.now().isoformat(),
                    'error': user_error_msg
                })
            elif task_status.get('status_str') == 'success':
                # 处理成功完成的任务
                logger.info(f"任务 {prompt_id} 已完成，检查输出")
                
                # 处理输出图片
                # 添加任务元数据到task_info
                task_info['task_id'] = task_id
                task_info['workflow_filename'] = running_tasks[task_id].get('workflow_filename', 'unknown')
                task_info['parameters'] = running_tasks[task_id].get('parameters', {})
                
                output_info = self._process_task_outputs(task_info)
                
                running_tasks[task_id].update({
                    'status': 'completed',
                    'end_time': datetime.now().isoformat(),
                    'progress': 100,
                    'output': output_info.get('message', '任务完成'),
                    'image_url': output_info.get('image_url'),
                    'metadata_url': output_info.get('metadata_url')
                })
            else:
                # 其他状态
                logger.info(f"任务 {prompt_id} 状态: {task_status.get('status_str', 'unknown')}")
                running_tasks[task_id].update({
                    'status': 'completed',
                    'end_time': datetime.now().isoformat(),
                    'progress': 100,
                    'output': "任务完成"
                })
                
        except Exception as e:
            logger.error(f"检查任务完成状态失败: {e}")
            running_tasks[task_id].update({
                'status': 'failed',
                'end_time': datetime.now().isoformat(),
                'error': f"检查任务状态失败: {str(e)}"
            })
    
    def _process_task_outputs(self, task_info):
        """处理任务输出，安全地处理图片输出"""
        try:
            outputs = task_info.get('outputs', {})
            if not outputs:
                return {'message': '任务完成，但没有输出'}
            
            logger.info(f"任务输出: {outputs}")
            
            # 获取任务元数据
            task_id = task_info.get('task_id', 'unknown')
            workflow_filename = task_info.get('workflow_filename', 'unknown')
            parameters = task_info.get('parameters', {})
            
            # 遍历输出节点
            for node_id, node_output in outputs.items():
                if not node_output or not isinstance(node_output, dict):
                    logger.warning(f"节点 {node_id} 输出为空或格式错误")
                    continue
                
                if 'images' not in node_output:
                    continue
                    
                images = node_output.get('images', [])
                if not images or not isinstance(images, list):
                    logger.warning(f"节点 {node_id} 图片列表为空或格式错误")
                    continue
                
                # 安全地处理图片列表
                for i, img in enumerate(images):
                    if img is None:
                        logger.warning(f"节点 {node_id} 第 {i} 个图片为null，跳过")
                        continue
                    
                    if not isinstance(img, dict):
                        logger.warning(f"节点 {node_id} 第 {i} 个图片格式错误: {type(img)}")
                        continue
                    
                    filename = img.get('filename')
                    if not filename:
                        logger.warning(f"节点 {node_id} 第 {i} 个图片缺少filename字段: {img}")
                        continue
                    
                    # 尝试获取图片
                    try:
                        subfolder = img.get('subfolder', '')
                        img_type = img.get('type', 'output')
                        
                        logger.info(f"尝试获取图片: filename={filename}, subfolder={subfolder}, type={img_type}")
                        
                        img_data = self._get_image_from_comfyui(filename, subfolder, img_type)
                        if img_data:
                            # 保存图片到本地输出目录
                            output_dir = os.path.join(os.path.dirname(__file__), 'outputs')
                            os.makedirs(output_dir, exist_ok=True)
                            
                            # 生成唯一的文件名
                            unique_id = uuid.uuid4().hex[:8]
                            output_filename = f"result_{unique_id}_{filename}"
                            output_path = os.path.join(output_dir, output_filename)
                            
                            # 保存图片文件
                            with open(output_path, 'wb') as f:
                                f.write(img_data)
                            
                            # 从ComfyUI历史记录中提取实际种子值
                            actual_seed = self._extract_actual_seed(task_info, parameters)
                            
                            # 更新参数中的种子值
                            if actual_seed is not None:
                                parameters['actual_seed'] = actual_seed
                                # 如果用户设置的是-1，也记录用户输入
                                if parameters.get('seed') == -1:
                                    parameters['user_seed'] = -1
                            
                            # 保存元数据
                            metadata = {
                                'task_id': task_id,
                                'workflow_filename': workflow_filename,
                                'original_filename': filename,
                                'output_filename': output_filename,
                                'parameters': parameters,
                                'created_time': datetime.now().isoformat(),
                                'node_id': node_id,
                                'subfolder': subfolder,
                                'img_type': img_type
                            }
                            
                            # 保存元数据到JSON文件
                            metadata_filename = f"metadata_{unique_id}.json"
                            metadata_path = os.path.join(output_dir, metadata_filename)
                            with open(metadata_path, 'w', encoding='utf-8') as f:
                                json.dump(metadata, f, ensure_ascii=False, indent=2)
                            
                            logger.info(f"图片和元数据已保存: {output_filename}")
                            return {
                                'message': f'任务完成，图片已生成: {filename}',
                                'image_url': f'/outputs/{output_filename}',
                                'metadata_url': f'/outputs/{metadata_filename}'
                            }
                    except Exception as e:
                        logger.error(f"处理图片失败 {filename}: {e}")
                        continue
            
            return {'message': '任务完成，但没有找到有效的图片输出'}
            
        except Exception as e:
            logger.error(f"处理任务输出失败: {e}")
            return {'message': f'任务完成，但处理输出时出错: {str(e)}'}
    
    def _extract_actual_seed(self, task_info, parameters):
        """从ComfyUI历史记录中提取实际使用的种子值"""
        try:
            # 获取prompt数据，包含实际执行的节点信息
            prompt_data = task_info.get('prompt', [])
            if not prompt_data or len(prompt_data) < 3:
                return None
            
            # prompt_data[2]包含节点配置
            nodes_config = prompt_data[2]
            
            # 查找RandomNoise节点
            for node_id, node_data in nodes_config.items():
                if node_data.get('class_type') == 'RandomNoise':
                    # 检查inputs中的noise_seed
                    inputs = node_data.get('inputs', {})
                    if 'noise_seed' in inputs:
                        actual_seed = inputs['noise_seed']
                        logger.info(f"找到RandomNoise节点 {node_id} 的实际种子值: {actual_seed}")
                        return actual_seed
            
            # 如果没有找到RandomNoise节点，尝试查找其他可能的种子节点
            # 比如KSampler节点
            for node_id, node_data in nodes_config.items():
                if node_data.get('class_type') == 'KSampler':
                    inputs = node_data.get('inputs', {})
                    if 'seed' in inputs:
                        actual_seed = inputs['seed']
                        logger.info(f"找到KSampler节点 {node_id} 的实际种子值: {actual_seed}")
                        return actual_seed
            
            logger.warning("未找到包含种子值的节点")
            return None
            
        except Exception as e:
            logger.error(f"提取实际种子值时发生错误: {e}")
            return None

    def _get_image_from_comfyui(self, filename, subfolder='', img_type='output'):
        """从ComfyUI获取图片数据"""
        try:
            params = {
                'filename': filename,
                'type': img_type
            }
            if subfolder:
                params['subfolder'] = subfolder
            
            response = requests.get(f"{COMFYUI_API_URL}/view", params=params, timeout=30)
            if response.status_code == 200:
                return response.content
            else:
                logger.error(f"获取图片失败: {response.status_code} - {response.text}")
                return None
        except Exception as e:
            logger.error(f"从ComfyUI获取图片时发生错误: {e}")
            return None

# 创建全局runner实例
runner = WorkflowRunner()

@app.route('/')
def index():
    """主页"""
    return render_template('index.html')

@app.route('/test')
def test():
    """测试页面"""
    return send_from_directory('.', 'test.html')

@app.route('/debug')
def debug():
    """调试页面"""
    return send_from_directory('.', 'debug.html')

@app.route('/test_image_display')
def test_image_display():
    """测试图片显示页面"""
    return send_from_directory('.', 'test_image_display.html')

@app.route('/test_frontend')
def test_frontend():
    """前端功能测试页面"""
    return send_from_directory('.', 'test_frontend.html')

@app.route('/gallery')
def gallery():
    """图片画廊页面"""
    return send_from_directory('.', 'gallery.html')

@app.route('/api/workflows')
def get_workflows():
    """获取所有workflow列表"""
    try:
        workflows = runner.get_workflows()
        return jsonify({'success': True, 'workflows': workflows})
    except Exception as e:
        logger.error(f"获取workflows失败: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/workflow/<path:filename>')
def get_workflow_details(filename):
    """获取特定工作流的详细信息"""
    try:
        filepath = os.path.join(WORKFLOW_DIR, filename)
        if not os.path.exists(filepath):
            return jsonify({'success': False, 'error': '工作流文件不存在'}), 404
        
        with open(filepath, 'r', encoding='utf-8') as f:
            workflow_data = json.load(f)
        
        return jsonify({'success': True, 'workflow': workflow_data})
    except Exception as e:
        logger.error(f"获取工作流详情失败: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/run', methods=['POST'])
def run_workflow():
    """运行选定的workflow"""
    data = request.get_json()
    filename = data.get('filename')
    parameters = data.get('parameters', {})
    
    if not filename:
        return jsonify({'success': False, 'error': '缺少filename参数'}), 400
    
    # 从parameters中提取selected_images
    selected_images = parameters.get('selected_images', {})
    
    # 生成任务ID
    task_id = f"task_{int(time.time())}_{len(running_tasks)}"
    
    # 在后台线程中运行
    def run_in_background():
        runner.run_workflow_with_parameters_and_images(filename, task_id, parameters, selected_images)
    
    thread = threading.Thread(target=run_in_background)
    thread.start()
    
    return jsonify({'success': True, 'task_id': task_id})

@app.route('/api/status/<task_id>')
def get_task_status(task_id):
    """获取任务状态"""
    if task_id in running_tasks:
        return jsonify({'success': True, 'task': running_tasks[task_id]})
    else:
        return jsonify({'success': False, 'error': '任务不存在'}), 404

@app.route('/api/tasks')
def get_all_tasks():
    """获取所有任务状态"""
    return jsonify({'success': True, 'tasks': running_tasks})

@app.route('/api/comfyui/status')
def check_comfyui():
    """检查ComfyUI连接状态"""
    try:
        is_running = runner.check_comfyui_status()
        if is_running:
            # 获取系统信息
            response = requests.get(f"{COMFYUI_API_URL}/system_stats", timeout=5)
            if response.status_code == 200:
                system_info = response.json()
                return jsonify({
                    'success': True, 
                    'connected': True,
                    'url': COMFYUI_API_URL,
                    'system_info': system_info.get('system', {})
                })
        
        return jsonify({
            'success': True, 
            'connected': False,
            'url': COMFYUI_API_URL,
            'error': 'ComfyUI服务未运行或无法连接'
        })
    except Exception as e:
        return jsonify({
            'success': False, 
            'connected': False,
            'url': COMFYUI_API_URL,
            'error': str(e)
        })

@app.route('/static/<path:filename>')
def static_files(filename):
    """静态文件服务"""
    return send_from_directory('static', filename)

@app.route('/outputs/<path:filename>')
def output_files(filename):
    """输出文件服务"""
    output_dir = os.path.join(os.path.dirname(__file__), 'outputs')
    return send_from_directory(output_dir, filename)

@app.route('/api/images')
def get_available_images():
    """获取可用的图像列表"""
    try:
        output_dir = os.path.join(os.path.dirname(__file__), 'outputs')
        uploaded_dir = os.path.join(output_dir, 'uploaded')
        generated_dir = os.path.join(output_dir, 'generated')
        
        images = {
            'uploaded': [],
            'generated': []
        }
        
        # 扫描已上传的图像
        if os.path.exists(uploaded_dir):
            for filename in os.listdir(uploaded_dir):
                if filename.lower().endswith(('.png', '.jpg', '.jpeg', '.webp')):
                    images['uploaded'].append({
                        'name': filename,
                        'path': f'uploaded/{filename}',
                        'size': os.path.getsize(os.path.join(uploaded_dir, filename))
                    })
        
        # 扫描已生成的图像（包括子目录和根目录）
        if os.path.exists(generated_dir):
            for filename in os.listdir(generated_dir):
                if filename.lower().endswith(('.png', '.jpg', '.jpeg', '.webp')):
                    images['generated'].append({
                        'name': filename,
                        'path': f'generated/{filename}',
                        'size': os.path.getsize(os.path.join(generated_dir, filename))
                    })
        
        # 扫描outputs根目录中的生成图像（以result_开头的文件）
        if os.path.exists(output_dir):
            for filename in os.listdir(output_dir):
                if (filename.lower().endswith(('.png', '.jpg', '.jpeg', '.webp')) and 
                    filename.startswith('result_')):
                    images['generated'].append({
                        'name': filename,
                        'path': filename,  # 根目录中的文件，路径就是文件名
                        'size': os.path.getsize(os.path.join(output_dir, filename))
                    })
        
        return jsonify({'success': True, 'images': images})
    except Exception as e:
        logger.error(f"获取图像列表失败: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/upload', methods=['POST'])
def upload_images():
    """上传图像文件"""
    try:
        if 'images' not in request.files:
            return jsonify({'success': False, 'error': '没有选择文件'}), 400
        
        files = request.files.getlist('images')
        if not files or all(file.filename == '' for file in files):
            return jsonify({'success': False, 'error': '没有选择文件'}), 400
        
        uploaded_dir = os.path.join(os.path.dirname(__file__), 'outputs', 'uploaded')
        os.makedirs(uploaded_dir, exist_ok=True)
        
        uploaded_files = []
        for file in files:
            if file and file.filename:
                # 生成安全的文件名
                filename = secure_filename(file.filename)
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                name, ext = os.path.splitext(filename)
                safe_filename = f"{name}_{timestamp}{ext}"
                
                filepath = os.path.join(uploaded_dir, safe_filename)
                file.save(filepath)
                
                uploaded_files.append({
                    'original_name': file.filename,
                    'saved_name': safe_filename,
                    'path': f'uploaded/{safe_filename}'
                })
        
        return jsonify({
            'success': True, 
            'message': f'成功上传 {len(uploaded_files)} 个文件',
            'files': uploaded_files
        })
    except Exception as e:
        logger.error(f"上传图像失败: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/analyze-workflow/<path:filename>')
def analyze_workflow(filename):
    """分析工作流结构并返回参数信息"""
    try:
        filepath = os.path.join(WORKFLOW_DIR, filename)
        if not os.path.exists(filepath):
            return jsonify({'success': False, 'error': '工作流文件不存在'}), 404
        
        with open(filepath, 'r', encoding='utf-8') as f:
            workflow_data = json.load(f)
        
        # 分析工作流结构
        analysis = analyze_workflow_structure(workflow_data)
        
        return jsonify({'success': True, 'analysis': analysis})
    except Exception as e:
        logger.error(f"分析工作流失败: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/generated-images')
def get_generated_images():
    """获取所有生成的图片列表"""
    try:
        output_dir = os.path.join(os.path.dirname(__file__), 'outputs')
        images = []
        
        if os.path.exists(output_dir):
            for filename in os.listdir(output_dir):
                if filename.lower().endswith(('.png', '.jpg', '.jpeg', '.webp')) and filename.startswith('result_'):
                    filepath = os.path.join(output_dir, filename)
                    stat = os.stat(filepath)
                    
                    # 提取唯一ID
                    unique_id = filename.split('_')[1] if '_' in filename else None
                    
                    # 尝试读取对应的元数据文件
                    metadata = {}
                    if unique_id:
                        metadata_filename = f"metadata_{unique_id}.json"
                        metadata_path = os.path.join(output_dir, metadata_filename)
                        if os.path.exists(metadata_path):
                            try:
                                with open(metadata_path, 'r', encoding='utf-8') as f:
                                    metadata = json.load(f)
                            except Exception as e:
                                logger.warning(f"读取元数据文件失败 {metadata_filename}: {e}")
                    
                    image_info = {
                        'filename': filename,
                        'url': f'/outputs/{filename}',
                        'size': stat.st_size,
                        'created_time': datetime.fromtimestamp(stat.st_ctime).isoformat(),
                        'modified_time': datetime.fromtimestamp(stat.st_mtime).isoformat(),
                        'metadata': metadata,
                        'has_metadata': bool(metadata)
                    }
                    
                    # 如果有元数据，添加一些关键信息到主对象中便于显示
                    if metadata:
                        parameters = metadata.get('parameters', {})
                        image_info.update({
                            'workflow': metadata.get('workflow_filename', 'unknown'),
                            'prompt': parameters.get('positive_prompt', ''),
                            'negative_prompt': parameters.get('negative_prompt', ''),
                            'steps': parameters.get('steps', ''),
                            'cfg': parameters.get('cfg', ''),
                            'seed': parameters.get('seed', ''),
                            'sampler': parameters.get('sampler', ''),
                            'width': parameters.get('width', ''),
                            'height': parameters.get('height', '')
                        })
                    
                    images.append(image_info)
        
        # 按修改时间倒序排列
        images.sort(key=lambda x: x['modified_time'], reverse=True)
        
        return jsonify({
            'success': True,
            'images': images,
            'total': len(images)
        })
    except Exception as e:
        logger.error(f"获取生成图片列表失败: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/image-metadata/<path:filename>')
def get_image_metadata(filename):
    """获取单个图片的详细元数据"""
    try:
        output_dir = os.path.join(os.path.dirname(__file__), 'outputs')
        
        # 提取唯一ID
        unique_id = filename.split('_')[1] if '_' in filename else None
        
        if not unique_id:
            return jsonify({'success': False, 'error': '无法解析图片ID'}), 400
        
        # 读取元数据文件
        metadata_filename = f"metadata_{unique_id}.json"
        metadata_path = os.path.join(output_dir, metadata_filename)
        
        if not os.path.exists(metadata_path):
            return jsonify({'success': False, 'error': '元数据文件不存在'}), 404
        
        with open(metadata_path, 'r', encoding='utf-8') as f:
            metadata = json.load(f)
        
        return jsonify({
            'success': True,
            'metadata': metadata
        })
    except Exception as e:
        logger.error(f"获取图片元数据失败: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

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
            'steps': 20,     # 默认值，会被JSON文件中的实际值覆盖
            'cfg': 1.0,      # 默认值，会被JSON文件中的实际值覆盖
            'seed': -1,      # 默认值，会被JSON文件中的实际值覆盖
            'sampler': 'euler', # 默认值，会被JSON文件中的实际值覆盖
            'positive_prompt': '',
            'negative_prompt': ''
        },
        'required_inputs': [],
        'optional_inputs': [],
        'model_loaders': [],
        'controlnet_configs': [],  # 新增：ControlNet配置
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
        
        # 检查LoadImageOutput（Kontext工作流中的图像输入）
        elif 'LoadImageOutput' in node_type:
            analysis['has_image_to_image'] = True
            if not analysis['has_text_to_image']:
                analysis['type'] = 'image-to-image'
            
            # 检查是否有默认图像值
            widgets_values = node.get('widgets_values', [])
            has_default_image = False
            if widgets_values and len(widgets_values) > 0:
                default_image = widgets_values[0]
                # 调试信息
                logger.info(f"LoadImageOutput 节点 {node_id} 默认图像值: '{default_image}'")
                # 如果默认图像不是空的，且不是占位符，则认为这个输入是可选的
                if (isinstance(default_image, str) and 
                    default_image.strip() and 
                    not default_image.startswith('Choose') and
                    not default_image.startswith('Select') and
                    not default_image.startswith('No image') and
                    default_image != '' and
                    '[' in default_image):  # 包含方括号的通常是默认图像文件名
                    has_default_image = True
                    logger.info(f"LoadImageOutput 节点 {node_id} 识别为可选输入")
            
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
                    logger.info(f"LoadImageOutput 节点 {node_id} 识别为示例图像")
            
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
        
        # 检查ControlNet相关节点（但不作为图像输入）
        elif 'ControlNet' in node_type:
            analysis['has_controlnet'] = True
            analysis['type'] = 'controlnet'
            
            # 如果是ControlNetLoader，添加到controlnet_configs
            if 'ControlNetLoader' in node_type:
                widgets_values = node.get('widgets_values', [])
                controlnet_config = {
                    'node_id': node_id,
                    'type': 'ControlNetLoader',
                    'name': 'ControlNet模型加载器',
                    'parameters': {}
                }
                
                if len(widgets_values) >= 1:
                    controlnet_config['parameters'] = {
                        'control_net_name': widgets_values[0] if widgets_values[0] is not None else ''
                    }
                
                analysis['controlnet_configs'].append(controlnet_config)
            
            # 如果是ControlNetApplyAdvanced，添加到controlnet_configs
            elif 'ControlNetApplyAdvanced' in node_type:
                widgets_values = node.get('widgets_values', [])
                controlnet_config = {
                    'node_id': node_id,
                    'type': 'ControlNetApplyAdvanced',
                    'name': 'ControlNet应用器',
                    'parameters': {}
                }
                
                if len(widgets_values) >= 3:
                    controlnet_config['parameters'] = {
                        'strength': widgets_values[0] if widgets_values[0] is not None else 1.0,
                        'start_percent': widgets_values[1] if widgets_values[1] is not None else 0.0,
                        'end_percent': widgets_values[2] if widgets_values[2] is not None else 1.0
                    }
                
                analysis['controlnet_configs'].append(controlnet_config)
            
            # 如果是SetUnionControlNetType，添加到controlnet_configs
            elif 'SetUnionControlNetType' in node_type:
                widgets_values = node.get('widgets_values', [])
                controlnet_config = {
                    'node_id': node_id,
                    'type': 'SetUnionControlNetType',
                    'name': 'ControlNet联合类型设置',
                    'parameters': {}
                }
                
                if len(widgets_values) >= 1:
                    controlnet_config['parameters'] = {
                        'union_type': widgets_values[0] if widgets_values[0] is not None else 'union'
                    }
                
                analysis['controlnet_configs'].append(controlnet_config)
            
            # 注意：ControlNet相关节点不添加到image_inputs，因为它们不是真正的图像输入节点
        
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
        
        # 检查NunchakuTextEncoderLoader节点
        elif 'NunchakuTextEncoderLoader' in node_type:
            widgets_values = node.get('widgets_values', [])
            model_loader_info = {
                'node_id': node_id,
                'type': 'NunchakuTextEncoderLoader',
                'name': '文本编码器加载器',
                'parameters': {}
            }
            
            if len(widgets_values) >= 6:
                model_loader_info['parameters'] = {
                    'model_type': widgets_values[0] if len(widgets_values) > 0 else 'flux',
                    'text_encoder1': widgets_values[1] if len(widgets_values) > 1 else 't5xxl_fp16.safetensors',
                    'text_encoder2': widgets_values[2] if len(widgets_values) > 2 else 'clip_l.safetensors',
                    't5_min_length': widgets_values[3] if len(widgets_values) > 3 else 512,
                    'use_4bit_t5': widgets_values[4] if len(widgets_values) > 4 else 'disable',
                    'int4_model': widgets_values[5] if len(widgets_values) > 5 else 'none'
                }
            
            analysis['model_loaders'].append(model_loader_info)
        
        # 检查NunchakuFluxDiTLoader节点
        elif 'NunchakuFluxDiTLoader' in node_type:
            widgets_values = node.get('widgets_values', [])
            model_loader_info = {
                'node_id': node_id,
                'type': 'NunchakuFluxDiTLoader',
                'name': 'Flux DiT模型加载器',
                'parameters': {}
            }
            
            if len(widgets_values) >= 7:
                model_loader_info['parameters'] = {
                    'model_path': widgets_values[0] if len(widgets_values) > 0 else 'svdq-int4-flux.1-dev',
                    'cache_threshold': widgets_values[1] if len(widgets_values) > 1 else 0,
                    'attention': widgets_values[2] if len(widgets_values) > 2 else 'nunchaku-fp16',
                    'cpu_offload': widgets_values[3] if len(widgets_values) > 3 else 'auto',
                    'device_id': widgets_values[4] if len(widgets_values) > 4 else 0,
                    'data_type': widgets_values[5] if len(widgets_values) > 5 else 'bfloat16',
                    'i_2_f_mode': widgets_values[6] if len(widgets_values) > 6 else 'enabled'
                }
            
            analysis['model_loaders'].append(model_loader_info)
        
        # 检查NunchakuFluxLoraLoader节点
        elif 'NunchakuFluxLoraLoader' in node_type:
            widgets_values = node.get('widgets_values', [])
            model_loader_info = {
                'node_id': node_id,
                'type': 'NunchakuFluxLoraLoader',
                'name': 'Flux LoRA加载器',
                'parameters': {}
            }
            
            if len(widgets_values) >= 2:
                model_loader_info['parameters'] = {
                    'lora_name': widgets_values[0] if len(widgets_values) > 0 else '',
                    'lora_strength': widgets_values[1] if len(widgets_values) > 1 else 1.0
                }
            
            analysis['model_loaders'].append(model_loader_info)
        
        # 检查VAELoader节点
        elif 'VAELoader' in node_type:
            widgets_values = node.get('widgets_values', [])
            model_loader_info = {
                'node_id': node_id,
                'type': 'VAELoader',
                'name': 'VAE加载器',
                'parameters': {}
            }
            
            if len(widgets_values) >= 1:
                model_loader_info['parameters'] = {
                    'vae_name': widgets_values[0] if len(widgets_values) > 0 else 'ae.safetensors'
                }
            
            analysis['model_loaders'].append(model_loader_info)
        
        # 检查DualCLIPLoader节点
        elif 'DualCLIPLoader' in node_type:
            widgets_values = node.get('widgets_values', [])
            model_loader_info = {
                'node_id': node_id,
                'type': 'DualCLIPLoader',
                'name': '双CLIP加载器',
                'parameters': {}
            }
            
            if len(widgets_values) >= 3:
                model_loader_info['parameters'] = {
                    'clip_name1': widgets_values[0] if len(widgets_values) > 0 else '',
                    'clip_name2': widgets_values[1] if len(widgets_values) > 1 else '',
                    'type': widgets_values[2] if len(widgets_values) > 2 else 'normal'
                }
            
            analysis['model_loaders'].append(model_loader_info)
        
        # 检查EmptyLatentImage节点获取默认尺寸
        elif 'EmptyLatentImage' in node_type:
            widgets_values = node.get('widgets_values', [])
            if len(widgets_values) >= 2:
                try:
                    analysis['default_values']['width'] = int(widgets_values[0]) if widgets_values[0] is not None and str(widgets_values[0]).isdigit() else widgets_values[0] if widgets_values[0] is not None else 1024
                except (ValueError, TypeError):
                    analysis['default_values']['width'] = widgets_values[0] if widgets_values[0] is not None else 1024
                
                try:
                    analysis['default_values']['height'] = int(widgets_values[1]) if widgets_values[1] is not None and str(widgets_values[1]).isdigit() else widgets_values[1] if widgets_values[1] is not None else 1024
                except (ValueError, TypeError):
                    analysis['default_values']['height'] = widgets_values[1] if widgets_values[1] is not None else 1024
        
        # 检查EmptySD3LatentImage节点获取默认尺寸（Nunchaku Flux.1使用）
        elif 'EmptySD3LatentImage' in node_type:
            widgets_values = node.get('widgets_values', [])
            if len(widgets_values) >= 2:
                try:
                    analysis['default_values']['width'] = int(widgets_values[0]) if widgets_values[0] is not None and str(widgets_values[0]).isdigit() else widgets_values[0] if widgets_values[0] is not None else 1024
                except (ValueError, TypeError):
                    analysis['default_values']['width'] = widgets_values[0] if widgets_values[0] is not None else 1024
                
                try:
                    analysis['default_values']['height'] = int(widgets_values[1]) if widgets_values[1] is not None and str(widgets_values[1]).isdigit() else widgets_values[1] if widgets_values[1] is not None else 1024
                except (ValueError, TypeError):
                    analysis['default_values']['height'] = widgets_values[1] if widgets_values[1] is not None else 1024
        
        # 检查PrimitiveNode节点获取尺寸（Nunchaku Flux.1使用）
        elif 'PrimitiveNode' in node_type:
            node_title = node.get('title', '').lower()
            widgets_values = node.get('widgets_values', [])
            
            if node_title == 'width' and len(widgets_values) >= 1:
                try:
                    analysis['default_values']['width'] = int(widgets_values[0]) if widgets_values[0] is not None and str(widgets_values[0]).isdigit() else widgets_values[0] if widgets_values[0] is not None else 1024
                except (ValueError, TypeError):
                    analysis['default_values']['width'] = widgets_values[0] if widgets_values[0] is not None else 1024
            
            elif node_title == 'height' and len(widgets_values) >= 1:
                try:
                    analysis['default_values']['height'] = int(widgets_values[0]) if widgets_values[0] is not None and str(widgets_values[0]).isdigit() else widgets_values[0] if widgets_values[0] is not None else 1024
                except (ValueError, TypeError):
                    analysis['default_values']['height'] = widgets_values[0] if widgets_values[0] is not None else 1024
        
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

if __name__ == '__main__':
    logger.info(f"启动ComfyUI Web服务...")
    logger.info(f"Workflow目录: {WORKFLOW_DIR}")
    logger.info(f"服务地址: http://{HOST}:{PORT}")
    
    # 检查workflow目录
    if not os.path.exists(WORKFLOW_DIR):
        logger.warning(f"创建workflow目录: {WORKFLOW_DIR}")
        os.makedirs(WORKFLOW_DIR, exist_ok=True)
    
    app.run(host=HOST, port=PORT, debug=True)