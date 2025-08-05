#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ComfyUI Web Service 配置文件
"""

import os
from pathlib import Path

class Config:
    """基础配置类"""
    
    # 基础路径
    BASE_DIR = Path(__file__).parent
    WORKFLOW_DIR = BASE_DIR / 'workflow'
    
    # 服务器配置
    HOST = os.getenv('HOST', '0.0.0.0')
    PORT = int(os.getenv('PORT', 5000))
    DEBUG = os.getenv('DEBUG', 'False').lower() in ['true', '1', 'yes']
    
    # ComfyUI配置
    COMFYUI_PATH = os.getenv('COMFYUI_PATH', '/path/to/ComfyUI')
    COMFYUI_OUTPUT_DIR = os.getenv('COMFYUI_OUTPUT_DIR', './output')
    
    # 日志配置
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    LOG_FILE = os.getenv('LOG_FILE', 'comfy-web-service.log')
    
    # 安全配置
    SECRET_KEY = os.getenv('SECRET_KEY', 'comfy-web-service-secret-key-change-in-production')
    
    # 任务配置
    MAX_CONCURRENT_TASKS = int(os.getenv('MAX_CONCURRENT_TASKS', 3))
    TASK_TIMEOUT = int(os.getenv('TASK_TIMEOUT', 3600))  # 1小时
    
    # 文件上传配置
    MAX_CONTENT_LENGTH = int(os.getenv('MAX_CONTENT_LENGTH', 16 * 1024 * 1024))  # 16MB
    UPLOAD_FOLDER = BASE_DIR / 'uploads'
    
    @classmethod
    def init_directories(cls):
        """初始化必要的目录"""
        directories = [
            cls.WORKFLOW_DIR,
            cls.UPLOAD_FOLDER,
            Path(cls.COMFYUI_OUTPUT_DIR)
        ]
        
        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)
    
    @classmethod
    def validate_config(cls):
        """验证配置"""
        errors = []
        
        if not Path(cls.COMFYUI_PATH).exists():
            errors.append(f"ComfyUI路径不存在: {cls.COMFYUI_PATH}")
        
        if not cls.WORKFLOW_DIR.exists():
            errors.append(f"Workflow目录不存在: {cls.WORKFLOW_DIR}")
        
        return errors

class DevelopmentConfig(Config):
    """开发环境配置"""
    DEBUG = True
    LOG_LEVEL = 'DEBUG'

class ProductionConfig(Config):
    """生产环境配置"""
    DEBUG = False
    LOG_LEVEL = 'WARNING'

class TestingConfig(Config):
    """测试环境配置"""
    TESTING = True
    DEBUG = True

# 配置映射
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}