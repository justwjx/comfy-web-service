// ComfyUI工作流管理器 - 优化版本

class ComfyWebApp {
    constructor() {
        this.workflows = [];
        this.selectedWorkflow = null;
        this.currentPage = 'selection';
        this.currentTask = null;
        
        console.log('ComfyWebApp 初始化');
        this.init();
    }
    
    init() {
        this.checkServerStatus();
        this.loadWorkflows();
        this.setupEventListeners();
        this.setupConfigEventListeners();
        this.checkUrlParams();
    }
    
    setupEventListeners() {
        const searchInput = document.getElementById('searchInput');
        if (searchInput) {
            searchInput.addEventListener('input', () => this.filterWorkflows());
        }
        
        // 快速选择工作流
        const workflowSelect = document.getElementById('workflowSelect');
        if (workflowSelect) {
            workflowSelect.addEventListener('change', (e) => this.quickSelectWorkflow(e.target.value));
        }
    }
    
    setupConfigEventListeners() {
        // 配置页面选项卡切换
        const navItems = document.querySelectorAll('.nav-item');
        navItems.forEach(item => {
            item.addEventListener('click', (e) => {
                const section = e.currentTarget.dataset.section;
                this.switchConfigSection(section);
            });
        });
        
        // 开始配置按钮
        const startConfigBtn = document.getElementById('startConfigBtn');
        if (startConfigBtn) {
            startConfigBtn.addEventListener('click', () => this.startWorkflow());
        }
        
        // 分享链接按钮
        const shareLinkBtn = document.getElementById('shareLinkBtn');
        if (shareLinkBtn) {
            shareLinkBtn.addEventListener('click', () => this.shareWorkflowLink());
        }
        
        // 开始生成按钮
        const startGenerationBtn = document.getElementById('startGenerationBtn');
        if (startGenerationBtn) {
            startGenerationBtn.addEventListener('click', () => this.startGeneration());
        }
        
        // 重置按钮
        const resetBtn = document.getElementById('resetBtn');
        if (resetBtn) {
            resetBtn.addEventListener('click', () => this.resetToDefaults());
        }
    }
    
    checkUrlParams() {
        const urlParams = new URLSearchParams(window.location.search);
        const workflow = urlParams.get('workflow');
        if (workflow) {
            // 延迟执行，确保工作流已加载
            setTimeout(() => {
                this.quickSelectWorkflow(workflow);
            }, 1000);
        }
    }
    
    switchConfigSection(sectionName) {
        // 移除所有活动状态
        document.querySelectorAll('.nav-item').forEach(item => {
            item.classList.remove('active');
        });
        document.querySelectorAll('.config-section').forEach(section => {
            section.classList.remove('active');
        });
        
        // 激活选中的选项卡
        const navItem = document.querySelector(`[data-section="${sectionName}"]`);
        const section = document.getElementById(`${sectionName}Section`);
        
        if (navItem) navItem.classList.add('active');
        if (section) section.classList.add('active');
        
        // 特殊处理：如果切换到模型加载器配置，确保内容已生成
        if (sectionName === 'modelLoaders' && this.selectedWorkflow) {
            // 重新加载工作流详情以确保模型加载器配置是最新的
            this.loadWorkflowDetails(this.selectedWorkflow.filename);
        }
    }
    
    quickSelectWorkflow(filename) {
        if (!filename) {
            this.hideWorkflowIntro();
            return;
        }
        
        const workflow = this.workflows.find(w => w.filename === filename);
        if (workflow) {
            this.selectedWorkflow = workflow;
            this.showWorkflowIntro(workflow);
        }
    }
    
    showWorkflowIntro(workflow) {
        const introCard = document.getElementById('selectedWorkflowIntro');
        const introTitle = document.getElementById('introTitle');
        const introType = document.getElementById('introType');
        const introDescription = document.getElementById('introDescription');
        const introFeatures = document.getElementById('introFeatures');
        const shareLinkBtn = document.getElementById('shareLinkBtn');
        
        if (introCard) introCard.style.display = 'block';
        if (introTitle) introTitle.textContent = workflow.name;
        if (introType) introType.textContent = this.getWorkflowTypeName(this.getWorkflowType(workflow.filename));
        if (introDescription) introDescription.textContent = workflow.description;
        
        // 显示分享链接按钮
        if (shareLinkBtn) shareLinkBtn.style.display = 'inline-flex';
        
        // 生成功能标签
        const tags = this.extractTags(workflow.filename);
        if (introFeatures) {
            introFeatures.innerHTML = tags.map(tag => 
                `<span class="feature-tag">${tag}</span>`
            ).join('');
        }
    }
    
    hideWorkflowIntro() {
        const introCard = document.getElementById('selectedWorkflowIntro');
        const shareLinkBtn = document.getElementById('shareLinkBtn');
        if (introCard) introCard.style.display = 'none';
        if (shareLinkBtn) shareLinkBtn.style.display = 'none';
    }
    
    shareWorkflowLink() {
        if (!this.selectedWorkflow) return;
        
        const url = `${window.location.origin}${window.location.pathname}?workflow=${encodeURIComponent(this.selectedWorkflow.filename)}`;
        
        // 尝试使用现代浏览器的分享API
        if (navigator.share) {
            navigator.share({
                title: `${this.selectedWorkflow.name} - ComfyUI工作流`,
                text: `使用 ${this.selectedWorkflow.name} 工作流生成AI图像`,
                url: url
            }).catch(err => {
                this.copyToClipboard(url);
            });
        } else {
            this.copyToClipboard(url);
        }
    }
    
    copyToClipboard(text) {
        if (navigator.clipboard) {
            navigator.clipboard.writeText(text).then(() => {
                alert('链接已复制到剪贴板！');
            }).catch(() => {
                this.fallbackCopyToClipboard(text);
            });
        } else {
            this.fallbackCopyToClipboard(text);
        }
    }
    
    fallbackCopyToClipboard(text) {
        const textArea = document.createElement('textarea');
        textArea.value = text;
        document.body.appendChild(textArea);
        textArea.select();
        try {
            document.execCommand('copy');
            alert('链接已复制到剪贴板！');
        } catch (err) {
            alert('复制失败，请手动复制链接：\n' + text);
        }
        document.body.removeChild(textArea);
    }
    
