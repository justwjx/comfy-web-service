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
from datetime import datetime, timedelta
from flask import Flask, render_template, jsonify, request, send_from_directory
from flask_cors import CORS
from werkzeug.utils import secure_filename
from collections import defaultdict, Counter
import threading
import queue
import time
import random
import subprocess
from typing import Dict, List, Any

# 可选图像处理依赖（用于自动生成扩图掩码）
try:
    from PIL import Image, ImageDraw, ImageFilter, ImageOps
except Exception:
    Image = None
    ImageDraw = None

# 可选依赖
try:
    import psutil  # 用于CPU/内存监控
except Exception:
    psutil = None

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

# 工作流使用统计存储
BASE_DIR = os.path.dirname(__file__)
OUTPUT_DIR = os.path.join(BASE_DIR, 'output')
WORKFLOW_STATS_FILE = os.path.join(OUTPUT_DIR, 'workflow_stats.json')
LEGACY_WORKFLOW_STATS_FILE = os.path.join(BASE_DIR, 'workflow_stats.json')

def load_workflow_stats():
    """加载工作流使用统计（支持从根目录旧路径迁移到output目录）"""
    try:
        # 优先从新位置读取
        if os.path.exists(WORKFLOW_STATS_FILE):
            with open(WORKFLOW_STATS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)

        # 兼容旧位置：根目录
        if os.path.exists(LEGACY_WORKFLOW_STATS_FILE):
            with open(LEGACY_WORKFLOW_STATS_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
            # 尝试迁移到新目录
            try:
                os.makedirs(OUTPUT_DIR, exist_ok=True)
                with open(WORKFLOW_STATS_FILE, 'w', encoding='utf-8') as nf:
                    json.dump(data, nf, ensure_ascii=False, indent=2)
                # 迁移成功后删除旧文件
                try:
                    os.remove(LEGACY_WORKFLOW_STATS_FILE)
                except Exception:
                    pass
            except Exception as migrate_error:
                logger.warning(f"迁移工作流统计到输出目录失败: {migrate_error}")
            return data
    except Exception as e:
        logger.warning(f"加载工作流统计失败: {e}")
    return {'usage_count': {}, 'recent_usage': {}}

def save_workflow_stats(stats):
    """保存工作流使用统计（保存到output目录）"""
    try:
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        with open(WORKFLOW_STATS_FILE, 'w', encoding='utf-8') as f:
            json.dump(stats, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"保存工作流统计失败: {e}")

def record_workflow_usage(workflow_filename):
    """记录工作流使用"""
    stats = load_workflow_stats()
    
    # 增加使用计数
    if workflow_filename not in stats['usage_count']:
        stats['usage_count'][workflow_filename] = 0
    stats['usage_count'][workflow_filename] += 1
    
    # 记录最近使用时间
    stats['recent_usage'][workflow_filename] = datetime.now().isoformat()
    
    save_workflow_stats(stats)

# 配置
WORKFLOW_DIR = os.path.join(os.path.dirname(__file__), 'workflow')
COMFYUI_HOST = os.getenv('COMFYUI_HOST', 'localhost')
COMFYUI_PORT = int(os.getenv('COMFYUI_PORT', 8188))
COMFYUI_API_URL = f"http://{COMFYUI_HOST}:{COMFYUI_PORT}"
HOST = os.getenv('HOST', '::')  # 使用 :: 来支持IPv6
PORT = int(os.getenv('PORT', 5000))

# 全局变量存储运行状态
running_tasks = {}
task_queue = queue.Queue()

# 参数分类体系：定义不同类型参数的归属区域
PARAMETER_CATEGORIES = {
    # 核心生成参数：影响采样过程的基础参数
    'CORE_GENERATION': {'steps', 'cfg', 'sampler', 'scheduler', 'denoise', 'seed', 'guidance'},
    
    # 输出控制参数：控制生成结果的格式、尺寸等
    'OUTPUT_CONTROL': {'width', 'height', 'batch_size', 'output_format', 'size_control_mode'},
    
    # 条件控制参数：影响生成内容的条件
    'CONDITIONING': {'strength', 'control_strength', 'style_strength', 'crop'},
    
    # 模型资源参数：模型、LoRA、VAE等资源配置
    'MODEL_RESOURCES': {'model_path', 'lora_name', 'vae_name', 'clip_name', 'style_model_name'},
    
    # 高级设置参数：优化、设备等高级配置
    'ADVANCED_SETTINGS': {'attention', 'cpu_offload', 'data_type', 'device', 'cache_threshold', 'i_2_f_mode'},
    
    # 文本相关参数
    'TEXT_INPUTS': {'text', 'positive_prompt', 'negative_prompt'},
    
    # 专用节点参数：由专门区域或卡片处理
    'SPECIALIZED': {'image', 'mask', 'filename_prefix', 'upload'}
}

# 模型加载器到下游节点的参数映射配置
# 格式：{源加载器类型: {目标节点类型: {源参数: (目标参数, 目标widget_index)}}}
LOADER_PARAM_MAPPING = {
    'StyleModelLoader': {
        'StyleModelApply': {
            'strength': ('strength', 0),
            'strength_type': ('strength_type', 1)
        }
    },
    'CLIPVisionLoader': {
        'CLIPVisionEncode': {
            'crop': ('crop', 0)
        }
    },
    'NunchakuFluxDiTLoader': {
        'ModelSamplingFlux': {
            'max_shift': ('max_shift', 0),
            'base_shift': ('base_shift', 1)
        }
    }
}

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
    "CLIPVisionLoader": {"clip_name": 0},
    "StyleModelLoader": {"style_model_name": 0},
    "CLIPVisionEncode": {"crop": 0},
    "StyleModelApply": {"strength": 0, "strength_type": 1},
    # Inpaint 易用组件：ImageAndMaskResizeNode
    "ImageAndMaskResizeNode": {"width": 0, "height": 1, "resize_method": 2, "crop": 3, "mask_blur_radius": 4},
    # Outpaint 扩图节点
    # 外补画板：ComfyUI API 期待的入参名为 left/top/right/bottom/feathering
    "ImagePadForOutpaint": {"left": 0, "top": 1, "right": 2, "bottom": 3, "feathering": 4},
    # Inpaint 条件节点：显式传递 noise_mask 布尔开关
    "InpaintModelConditioning": {"noise_mask": 0},
}

