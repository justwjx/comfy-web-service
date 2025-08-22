// ComfyUI工作流管理器 - 修复版本

class ComfyWebApp {
    constructor() {
        this.workflows = [];
        this.selectedWorkflow = null;
        this.currentPage = 'selection';
        this.currentTask = null;
        this.imageListRefreshTimer = null;
        this.resourceRefreshTimer = null;
        this.workflowTypeCache = {};
        this.maskEditor = {
            tool: 'brush',
            brushSize: 48,
            feather: 24,
            invert: false,
            baseImageUrl: '',
        };
        
        console.log('ComfyWebApp 初始化');
        
        // 使用新的提示词系统
        this.promptSystem = new PromptShortcutSystem();
        this.lastPresetLabel = '';
        this.shortcutContext = {};
        
        // 延迟初始化，确保DOM完全加载
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', () => this.init());
        } else {
            this.init();
        }
    }

    init() {
        console.log('开始初始化...');
        try {
            console.log('检查DOM元素...');
            this.checkDOMElements();
            console.log('检查服务器状态...');
            this.checkServerStatus();
            console.log('加载工作流...');
            this.loadWorkflows();
            console.log('设置事件监听器...');
            this.setupEventListeners();
            console.log('设置配置事件监听器...');
            this.setupConfigEventListeners();
            console.log('检查URL参数...');
            this.checkUrlParams();
            console.log('初始化完成');
        } catch (error) {
            console.error('初始化过程中出错:', error);
            this.showError(`初始化失败: ${error.message}`);
        }
    }
    
    checkDOMElements() {
        const requiredElements = [
            'loadingState',
            'errorState', 
            'workflowSelectionPage',
            'workflowCards'
        ];
        
        const missingElements = requiredElements.filter(id => !document.getElementById(id));
        if (missingElements.length > 0) {
            throw new Error(`缺少必需的DOM元素: ${missingElements.join(', ')}`);
        }
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
        if (shareLinkBtn) shareLinkBtn.style.display = 'block';
        
        // 生成特性标签
        if (introFeatures) {
            const tags = this.extractTags(workflow.filename);
            introFeatures.innerHTML = tags.map(tag => `<span class="feature-tag">${this.escapeHtml(tag)}</span>`).join('');
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
        if (filenameLower.includes('kontext')) return 'image-to-image';
        if (filenameLower.includes('schnell')) return 'text-to-image';
        if (filenameLower.includes('redux')) return 'image-to-image';
        if (filenameLower.includes('fill') || filenameLower.includes('removal')) return 'inpaint';
        if (filenameLower.includes('controlnet')) return 'controlnet';
        if (filenameLower.includes('upscaler')) return 'upscaler';
        return 'text-to-image';
    }
    
    getWorkflowTypeName(type) {
        const typeNames = {
            'text-to-image': '文生图',
            'image-to-image': '图生图',
            'inpaint': '图像修复',
            'controlnet': '精确控制',
            'upscaler': '超分辨率'
        };
        return typeNames[type] || type;
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
        
        try {
            this.showPage('status');
            this.startTaskStatusRefresh();
            
            const response = await fetch('/api/run', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    workflow: this.selectedWorkflow.filename,
                    parameters: parameters
                })
            });
            
            if (!response.ok) throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            
            const data = await response.json();
            if (data.success) {
                this.currentTask = data.task_id;
                this.updateTaskStatus();
            } else {
                throw new Error(data.error || '启动任务失败');
            }
        } catch (error) {
            console.error('启动生成失败:', error);
            this.showError(`启动生成失败: ${error.message}`);
            this.showPage('config');
        }
    }
    
    collectParameters() {
        const parameters = {};
        
        // 基础参数
        const positivePrompt = document.getElementById('positivePrompt');
        const negativePrompt = document.getElementById('negativePrompt');
        const width = document.getElementById('width');
        const height = document.getElementById('height');
        const steps = document.getElementById('steps');
        const cfg = document.getElementById('cfg');
        const seed = document.getElementById('seed');
        
        if (positivePrompt) parameters.positive_prompt = positivePrompt.value;
        if (negativePrompt) parameters.negative_prompt = negativePrompt.value;
        if (width) parameters.width = parseInt(width.value);
        if (height) parameters.height = parseInt(height.value);
        if (steps) parameters.steps = parseInt(steps.value);
        if (cfg) parameters.cfg = parseFloat(cfg.value);
        if (seed) parameters.seed = parseInt(seed.value);
        
        return parameters;
    }
    
    resetToDefaults() {
        if (!this.currentAnalysis || !this.currentAnalysis.default_values) return;
        
        const defaults = this.currentAnalysis.default_values;
        Object.keys(defaults).forEach(key => {
            const element = document.getElementById(key);
            if (element) {
                if (element.type === 'checkbox') {
                    element.checked = !!defaults[key];
                } else {
                    element.value = defaults[key];
                }
            }
        });
    }
    
    filterWorkflows() {
        const searchInput = document.getElementById('searchInput');
        if (!searchInput) return;
        
        const query = searchInput.value.toLowerCase();
        const filteredWorkflows = this.workflows.filter(workflow => {
            return workflow.name.toLowerCase().includes(query) ||
                   workflow.description.toLowerCase().includes(query) ||
                   workflow.filename.toLowerCase().includes(query);
        });
        
        this.renderWorkflows(filteredWorkflows);
    }
    
    async checkServerStatus() {
        const statusElement = document.getElementById('serverStatus');
        const statusText = statusElement?.querySelector('.status-text');
        if (statusText) statusText.textContent = '正在连接...';
    }
    
    async loadWorkflows() {
        console.log('开始加载工作流...');
        this.showLoading();
        
        try {
            console.log('并行调用API...');
            // 并行检查服务器状态和加载工作流
            const [workflowResponse, statusResponse] = await Promise.all([
                fetch('/api/workflows'),
                fetch('/api/comfyui/status')
            ]);
            
            console.log('API调用完成，检查响应...');
            if (!workflowResponse.ok) throw new Error(`HTTP ${workflowResponse.status}: ${workflowResponse.statusText}`);
            
            console.log('解析工作流数据...');
            const data = await workflowResponse.json();
            console.log('工作流数据:', data);
            
            if (data.success) {
                this.workflows = data.workflows || [];
                console.log('工作流数量:', this.workflows.length);
                console.log('渲染工作流列表...');
                this.renderWorkflows();
                console.log('填充工作流选择器...');
                this.populateWorkflowSelect();
                console.log('显示选择页面...');
                this.showPage('selection');
                
                // 更新服务器状态（异步执行，不阻塞页面显示）
                console.log('更新服务器状态...');
                this.updateServerStatus(statusResponse).catch(error => {
                    console.error('更新服务器状态失败:', error);
                });
                console.log('加载工作流完成');
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
    }
    
    renderWorkflows(workflows = this.workflows) {
        const container = document.getElementById('workflowCards');
        if (!container) {
            console.error('找不到workflowCards容器');
            return;
        }
        
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
        // 保存当前分析结果，供其他方法使用
        this.currentAnalysis = analysis;
        
        const configWorkflowName = document.getElementById('configWorkflowName');
        const configWorkflowType = document.getElementById('configWorkflowType');
        
        if (configWorkflowName) configWorkflowName.textContent = this.selectedWorkflow.name;
        if (configWorkflowType) configWorkflowType.textContent = this.getWorkflowTypeName(analysis.type);
        
        // 显示配置页面
        this.showPage('config');
    }
    
    showPage(pageName) {
        this.currentPage = pageName;
        
        // 隐藏所有页面和状态
        const pages = ['loadingState', 'errorState', 'workflowSelectionPage', 'parameterConfigPage', 'taskStatusPage'];
        pages.forEach(id => {
            const element = document.getElementById(id);
            if (element) element.style.display = 'none';
        });
        
        // 显示指定页面
        switch (pageName) {
            case 'selection':
                const selectionPage = document.getElementById('workflowSelectionPage');
                if (selectionPage) selectionPage.style.display = 'block';
                break;
            case 'config':
                const configPage = document.getElementById('parameterConfigPage');
                if (configPage) configPage.style.display = 'block';
                break;
            case 'status':
                const statusPage = document.getElementById('taskStatusPage');
                if (statusPage) statusPage.style.display = 'block';
                break;
        }
    }
    
    backToWorkflowSelection() {
        this.showPage('selection');
        this.selectedWorkflow = null;
    }
    
    showLoading() {
        const loadingState = document.getElementById('loadingState');
        const errorState = document.getElementById('errorState');
        const workflowSelectionPage = document.getElementById('workflowSelectionPage');
        
        if (loadingState) loadingState.style.display = 'block';
        if (errorState) errorState.style.display = 'none';
        if (workflowSelectionPage) workflowSelectionPage.style.display = 'none';
    }
    
    showError(message) {
        const errorMessageElement = document.getElementById('errorMessage');
        if (errorMessageElement) errorMessageElement.textContent = message || '发生未知错误';
        
        const loadingState = document.getElementById('loadingState');
        const errorState = document.getElementById('errorState');
        const workflowSelectionPage = document.getElementById('workflowSelectionPage');
        
        if (loadingState) loadingState.style.display = 'none';
        if (errorState) errorState.style.display = 'block';
        if (workflowSelectionPage) workflowSelectionPage.style.display = 'none';
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
    
    startTaskStatusRefresh() {
        if (this.imageListRefreshTimer) {
            clearInterval(this.imageListRefreshTimer);
        }
        this.imageListRefreshTimer = setInterval(() => this.updateTaskStatus(), 2000);
    }
    
    async updateTaskStatus() {
        if (!this.currentTask) return;
        
        try {
            const response = await fetch(`/api/status/${this.currentTask}`);
            if (!response.ok) throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            
            const data = await response.json();
            if (data.success) {
                const statusElement = document.getElementById('taskStatus');
                if (statusElement) {
                    statusElement.textContent = data.status;
                }
                
                if (data.status === 'completed') {
                    this.stopTaskStatusRefresh();
                    this.showPage('selection');
                    alert('生成完成！');
                } else if (data.status === 'failed') {
                    this.stopTaskStatusRefresh();
                    this.showError('生成失败');
                }
            }
        } catch (error) {
            console.error('更新任务状态失败:', error);
        }
    }
    
    stopTaskStatusRefresh() {
        if (this.imageListRefreshTimer) {
            clearInterval(this.imageListRefreshTimer);
            this.imageListRefreshTimer = null;
        }
    }
}

// 初始化应用
let app;
document.addEventListener('DOMContentLoaded', () => {
    console.log('DOM加载完成，开始初始化应用...');
    try {
        app = new ComfyWebApp();
        console.log('应用初始化成功');
    } catch (error) {
        console.error('应用初始化失败:', error);
    }
});