    getWorkflowType(filename) {
        const filenameLower = filename.toLowerCase();
        if (filenameLower.includes('schnell')) return 'text-to-image';
        if (filenameLower.includes('redux')) return 'image-to-image';
        if (filenameLower.includes('fill') || filenameLower.includes('removal')) return 'inpaint';
        if (filenameLower.includes('controlnet')) return 'controlnet';
        if (filenameLower.includes('upscaler')) return 'upscaler';
        return 'text-to-image';
    }
    
    startWorkflow() {
        if (!this.selectedWorkflow) return;
        this.loadWorkflowDetails(this.selectedWorkflow.filename);
    }
    
    async startGeneration() {
        if (!this.selectedWorkflow) {
            alert('请先选择工作流');
            return;
        }
        
        // 收集参数
        const parameters = this.collectParameters();
        
        // 验证必需参数
        if (!parameters.positive_prompt) {
            alert('请输入正面提示词');
            return;
        }
        
        // 验证图像输入（如果有的话）
        if (this.selectedWorkflow.image_inputs && this.selectedWorkflow.image_inputs.length > 0) {
            const requiredImages = this.selectedWorkflow.image_inputs.filter(input => input.required);
            const missingImages = requiredImages.filter(input => 
                !parameters.selected_images || !parameters.selected_images[input.node_id]
            );
            
            if (missingImages.length > 0) {
                alert(`请选择必需的图像输入: ${missingImages.map(img => img.name).join(', ')}`);
                return;
            }
        }
        
        try {
            const response = await fetch('/api/run', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    filename: this.selectedWorkflow.filename,
                    parameters: parameters
                })
            });
            
            const data = await response.json();
            if (data.success) {
                this.currentTask = data.task_id;
                this.showPage('status');
                this.monitorTask(data.task_id);
            } else {
                throw new Error(data.error || '启动任务失败');
            }
        } catch (error) {
            console.error('启动生成失败:', error);
            alert(`启动生成失败: ${error.message}`);
        }
    }
    
    collectParameters() {
        const baseParams = {
            width: parseInt(document.getElementById('width')?.value || this.getDefaultValue('width')),
            height: parseInt(document.getElementById('height')?.value || this.getDefaultValue('height')),
            steps: parseInt(document.getElementById('steps')?.value || this.getDefaultValue('steps')),
            cfg: parseFloat(document.getElementById('cfg')?.value || this.getDefaultValue('cfg')),
            seed: parseInt(document.getElementById('seed')?.value || this.getDefaultValue('seed')),
            sampler: document.getElementById('sampler')?.value || this.getDefaultValue('sampler'),
            positive_prompt: document.getElementById('positivePrompt')?.value || '',
            negative_prompt: document.getElementById('negativePrompt')?.value || ''
        };

        // 收集模型加载器参数
        const modelLoaderParams = {};
        const modelLoaderElements = document.querySelectorAll('[id^="model_type_"], [id^="text_encoder1_"], [id^="text_encoder2_"], [id^="t5_min_length_"], [id^="use_4bit_t5_"], [id^="int4_model_"], [id^="model_path_"], [id^="cache_threshold_"], [id^="attention_"], [id^="cpu_offload_"], [id^="device_id_"], [id^="data_type_"], [id^="i_2_f_mode_"], [id^="lora_name_"], [id^="lora_strength_"], [id^="vae_name_"], [id^="clip_name1_"], [id^="clip_name2_"], [id^="clip_type_"]');
        
        modelLoaderElements.forEach(element => {
            const value = element.type === 'number' ? parseFloat(element.value) : element.value;
            modelLoaderParams[element.name] = value;
        });

        // 收集ControlNet配置参数
        const controlnetParams = {};
        const controlnetElements = document.querySelectorAll('[id^="control_net_name_"], [id^="strength_"], [id^="start_percent_"], [id^="end_percent_"], [id^="union_type_"]');
        
        controlnetElements.forEach(element => {
            const value = element.type === 'number' ? parseFloat(element.value) : element.value;
            controlnetParams[element.name] = value;
        });

        const parameters = {
            ...baseParams,
            model_loaders: modelLoaderParams,
            controlnet_configs: controlnetParams
        };

        // 添加选择的图像
        if (this.selectedImages && Object.keys(this.selectedImages).length > 0) {
            parameters.selected_images = this.selectedImages;
        }

        return parameters;
    }
    
    resetToDefaults() {
        if (!this.selectedWorkflow) return;
        
        // 重新加载工作流详情以重置默认值
        this.loadWorkflowDetails(this.selectedWorkflow.filename);
    }
    
    async monitorTask(taskId) {
        const maxAttempts = 300; // 最多等待5分钟
        let attempts = 0;
        
        const updateProgress = async () => {
            try {
                const response = await fetch(`/api/status/${taskId}`);
                const data = await response.json();
                
                if (data.success) {
                    const task = data.task;
                    const status = task.status;
                    const progress = task.progress || 0;
                    
                    // 更新进度显示
                    const progressBar = document.getElementById('progressBar');
                    const progressText = document.getElementById('progressText');
                    const taskStatus = document.getElementById('taskStatus');
                    const taskWorkflowName = document.getElementById('taskWorkflowName');
                    const taskStartTime = document.getElementById('taskStartTime');
                    
                    if (progressBar) progressBar.style.width = `${progress}%`;
                    if (progressText) progressText.textContent = `${Math.round(progress)}%`;
                    if (taskStatus) taskStatus.textContent = status;
                    if (taskWorkflowName) taskWorkflowName.textContent = task.filename || '-';
                    if (taskStartTime) taskStartTime.textContent = task.start_time ? new Date(task.start_time).toLocaleString() : '-';
                    
                    if (status === 'completed') {
                        this.showTaskResults(task);
                        return;
                    } else if (status === 'failed') {
                        this.showTaskError(task.error || '任务执行失败');
                        return;
                    }
                }
                
                attempts++;
                if (attempts < maxAttempts) {
                    setTimeout(updateProgress, 2000);
                } else {
                    this.showTaskError('任务超时');
                }
            } catch (error) {
                console.error('监控任务失败:', error);
                this.showTaskError('监控任务失败');
            }
        };
        
        updateProgress();
    }
    
    showTaskResults(task) {
        const taskOutput = document.getElementById('taskOutput');
        const outputImages = document.getElementById('outputImages');
        const outputInfo = document.getElementById('outputInfo');
        
        if (taskOutput) taskOutput.style.display = 'block';
        
        // 显示生成的图像
        if (outputImages && task.image_url) {
            outputImages.innerHTML = `
                <div class="output-image">
                    <img src="${task.image_url}" alt="生成结果" onclick="window.open('${task.image_url}', '_blank')">
                    <div class="image-actions">
                        <button class="btn btn-sm btn-primary" onclick="window.open('${task.image_url}', '_blank')">
                            <i class="fas fa-external-link-alt"></i> 查看大图
                        </button>
                        <button class="btn btn-sm btn-secondary" onclick="app.downloadImage('${task.image_url}')">
                            <i class="fas fa-download"></i> 下载
                        </button>
                    </div>
                </div>
            `;
        }
        
        // 显示生成信息
        if (outputInfo) {
            outputInfo.innerHTML = `
                <div class="info-item">
                    <strong>工作流:</strong> ${task.filename}
                </div>
                <div class="info-item">
                    <strong>生成时间:</strong> ${task.end_time ? new Date(task.end_time).toLocaleString() : new Date().toLocaleString()}
                </div>
                <div class="info-item">
                    <strong>执行时间:</strong> ${task.start_time && task.end_time ? 
                        Math.round((new Date(task.end_time) - new Date(task.start_time)) / 1000) + '秒' : '-'}
                </div>
                <div class="info-item">
                    <strong>输出信息:</strong> ${task.output || '任务完成'}
                </div>
            `;
        }
    }
    
    downloadImage(imageUrl) {
        const link = document.createElement('a');
        link.href = imageUrl;
        link.download = imageUrl.split('/').pop() || 'generated_image.png';
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
    }
    
    showTaskError(error) {
        const taskError = document.getElementById('taskError');
        const errorContent = document.getElementById('errorContent');
        
        if (taskError) taskError.style.display = 'block';
        if (errorContent) errorContent.innerHTML = `<p>${error}</p>`;
    }
    
    backToParameterConfig() {
        this.showPage('config');
    }
    
    insertPromptTemplate(type) {
        const textarea = document.getElementById('positivePrompt');
        if (!textarea) return;
        
        const templates = {
            portrait: 'portrait of a beautiful woman, detailed face, professional photography, 8k uhd',
            landscape: 'beautiful landscape, mountains, sunset, golden hour, cinematic lighting',
            anime: 'anime style, cute character, vibrant colors, detailed illustration'
        };
        
        const template = templates[type];
        if (template) {
            textarea.value = template;
        }
    }
    
    insertNegativeTemplate() {
        const textarea = document.getElementById('negativePrompt');
        if (!textarea) return;
        
        const negativePrompt = 'blurry, low quality, distorted, deformed, ugly, bad anatomy';
        textarea.value = negativePrompt;
    }
    
    async checkServerStatus() {
        // 服务器状态检查现在在loadWorkflows中并行进行
        // 这里只设置初始状态
        const statusElement = document.getElementById('serverStatus');
        const statusText = statusElement?.querySelector('.status-text');
        if (statusText) statusText.textContent = '正在连接...';
    }
    
    async loadWorkflows() {
        this.showLoading();
        
        try {
            // 并行检查服务器状态和加载工作流
            const [workflowResponse, statusResponse] = await Promise.all([
                fetch('/api/workflows'),
                fetch('/api/comfyui/status')
            ]);
            
            if (!workflowResponse.ok) throw new Error(`HTTP ${workflowResponse.status}: ${workflowResponse.statusText}`);
            
            const data = await workflowResponse.json();
            if (data.success) {
                this.workflows = data.workflows || [];
                this.renderWorkflows();
                this.populateWorkflowSelect();
                this.showPage('selection');
                
                // 更新服务器状态
                this.updateServerStatus(statusResponse);
            } else {
                throw new Error(data.error || '加载失败');
            }
        } catch (error) {
            console.error('加载工作流失败:', error);
            this.showError(`加载失败: ${error.message}`);
        }
    }
    
    async updateServerStatus(statusResponse) {
        try {
            const statusData = await statusResponse.json();
            const statusElement = document.getElementById('serverStatus');
            const statusDot = statusElement?.querySelector('.status-dot');
            const statusText = statusElement?.querySelector('.status-text');
            
            if (statusData.success && statusData.connected) {
                statusDot?.classList.remove('error');
                statusText && (statusText.textContent = '服务正常 (ComfyUI已连接)');
            } else {
                statusDot?.classList.add('error');
                statusText && (statusText.textContent = 'ComfyUI未连接');
            }
        } catch (error) {
            console.error('更新服务器状态失败:', error);
        }
    }
    
    populateWorkflowSelect() {
        const select = document.getElementById('workflowSelect');
        if (!select) return;
        
        // 清空现有选项
        select.innerHTML = '<option value="">请选择工作流...</option>';
        
        // 添加工作流选项
        this.workflows.forEach(workflow => {
            const option = document.createElement('option');
            option.value = workflow.filename;
            option.textContent = workflow.name;
            select.appendChild(option);
        });
        
        // 生成快速链接
        this.generateQuickLinks();
    }
    
    generateQuickLinks() {
        const container = document.getElementById('quickLinks');
        if (!container) return;
        
        // 获取前6个最常用的工作流
        const popularWorkflows = this.workflows.slice(0, 6);
        
        const links = popularWorkflows.map(workflow => {
            const type = this.getWorkflowType(workflow.filename);
            const icon = this.getWorkflowIcon(type);
            const shortDesc = this.getShortDescription(workflow.description);
            
            return `
                <a href="?workflow=${encodeURIComponent(workflow.filename)}" class="quick-link-item">
                    <div class="quick-link-icon">
                        <i class="${icon}"></i>
                    </div>
                    <div class="quick-link-content">
                        <h4>${workflow.name}</h4>
                        <p>${shortDesc}</p>
                    </div>
                </a>
            `;
        }).join('');
        
        container.innerHTML = links;
    }
    
    getWorkflowIcon(type) {
        const icons = {
            'text-to-image': 'fas fa-image',
            'image-to-image': 'fas fa-exchange-alt',
            'inpaint': 'fas fa-paint-brush',
            'controlnet': 'fas fa-sliders-h',
            'upscaler': 'fas fa-expand-arrows-alt'
        };
        return icons[type] || 'fas fa-cog';
    }
    
    getShortDescription(description) {
        if (!description) return 'AI图像生成';
        return description.length > 30 ? description.substring(0, 30) + '...' : description;
    }
    
    filterWorkflows() {
        const searchTerm = document.getElementById('searchInput')?.value.toLowerCase() || '';
        const filteredWorkflows = this.workflows.filter(workflow => {
            if (!workflow) return false;
            
            const name = workflow.name || '';
            const filename = workflow.filename || '';
            const description = workflow.description || '';
            
            return name.toLowerCase().includes(searchTerm) ||
                   filename.toLowerCase().includes(searchTerm) ||
                   description.toLowerCase().includes(searchTerm);
        });
        
        this.renderWorkflows(filteredWorkflows);
    }
    
    renderWorkflows(workflows = this.workflows) {
        const container = document.getElementById('workflowCards');
        if (!container) return;
        
        if (workflows.length === 0) {
            container.innerHTML = `
                <div class="empty-state" style="text-align: center; padding: 40px 20px; color: var(--text-secondary); grid-column: 1 / -1;">
                    <i class="fas fa-search" style="font-size: 48px; margin-bottom: 16px; opacity: 0.5;"></i>
                    <h3>没有找到匹配的工作流</h3>
                    <p>尝试调整搜索条件或刷新列表</p>
                </div>
            `;
            return;
        }
        
        container.innerHTML = workflows.map(workflow => {
            if (!workflow || typeof workflow !== 'object') return '';
            
            const safeFilename = String(workflow.filename || '');
            const safeName = String(workflow.name || '未命名');
            const safeDescription = String(workflow.description || '暂无描述');
            const safeFileSize = String(workflow.file_size || '未知');
            const safeNodeCount = Number(workflow.node_count || 0);
            const safeRevision = Number(workflow.revision || 0);
            
            if (!safeFilename) return '';
            
            const tags = this.extractTags(safeFilename);
            const tagHtml = tags.map(tag => `<span class="feature-tag">${this.escapeHtml(tag)}</span>`).join('');
            const escapedFilename = this.escapeHtml(safeFilename).replace(/'/g, '&apos;');
            
            return `
                <div class="workflow-card" onclick="app.selectWorkflow('${escapedFilename}')">
                    <div class="workflow-header">
                        <h3 class="workflow-name">${this.escapeHtml(safeName)}</h3>
                        <span class="workflow-badge">${safeNodeCount} 节点</span>
                    </div>
                    
                    <div class="workflow-description-section">
                        <p class="workflow-description">${this.escapeHtml(safeDescription)}</p>
                        ${tagHtml ? `<div class="feature-tags">${tagHtml}</div>` : ''}
                    </div>
                    
                    <div class="workflow-meta">
                        <div class="meta-item">
                            <i class="fas fa-file"></i>
                            <span>${this.escapeHtml(safeFileSize)}</span>
                        </div>
                        <div class="meta-item">
                            <i class="fas fa-code-branch"></i>
                            <span>v${safeRevision}</span>
                        </div>
                        <div class="meta-item">
                            <i class="fas fa-layer-group"></i>
                            <span>${safeNodeCount} 节点</span>
                        </div>
                    </div>
                    
                    <div class="workflow-actions">
                        <button class="btn btn-primary" onclick="event.stopPropagation(); app.selectWorkflow('${escapedFilename}')">
                            <i class="fas fa-cog"></i>
                            配置参数
                        </button>
                        <button class="btn btn-secondary" onclick="event.stopPropagation(); app.viewWorkflowDetails('${escapedFilename}')">
                            <i class="fas fa-info-circle"></i>
                            详情
                        </button>
                    </div>
                </div>
            `;
        }).filter(html => html).join('');
    }
    
    async selectWorkflow(filename) {
        try {
            if (!filename || typeof filename !== 'string') {
                this.showError('选择的工作流无效');
                return;
            }
            
            const decodedFilename = filename.replace(/&apos;/g, "'").replace(/&quot;/g, '"').replace(/&amp;/g, '&').replace(/&lt;/g, '<').replace(/&gt;/g, '>');
            
            const workflow = this.workflows.find(w => {
                return w && typeof w === 'object' && w.filename && 
                       (w.filename === filename || w.filename === decodedFilename);
            });
            
            if (!workflow) {
                this.showError(`找不到工作流: ${filename}`);
                return;
            }
            
            this.selectedWorkflow = workflow;
            await this.loadWorkflowDetails(workflow.filename);
            
        } catch (error) {
            console.error('选择工作流出错:', error);
            this.showError('选择工作流时出错');
        }
    }
    
    async loadWorkflowDetails(filename) {
        try {
            const response = await fetch(`/api/analyze-workflow/${encodeURIComponent(filename)}`);
            if (!response.ok) throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            
            const data = await response.json();
            if (data.success) {
                this.showParameterConfig(data.analysis);
            } else {
                throw new Error(data.error || '获取工作流详情失败');
            }
        } catch (error) {
            console.error('加载工作流详情失败:', error);
            this.showError('加载工作流详情失败');
        }
    }
    
    showParameterConfig(analysis) {
        const configWorkflowName = document.getElementById('configWorkflowName');
        const configWorkflowType = document.getElementById('configWorkflowType');
        
        if (configWorkflowName) configWorkflowName.textContent = this.selectedWorkflow.name;
        if (configWorkflowType) configWorkflowType.textContent = this.getWorkflowTypeName(analysis.type);
        
        this.setDefaultValues(analysis.default_values);
        this.generateImageInputs(analysis.image_inputs);
        this.generateModelLoaders(analysis.model_loaders);
        this.generateControlNetConfigs(analysis.controlnet_configs);
        this.toggleNegativePrompt(analysis.has_negative_prompt);
        
        // 立即显示所有配置选项，不再需要点击切换
        this.showAllConfigSections();
        
        this.showPage('config');
    }
    
    showAllConfigSections() {
        // 显示所有配置区域
        const sections = ['promptSection', 'imageSection', 'modelLoadersSection', 'controlnetConfigsSection'];
        sections.forEach(sectionId => {
            const section = document.getElementById(sectionId);
            if (section) {
                section.style.display = 'block';
            }
        });
        
        // 更新导航状态
        const navItems = document.querySelectorAll('.nav-item');
        navItems.forEach(item => {
            item.classList.add('active');
        });
    }
    
    setDefaultValues(defaults) {
        const elements = {
            width: document.getElementById('width'),
            height: document.getElementById('height'),
            steps: document.getElementById('steps'),
            cfg: document.getElementById('cfg'),
            seed: document.getElementById('seed'),
            sampler: document.getElementById('sampler'),
            positivePrompt: document.getElementById('positivePrompt'),
            negativePrompt: document.getElementById('negativePrompt')
        };
        
        const defaultElements = {
            width: document.getElementById('defaultWidth'),
            height: document.getElementById('defaultHeight'),
            steps: document.getElementById('defaultSteps'),
            cfg: document.getElementById('defaultCfg'),
            seed: document.getElementById('defaultSeed'),
            sampler: document.getElementById('defaultSampler')
        };
        
        Object.keys(elements).forEach(key => {
            const element = elements[key];
            const defaultElement = defaultElements[key];
            // 优先使用JSON文件中的默认值，如果没有则使用硬编码默认值
            const defaultValue = defaults[key] !== undefined ? defaults[key] : this.getDefaultValue(key);
            
            if (element) {
                element.value = defaultValue;
                // 触发change事件以确保UI更新
                element.dispatchEvent(new Event('change', { bubbles: true }));
            }
            if (defaultElement) defaultElement.textContent = defaultValue;
        });
        
        console.log('设置默认值:', defaults);
    }
    
    getDefaultValue(key) {
        const defaults = {
            width: 1024,  // 默认值，会被JSON文件中的实际值覆盖
            height: 1024,  // 默认值，会被JSON文件中的实际值覆盖
            steps: 20,     // 默认值，会被JSON文件中的实际值覆盖
            cfg: 1.0,      // 默认值，会被JSON文件中的实际值覆盖
            seed: -1,      // 默认值，会被JSON文件中的实际值覆盖
            sampler: 'euler' // 默认值，会被JSON文件中的实际值覆盖
        };
        return defaults[key] || '';
    }
    
    generateImageInputs(imageInputs) {
        const container = document.getElementById('imageInputs');
        if (!container) return;
        
        if (!imageInputs || imageInputs.length === 0) {
            container.innerHTML = `
                <div class="no-image-inputs">
                    <i class="fas fa-info-circle"></i>
                    <p>此工作流不需要图像输入</p>
                </div>
            `;
            return;
        }
        
        container.innerHTML = imageInputs.map(input => `
            <div class="image-input-group">
                <div class="input-header">
                    <h4>${input.name}</h4>
                    <span class="input-type">${input.type}</span>
                    ${input.required ? '<span class="required-badge">必需</span>' : '<span class="optional-badge">可选</span>'}
                </div>
                <p class="input-description">${input.description}</p>
                <div class="image-selector">
                    <button type="button" class="btn btn-secondary" onclick="app.showImageSelectModal('${input.node_id}', '${input.type}')">
                        <i class="fas fa-image"></i>
                        选择图像
                    </button>
                    <div class="selected-image" id="selected-${input.node_id}" style="display: none;">
                        <img src="" alt="已选择的图像" id="preview-${input.node_id}">
                        <button type="button" class="btn btn-sm btn-secondary" onclick="app.clearImageSelection('${input.node_id}')">
                            <i class="fas fa-times"></i>
                        </button>
                    </div>
                </div>
            </div>
        `).join('');
    }

    // 图像选择模态框相关函数
    showImageSelectModal(nodeId, imageType) {
        this.currentImageNodeId = nodeId;
        this.currentImageType = imageType;
        
        const modal = document.getElementById('imageSelectModal');
        if (modal) {
            modal.style.display = 'flex';
            this.loadImages();
            this.setupImageModalEvents();
        }
    }

    hideImageSelectModal() {
        const modal = document.getElementById('imageSelectModal');
        if (modal) {
            modal.style.display = 'none';
        }
    }

    async loadImages() {
        try {
            const response = await fetch('/api/images');
            const data = await response.json();
            
            if (data.success) {
                this.renderImageTabs(data.images);
            } else {
                console.error('加载图像失败:', data.error);
            }
        } catch (error) {
            console.error('加载图像失败:', error);
        }
    }

    renderImageTabs(images) {
        // 渲染已上传的图像
        const uploadedContainer = document.getElementById('uploadedImages');
        if (uploadedContainer) {
            if (images.uploaded && images.uploaded.length > 0) {
                uploadedContainer.innerHTML = images.uploaded.map(img => `
                    <div class="image-item" onclick="app.selectImage('${img.path}', '${img.name}', 'uploaded')">
                        <img src="/outputs/${img.path}" alt="${img.name}">
                        <div class="image-info">
                            <span class="image-name">${img.name}</span>
                            <span class="image-size">${this.formatFileSize(img.size)}</span>
                        </div>
                    </div>
                `).join('');
            } else {
                uploadedContainer.innerHTML = `
                    <div class="no-images">
                        <i class="fas fa-image"></i>
                        <p>暂无已上传的图像</p>
                    </div>
                `;
            }
        }

        // 渲染已生成的图像
        const generatedContainer = document.getElementById('generatedImages');
        if (generatedContainer) {
            if (images.generated && images.generated.length > 0) {
                generatedContainer.innerHTML = images.generated.map(img => `
                    <div class="image-item" onclick="app.selectImage('${img.path}', '${img.name}', 'generated')">
                        <img src="/outputs/${img.path}" alt="${img.name}">
                        <div class="image-info">
                            <span class="image-name">${img.name}</span>
                            <span class="image-size">${this.formatFileSize(img.size)}</span>
                        </div>
                    </div>
                `).join('');
            } else {
                generatedContainer.innerHTML = `
                    <div class="no-images">
                        <i class="fas fa-image"></i>
                        <p>暂无已生成的图像</p>
                    </div>
                `;
            }
        }
    }

    formatFileSize(bytes) {
        if (bytes === 0) return '0 B';
        const k = 1024;
        const sizes = ['B', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }

    selectImage(imagePath, imageName, source) {
        // 存储选择的图像信息
        if (!this.selectedImages) {
            this.selectedImages = {};
        }
        
        this.selectedImages[this.currentImageNodeId] = {
            path: imagePath,
            name: imageName,
            source: source,
            type: this.currentImageType
        };

        // 更新UI显示
        const selectedDiv = document.getElementById(`selected-${this.currentImageNodeId}`);
        const previewImg = document.getElementById(`preview-${this.currentImageNodeId}`);
        
        if (selectedDiv && previewImg) {
            previewImg.src = `/outputs/${imagePath}`;
            selectedDiv.style.display = 'flex';
        }

        // 关闭模态框
        this.hideImageSelectModal();
    }

    clearImageSelection(nodeId) {
        // 清除选择的图像
        if (this.selectedImages && this.selectedImages[nodeId]) {
            delete this.selectedImages[nodeId];
        }

        // 更新UI显示
        const selectedDiv = document.getElementById(`selected-${nodeId}`);
        if (selectedDiv) {
            selectedDiv.style.display = 'none';
        }
    }

    setupImageModalEvents() {
        // 设置模态框关闭事件
        const modal = document.getElementById('imageSelectModal');
        const closeBtn = modal?.querySelector('.close-btn');
        
        if (closeBtn) {
            closeBtn.onclick = () => this.hideImageSelectModal();
        }

        // 点击模态框背景关闭
        if (modal) {
            modal.onclick = (e) => {
                if (e.target === modal) {
                    this.hideImageSelectModal();
                }
            };
        }

        // 设置标签页切换事件
        const tabBtns = modal?.querySelectorAll('.tab-btn');
        if (tabBtns) {
            tabBtns.forEach(btn => {
                btn.onclick = () => this.switchImageTab(btn.dataset.tab);
            });
        }

        // 设置文件上传事件
        const uploadInput = document.getElementById('imageUploadInput');
        if (uploadInput) {
            uploadInput.onchange = (e) => this.handleImageUpload(e);
        }

        // 设置拖拽上传事件
        const uploadArea = modal?.querySelector('.upload-area');
        if (uploadArea) {
            uploadArea.ondragover = (e) => {
                e.preventDefault();
                uploadArea.classList.add('drag-over');
            };
            
            uploadArea.ondragleave = () => {
                uploadArea.classList.remove('drag-over');
            };
            
            uploadArea.ondrop = (e) => {
                e.preventDefault();
                uploadArea.classList.remove('drag-over');
                this.handleFileDrop(e);
            };
        }
    }

    switchImageTab(tabName) {
        // 更新标签页状态
        const tabBtns = document.querySelectorAll('.tab-btn');
        tabBtns.forEach(btn => {
            btn.classList.toggle('active', btn.dataset.tab === tabName);
        });

        // 更新内容区域
        const contentAreas = ['uploadedImages', 'generatedImages', 'uploadNewImage'];
        contentAreas.forEach(areaId => {
            const area = document.getElementById(areaId);
            if (area) {
                area.classList.toggle('active', areaId === `${tabName}Images` || areaId === 'uploadNewImage');
            }
        });
    }

    async handleImageUpload(event) {
        const files = event.target.files;
        if (!files || files.length === 0) return;

        await this.uploadImages(files);
    }

    async handleFileDrop(event) {
        const files = event.dataTransfer.files;
        if (!files || files.length === 0) return;

        await this.uploadImages(files);
    }

    async uploadImages(files) {
        const formData = new FormData();
        for (let i = 0; i < files.length; i++) {
            formData.append('images', files[i]);
        }

        try {
            const response = await fetch('/api/upload', {
                method: 'POST',
                body: formData
            });

            const data = await response.json();
            if (data.success) {
                // 重新加载图像列表
                await this.loadImages();
                // 切换到已上传标签页
                this.switchImageTab('uploaded');
            } else {
                console.error('上传失败:', data.error);
            }
        } catch (error) {
            console.error('上传失败:', error);
        }
    }

    toggleNegativePrompt(hasNegativePrompt) {
        const negativePromptGroup = document.getElementById('negativePromptGroup');
        if (negativePromptGroup) {
            negativePromptGroup.style.display = hasNegativePrompt ? 'block' : 'none';
        }
    }

    generateControlNetConfigs(controlnetConfigs) {
        const container = document.getElementById('controlnetConfigs');
        if (!container) return;
        
        if (!controlnetConfigs || controlnetConfigs.length === 0) {
            container.innerHTML = `
                <div class="no-controlnet-configs">
                    <i class="fas fa-info-circle"></i>
                    <p>此工作流没有可配置的ControlNet参数</p>
                </div>
            `;
            return;
        }
        
        container.innerHTML = controlnetConfigs.map(config => {
            const params = config.parameters;
            let paramHtml = '';
            
            // 根据不同的ControlNet节点类型生成不同的参数配置
            switch (config.type) {
                case 'ControlNetLoader':
                    paramHtml = `
                        <div class="form-group">
                            <label for="control_net_name_${config.node_id}">ControlNet模型</label>
                            <input type="text" id="control_net_name_${config.node_id}" name="control_net_name_${config.node_id}" 
                                   value="${params.control_net_name || ''}" placeholder="输入ControlNet模型文件名">
                        </div>
                    `;
                    break;
                    
                case 'ControlNetApplyAdvanced':
                    paramHtml = `
                        <div class="form-group">
                            <label for="strength_${config.node_id}">ControlNet强度</label>
                            <input type="number" id="strength_${config.node_id}" name="strength_${config.node_id}" 
                                   value="${params.strength || 1.0}" min="0.0" max="2.0" step="0.1">
                        </div>
                        <div class="form-group">
                            <label for="start_percent_${config.node_id}">开始百分比</label>
                            <input type="number" id="start_percent_${config.node_id}" name="start_percent_${config.node_id}" 
                                   value="${params.start_percent || 0.0}" min="0.0" max="1.0" step="0.1">
                        </div>
                        <div class="form-group">
                            <label for="end_percent_${config.node_id}">结束百分比</label>
                            <input type="number" id="end_percent_${config.node_id}" name="end_percent_${config.node_id}" 
                                   value="${params.end_percent || 1.0}" min="0.0" max="1.0" step="0.1">
                        </div>
                    `;
                    break;
                    
                case 'SetUnionControlNetType':
                    paramHtml = `
                        <div class="form-group">
                            <label for="union_type_${config.node_id}">联合类型</label>
                            <select id="union_type_${config.node_id}" name="union_type_${config.node_id}">
                                <option value="union" ${params.union_type === 'union' ? 'selected' : ''}>联合</option>
                                <option value="intersection" ${params.union_type === 'intersection' ? 'selected' : ''}>交集</option>
                                <option value="difference" ${params.union_type === 'difference' ? 'selected' : ''}>差集</option>
                            </select>
                        </div>
                    `;
                    break;
                    
                default:
                    paramHtml = `
                        <div class="form-group">
                            <p>未知的ControlNet节点类型: ${config.type}</p>
                        </div>
                    `;
            }
            
            return `
                <div class="controlnet-config-group">
                    <div class="config-header">
                        <h4>${config.name}</h4>
                        <span class="config-type">${config.type}</span>
                    </div>
                    <div class="config-parameters">
                        ${paramHtml}
                    </div>
                </div>
            `;
        }).join('');
    }

    generateModelLoaders(modelLoaders) {
        const container = document.getElementById('modelLoaders');
        if (!container) return;
        
        if (!modelLoaders || modelLoaders.length === 0) {
            container.innerHTML = `
                <div class="no-model-loaders">
                    <i class="fas fa-info-circle"></i>
                    <p>此工作流没有可配置的模型加载器</p>
                </div>
            `;
            return;
        }
        
        container.innerHTML = modelLoaders.map(loader => {
            const params = loader.parameters;
            let paramHtml = '';
            
            // 根据不同的模型加载器类型生成不同的参数配置
            switch (loader.type) {
                case 'NunchakuTextEncoderLoader':
                    paramHtml = `
                        <div class="form-group">
                            <label for="model_type_${loader.node_id}">模型类型</label>
                            <select id="model_type_${loader.node_id}" name="model_type_${loader.node_id}">
                                <option value="flux" ${params.model_type === 'flux' ? 'selected' : ''}>Flux</option>
                                <option value="sd3" ${params.model_type === 'sd3' ? 'selected' : ''}>SD3</option>
                            </select>
                        </div>
                        <div class="form-group">
                            <label for="text_encoder1_${loader.node_id}">文本编码器1</label>
                            <input type="text" id="text_encoder1_${loader.node_id}" name="text_encoder1_${loader.node_id}" 
                                   value="${params.text_encoder1 || 't5xxl_fp16.safetensors'}" placeholder="t5xxl_fp16.safetensors">
                        </div>
                        <div class="form-group">
                            <label for="text_encoder2_${loader.node_id}">文本编码器2</label>
                            <input type="text" id="text_encoder2_${loader.node_id}" name="text_encoder2_${loader.node_id}" 
                                   value="${params.text_encoder2 || 'clip_l.safetensors'}" placeholder="clip_l.safetensors">
                        </div>
                        <div class="form-group">
                            <label for="t5_min_length_${loader.node_id}">T5最小长度</label>
                            <input type="number" id="t5_min_length_${loader.node_id}" name="t5_min_length_${loader.node_id}" 
                                   value="${params.t5_min_length || 512}" min="1" max="2048">
                        </div>
                        <div class="form-group">
                            <label for="use_4bit_t5_${loader.node_id}">使用4bit T5</label>
                            <select id="use_4bit_t5_${loader.node_id}" name="use_4bit_t5_${loader.node_id}">
                                <option value="disable" ${params.use_4bit_t5 === 'disable' ? 'selected' : ''}>禁用</option>
                                <option value="enable" ${params.use_4bit_t5 === 'enable' ? 'selected' : ''}>启用</option>
                            </select>
                        </div>
                        <div class="form-group">
                            <label for="text_encoder2_${loader.node_id}">INT4模型</label>
                            <select id="int4_model_${loader.node_id}" name="int4_model_${loader.node_id}">
                                <option value="none" ${params.int4_model === 'none' ? 'selected' : ''}>无</option>
                                <option value="auto" ${params.int4_model === 'auto' ? 'selected' : ''}>自动</option>
                            </select>
                        </div>
                    `;
                    break;
                    
                case 'NunchakuFluxDiTLoader':
                    paramHtml = `
                        <div class="form-group">
                            <label for="model_path_${loader.node_id}">模型路径</label>
                            <input type="text" id="model_path_${loader.node_id}" name="model_path_${loader.node_id}" 
                                   value="${params.model_path || 'svdq-int4-flux.1-dev'}" placeholder="svdq-int4-flux.1-dev">
                        </div>
                        <div class="form-group">
                            <label for="cache_threshold_${loader.node_id}">缓存阈值</label>
                            <input type="number" id="cache_threshold_${loader.node_id}" name="cache_threshold_${loader.node_id}" 
                                   value="${params.cache_threshold || 0}" min="0" max="100">
                        </div>
                        <div class="form-group">
                            <label for="attention_${loader.node_id}">注意力机制</label>
                            <select id="attention_${loader.node_id}" name="attention_${loader.node_id}">
                                <option value="nunchaku-fp16" ${params.attention === 'nunchaku-fp16' ? 'selected' : ''}>Nunchaku FP16</option>
                                <option value="flash-attn" ${params.attention === 'flash-attn' ? 'selected' : ''}>Flash Attention</option>
                            </select>
                        </div>
                        <div class="form-group">
                            <label for="cpu_offload_${loader.node_id}">CPU卸载</label>
                            <select id="cpu_offload_${loader.node_id}" name="cpu_offload_${loader.node_id}">
                                <option value="auto" ${params.cpu_offload === 'auto' ? 'selected' : ''}>自动</option>
                                <option value="enabled" ${params.cpu_offload === 'enabled' ? 'selected' : ''}>启用</option>
                                <option value="disabled" ${params.cpu_offload === 'disabled' ? 'selected' : ''}>禁用</option>
                            </select>
                        </div>
                        <div class="form-group">
                            <label for="device_id_${loader.node_id}">设备ID</label>
                            <input type="number" id="device_id_${loader.node_id}" name="device_id_${loader.node_id}" 
                                   value="${params.device_id || 0}" min="0" max="10">
                        </div>
                        <div class="form-group">
                            <label for="data_type_${loader.node_id}">数据类型</label>
                            <select id="data_type_${loader.node_id}" name="data_type_${loader.node_id}">
                                <option value="bfloat16" ${params.data_type === 'bfloat16' ? 'selected' : ''}>BFloat16</option>
                                <option value="float16" ${params.data_type === 'float16' ? 'selected' : ''}>Float16</option>
                                <option value="float32" ${params.data_type === 'float32' ? 'selected' : ''}>Float32</option>
                            </select>
                        </div>
                        <div class="form-group">
                            <label for="i_2_f_mode_${loader.node_id}">I2F模式</label>
                            <select id="i_2_f_mode_${loader.node_id}" name="i_2_f_mode_${loader.node_id}">
                                <option value="enabled" ${params.i_2_f_mode === 'enabled' ? 'selected' : ''}>启用</option>
                                <option value="disabled" ${params.i_2_f_mode === 'disabled' ? 'selected' : ''}>禁用</option>
                            </select>
                        </div>
                    `;
                    break;
                    
                case 'NunchakuFluxLoraLoader':
                    paramHtml = `
                        <div class="form-group">
                            <label for="lora_name_${loader.node_id}">LoRA名称</label>
                            <input type="text" id="lora_name_${loader.node_id}" name="lora_name_${loader.node_id}" 
                                   value="${params.lora_name || ''}" placeholder="输入LoRA文件名">
                        </div>
                        <div class="form-group">
                            <label for="lora_strength_${loader.node_id}">LoRA强度</label>
                            <input type="number" id="lora_strength_${loader.node_id}" name="lora_strength_${loader.node_id}" 
                                   value="${params.lora_strength || 1.0}" min="0.0" max="2.0" step="0.1">
                        </div>
                    `;
                    break;
                    
                case 'VAELoader':
                    paramHtml = `
                        <div class="form-group">
                            <label for="vae_name_${loader.node_id}">VAE名称</label>
                            <input type="text" id="vae_name_${loader.node_id}" name="vae_name_${loader.node_id}" 
                                   value="${params.vae_name || 'ae.safetensors'}" placeholder="ae.safetensors">
                        </div>
                    `;
                    break;
                    
                case 'DualCLIPLoader':
                    paramHtml = `
                        <div class="form-group">
                            <label for="clip_name1_${loader.node_id}">CLIP名称1</label>
                            <input type="text" id="clip_name1_${loader.node_id}" name="clip_name1_${loader.node_id}" 
                                   value="${params.clip_name1 || ''}" placeholder="输入CLIP文件名">
                        </div>
                        <div class="form-group">
                            <label for="clip_name1_${loader.node_id}">CLIP名称2</label>
                            <input type="text" id="clip_name2_${loader.node_id}" name="clip_name2_${loader.node_id}" 
                                   value="${params.clip_name2 || ''}" placeholder="输入CLIP文件名">
                        </div>
                        <div class="form-group">
                            <label for="clip_type_${loader.node_id}">CLIP类型</label>
                            <select id="clip_type_${loader.node_id}" name="clip_type_${loader.node_id}">
                                <option value="normal" ${params.type === 'normal' ? 'selected' : ''}>普通</option>
                                <option value="weighted" ${params.type === 'weighted' ? 'selected' : ''}>加权</option>
                            </select>
                        </div>
                    `;
                    break;
                    
                default:
                    paramHtml = `
                        <div class="form-group">
                            <p>未知的模型加载器类型: ${loader.type}</p>
                        </div>
                    `;
            }
            
            return `
                <div class="model-loader-group">
                    <div class="loader-header">
                        <h4>${loader.name}</h4>
                        <span class="loader-type">${loader.type}</span>
                    </div>
                    <div class="loader-parameters">
                        ${paramHtml}
                    </div>
                </div>
            `;
        }).join('');
    }
    
    getWorkflowTypeName(type) {
        const typeNames = {
            'text-to-image': '文生图',
            'image-to-image': '图生图',
            'controlnet': 'ControlNet控制',
            'inpaint': '图像修复',
            'upscaler': '超分辨率',
            'unknown': '未知类型'
        };
        return typeNames[type] || '未知类型';
    }
    
    showPage(pageName) {
        this.currentPage = pageName;
        
        // 隐藏所有页面和状态
        document.getElementById('loadingState').style.display = 'none';
        document.getElementById('errorState').style.display = 'none';
        document.getElementById('workflowSelectionPage').style.display = 'none';
        document.getElementById('parameterConfigPage').style.display = 'none';
        document.getElementById('taskStatusPage').style.display = 'none';
        
        switch (pageName) {
            case 'selection':
                document.getElementById('workflowSelectionPage').style.display = 'block';
                break;
            case 'config':
                document.getElementById('parameterConfigPage').style.display = 'block';
                break;
            case 'status':
                document.getElementById('taskStatusPage').style.display = 'block';
                break;
        }
    }
    
    backToWorkflowSelection() {
        this.showPage('selection');
        this.selectedWorkflow = null;
    }
    
    showLoading() {
        document.getElementById('loadingState').style.display = 'block';
        document.getElementById('errorState').style.display = 'none';
        document.getElementById('workflowSelectionPage').style.display = 'none';
    }
    
    showError(message) {
        const errorMessageElement = document.getElementById('errorMessage');
        if (errorMessageElement) errorMessageElement.textContent = message || '发生未知错误';
        
        document.getElementById('loadingState').style.display = 'none';
        document.getElementById('errorState').style.display = 'block';
        document.getElementById('workflowSelectionPage').style.display = 'none';
    }
    
    extractTags(filename) {
        const tags = [];
        if (!filename || typeof filename !== 'string') return tags;
        
        const filenameLower = filename.toLowerCase();
        
        if (filenameLower.includes('schnell')) tags.push('快速生成');
        if (filenameLower.includes('dev')) tags.push('高质量');
        if (filenameLower.includes('redux')) tags.push('风格转换');
        if (filenameLower.includes('fill')) tags.push('图像修复');
        if (filenameLower.includes('removal')) tags.push('智能移除');
        if (filenameLower.includes('controlnet')) tags.push('精确控制');
        if (filenameLower.includes('upscaler')) tags.push('超分辨率');
        if (filenameLower.includes('depth')) tags.push('深度控制');
        if (filenameLower.includes('canny')) tags.push('边缘控制');
        if (filenameLower.includes('pulid')) tags.push('面部保持');
        if (filenameLower.includes('lora')) tags.push('LoRA');
        if (filenameLower.includes('turbo')) tags.push('加速版');
        if (filenameLower.includes('kontext')) tags.push('上下文感知');
        
        return tags;
    }
    
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text || '';
        return div.innerHTML;
    }
    
    async viewWorkflowDetails(filename) {
        try {
            const decodedFilename = filename.replace(/&apos;/g, "'").replace(/&quot;/g, '"').replace(/&amp;/g, '&').replace(/&lt;/g, '<').replace(/&gt;/g, '>');
            
            const workflow = this.workflows.find(w => {
                return w && typeof w === 'object' && w.filename && 
                       (w.filename === filename || w.filename === decodedFilename);
            });
            
            if (!workflow) {
                this.showError(`找不到工作流: ${filename}`);
                return;
            }
            
            const safeName = String(workflow.name || '未命名');
            const safeFilename = String(workflow.filename || '未知');
            const safeFileSize = String(workflow.file_size || '未知');
            const safeNodeCount = Number(workflow.node_count || 0);
            const safeRevision = Number(workflow.revision || 0);
            const safeId = String(workflow.id || '未知');
            const safeDescription = String(workflow.description || '暂无描述');
            
            alert(`工作流详情：
名称: ${safeName}
文件: ${safeFilename}
大小: ${safeFileSize}
节点数: ${safeNodeCount}
版本: ${safeRevision}
ID: ${safeId}
描述: ${safeDescription}`);
        } catch (error) {
            console.error('查看工作流详情出错:', error);
            this.showError('查看工作流详情时出错');
        }
    }
}

// 初始化应用
let app;
document.addEventListener('DOMContentLoaded', () => {
    app = new ComfyWebApp();
});