def apply_loader_param_mapping(workflow_data, parameters):
    """
    通用的模型加载器参数映射处理
    根据LOADER_PARAM_MAPPING配置，将加载器面板的参数应用到对应的下游节点
    """
    # 构建节点ID到节点类型的映射
    node_type_map = {}
    for node in workflow_data.get('nodes', []):
        node_type_map[str(node.get('id', ''))] = node.get('type', '')
    
    # 构建节点连接关系映射：{下游节点ID: [上游节点ID列表]}
    connection_map = {}
    for link in workflow_data.get('links', []):
        if len(link) >= 6:
            _lid, src_id, _src_slot, dst_id, dst_slot, _t = link
            src_id, dst_id = str(src_id), str(dst_id)
            if dst_id not in connection_map:
                connection_map[dst_id] = []
            connection_map[dst_id].append(src_id)
    
    model_loaders = parameters.get('model_loaders', {})
    
    # 遍历所有加载器映射配置
    for loader_type, target_mappings in LOADER_PARAM_MAPPING.items():
        for target_node_type, param_mappings in target_mappings.items():
            # 找到该类型的目标节点
            for node in workflow_data.get('nodes', []):
                node_id = str(node.get('id', ''))
                node_type = node.get('type', '')
                
                if node_type == target_node_type:
                    # 找到连接到此节点的加载器节点
                    connected_loaders = []
                    for upstream_id in connection_map.get(node_id, []):
                        upstream_type = node_type_map.get(upstream_id, '')
                        if upstream_type == loader_type:
                            connected_loaders.append(upstream_id)
                    
                    # 应用参数映射
                    for loader_node_id in connected_loaders:
                        widgets_values = node.get('widgets_values', []) or []
                        
                        # 确保widgets_values有足够的槽位
                        max_index = max((index for _, index in param_mappings.values()), default=-1)
                        if len(widgets_values) <= max_index:
                            widgets_values = list(widgets_values) + [None] * (max_index + 1 - len(widgets_values))
                        
                        # 应用每个参数映射
                        for source_param, (target_param, target_index) in param_mappings.items():
                            param_key = f'{source_param}_{loader_node_id}'
                            if param_key in model_loaders:
                                try:
                                    value = model_loaders[param_key]
                                    # 类型转换
                                    if source_param in ['max_shift', 'base_shift', 'strength']:
                                        value = float(value)
                                    else:
                                        value = str(value)
                                    widgets_values[target_index] = value
                                except (ValueError, TypeError):
                                    pass
                        
                        node['widgets_values'] = widgets_values

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

        # 精确文件名到描述的映射（优先使用），参考 Nunchaku 官方工作流目录
        # https://nunchaku.tech/docs/ComfyUI-nunchaku/workflows/toc.html
        precise_map = {
            # Text-to-Image
            'nunchaku-flux.1-dev.json': 'FLUX.1 Dev 文生图：标准高质量生成，适合大多数通用场景，提供完整参数可调。',
            'nunchaku-flux.1-schnell.json': 'FLUX.1 Schnell 极速文生图：速度优先，几秒内出图，适合快速预览与创意草图。',
            'nunchaku-flux.1-dev-qencoder.json': 'FLUX.1 Dev + 量化编码器：显著降低显存占用，在中低显存环境下也可稳定出图。',

            # Kontext
            'nunchaku-flux.1-dev-kontext.json': 'FLUX.1 Kontext 上下文感知：对长提示词与上下文更敏感，适合结构与叙事性更强的图像。',
            'nunchaku-flux.1-kontext-dev-turbo_lora.json': 'FLUX.1 Kontext Turbo + LoRA：在保留上下文理解的同时提升速度，并支持应用风格 LoRA。',

            # ControlNets
            'nunchaku-flux.1-dev-controlnet-union-pro2.json': 'FLUX.1 + ControlNet Union Pro 2：多线索可控（边缘/深度/法线等）联合驱动，精确复现构图与细节。',
            'nunchaku-flux.1-dev-controlnet-upscaler.json': 'FLUX.1 + 可控放大：在放大细节的同时维持可控性，适合高清修饰与印刷输出前处理。',

            # PuLID
            'nunchaku-flux.1-dev-pulid.json': 'FLUX.1 + PuLID 人像一致性：在多张图中保持身份一致与五官稳定，适合角色/证件/品牌人像。',

            # Redux
            'nunchaku-flux.1-redux-dev.json': 'FLUX.1 Redux 图像再创作：对已有图像进行风格迁移/再渲染/结构保留的二次创作。',

            # Canny
            'nunchaku-flux.1-canny.json': 'FLUX.1 Canny 边缘控制：用线稿/边缘图约束构图，精准复现轮廓与透视。',
            'nunchaku-flux.1-canny-lora.json': 'FLUX.1 Canny + LoRA：在边缘可控的基础上叠加风格 LoRA，快速得到特定风格成品。',

            # Depth
            'nunchaku-flux.1-depth.json': 'FLUX.1 Depth 深度控制：以深度图约束三维结构与景深关系，构图更稳定。',
            'nunchaku-flux.1-depth-lora.json': 'FLUX.1 Depth + LoRA：结合深度控制与风格 LoRA，兼顾结构稳定与风格统一。',

            # Fill / Inpaint
            'nunchaku-flux.1-fill.json': 'FLUX.1 Fill 图像补全/修复：对遮罩区域进行智能补全，适合擦除/扩图/局部改写。',
            'nunchaku-flux.1-fill-removalv2.json': 'FLUX.1 Fill + Removal V2：在补全基础上强化移除能力，去物/去水印更干净自然。',
        }

        if filename_lower in precise_map:
            return precise_map[filename_lower]
        
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

    def get_available_node_types(self):
        """获取后端ComfyUI可用的节点类型集合（最佳努力）。

        优先尝试 /object_info（部分版本提供），失败则返回 None 表示无法预检。
        返回: set[str] | None
        """
        try:
            # 尝试获取所有节点定义
            resp = requests.get(f"{COMFYUI_API_URL}/object_info", timeout=5)
            if resp.status_code == 200:
                data = resp.json()
                # 常见格式：{"nodes": {"ClassName": {...}, ...}} 或直接 {"ClassName": {...}}
                if isinstance(data, dict):
                    if 'nodes' in data and isinstance(data['nodes'], dict):
                        return set(data['nodes'].keys())
                    else:
                        # 直接是节点映射
                        return set(k for k, v in data.items() if isinstance(v, dict))
            return None
        except Exception as e:
            logger.debug(f"获取可用节点列表失败（将跳过预检）: {e}")
            return None
    
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
            
            # 预计算节点顺序映射与节点元信息，供更精准进度与可读状态显示
            try:
                nodes = workflow_data.get('nodes', [])
                total_nodes = len(nodes)
                node_index_map = {str(n.get('id')): i for i, n in enumerate(nodes)}
                # 节点可读标签映射：id -> "类型 - 标题"/"类型"
                node_meta_map = {}
                # 按顺序的节点ID列表
                node_order_list = []
                for n in nodes:
                    nid = str(n.get('id'))
                    ntype = n.get('type') or n.get('class_type') or 'Node'
                    ntitle = n.get('title') or ''
                    label = f"{ntype} - {ntitle}".strip(' -')
                    node_meta_map[nid] = label
                    node_order_list.append(nid)
                # 根据 index 排序确保顺序一致
                node_order_list.sort(key=lambda nid: node_index_map.get(nid, 0))
            except Exception:
                total_nodes = 0
                node_index_map = {}
                node_meta_map = {}

            # 更新任务状态
            running_tasks[task_id] = {
                'status': 'running',
                'filename': filename,
                'workflow_filename': filename,  # 添加工作流文件名
                'parameters': parameters,  # 添加参数
                'start_time': datetime.now().isoformat(),
                'progress': 0,
                'prompt_id': None,
                'total_nodes': total_nodes,
                'node_index_map': node_index_map,
                'node_meta_map': node_meta_map,
                'node_order_list': node_order_list,
                'current_node_id': None,
                'current_node_label': None
            }
            
            # 修改工作流参数和图像输入
            modified_workflow = self.modify_workflow_with_parameters_and_images(workflow_data, parameters, selected_images)
            
            # 检查修改是否成功
            if modified_workflow is None:
                error_msg = "必选图像输入节点没有提供图像，任务无法执行"
                logger.error(error_msg)
                running_tasks[task_id].update({
                    'status': 'failed',
                    'end_time': datetime.now().isoformat(),
                    'error': error_msg,
                    'message': '任务无法执行：缺少必选图像输入'
                })
                return {'success': False, 'error': error_msg}
            
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
            
            # 提交前进行后端节点可用性预检（若可用）
            try:
                # 收集此次提交所需的节点类型
                required_types = set()
                for _nid, _n in api_workflow.get('prompt', {}).items():
                    ctype = _n.get('class_type')
                    if isinstance(ctype, str) and ctype:
                        required_types.add(ctype)

                available_types = self.get_available_node_types()
                if isinstance(available_types, set) and required_types:
                    missing = sorted(list(required_types - available_types))
                    if missing:
                        error_msg = (
                            "后端ComfyUI缺少以下节点类型: " + ", ".join(missing) +
                            f"。请确认目标实例({COMFYUI_API_URL})已安装相应自定义节点，或检查 COMFYUI_HOST/COMFYUI_PORT 是否指向正确的实例。"
                        )
                        logger.error(error_msg)
                        running_tasks[task_id].update({
                            'status': 'failed',
                            'end_time': datetime.now().isoformat(),
                            'error': error_msg,
                            'message': '任务提交前检查失败：后端缺少节点'
                        })
                        return {'success': False, 'error': error_msg}
            except Exception as _e:
                logger.debug(f"预检节点可用性时发生非致命错误，继续提交: {_e}")

            # 发送到ComfyUI API（若预检通过或不可用）
            logger.info(f"发送修改后的workflow到ComfyUI: {filename}")
            
            # 更新任务状态为正在提交
            running_tasks[task_id].update({
                'status': 'submitting',
                'progress': 5,
                'message': '正在提交任务到ComfyUI...'
            })
            
            response = requests.post(
                f"{COMFYUI_API_URL}/prompt", 
                json=prompt_data,
                timeout=30
            )
            
            if response.status_code == 200:
                result_data = response.json()
                prompt_id = result_data.get('prompt_id')
                
                if not prompt_id:
                    error_msg = "ComfyUI返回的响应中没有prompt_id"
                    logger.error(error_msg)
                    running_tasks[task_id].update({
                        'status': 'failed',
                        'end_time': datetime.now().isoformat(),
                        'error': error_msg,
                        'message': '提交失败：未获得任务ID'
                    })
                    return {'success': False, 'error': error_msg}
                
                running_tasks[task_id].update({
                    'prompt_id': prompt_id,
                    'client_id': client_id,
                    'status': 'submitted',
                    'progress': 10,
                    'message': '任务已提交，等待执行...'
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
                    'error': error_msg,
                    'message': f'提交失败：HTTP {response.status_code}'
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
    
    def apply_output_settings(self, workflow_data, parameters):
        """应用输出设置参数到PrimitiveNode"""
        output_settings = parameters.get('output_settings', {})
        if not output_settings:
            return
            
        # 查找width和height的PrimitiveNode
        for node in workflow_data.get('nodes', []):
            if node.get('type') == 'PrimitiveNode':
                title = node.get('title', '').lower()
                widgets_values = node.get('widgets_values', [])
                
                if title == 'width' and 'output_width' in output_settings:
                    if len(widgets_values) >= 1:
                        widgets_values[0] = int(output_settings['output_width'])
                    if len(widgets_values) >= 2 and 'size_control_mode' in output_settings:
                        widgets_values[1] = output_settings['size_control_mode']
                    node['widgets_values'] = widgets_values
                    
                elif title == 'height' and 'output_height' in output_settings:
                    if len(widgets_values) >= 1:
                        widgets_values[0] = int(output_settings['output_height'])
                    if len(widgets_values) >= 2 and 'size_control_mode' in output_settings:
                        widgets_values[1] = output_settings['size_control_mode']
                    node['widgets_values'] = widgets_values
                    
            # 处理batch_size参数
            elif 'batch_size' in output_settings:
                node_type = node.get('type', '')
                if node_type in WIDGET_INDEX_MAP and 'batch_size' in WIDGET_INDEX_MAP[node_type]:
                    widgets_values = node.get('widgets_values', [])
                    batch_idx = WIDGET_INDEX_MAP[node_type]['batch_size']
                    if len(widgets_values) > batch_idx:
                        widgets_values[batch_idx] = int(output_settings['batch_size'])
                        node['widgets_values'] = widgets_values

    def modify_workflow_with_parameters(self, workflow_data, parameters):
        """根据用户参数修改工作流"""
        return self.modify_workflow_with_parameters_and_images(workflow_data, parameters, {})
    
    def modify_workflow_with_parameters_and_images(self, workflow_data, parameters, selected_images):
        """根据用户参数和图像输入修改工作流（UI格式）"""
        try:
            # 在处理节点之前，先应用通用的模型加载器参数映射
            apply_loader_param_mapping(workflow_data, parameters)
            
            # 处理输出设置参数
            self.apply_output_settings(workflow_data, parameters)
            
            nodes = workflow_data.get('nodes', [])
            modified_nodes = []
            auto_outpaint_mask = bool(parameters.get('auto_outpaint_mask', True))
            # 前端遮罩编辑器保存的遮罩（outputs/uploaded/xxx.png）。若提供则优先使用该遮罩，且仍沿用 Fill 工作流链路。
            mask_image_from_editor = parameters.get('mask_image')
            # 记录第一个用户实际选择的图像文件，供可选节点缺省时使用占位
            fallback_image_filename = None
            logger.info(f"开始处理工作流，selected_images: {selected_images}")
            if selected_images:
                # 取第一个有效的上传文件名
                first_key = next(iter(selected_images))
                fallback_path = selected_images[first_key].get('path', '')
                if fallback_path:
                    # 使用 ComfyUI input 标记，保证校验解析正确
                    fallback_image_filename = f"{os.path.basename(fallback_path)} [input]"
            else:
                logger.info("没有选择任何图像，将检查必选节点")
            
            # 记录尺寸，供自动掩码使用（仅Fill工作流使用）
            target_width = None
            target_height = None
            has_outpaint_node = False

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
                    # 修改 FluxGuidance 参数（guidance 单独管理，不再复用 cfg 名称）
                    widgets_values = modified_node.get('widgets_values', [])
                    if 'guidance' in parameters and len(widgets_values) > 0:
                        try:
                            widgets_values[0] = float(parameters['guidance'])
                        except (ValueError, TypeError):
                            widgets_values[0] = 7.0
                    modified_node['widgets_values'] = widgets_values

                elif 'KSampler' in node_type:
                    # 修改 KSampler 参数
                    widgets_values = modified_node.get('widgets_values', [])
                    # 确保长度至少为7
                    if len(widgets_values) < 7:
                        widgets_values = (widgets_values + [None] * 7)[:7]
                    try:
                        if 'seed' in parameters and parameters['seed'] not in (None, ''):
                            widgets_values[0] = int(parameters['seed'])
                    except (ValueError, TypeError):
                        pass
                    try:
                        if 'steps' in parameters and parameters['steps'] not in (None, ''):
                            widgets_values[2] = int(parameters['steps'])
                    except (ValueError, TypeError):
                        pass
                    try:
                        if 'cfg' in parameters and parameters['cfg'] not in (None, ''):
                            widgets_values[3] = float(parameters['cfg'])
                    except (ValueError, TypeError):
                        pass
                    if 'sampler' in parameters and parameters['sampler']:
                        widgets_values[4] = parameters['sampler']
                    if 'scheduler' in parameters and parameters['scheduler']:
                        widgets_values[5] = parameters['scheduler']
                    try:
                        if 'denoise' in parameters and parameters['denoise'] not in (None, ''):
                            widgets_values[6] = float(parameters['denoise'])
                    except (ValueError, TypeError):
                        pass
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
                    modified_node['widgets_values'] = widgets_values

                elif 'InpaintModelConditioning' in node_type:
                    # 噪声掩码：优先采用用户参数；若无且为 Fill（非 Outpaint）自动开启
                    widgets_values = modified_node.get('widgets_values', [])
                    if 'noise_mask' in parameters:
                        try:
                            val = bool(parameters.get('noise_mask'))
                            if not widgets_values:
                                widgets_values = [val]
                            else:
                                widgets_values[0] = val
                        except Exception:
                            pass
                    elif auto_outpaint_mask and not has_outpaint_node:
                        if not widgets_values:
                            widgets_values = [True]
                        else:
                            try:
                                widgets_values[0] = True
                            except Exception:
                                widgets_values = [True]
                    modified_node['widgets_values'] = widgets_values

                elif 'ImagePadForOutpaint' in node_type:
                    widgets_values = modified_node.get('widgets_values', [])
                    if len(widgets_values) < 5:
                        widgets_values = (widgets_values + [0, 0, 0, 0, 24])[:5]
                    try:
                        if parameters.get('outpaint_left') is not None:
                            widgets_values[0] = int(parameters['outpaint_left'])
                        if parameters.get('outpaint_right') is not None:
                            widgets_values[1] = int(parameters['outpaint_right'])
                        if parameters.get('outpaint_top') is not None:
                            widgets_values[2] = int(parameters['outpaint_top'])
                        if parameters.get('outpaint_bottom') is not None:
                            widgets_values[3] = int(parameters['outpaint_bottom'])
                        if parameters.get('outpaint_feather') is not None:
                            widgets_values[4] = int(parameters['outpaint_feather'])
                    except Exception:
                        pass
                    modified_node['widgets_values'] = widgets_values
                    has_outpaint_node = True
                
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
                
                elif 'SaveImage' in node_type:
                    # 修改SaveImage节点的filename_prefix，避免ComfyUI内部缓存
                    widgets_values = modified_node.get('widgets_values', [])
                    if len(widgets_values) > 0:
                        # 生成唯一的文件名前缀，包含时间戳和随机数
                        import time
                        timestamp = int(time.time())
                        random_suffix = random.randint(1000, 9999)
                        unique_prefix = f"ComfyUI_{timestamp}_{random_suffix}"
                        widgets_values[0] = unique_prefix
                        logger.info(f"为SaveImage节点 {node_id} 设置唯一文件名前缀: {unique_prefix}")
                    modified_node['widgets_values'] = widgets_values

                elif 'ImageAndMaskResizeNode' in node_type:
                    # 覆盖并记录目标尺寸与缩放策略（来自参数 → widgets），否则保持JSON默认
                    widgets_values = modified_node.get('widgets_values', [])
                    # 确保长度至少为5
                    while len(widgets_values) < 5:
                        widgets_values.append(None)
                    # 应用前端传入的 width/height（若提供）
                    try:
                        if 'width' in parameters and parameters['width']:
                            widgets_values[0] = int(parameters['width'])
                        if 'height' in parameters and parameters['height']:
                            widgets_values[1] = int(parameters['height'])
                    except Exception:
                        pass
                    # 应用前端传入的 resize_method/crop/mask_blur_radius（若提供）
                    try:
                        if parameters.get('resize_method'):
                            widgets_values[2] = parameters['resize_method']
                        if parameters.get('crop'):
                            widgets_values[3] = parameters['crop']
                        if parameters.get('mask_blur_radius') is not None and parameters.get('mask_blur_radius') != '':
                            widgets_values[4] = int(parameters['mask_blur_radius'])
                    except Exception:
                        pass
                    # 记录用于自动掩码
                # Outpaint：ImagePadForOutpaint 参数注入
                elif 'ImagePadForOutpaint' in node_type:
                    widgets_values = modified_node.get('widgets_values', [])
                    # 确保长度至少为5
                    if len(widgets_values) < 5:
                        widgets_values = (widgets_values + [0, 0, 0, 0, 24])[:5]
                    try:
                        # 原生顺序：左、上、右、下、羽化
                        if parameters.get('outpaint_left') is not None:
                            widgets_values[0] = int(parameters['outpaint_left'])
                        if parameters.get('outpaint_top') is not None:
                            widgets_values[1] = int(parameters['outpaint_top'])
                        if parameters.get('outpaint_right') is not None:
                            widgets_values[2] = int(parameters['outpaint_right'])
                        if parameters.get('outpaint_bottom') is not None:
                            widgets_values[3] = int(parameters['outpaint_bottom'])
                        if parameters.get('outpaint_feather') is not None:
                            widgets_values[4] = int(parameters['outpaint_feather'])
                    except Exception:
                        pass
                    modified_node['widgets_values'] = widgets_values
                    has_outpaint_node = True
                    try:
                        target_width = int(widgets_values[0])
                        target_height = int(widgets_values[1])
                    except Exception:
                        target_width = target_width or None
                        target_height = target_height or None
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
                            # 归一化前端传入的取值，避免校验失败
                            raw_value = str(model_loaders[param_key]).lower()
                            normalization_map = {
                                'enabled': 'enable',
                                'disabled': 'disable'
                            }
                            widgets_values[3] = normalization_map.get(raw_value, raw_value)
                        
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
                        
                        # I2F模式（保持原值，部分节点允许值为 enabled/disabled）
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
                        
                        # CLIP类型 - 验证类型值是否有效
                        param_key = f'clip_type_{node_id}'
                        if param_key in model_loaders and len(widgets_values) > 2:
                            clip_type = model_loaders[param_key]
                            # 验证类型值是否在允许的范围内
                            valid_types = ['sdxl', 'sd3', 'flux', 'hunyuan_video', 'hidream']
                            if clip_type in valid_types:
                                widgets_values[2] = clip_type
                            else:
                                # 如果类型无效，使用默认值 'flux'
                                logger.warning(f"无效的CLIP类型 '{clip_type}'，使用默认值 'flux'")
                                widgets_values[2] = 'flux'
                    
                    modified_node['widgets_values'] = widgets_values

                elif 'LoraLoader' in node_type:
                    widgets_values = modified_node.get('widgets_values', [])
                    model_loaders = parameters.get('model_loaders', {})
                    if len(widgets_values) >= 2:
                        # LoRA 名称
                        param_key = f'lora_name_{node_id}'
                        if param_key in model_loaders:
                            widgets_values[0] = model_loaders[param_key]
                        # LoRA 强度（通用LoraLoader字段名为 strength_model）
                        param_key = f'strength_model_{node_id}'
                        if param_key in model_loaders:
                            try:
                                v = float(model_loaders[param_key])
                                widgets_values[1] = v
                            except (ValueError, TypeError):
                                pass
                    modified_node['widgets_values'] = widgets_values

                elif 'CheckpointLoaderSimple' in node_type:
                    widgets_values = modified_node.get('widgets_values', [])
                    model_loaders = parameters.get('model_loaders', {})
                    if len(widgets_values) >= 1:
                        param_key = f'ckpt_name_{node_id}'
                        if param_key in model_loaders:
                            widgets_values[0] = model_loaders[param_key]
                    modified_node['widgets_values'] = widgets_values

                elif 'CLIPVisionLoader' in node_type:
                    # 允许前端覆盖视觉CLIP模型名称
                    widgets_values = modified_node.get('widgets_values', [])
                    model_loaders = parameters.get('model_loaders', {})
                    if len(widgets_values) >= 1:
                        param_key = f'clip_name_{node_id}'
                        if param_key in model_loaders:
                            widgets_values[0] = model_loaders[param_key]
                    # 透传前端可能提供的 crop（与 CLIPVisionEncode 对齐）
                    extra_crop_key = f'crop_{node_id}'
                    if extra_crop_key in model_loaders:
                        # 如果该 Loader 节点没有 crop 的 widgets_values 槽位，则忽略，仅供 encode 节点使用
                        pass
                    modified_node['widgets_values'] = widgets_values

                elif 'StyleModelLoader' in node_type:
                    # 允许前端覆盖风格模型名称
                    widgets_values = modified_node.get('widgets_values', [])
                    model_loaders = parameters.get('model_loaders', {})
                    if len(widgets_values) >= 1:
                        param_key = f'style_model_name_{node_id}'
                        if param_key in model_loaders:
                            widgets_values[0] = model_loaders[param_key]
                    # Style strength 与 type 实际应用在 StyleModelApply 节点，这里仅保留供后续节点读取
                    # 不修改 widgets_values 长度避免索引错位
                    modified_node['widgets_values'] = widgets_values

                # 注意：模型加载器参数映射现在由通用函数 apply_loader_param_mapping 处理
                # 原有的 StyleModelApply、CLIPVisionEncode、ModelSamplingFlux 特定处理逻辑已移除
                
                # 通用兜底：任意包含 Loader 的节点作为潜在模型加载器
                elif 'Loader' in node_type:
                    widgets_values = modified_node.get('widgets_values', [])
                    model_loaders = parameters.get('model_loaders', {})
                    widget_inputs = [
                        (inp.get('widget', {}) or {}).get('name')
                        for inp in node.get('inputs', [])
                        if isinstance(inp, dict) and 'widget' in inp and isinstance(inp.get('widget'), dict)
                    ]
                    if isinstance(widgets_values, list) and widget_inputs:
                        for idx, pname in enumerate(widget_inputs):
                            if not pname:
                                continue
                            key = f"{pname}_{node_id}"
                            if key in model_loaders and idx < len(widgets_values):
                                widgets_values[idx] = model_loaders[key]
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
                        image_source = image_info.get('source', 'uploaded')
                        logger.info(f"LoadImage节点 {node_id} 有选择的图像: {image_path}, 来源: {image_source}")
                        
                        # 构建完整的图像路径
                        output_dir = os.path.join(os.path.dirname(__file__), 'outputs')
                        
                        # 根据图片来源确定源文件路径
                        if image_source == 'uploaded':
                            # 上传的图片在 outputs/uploaded/ 目录
                            full_image_path = os.path.join(output_dir, image_path)
                        else:
                            # 生成的图片在 outputs/ 根目录
                            full_image_path = os.path.join(output_dir, image_path)
                        
                        if os.path.exists(full_image_path):
                            # 将图片复制到ComfyUI的input目录
                            comfyui_input_dir = '/home/wjx/ComfyUI/input'
                            
                            # 确保ComfyUI input目录存在
                            if not os.path.exists(comfyui_input_dir):
                                logger.error(f"ComfyUI input目录不存在: {comfyui_input_dir}")
                                continue
                            
                            # 智能文件名管理：避免重复复制相同文件
                            original_filename = os.path.basename(image_path)
                            name, ext = os.path.splitext(original_filename)
                            
                            # 检查文件是否已经存在于ComfyUI input目录
                            comfyui_image_path = os.path.join(comfyui_input_dir, original_filename)
                            final_filename = original_filename
                            
                            # 如果文件不存在，或者文件内容不同，才复制
                            need_copy = True
                            if os.path.exists(comfyui_image_path):
                                # 比较文件大小和修改时间
                                source_stat = os.stat(full_image_path)
                                target_stat = os.stat(comfyui_image_path)
                                if (source_stat.st_size == target_stat.st_size and 
                                    abs(source_stat.st_mtime - target_stat.st_mtime) < 1):
                                    need_copy = False
                                    logger.info(f"文件已存在且相同，跳过复制: {original_filename}")
                                else:
                                    # 文件不同，生成新的唯一文件名
                                    import time
                                    timestamp = int(time.time())
                                    final_filename = f"{name}_{timestamp}{ext}"
                                    comfyui_image_path = os.path.join(comfyui_input_dir, final_filename)
                            
                            if need_copy:
                                try:
                                    import shutil
                                    
                                    # 复制文件到ComfyUI input目录
                                    shutil.copy2(full_image_path, comfyui_image_path)
                                    logger.info(f"图片已复制到ComfyUI input目录: {comfyui_image_path}")
                                    
                                except Exception as e:
                                    logger.error(f"处理图片到ComfyUI input目录失败: {e}")
                                    # 如果复制失败，尝试使用原始文件名
                                    final_filename = original_filename
                            
                            # 修改图像路径 - UI格式中widgets_values包含图像文件名
                            widgets_values = modified_node.get('widgets_values', [])
                            if len(widgets_values) > 0:
                                widgets_values[0] = final_filename
                                modified_node['widgets_values'] = widgets_values
                                logger.info(f"设置LoadImage图像输入 {node_id}: {final_filename}")
                        else:
                            logger.warning(f"LoadImage图像文件不存在: {full_image_path}")
                    # 自动扩图掩码：若开启、且该节点输出有 MASK 且未提供掩码，则记录原图尺寸用于后续生成掩码
                    try:
                        if auto_outpaint_mask and any(o.get('type') == 'MASK' for o in (node.get('outputs') or [])):
                            # 读取原图尺寸
                            img_path = None
                            wv = modified_node.get('widgets_values', [])
                            if wv and isinstance(wv[0], str):
                                img_path = wv[0].replace(' [input]', '')
                            if img_path:
                                input_dir = '/home/wjx/ComfyUI/input'
                                abs_img = os.path.join(input_dir, os.path.basename(img_path))
                                if os.path.exists(abs_img) and Image is not None:
                                    with Image.open(abs_img) as im:
                                        orig_w, orig_h = im.size
                                    # 若目标尺寸更大且未显式提供掩码，则标记需要自动生成
                                    modified_node.setdefault('_auto_mask_meta', {})
                                    modified_node['_auto_mask_meta']['orig_w'] = orig_w
                                    modified_node['_auto_mask_meta']['orig_h'] = orig_h
                    except Exception as _e:
                        logger.debug(f"自动扩图掩码尺寸预读失败: {_e}")
                    else:
                        # 未为该 LoadImage 节点显式提供图片，尝试使用任意可用的已选图片作为兜底
                        fallback_info = None
                        # 仅在“全局完全未选择任何图片”时，才启用兜底，避免误用
                        if isinstance(selected_images, dict) and len(selected_images) == 0:
                            try:
                                fallback_key = next(iter(selected_images.keys()))
                                fallback_info = selected_images.get(fallback_key)
                            except Exception:
                                fallback_info = None
                        if fallback_info:
                            fb_path = fallback_info.get('path', '')
                            fb_source = fallback_info.get('source', 'uploaded')
                            logger.info(f"LoadImage节点 {node_id} 无显式输入，回退使用已选图片: {fb_path} (来源: {fb_source})")
                            output_dir = os.path.join(os.path.dirname(__file__), 'outputs')
                            full_image_path = os.path.join(output_dir, fb_path)
                            if os.path.exists(full_image_path):
                                comfyui_input_dir = '/home/wjx/ComfyUI/input'
                                if os.path.exists(comfyui_input_dir):
                                    try:
                                        import shutil, time
                                        original_filename = os.path.basename(fb_path)
                                        name, ext = os.path.splitext(original_filename)
                                        comfyui_image_path = os.path.join(comfyui_input_dir, original_filename)
                                        final_filename = original_filename
                                        need_copy = True
                                        if os.path.exists(comfyui_image_path):
                                            source_stat = os.stat(full_image_path)
                                            target_stat = os.stat(comfyui_image_path)
                                            if (source_stat.st_size == target_stat.st_size and 
                                                abs(source_stat.st_mtime - target_stat.st_mtime) < 1):
                                                need_copy = False
                                            else:
                                                ts = int(time.time())
                                                final_filename = f"{name}_{ts}{ext}"
                                                comfyui_image_path = os.path.join(comfyui_input_dir, final_filename)
                                        if need_copy:
                                            shutil.copy2(full_image_path, comfyui_image_path)
                                        widgets_values = modified_node.get('widgets_values', [])
                                        if len(widgets_values) > 0:
                                            widgets_values[0] = final_filename
                                            modified_node['widgets_values'] = widgets_values
                                            logger.info(f"兜底设置LoadImage图像输入 {node_id}: {final_filename}")
                                    except Exception as e:
                                        logger.error(f"LoadImage兜底设置失败: {e}")
                                else:
                                    logger.error(f"ComfyUI input目录不存在: {comfyui_input_dir}")
                            else:
                                logger.warning(f"LoadImage兜底文件不存在: {full_image_path}")
                        else:
                            # 顶部统一覆盖：若无显式选择，则保持原有 widgets，不再生成兜底，避免误连
                            logger.info(f"LoadImage 节点 {node_id} 未选择图片，保持原配置")
                
                # 处理LoadImageOutput节点（Kontext工作流中的图像输入）
                elif 'LoadImageOutput' in node_type:
                    logger.info(f"处理LoadImageOutput节点 {node_id}，selected_images: {selected_images}")
                    if str(node_id) in selected_images:
                        image_info = selected_images[str(node_id)]
                        image_path = image_info.get('path', '')
                        image_source = image_info.get('source', 'uploaded')
                        logger.info(f"LoadImageOutput节点 {node_id} 有选择的图像: {image_path}, 来源: {image_source}")
                        
                        # 构建完整的图像路径
                        output_dir = os.path.join(os.path.dirname(__file__), 'outputs')
                        
                        # 根据图片来源确定源文件路径
                        if image_source == 'uploaded':
                            # 上传的图片在 outputs/uploaded/ 目录
                            full_image_path = os.path.join(output_dir, image_path)
                        else:
                            # 生成的图片在 outputs/ 根目录
                            full_image_path = os.path.join(output_dir, image_path)
                        
                        if os.path.exists(full_image_path):
                            # 将图片复制到ComfyUI的input目录（智能复制）
                            comfyui_input_dir = '/home/wjx/ComfyUI/input'
                            
                            # 确保ComfyUI input目录存在
                            if not os.path.exists(comfyui_input_dir):
                                logger.error(f"ComfyUI input目录不存在: {comfyui_input_dir}")
                                continue
                            
                            # 智能文件名管理：避免重复复制相同文件
                            original_filename = os.path.basename(image_path)
                            name, ext = os.path.splitext(original_filename)
                            
                            # 检查文件是否已经存在于ComfyUI input目录
                            comfyui_image_path = os.path.join(comfyui_input_dir, original_filename)
                            final_filename = original_filename
                            
                            # 如果文件不存在，或者文件内容不同，才复制
                            need_copy = True
                            if os.path.exists(comfyui_image_path):
                                # 比较文件大小和修改时间
                                source_stat = os.stat(full_image_path)
                                target_stat = os.stat(comfyui_image_path)
                                if (source_stat.st_size == target_stat.st_size and 
                                    abs(source_stat.st_mtime - target_stat.st_mtime) < 1):
                                    need_copy = False
                                    logger.info(f"文件已存在且相同，跳过复制: {original_filename}")
                                else:
                                    # 文件不同，生成新的唯一文件名
                                    import time
                                    timestamp = int(time.time())
                                    final_filename = f"{name}_{timestamp}{ext}"
                                    comfyui_image_path = os.path.join(comfyui_input_dir, final_filename)
                            
                            if need_copy:
                                try:
                                    import shutil
                                    
                                    # 复制文件到ComfyUI input目录
                                    shutil.copy2(full_image_path, comfyui_image_path)
                                    logger.info(f"图片已复制到ComfyUI input目录: {comfyui_image_path}")
                                    
                                except Exception as e:
                                    logger.error(f"处理图片到ComfyUI input目录失败: {e}")
                                    # 如果复制失败，尝试使用原始文件名
                                    final_filename = original_filename
                            
                            # 修改图像路径 - UI格式中widgets_values包含图像文件名
                            widgets_values = modified_node.get('widgets_values', [])
                            if len(widgets_values) > 0:
                                # 使用带有 [input] 标记的文件名
                                widgets_values[0] = f"{final_filename} [input]"
                                modified_node['widgets_values'] = widgets_values
                                logger.info(f"设置LoadImageOutput图像输入 {node_id}: {final_filename} [input]")
                        else:
                            logger.warning(f"LoadImageOutput图像文件不存在: {full_image_path}")
                    else:
                            # 顶部统一覆盖：未选择则保持，不再强判必需/禁用，交由用户在顶层选择
                            logger.info(f"LoadImageOutput 节点 {node_id} 未选择图片，保持原配置")

                # 通用节点参数注入（兜底）：来自前端 node_generic_params 的键 "nodeId:widgetIndex"
                try:
                    generic_params = parameters.get('node_generic_params') or {}
                    if isinstance(generic_params, dict):
                        wv = modified_node.get('widgets_values', [])
                        if not isinstance(wv, list):
                            wv = []
                        for key, val in generic_params.items():
                            try:
                                nid_str, idx_str = str(key).split(':', 1)
                            except ValueError:
                                continue
                            if str(nid_str) != str(node_id):
                                continue
                            try:
                                idx = int(idx_str)
                            except Exception:
                                continue
                            # 扩容到可写入位置
                            if idx >= 0 and idx >= len(wv):
                                wv.extend([None] * (idx + 1 - len(wv)))
                            if idx >= 0:
                                orig = wv[idx]
                                new_val = val
                                # 类型感知转换（若有原值则按原值类型转换）
                                try:
                                    if isinstance(orig, bool):
                                        new_val = (str(val).lower() in ('1','true','yes','on')) if isinstance(val, str) else bool(val)
                                    elif isinstance(orig, int):
                                        new_val = int(float(val))
                                    elif isinstance(orig, float):
                                        new_val = float(val)
                                except Exception:
                                    pass
                                wv[idx] = new_val
                        modified_node['widgets_values'] = wv
                except Exception as _e:
                    logger.debug(f"通用参数注入失败 node#{node_id}: {_e}")

                modified_nodes.append(modified_node)
            
            # 自动扩图掩码：仅在Fill类型（无ImagePadForOutpaint）工作流启用
            if (auto_outpaint_mask or mask_image_from_editor) and Image is not None and not has_outpaint_node:
                try:
                    # 查找 LoadImage 节点（带 _auto_mask_meta）与 Resize 节点及其 mask 输入链接
                    resize_node = next((n for n in modified_nodes if 'ImageAndMaskResizeNode' in n.get('type','')), None)
                    load_node = next((n for n in modified_nodes if n.get('_auto_mask_meta')), None)
                    links = workflow_data.get('links', [])
                    if resize_node and load_node and isinstance(links, list):
                        meta = load_node['_auto_mask_meta']
                        orig_w, orig_h = meta.get('orig_w'), meta.get('orig_h')
                        # 是否需要创建/替换遮罩节点：
                        need_mask_node = bool(mask_image_from_editor) or (
                            orig_w and orig_h and target_width and target_height and (target_width > orig_w or target_height > orig_h)
                        )
                        if need_mask_node:
                            input_dir = '/home/wjx/ComfyUI/input'
                            os.makedirs(input_dir, exist_ok=True)
                            if mask_image_from_editor:
                                # 将编辑器遮罩复制到 ComfyUI/input
                                try:
                                    # 前端上传到 outputs/uploaded/xxx，所以这里需要解析 path
                                    rel_path = mask_image_from_editor.replace(' [input]', '')
                                    if rel_path.startswith('masks/'):
                                        src_mask = os.path.join(os.path.dirname(__file__), 'outputs', rel_path)
                                    elif rel_path.startswith('uploaded/'):
                                        src_mask = os.path.join(os.path.dirname(__file__), 'outputs', rel_path)
                                    else:
                                        src_mask = os.path.join(os.path.dirname(__file__), 'outputs', mask_image_from_editor)
                                    mask_filename = os.path.basename(src_mask)
                                    abs_mask = os.path.join(input_dir, mask_filename)
                                    import shutil
                                    if os.path.exists(src_mask) and os.path.abspath(src_mask) != os.path.abspath(abs_mask):
                                        shutil.copy2(src_mask, abs_mask)
                                except Exception as _e:
                                    logger.debug(f"复制遮罩到输入目录失败: {_e}")
                            else:
                                # 自动生成扩图遮罩
                                # 生成掩码图片（RGBA Alpha）：
                                #  - 外圈：alpha=0（透明 → 需要重建）
                                #  - 原图区域：alpha=255（不透明 → 保留）
                                offset_x = (target_width - orig_w) // 2
                                offset_y = (target_height - orig_h) // 2
                                mask_rgba = Image.new('RGBA', (target_width, target_height), color=(0, 0, 0, 0))
                                draw = ImageDraw.Draw(mask_rgba)
                                draw.rectangle([offset_x, offset_y, offset_x + orig_w - 1, offset_y + orig_h - 1], fill=(0, 0, 0, 255))
                                try:
                                    blur_param = 24
                                    try:
                                        if isinstance(parameters.get('mask_blur_radius'), (int, float)):
                                            blur_param = max(0, min(int(parameters.get('mask_blur_radius')), 128))
                                    except Exception:
                                        pass
                                    alpha = mask_rgba.split()[-1]
                                    alpha = alpha.filter(ImageFilter.GaussianBlur(radius=max(6, blur_param // 2)))
                                    mask_rgba.putalpha(alpha)
                                except Exception:
                                    pass
                                mask_filename = f"auto_outpaint_mask_{target_width}x{target_height}.png"
                                abs_mask = os.path.join(input_dir, mask_filename)
                                mask_rgba.save(abs_mask)

                            # 生成预填充（pad）后的目标尺寸图像，避免被 Resize 节点裁剪
                            try:
                                # 读取当前 LoadImage 使用的源文件名
                                wv = load_node.get('widgets_values', [])
                                src_name = None
                                if wv and isinstance(wv[0], str):
                                    src_name = wv[0].replace(' [input]', '')
                                if src_name:
                                    abs_src = os.path.join(input_dir, os.path.basename(src_name))
                                    if os.path.exists(abs_src):
                                        with Image.open(abs_src) as simg:
                                            # 建立与原图相同mode的画布；若非RGB则转RGB
                                            base_mode = 'RGB'
                                            try:
                                                if simg.mode in ['RGB', 'RGBA']:
                                                    base_mode = 'RGB'
                                                else:
                                                    base_mode = 'RGB'
                                            except Exception:
                                                base_mode = 'RGB'
                                            # 生成更自然的预填充底图：将原图缩放到目标尺寸并高斯模糊，再居中粘贴原图
                                            if simg.mode not in ['RGB']:
                                                simg = simg.convert('RGB')
                                            # 背景：缩放+模糊，半径可基于 mask_blur_radius 放大
                                            blur_bg_radius = 24
                                            try:
                                                if isinstance(parameters.get('mask_blur_radius'), (int, float)):
                                                    blur_bg_radius = max(8, min(int(parameters.get('mask_blur_radius')) * 2, 96))
                                            except Exception:
                                                pass
                                            blurred_bg = simg.resize((target_width, target_height), Image.LANCZOS).filter(ImageFilter.GaussianBlur(radius=blur_bg_radius))
                                            canvas = blurred_bg.copy()
                                            # 以羽化遮罩贴回原图，进一步软化粘贴边界
                                            feather = max(6, min(64, int((parameters.get('mask_blur_radius') or 24))))
                                            placement_mask_full = Image.new('L', (target_width, target_height), color=0)
                                            pm_draw = ImageDraw.Draw(placement_mask_full)
                                            pm_draw.rectangle([offset_x, offset_y, offset_x + orig_w - 1, offset_y + orig_h - 1], fill=255)
                                            placement_mask_full = placement_mask_full.filter(ImageFilter.GaussianBlur(radius=feather))
                                            placement_mask = placement_mask_full.crop((offset_x, offset_y, offset_x + orig_w, offset_y + orig_h))
                                            canvas.paste(simg, (offset_x, offset_y), placement_mask)
                                            padded_filename = f"auto_outpaint_image_{target_width}x{target_height}_" + os.path.basename(src_name)
                                            abs_padded = os.path.join(input_dir, padded_filename)
                                            canvas.save(abs_padded)
                                            # 覆盖 LoadImage 的图像输入为预填充后的新图（带 [input] 后缀）
                                            load_node['widgets_values'][0] = f"{padded_filename} [input]"
                                            logger.info(f"已生成并使用预填充图像: {padded_filename}")
                            except Exception as _pe:
                                logger.debug(f"自动生成预填充图像失败: {_pe}")

                            # 动态创建一个 LoadImage 节点加载该掩码（仅输出 MASK）
                            new_node_id = max(int(n.get('id', 0)) for n in modified_nodes) + 1
                            mask_node = {
                                'id': new_node_id,
                                'type': 'LoadImage',
                                'pos': [resize_node.get('pos', [0,0])[0] - 200, resize_node.get('pos', [0,0])[1] + 100],
                                'size': [300, 100],
                                'flags': {},
                                'order': resize_node.get('order', 0),
                                'mode': 0,
                                'inputs': [
                                    { 'localized_name': 'image', 'name': 'image', 'type': 'COMBO', 'widget': { 'name': 'image' }, 'link': None },
                                    { 'localized_name': 'choose file to upload', 'name': 'upload', 'type': 'IMAGEUPLOAD', 'widget': { 'name': 'upload' }, 'link': None }
                                ],
                                'outputs': [
                                    { 'localized_name': 'IMAGE', 'name': 'IMAGE', 'type': 'IMAGE', 'slot_index': 0, 'links': [] },
                                    { 'localized_name': 'MASK', 'name': 'MASK', 'type': 'MASK', 'slot_index': 1, 'links': [] }
                                ],
                                'properties': { 'Node name for S&R': 'LoadImage', 'cnr_id': 'comfy-core', 'ver': '0.3.27' },
                                'widgets_values': [ f"{os.path.basename(abs_mask)} [input]", 'image' ]
                            }
                            modified_nodes.append(mask_node)

                            # 重连：将 Resize 的 mask 输入连到新节点的 MASK 输出；
                            # 同时将 InpaintModelConditioning 的 pixels 输入改为使用 Resize 后的图像，确保掩码生效
                            # 找到 Resize 的 mask 输入槽位索引
                            resize_inputs = resize_node.get('inputs', [])
                            mask_slot_index = None
                            for idx, inp in enumerate(resize_inputs):
                                if inp.get('name') == 'mask':
                                    mask_slot_index = idx
                                    break
                            if mask_slot_index is not None:
                                # 移除原有指向该 mask 输入槽位的旧链接，避免双链接冲突
                                try:
                                    old_links = []
                                    for li in range(len(links)):
                                        if len(links[li]) >= 6:
                                            link_id, src_id, src_slot, dst_id, dst_slot, ltype = links[li]
                                            if str(dst_id) == str(resize_node.get('id')) and dst_slot == mask_slot_index:
                                                old_links.append(links[li])
                                    for ol in old_links:
                                        links.remove(ol)
                                except Exception:
                                    pass
                                # 构造新 link（使用新的唯一 link id）
                                new_link_id = max(l[0] for l in links) + 1 if links else 1000
                                links.append([new_link_id, new_node_id, 1, resize_node.get('id'), mask_slot_index, 'MASK'])
                                # 更新节点本体的 inputs/outputs 链接数组
                                resize_node_inputs = resize_node.get('inputs', [])
                                if 0 <= mask_slot_index < len(resize_node_inputs):
                                    resize_node_inputs[mask_slot_index]['link'] = new_link_id
                                mask_node['outputs'][1]['links'].append(new_link_id)

                            # 确保 InpaintModelConditioning 的 pixels 来自 Resize 输出（而非原图）
                            try:
                                inpaint_node = next((n for n in modified_nodes if 'InpaintModelConditioning' in n.get('type','')), None)
                                if inpaint_node is not None:
                                    # 找到 Resize 的 image 输出 link id
                                    resize_outputs = resize_node.get('outputs', [])
                                    image_out_link = None
                                    if resize_outputs and resize_outputs[0].get('links'):
                                        # 使用第一个 image 输出链接 id
                                        image_out_link = resize_outputs[0]['links'][0]
                                    if image_out_link is not None:
                                        # 更新 links 中指向 Inpaint.pixels 的链接为来自 Resize 的输出
                                        # 先找到 Inpaint.pixels 输入槽位索引
                                        pixels_slot = None
                                        for idx, inp in enumerate(inpaint_node.get('inputs', []) or []):
                                            if inp.get('name') == 'pixels':
                                                pixels_slot = idx
                                                break
                                        if pixels_slot is not None:
                                            # 替换 links 里 dst=Inpaint, dst_slot=pixels_slot 的条目（或新增）
                                            replaced = False
                                            for li in range(len(links)):
                                                if len(links[li]) >= 6:
                                                    _, src_id, src_slot, dst_id, dst_slot, _t = links[li]
                                                    if str(dst_id) == str(inpaint_node.get('id')) and dst_slot == pixels_slot:
                                                        # 替换为来自 Resize 的输出（需要找到 Resize 的 node_id 与对应输出slot=0）
                                                        links[li] = [links[li][0], resize_node.get('id'), 0, inpaint_node.get('id'), pixels_slot, 'IMAGE']
                                                        replaced = True
                                                        break
                                            if not replaced:
                                                # 新增一个 link id
                                                new_link2 = (max(l[0] for l in links) + 1) if links else 1001
                                                links.append([new_link2, resize_node.get('id'), 0, inpaint_node.get('id'), pixels_slot, 'IMAGE'])
                            except Exception as _re:
                                logger.debug(f"修正 Inpaint pixels 链接失败: {_re}")

                            # 写回 links 到工作流
                            workflow_data['links'] = links
                except Exception as e:
                    logger.error(f"自动扩图掩码生成失败: {e}")

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
            
            # 记录被跳过的LoadImageOutput节点
            skipped_loadimage_nodes = set()

            for node_id, node in nodes_by_id.items():
                if node.get('type') in NODE_TYPES_TO_IGNORE: continue
                node_type = node.get('type')
                
                # LoadImageOutput节点特殊处理：检查是否应该跳过整个节点
                if node_type == 'LoadImageOutput':
                    node_mode = node.get('mode', 0)
                    is_disabled = node_mode == 4
                    
                    if is_disabled:
                        # 可选节点被禁用，跳过该节点
                        logger.info(f"可选LoadImageOutput节点 {node_id} 被禁用，跳过该节点")
                        skipped_loadimage_nodes.add(str(node_id))
                        continue  # 跳过这个节点，不添加到API workflow中
                
                api_node = {"class_type": node_type, "inputs": {}}
                
                # 处理widgets_values
                if node_type in WIDGET_INDEX_MAP and 'widgets_values' in node:
                    for w_name, w_idx in WIDGET_INDEX_MAP[node_type].items():
                        if w_idx >= 0 and len(node['widgets_values']) > w_idx:
                            value = node['widgets_values'][w_idx]
                            # 清理模型名称中的状态标记
                            if isinstance(value, str):
                                cleaned_value = value.replace(' ✅', '').replace(' ❌ (文件不存在)', '')
                                # 修正文件名不匹配问题
                                if cleaned_value == 'flux1-turbo-alpha.safetensors':
                                    cleaned_value = 'flux.1-turbo-alpha.safetensors'
                                # LoadImageOutput节点特殊处理
                                if node_type == 'LoadImageOutput':
                                    # 直接写入图像路径，让ComfyUI处理
                                    api_node['inputs'][w_name] = cleaned_value
                                else:
                                    api_node['inputs'][w_name] = cleaned_value
                            else:
                                api_node['inputs'][w_name] = value
                    # 兜底：对 CLIPVisionEncode 和 StyleModelApply 填充默认值（若未在 widgets_values 中取到）
                    if node_type == 'CLIPVisionEncode':
                        api_node['inputs'].setdefault('crop', 'center')
                    if node_type == 'StyleModelApply':
                        api_node['inputs'].setdefault('strength', 1.0)
                        api_node['inputs'].setdefault('strength_type', 'multiply')
                    if node_type == 'InpaintModelConditioning':
                        # 兜底：若未从 widgets 读取到，默认 false
                        api_node['inputs'].setdefault('noise_mask', False)
                    
                    # 添加调试日志
                    if node_type in ['CLIPTextEncode', 'RandomNoise', 'FluxGuidance', 'BasicScheduler']:
                        logger.info(f"节点 {node_id} ({node_type}) 转换结果: {api_node['inputs']}")
                    
                    # 特别调试LoadImageOutput节点
                    if node_type == 'LoadImageOutput':
                        logger.info(f"LoadImageOutput节点 {node_id} widgets_values: {node.get('widgets_values', [])}")
                        logger.info(f"LoadImageOutput节点 {node_id} 转换结果: {api_node['inputs']}")
                
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
                                            # 检查源节点是否被跳过
                                            if str(src_id) in skipped_loadimage_nodes:
                                                logger.info(f"跳过来自被禁用节点 {src_id} 的连接到节点 {node_id}")
                                                continue
                                            
                                            in_name = input_data['name']
                                            api_node['inputs'][in_name] = primitive_values.get(str(src_id), [str(src_id), src_slot])
                                            break
                                    else:  # 旧格式
                                        link_id, src_id, src_slot, dst_id = link
                                        if str(dst_id) == node_id and i == 0:  # 旧格式假设dst_slot为0
                                            # 检查源节点是否被跳过
                                            if str(src_id) in skipped_loadimage_nodes:
                                                logger.info(f"跳过来自被禁用节点 {src_id} 的连接到节点 {node_id}")
                                                continue
                                            
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
                last_progress = 0
                while True:
                    time.sleep(1)  # 每1秒检查一次，提高响应速度
                    
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
                                # 任务正在执行中，获取更详细的进度信息
                                progress = self._get_detailed_progress(task_id, prompt_id, client_id)
                                current_label = running_tasks[task_id].get('current_node_label')
                                status_msg = f"正在执行: {current_label}" if current_label else '正在执行工作流...'
                                running_tasks[task_id].update({
                                    'status': 'running',
                                    'progress': progress,
                                    'message': status_msg
                                })
                            elif found_in_pending:
                                # 计算排队位置
                                queue_position = self._get_queue_position(prompt_id, pending_queue)
                                progress = max(5, min(15, 15 - queue_position * 2))  # 排队时显示5-15%的进度
                                running_tasks[task_id].update({
                                    'status': 'pending',
                                    'progress': progress,
                                    'message': f'排队中... (位置: {queue_position + 1})'
                                })
                            else:
                                # 任务完成或失败 - 检查历史记录
                                self._check_task_completion(task_id, prompt_id)
                                break
                        else:
                            # 队列API调用失败，但任务可能仍在运行
                            if last_progress < 90:  # 避免无限增长
                                last_progress += 1
                            running_tasks[task_id].update({
                                'status': 'running',
                                'progress': last_progress,
                                'message': '正在执行...'
                            })
                    except Exception as e:
                        logger.error(f"监控进度失败: {e}")
                        # 出错时保持当前进度，不要重置
                        if task_id in running_tasks and running_tasks[task_id]['status'] == 'running':
                            current_progress = running_tasks[task_id].get('progress', 0)
                            running_tasks[task_id].update({
                                'progress': current_progress,
                                'message': '正在执行...'
                            })
                        time.sleep(3)  # 出错时等待更长时间
                        
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
    
    def _get_detailed_progress(self, task_id, prompt_id, client_id):
        """获取详细的执行进度：基于当前执行节点在工作流中的位置估算"""
        try:
            task_info = running_tasks.get(task_id, {})
            total_nodes = int(task_info.get('total_nodes') or 0)
            node_index_map = task_info.get('node_index_map') or {}

            # 尝试获取执行状态（允许 /executing 短时间无数据）
            execution_response = requests.get(f"{COMFYUI_API_URL}/executing", timeout=5)
            if execution_response.status_code == 200:
                execution_data = execution_response.json()
                # 某些版本executing为列表，取最后一项；或为dict
                if isinstance(execution_data, list) and execution_data:
                    execution_data = execution_data[-1]
                
                # 检查是否有正在执行的节点（优先严格匹配 prompt_id，若无则宽松匹配 node 属于本workflow）
                exec_node = execution_data.get('node')
                exec_pid = execution_data.get('prompt_id')
                is_our_prompt = (exec_pid == prompt_id)
                belongs_to_workflow = exec_node is not None and str(exec_node) in node_index_map
                if exec_node is not None and (is_our_prompt or belongs_to_workflow):
                    current_node = exec_node
                    # 节点ID可能为字符串/数字，统一为字符串键
                    node_key = str(current_node)
                    idx = node_index_map.get(node_key)
                    # 更新当前节点可读信息与相邻待执行节点，供前端显示
                    task_state = running_tasks.get(task_id, {})
                    current_label = (task_state.get('node_meta_map') or {}).get(node_key)
                    order_list = task_state.get('node_order_list') or []
                    next_label = None
                    if node_key in order_list:
                        idx_in_order = order_list.index(node_key)
                        if idx_in_order + 1 < len(order_list):
                            next_id = order_list[idx_in_order + 1]
                            next_label = (task_state.get('node_meta_map') or {}).get(next_id)
                    if task_id in running_tasks:
                        running_tasks[task_id]['current_node_id'] = node_key
                        running_tasks[task_id]['current_node_label'] = current_label or f"Node {node_key}"
                        running_tasks[task_id]['next_node_label'] = next_label
                    if idx is not None and total_nodes > 0:
                        # 15%~95%区间根据节点索引线性映射
                        frac = max(0.0, min(1.0, idx / max(1, total_nodes - 1)))
                        base = int(15 + frac * 80)
                        # 若执行数据包含推进度的细粒度信息（如执行步/总步），进一步细化
                        try:
                            # 某些扩展会返回 'execution' 或 'step' 字段；最佳努力读取
                            exec_block = execution_data.get('execution') or {}
                            step = execution_data.get('step') or execution_data.get('current_step') or exec_block.get('step')
                            total = execution_data.get('total_steps') or execution_data.get('max_step') or exec_block.get('total_steps')
                            if step is not None and total:
                                fine = max(0.0, min(1.0, float(step) / float(total)))
                                base = min(95, max(base, int(base + fine * 2)))
                        except Exception:
                            pass
                        return base
                    # 没有映射信息，返回保守中间值
                    return 55
                
                # 检查历史记录中的进度
                history_response = requests.get(f"{COMFYUI_API_URL}/history/{prompt_id}", timeout=5)
                if history_response.status_code == 200:
                    history_data = history_response.json()
                    if prompt_id in history_data:
                        task_info = history_data[prompt_id]
                        outputs = task_info.get('outputs', {})
                        # 尝试基于已完成节点数与总节点数细化
                        try:
                            executed = task_info.get('executed', [])
                            if executed and total_nodes:
                                done_ratio = max(0.0, min(1.0, len(executed) / float(total_nodes)))
                                return max(60, min(95, int(15 + done_ratio * 80)))
                        except Exception:
                            pass
                        
                        # 根据输出节点数量估算进度
                        if outputs:
                            # 有输出表示任务接近完成
                            return 90
                        else:
                            # 没有输出但任务在运行中
                            return 60
            
            # 默认进度
            return 50
            
        except Exception as e:
            logger.error(f"获取详细进度失败: {e}")
            return 50
    
    def _get_queue_position(self, prompt_id, pending_queue):
        """获取在队列中的位置"""
        try:
            for i, item in enumerate(pending_queue):
                if item[1] == prompt_id:
                    return i
            return 0
        except Exception as e:
            logger.error(f"获取队列位置失败: {e}")
            return 0
    
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
            
            # 用于存储最后处理的图片信息
            last_processed_image = None
            output_images = []  # 存储所有找到的图片信息
            
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
                        
                        # 仅处理输出类型的图片，跳过临时预览图
                        if img_type != 'output':
                            continue
                        img_data = self._get_image_from_comfyui(filename, subfolder, img_type)
                        if img_data:
                            # 保存图片到本地输出目录
                            output_dir = os.path.join(os.path.dirname(__file__), 'outputs')
                            os.makedirs(output_dir, exist_ok=True)
                            
                            # 生成人类可读的文件名
                            # 格式：工作流名称_YYYY-MM-DD_HH-MM-SS_序号.扩展名
                            now = datetime.now()
                            date_str = now.strftime("%Y-%m-%d")
                            time_str = now.strftime("%H-%M-%S")
                            
                            # 从工作流文件名中提取主要名称（去掉.json）
                            workflow_base_name = workflow_filename.replace('.json', '').replace('workflow_', '')
                            
                            # 处理原文件名：提取扩展名
                            name_part, ext = os.path.splitext(filename)
                            if not ext:
                                ext = '.png'  # 默认扩展名
                            
                            # 查找当前日期的最大序号，避免重复
                            prefix = f"{workflow_base_name}_{date_str}_{time_str}"
                            existing_files = [f for f in os.listdir(output_dir) if f.startswith(prefix)]
                            sequence = len(existing_files) + 1
                            
                            output_filename = f"{prefix}_{sequence:03d}{ext}"
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

                            # 补充：从实际执行的 prompt 中提取模型加载信息，便于画廊展示
                            try:
                                model_info = self._extract_model_loaders(task_info)
                                if model_info:
                                    metadata['model_loaders'] = model_info.get('by_node')
                                    # 同时写入摘要，前端可直接读取主要模型
                                    metadata['model_summary'] = model_info.get('summary')
                            except Exception as _e:
                                logger.warning(f"提取模型信息失败（可忽略）: {_e}")

                            # 补充：从实际执行的 prompt 中补齐通用生成参数（steps/cfg/sampler/width/height...）
                            try:
                                auto_params = self._extract_generation_parameters(task_info)
                                if auto_params:
                                    # 不覆盖用户明确设置的字段，仅在缺失时填充
                                    for k, v in auto_params.items():
                                        parameters.setdefault(k, v)
                            except Exception as _e:
                                logger.warning(f"提取生成参数失败（可忽略）: {_e}")
                            
                            # 保存元数据到JSON文件（与图片文件名对应）
                            metadata_filename = output_filename.replace(ext, '.json')
                            metadata_path = os.path.join(output_dir, metadata_filename)
                            with open(metadata_path, 'w', encoding='utf-8') as f:
                                json.dump(metadata, f, ensure_ascii=False, indent=2)
                            
                            logger.info(f"图片和元数据已保存: {output_filename}")
                            
                            # 存储图片信息，按类型分类
                            image_info = {
                                'message': f'任务完成，图片已生成: {filename}',
                                'image_url': f'/outputs/{output_filename}',
                                'metadata_url': f'/outputs/{metadata_filename}',
                                'img_type': img_type,
                                'filename': filename
                            }
                            output_images.append(image_info)
                    except Exception as e:
                        logger.error(f"处理图片失败 {filename}: {e}")
                        continue
            
            # 优先返回 output 类型的图片，如果没有则返回 temp 类型的图片
            if output_images:
                # 按类型排序：output 类型优先
                output_images.sort(key=lambda x: x['img_type'] != 'output')
                # 取第一个元素（优先级最高的）
                last_processed_image = output_images[0]
                logger.info(f"返回图片: {last_processed_image['filename']} (类型: {last_processed_image['img_type']})")
                return last_processed_image
            else:
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

    def _extract_model_loaders(self, task_info):
        """从ComfyUI历史记录的prompt中提取实际生效的模型加载相关配置。
        返回形如：{
          'by_node': {
             'model_path_45': 'flux.1-dev-fp8.safetensors',
             'vae_name_10': 'flux_vae.safetensors',
             'lora_name_46': 'some_lora.safetensors',
             ...
          },
          'summary': {
             'main_model': 'flux.1-dev-fp8.safetensors',
             'vae': 'flux_vae.safetensors',
             'loras': ['some_lora.safetensors']
          }
        }
        """
        try:
            prompt_data = task_info.get('prompt', [])
            if not prompt_data or len(prompt_data) < 3:
                return None
            nodes_config = prompt_data[2]  # dict: node_id -> {class_type, inputs}
            if not isinstance(nodes_config, dict):
                return None

            by_node = {}
            loras = []
            main_model_candidate = None
            vae_candidate = None

            for node_id, node_data in nodes_config.items():
                try:
                    class_type = node_data.get('class_type')
                    inputs = node_data.get('inputs', {}) or {}
                    sid = str(node_id)

                    # 统一采集所有 inputs 的基础键，带上 node 后缀
                    for k, v in inputs.items():
                        key = f"{k}_{sid}"
                        by_node[key] = v

                    # 根据节点类型推断主模型/vae/lora
                    if class_type == 'NunchakuFluxDiTLoader':
                        # 主模型优先 model_path
                        if not main_model_candidate and inputs.get('model_path'):
                            main_model_candidate = inputs.get('model_path')
                    elif class_type == 'CheckpointLoaderSimple':
                        if not main_model_candidate and inputs.get('ckpt_name'):
                            main_model_candidate = inputs.get('ckpt_name')
                    elif class_type == 'NunchakuTextEncoderLoader':
                        # 作为兜底展示
                        if not main_model_candidate and inputs.get('model_type'):
                            main_model_candidate = inputs.get('model_type')
                    elif class_type == 'VAELoader':
                        if not vae_candidate and inputs.get('vae_name'):
                            vae_candidate = inputs.get('vae_name')
                    elif class_type in ('NunchakuFluxLoraLoader', 'LoraLoader'):
                        lname = inputs.get('lora_name') or inputs.get('lora_name_1')
                        if lname:
                            loras.append(lname)
                except Exception:
                    continue

            summary = {
                'main_model': main_model_candidate,
                'vae': vae_candidate,
                'loras': loras or None
            }

            return {'by_node': by_node, 'summary': summary}
        except Exception as e:
            logger.error(f"提取模型加载信息失败: {e}")
            return None

    def _extract_generation_parameters(self, task_info):
        """从执行的 prompt 配置中提取通用生成参数（steps/cfg/sampler/scheduler/denoise/width/height）。
        返回 dict，仅包含解析成功的键。"""
        try:
            prompt_data = task_info.get('prompt', [])
            if not prompt_data or len(prompt_data) < 3:
                return {}
            nodes_config = prompt_data[2]
            if not isinstance(nodes_config, dict):
                return {}

            out = {}
            for node_id, node_data in nodes_config.items():
                try:
                    class_type = node_data.get('class_type')
                    inputs = node_data.get('inputs', {}) or {}
                    if class_type == 'KSampler':
                        if 'seed' in inputs and inputs['seed'] is not None:
                            out.setdefault('seed', inputs['seed'])
                        if 'sampler_name' in inputs and inputs['sampler_name']:
                            out.setdefault('sampler', inputs['sampler_name'])
                    if class_type == 'BasicScheduler':
                        if 'steps' in inputs and inputs['steps'] is not None:
                            out.setdefault('steps', inputs['steps'])
                        if 'scheduler' in inputs and inputs['scheduler']:
                            out.setdefault('scheduler', inputs['scheduler'])
                        if 'denoise' in inputs and inputs['denoise'] is not None:
                            out.setdefault('denoise', inputs['denoise'])
                    if class_type == 'FluxGuidance':
                        if 'guidance' in inputs and inputs['guidance'] is not None:
                            out.setdefault('cfg', inputs['guidance'])
                    if class_type in ('EmptyLatentImage', 'EmptySD3LatentImage'):
                        if 'width' in inputs and inputs['width'] is not None:
                            out.setdefault('width', inputs['width'])
                        if 'height' in inputs and inputs['height'] is not None:
                            out.setdefault('height', inputs['height'])
                    if class_type == 'ModelSamplingFlux':
                        # 某些工作流宽高在该节点
                        if 'width' in inputs and inputs['width'] is not None:
                            out.setdefault('width', inputs['width'])
                        if 'height' in inputs and inputs['height'] is not None:
                            out.setdefault('height', inputs['height'])
                except Exception:
                    continue
            return out
        except Exception as e:
            logger.error(f"提取生成参数失败: {e}")
            return {}

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
    return render_template('index.html', cache_bust=int(time.time()))

@app.route('/test')
def test():
    """测试页面"""
    return send_from_directory('.', 'test.html')

@app.route('/debug')
def debug():
    """调试页面"""
    return render_template('debug.html')

@app.route('/test-simple')
def test_simple():
    """简化测试页面"""
    return render_template('test_simple.html')

@app.route('/test_image_display')
def test_image_display():
    """测试图片显示页面"""
    return send_from_directory('.', 'test_image_display.html')

@app.route('/test_frontend')
def test_frontend():
    """前端功能测试页面"""
    return send_from_directory('.', 'test_frontend.html')

@app.route('/debug_workflow_loading')
def debug_workflow_loading():
    """工作流加载调试页面"""
    return send_from_directory('.', 'debug_workflow_loading.html')

@app.route('/test_simple_loading')
def test_simple_loading():
    """简单工作流加载测试页面"""
    return send_from_directory('.', 'test_simple_loading.html')

@app.route('/test_js_loading')
def test_js_loading():
    """JavaScript加载测试页面"""
    return send_from_directory('.', 'test_js_loading.html')

@app.route('/debug_main_page')
def debug_main_page():
    """主页调试页面"""
    return send_from_directory('.', 'debug_main_page.html')

@app.route('/gallery')
def gallery():
    """图片画廊页面"""
    return render_template('gallery.html')

@app.route('/prompt-manager')
def prompt_manager():
    """提示词管理器页面"""
    return render_template('prompt-manager.html')

@app.route('/api/workflow-stats')
def get_workflow_stats():
    """获取工作流使用统计"""
    try:
        stats = load_workflow_stats()
        
        # 获取最近7天使用的工作流
        recent_cutoff = datetime.now() - timedelta(days=7)
        recent_workflows = []
        
        for workflow, usage_time_str in stats['recent_usage'].items():
            try:
                usage_time = datetime.fromisoformat(usage_time_str)
                if usage_time >= recent_cutoff:
                    recent_workflows.append({
                        'workflow': workflow,
                        'last_used': usage_time_str,
                        'usage_count': stats['usage_count'].get(workflow, 0)
                    })
            except Exception:
                continue
        
        # 按最后使用时间排序
        recent_workflows.sort(key=lambda x: x['last_used'], reverse=True)
        
        # 获取使用次数最多的工作流
        popular_workflows = []
        for workflow, count in sorted(stats['usage_count'].items(), key=lambda x: x[1], reverse=True):
            popular_workflows.append({
                'workflow': workflow,
                'usage_count': count,
                'last_used': stats['recent_usage'].get(workflow, '')
            })
        
        return jsonify({
            'success': True,
            'recent_workflows': recent_workflows[:10],  # 最近10个
            'popular_workflows': popular_workflows[:10]  # 最热门10个
        })
    except Exception as e:
        logger.error(f"获取工作流统计失败: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

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
    
    # 先检查ComfyUI连接状态
    if not runner.check_comfyui_status():
        return jsonify({
            'success': False, 
            'error': 'ComfyUI服务未运行或无法连接，请确保ComfyUI后端已启动'
        }), 503
    
    # 从parameters中提取selected_images，如果没有则从顶级字段获取
    selected_images = parameters.get('selected_images', {})
    if not selected_images:
        selected_images = data.get('selected_images', {})
    
    # 记录工作流使用统计
    record_workflow_usage(filename)
    
    # 生成任务ID
    task_id = f"task_{int(time.time())}_{len(running_tasks)}"
    
    # 初始化任务状态
    running_tasks[task_id] = {
        'status': 'initializing',
        'filename': filename,
        'workflow_filename': filename,
        'parameters': parameters,
        'start_time': datetime.now().isoformat(),
        'progress': 0,
        'message': '正在初始化任务...',
        'prompt_id': None
    }
    
    # 在后台线程中运行
    def run_in_background():
        try:
            result = runner.run_workflow_with_parameters_and_images(filename, task_id, parameters, selected_images)
            if not result.get('success', False):
                # 如果任务启动失败，更新任务状态
                if task_id in running_tasks:
                    running_tasks[task_id].update({
                        'status': 'failed',
                        'end_time': datetime.now().isoformat(),
                        'error': result.get('error', '任务启动失败'),
                        'message': '任务启动失败'
                    })
        except Exception as e:
            logger.error(f"后台任务执行异常: {e}")
            if task_id in running_tasks:
                running_tasks[task_id].update({
                    'status': 'failed',
                    'end_time': datetime.now().isoformat(),
                    'error': f'任务执行异常: {str(e)}',
                    'message': '任务执行异常'
                })
    
    thread = threading.Thread(target=run_in_background)
    thread.daemon = True
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

@app.route('/api/system-resources')
def system_resources():
    """返回系统资源占用（CPU/内存/GPU/VRAM），尽量轻量"""
    try:
        result = {
            'success': True,
            'cpu_percent': None,
            'memory_percent': None,
            'memory_total_mb': None,
            'memory_used_mb': None,
            'gpus': []
        }
        # CPU/内存
        if psutil:
            try:
                result['cpu_percent'] = psutil.cpu_percent(interval=0.1)
                vm = psutil.virtual_memory()
                result['memory_percent'] = vm.percent
                result['memory_total_mb'] = round(vm.total / (1024 * 1024))
                # used 采用 total - available 更符合系统观感
                result['memory_used_mb'] = max(0, round((vm.total - vm.available) / (1024 * 1024)))
            except Exception as e:
                logger.warning(f"psutil 读取失败: {e}")
        else:
            # 无 psutil 的回退：读取 /proc/meminfo 与 /proc/stat
            try:
                # 内存：/proc/meminfo (kB)
                meminfo = {}
                with open('/proc/meminfo', 'r') as f:
                    for line in f:
                        parts = line.split(':')
                        if len(parts) == 2:
                            key = parts[0].strip()
                            val = parts[1].strip().split()[0]
                            meminfo[key] = int(val)
                mem_total_kb = meminfo.get('MemTotal', 0)
                mem_available_kb = meminfo.get('MemAvailable', 0)
                mem_used_kb = max(0, mem_total_kb - mem_available_kb)
                result['memory_total_mb'] = round(mem_total_kb / 1024)
                result['memory_used_mb'] = round(mem_used_kb / 1024)
                result['memory_percent'] = round((mem_used_kb / mem_total_kb * 100), 1) if mem_total_kb else 0
            except Exception as e:
                logger.debug(f"/proc/meminfo 读取失败: {e}")
            try:
                # CPU：/proc/stat 两次采样
                def read_cpu_times():
                    with open('/proc/stat', 'r') as f:
                        for line in f:
                            if line.startswith('cpu '):
                                parts = [int(x) for x in line.split()[1:]]
                                user, nice, system, idle, iowait, irq, softirq, steal, *_ = parts + [0]*(10-len(parts))
                                idle_all = idle + iowait
                                non_idle = user + nice + system + irq + softirq + steal
                                total = idle_all + non_idle
                                return total, idle_all
                    return None, None
                t1, i1 = read_cpu_times()
                time.sleep(0.05)
                t2, i2 = read_cpu_times()
                if t1 is not None and t2 is not None and (t2 - t1) > 0:
                    cpu_percent = (1 - (i2 - i1) / (t2 - t1)) * 100
                    result['cpu_percent'] = max(0, min(100, round(cpu_percent, 1)))
            except Exception as e:
                logger.debug(f"/proc/stat 读取失败: {e}")
        # GPU/VRAM - 通过 nvidia-smi
        try:
            smi = subprocess.run(
                ['nvidia-smi', '--query-gpu=index,name,memory.total,memory.used,utilization.gpu', '--format=csv,noheader,nounits'],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=1.5
            )
            if smi.returncode == 0:
                lines = [l.strip() for l in smi.stdout.split('\n') if l.strip()]
                for line in lines:
                    parts = [p.strip() for p in line.split(',')]
                    if len(parts) >= 5:
                        idx, name, mem_total, mem_used, util = parts[:5]
                        try:
                            mem_total = float(mem_total)
                            mem_used = float(mem_used)
                            util = float(util)
                            vram_percent = (mem_used / mem_total * 100) if mem_total > 0 else 0
                        except Exception:
                            vram_percent = None
                        result['gpus'].append({
                            'index': idx,
                            'name': name,
                            'vram_used_mb': mem_used,
                            'vram_total_mb': mem_total,
                            'vram_percent': vram_percent,
                            'util_percent': util
                        })
        except Exception as e:
            logger.debug(f"nvidia-smi 不可用: {e}")
        return jsonify(result)
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/clean-vram', methods=['POST'])
def clean_vram():
    """尝试清理VRAM（调用ComfyUI unload 或 torch.cuda.empty_cache 的代理）"""
    try:
        # 优先尝试ComfyUI 提供的卸载接口（如果有）
        try:
            resp = requests.post(f"{COMFYUI_API_URL}/unload", timeout=3)
            if resp.status_code == 200:
                return jsonify({'success': True, 'message': '已请求ComfyUI卸载模型/清理VRAM'})
        except Exception:
            pass
        # 兜底：调用nvidia-smi建议的清理方式不可行；这里仅返回提示
        return jsonify({'success': True, 'message': '已触发清理请求（如未生效，请在后端手动释放/重启相关进程）'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
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
            uploaded_files = []
            for filename in os.listdir(uploaded_dir):
                if filename.lower().endswith(('.png', '.jpg', '.jpeg', '.webp')):
                    file_path = os.path.join(uploaded_dir, filename)
                    uploaded_files.append({
                        'name': filename,
                        'path': f'uploaded/{filename}',
                        'size': os.path.getsize(file_path),
                        'mtime': os.path.getmtime(file_path)
                    })
            # 按修改时间倒序排列（最新的在前面）
            uploaded_files.sort(key=lambda x: x['mtime'], reverse=True)
            # 移除mtime字段，只保留需要的数据
            for file_info in uploaded_files:
                del file_info['mtime']
                images['uploaded'].append(file_info)
        
        # 扫描已生成的图像（包括子目录和根目录）
        generated_files = []
        
        if os.path.exists(generated_dir):
            for filename in os.listdir(generated_dir):
                if filename.lower().endswith(('.png', '.jpg', '.jpeg', '.webp')):
                    file_path = os.path.join(generated_dir, filename)
                    generated_files.append({
                        'name': filename,
                        'path': f'generated/{filename}',
                        'size': os.path.getsize(file_path),
                        'mtime': os.path.getmtime(file_path)
                    })
        
        # 扫描outputs根目录中的生成图像（支持新旧格式）
        if os.path.exists(output_dir):
            for filename in os.listdir(output_dir):
                if filename.lower().endswith(('.png', '.jpg', '.jpeg', '.webp')):
                    # 排除子目录中的文件和非图片文件
                    file_path = os.path.join(output_dir, filename)
                    if os.path.isfile(file_path):
                        # 支持两种格式：
                        # 1. 旧格式：result_xxx_xxx.png
                        # 2. 新格式：workflow_2025-08-07_14-30-25_001.png
                        is_generated = (
                            filename.startswith('result_') or  # 旧格式
                            ('_2' in filename and len(filename.split('_')) >= 4)  # 新格式（包含日期时间）
                        )
                        
                        if is_generated:
                            generated_files.append({
                                'name': filename,
                                'path': filename,  # 根目录中的文件，路径就是文件名
                                'size': os.path.getsize(file_path),
                                'mtime': os.path.getmtime(file_path)
                            })
        
        # 按修改时间倒序排列（最新的在前面）
        generated_files.sort(key=lambda x: x['mtime'], reverse=True)
        # 移除mtime字段，只保留需要的数据
        for file_info in generated_files:
            del file_info['mtime']
            images['generated'].append(file_info)
        
        return jsonify({'success': True, 'images': images})
    except Exception as e:
        logger.error(f"获取图像列表失败: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/delete-image', methods=['POST'])
def delete_image():
    """删除单个图片"""
    try:
        data = request.get_json()
        if not data or 'filename' not in data:
            return jsonify({'success': False, 'error': '缺少文件名参数'}), 400
        
        filename = data['filename']
        output_dir = os.path.join(os.path.dirname(__file__), 'outputs')
        
        # 查找文件路径
        file_paths = []
        
        # 检查根目录
        root_path = os.path.join(output_dir, filename)
        if os.path.exists(root_path):
            file_paths.append(root_path)
        
        # 检查uploaded子目录
        uploaded_path = os.path.join(output_dir, 'uploaded', filename)
        if os.path.exists(uploaded_path):
            file_paths.append(uploaded_path)
        
        # 检查generated子目录
        generated_path = os.path.join(output_dir, 'generated', filename)
        if os.path.exists(generated_path):
            file_paths.append(generated_path)
        
        if not file_paths:
            return jsonify({'success': False, 'error': '文件不存在'}), 404
        
        # 删除文件
        deleted_count = 0
        for file_path in file_paths:
            try:
                os.remove(file_path)
                deleted_count += 1
                logger.info(f"已删除图片: {file_path}")
            except Exception as e:
                logger.error(f"删除文件失败 {file_path}: {e}")
        
        # 删除对应的元数据文件（新格式：图片文件名.json）
        name_part, ext = os.path.splitext(filename)
        metadata_filename = f"{name_part}.json"
        metadata_path = os.path.join(output_dir, metadata_filename)
        if os.path.exists(metadata_path):
            try:
                os.remove(metadata_path)
                logger.info(f"已删除元数据: {metadata_path}")
            except Exception as e:
                logger.error(f"删除元数据失败 {metadata_path}: {e}")
        else:
            # 尝试旧格式的元数据文件（向后兼容）
            if 'result_' in filename and '_' in filename:
                old_id = filename.split('_')[1]
                old_metadata_filename = f"metadata_{old_id}.json"
                old_metadata_path = os.path.join(output_dir, old_metadata_filename)
                if os.path.exists(old_metadata_path):
                    try:
                        os.remove(old_metadata_path)
                        logger.info(f"已删除旧格式元数据: {old_metadata_path}")
                    except Exception as e:
                        logger.error(f"删除旧格式元数据失败 {old_metadata_path}: {e}")
        
        return jsonify({'success': True, 'deleted_count': deleted_count})
    
    except Exception as e:
        logger.error(f"删除图片失败: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/delete-images', methods=['POST'])
def delete_images():
    """批量删除图片"""
    try:
        data = request.get_json()
        if not data or 'filenames' not in data:
            return jsonify({'success': False, 'error': '缺少文件名列表参数'}), 400
        
        filenames = data['filenames']
        if not isinstance(filenames, list):
            return jsonify({'success': False, 'error': '文件名列表格式错误'}), 400
        
        output_dir = os.path.join(os.path.dirname(__file__), 'outputs')
        deleted_count = 0
        
        for filename in filenames:
            # 查找文件路径
            file_paths = []
            
            # 检查根目录
            root_path = os.path.join(output_dir, filename)
            if os.path.exists(root_path):
                file_paths.append(root_path)
            
            # 检查uploaded子目录
            uploaded_path = os.path.join(output_dir, 'uploaded', filename)
            if os.path.exists(uploaded_path):
                file_paths.append(uploaded_path)
            
            # 检查generated子目录
            generated_path = os.path.join(output_dir, 'generated', filename)
            if os.path.exists(generated_path):
                file_paths.append(generated_path)
            
            # 删除文件
            for file_path in file_paths:
                try:
                    os.remove(file_path)
                    deleted_count += 1
                    logger.info(f"已删除图片: {file_path}")
                except Exception as e:
                    logger.error(f"删除文件失败 {file_path}: {e}")
            
            # 删除对应的元数据文件（新格式：图片文件名.json）
            name_part, ext = os.path.splitext(filename)
            metadata_filename = f"{name_part}.json"
            metadata_path = os.path.join(output_dir, metadata_filename)
            if os.path.exists(metadata_path):
                try:
                    os.remove(metadata_path)
                    logger.info(f"已删除元数据: {metadata_path}")
                except Exception as e:
                    logger.error(f"删除元数据失败 {metadata_path}: {e}")
            else:
                # 尝试旧格式的元数据文件（向后兼容）
                if 'result_' in filename and '_' in filename:
                    old_id = filename.split('_')[1]
                    old_metadata_filename = f"metadata_{old_id}.json"
                    old_metadata_path = os.path.join(output_dir, old_metadata_filename)
                    if os.path.exists(old_metadata_path):
                        try:
                            os.remove(old_metadata_path)
                            logger.info(f"已删除旧格式元数据: {old_metadata_path}")
                        except Exception as e:
                            logger.error(f"删除旧格式元数据失败 {old_metadata_path}: {e}")
        
        return jsonify({'success': True, 'deleted_count': deleted_count})
    
    except Exception as e:
        logger.error(f"批量删除图片失败: {str(e)}")
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
                
                # 若是遮罩文件（来自遮罩编辑器），单独放到 masks 目录，并在返回值中标记 is_mask
                is_mask_upload = name.startswith('mask_editor') or name.startswith('mask')
                target_dir = os.path.join(os.path.dirname(__file__), 'outputs', 'masks') if is_mask_upload else uploaded_dir
                os.makedirs(target_dir, exist_ok=True)
                filepath = os.path.join(target_dir, safe_filename)
                file.save(filepath)
                
                uploaded_files.append({
                    'original_name': file.filename,
                    'saved_name': safe_filename,
                    'path': (f'masks/{safe_filename}' if is_mask_upload else f'uploaded/{safe_filename}'),
                    'is_mask': is_mask_upload
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
                if filename.lower().endswith(('.png', '.jpg', '.jpeg', '.webp')):
                    filepath = os.path.join(output_dir, filename)
                    if os.path.isfile(filepath):
                        # 支持两种格式：
                        # 1. 旧格式：result_xxx_xxx.png
                        # 2. 新格式：workflow_2025-08-07_14-30-25_001.png
                        is_generated = (
                            filename.startswith('result_') or  # 旧格式
                            ('_2' in filename and len(filename.split('_')) >= 4)  # 新格式（包含日期时间）
                        )
                        
                        if not is_generated:
                            continue
                            
                        stat = os.stat(filepath)
                        
                        # 尝试读取对应的元数据文件
                        metadata = {}
                        
                        # 新格式：直接用文件名查找对应的.json文件
                        name_part, ext = os.path.splitext(filename)
                        metadata_filename = f"{name_part}.json"
                        metadata_path = os.path.join(output_dir, metadata_filename)
                        
                        if os.path.exists(metadata_path):
                            try:
                                with open(metadata_path, 'r', encoding='utf-8') as f:
                                    metadata = json.load(f)
                            except Exception as e:
                                logger.warning(f"读取元数据文件失败 {metadata_filename}: {e}")
                        else:
                            # 向后兼容：尝试旧格式的元数据文件
                            if filename.startswith('result_') and '_' in filename:
                                unique_id = filename.split('_')[1]
                                old_metadata_filename = f"metadata_{unique_id}.json"
                                old_metadata_path = os.path.join(output_dir, old_metadata_filename)
                                if os.path.exists(old_metadata_path):
                                    try:
                                        with open(old_metadata_path, 'r', encoding='utf-8') as f:
                                            metadata = json.load(f)
                                    except Exception as e:
                                        logger.warning(f"读取旧格式元数据文件失败 {old_metadata_filename}: {e}")
                    
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
    """获取单个图片的详细元数据（兼容新旧两种元数据命名）"""
    try:
        output_dir = os.path.join(os.path.dirname(__file__), 'outputs')

        # 1) 新格式：<output_filename>.json（与图片同名）
        name_part, ext = os.path.splitext(filename)
        new_metadata_filename = f"{name_part}.json"
        new_metadata_path = os.path.join(output_dir, new_metadata_filename)
        if os.path.exists(new_metadata_path):
            try:
                with open(new_metadata_path, 'r', encoding='utf-8') as f:
                    metadata = json.load(f)
                return jsonify({'success': True, 'metadata': metadata})
            except Exception as e:
                logger.warning(f"读取新格式元数据失败 {new_metadata_filename}: {e}")

        # 2) 旧格式回退：metadata_<unique_id>.json（从文件名中提取第二段ID）
        unique_id = filename.split('_')[1] if '_' in filename else None
        if unique_id:
            old_metadata_filename = f"metadata_{unique_id}.json"
            old_metadata_path = os.path.join(output_dir, old_metadata_filename)
            if os.path.exists(old_metadata_path):
                try:
                    with open(old_metadata_path, 'r', encoding='utf-8') as f:
                        metadata = json.load(f)
                    return jsonify({'success': True, 'metadata': metadata})
                except Exception as e:
                    logger.warning(f"读取旧格式元数据失败 {old_metadata_filename}: {e}")

        return jsonify({'success': False, 'error': '元数据文件不存在'}), 404
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
        'resize_nodes': [],
        'default_values': {
            'width': 1024,    # 默认值，会被JSON文件中的实际值覆盖
            'height': 1024,   # 默认值，会被JSON文件中的实际值覆盖
            'steps': 20,      # 默认值，会被JSON文件中的实际值覆盖
            'cfg': 1.0,       # 默认值，会被JSON文件中的实际值覆盖
            'seed': -1,       # 默认值，会被JSON文件中的实际值覆盖
            'sampler': 'euler',   # 默认值，会被JSON文件中的实际值覆盖
            'scheduler': 'normal', # 默认值，会被JSON文件中的实际值覆盖
            'denoise': 1.0,       # 默认值，会被JSON文件中的实际值覆盖
            'positive_prompt': '',
            'negative_prompt': ''
        },
        'required_inputs': [],
        'optional_inputs': [],
        'model_loaders': [],
        'controlnet_configs': [],  # 新增：ControlNet配置
        'has_negative_prompt': False,
        # LoRA 相关信息（新增）
        'lora': {
            'has_lora': False,
            'lora_nodes': [],
            'detected_lora_names': [],
            'triggers': []  # 形如 [{ 'lora_name': 'xxx.safetensors', 'triggers': ['word1','word2'] }]
        },
        # 新增：按节点分组的通用参数视图，确保无遗漏
        'node_groups': [],  # 形如 [{ id, type, title, params: [{name,label,kind,default,node_id,widget_index}], order }]
        
        # 新增：输出控制设置
        'output_settings': {
            'has_output_control': False,
            'output_dimensions': {'width': 1024, 'height': 1024},
            'size_control_mode': 'fixed',
            'batch_settings': {'batch_size': 1},
            'connected_primitive_nodes': []  # 连接的PrimitiveNode信息
        }
    }
    
    for node in nodes:
        # UI格式使用type字段
        node_type = node.get('type', '')
        node_id = node.get('id')
        
        # ⚠️ 先进行输出控制检测，避免被后续的过滤逻辑跳过
        if node_type == 'PrimitiveNode':
            title = node.get('title', '').lower()
            widgets_values = node.get('widgets_values', [])
            # 检测width/height的PrimitiveNode用于输出控制
            if title in ['width', 'height'] and len(widgets_values) >= 1:
                analysis['output_settings']['has_output_control'] = True
                analysis['output_settings']['connected_primitive_nodes'].append({
                    'id': node_id,
                    'type': title,
                    'value': widgets_values[0] if len(widgets_values) > 0 else 1024,
                    'mode': widgets_values[1] if len(widgets_values) > 1 else 'fixed'
                })
                # 更新输出尺寸
                if title == 'width':
                    analysis['output_settings']['output_dimensions']['width'] = widgets_values[0]
                elif title == 'height':
                    analysis['output_settings']['output_dimensions']['height'] = widgets_values[0]
                # 更新控制模式
                if len(widgets_values) > 1 and widgets_values[1]:
                    analysis['output_settings']['size_control_mode'] = widgets_values[1]
        
        # 过滤掉应该在专门区域显示的节点类型，避免在node_groups中重复
        excluded_node_types = {
            # 基础参数区的节点
            'BasicScheduler', 'FluxGuidance', 'RandomNoise', 'EmptySD3LatentImage',
            # 模型加载器相关节点
            'ModelSamplingFlux', 'CLIPVisionEncode', 'StyleModelApply',
            'NunchakuFluxDiTLoader', 'DualCLIPLoader', 'VAELoader', 'CLIPVisionLoader', 
            'StyleModelLoader', 'NunchakuFluxLoraLoader',
            # 专用卡片渲染的节点
            'ImageAndMaskResizeNode', 'ImagePadForOutpaint',
            # 不需要用户配置的节点
            'Note', 'BasicGuider', 'SamplerCustomAdvanced', 'VAEDecode', 'SaveImage', 'LoadImage'
        }
        
        # 通用参数采集：将每个节点可编辑的 widgets 映射为通用参数
        try:
            widgets_values = node.get('widgets_values', [])
            inputs = node.get('inputs', []) or []
            # 从 inputs 内的 widget name 顺序推断参数含义；无则用 p0,p1...
            param_names = []
            # 针对部分节点做精确命名，避免把输入连线名（image/mask等）错当参数名
            if 'ImageAndMaskResizeNode' in node_type:
                param_names = ['width', 'height', 'resize_method', 'crop', 'mask_blur_radius']
            elif 'ImagePadForOutpaint' in node_type:
                # ComfyUI 原生参数顺序：left, top, right, bottom, feathering
                param_names = ['left', 'top', 'right', 'bottom', 'feathering']
            else:
                for inp in inputs:
                    if isinstance(inp, dict):
                        w = inp.get('widget') or {}
                        pname = w.get('name') or inp.get('name')
                        if isinstance(pname, str) and pname:
                            param_names.append(pname)
            # 兜底生成参数名
            if not param_names and isinstance(widgets_values, list):
                param_names = [f"p{i}" for i in range(len(widgets_values))]

            # 特殊处理：width/height的PrimitiveNode由输出设置区域处理，完全排除
            if node_type == 'PrimitiveNode':
                title = node.get('title', '').lower()
                if title in ['width', 'height']:
                    continue  # 跳过，由输出设置区域处理

            # 仅当该节点确有 widgets_values 且为列表时纳入，并且不在排除列表中
            if isinstance(widgets_values, list) and len(widgets_values) > 0 and node_type not in excluded_node_types:
                params = []
                for idx, default_val in enumerate(widgets_values):
                    # 过滤明显是系统/占位参数的 None 但保留以免遗漏
                    name = param_names[idx] if idx < len(param_names) else f"p{idx}"
                    
                    # 过滤掉通常是连接输入而非用户可编辑参数的字段
                    connection_inputs = {'model', 'conditioning', 'clip_vision', 'style_model', 'image', 'latent_image', 
                                       'samples', 'vae', 'clip', 'guider', 'sampler', 'sigmas', 'noise', 
                                       'style_model_apply', 'clip_vision_output'}
                    if name in connection_inputs:
                        continue
                    
                    # 特殊处理：对于width/height PrimitiveNode，只显示控制模式（第二个参数），因为数值已在基础参数区
                    if node_type == 'PrimitiveNode':
                        node_title = node.get('title', '').lower()
                        if node_title in ['width', 'height'] and idx == 0:
                            # 跳过第一个参数（数值），因为已在基础参数区显示
                            continue
                    
                    # 为常见参数名提供友好的中文显示
                    param_labels = {
                        'model': '模型',
                        'conditioning': '条件',
                        'clip_vision': '视觉CLIP',
                        'style_model': '风格模型',
                        'text': '文本',
                        'image': '图像',
                        'sampler_name': '采样器',
                        'scheduler': '调度器',
                        'steps': '步数',
                        'cfg': 'CFG引导强度',
                        'denoise': '去噪强度',
                        'guidance': '引导强度',
                        'seed': '随机种子',
                        'width': '宽度',
                        'height': '高度',
                        'batch_size': '批量大小',
                        'filename_prefix': '文件名前缀',
                        'value': '数值',
                        'p1': '控制模式'  # PrimitiveNode的第二个参数通常是控制模式
                    }
                    
                    # 为PrimitiveNode提供更精确的标签
                    if node_type == 'PrimitiveNode':
                        node_title = node.get('title', '').lower()
                        if node_title in ['width', 'height']:
                            if idx == 1:  # 控制模式参数
                                title_map = {'width': '宽度', 'height': '高度'}
                                chinese_title = title_map.get(node_title, node_title.title())
                                label = f"{chinese_title}控制模式"
                            else:
                                label = param_labels.get(name, name)
                        else:
                            label = param_labels.get(name, name)
                    else:
                        label = param_labels.get(name, name)
                    
                    # 推断类型：number / boolean / text / select
                    kind = 'text'
                    if isinstance(default_val, bool):
                        kind = 'boolean'
                    elif isinstance(default_val, (int, float)):
                        kind = 'number'
                    elif isinstance(default_val, str):
                        # 常见选择类值保持为 text，由前端不强约束
                        kind = 'text'
                    params.append({
                        'name': name,
                        'label': label,
                        'kind': kind,
                        'default': default_val,
                        'node_id': node_id,
                        'widget_index': idx
                    })
                # 友好的节点标题
                title = node.get('title') or node_type
                analysis['node_groups'].append({
                    'id': node_id,
                    'type': node_type,
                    'title': title,
                    'order': node.get('order', 9999),
                    'params': params
                })
        except Exception as _e:
            try:
                logger.debug(f"采集节点通用参数失败 node#{node_id} {node_type}: {_e}")
            except Exception:
                pass
        
        # 检查文生图
        if 'KSampler' in node_type:
            analysis['has_text_to_image'] = True
            analysis['type'] = 'text-to-image'
        
        # 输出控制检测已在循环开始时完成
        
        # 检测批量设置
        if 'batch_size' in str(node.get('widgets_values', [])):
            widgets_values = node.get('widgets_values', [])
            # 寻找batch_size参数的位置
            if node_type in WIDGET_INDEX_MAP and 'batch_size' in WIDGET_INDEX_MAP[node_type]:
                batch_idx = WIDGET_INDEX_MAP[node_type]['batch_size']
                if len(widgets_values) > batch_idx:
                    analysis['output_settings']['batch_settings']['batch_size'] = widgets_values[batch_idx]
            
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
        
        # 检查图生图（但不包括LoadImageOutput，它有专门的处理逻辑）
        elif ('LoadImage' in node_type or 'ImageLoader' in node_type) and 'LoadImageOutput' not in node_type:
            analysis['has_image_to_image'] = True
            # 优先判定为图生图（Kontext 等编辑类工作流常同时包含KSampler）
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
            # 优先判定为图生图
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
            
            # 对于Kontext工作流，根据order字段确定哪个是主要的图像输入
            # order较小的节点是主要的图像输入（必须的），order较大的节点是辅助的图像输入（可选的）
            existing_image_inputs = [n for n in analysis['image_inputs'] if n.get('type') == 'image']
            node_order = node.get('order', 999)  # 如果没有order字段，默认为999
            
            # 检查默认图像是否是示例图像
            is_example_image = False
            if has_default_image and widgets_values and len(widgets_values) > 0:
                default_image = widgets_values[0]
                # 如果默认图像文件名包含示例相关的关键词，认为是示例图像
                if any(keyword in default_image.lower() for keyword in ['example', 'demo', 'sample', 'test', 'pikachu', 'yarn']):
                    is_example_image = True
                    logger.info(f"LoadImageOutput 节点 {node_id} 识别为示例图像")
            
            # 分析ImageStitch节点的连接关系来确定必选性
            # 连接到ImageStitch的image1输入的是主图像（必需），连接到image2的是辅助图像（可选）
            is_optional = False
            links = workflow_data.get('links', [])
            
            for link in links:
                # 支持新格式：links = [link_id, src_node_id, src_slot, dst_node_id, dst_slot, type]
                if len(link) >= 6:
                    link_id, src_id, src_slot, dst_id, dst_slot, link_type = link
                    # 检查这个LoadImageOutput节点是否连接到ImageStitch
                    if str(src_id) == str(node_id):
                        # 找到目标节点
                        dst_node = next((n for n in nodes if str(n.get('id')) == str(dst_id)), None)
                        if dst_node and 'ImageStitch' in dst_node.get('type', ''):
                            # 检查连接到ImageStitch的哪个输入
                            if dst_slot == 0:  # image1 - 主图像，必需
                                is_optional = False
                                logger.info(f"LoadImageOutput 节点 {node_id} 连接到ImageStitch的image1 (链接 {link_id})")
                                logger.info(f"LoadImageOutput 节点 {node_id} 连接到ImageStitch的image1，标记为主图像")
                                break
                            elif dst_slot == 1:  # image2 - 辅助图像，可选
                                is_optional = True
                                logger.info(f"LoadImageOutput 节点 {node_id} 连接到ImageStitch的image2 (链接 {link_id})")
                                logger.info(f"LoadImageOutput 节点 {node_id} 连接到ImageStitch的image2，标记为辅助图像")
                                break
            
            if is_optional:
                logger.info(f"LoadImageOutput 节点 {node_id} 标记为可选的输入")
            else:
                logger.info(f"LoadImageOutput 节点 {node_id} 标记为必须的输入")
            
            analysis['image_inputs'].append({
                'node_id': node_id,
                'type': 'image',
                'required': not is_optional,  # 如果有默认图像或是第二个图像，则不是必需的
                'name': f'输入图像 {len(existing_image_inputs) + 1}',
                'description': f'选择要处理的图像{" (可选)" if is_optional else " (必需)"}'
            })
        
        # 识别 ImageAndMaskResizeNode（图像与掩码缩放）
        elif 'ImageAndMaskResizeNode' in node_type:
            widgets_values = node.get('widgets_values', [])
            analysis['resize_nodes'].append({
                'node_id': node_id,
                'type': 'ImageAndMaskResizeNode',
                'name': '图像与掩码缩放',
                'parameters': {
                    'width': widgets_values[0] if len(widgets_values) > 0 else 1024,
                    'height': widgets_values[1] if len(widgets_values) > 1 else 1024,
                    'resize_method': widgets_values[2] if len(widgets_values) > 2 else 'nearest-exact',
                    'crop': widgets_values[3] if len(widgets_values) > 3 else 'center',
                    'mask_blur_radius': widgets_values[4] if len(widgets_values) > 4 else 10
                }
            })
            # 该工作流具有分辨率输入
            analysis['has_resolution'] = True

        # 识别 Outpaint 扩图节点
        elif 'ImagePadForOutpaint' in node_type:
            widgets_values = node.get('widgets_values', [])
            # 顺序按原生节点：左、上、右、下、羽化
            analysis.setdefault('outpaint_nodes', []).append({
                'node_id': node_id,
                'type': 'ImagePadForOutpaint',
                'name': '扩图边距',
                'parameters': {
                    'pad_left': widgets_values[0] if len(widgets_values) > 0 else 0,
                    'pad_up': widgets_values[1] if len(widgets_values) > 1 else 0,
                    'pad_right': widgets_values[2] if len(widgets_values) > 2 else 0,
                    'pad_down': widgets_values[3] if len(widgets_values) > 3 else 0,
                    'feather': widgets_values[4] if len(widgets_values) > 4 else 24
                }
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
        
        # 检查修复（仅标记类型，不新增图像输入，避免与 LoadImage 重复）
        elif 'Inpaint' in node_type:
            analysis['has_inpaint'] = True
            analysis['type'] = 'inpaint'
        
        # 检查超分辨率
        elif 'Upscale' in node_type or 'Upscaler' in node_type:
            analysis['has_upscaler'] = True
        
        # 检查BasicScheduler节点获取steps和scheduler（Redux Dev 等 Flux 工作流）
        elif 'BasicScheduler' in node_type:
            # 标记为文生图工作流，以便前端基础参数区渲染调度器等控件
            analysis['has_text_to_image'] = True
            analysis['type'] = 'text-to-image'
            widgets_values = node.get('widgets_values', [])
            if len(widgets_values) >= 3:
                # scheduler
                try:
                    analysis['default_values']['scheduler'] = str(widgets_values[0]) if widgets_values[0] is not None else 'simple'
                except Exception:
                    analysis['default_values']['scheduler'] = 'simple'
                # steps
                try:
                    analysis['default_values']['steps'] = int(widgets_values[1]) if widgets_values[1] is not None else 20
                except Exception:
                    analysis['default_values']['steps'] = 20
                # denoise（部分工作流默认值为1.0）
                try:
                    analysis['default_values']['denoise'] = float(widgets_values[2]) if widgets_values[2] is not None else 1.0
                except Exception:
                    analysis['default_values']['denoise'] = 1.0
            else:
                analysis['default_values'].setdefault('scheduler', 'simple')
                analysis['default_values'].setdefault('steps', 20)
                analysis['default_values'].setdefault('denoise', 1.0)
        
        # 检查FluxGuidance节点获取 guidance（不再映射到 cfg）
        elif 'FluxGuidance' in node_type:
            widgets_values = node.get('widgets_values', [])
            if len(widgets_values) >= 1:
                try:
                    analysis['default_values']['guidance'] = float(widgets_values[0]) if widgets_values[0] is not None and str(widgets_values[0]).replace('.', '').replace('-', '').isdigit() else 7.0
                except (ValueError, TypeError):
                    analysis['default_values']['guidance'] = 7.0

        # 记录 InpaintModelConditioning 的 noise_mask 默认值
        elif 'InpaintModelConditioning' in node_type:
            widgets_values = node.get('widgets_values', [])
            if len(widgets_values) >= 1:
                try:
                    analysis['default_values']['noise_mask'] = bool(widgets_values[0])
                except Exception:
                    analysis['default_values']['noise_mask'] = False
        
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
            # LoRA 标记与收集
            analysis['lora']['has_lora'] = True
            analysis['lora']['lora_nodes'].append({
                'node_id': node_id,
                'type': 'NunchakuFluxLoraLoader',
                'lora_name': model_loader_info['parameters'].get('lora_name') or ''
            })

        # 检查通用 LoraLoader 节点
        elif 'LoraLoader' in node_type:
            widgets_values = node.get('widgets_values', [])
            model_loader_info = {
                'node_id': node_id,
                'type': 'LoraLoader',
                'name': 'LoRA加载器',
                'parameters': {}
            }
            if len(widgets_values) >= 2:
                model_loader_info['parameters'] = {
                    'lora_name': widgets_values[0] if len(widgets_values) > 0 else '',
                    'strength_model': widgets_values[1] if len(widgets_values) > 1 else 1.0
                }
            analysis['model_loaders'].append(model_loader_info)
            # LoRA 标记与收集
            analysis['lora']['has_lora'] = True
            analysis['lora']['lora_nodes'].append({
                'node_id': node_id,
                'type': 'LoraLoader',
                'lora_name': model_loader_info['parameters'].get('lora_name') or ''
            })

        # 检查通用 CheckpointLoaderSimple 节点
        elif 'CheckpointLoaderSimple' in node_type:
            widgets_values = node.get('widgets_values', [])
            model_loader_info = {
                'node_id': node_id,
                'type': 'CheckpointLoaderSimple',
                'name': 'Checkpoint加载器',
                'parameters': {}
            }
            if len(widgets_values) >= 1:
                model_loader_info['parameters'] = {
                    'ckpt_name': widgets_values[0] if len(widgets_values) > 0 else ''
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

        # 通用兜底：任意包含 Loader 的节点作为潜在模型加载器
        elif 'Loader' in node_type:
            widgets_values = node.get('widgets_values', [])
            widget_inputs = [
                (inp.get('widget', {}) or {}).get('name')
                for inp in node.get('inputs', [])
                if isinstance(inp, dict) and 'widget' in inp and isinstance(inp.get('widget'), dict)
            ]
            if widget_inputs and isinstance(widgets_values, list):
                parameters = {}
                param_order = []
                for idx, pname in enumerate(widget_inputs):
                    if not pname:
                        continue
                    param_order.append(pname)
                    parameters[pname] = widgets_values[idx] if idx < len(widgets_values) else None
                model_loader_info = {
                    'node_id': node_id,
                    'type': node_type,
                    'name': f'{node_type}（模型加载器）',
                    'parameters': parameters,
                    'param_order': param_order
                }
                analysis['model_loaders'].append(model_loader_info)

        # 识别 CLIPVisionLoader（视觉CLIP模型加载）
        elif 'CLIPVisionLoader' in node_type:
            widgets_values = node.get('widgets_values', [])
            model_loader_info = {
                'node_id': node_id,
                'type': 'CLIPVisionLoader',
                'name': 'CLIP视觉模型加载器',
                'parameters': {}
            }
            if len(widgets_values) >= 1:
                model_loader_info['parameters'] = {
                    'clip_name': widgets_values[0] if len(widgets_values) > 0 else ''
                }
            analysis['model_loaders'].append(model_loader_info)

        # 识别 StyleModelLoader（风格模型加载）
        elif 'StyleModelLoader' in node_type:
            widgets_values = node.get('widgets_values', [])
            model_loader_info = {
                'node_id': node_id,
                'type': 'StyleModelLoader',
                'name': '风格模型加载器',
                'parameters': {}
            }
            if len(widgets_values) >= 1:
                model_loader_info['parameters'] = {
                    'style_model_name': widgets_values[0] if len(widgets_values) > 0 else ''
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
    
    # 汇总工作流内的 LoRA 名称并尝试匹配触发词（来自模型目录 .civitai.info 或 .json）
    try:
        if analysis.get('lora', {}).get('has_lora'):
            lora_names = []
            for ln in analysis['lora']['lora_nodes']:
                name = (ln.get('lora_name') or '').strip()
                if name:
                    lora_names.append(name)
            # 去重
            lora_names = sorted(set(lora_names))
            analysis['lora']['detected_lora_names'] = lora_names
            if lora_names:
                triggers = _scan_lora_triggers_from_models(lora_names)
                # 转为列表形式以便前端渲染
                trigger_items = []
                for name in lora_names:
                    words = triggers.get(name) or []
                    if words:
                        trigger_items.append({'lora_name': name, 'triggers': words})
                analysis['lora']['triggers'] = trigger_items
    except Exception as e:
        try:
            logger.warning(f"扫描LoRA触发词时出错: {e}")
        except Exception:
            pass
    
    return analysis


def _scan_lora_triggers_from_models(lora_names):
    """在 ComfyUI/models/loras(或lora) 目录下，尝试读取与 LoRA 文件同名的 .civitai.info 或 .json 文件，
    提取其中的触发词（trainedWords / triggerWords）。
    返回: { lora_filename: [trigger1, trigger2, ...] }
    """
    result = {}
    if not lora_names:
        return result
    try:
        base_dir = '/home/wjx/ComfyUI/models'
        search_dirs = []
        for d in ['loras', 'lora']:
            p = os.path.join(base_dir, d)
            if os.path.isdir(p):
                search_dirs.append(p)
        if not search_dirs:
            return result

        # 为所有 LoRA 文件建立索引：文件名 -> 所在目录绝对路径列表
        from collections import defaultdict
        name_to_dirs = defaultdict(list)
        for root_dir in search_dirs:
            for root, _, files in os.walk(root_dir):
                for fn in files:
                    # 只索引可能的权重文件
                    if fn.lower().endswith(('.safetensors', '.pt', '.bin')):
                        name_to_dirs[fn].append(root)

        for lora_name in lora_names:
            dirs = name_to_dirs.get(lora_name) or []
            if not dirs:
                continue
            # 逐个目录尝试读取 sidecar 信息文件
            base_without_ext, _ = os.path.splitext(lora_name)
            candidates = [
                f"{base_without_ext}.civitai.info",
                f"{base_without_ext}.json",
            ]
            found_words = []
            for d in dirs:
                for cand in candidates:
                    meta_path = os.path.join(d, cand)
                    if not os.path.exists(meta_path):
                        continue
                    try:
                        with open(meta_path, 'r', encoding='utf-8') as f:
                            meta = json.load(f)
                        # 常见字段：trainedWords / triggerWords
                        words = []
                        if isinstance(meta, dict):
                            if isinstance(meta.get('trainedWords'), list):
                                words = [str(x).strip() for x in meta.get('trainedWords') if isinstance(x, (str,int,float))]
                            elif isinstance(meta.get('triggerWords'), list):
                                words = [str(x).strip() for x in meta.get('triggerWords') if isinstance(x, (str,int,float))]
                            # 某些 .json 包在 versions[0].trainedWords
                            elif isinstance(meta.get('versions'), list) and meta['versions']:
                                v0 = meta['versions'][0]
                                if isinstance(v0, dict) and isinstance(v0.get('trainedWords'), list):
                                    words = [str(x).strip() for x in v0.get('trainedWords') if isinstance(x, (str,int,float))]
                        if words:
                            found_words.extend(words)
                    except Exception as _e:
                        try:
                            logger.debug(f"读取LoRA侧信息失败 {meta_path}: {_e}")
                        except Exception:
                            pass
            # 去重并过滤空词
            found_words = [w for w in {w for w in found_words if w}]
            if found_words:
                result[lora_name] = found_words
    except Exception as e:
        try:
            logger.debug(f"扫描LoRA触发词失败: {e}")
        except Exception:
            pass
    return result


@app.route('/api/lora-info')
def get_lora_info():
    """按名称返回 LoRA 的触发词与提示信息。
    请求示例：/api/lora-info?name=foo.safetensors&name=bar.safetensors 或 name=foo,bar
    返回：{ success: true, items: { "foo.safetensors": {"triggers": [...], "tips": [..] }, ... } }
    """
    try:
        names_param = request.args.getlist('name') or []
        if len(names_param) == 1 and ',' in names_param[0]:
            names_param = [x.strip() for x in names_param[0].split(',') if x.strip()]
        lora_names = [n for n in names_param if n]
        if not lora_names:
            return jsonify({'success': False, 'error': '缺少 name 参数'}), 400

        info_map = _scan_lora_info_from_models(lora_names)
        return jsonify({'success': True, 'items': info_map})
    except Exception as e:
        logger.error(f"获取LoRA信息失败: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


def _scan_lora_info_from_models(lora_names):
    """扫描 LoRA 侧信息文件，返回 { name: { triggers: [...], tips: [...] } }"""
    result: Dict[str, Dict[str, Any]] = {}
    if not lora_names:
        return result
    try:
        base_dir = '/home/wjx/ComfyUI/models'
        search_dirs = []
        for d in ['loras', 'lora']:
            p = os.path.join(base_dir, d)
            if os.path.isdir(p):
                search_dirs.append(p)
        if not search_dirs:
            return result

        # 建立文件名到所在目录映射（含无扩展名索引）
        from collections import defaultdict
        name_to_dirs = defaultdict(list)
        stem_to_fullnames = defaultdict(list)
        for root_dir in search_dirs:
            for root, _, files in os.walk(root_dir):
                for fn in files:
                    if fn.lower().endswith(('.safetensors', '.pt', '.bin')):
                        name_to_dirs[fn].append(root)
                        stem, _ext = os.path.splitext(fn)
                        stem_to_fullnames[stem].append(fn)

        for raw in lora_names:
            lora_name = os.path.basename(str(raw or ''))
            lora_name_ci = lora_name.lower()
            # 1) 精确匹配（大小写原样或小写）
            dirs = name_to_dirs.get(lora_name) or name_to_dirs.get(lora_name_ci) or []
            matched_fullname = lora_name if dirs else None
            # 2) 无扩展名匹配
            if not dirs:
                stem = os.path.splitext(lora_name)[0]
                cands = stem_to_fullnames.get(stem) or stem_to_fullnames.get(stem.lower()) or []
                if cands:
                    matched_fullname = cands[0]
                    dirs = name_to_dirs.get(matched_fullname) or []
            # 3) 模糊包含（大小写不敏感）
            if not dirs and lora_name_ci:
                for fn, dlist in name_to_dirs.items():
                    if lora_name_ci in fn.lower():
                        matched_fullname = fn
                        dirs = dlist
                        break
            if not dirs:
                result[raw] = {'triggers': [], 'tips': []}
                continue
            use_name = matched_fullname or lora_name
            base_without_ext, _ = os.path.splitext(use_name)
            candidates = [f"{base_without_ext}.civitai.info", f"{base_without_ext}.json"]
            triggers: List[str] = []
            tips: List[str] = []
            for d in dirs:
                for cand in candidates:
                    meta_path = os.path.join(d, cand)
                    if not os.path.exists(meta_path):
                        continue
                    try:
                        with open(meta_path, 'r', encoding='utf-8') as f:
                            meta = json.load(f)
                        # 触发词
                        w = _extract_lora_triggers_from_meta(meta)
                        if w:
                            triggers.extend(w)
                        # 提示信息
                        t = _extract_lora_tips_from_meta(meta)
                        if t:
                            tips.extend(t)
                    except Exception as _e:
                        try:
                            logger.debug(f"读取LoRA元信息失败 {meta_path}: {_e}")
                        except Exception:
                            pass
            # 去重
            triggers = [w for w in {w.strip() for w in triggers if isinstance(w, str) and w.strip()}]
            tips = [w for w in {w.strip() for w in tips if isinstance(w, str) and w.strip()}]
            result[raw] = {'triggers': triggers, 'tips': tips}
    except Exception as e:
        try:
            logger.debug(f"扫描LoRA信息失败: {e}")
        except Exception:
            pass
    return result


def _extract_lora_triggers_from_meta(meta: Dict[str, Any]) -> List[str]:
    try:
        if not isinstance(meta, dict):
            return []
        if isinstance(meta.get('trainedWords'), list):
            return [str(x) for x in meta['trainedWords'] if isinstance(x, (str, int, float))]
        if isinstance(meta.get('triggerWords'), list):
            return [str(x) for x in meta['triggerWords'] if isinstance(x, (str, int, float))]
        if isinstance(meta.get('versions'), list) and meta['versions']:
            v0 = meta['versions'][0]
            if isinstance(v0, dict) and isinstance(v0.get('trainedWords'), list):
                return [str(x) for x in v0['trainedWords'] if isinstance(x, (str, int, float))]
        return []
    except Exception:
        return []


def _extract_lora_tips_from_meta(meta: Dict[str, Any]) -> List[str]:
    """从元数据提取 tips/usage 信息，返回字符串列表。"""
    try:
        if not isinstance(meta, dict):
            return []
        candidates: List[str] = []
        # 常见字段
        for key in ['tips', 'usage_tips', 'usageTips', 'how_to_use', 'usage', 'notes']:
            v = meta.get(key)
            if isinstance(v, str):
                candidates.append(v)
            elif isinstance(v, list):
                candidates.extend([str(x) for x in v])
        # 退化到描述
        desc = meta.get('description')
        if isinstance(desc, str):
            candidates.append(desc)
        # 版本级别
        if isinstance(meta.get('versions'), list) and meta['versions']:
            v0 = meta['versions'][0]
            if isinstance(v0, dict):
                for key in ['tips', 'usage_tips', 'usageTips', 'notes', 'description']:
                    v = v0.get(key)
                    if isinstance(v, str):
                        candidates.append(v)
                    elif isinstance(v, list):
                        candidates.extend([str(x) for x in v])
        # 规范化：拆行，去空白，限制长度
        lines: List[str] = []
        for c in candidates:
            if not isinstance(c, str):
                continue
            parts = [p.strip('-• \t') for p in str(c).split('\n')]
            for p in parts:
                if p:
                    lines.append(p)
        # 限制最多 12 条
        return lines[:12]
    except Exception:
        return []


@app.route('/api/model-files')
def get_model_files():
    """列出 ComfyUI/models 下可用的模型文件，按子目录分类。
    仅返回文件名，不含路径，便于前端下拉选择。
    """
    try:
        base_dir = '/home/wjx/ComfyUI/models'
        exts = {'.safetensors', '.ckpt', '.pt', '.bin'}
        categories: Dict[str, List[str]] = {}
        if os.path.exists(base_dir):
            for entry in os.listdir(base_dir):
                subdir = os.path.join(base_dir, entry)
                if not os.path.isdir(subdir):
                    continue
                files: List[str] = []
                for root, _, filenames in os.walk(subdir):
                    for fn in filenames:
                        _, ext = os.path.splitext(fn)
                        if ext.lower() in exts:
                            files.append(fn)
                # 去重并排序
                if files:
                    categories[entry] = sorted(sorted(set(files)))

        # 目录别名与合并，兼容 ComfyUI 常见目录结构
        def merged(*keys: str) -> List[str]:
            seen = set()
            out: List[str] = []
            for k in keys:
                for v in categories.get(k, []) or []:
                    if v not in seen:
                        seen.add(v)
                        out.append(v)
            return sorted(out)

        # 生成规范键（兼容更多常见目录）
        norm: Dict[str, List[str]] = {}
        norm['clip'] = merged('clip', 'text_encoders')
        norm['clip_vision'] = merged('clip_vision')
        norm['vae'] = merged('vae')
        # 主模型/检查点：尽可能互相兼容
        norm['unet'] = merged('unet', 'diffusion_models', 'checkpoints')
        norm['checkpoints'] = merged('checkpoints', 'unet', 'diffusion_models')
        # LoRA 目录兼容单复数
        norm['loras'] = merged('loras', 'lora')
        norm['lora'] = merged('lora', 'loras')
        # ControlNet 常见目录
        norm['controlnet'] = merged('controlnet', 'controlnet_models', 'controlnets')
        # 风格模型（若无专用目录则为空）
        norm['style_models'] = merged('style_models')

        # 用规范键覆盖/补充
        for k, v in norm.items():
            categories[k] = v

        # 常见类别兜底键名，确保前端有稳定键
        for key in ['clip', 'clip_vision', 'vae', 'unet', 'checkpoints', 'loras', 'lora', 'style_models', 'controlnet']:
            categories.setdefault(key, [])

        return jsonify({'success': True, 'categories': categories})
    except Exception as e:
        logger.error(f"扫描模型文件失败: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

if __name__ == '__main__':
    logger.info(f"启动ComfyUI Web服务...")
    logger.info(f"Workflow目录: {WORKFLOW_DIR}")
    logger.info(f"服务地址: http://{HOST}:{PORT}")
    
    # 检查workflow目录
    if not os.path.exists(WORKFLOW_DIR):
        logger.warning(f"创建workflow目录: {WORKFLOW_DIR}")
        os.makedirs(WORKFLOW_DIR, exist_ok=True)
    
    app.run(host=HOST, port=PORT, debug=True, threaded=True)