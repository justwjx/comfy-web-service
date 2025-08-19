// 简化版ComfyWebApp测试
class ComfyWebApp {
    constructor() {
        this.workflows = [];
        this.selectedWorkflow = null;
        this.currentPage = 'selection';
        console.log('ComfyWebApp 初始化');
        this.init();
    }
    
    init() {
        console.log('开始初始化...');
        this.loadWorkflows();
    }
    
    async loadWorkflows() {
        console.log('开始加载工作流...');
        this.showLoading();
        
        try {
            console.log('调用API...');
            const response = await fetch('/api/workflows');
            console.log('API响应状态:', response.status);
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            const data = await response.json();
            console.log('API数据:', data);
            
            if (data.success) {
                this.workflows = data.workflows || [];
                console.log('工作流数量:', this.workflows.length);
                this.renderWorkflows();
                this.showPage('selection');
            } else {
                throw new Error(data.error || '加载失败');
            }
        } catch (error) {
            console.error('加载工作流失败:', error);
            this.showError(`加载失败: ${error.message}`);
        }
    }
    
    showLoading() {
        console.log('显示加载状态');
        const loadingState = document.getElementById('loadingState');
        const errorState = document.getElementById('errorState');
        const workflowSelectionPage = document.getElementById('workflowSelectionPage');
        
        if (loadingState) loadingState.style.display = 'block';
        if (errorState) errorState.style.display = 'none';
        if (workflowSelectionPage) workflowSelectionPage.style.display = 'none';
    }
    
    showError(message) {
        console.log('显示错误:', message);
        const errorMessageElement = document.getElementById('errorMessage');
        const loadingState = document.getElementById('loadingState');
        const errorState = document.getElementById('errorState');
        const workflowSelectionPage = document.getElementById('workflowSelectionPage');
        
        if (errorMessageElement) errorMessageElement.textContent = message || '发生未知错误';
        if (loadingState) loadingState.style.display = 'none';
        if (errorState) errorState.style.display = 'block';
        if (workflowSelectionPage) workflowSelectionPage.style.display = 'none';
    }
    
    renderWorkflows() {
        console.log('渲染工作流列表');
        const container = document.getElementById('workflowCards');
        if (!container) {
            console.error('找不到workflowCards容器');
            return;
        }
        
        if (this.workflows.length === 0) {
            container.innerHTML = '<div class="empty-state">没有找到工作流</div>';
            return;
        }
        
        const html = this.workflows.map(workflow => `
            <div class="workflow-card">
                <h3>${workflow.name || '未命名'}</h3>
                <p>${workflow.description || '暂无描述'}</p>
            </div>
        `).join('');
        
        container.innerHTML = html;
    }
    
    showPage(pageName) {
        console.log('显示页面:', pageName);
        this.currentPage = pageName;
        
        const loadingState = document.getElementById('loadingState');
        const errorState = document.getElementById('errorState');
        const workflowSelectionPage = document.getElementById('workflowSelectionPage');
        
        if (loadingState) loadingState.style.display = 'none';
        if (errorState) errorState.style.display = 'none';
        if (workflowSelectionPage) workflowSelectionPage.style.display = 'none';
        
        switch (pageName) {
            case 'selection':
                if (workflowSelectionPage) workflowSelectionPage.style.display = 'block';
                break;
        }
    }
}

// 初始化应用
let app;
document.addEventListener('DOMContentLoaded', () => {
    console.log('DOM加载完成，初始化应用...');
    try {
        app = new ComfyWebApp();
    } catch (error) {
        console.error('应用初始化失败:', error);
    }
});

