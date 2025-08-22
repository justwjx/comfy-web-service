// ComfyUI工作流管理器 - 优化版本

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
        // 防御性处理：PromptTemplates 可能未定义，避免初始化期报错导致页面卡死
        try {
            if (typeof PromptTemplates === 'function') {
                this.promptTemplates = new PromptTemplates();
            } else {
                this.promptTemplates = null;
            }
        } catch (_) {
            this.promptTemplates = null;
        }
        this.lastPresetLabel = '';
        this.shortcutContext = {};
        this._pendingPositivePrompt = null;
        this.init();
    }

    // 安全插入 LoRA 触发词到快捷区（兼容模块或直接写 DOM）
    safeInsertLoraShortcuts(words, loraName) {
        try {
            if (this.prependLoraPromptShortcuts && typeof this.prependLoraPromptShortcuts === 'function') {
                this.prependLoraPromptShortcuts(words, loraName);
                return;
            }
        } catch (_) {}
        try {
            if (this.promptSystem && typeof this.promptSystem.prependLoraPromptShortcuts === 'function') {
                this.promptSystem.prependLoraPromptShortcuts(words, loraName);
                return;
            }
        } catch (_) {}
        try {
            const container = document.getElementById('promptShortcuts');
            if (!container || !Array.isArray(words) || words.length === 0) return;
            const old = container.querySelector('.lora-shortcuts-block');
            if (old) old.remove();
            const block = document.createElement('div');
            block.className = 'shortcut-subgroup lora-shortcuts-block';
            const title = document.createElement('h5');
            title.className = 'shortcut-subheader';
            title.textContent = `LoRA 触发词（${loraName}）`;
            block.appendChild(title);
            const btns = document.createElement('div');
            btns.className = 'shortcut-buttons';
            words.forEach(w => {
                const btn = document.createElement('button');
                btn.type = 'button';
                btn.className = 'shortcut-btn';
                btn.textContent = w;
                btn.addEventListener('click', () => {
                    const el = document.getElementById('positivePrompt');
                    const overwrite = document.getElementById('promptOverwriteSwitch')?.checked;
                    if (!el) return;
                    const trimmed = (el.value || '').trim();
                    if (overwrite || !trimmed) { el.value = w; }
                    else { el.value = el.value + (trimmed.endsWith(',') ? ' ' : ', ') + w; }
                    el.dispatchEvent(new Event('input', { bubbles: true }));
                    el.dispatchEvent(new Event('change', { bubbles: true }));
                });
                btns.appendChild(btn);
            });
            block.appendChild(btns);
            container.prepend(block);
        } catch (_) {}
    }
    // 友好显示：节点中文名
    getFriendlyNodeName(type, fallbackTitle) {
        const map = {
            'ImagePadForOutpaint': '外补画板',
            'ImageAndMaskResizeNode': '图像与掩码缩放',
            'ControlNetApplyAdvanced': 'ControlNet 应用器',
            'ControlNetLoader': 'ControlNet 模型加载器',
            'CLIPTextEncode': '提示词编码器',
            'LoadImage': '加载图像',
            'LoadImageOutput': '加载图像（外部）',
            'MarkdownNote': '说明',
            'InpaintModelConditioning': '修复条件（噪声遮罩）',
            'SaveImage': '保存图片',
            'RandomNoise': '随机噪声',
            'BasicScheduler': '调度器',
            'BasicGuider': '采样引导器',
            'ModelSamplingFlux': 'Flux 采样模型',
            'VAEDecode': 'VAE 解码',
            'EmptySD3LatentImage': '空 Latent（SD3）',
            'PrimitiveNode': '常量/尺寸',
            'KSamplerSelect': '采样器选择',
            'KSampler': 'KSampler'
        };
        return map[type] || fallbackTitle || type || '节点';
    }

    // 友好显示：参数中文名与提示
    getParamMeta(nodeType, rawName, defaultValue, widgetIndex) {
        const name = String(rawName || '').toLowerCase();
        const meta = { label: rawName || '参数', hint: '' };
        const H = (text) => { meta.hint = text; return meta; };
        const L = (label, hint) => { meta.label = label; meta.hint = hint || ''; return meta; };

        // 外部画板
        if (nodeType.includes('ImagePadForOutpaint')) {
            // 优先按索引名对齐原生：左、上、右、下、羽化
            if (typeof widgetIndex === 'number') {
                const byIndex = {
                    0: ['左 (px)', '在左侧扩展的像素数量'],
                    1: ['上 (px)', '在上方扩展的像素数量'],
                    2: ['右 (px)', '在右侧扩展的像素数量'],
                    3: ['下 (px)', '在下方扩展的像素数量'],
                    4: ['羽化 (px)', '边缘过渡羽化半径，数值越大越柔和']
                };
                if (byIndex[widgetIndex]) {
                    const [lbl, hint] = byIndex[widgetIndex];
                    return L(lbl, hint);
                }
            }
            if (name.includes('pad_left')) return L('左 (px)', '在左侧扩展的像素数量');
            if (name.includes('pad_right')) return L('右 (px)', '在右侧扩展的像素数量');
            if (name.includes('pad_top') || name.includes('pad_up')) return L('上 (px)', '在上方扩展的像素数量');
            if (name.includes('pad_bottom') || name.includes('pad_down')) return L('下 (px)', '在下方扩展的像素数量');
            if (name.includes('feather')) return L('羽化 (px)', '边缘过渡羽化半径，数值越大越柔和');
        }

        // 图像与掩码缩放
        if (nodeType.includes('ImageAndMaskResizeNode')) {
            // 优先按 widgets 索引硬映射，避免把 inputs 名称（image/mask）错当成参数名
            if (typeof widgetIndex === 'number') {
                const byIndex = {
                    0: ['图像宽度 (px)', '用于生成/处理的目标宽度'],
                    1: ['图像高度 (px)', '用于生成/处理的目标高度'],
                    2: ['缩放算法', '选择插值方式，影响缩放质量与速度'],
                    3: ['裁剪', 'center 保持中心；disabled 不裁剪'],
                    4: ['掩码羽化半径 (px)', '增大以减轻硬边']
                };
                if (byIndex[widgetIndex]) {
                    const [lbl, hint] = byIndex[widgetIndex];
                    return L(lbl, hint);
                }
            }
            // 名称兜底（兼容未来节点命名变动）
            if (name.includes('resize_method')) return L('缩放算法', '选择插值方式，影响缩放质量与速度');
            if (name === 'crop') return L('裁剪', 'center 保持中心；disabled 不裁剪');
            if (name.includes('mask_blur_radius')) return L('掩码羽化半径 (px)', '增大以减轻硬边');
        }

        // ControlNet 应用器
        if (nodeType.includes('ControlNetApplyAdvanced')) {
            if (name.includes('strength')) return L('强度', '控制影响程度，0-1');
            if (name.includes('start_percent')) return L('起始百分比', '从采样进程的何处开始生效，0-1');
            if (name.includes('end_percent')) return L('结束百分比', '在哪个阶段结束生效，0-1');
        }

        // Inpaint 条件
        if (nodeType.includes('InpaintModelConditioning')) {
            // 该节点通常只有一个 widgets：index 0
            if (typeof widgetIndex === 'number' && widgetIndex === 0) return L('噪声遮罩', '启用后仅在遮罩区域填充噪声进行修复');
            if (name.includes('noise_mask')) return L('噪声遮罩', '启用后仅在遮罩区域填充噪声进行修复');
        }

        // SaveImage
        if (nodeType.includes('SaveImage')) {
            if (name.includes('filename_prefix') || name === 'p0' || widgetIndex === 0) {
                return L('文件名前缀', '生成图片保存到 /outputs/ 下的文件名前缀；用于区分任务与避免覆盖');
            }
        }

        // RandomNoise
        if (nodeType.includes('RandomNoise')) {
            if (name.includes('noise_seed') || name === 'p0') return L('噪声种子', '固定以复现实验；为空或随机模式表示每次随机');
            if (name.includes('randomize') || name === 'p1') return L('种子模式', 'randomize/固定');
        }

        // BasicScheduler
        if (nodeType.includes('BasicScheduler')) {
            if (name === 'scheduler' || name === 'p0') return L('调度器', '影响噪声分布与收敛特性');
            if (name === 'steps' || name === 'p1') return L('步数', '越高细节越多但更慢');
            if (name === 'denoise' || name === 'p2') return L('去噪强度', '0-1；越小越保留初始条件');
        }

        // ModelSamplingFlux
        if (nodeType.includes('ModelSamplingFlux')) {
            if (name.includes('max_shift')) return L('最大偏移', 'Flux 采样参数');
            if (name.includes('base_shift')) return L('基础偏移', 'Flux 采样参数');
            if (name === 'width') return L('宽度 (px)', '用于 Flux 采样模型的宽度');
            if (name === 'height') return L('高度 (px)', '用于 Flux 采样模型的高度');
        }

        // 常见通用名
        if (name === 'width') return L('宽度 (px)', '输出或中间特征图的宽度');
        if (name === 'height') return L('高度 (px)', '输出或中间特征图的高度');
        if (name === 'strength') return L('强度', '控制影响程度，0-1');
        if (name === 'guidance') return L('Flux Guidance', 'Flux 流派的提示词贴合程度');

        // 兜底：p0/p1 → 参数#
        if (/^p\d+$/.test(name)) {
            return L(`参数 ${name.slice(1)}`, '来自工作流的自定义参数');
        }
        return meta;
    }
    
    init() {
        console.log('开始初始化...');
        try {
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
        const from = urlParams.get('from');
        const positive = urlParams.get('positive');
        const negative = urlParams.get('negative');

        // 从提示词管理器回填正负面提示词
        if (from === 'prompt-manager' && (positive || negative)) {
            // 延迟到参数界面渲染后再注入，避免元素未就绪
            const posText = positive;
            const negText = negative;
            let attempts = 0;
            const tryApply = () => {
                const positiveEl = document.getElementById('positivePrompt');
                const negativeEl = document.getElementById('negativePrompt');
                if (!positiveEl) { if (attempts++ < 25) { setTimeout(tryApply, 200); } return; }
                try {
                    const overwrite = document.getElementById('promptOverwriteSwitch')?.checked;
                    // 记录回填前的值以支持撤销
                    const prevPositive = (positiveEl.value || '');
                    const prevNegative = (negativeEl ? (negativeEl.value || '') : '');
                    if (posText) {
                        const trimmed = (positiveEl.value || '').trim();
                        if (overwrite || !trimmed) {
                            positiveEl.value = posText;
                        } else {
                            const needsComma = trimmed.length > 0 && !trimmed.endsWith(',');
                            positiveEl.value = positiveEl.value + (needsComma ? ', ' : ' ') + posText;
                        }
                        positiveEl.dispatchEvent(new Event('input', { bubbles: true }));
                        positiveEl.dispatchEvent(new Event('change', { bubbles: true }));
                        // 高亮并聚焦
                        positiveEl.focus();
                        const oldOutline = positiveEl.style.outline;
                        positiveEl.style.outline = '2px solid var(--primary-color)';
                        setTimeout(() => { positiveEl.style.outline = oldOutline || ''; }, 1200);
                    }
                    if (negText && negativeEl) {
                        const ntrim = (negativeEl.value || '').trim();
                        if (overwrite || !ntrim) {
                            negativeEl.value = negText;
                        } else {
                            const needsCommaN = ntrim.length > 0 && !ntrim.endsWith(',');
                            negativeEl.value = negativeEl.value + (needsCommaN ? ', ' : ' ') + negText;
                        }
                        negativeEl.dispatchEvent(new Event('input', { bubbles: true }));
                        negativeEl.dispatchEvent(new Event('change', { bubbles: true }));
                    }
                    // 显示“来自提示词库”的提示条，支持撤销回填
                    try {
                        const parent = document.getElementById('parameterConfigPage');
                        if (parent && !document.getElementById('promptInjectionBanner')) {
                            const banner = document.createElement('div');
                            banner.id = 'promptInjectionBanner';
                            banner.style.cssText = 'margin:10px 0; padding:10px 12px; border:1px solid var(--border-color); background: var(--bg-secondary); border-radius:8px; display:flex; align-items:center; justify-content:space-between; gap:8px;';
                            banner.innerHTML = '<span>已从提示词库回填。</span>' +
                                '<div style="display:flex; gap:8px;">' +
                                '<button id="undoPromptInjectionBtn" class="btn btn-sm btn-secondary">撤销回填</button>' +
                                '<button id="dismissPromptInjectionBtn" class="btn btn-sm">关闭</button>' +
                                '</div>';
                            const container = parent.querySelector('.config-container');
                            parent.insertBefore(banner, container || parent.firstChild);
                            const undoBtn = document.getElementById('undoPromptInjectionBtn');
                            const dismissBtn = document.getElementById('dismissPromptInjectionBtn');
                            if (undoBtn) {
                                undoBtn.addEventListener('click', () => {
                                    try {
                                        if (positiveEl) {
                                            positiveEl.value = prevPositive;
                                            positiveEl.dispatchEvent(new Event('input', { bubbles: true }));
                                            positiveEl.dispatchEvent(new Event('change', { bubbles: true }));
                                        }
                                        if (negativeEl) {
                                            negativeEl.value = prevNegative;
                                            negativeEl.dispatchEvent(new Event('input', { bubbles: true }));
                                            negativeEl.dispatchEvent(new Event('change', { bubbles: true }));
                                        }
                                    } catch (_) {}
                                    try { banner.remove(); } catch (_) {}
                                });
                            }
                            if (dismissBtn) {
                                dismissBtn.addEventListener('click', () => { try { banner.remove(); } catch (_) {} });
                            }
                        }
                    } catch (_) {}
                    // 一次性应用后清理URL中的触发参数，避免刷新重复注入
                    try {
                        if (window.history && typeof window.history.replaceState === 'function') {
                            const url = new URL(window.location.href);
                            url.searchParams.delete('from');
                            url.searchParams.delete('positive');
                            url.searchParams.delete('negative');
                            const newSearch = url.searchParams.toString();
                            const newUrl = url.pathname + (newSearch ? ('?' + newSearch) : '') + (url.hash || '');
                            window.history.replaceState(null, '', newUrl);
                        }
                    } catch (_) {}
                } catch (_) {}
            };
            setTimeout(tryApply, 600);
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
        // 先用快速猜测，随后用精准分析结果覆盖
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
        // 异步获取精准类型
        this.getAccurateWorkflowType(workflow.filename).then(type => {
            const t = this.getWorkflowTypeName(type);
            const introTypeEl = document.getElementById('introType');
            if (introTypeEl) introTypeEl.textContent = t;
        }).catch(() => {});
    }

    async getAccurateWorkflowType(filename) {
        try {
            if (this.workflowTypeCache[filename]) {
                return this.workflowTypeCache[filename];
            }
            const resp = await fetch(`/api/analyze-workflow/${encodeURIComponent(filename)}`);
            const data = await resp.json();
            if (data.success && data.analysis && data.analysis.type) {
                this.workflowTypeCache[filename] = data.analysis.type;
                return data.analysis.type;
            }
        } catch (e) {
            // 忽略错误，回退到快速猜测
        }
        return this.getWorkflowType(filename);
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
        // Kontext 系列归类为图像修改/图生图
        if (filenameLower.includes('kontext')) return 'image-to-image';
        if (filenameLower.includes('schnell')) return 'text-to-image';
        if (filenameLower.includes('redux')) return 'image-to-image';
        if (filenameLower.includes('fill') || filenameLower.includes('removal')) return 'inpaint';
        if (filenameLower.includes('controlnet')) return 'controlnet';
        if (filenameLower.includes('upscaler')) return 'upscaler';
        return 'text-to-image';
    }
    
    startWorkflow() {
        // 若未记录，尝试从下拉菜单读取
        if (!this.selectedWorkflow) {
            const sel = document.getElementById('workflowSelect');
            const val = sel && sel.value;
            if (val) {
                this.quickSelectWorkflow(val);
            }
        }
        if (!this.selectedWorkflow) return;
        // 进入配置页前，将工作流写入URL并持久化最近工作流
        try {
            if (window.history && typeof window.history.replaceState === 'function') {
                const url = new URL(window.location.href);
                url.searchParams.set('workflow', this.selectedWorkflow.filename);
                const newSearch = url.searchParams.toString();
                const newUrl = url.pathname + (newSearch ? ('?' + newSearch) : '') + (url.hash || '');
                window.history.replaceState(null, '', newUrl);
            }
        } catch (_) {}
        try { localStorage.setItem('cw_last_workflow', this.selectedWorkflow.filename); } catch (_) {}
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
        
        // 先检查ComfyUI连接状态
        try {
            const statusResponse = await fetch('/api/comfyui/status');
            const statusData = await statusResponse.json();
            
            if (!statusData.success || !statusData.connected) {
                const errorMsg = statusData.error || 'ComfyUI后端未连接';
                alert(`无法连接到ComfyUI后端：${errorMsg}\n\n请确保：\n1. ComfyUI服务已启动\n2. 服务地址配置正确\n3. 网络连接正常`);
                return;
            }
        } catch (error) {
            console.error('检查ComfyUI状态失败:', error);
            alert('无法检查ComfyUI连接状态，请确保后端服务正常运行');
            return;
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
        // 获取 seed 输入框的值
        let seedInput = document.getElementById('seed');
        let seedValue = seedInput ? seedInput.value : '';
        // 如果 seed 为空或为-1，则自动生成随机 seed
        let seed;
        if (seedValue === '' || seedValue === '-1') {
            seed = Math.floor(Math.random() * 1e16); // 生成一个大随机数
            if (seedInput) seedInput.value = seed; // 同步到输入框，便于用户复用
        } else {
            seed = parseInt(seedValue);
        }
        const baseParams = {
            steps: parseInt(document.getElementById('steps')?.value || (this.currentAnalysis?.default_values?.steps || this.getDefaultValue('steps'))),
            cfg: parseFloat(document.getElementById('cfg')?.value || (this.currentAnalysis?.default_values?.cfg || this.getDefaultValue('cfg'))),
            seed: seed,
            sampler: document.getElementById('sampler')?.value || (this.currentAnalysis?.default_values?.sampler || this.getDefaultValue('sampler')),
            scheduler: document.getElementById('scheduler')?.value || (this.currentAnalysis?.default_values?.scheduler || this.getDefaultValue('scheduler')),
            denoise: parseFloat(document.getElementById('denoise')?.value || (this.currentAnalysis?.default_values?.denoise || this.getDefaultValue('denoise'))),
            // guidance 仅当 workflow 中存在 FluxGuidance 节点时才读取
            guidance: (()=>{
                const el = document.getElementById('guidance');
                if (!el) return undefined;
                const v = el.value;
                return v === '' ? undefined : parseFloat(v);
            })(),
            positive_prompt: document.getElementById('positivePrompt')?.value || '',
            negative_prompt: document.getElementById('negativePrompt')?.value || '',
            auto_outpaint_mask: document.getElementById('autoOutpaintMask')?.checked ?? true,
            resize_method: document.getElementById('resize_method')?.value,
            crop: document.getElementById('crop')?.value,
            mask_blur_radius: (()=>{ const v = document.getElementById('mask_blur_radius')?.value; return v!==undefined && v!==null && v!=='' ? parseInt(v) : undefined; })()
        };

        // 收集输出设置参数
        const outputSettings = {};
        const outputElements = document.querySelectorAll('#output_width, #output_height, #size_control_mode, #batch_size');
        outputElements.forEach(el => {
            if (el) {
                let value = el.value;
                if (el.type === 'number') {
                    value = value === '' ? undefined : parseFloat(value);
                }
                if (value !== undefined && value !== '') {
                    outputSettings[el.name] = value;
                }
            }
        });

        // 收集模型加载器参数
        const modelLoaderParams = {};
        const modelLoaderElements = document.querySelectorAll('[id^="model_type_"], [id^="text_encoder1_"], [id^="text_encoder2_"], [id^="t5_min_length_"], [id^="use_4bit_t5_"], [id^="int4_model_"], [id^="model_path_"], [id^="cache_threshold_"], [id^="attention_"], [id^="cpu_offload_"], [id^="device_id_"], [id^="data_type_"], [id^="i_2_f_mode_"], [id^="lora_name_"], [id^="lora_strength_"], [id^="vae_name_"], [id^="clip_name1_"], [id^="clip_name2_"], [id^="clip_type_"], [id^="clip_name_"], [id^="style_model_name_"], [data-ml-param="true"]');
        
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
            output_settings: outputSettings,
            model_loaders: modelLoaderParams,
            controlnet_configs: controlnetParams
        };

        // 收集通用节点参数（兜底）：data-node-param="nodeId:widgetIndex"
        try {
            const genericParams = {};
            const genericInputs = document.querySelectorAll('[data-node-param]');
            genericInputs.forEach(el => {
                const key = el.getAttribute('data-node-param');
                if (!key) return;
                let value;
                if (el.type === 'checkbox') value = !!el.checked;
                else if (el.type === 'number') value = el.value === '' ? undefined : Number(el.value);
                else value = el.value;
                if (typeof value !== 'undefined') genericParams[key] = value;
            });
            if (Object.keys(genericParams).length > 0) {
                parameters.node_generic_params = genericParams;
            }
        } catch (_) {}

        // 添加选择的图像
        if (this.selectedImages && Object.keys(this.selectedImages).length > 0) {
            parameters.selected_images = this.selectedImages;
        }
        // 若用户在遮罩编辑器保存了 mask，附加到参数，后端自动接入
        if (this.selectedMaskPath) {
            parameters.mask_image = this.selectedMaskPath;
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
                    const message = task.message || '';
                    
                    // 更新进度显示
                    const progressBar = document.getElementById('progressBar');
                    const progressText = document.getElementById('progressText');
                    const taskStatus = document.getElementById('taskStatusHeader');
                    const taskNodeNow = document.getElementById('taskNodeNow');
                    const taskNodeNext = document.getElementById('taskNodeNext');
                    const taskWorkflowName = document.getElementById('taskWorkflowName');
                    const taskStartTime = document.getElementById('taskStartTime');
                    const taskRemaining = document.getElementById('taskRemaining');
                    const taskWorkflowNameValue = document.querySelector('#taskWorkflowName + .value, #taskWorkflowName');
                    const taskStartTimeValue = document.querySelector('#taskStartTime + .value, #taskStartTime');
                    const taskRemainingValue = document.querySelector('#taskRemaining + .value, #taskRemaining');
                    
                    if (progressBar) progressBar.style.width = `${progress}%`;
                    if (progressText) progressText.textContent = `${Math.round(progress)}%`;
                    
                    // 更新状态信息，包含详细消息
                    if (taskStatus) {
                        let statusText = status;
                        if (message) statusText += ` - ${message}`;
                        taskStatus.textContent = statusText;
                    }
                    if (taskNodeNow) taskNodeNow.textContent = task.current_node_label || '-';
                    if (taskNodeNext) taskNodeNext.textContent = task.next_node_label || '-';
                    
                    const wfText = task.filename || '-';
                    const stText = task.start_time ? new Date(task.start_time).toLocaleString() : '-';
                    if (taskWorkflowName) taskWorkflowName.textContent = wfText;
                    if (taskStartTime) taskStartTime.textContent = stText;
                    if (taskWorkflowNameValue) taskWorkflowNameValue.textContent = wfText;
                    if (taskStartTimeValue) taskStartTimeValue.textContent = stText;
                    
                    // 更新预计剩余时间
                    if (taskRemaining) {
                        if (status === 'pending') {
                            (taskRemainingValue || taskRemaining).textContent = '等待中...';
                        } else if (status === 'running') {
                            if (progress < 30) {
                                (taskRemainingValue || taskRemaining).textContent = '预计 2-3 分钟';
                            } else if (progress < 70) {
                                (taskRemainingValue || taskRemaining).textContent = '预计 1-2 分钟';
                            } else {
                                (taskRemainingValue || taskRemaining).textContent = '即将完成';
                            }
                        } else {
                            (taskRemainingValue || taskRemaining).textContent = '-';
                        }
                    }
                    
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
                    setTimeout(updateProgress, 1000); // 每秒更新一次
                } else {
                    this.showTaskError('任务超时，请检查ComfyUI后端状态');
                }
            } catch (error) {
                console.error('监控任务失败:', error);
                this.showTaskError('监控任务失败，请刷新页面重试');
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
            const wmLabel = (this.lastPresetLabel && typeof this.lastPresetLabel === 'string') ? this.lastPresetLabel : '';
            const fullPrompt = document.getElementById('positivePrompt')?.value || '';
            outputImages.innerHTML = `
                <div class="output-image with-watermark">
                    <img src="${task.image_url}" alt="生成结果" onclick="window.open('${task.image_url}', '_blank')">
                    <div class="image-actions">
                        <button class="btn btn-sm btn-primary" onclick="window.open('${task.image_url}', '_blank')">
                            <i class="fas fa-external-link-alt"></i> 查看大图
                        </button>
                        <button class="btn btn-sm btn-secondary" onclick="app.downloadImage('${task.image_url}')">
                            <i class="fas fa-download"></i> 下载
                        </button>
                    </div>
                    <div class="soft-watermark soft-watermark-top">
                        ${wmLabel ? `<div class="wm-preset" title="预设">${wmLabel}</div>` : ''}
                        ${fullPrompt ? `<div class="wm-prompt" title="完整提示词">${fullPrompt.replace(/</g,'&lt;').replace(/>/g,'&gt;')}</div>` : ''}
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
        
        // 任务完成后，如果图片选择模态框是打开的，自动刷新图片列表
        this.refreshImageListIfModalOpen();
    }

    // 如果图片选择模态框是打开的，刷新图片列表
    refreshImageListIfModalOpen() {
        const modal = document.getElementById('imageSelectModal');
        if (modal && modal.style.display === 'flex') {
            console.log('任务完成，自动刷新图片列表');
            this.loadImages(true);
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

    async deleteImage(imageName, source) {
        if (!confirm(`确定要删除图片 "${imageName}" 吗？此操作不可撤销。`)) {
            return;
        }

        try {
            const response = await fetch('/api/delete-image', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    filename: imageName
                })
            });

            const data = await response.json();

            if (data.success) {
                this.showUploadMessage('success', '图片删除成功！');
                // 重新加载图片列表
                await this.loadImages(true);
            } else {
                this.showUploadMessage('error', '删除失败: ' + (data.error || '未知错误'));
            }
        } catch (error) {
            console.error('删除图片失败:', error);
            this.showUploadMessage('error', '删除失败: ' + error.message);
        }
    }
    
    showTaskError(error) {
        const taskOutput = document.getElementById('taskOutput');
        const taskError = document.getElementById('taskError');
        
        if (taskOutput) taskOutput.style.display = 'none';
        if (taskError) {
            taskError.style.display = 'block';
            const errorTitle = taskError.querySelector('h3');
            const errorContent = taskError.querySelector('.error-content');
            
            if (errorTitle) errorTitle.textContent = '任务执行失败';
            if (errorContent) {
                // 格式化错误信息
                let errorText = error;
                if (typeof error === 'object' && error.message) {
                    errorText = error.message;
                }
                
                // 添加常见错误的解决建议
                let suggestions = '';
                if (errorText.includes('ComfyUI') || errorText.includes('连接') || errorText.includes('无法连接')) {
                    suggestions = '\n\n解决建议：\n1. 确保ComfyUI服务已启动\n2. 检查ComfyUI服务地址和端口配置\n3. 确认网络连接正常\n4. 查看ComfyUI服务日志';
                } else if (errorText.includes('超时')) {
                    suggestions = '\n\n解决建议：\n1. 检查ComfyUI服务是否正常运行\n2. 尝试重新启动ComfyUI服务\n3. 检查系统资源使用情况';
                } else if (errorText.includes('参数') || errorText.includes('配置')) {
                    suggestions = '\n\n解决建议：\n1. 检查工作流参数配置\n2. 确保所有必需参数都已填写\n3. 验证参数值是否在有效范围内';
                }
                
                errorContent.textContent = errorText + suggestions;
            }
        }
    }
    
    backToParameterConfig() {
        this.showPage('config');
        this.showResourceMonitor();
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
    
    // 已移除基础参数快捷模式
    
    toggleSection(sectionName) {
        const section = document.getElementById(`${sectionName}Section`);
        const content = document.getElementById(`${sectionName}Content`);
        const toggle = document.getElementById(`${sectionName}Toggle`);
        
        if (!section || !content || !toggle) return;
        
        section.classList.toggle('expanded');
        
        if (section.classList.contains('expanded')) {
            content.style.maxHeight = content.scrollHeight + 'px';
        } else {
            content.style.maxHeight = '0';
        }
    }
    
    // 初始化时展开基础参数（在页面显示后再测量高度，避免为0）
    initializeCollapsibleSections() {
        const section = document.getElementById('basicParametersSection');
            const content = document.getElementById('basicParametersContent');
        if (!section || !content) return;

        // 展开样式
        section.classList.add('expanded');

        const ensureVisibleAndMeasure = () => {
            const page = document.getElementById('parameterConfigPage');
            const isVisible = page && page.style.display === 'block';
            if (!isVisible) {
                requestAnimationFrame(ensureVisibleAndMeasure);
                return;
            }
            // 下一帧再测量，确保布局稳定
            requestAnimationFrame(() => {
                content.style.maxHeight = content.scrollHeight + 'px';
            });
        };
        requestAnimationFrame(ensureVisibleAndMeasure);
    }

    // 资源监控相关函数
    showResourceMonitor() {
        const rm = document.getElementById('resourceMonitor');
        if (rm) rm.style.display = 'block';
        // 初始化布局切换与首次渲染
        this.updateResourceMonitorLayout();
        if (!this._rmResizeBound) {
            window.addEventListener('resize', () => {
                this.updateResourceMonitorLayout();
                // 重新拉取一次，确保视图与数据同步
                this.fetchSystemResources();
            });
            this._rmResizeBound = true;
        }

        // 根据当前header高度，设置CSS变量，避免遮挡
        const header = document.querySelector('.header');
        if (header) {
            const headerHeight = Math.ceil(header.getBoundingClientRect().height);
            document.documentElement.style.setProperty('--header-height', `${headerHeight}px`);
            // 预留2px视觉间距，防止接缝抖动
            document.documentElement.style.setProperty('--header-offset', `${Math.max(headerHeight - 2, 0)}px`);
        }
    }

    hideResourceMonitor() {
        const rm = document.getElementById('resourceMonitor');
        if (rm) rm.style.display = 'none';
    }

    async fetchSystemResources() {
        try {
            const resp = await fetch('/api/system-resources');
            const data = await resp.json();
            if (!data.success) return;
            const isMobile = this.isMobileLayout();
            if (!Array.isArray(data.gpus)) data.gpus = [];
            if (data.gpus.length === 0 && this._lastGpus && this._lastGpus.length > 0) {
                data.gpus = this._lastGpus;
            } else if (data.gpus.length > 0) {
                this._lastGpus = data.gpus;
            }
            // CPU/内存
            const cpu = Math.round(data.cpu_percent || 0);
            const mem = Math.round(data.memory_percent || 0);
            const cpuBar = document.getElementById('cpuBar');
            const memBar = document.getElementById('memBar');
            const cpuText = document.getElementById('cpuText');
            const memText = document.getElementById('memText');
            if (cpuBar) cpuBar.style.width = `${cpu}%`;
            if (memBar) memBar.style.width = `${mem}%`;
            if (cpuText) cpuText.textContent = `${cpu}%`;
            if (memText) {
                const used = data.memory_used_mb ? `${data.memory_used_mb}M` : `${mem}%`;
                const total = data.memory_total_mb ? `${data.memory_total_mb}M` : '';
                memText.textContent = total ? `${used} / ${total}` : `${mem}%`;
            }
            // 桌面端：行内GPU（显示核心利用率 + 显存）
            const inlineGpus = document.getElementById('rmInlineGpus');
            if (!isMobile && inlineGpus) {
                const gpus = Array.isArray(data.gpus) ? data.gpus : [];
                inlineGpus.innerHTML = gpus.map(g => {
                    const vram = Math.round(g.vram_percent || 0);
                    const util = Math.round((g.util_percent ?? g.util) || 0);
                    const used = g.vram_used_mb ? `${Math.round(g.vram_used_mb)}M` : `${vram}%`;
                    const total = g.vram_total_mb ? `${Math.round(g.vram_total_mb)}M` : '';
                    return `
                        <span class="rm-inline-item">GPU${g.index} ${util || util === 0 ? `${util}% · ` : ''}${total ? `${used}/${total}` : `${vram}%`}
                          <span class="rm-inline-bar"><span class="rm-inline-fill" style="width:${vram}%"></span></span>
                        </span>
                    `;
                }).join('');
            }
            // 移动端：芯片视图
            const chips = document.getElementById('rmChips');
            if (chips) {
                if (isMobile) {
                    const memLabel = data.memory_total_mb ? `${data.memory_used_mb}M/${data.memory_total_mb}M` : `${mem}%`;
                    const gpus = Array.isArray(data.gpus) ? data.gpus : [];
                    const gpuChipHtml = gpus.map(g => {
                        const vram = Math.round(g.vram_percent || 0);
                        const util = Math.round((g.util_percent ?? g.util) || 0);
                        const used = g.vram_used_mb ? `${Math.round(g.vram_used_mb)}M` : `${vram}%`;
                        const total = g.vram_total_mb ? `${Math.round(g.vram_total_mb)}M` : '';
                        return `
                        <div class="rm-chip">
                            <span class="chip-label">GPU${g.index}</span>
                            <div class="chip-bar"><div class="chip-fill" style="width:${vram}%"></div></div>
                            <span class="chip-text">${(util || util === 0) ? `${util}% · ` : ''}${total ? `${used}/${total}` : `${vram}%`}</span>
                        </div>`;
                    }).join('');
                    chips.style.display = 'flex';
                    chips.innerHTML = `
                      <div class="rm-chip">
                        <span class="chip-label">CPU</span>
                        <div class="chip-bar"><div class="chip-fill" style="width:${cpu}%"></div></div>
                        <span class="chip-text">${cpu}%</span>
                      </div>
                      <div class="rm-chip">
                        <span class="chip-label">内存</span>
                        <div class="chip-bar"><div class="chip-fill" style="width:${mem}%"></div></div>
                        <span class="chip-text">${memLabel}</span>
                      </div>
                      ${gpuChipHtml}
                    `;
                } else {
                    chips.style.display = 'none';
                    chips.innerHTML = '';
                }
            }
        } catch (e) {
            // 静默失败，避免干扰
        }
    }

    isMobileLayout() {
        return window.matchMedia('(max-width: 768px)').matches;
    }

    updateResourceMonitorLayout() {
        const isMobile = this.isMobileLayout();
        const chips = document.getElementById('rmChips');
        const inline = document.getElementById('rmInline');
        if (chips) chips.style.display = isMobile ? 'flex' : 'none';
        if (inline) inline.style.display = isMobile ? 'none' : 'flex';
    }

    startResourceAutoRefresh() {
        this.stopResourceAutoRefresh();
        this.fetchSystemResources();
        this.resourceRefreshTimer = setInterval(() => this.fetchSystemResources(), 3000);
        const btn = document.getElementById('rmRefreshBtn');
        if (btn) btn.textContent = '停止';
    }

    stopResourceAutoRefresh() {
        if (this.resourceRefreshTimer) {
            clearInterval(this.resourceRefreshTimer);
            this.resourceRefreshTimer = null;
        }
        const btn = document.getElementById('rmRefreshBtn');
        if (btn) btn.textContent = '刷新';
    }

    async cleanVRAM() {
        try {
            const resp = await fetch('/api/clean-vram', { method: 'POST' });
            const data = await resp.json();
            alert(data.message || (data.success ? '已触发清理VRAM' : '清理VRAM失败'));
            // 清理后主动刷新一次资源
            this.fetchSystemResources();
        } catch (e) {
            alert('清理VRAM请求失败');
        }
    }

    toggleResourceAutoRefresh() {
        if (this.resourceRefreshTimer) {
            this.stopResourceAutoRefresh();
        } else {
            this.startResourceAutoRefresh();
        }
    }
    
    async checkServerStatus() {
        // 服务器状态检查现在在loadWorkflows中并行进行
        // 这里只设置初始状态
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
                
                // URL/本地参数驱动：自动进入配置页
                try {
                    const params = new URLSearchParams(window.location.search);
                    const wf = params.get('workflow');
                    const from = params.get('from');
                    let target = wf;
                    if (!target && from === 'prompt-manager') {
                        try { target = localStorage.getItem('cw_last_workflow') || ''; } catch (_) {}
                    }
                    if (target) {
                        // 异步进入配置页
                        setTimeout(() => this.selectWorkflow(target), 0);
                    }
                } catch (_) {}
                
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
        
        // 生成快速链接（异步执行，不阻塞页面显示）
        this.generateQuickLinks().catch(error => {
            console.error('生成快速链接失败:', error);
        });
    }
    
    async generateQuickLinks() {
        const container = document.getElementById('quickLinks');
        if (!container) return;
        
        // 先显示默认的快速链接，避免页面卡住
        this.generateDefaultQuickLinks();
        
        try {
            // 获取工作流使用统计
            const statsResponse = await fetch('/api/workflow-stats');
            const statsData = await statsResponse.json();
            
            let recommendedWorkflows = [];
            
            if (statsData.success) {
                // 合并最近使用和热门工作流，避免重复
                const recentWorkflows = statsData.recent_workflows || [];
                const popularWorkflows = statsData.popular_workflows || [];
                
                // 创建工作流映射
                const workflowMap = {};
                this.workflows.forEach(w => {
                    workflowMap[w.filename] = w;
                });
                
                // 先添加最近使用的（最多3个）
                recentWorkflows.slice(0, 3).forEach(stat => {
                    const workflow = workflowMap[stat.workflow];
                    if (workflow) {
                        recommendedWorkflows.push({
                            ...workflow,
                            category: 'recent',
                            usage_count: stat.usage_count,
                            last_used: stat.last_used
                        });
                    }
                });
                
                // 再添加热门的，但排除已添加的（最多3个）
                const addedFilenames = new Set(recommendedWorkflows.map(w => w.filename));
                popularWorkflows.slice(0, 6).forEach(stat => {
                    if (recommendedWorkflows.length < 6 && !addedFilenames.has(stat.workflow)) {
                        const workflow = workflowMap[stat.workflow];
                        if (workflow) {
                            recommendedWorkflows.push({
                                ...workflow,
                                category: 'popular',
                                usage_count: stat.usage_count,
                                last_used: stat.last_used
                            });
                        }
                    }
                });
            }
            
            // 如果统计数据不足，用前6个工作流填充
            if (recommendedWorkflows.length < 6) {
                const usedFilenames = new Set(recommendedWorkflows.map(w => w.filename));
                this.workflows.slice(0, 6).forEach(workflow => {
                    if (recommendedWorkflows.length < 6 && !usedFilenames.has(workflow.filename)) {
                        recommendedWorkflows.push({
                            ...workflow,
                            category: 'default'
                        });
                    }
                });
            }
            
            const links = recommendedWorkflows.map(workflow => {
                const type = this.getWorkflowType(workflow.filename);
                const icon = this.getWorkflowIcon(type);
                const shortDesc = this.getShortDescription(workflow.description);
                
                // 添加标签显示
                let badge = '';
                if (workflow.category === 'recent') {
                    badge = '<span class="quick-link-badge recent">最近使用</span>';
                } else if (workflow.category === 'popular') {
                    badge = `<span class="quick-link-badge popular">热门(${workflow.usage_count}次)</span>`;
                }
                
                return `
                    <a href="?workflow=${encodeURIComponent(workflow.filename)}" class="quick-link-item">
                        <div class="quick-link-icon">
                            <i class="${icon}"></i>
                        </div>
                        <div class="quick-link-content">
                            <h4>${workflow.name}</h4>
                            <p>${shortDesc}</p>
                            ${badge}
                        </div>
                    </a>
                `;
            }).join('');
            
            container.innerHTML = links;
            
        } catch (error) {
            console.error('加载工作流统计失败:', error);
            // 保持默认的快速链接
        }
    }
    
    generateDefaultQuickLinks() {
        const container = document.getElementById('quickLinks');
        if (!container) return;
        
        // 降级方案：显示前6个工作流
        const defaultWorkflows = this.workflows.slice(0, 6);
        
        const links = defaultWorkflows.map(workflow => {
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
            // 记住最近工作流
            try { localStorage.setItem('cw_last_workflow', workflow.filename); } catch (_) {}
            // 先确定准确类型以驱动界面（提示词/图像输入等）
            try {
                const type = await this.getAccurateWorkflowType(workflow.filename);
                // 将准确类型注入 selectedWorkflow 供后续使用
                this.selectedWorkflow._accurateType = type;
            } catch {}
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
        
        // 使用精准类型覆盖
        if (this.selectedWorkflow && this.selectedWorkflow._accurateType) {
            analysis.type = this.selectedWorkflow._accurateType;
        }

        this.setDefaultValues(analysis.default_values);
        this.generateImageInputs(analysis.image_inputs);
        // 节点分组：仅按工作流节点定义渲染
        this.renderNodeGroups(analysis);
        // 通用节点分组：剔除模型加载器类与KSampler类
        this.renderGenericNodeParams({
            ...analysis,
            node_groups: (analysis.node_groups || []).filter(g => {
                const t = String(g.type || '');
                if (t.includes('Loader')) return false; // 2) 所有模型相关参数进入模型加载器分组
                if (t.includes('KSampler')) return false; // 3) KSampler 已在基础参数中体现
                return true;
            })
        });
        this.renderOutputSettings(analysis);
        this.generateModelLoaders(analysis.model_loaders);
        // 异步拉取模型库，增强下拉选择（不覆盖默认值，仅填充可选项）
        this.populateModelChoices();
        this.generateControlNetConfigs(analysis.controlnet_configs);
        this.toggleNegativePrompt(analysis.has_negative_prompt);
        this.generatePromptShortcuts(analysis);
        
        // 立即显示所有配置选项，不再需要点击切换
        this.showAllConfigSections();

        // 根据分析结果显式初始化 Inpaint 开关与 Outpaint 默认值
        try {
            const noiseMaskEl = document.getElementById('noise_mask');
            if (noiseMaskEl && typeof analysis?.default_values?.noise_mask !== 'undefined') {
                noiseMaskEl.checked = !!analysis.default_values.noise_mask;
                document.getElementById('inpaintExtrasRow').style.display = 'flex';
            }
        } catch(_) {}
        
        // 先显示页面，再展开基础参数，避免首次测量高度为0
        this.showPage('config');
        this.initializeCollapsibleSections();

        // 显示并启动资源监控
        this.showResourceMonitor();
        this.startResourceAutoRefresh();
    }

    renderNodeGroups(analysis) {
        // Resize 分组
        if (Array.isArray(analysis.resize_nodes) && analysis.resize_nodes.length > 0) {
            this.generateResizeParams(analysis.resize_nodes);
        } else {
            const blk = document.getElementById('resizeParamsBlock');
            if (blk) blk.innerHTML = '';
        }
        // Outpaint 分组
        if (Array.isArray(analysis.outpaint_nodes) && analysis.outpaint_nodes.length > 0) {
            this.generateOutpaintParams(analysis.outpaint_nodes);
        } else {
            const blk = document.getElementById('outpaintParamsBlock');
            if (blk) blk.innerHTML = '';
        }
        // KSampler（通用）分组（仅调度器/降噪/Flux Guidance）
        const block = document.getElementById('ksamplerParamsBlock');
        if (block) {
            const hasKSampler = !!analysis?.has_text_to_image;
            if (!hasKSampler) { block.innerHTML=''; } else {
                // 直接作为基础生成参数网格中的控件渲染（无额外分组标题），并补充默认值与备注
                // guidance 仅当 workflow 内存在 FluxGuidance 节点时才渲染，且默认值严格取自分析结果
                const hasFluxGuidance = !!(analysis && analysis.default_values && typeof analysis.default_values.guidance !== 'undefined');
                block.outerHTML = `
                  <div class="form-group">
                    <label>Scheduler</label>
                    <select id="scheduler" name="scheduler">
                      ${['normal','karras','exponential','sgm_uniform','simple','ddim_uniform','beta','linear_quadratic','kl_optimal'].map(opt => `<option value="${opt}" ${(analysis.default_values?.scheduler || 'normal') === opt ? 'selected' : ''}>${opt}</option>`).join('')}
                    </select>
                    <span class="default-value">默认: <span id="defaultScheduler">${analysis.default_values?.scheduler || 'normal'}</span></span>
                    <div class="form-hint">采样调度器影响噪声分布与收敛速度；Redux Dev 默认 simple，其他默认 normal。</div>
                  </div>
                  <div class="form-group">
                    <label>Denoise</label>
                    <input type="number" id="denoise" name="denoise" min="0" max="1" step="0.01" value="${analysis.default_values?.denoise || 1.0}" />
                    <span class="default-value">默认: <span id="defaultDenoise">${analysis.default_values?.denoise || 1.0}</span></span>
                    <div class="form-hint">去噪强度；越小保留初始条件（图生图/控制）越多，1 表示完全从噪声采样。</div>
                  </div>
                  ${hasFluxGuidance ? `
                  <div class="form-group">
                    <label>Flux Guidance</label>
                    <input type="number" id="guidance" name="guidance" min="0" max="40" step="0.5" value="${analysis.default_values.guidance}" />
                    <span class="default-value">默认: <span id="defaultGuidance">${analysis.default_values.guidance}</span></span>
                    <div class="form-hint">仅对 Flux 流派生效；越高越贴近提示词，过高可能牺牲自然度。</div>
                  </div>` : ''}`;
            }
        }
    }

    // 渲染输出设置区域
    renderOutputSettings(analysis) {
        const section = document.getElementById('outputSettingsSection');
        const container = document.getElementById('outputSettings');
        if (!section || !container) return;

        const outputSettings = analysis.output_settings || {};
        
        // 检查是否需要显示输出设置区域
        if (!outputSettings.has_output_control) {
            section.style.display = 'none';
            return;
        }

        section.style.display = 'block';
        
        const dimensions = outputSettings.output_dimensions || {width: 1024, height: 1024};
        const mode = outputSettings.size_control_mode || 'fixed';
        const batchSize = outputSettings.batch_settings?.batch_size || 1;

        container.innerHTML = `
            <div class="setting-group">
                <h4>🖼️ 输出尺寸</h4>
                <div class="form-row">
                    <div class="form-group">
                        <label for="output_width">宽度 (px)</label>
                        <input type="number" id="output_width" name="output_width" 
                               value="${dimensions.width}" min="512" max="2048" step="64">
                        <span class="default-value">默认: <span>${dimensions.width}</span></span>
                        <small class="form-hint">生成图像的宽度，建议使用64的倍数</small>
                    </div>
                    <div class="form-group">
                        <label for="output_height">高度 (px)</label>
                        <input type="number" id="output_height" name="output_height" 
                               value="${dimensions.height}" min="512" max="2048" step="64">
                        <span class="default-value">默认: <span>${dimensions.height}</span></span>
                        <small class="form-hint">生成图像的高度，建议使用64的倍数</small>
                    </div>
                </div>
                <div class="form-group">
                    <label for="size_control_mode">尺寸控制模式</label>
                    <select id="size_control_mode" name="size_control_mode">
                        <option value="fixed" ${mode === 'fixed' ? 'selected' : ''}>固定</option>
                        <option value="increment" ${mode === 'increment' ? 'selected' : ''}>递增</option>
                        <option value="decrement" ${mode === 'decrement' ? 'selected' : ''}>递减</option>
                        <option value="randomize" ${mode === 'randomize' ? 'selected' : ''}>随机</option>
                    </select>
                    <span class="default-value">默认: <span>${mode}</span></span>
                    <small class="form-hint">控制生成后的尺寸变化：固定=每次相同；递增/递减=自动调整；随机=每次不同</small>
                </div>
            </div>

            <div class="setting-group">
                <h4>📦 批量设置</h4>
                <div class="form-group">
                    <label for="batch_size">批量大小</label>
                    <input type="number" id="batch_size" name="batch_size" 
                           value="${batchSize}" min="1" max="4" step="1">
                    <span class="default-value">默认: <span>${batchSize}</span></span>
                    <small class="form-hint">一次生成的图片数量，数量越多消耗显存越大</small>
                </div>
            </div>
        `;
    }

    // 渲染通用节点参数分组：后端按每个节点收集的 widgets_values -> 通用参数
    renderGenericNodeParams(analysis) {
        const containerAnchor = document.getElementById('genericNodeParamsBlock');
        if (!containerAnchor) return;
        const groups = Array.isArray(analysis.node_groups) ? analysis.node_groups.slice() : [];
        if (groups.length === 0) {
            containerAnchor.innerHTML = '';
            return;
        }
        // 排序：先按常见节点重要性，其次 order，再按 type/title
        const priorityOrder = {
            'KSampler': 0, 'KSamplerSelect': 1, 
            // 这些节点的参数已在基础参数区展示，不重复显示
            'BasicScheduler': 9999,
            'FluxGuidance': 9999,
            'RandomNoise': 9999,
            'PrimitiveNode': 9999,
            'EmptySD3LatentImage': 9999,
            // 这些节点的参数已在模型加载器配置区展示，不重复显示
            'ModelSamplingFlux': 9999,
            'CLIPVisionEncode': 9999,
            'StyleModelApply': 9999,
            // 模型加载器本身在专门区域展示
            'NunchakuFluxDiTLoader': 9999,
            'DualCLIPLoader': 9999,
            'VAELoader': 9999,
            'CLIPVisionLoader': 9999,
            'StyleModelLoader': 9999,
            'NunchakuFluxLoraLoader': 9999,
            // 这些节点由专用卡片渲染
            'ImageAndMaskResizeNode': 9999,
            'ImagePadForOutpaint': 9999,
            // 普通文本输入节点优先级较低
            'CLIPTextEncode': 90,
            'EmptyLatentImage': 4, 
        };
        groups.sort((a,b)=>{
            const ap = priorityOrder[a.type] ?? 99;
            const bp = priorityOrder[b.type] ?? 99;
            if (ap !== bp) return ap - bp;
            const ao = (a.order ?? 9999) - (b.order ?? 9999);
            if (ao !== 0) return ao;
            return String(a.type).localeCompare(String(b.type));
        });
        // 仅渲染有参数的节点，避免空卡片
        const html = groups.map(g => {
            // 过滤 FluxGuidance 节点整个分组
            if (String(g.type || '').includes('FluxGuidance')) return '';
            // 过滤 LoadImage 和 CLIPTextEncode（这些由页面顶端统一覆盖）
            if (String(g.type || '').includes('LoadImage')) return '';
            if (String(g.type || '').includes('CLIPTextEncode')) return '';
            // 过滤备注/说明类节点
            if (String(g.type || '').includes('MarkdownNote') || String(g.type||'') === 'Note') return '';
            // 专用渲染的节点（Resize/Outpaint）不在通用分组里重复渲染
            if (String(g.type || '').includes('ImageAndMaskResizeNode')) return '';
            if (String(g.type || '').includes('ImagePadForOutpaint')) return '';
            const params = Array.isArray(g.params) ? g.params.filter(p => p && typeof p.widget_index === 'number') : [];
            if (params.length === 0) return '';
            // 为避免与已存在的专用区块重复，过滤掉基础参数中已经有的键和模型加载器中已经有的键
            const knownKeys = new Set([
                // 基础参数区的参数
                'width','height','steps','cfg','sampler','scheduler','denoise','guidance','seed','noise_seed','randomize',
                // 模型加载器区的参数
                'model_path','cache_threshold','attention','cpu_offload','device_id','data_type','i_2_f_mode','i2f_mode',
                'lora_name','lora_strength','vae_name','clip_name','clip_name1','clip_name2','type','device',
                'style_model_name','max_shift','base_shift','strength','strength_type','crop',
                // 常用的通用参数
                'value','batch_size','filename_prefix','text'
            ]);
            const items = params.map(p => {
                const pid = `node_${g.id}_${p.widget_index}`;
                const dataKey = `${g.id}:${p.widget_index}`;
                const paramMeta = this.getParamMeta(g.type || '', p.name || '', p.default, p.widget_index);
                const label = this.escapeHtml(paramMeta.label || p.label || p.name || `Param ${p.widget_index}`);
                const defVal = (p.default ?? '');
                // 如果名称命中基础参数，且该节点类型属于基础调度，不重复渲染
                if (knownKeys.has(String(p.name))) return '';
                let inputHtml = '';
                if (p.kind === 'boolean') {
                    const checked = defVal ? 'checked' : '';
                    inputHtml = `<input type="checkbox" data-node-param="${dataKey}" id="${pid}" ${checked}>`;
                } else if (p.kind === 'number') {
                    const val = (typeof defVal === 'number' && !Number.isNaN(defVal)) ? defVal : '';
                    inputHtml = `<input type="number" step="any" data-node-param="${dataKey}" id="${pid}" value="${val}">`;
                } else {
                    const val = typeof defVal === 'string' ? this.escapeHtml(defVal) : (defVal ?? '');
                    inputHtml = `<input type="text" data-node-param="${dataKey}" id="${pid}" value="${val}">`;
                }
                return `
                    <div class="form-group">
                        <label for="${pid}">${label} <span class="node-id-badge">#${g.id}:${p.widget_index}</span></label>
                        ${inputHtml}
                        <span class="default-value">默认: ${defVal===undefined||defVal===null? '': this.escapeHtml(String(defVal))}</span>
                        ${paramMeta.hint ? `<div class="form-hint">${this.escapeHtml(paramMeta.hint)}</div>` : ''}
                    </div>
                `;
            }).filter(Boolean).join('');
            if (!items) return '';
            return `
                <div class="model-loader-group">
                  <div class="loader-header">
                    <h4>${this.escapeHtml(this.getFriendlyNodeName(g.type || '', g.title))}</h4>
                    <span class="loader-type">${this.escapeHtml(g.type)}</span>
                  </div>
                  <div class="loader-parameters">${items}</div>
                </div>
            `;
        }).filter(Boolean).join('');
        containerAnchor.innerHTML = html;
    }

    generateOutpaintParams(outpaintNodes) {
        // 在当前结构中没有 id=advancedParams，改为直接使用锚点或节点参数容器
        const container = document.getElementById('nodeParametersContent');
        const node = Array.isArray(outpaintNodes) && outpaintNodes.length > 0 ? outpaintNodes[0] : null;
        const params = (node && node.parameters) || {};
        const html = `
          <div class="model-loader-group">
            <div class="loader-header">
              <h4>${this.getFriendlyNodeName('ImagePadForOutpaint','扩图设置（Outpaint）')}</h4>
              <span class="loader-type">ImagePadForOutpaint</span>
            </div>
            <div class="loader-parameters">
              <div class="form-group">
                <label>左 (px)</label>
                <input type="number" id="outpaint_left" name="outpaint_left" min="0" max="2048" step="1" value="${params.pad_left ?? 0}" />
                <span class="default-value">默认: ${params.pad_left ?? 0}</span>
                <div class="form-hint">在左侧扩展的像素数量。</div>
              </div>
              <div class="form-group">
                <label>上 (px)</label>
                <input type="number" id="outpaint_top" name="outpaint_top" min="0" max="2048" step="1" value="${params.pad_up ?? 0}" />
                <span class="default-value">默认: ${params.pad_up ?? 0}</span>
                <div class="form-hint">在上方扩展的像素数量。</div>
              </div>
              <div class="form-group">
                <label>右 (px)</label>
                <input type="number" id="outpaint_right" name="outpaint_right" min="0" max="2048" step="1" value="${params.pad_right ?? 0}" />
                <span class="default-value">默认: ${params.pad_right ?? 0}</span>
                <div class="form-hint">在右侧扩展的像素数量。</div>
              </div>
              <div class="form-group">
                <label>下 (px)</label>
                <input type="number" id="outpaint_bottom" name="outpaint_bottom" min="0" max="2048" step="1" value="${params.pad_down ?? 0}" />
                <span class="default-value">默认: ${params.pad_down ?? 0}</span>
                <div class="form-hint">在下方扩展的像素数量。</div>
              </div>
              <div class="form-group">
                <label>羽化 (px)</label>
                <input type="number" id="outpaint_feather" name="outpaint_feather" min="0" max="256" step="1" value="${params.feather ?? 24}" />
                <span class="default-value">默认: ${params.feather ?? 24}</span>
                <div class="form-hint">边缘过渡羽化半径，数值越大越柔和。</div>
              </div>
            </div>
          </div>`;
        const anchor = document.getElementById('outpaintParamsBlock');
        if (anchor) {
            anchor.outerHTML = `<div id="outpaintParamsBlock">${html}</div>`;
        } else {
            const wrap = document.createElement('div');
            wrap.id = 'outpaintParamsBlock';
            wrap.innerHTML = html;
            if (container) container.appendChild(wrap);
        }
    }

    generateResizeParams(resizeNodes) {
        // 在当前结构中没有 id=advancedParams，改为直接使用锚点或节点参数容器
        const container = document.getElementById('nodeParametersContent');
        const node = Array.isArray(resizeNodes) && resizeNodes.length > 0 ? resizeNodes[0] : null;
        const params = (node && node.parameters) || {};
        const html = `
          <div class="model-loader-group">
            <div class="loader-header">
              <h4>${this.getFriendlyNodeName('ImageAndMaskResizeNode','图像与掩码缩放')}</h4>
              <span class="loader-type">ImageAndMaskResizeNode</span>
            </div>
            <div class="loader-parameters">
              <div class="form-group">
                <label>图像宽度 (px)</label>
                <input type="number" id="width" name="width" min="64" max="2048" step="64" value="${params.width ?? 1024}" />
                <span class="default-value">默认: ${params.width ?? 1024}</span>
                <div class="form-hint">用于生成的目标宽度；若工作流内连接到 Latent/Flux 采样模型，也会同步影响该模块。</div>
              </div>
              <div class="form-group">
                <label>图像高度 (px)</label>
                <input type="number" id="height" name="height" min="64" max="2048" step="64" value="${params.height ?? 1024}" />
                <span class="default-value">默认: ${params.height ?? 1024}</span>
                <div class="form-hint">用于生成的目标高度；与宽度共同决定分辨率。</div>
              </div>
              <div class="form-group">
                <label>缩放算法</label>
                <select id="resize_method" name="resize_method">
                  ${['nearest-exact','nearest','area','bilinear','bicubic'].map(opt => `<option value="${opt}" ${params.resize_method===opt?'selected':''}>${opt}</option>`).join('')}
                </select>
                <span class="default-value">默认: ${params.resize_method ?? 'nearest-exact'}</span>
                <div class="form-hint">选择插值方式，影响缩放质量与速度。</div>
              </div>
              <div class="form-group">
                <label>裁剪</label>
                 <select id="crop" name="crop">
                   ${['center','disabled'].map(opt => `<option value="${opt}" ${params.crop===opt?'selected':''}>${opt}</option>`).join('')}
                 </select>
                <span class="default-value">默认: ${params.crop ?? 'center'}</span>
                <div class="form-hint">center 保持中心；disabled 不裁剪。</div>
              </div>
              <div class="form-group">
                <label>掩码羽化半径 (px)</label>
                <input type="number" id="mask_blur_radius" name="mask_blur_radius" min="0" max="64" value="${params.mask_blur_radius ?? 24}" />
                <span class="default-value">默认: ${params.mask_blur_radius ?? 24}</span>
                <div class="form-hint">增大以减轻硬边。</div>
              </div>
              <div class="form-group" id="inpaintExtrasRow" style="display:none;">
                <label><input type="checkbox" id="noise_mask" /> 噪声遮罩（Inpaint）</label>
                <div class="form-hint">启用后仅在遮罩区域填充噪声进行修复。</div>
              </div>
              <div class="form-group">
                <label><input type="checkbox" id="autoOutpaintMask" checked /> 自动扩图掩码</label>
                <div class="form-hint">在扩图工作流中自动生成与原图尺寸匹配的掩码。</div>
              </div>
            </div>
          </div>`;
        const anchor = document.getElementById('resizeParamsBlock');
        if (anchor) {
            anchor.outerHTML = `<div id="resizeParamsBlock">${html}</div>`;
        } else {
            const wrap = document.createElement('div');
            wrap.id = 'resizeParamsBlock';
            wrap.innerHTML = html;
            if (container) container.appendChild(wrap);
        }
    }

    async populateModelChoices() {
        try {
            const resp = await fetch('/api/model-files');
            if (!resp.ok) return;
            const data = await resp.json();
            if (!data.success) return;
            const cats = data.categories || {};
            // 缓存分类供后续填充 select
            this.modelCategories = cats;

            // 根据已渲染的输入框，补充datalist供下拉/自动补全
            const addDataList = (inputId, listId, items) => {
                const input = document.getElementById(inputId);
                if (!input) return;
                let dl = document.getElementById(listId);
                if (!dl) {
                    dl = document.createElement('datalist');
                    dl.id = listId;
                    document.body.appendChild(dl);
                }
                dl.innerHTML = (items || []).map(n => `<option value="${n}"></option>`).join('');
                input.setAttribute('list', listId);
            };

            // 视觉CLIP（CLIPVisionLoader）的 clip_name_* 改为 select；保留默认值
            document.querySelectorAll('select[id^="clip_name_"]').forEach(sel => {
                const items = (cats.clip_vision || []).concat(cats.clip || []);
                const def = sel.getAttribute('data-default') || '';
                sel.innerHTML = items.map(v => `<option value="${v}" ${def===v?'selected':''}>${v}</option>`).join('');
                if (def && !items.includes(def)) sel.insertAdjacentHTML('afterbegin', `<option value="${def}" selected>${def}</option>`);
            });

            // 文本编码器/CLIP（DualCLIPLoader）
            // DualCLIPLoader 改为 select：直接填充所有候选，点击即展开；保留默认值
            document.querySelectorAll('select[id^="clip_name1_"]').forEach(sel => {
                const items = cats.clip || [];
                const def = sel.getAttribute('data-default') || '';
                sel.innerHTML = items.map(v => `<option value="${v}" ${def===v?'selected':''}>${v}</option>`).join('');
                if (def && !items.includes(def)) sel.insertAdjacentHTML('afterbegin', `<option value="${def}" selected>${def}</option>`);
            });
            document.querySelectorAll('select[id^="clip_name2_"]').forEach(sel => {
                const items = cats.clip || [];
                const def = sel.getAttribute('data-default') || '';
                sel.innerHTML = items.map(v => `<option value="${v}" ${def===v?'selected':''}>${v}</option>`).join('');
                if (def && !items.includes(def)) sel.insertAdjacentHTML('afterbegin', `<option value="${def}" selected>${def}</option>`);
            });

            // VAE
            // VAE 改为 select：点击无输入也能看到全部
            document.querySelectorAll('select[id^="vae_name_"]').forEach(sel => {
                const items = cats.vae || [];
                const def = sel.getAttribute('data-default') || '';
                sel.innerHTML = items.map(v => `<option value="${v}" ${def===v?'selected':''}>${v}</option>`).join('');
                if (def && !items.includes(def)) sel.insertAdjacentHTML('afterbegin', `<option value="${def}" selected>${def}</option>`);
            });

            // LoRA
            // LoRA 改为 select
            document.querySelectorAll('select[id^="lora_name_"]').forEach(sel => {
                const items = (cats.loras || []).concat(cats.lora || []);
                const def = sel.getAttribute('data-default') || '';
                sel.innerHTML = items.map(v => `<option value="${v}" ${def===v?'selected':''}>${v}</option>`).join('');
                if (def && !items.includes(def)) sel.insertAdjacentHTML('afterbegin', `<option value="${def}" selected>${def}</option>`);
                // 绑定变更事件：自动拉取 LoRA 触发词与提示
                sel.addEventListener('change', async () => {
                    try {
                        const val = sel.value;
                        if (!val) return;
                        const nodeId = (sel.id.split('_').pop()) || '';
                        const hint = document.getElementById(`loraInfo_${nodeId}`);
                        if (hint) { hint.style.display = 'block'; hint.textContent = '正在读取 LoRA 提示与触发词…'; }
                        const resp = await fetch(`/api/lora-info?name=${encodeURIComponent(val)}`);
                        const data = await resp.json();
                        const item = (data.items && data.items[val]) || { triggers: [], tips: [] };
                        let triggers = (item.triggers || []).slice(0, 12);
                        const tips = (item.tips || []).slice(0, 6);
                        const triggerHtml = triggers.length ? `<div><b>触发词:</b> ${triggers.join(', ')}</div>` : '';
                        const tipsHtml = tips.length ? `<ul style="margin:6px 0 0 14px;">${tips.map(t => `<li>${this.escapeHtml(t)}</li>`).join('')}</ul>` : '';
                        if (hint) {
                            hint.innerHTML = `${triggerHtml}${tipsHtml || (triggerHtml ? '' : '<span>无可用提示</span>')}`;
                            hint.style.display = (triggerHtml || tipsHtml) ? 'block' : 'none';
                        }
                        // 更新小问号气泡的内容
                        const tipBtn = document.getElementById(`lora_tip_btn_${nodeId}`);
                        if (tipBtn) {
                            const compact = (item.tips || []).join('\n');
                            tipBtn.title = compact || '暂无Tips';
                        }
                        // 将触发词插入到快捷提示词组前置区（若无触发词，回退用 tips 拆分的短语）
                        if (!triggers.length && tips.length) {
                            const parsed = [];
                            tips.forEach(t => {
                                String(t).split(/[，,\n]/).forEach(p => {
                                    const s = p.trim();
                                    if (s) parsed.push(s);
                                });
                            });
                            triggers = parsed.slice(0, 12);
                        }
                        if (triggers.length) this.safeInsertLoraShortcuts(triggers, val);
                    } catch (e) {}
                });
                // 初次渲染时也触发一次，若已有默认值
                try { sel.dispatchEvent(new Event('change')); } catch(_) {}
            });

            // StyleModel（若有专用目录可映射到 style_models，否则复用 clip/其他）
            // StyleModel 改为 select
            document.querySelectorAll('select[id^="style_model_name_"]').forEach(sel => {
                const items = cats.style_models || [];
                const def = sel.getAttribute('data-default') || '';
                sel.innerHTML = items.map(v => `<option value="${v}" ${def===v?'selected':''}>${v}</option>`).join('');
                if (def && !items.includes(def)) sel.insertAdjacentHTML('afterbegin', `<option value="${def}" selected>${def}</option>`);
            });

            // 主模型/检查点
            // Checkpoint 改为 select
            document.querySelectorAll('select[id^="ckpt_name_"]').forEach(sel => {
                const items = (cats.checkpoints || []).concat(cats.unet || []);
                const def = sel.getAttribute('data-default') || '';
                sel.innerHTML = items.map(v => `<option value="${v}" ${def===v?'selected':''}>${v}</option>`).join('');
                if (def && !items.includes(def)) sel.insertAdjacentHTML('afterbegin', `<option value="${def}" selected>${def}</option>`);
            });

            // 主模型路径（NunchakuFluxDiTLoader）
            // NunchakuFluxDiTLoader 的 model_path 改为 select（包含 unet+checkpoints）
            document.querySelectorAll('select[id^="model_path_"]').forEach(sel => {
                const items = (cats.unet || []).concat(cats.checkpoints || []);
                const def = sel.getAttribute('data-default') || '';
                sel.innerHTML = items.map(v => `<option value="${v}" ${def===v?'selected':''}>${v}</option>`).join('');
                if (def && !items.includes(def)) sel.insertAdjacentHTML('afterbegin', `<option value="${def}" selected>${def}</option>`);
            });

            // ControlNet 模型
            // ControlNet 模型 改为 select
            document.querySelectorAll('select[id^="control_net_name_"]').forEach(sel => {
                const items = cats.controlnet || [];
                const def = sel.getAttribute('data-default') || '';
                sel.innerHTML = items.map(v => `<option value="${v}" ${def===v?'selected':''}>${v}</option>`).join('');
                if (def && !items.includes(def)) sel.insertAdjacentHTML('afterbegin', `<option value="${def}" selected>${def}</option>`);
            });

            // NunchakuFluxDiTLoader 的 model_path 可能不是文件而是别名，保留手输
        } catch {}
    }

    // 取消自定义下拉，完全采用原生 datalist 行为（保持与 VAE 一致）
    // 生成快捷提示词按钮（根据工作流类型/模式）
    generatePromptShortcuts(analysis) {
        const container = document.getElementById('promptShortcuts');
        const hint = document.getElementById('promptContextHint');
        if (!container) return;

        // 清空容器
        container.innerHTML = '';

        // 判定工作流类型
        const filename = (this.selectedWorkflow?.filename || '').toLowerCase();
        const isFlux = filename.includes('flux');
        // 优先使用 analyze-workflow 的类型，其次 selectedWorkflow._accurateType，最后快速猜测
        const mode = analysis?.type || this.selectedWorkflow?._accurateType || this.getWorkflowType(filename) || 'text-to-image';
        const isTxt2Img = mode === 'text-to-image';
        const isImg2Img = mode === 'image-to-image';

        // 记录当前快捷分组上下文，供"最近/最常用"类型过滤使用
        this.shortcutContext = { isFlux, isTxt2Img, isImg2Img };

        if (hint) {
            hint.textContent = `${isFlux ? 'Flux' : '标准'} · ${isTxt2Img ? '文生图' : (isImg2Img ? '图生图' : mode)} · 已适配快捷提示词`;
        }

        // 定义分组数据
        const groups = this.buildPromptShortcutGroups({ isFlux, isTxt2Img, isImg2Img });

        // 不再插入静态的"LoRA 触发词"组，改为选择LoRA后动态插入（见 prependLoraPromptShortcuts）

        // 在最上方插入：最近使用、最常用
        const topGroups = [];
        const recent = this.getRecentShortcutGroup(8, this.shortcutContext);
        const frequent = this.getFrequentShortcutGroup(8, this.shortcutContext);
        if (recent) topGroups.push(recent);
        if (frequent) topGroups.push(frequent);
        if (topGroups.length > 0) {
            topGroups.reverse().forEach(g => groups.unshift(g));
        }

        // 渲染：扁平化所有子分组为同级卡片，按原总分组顺序连续排列
        const grid = document.createElement('div');
        grid.className = 'subgroup-grid all-subgroups';
        const self = this; // 稳定引用，避免事件回调中 this 被改变

        const flatSubs = [];
        groups.forEach(group => {
            if (Array.isArray(group.subgroups) && group.subgroups.length > 0) {
                group.subgroups.forEach(sub => flatSubs.push(sub));
            } else if (group.items && group.items.length > 0) {
                flatSubs.push({ title: group.title, items: group.items });
            }
        });

        flatSubs.forEach(sub => {
            const subCard = document.createElement('div');
            subCard.className = 'shortcut-subgroup';

            const subHeader = document.createElement('h5');
            subHeader.className = 'shortcut-subheader';
            subHeader.textContent = sub.title;
            subCard.appendChild(subHeader);

            const subButtons = document.createElement('div');
            subButtons.className = 'shortcut-buttons';
            (sub.items || []).forEach(item => {
                const btn = document.createElement('button');
                btn.type = 'button';
                btn.className = 'shortcut-btn';
                btn.textContent = item.label;
                btn.addEventListener('click', () => {
                    self.lastPresetLabel = item.label;
                    if (typeof self.applyPromptShortcut === 'function') {
                        try { self.applyPromptShortcut(item); return; } catch (_) {}
                    }
                    if (self.promptSystem && typeof self.promptSystem.applyPromptShortcut === 'function') {
                        try { self.promptSystem.applyPromptShortcut(item); return; } catch (_) {}
                    }
                    // 兜底直写
                    try {
                        const positiveEl = document.getElementById('positivePrompt');
                        const negativeEl = document.getElementById('negativePrompt');
                        const overwrite = document.getElementById('promptOverwriteSwitch')?.checked;
                        const applyToField = (el, text) => {
                            if (!el || !text) return;
                            const trimmed = (el.value || '').trim();
                            if (overwrite || !trimmed) el.value = text; else el.value = el.value + (trimmed.endsWith(',') ? ' ' : ', ') + text;
                            el.dispatchEvent(new Event('input', { bubbles: true }));
                            el.dispatchEvent(new Event('change', { bubbles: true }));
                        };
                        applyToField(positiveEl, item?.prompt || item?.label || '');
                        if (item?.negative) applyToField(negativeEl, item.negative);
                    } catch (_) {}
                });
                // 右键菜单：收藏/编辑为自定义/复制/仅插入负面
                btn.addEventListener('contextmenu', (ev) => {
                    ev.preventDefault();
                    const menu = document.createElement('div');
                    menu.style.cssText = 'position:absolute; z-index:9999; background:var(--card-bg); border:1px solid var(--border-color); border-radius:6px; padding:6px; box-shadow: var(--shadow)';
                    const makeItem = (text, handler) => {
                        const a = document.createElement('div'); a.textContent = text; a.style.cssText = 'padding:6px 10px; cursor:pointer;'; a.addEventListener('click', ()=>{ try{ handler(); }catch(_){}; try{ menu.remove(); }catch(_){} }); a.addEventListener('mouseenter', ()=> a.style.background = 'var(--bg-secondary)'); a.addEventListener('mouseleave', ()=> a.style.background = 'transparent'); return a;
                    };
                    menu.appendChild(makeItem('收藏/取消收藏', () => {
                        try { if (self.promptSystem) { const added = self.promptSystem.toggleFavorite(item); self._showToast && self._showToast(added ? '已收藏' : '已取消收藏'); } } catch(_) {}
                    }));
                    menu.appendChild(makeItem('保存为自定义...', () => {
                        try { if (self.promptSystem && typeof self.promptSystem.openInlineEdit === 'function') self.promptSystem.openInlineEdit(item); } catch(_) {}
                    }));
                    menu.appendChild(makeItem('复制到剪贴板', () => {
                        try { navigator.clipboard.writeText(item.prompt || item.label || ''); self._showToast && self._showToast('已复制'); } catch(_) {}
                    }));
                    if (item.negative) {
                        menu.appendChild(makeItem('仅插入负面', () => {
                            try {
                                const negativeEl = document.getElementById('negativePrompt');
                                const overwrite = document.getElementById('promptOverwriteSwitch')?.checked;
                                const ntrim = (negativeEl?.value || '').trim();
                                if (negativeEl) {
                                    if (overwrite || !ntrim) negativeEl.value = item.negative; else negativeEl.value = negativeEl.value + (ntrim.endsWith(',') ? ' ' : ', ') + (item.negative || '');
                                    negativeEl.dispatchEvent(new Event('input', { bubbles: true }));
                                    negativeEl.dispatchEvent(new Event('change', { bubbles: true }));
                                }
                            } catch(_) {}
                        }));
                    }
                    document.body.appendChild(menu);
                    const x = ev.clientX, y = ev.clientY; menu.style.left = `${x}px`; menu.style.top = `${y}px`;
                    const onHide = () => { try { menu.remove(); } catch(_){}; document.removeEventListener('click', onHide); };
                    document.addEventListener('click', onHide);
                });
                subButtons.appendChild(btn);
            });
            subCard.appendChild(subButtons);
            grid.appendChild(subCard);
        });

        container.appendChild(grid);

        // 监听收藏/自定义更新事件，实时重绘快捷区
        try {
            if (!this._promptEventsBound) {
                window.addEventListener('cw_prompt_favorites_updated', () => {
                    try { this.generatePromptShortcuts(analysis); } catch (_) {}
                });
                window.addEventListener('cw_prompt_custom_updated', () => {
                    try { this.generatePromptShortcuts(analysis); } catch (_) {}
                });
                this._promptEventsBound = true;
            }
        } catch (_) {}

        // 渲染完成后，若 LoRA 有默认值，重触发一次以将触发词插入快捷区顶部
        try {
            document.querySelectorAll('select[id^="lora_name_"]').forEach(sel => {
                if (sel && sel.value) {
                    sel.dispatchEvent(new Event('change'));
                }
            });
        } catch (_) {}

        // 兜底：直接读取当前 LoRA 选择并拉取触发词，插入到快捷区顶部（避免事件竞态）
        try {
            const selected = Array.from(document.querySelectorAll('select[id^="lora_name_"]'))
                .map(sel => sel && sel.value).filter(Boolean);
            const uniq = Array.from(new Set(selected));
            if (uniq.length > 0) {
                const query = uniq.map(n => `name=${encodeURIComponent(n)}`).join('&');
                fetch(`/api/lora-info?${query}`).then(r => r.json()).then(data => {
                    if (!data || !data.items) return;
                    uniq.forEach(n => {
                        const item = data.items[n];
                        const triggers = (item && item.triggers) || [];
                        if (triggers.length) this.safeInsertLoraShortcuts(triggers, n);
                    });
                }).catch(() => {});
            }
        } catch (_) {}

        // 最终兜底：观察 LoRA 信息提示块变化（loraInfo_*），一旦出现"触发词:"文本或提示列表，立即插入快捷区
        try { this.observeLoraInfoAndInsertShortcuts(); } catch (_) {}
    }

    // 监听 loraInfo_* 的内容变化，自动解析并插入快捷区
    observeLoraInfoAndInsertShortcuts() {
        const parseTriggersFromHint = (el) => {
            if (!el) return [];
            // 严格只从"触发词:"那一行解析，避免把评论 tips 当作触发词
            const triggerLine = el.querySelector('div');
            if (!triggerLine) return [];
            const text = triggerLine.textContent || '';
            const idx = text.indexOf('触发词:');
            if (idx < 0) return [];
            const part = text.slice(idx + '触发词:'.length).trim();
            const items = part.split(/[，,]/).map(s => s.trim()).filter(Boolean);
            // 过滤明显为长句或说明性的项，只保留较短的词/短语
            const filtered = items.filter(s => s.length <= 40);
            return filtered.slice(0, 12);
        };

        const ensureInsertForNodeId = (nodeId) => {
            const hint = document.getElementById(`loraInfo_${nodeId}`);
            const sel = document.getElementById(`lora_name_${nodeId}`);
            if (!hint || !sel) return;
            const words = parseTriggersFromHint(hint);
            if (words && words.length) this.safeInsertLoraShortcuts(words, sel.value || 'LoRA');
        };

        // 初次扫描
        Array.from(document.querySelectorAll('div[id^="loraInfo_"]')).forEach(div => {
            const nodeId = (div.id.split('_').pop()) || '';
            ensureInsertForNodeId(nodeId);
        });

        // 观察后续变化
        const container = document.getElementById('modelLoadersSection') || document;
        try {
            const mo = new MutationObserver((mutations) => {
                for (const m of mutations) {
                    if (!m.target || !(m.target instanceof HTMLElement)) continue;
                    const el = m.target.closest && m.target.closest('div[id^="loraInfo_"]');
                    const idEl = el || (m.target.id && String(m.target.id).startsWith('loraInfo_') ? m.target : null);
                    if (idEl) {
                        const nodeId = (idEl.id.split('_').pop()) || '';
                        ensureInsertForNodeId(nodeId);
                    }
                }
            });
            mo.observe(container, { childList: true, subtree: true, characterData: true });
            this._loraInfoObserver = mo;
        } catch (_) {}
    }

    // 提示词系统 - 委托给独立模块
    buildPromptShortcutGroups({ isFlux, isTxt2Img, isImg2Img }) {
        this.promptSystem.selectedWorkflow = this.selectedWorkflow;
        return this.promptSystem.buildPromptShortcutGroups({ isFlux, isTxt2Img, isImg2Img });
    }

    // 旧的提示词系统函数 - 已被新系统替代
    buildPromptShortcutGroups_OLD({ isFlux, isTxt2Img, isImg2Img }) {
        const filename = (this.selectedWorkflow?.filename || '').toLowerCase();

        // ============== FLUX 文生图提示词库 ==============
        const fluxTextToImageGroups = [
            {
                title: '📸 摄影类', badges: ['Flux'], items: [
                    { label: '人像摄影', prompt: 'A professional portrait photograph with natural lighting and shallow depth of field, detailed skin texture, sharp eyes, high resolution' },
                    { label: '环境人像', prompt: 'A portrait photograph showing person in their natural environment, documentary style, authentic moment captured' },
                    { label: '工作室人像', prompt: 'A studio portrait with professional lighting setup, clean background, polished commercial photography style' },
                    { label: '街头人像', prompt: 'A candid street portrait with urban background, natural expression, photojournalistic style' },
                    { label: '风景摄影', prompt: 'A landscape photograph with dramatic natural lighting, wide composition, detailed textures, professional camera work' },
                    { label: '城市风光', prompt: 'An urban landscape photograph capturing city skyline, architectural details, dynamic lighting conditions' },
                    { label: '自然风光', prompt: 'A nature landscape showing pristine wilderness, dramatic sky, rich natural colors and textures' },
                    { label: '微距摄影', prompt: 'A macro photograph revealing intricate details, shallow depth of field, beautiful bokeh, scientific precision' },
                    { label: '产品摄影', prompt: 'A professional product photograph with clean background, even lighting, detailed textures, commercial quality' },
                    { label: '建筑摄影', prompt: 'An architectural photograph emphasizing geometric forms, interesting perspectives, natural and artificial lighting' }
                ]
            },
            {
                title: '🎨 艺术创作', badges: ['Flux'], items: [
                    { label: '数字绘画', prompt: 'A digital painting with painterly brushstrokes, rich colors, artistic composition, detailed illustration' },
                    { label: '概念艺术', prompt: 'A concept art illustration with cinematic composition, detailed environment design, professional artwork' },
                    { label: '角色设计', prompt: 'A character design illustration with detailed features, expressive pose, clean art style, professional character art' },
                    { label: '水彩风格', prompt: 'A watercolor painting with soft, flowing edges, translucent washes, organic color bleeding, artistic spontaneity' },
                    { label: '油画风格', prompt: 'An oil painting with rich impasto textures, classical techniques, sophisticated color mixing, fine art quality' },
                    { label: '插画风格', prompt: 'A stylized illustration with clean lines, balanced composition, vibrant colors, editorial quality artwork' },
                    { label: '素描风格', prompt: 'A detailed pencil drawing with fine line work, subtle shading, classical draftsmanship, monochromatic tones' },
                    { label: '漫画风格', prompt: 'A comic book style illustration with bold outlines, dynamic poses, expressive features, vibrant colors' }
                ]
            },
            {
                title: '💡 创意场景', badges: ['Flux'], items: [
                    { label: '科幻场景', prompt: 'A futuristic science fiction scene with advanced technology, sleek designs, atmospheric lighting, imaginative concepts' },
                    { label: '奇幻世界', prompt: 'A fantasy world scene with magical elements, ethereal atmosphere, rich storytelling details, mystical quality' },
                    { label: '历史重现', prompt: 'A historical scene accurately depicting period details, authentic costumes, appropriate architecture, documentary realism' },
                    { label: '日常生活', prompt: 'A slice of life scene capturing ordinary moments with warmth, authenticity, relatable human experiences' },
                    { label: '抽象概念', prompt: 'An abstract visual representation of ideas or emotions through color, form, and composition, non-literal interpretation' },
                    { label: '超现实主义', prompt: 'A surreal scene blending reality with impossible elements, dreamlike quality, thought-provoking imagery' }
                ]
            },
            {
                title: '🌟 质量优化', badges: ['Flux'], items: [
                    { label: '专业品质', prompt: 'Professional quality with meticulous attention to detail, perfect technical execution, commercial grade standards' },
                    { label: '艺术精品', prompt: 'Masterpiece quality with exceptional artistic merit, museum-worthy craftsmanship, timeless aesthetic appeal' },
                    { label: '高分辨率', prompt: 'Ultra high resolution with crystal clear details, sharp focus throughout, suitable for large format printing' },
                    { label: '电影质感', prompt: 'Cinematic quality with dramatic lighting, professional color grading, film-like depth and atmosphere' },
                    { label: '纪实风格', prompt: 'Documentary style with authentic, unposed moments, natural lighting, journalistic integrity' }
                ]
            }
        ];

        // ============== FLUX 图生图提示词库 ==============
        const fluxImageToImageGroups = [
            {
                title: '🎯 精确编辑', badges: ['Flux'], items: [
                    { label: '保持一致性', prompt: 'Maintain the exact same person with identical facial features, expression, pose, and all physical characteristics unchanged' },
                    { label: '背景替换', prompt: 'Replace the entire background with a completely new environment while keeping the main subject perfectly unchanged in position and appearance' },
                    { label: '服装更换', prompt: 'Change the clothing while keeping the person, pose, and facial expression exactly the same, maintain body proportions' },
                    { label: '表情调整', prompt: 'Modify the facial expression while preserving all other facial features, identity, and overall composition' },
                    { label: '姿态调整', prompt: 'Adjust the body pose or gesture while maintaining the person\'s identity, facial features, and overall character' },
                    { label: '添加元素', prompt: 'Add new objects or elements to the scene while preserving the existing composition and main subjects unchanged' }
                ]
            },
            {
                title: '🎨 风格转换', badges: ['Flux'], items: [
                    { label: '艺术风格', prompt: 'Transform into an artistic painting style while preserving the subject\'s identity and basic composition structure' },
                    { label: '水彩效果', prompt: 'Convert to watercolor painting style with soft, flowing edges and translucent washes while keeping the composition intact' },
                    { label: '油画效果', prompt: 'Transform into oil painting style with rich textures and classical techniques while maintaining subject recognition' },
                    { label: '素描效果', prompt: 'Convert to detailed pencil sketch with fine line work and shading while preserving all recognizable features' },
                    { label: '漫画风格', prompt: 'Transform into comic book illustration style with bold outlines and stylized features while keeping character identity' },
                    { label: '黑白处理', prompt: 'Convert to black and white with enhanced contrast and dramatic lighting while maintaining all compositional elements' }
                ]
            },
            {
                title: '⚡ 质量提升', badges: ['Flux'], items: [
                    { label: '细节增强', prompt: 'Enhance all details and textures while maintaining the exact same composition, colors, and subject matter' },
                    { label: '清晰度提升', prompt: 'Improve image sharpness and clarity throughout while preserving all original elements and characteristics' },
                    { label: '色彩增强', prompt: 'Enhance color saturation and vibrancy while keeping the same lighting conditions and overall mood' },
                    { label: '光线优化', prompt: 'Improve lighting quality and balance while maintaining the same scene composition and subject positioning' },
                    { label: '去噪处理', prompt: 'Remove noise and artifacts while preserving all fine details and maintaining image authenticity' }
                ]
            }
        ];

        // ============== Redux 专用提示词库 ==============
        const reduxSpecificGroups = [
            {
                title: '🔄 Redux特效', badges: ['Redux'], items: [
                    { label: 'Redux增强', prompt: 'Enhanced with Redux processing for improved detail reconstruction and natural texture refinement' },
                    { label: '细节重建', prompt: 'Detailed reconstruction focusing on texture enhancement, edge refinement, and natural detail restoration' },
                    { label: '质感提升', prompt: 'Material texture enhancement with realistic surface properties and natural lighting interaction' },
                    { label: '边缘优化', prompt: 'Edge refinement and sharpening while maintaining natural appearance and avoiding over-processing artifacts' }
                ]
            }
        ];

        // ============== ControlNet 专用提示词库 ==============
        const controlnetSpecificGroups = [
            {
                title: '🎮 ControlNet控制', badges: ['ControlNet'], items: [
                    { label: '姿态控制', prompt: 'Precise pose control while maintaining natural body proportions and realistic joint articulation' },
                    { label: '边缘引导', prompt: 'Edge-guided generation following the provided structural outline while adding realistic details' },
                    { label: '深度控制', prompt: 'Depth-aware generation maintaining proper spatial relationships and realistic perspective' },
                    { label: '语义分割', prompt: 'Semantic segmentation guided creation with accurate object boundaries and realistic textures' }
                ]
            }
        ];

        // ============== Outpaint 专用提示词库 ==============
        const outpaintSpecificGroups = [
            {
                title: '🖼️ 扩展绘制', badges: ['Outpaint'], items: [
                    { label: '无缝扩展', prompt: 'Seamless outpainting that naturally extends the existing scene with consistent lighting and perspective' },
                    { label: '环境补全', prompt: 'Complete the surrounding environment while maintaining visual coherence and realistic spatial relationships' },
                    { label: '边界融合', prompt: 'Smooth boundary blending between original and extended areas with natural transition zones' },
                    { label: '背景延续', prompt: 'Continue the background patterns and textures naturally while preserving the original scene\'s mood and style' }
                ]
            }
        ];

        // ============== 传统模型提示词库 ==============
        const legacyGroups = [
            {
                title: '📷 经典摄影', badges: ['传统'], items: [
                    { label: '人像摄影', prompt: '8k, ultra detailed, high dynamic range, portrait, natural skin texture, softbox lighting, catchlight in eyes, sharp focus, masterpiece, best quality' },
                    { label: '风景摄影', prompt: '8k, ultra detailed, landscape photography, dramatic lighting, wide angle, natural colors, atmospheric perspective, sharp focus, masterpiece, best quality' },
                    { label: '产品摄影', prompt: '8k, ultra detailed, product photography, clean background, studio lighting, commercial quality, sharp focus, masterpiece, best quality' }
                ]
            },
            {
                title: '🎨 传统绘画', badges: ['传统'], items: [
                    { label: '数字绘画', prompt: 'digital painting, concept art, detailed illustration, rich colors, dynamic composition, professional artwork, masterpiece, best quality' },
                    { label: '动漫风格', prompt: 'anime style, manga, detailed character design, vibrant colors, clean line art, professional illustration, masterpiece, best quality' }
                ]
            }
        ];

        // ============== 智能路由逻辑 ==============
        let groups = [];

        if (isFlux) {
            if (isTxt2Img) {
                // Flux文生图：基础库
                groups = [...fluxTextToImageGroups];
                
                // 根据工作流名称添加特定提示词
                if (filename.includes('redux')) {
                    groups.push(...reduxSpecificGroups);
                }
                if (filename.includes('controlnet')) {
                    groups.push(...controlnetSpecificGroups);
                }
            } else if (isImg2Img) {
                // Flux图生图：编辑优化库
                groups = [...fluxImageToImageGroups];
                
                // 添加特定工作流提示词
                if (filename.includes('redux')) {
                    groups.push(...reduxSpecificGroups);
                }
                if (filename.includes('controlnet')) {
                    groups.push(...controlnetSpecificGroups);
                }
                if (filename.includes('outpaint')) {
                    groups.push(...outpaintSpecificGroups);
                }
            } else {
                // 默认Flux提示词
                groups = fluxTextToImageGroups;
            }
        } else {
            // 传统模型：使用关键词堆叠风格的提示词
            groups = legacyGroups;
        }
        
        return groups;
    }

    /*  已清理的旧代码块 */

    applyPromptShortcut(item) {
        const positiveEl = document.getElementById('positivePrompt');
        const negativeEl = document.getElementById('negativePrompt');
        const overwrite = document.getElementById('promptOverwriteSwitch')?.checked;
        const applyToField = (el, text) => {
            if (!el || !text) return;
            const trimmed = (el.value || '').trim();
            if (overwrite || !trimmed) {
                el.value = text;
            } else {
                const needsComma = trimmed.length > 0 && !trimmed.endsWith(',');
                el.value = el.value + (needsComma ? ', ' : ' ') + text;
            }
            try {
                el.dispatchEvent(new Event('input', { bubbles: true }));
                el.dispatchEvent(new Event('change', { bubbles: true }));
            } catch (_) {}
        };
        applyToField(positiveEl, item?.prompt || item?.label || '');
        if (item?.negative) applyToField(negativeEl, item.negative);
        this.lastPresetLabel = item?.label || '';
        try {
            this.promptSystem.shortcutContext = this.shortcutContext;
            if (typeof this.promptSystem.recordShortcutUsage === 'function') {
                this.promptSystem.recordShortcutUsage(item);
            }
        } catch (_) {}
    }

    applyPromptShortcut_OLD(item) {
        const positiveEl = document.getElementById('positivePrompt');
        const negativeEl = document.getElementById('negativePrompt');
        const overwrite = document.getElementById('promptOverwriteSwitch')?.checked;

        const applyToField = (el, text) => {
            if (!el || !text) return;
            const trimmed = (el.value || '').trim();
            if (overwrite || !trimmed) {
                el.value = text;
            } else {
                const needsComma = trimmed.length > 0 && !trimmed.endsWith(',');
                el.value = el.value + (needsComma ? ', ' : ' ') + text;
            }
            el.dispatchEvent(new Event('input', { bubbles: true }));
            el.dispatchEvent(new Event('change', { bubbles: true }));
        };

        // 正向与负向提示词
        applyToField(positiveEl, item.prompt || '');
        if (item.negative) applyToField(negativeEl, item.negative);

        // 记录使用统计
        try { this.recordShortcutUsage(item); } catch (_) {}

        // 可选参数设置
        if (item.set && typeof item.set === 'object') {
            const setValue = (id, val) => {
                const el = document.getElementById(id);
                if (!el || val === undefined || val === null) return;
                el.value = val;
                el.dispatchEvent(new Event('input', { bubbles: true }));
                el.dispatchEvent(new Event('change', { bubbles: true }));
            };
            setValue('steps', item.set.steps);
            setValue('cfg', item.set.cfg);
            setValue('sampler', item.set.sampler);
        }
    }

    // 将 LoRA 触发词作为一个"临时快捷组"插到最前面（委托给模块）
    prependLoraPromptShortcuts(words, loraName) {
        if (this.promptSystem && typeof this.promptSystem.prependLoraPromptShortcuts === 'function') {
            this.promptSystem.prependLoraPromptShortcuts(words, loraName);
        }
    }

    // 记录快捷提示词使用统计
    recordShortcutUsage(item) {
        const key = `${item.label}|${(item.prompt || '').slice(0,200)}`;
        const store = this.getShortcutUsageStore();
        if (!store[key]) {
            store[key] = { label: item.label, prompt: item.prompt || '', count: 0, lastTs: 0 };
        }
        // 标注当前使用的工作流类型键，供"最近/最常用"筛选
        const ctx = this.shortcutContext || {};
        const typeKey = `${ctx.isFlux ? 'flux' : 'std'}:${ctx.isTxt2Img ? 'txt2img' : (ctx.isImg2Img ? 'img2img' : 'other')}`;
        store[key].typeKey = typeKey;
        store[key].count += 1;
        store[key].lastTs = Date.now();
        // 限制存储大小
        const entries = Object.entries(store);
        if (entries.length > 200) {
            // 删除最旧的多余项
            entries.sort((a,b)=>a[1].lastTs - b[1].lastTs);
            const toDelete = entries.slice(0, entries.length - 200);
            toDelete.forEach(([k])=>delete store[k]);
        }
        this.saveShortcutUsageStore(store);
    }

    getShortcutUsageStore() {
        try {
            return JSON.parse(localStorage.getItem('cw_shortcut_usage') || '{}');
        } catch (_) {
            return {};
        }
    }

    saveShortcutUsageStore(data) {
        try {
            localStorage.setItem('cw_shortcut_usage', JSON.stringify(data));
        } catch (_) {}
    }

        // ============== Flux 图生图（Image-to-Image / Kontext） ==============
        const fluxImgGroups = [
            {
                title: '🎯 精确编辑', badges: ['Flux', 'Redux', 'i2i'], items: [
                    { label: '人物一致性', prompt: 'Keep the person identical with same facial features, expression, and pose. Maintain all physical characteristics and identity.' },
                    { label: '对象颜色替换', prompt: 'Change only the color of the specified object while preserving its shape, texture, lighting, and all other properties.' },
                    { label: '背景完全替换', prompt: 'Replace the entire background with a new environment while keeping the main subject completely unchanged in position and appearance.' },
                    { label: '局部细节修改', prompt: 'Modify only the specified detail while keeping everything else exactly the same. Focus on precise, targeted changes.' },
                    { label: '材质纹理改变', prompt: 'Change the material or texture of the object while maintaining its shape, color, and lighting conditions.' },
                    { label: '光照条件调整', prompt: 'Adjust the lighting conditions while keeping all objects and composition exactly the same.' }
                ]
            },
            {
                title: '🎨 艺术风格迁移', badges: ['Flux', 'style'], items: [
                    { label: '水彩画风', prompt: 'Transform into a watercolor painting style with soft, flowing edges and translucent washes while keeping the composition intact.' },
                    { label: '油画质感', prompt: 'Convert to oil painting style with visible brushstrokes, rich impasto texture, and painterly quality while preserving the subject.' },
                    { label: '铅笔素描', prompt: 'Transform into a detailed pencil sketch with natural graphite shading and fine line work while maintaining composition.' },
                    { label: '数字艺术', prompt: 'Convert to clean digital art style with smooth rendering, vibrant colors, and modern illustration quality.' },
                    { label: '动漫风格', prompt: 'Transform into anime or manga art style with clean lineart, cel-shaded coloring, and stylized features.' },
                    { label: '概念设计', prompt: 'Convert to concept art style with painterly quality, atmospheric effects, and professional illustration appearance.' },
                    { label: '纸艺剪贴', prompt: 'Convert to paper cut collage with layered colored paper and cast shadows.' },
                    { label: '折纸', prompt: 'Convert to origami style with folded paper facets and crisp edges.' },
                    { label: '木刻版画', prompt: 'Convert to woodcut print with bold carved lines and limited palette.' },
                    { label: '铜版蚀刻', prompt: 'Convert to etching with fine hatch lines and print texture.' },
                    { label: '点彩', prompt: 'Convert to pointillism with dot-based color mixing and shimmering light.' },
                    { label: '水墨', prompt: 'Convert to ink wash painting with flowing ink, brush texture and paper bleed.' },
                    { label: '低多边形', prompt: 'Convert to low poly with faceted geometry and flat shading.' },
                    { label: '像素风', prompt: 'Convert to pixel art with limited color palette and crisp pixel edges.' },
                    { label: '赛璐璐', prompt: 'Convert to cel-shaded style with clean outlines and flat color planes.' },
                    { label: '线稿', prompt: 'Convert to line art with clean ink lines and minimal shading.' },
                    { label: '等距视角', prompt: 'Convert to isometric illustration with precise geometry and clean shading.' },
                    { label: '扁平化', prompt: 'Convert to flat design with minimal shading and bold shapes.' },
                    { label: '3D渲染', prompt: 'Convert to 3D render with realistic materials, reflections and GI lighting.' },
                    { label: '黏土动画', prompt: 'Convert to claymation with sculpted clay textures and handmade look.' },
                    { label: '彩绘玻璃', prompt: 'Convert to stained glass with leaded outlines and luminous translucent colors.' },
                    { label: '马赛克', prompt: 'Convert to mosaic with tessellated tiles and grout lines.' },
                    { label: '涂鸦', prompt: 'Convert to graffiti street art with bold spray strokes and drips.' },
                    { label: '波普艺术', prompt: 'Convert to pop art with bold halftones, graphic outlines and vivid colors.' },
                    { label: '蒸汽波', prompt: 'Apply vaporwave retro neon palette, gradients and nostalgic graphics.' },
                    { label: '合成波', prompt: 'Apply synthwave neon grids, sun-set gradient and retro futurism.' },
                    { label: '赛博朋克', prompt: 'Apply cyberpunk neon palette, rain reflections and high contrast; keep composition.' },
                    { label: '蒸汽朋克', prompt: 'Apply steampunk aesthetics with brass, gears and victorian embellishments.' },
                    { label: '柴油朋克', prompt: 'Apply dieselpunk industrial grit with heavy machinery aesthetics.' },
                    { label: '黑色电影', prompt: 'Apply film noir with deep shadows, hard light and dramatic contrast.' },
                    { label: '复古VHS', prompt: 'Apply retro VHS look with scanlines, noise and chroma bleed.' },
                    { label: '胶片风', prompt: 'Apply film emulation with soft halation and natural grain; keep color integrity.' },
                    { label: '富士Velvia', prompt: 'Apply Fuji Velvia color emulation with rich saturation and crisp contrast.' },
                    { label: '柯达Portra', prompt: 'Apply Kodak Portra film look with gentle skin tones and subtle contrast.' },
                    { label: '依尔福HP5', prompt: 'Apply Ilford HP5 black-and-white film with fine grain and deep blacks.' },
                    { label: '巴洛克', prompt: 'Apply baroque painting style with dramatic lighting and ornate detail.' },
                    { label: '洛可可', prompt: 'Apply rococo with elegant ornament, pastel palette and playful grace.' },
                    { label: '文艺复兴', prompt: 'Apply renaissance painting with classical proportions and chiaroscuro.' },
                    { label: '新艺术', prompt: 'Apply art nouveau with flowing lines, floral motifs and decorative borders.' },
                    { label: '包豪斯', prompt: 'Apply bauhaus minimal geometry, primary colors and functional design.' },
                    { label: '野兽派', prompt: 'Apply fauvism with bold colors and expressive brushwork.' },
                    { label: '印象派', prompt: 'Apply impressionism with broken brush strokes and light atmosphere.' },
                    { label: '立体派', prompt: 'Apply cubism with fragmented geometry and multiple viewpoints.' },
                    { label: '超现实主义', prompt: 'Apply surrealism with dreamlike scenes and unexpected juxtapositions.' },
                    { label: '抽象表现', prompt: 'Apply abstract expressionism with gestural strokes and emotive color.' },
                    { label: '现实主义', prompt: 'Apply realism with accurate representation and natural proportions.' },
                    { label: '极简主义', prompt: 'Apply minimalism with clean forms, negative space and restrained palette.' },
                    { label: '故障艺术', prompt: 'Apply glitch aesthetics with databending artifacts and RGB shifts.' },
                    { label: '霓虹辉光', prompt: 'Apply neon glow effects, emissive edges and high contrast.' },
                    { label: '移轴小景', prompt: 'Apply tilt-shift miniature effect with shallow plane of focus.' },
                    { label: '镜头散景', prompt: 'Apply expressive bokeh with bright highlights and depth separation.' }
                ]
            },
            {
                title: '风格迁移 · 艺术流派', badges: ['style transfer', 'art styles'], items: [
                    { label: '中式水墨', prompt: 'Convert to Chinese ink wash with rice paper bleed and calligraphic brushwork.' },
                    { label: '浮世绘', prompt: 'Convert to ukiyo-e woodblock style with flat colors and bold outlines.' },
                    { label: '国潮新中式', prompt: 'Apply modern Chinese aesthetic with contemporary palettes and motifs.' },
                    { label: '古典油画', prompt: 'Apply classical oil painting with layered glazing and realistic lighting.' },
                    { label: '科幻概念', prompt: 'Apply concept art style with cinematic framing and atmospheric depth.' },
                    { label: '赛博插画', prompt: 'Apply sci-fi illustration with holograms and hard-surface design.' },
                    { label: '儿童绘本', prompt: 'Apply children storybook style with soft palette and whimsical look.' },
                    { label: '像素复古游戏', prompt: 'Apply retro game pixel art with 16-color palette and crisp sprites.' },
                    { label: '低保真Lo-Fi', prompt: 'Apply lo-fi aesthetic with soft noise, warm tones and cozy vibe.' },
                    { label: '纸面速写', prompt: 'Apply quick paper sketch with pencil construction lines and smudges.' },
                    { label: '剪影构成', prompt: 'Apply silhouette-driven composition with bold shapes and minimal detail.' },
                    { label: '马蒂斯拼贴', prompt: 'Apply Matisse-like cutout collage with bold color fields.' },
                    { label: '蒙德里安格构', prompt: 'Apply De Stijl grid with primary colors and black lines.' }
                ]
            },
            {
                title: '对象操作', badges: ['object ops'], items: [
                    { label: '移除物品', prompt: 'Remove the unwanted object and reconstruct the background seamlessly.' },
                    { label: '替换物品', prompt: 'Replace the target object with the specified item; match lighting and perspective.' },
                    { label: '添加小物件', prompt: 'Add a small object that blends naturally with the scene; match color and shadows.' }
                ]
            },
            {
                title: '文本编辑', badges: ['text edit'], items: [
                    { label: "替换招牌文字", prompt: "Replace 'OPEN' with 'CLOSED' on the sign while matching font style and perspective." },
                    { label: '修改包装文字', prompt: "Change the label text to 'ORGANIC' while maintaining typography and alignment." }
                ]
            },
            {
                title: '增强与修复', badges: ['enhance'], items: [
                    { label: '清晰锐化', prompt: 'Sharpen details and increase micro-contrast while reducing noise; preserve skin texture.' },
                    { label: '低光提亮', prompt: 'Recover low-light image, boost exposure and balance colors while preventing banding.' },
                    { label: '去雾与净化', prompt: 'Dehaze the scene and restore natural contrast and true colors.' }
                ]
            },
            {
                title: '背景与环境', badges: ['background'], items: [
                    { label: '更换天空', prompt: 'Replace the sky with dramatic clouds while keeping foreground unchanged.' },
                    { label: '季节转换', prompt: 'Change the season to autumn with golden leaves while preserving composition.' },
                    { label: '昼夜切换', prompt: 'Change the scene from day to night while maintaining lighting consistency on subjects.' }
                ]
            },
            {
                title: '人物一致性与美化', badges: ['portrait'], items: [
                    { label: '保持身份特征', prompt: 'Maintain the same identity, facial features and expression; avoid identity drift.' },
                    { label: '肤质自然', prompt: 'Subtle skin smoothing while preserving pores and natural texture.' },
                    { label: '妆容微调', prompt: 'Add subtle makeup enhancements while keeping the original style.' }
                ]
            },
            {
                title: '修复/外扩（Fill）', badges: ['inpaint', 'outpaint'], items: [
                    { label: '遮罩区域修复', prompt: 'Inpaint the masked area seamlessly to match surrounding texture and lighting.' },
                    { label: '画布向外扩展', prompt: 'Outpaint to extend the canvas while keeping style and perspective consistent.' }
                ]
            },
            {
                title: '放大与细节', badges: ['upscale'], items: [
                    { label: '2x-4x放大', prompt: 'Upscale 2x to 4x emphasizing detail preservation and artifact reduction.' },
                    { label: '面部细节增强', prompt: 'Enhance facial details, eyes clarity and hair strands while staying realistic.' }
                ]
            },
            // ====== 扩展：Kontext 分类别编辑快捷 ======
            {
                title: '环境/季节替换', badges: ['background', 'season'], items: [
                    { label: '替换为秋色', prompt: 'Change the scene to autumn with golden leaves while preserving the subject and composition.' },
                    { label: '冬季雪景', prompt: 'Convert environment to winter snowy landscape; maintain lighting consistency on subject.' },
                    { label: '晴转夜景', prompt: 'Turn daytime scene into night while keeping subject illumination plausible.' }
                ]
            },
            {
                title: '风格/艺术迁移', badges: ['style transfer'], items: [
                    { label: '印象派风', prompt: 'Apply impressionist brushwork and luminous color; preserve structure and silhouettes.' },
                    { label: '赛博朋克化', prompt: 'Apply cyberpunk neon palette, rain reflections and high contrast; keep composition.' },
                    { label: '复古胶片感', prompt: 'Apply film emulation with soft halation and natural grain; preserve details.' }
                ]
            },
            {
                title: '风格迁移 · 动漫/影视/游戏', badges: ['style transfer', 'media'], items: [
                    { label: '吉卜力', prompt: 'Apply Studio Ghibli-inspired hand-painted style with soft colors, warm lighting and simplified forms; preserve composition.' },
                    { label: '宫崎骏', prompt: 'Apply Hayao Miyazaki film aesthetic with watercolor-like backgrounds, whimsical mood and clean linework; keep composition.' },
                    { label: '皮克斯', prompt: 'Apply Pixar CG look with stylized PBR materials, soft global illumination and expressive character lighting; preserve forms.' },
                    { label: '迪士尼', prompt: 'Apply Disney animation style with clean outlines, saturated colors and classic character proportions; keep composition.' },
                    { label: '梦工厂', prompt: 'Apply DreamWorks animation style with playful shapes, appealing character design and polished lighting; preserve composition.' },
                    { label: 'GTA 加载页插画', prompt: 'Apply GTA loading-screen illustration style with bold outlines, cel-shaded blocks and high contrast; preserve shapes.' },
                    { label: '塞尔达', prompt: 'Apply cel-shaded painterly game style with soft ink-like edges, airy palette and simple shading; keep composition.' },
                    { label: '原神', prompt: 'Apply anime cel-shaded style with crisp lineart, pastel palette and glossy specular highlights; preserve composition.' },
                    { label: '最终幻想', prompt: 'Apply Final Fantasy concept-art style with high-fantasy motifs, ornate details and cinematic lighting; keep structure.' },
                    { label: '巫师', prompt: 'Apply gritty dark-fantasy game grading with muted palette, high micro-contrast and moody atmosphere; preserve forms.' },
                    { label: '赛博朋克2077', prompt: 'Apply neon-drenched sci-fi game look with chromatic aberration accents and high contrast; keep composition.' },
                    { label: '我的世界', prompt: 'Convert to voxel/cubic Minecraft-like style with blocky geometry and pixel textures; preserve layout.' },
                    { label: '守望先锋', prompt: 'Apply stylized hero-shooter look with clean PBR, saturated colors and graphic readability; keep composition.' },
                    { label: '英雄联盟海报', prompt: 'Apply LoL splash-art style with dynamic posing, dramatic lighting and painterly rendering; preserve subject.' },
                    { label: '魔兽世界', prompt: 'Apply WoW hand-painted fantasy style with high saturation, chunky forms and stylized outlines; keep structure.' },
                    { label: '宝可梦', prompt: 'Apply Pokémon style with rounded forms, clean lineart and cheerful palette; preserve composition.' },
                    { label: '任天堂卡通', prompt: 'Apply Nintendo cartoony look with bright palette, simple shading and bold readability; keep layout.' },
                    { label: '超级马里奥', prompt: 'Apply Super Mario cheerful style with vivid colors, soft shading and playful shapes; keep composition.' },
                    { label: '索尼克', prompt: 'Apply Sonic high-energy style with saturated palette and motion-line accents; keep composition.' },
                    { label: '街头霸王', prompt: 'Apply Street Fighter poster style with dynamic brush strokes, bold highlights and gritty edges; preserve forms.' },
                    { label: '铁拳', prompt: 'Apply TEKKEN character poster style with high contrast, metallic speculars and dramatic rim light; keep composition.' },
                    { label: '火影忍者', prompt: 'Apply Naruto anime style with crisp linework, cel shading and dynamic composition; preserve subject.' },
                    { label: '海贼王', prompt: 'Apply One Piece anime style with bold outlines, saturated colors and exaggerated expressions; keep layout.' },
                    { label: '龙珠', prompt: 'Apply Dragon Ball anime style with energetic linework, cel shading and power-effect glows; keep structure.' },
                    { label: 'EVA', prompt: 'Apply Evangelion anime aesthetic with graphic neon accents, bold typography motifs and moody grading; keep composition.' },
                    { label: 'JOJO', prompt: 'Apply JoJo manga style with dramatic poses, halftone textures and flamboyant color schemes; preserve forms.' },
                    { label: '进击的巨人', prompt: 'Apply AoT anime style with gritty textures, desaturated palette and epic scale; preserve composition.' },
                    { label: '鬼灭之刃', prompt: 'Apply Demon Slayer anime style with clean cel shading, ukiyo-e-like patterns and high contrast; keep layout.' },
                    { label: '咒术回战', prompt: 'Apply Jujutsu Kaisen anime style with crisp linework, modern palettes and dynamic contrasts; preserve composition.' }
                ]
            },
            {
                title: '人像一致性', badges: ['portrait consistency'], items: [
                    { label: '身份保持', prompt: 'Maintain the same identity, facial features, hairstyle and expression through edits.' },
                    { label: '妆容调整', prompt: 'Subtle makeup enhancement while keeping natural skin texture and identity.' },
                    { label: '服饰替换', prompt: 'Replace outfit with the specified style; maintain pose and cloth physics consistency.' }
                ]
            },
            {
                title: '情绪/色调', badges: ['mood'], items: [
                    { label: '明快暖色', prompt: 'Shift to uplifting warm tone while preserving original contrast and materials.' },
                    { label: '冷峻蓝调', prompt: 'Shift to cool blue tone, cinematic contrast; keep highlights natural.' },
                    { label: '低饱和电影感', prompt: 'Reduce saturation and apply cinematic grading while preserving skin tones.' }
                ]
            },
            {
                title: '电商与产品', badges: ['product'], items: [
                    { label: '纯净背景', prompt: 'Replace background with clean white while keeping natural product shadows.' },
                    { label: '品牌统一色', prompt: 'Recolor product to brand palette while retaining material properties.' },
                    { label: '反射控制', prompt: 'Adjust reflections and highlights to look premium without clipping.' }
                ]
            }
        ];

        // ============== 工作流特定提示词库 ==============
        
        // Redux专用提示词
        const reduxSpecificGroups = [
            {
                title: '🔧 Redux精准编辑', badges: ['Redux', 'specific'], items: [
                    { label: '保持身份特征', prompt: 'Maintain the exact same person with identical facial features, bone structure, and expression. No changes to identity.' },
                    { label: '服装款式替换', prompt: 'Change only the clothing style while keeping the person, pose, and background exactly the same.' },
                    { label: '发型颜色调整', prompt: 'Modify only the hair color or style while maintaining all other facial features and identity.' },
                    { label: '物体移除重建', prompt: 'Remove the specified object and reconstruct the background seamlessly with matching textures.' },
                    { label: '季节环境切换', prompt: 'Change the season or weather while keeping all subjects and main composition unchanged.' },
                    { label: '照片品质提升', prompt: 'Enhance image quality, sharpness, and details while preserving all original content exactly.' }
                ]
            }
        ];

        // ControlNet专用提示词
        const controlnetSpecificGroups = [
            {
                title: '🎮 ControlNet引导', badges: ['ControlNet', 'specific'], items: [
                    { label: '姿势控制', prompt: 'Follow the pose reference exactly, detailed human anatomy, natural movement, realistic proportions.' },
                    { label: '边缘引导', prompt: 'Respect the edge map precisely, maintain structural accuracy, detailed line art interpretation.' },
                    { label: '深度控制', prompt: 'Follow depth information accurately, realistic spatial relationships, proper foreground and background.' },
                    { label: '语义分割', prompt: 'Respect the segmentation map, accurate object boundaries, realistic material transitions.' },
                    { label: '法线贴图', prompt: 'Follow surface normal information, accurate lighting response, realistic material properties.' },
                    { label: '线稿上色', prompt: 'Color the line art beautifully, respect line boundaries, harmonious color palette, clean coloring.' }
                ]
            }
        ];

        // 外扩专用提示词
        const outpaintSpecificGroups = [
            {
                title: '🖼️ 画布扩展', badges: ['Outpaint', 'specific'], items: [
                    { label: '左右对称扩展', prompt: 'Extend the canvas symmetrically while maintaining the central composition, consistent style and lighting.' },
                    { label: '上下自然扩展', prompt: 'Expand vertically with natural continuation of the scene, matching perspective and atmospheric depth.' },
                    { label: '环境完整补全', prompt: 'Complete the environment logically, add contextual elements that make sense with the existing scene.' },
                    { label: '风格一致延续', prompt: 'Extend with perfect style consistency, matching colors, textures, and artistic approach throughout.' },
                    { label: '透视准确延伸', prompt: 'Maintain correct perspective when extending, accurate vanishing points and spatial relationships.' },
                    { label: '无缝边界融合', prompt: 'Create seamless transitions at the expansion boundaries, no visible seams or inconsistencies.' }
                ]
            }
        ];

        // ========= 根据工作流类型返回对应分组 =========
        
        // 根据工作流类型和功能返回相应的分组数据
        const filename = (this.selectedWorkflow?.filename || '').toLowerCase();
        let groups = [];
        
        if (isFlux && isTxt2Img) {
            // Flux文生图：使用重构后的现代提示词
            groups = fluxTxtGroups;
        } else if (isFlux && isImg2Img) {
            // Flux图生图：使用简化的风格迁移和编辑提示词
            groups = fluxImgGroups;
            
            // 根据具体工作流类型添加专用提示词
            if (filename.includes('redux')) {
                groups = [...reduxSpecificGroups, ...groups];
            } else if (filename.includes('controlnet')) {
                groups = [...controlnetSpecificGroups, ...groups];
            } else if (filename.includes('outpaint') || filename.includes('fill')) {
                groups = [...outpaintSpecificGroups, ...groups];
            }
        } else {
            // 传统模型：保持现有逻辑
            groups = isImg2Img ? fluxImgGroups : fluxTxtGroups;
        }
        
        return groups;
        
        // ========= 以下为原有的复杂逻辑（暂时保留但不执行）=========
        const addItems = (arr, title, newItems) => {
            const g = arr.find(x => x.title === title);
            if (g) g.items = (g.items || []).concat(newItems);
        };
        // Kontext 核心编辑：曝光/重光/取景/透视等
        addItems(fluxImgGroups, 'Kontext 核心编辑', [
            { label: '整体提亮', prompt: 'Increase exposure by 0.5~1.0 stops while protecting highlights and skin tones; keep natural contrast.' },
            { label: '重打光（三点布光）', prompt: 'Relight the subject with three-point lighting (key, fill, rim) while keeping the background consistent.' },
            { label: '背景虚化', prompt: 'Increase background blur for shallow depth of field while keeping subject sharp; realistic bokeh.' },
            { label: '透视校正', prompt: 'Correct perspective distortion to vertical alignment while preserving composition and proportions.' },
            { label: '智能裁切构图', prompt: 'Crop to a stronger composition (rule of thirds) without cutting off important parts; maintain subject breathing room.' },
            { label: '局部高光压制', prompt: 'Reduce specular highlights on shiny areas while preserving material realism.' }
        ]);
        // 对象操作：复制/缩放/材质/阴影反射
        addItems(fluxImgGroups, '对象操作', [
            { label: '复制对象', prompt: 'Duplicate the selected object and place it symmetrically; match shadows and reflections.' },
            { label: '缩放并重排', prompt: 'Resize the target object to 120% and reposition for balanced layout; maintain perspective.' },
            { label: '材质更换', prompt: 'Change object material to brushed metal while preserving shape and lighting.' },
            { label: '添加真实阴影', prompt: 'Add realistic contact shadow under the object consistent with the scene light direction.' },
            { label: '添加反射高光', prompt: 'Add subtle glossy reflection to emphasize material quality without clipping highlights.' },
            { label: '去除水印/Logo', prompt: 'Remove watermark or logo cleanly and reconstruct underlying texture seamlessly.' }
        ]);
        // 文本编辑：新增字体/翻译/透视/描边
        addItems(fluxImgGroups, '文本编辑', [
            { label: '新增标题', prompt: 'Add a bold title text centered at the top; clean sans-serif font; match perspective.' },
            { label: '翻译并替换', prompt: 'Translate existing text to Chinese and replace while keeping font weight and alignment.' },
            { label: '字体更换', prompt: 'Change the sign text to a serif font with subtle stroke contrast; maintain layout.' },
            { label: '颜色与描边', prompt: 'Change text color to white with 2px dark outline for readability; preserve kerning.' },
            { label: '透视重投影', prompt: 'Reproject the text to match wall perspective; keep sharp edges and anti-aliasing.' }
        ]);
        // 增强与修复：降噪/白平衡/去伪影等
        addItems(fluxImgGroups, '增强与修复', [
            { label: '智能降噪', prompt: 'Denoise while preserving edge detail and skin texture; avoid plastic look.' },
            { label: '白平衡矫正', prompt: 'Correct white balance to neutral gray; keep ambience; avoid green/magenta cast.' },
            { label: '颜色均衡', prompt: 'Balance midtones and shadows; subtle S-curve; maintain highlight roll-off.' },
            { label: '去条带和压缩伪影', prompt: 'Reduce banding and JPEG artifacts in gradients while keeping sharpness.' },
            { label: '动态模糊还原', prompt: 'Reduce motion blur with deconvolution; improve legibility without halos.' }
        ]);
        // 背景与环境：天气/时间/室内外/景深
        addItems(fluxImgGroups, '背景与环境', [
            { label: '室内 → 室外', prompt: 'Change the setting from indoor studio to outdoor urban street while keeping subject lighting plausible.' },
            { label: '大光圈景深', prompt: 'Simulate f/1.8 shallow depth-of-field with smooth bokeh and cat-eye highlights.' },
            { label: '雨天氛围', prompt: 'Add rainy atmosphere with wet surfaces and subtle droplets; adjust reflections accordingly.' },
            { label: '雪天氛围', prompt: 'Add light snowfall and cold grading while keeping subject visibility.' },
            { label: '黄昏色调', prompt: 'Shift to golden hour dusk; warm key light and long soft shadows.' }
        ]);
        // 环境/季节替换：更丰富季节与天气
        addItems(fluxImgGroups, '环境/季节替换', [
            { label: '春季樱花', prompt: 'Convert environment to spring with sakura blossoms; keep subject lighting consistent.' },
            { label: '夏日海岸', prompt: 'Convert to summer seaside environment with turquoise water and bright sun.' },
            { label: '雨夜街景', prompt: 'Turn into rainy night street with neon reflections and wet asphalt.' }
        ]);
        // 人像一致性与美化：细项
        addItems(fluxImgGroups, '人物一致性与美化', [
            { label: '牙齿美白', prompt: 'Whiten teeth naturally without overexposure; keep enamel texture.' },
            { label: '眼睛增强', prompt: 'Enhance iris clarity and catchlights while avoiding oversharpening.' },
            { label: '头发碎发整理', prompt: 'Tame flyaway hairs and smooth edges while keeping natural volume.' },
            { label: '肤色统一', prompt: 'Unify skin tone across face and neck; maintain realistic texture.' },
            { label: '身形微调', prompt: 'Subtle body contour refinement while preserving natural proportions.' }
        ]);
        // 修复/外扩（Fill）：更多方向与纵横比
        addItems(fluxImgGroups, '修复/外扩（Fill）', [
            { label: '去字修复', prompt: 'Remove text from wall and reconstruct underlying brick or plaster texture seamlessly.' },
            { label: '向左外扩', prompt: 'Outpaint canvas to the left by 20% while keeping style and perspective consistent.' },
            { label: '向右外扩', prompt: 'Outpaint canvas to the right by 20% while keeping style and perspective consistent.' },
            { label: '改变纵横比', prompt: 'Extend canvas to 16:9 while maintaining composition balance and background continuity.' }
        ]);
        // 放大与细节：档位与专向增强
        addItems(fluxImgGroups, '放大与细节', [
            { label: '1.5x放大', prompt: 'Upscale 1.5x with detail preservation and anti-aliasing for thin lines.' },
            { label: '4x超分', prompt: 'Upscale 4x with texture-enhanced super-resolution; suppress ringing.' },
            { label: '线稿增强', prompt: 'Enhance line-art clarity and uniform line weight without jaggies.' },
            { label: '纹理微细化', prompt: 'Boost micro-texture and fabric weave visibility while avoiding noise.' }
        ]);

        // ============== 标准工作流（非 Flux） ==============
        const stdTxtGroups = [
            {
                title: '写实摄影', badges: ['standard', 'txt2img'], items: [
                    { label: '自然光写实', prompt: `${baseQuality}, ultra realistic, ${basePhotography}, ${baseSafety}` },
                    { label: '棚拍硬光', prompt: `${baseQuality}, studio hard light, dramatic shadows, ${basePhotography}` },
                    { label: '街头纪实', prompt: `${baseQuality}, street photography, candid moment, motion blur` }
                ]
            },
            {
                title: '插画艺术', badges: ['illustration'], items: [
                    { label: '厚涂插画', prompt: `${baseQuality}, painterly style, textured brushwork, color harmony` },
                    { label: '赛博插画', prompt: `${baseQuality}, sci-fi illustration, holograms, hard-surface design` },
                    { label: '儿童绘本', prompt: `${baseQuality}, children storybook, soft palette, whimsical` }
                ]
            }
        ];
        // 标准文生图：补充主题
        addItems(stdTxtGroups, '写实摄影', [
            { label: '自然风光', prompt: `${baseQuality}, landscape photography, golden hour, wide dynamic range` },
            { label: '美食特写', prompt: `${baseQuality}, food photography, soft diffused light, appetizing steam` },
            { label: '建筑室内', prompt: `${baseQuality}, interior photography, natural window light, clean lines` }
        ]);
        addItems(stdTxtGroups, '插画艺术', [
            { label: '像素风插画', prompt: `${baseQuality}, pixel art, crisp pixel edges, limited palette` },
            { label: '低多边形', prompt: `${baseQuality}, low poly illustration, faceted geometry, flat shading` }
        ]);

        const stdImgGroups = [
            {
                title: '修图增强', badges: ['retouch'], items: [
                    { label: '人像修饰', prompt: 'Subtle skin smoothing, blemish removal, keep natural texture.' },
                    { label: '景色优化', prompt: 'Increase clarity, color grading teal & orange, preserve natural look.' }
                ]
            },
            {
                title: '风格化', badges: ['stylize'], items: [
                    { label: '胶片复古', prompt: 'Film emulation with natural grain and soft halation.' },
                    { label: '赛博朋克', prompt: 'Neon teal/purple palette, high contrast, rainy reflections.' }
                ]
            }
        ];
        // 标准图生图：增强更多细分能力
        addItems(stdImgGroups, '修图增强', [
            { label: '白平衡', prompt: 'Correct white balance to neutral; preserve ambiance.' },
            { label: '降噪保细节', prompt: 'Denoise while keeping hair and fabric details.' },
            { label: '锐化微对比', prompt: 'Micro-contrast sharpening for a natural crisp look.' }
        ]);
        addItems(stdImgGroups, '风格化', [
            { label: '黑白高反差', prompt: 'High-contrast black and white conversion, strong tonal separation.' },
            { label: 'HDR冷暖', prompt: 'Balanced HDR with cool shadows and warm highlights.' }
        ]);

        // ===== 将同类子分组整合为"总分组 + 子分组"结构 =====
        const findByTitle = (arr, title) => arr.find(g => g.title === title);

        if (isFlux && isTxt2Img) {
            // 基础构图与摄影（文生图）
            const baseGroup = {
                title: '基础构图与摄影（文生图）',
                badges: ['Flux', 'txt2img'],
                subgroups: [
                    '构图与风格', '人像与姿态', '风景与自然', '建筑与室内', '产品与电商', '光照与镜头', '图形设计与Logo'
                ].map(t => {
                    const g = findByTitle(fluxTxtGroups, t);
                    return g ? { title: g.title, items: g.items } : null;
                }).filter(Boolean)
            };

            // 艺术与风格（文生图）
            const styleGroup = {
                title: '艺术与风格（文生图）',
                badges: ['Flux', 'txt2img'],
                subgroups: [
                    '艺术插画', '幻想与科幻', '艺术风格 Art Styles'
                ].map(t => {
                    const g = findByTitle(fluxTxtGroups, t);
                    return g ? { title: g.title, items: g.items } : null;
                }).filter(Boolean)
            };

            // 主题与题材（文生图）
            const topicTitles = [
                '自然 Nature','城市 Cities','人物 People','动物 Animals','历史 Historical','科技 Technology','神话 Mythology','太空 Space','载具 Vehicles','文化 Cultural','事件 Events','情绪 Emotions','美食 Food','四季 Seasons','爱好 Hobbies','时尚 Fashion','流行文化 Pop Culture','生活方式 Lifestyle','健康 Health'
            ];
            const topicGroup = {
                title: '主题与题材（文生图）',
                badges: ['Flux', 'txt2img'],
                subgroups: topicTitles.map(t => {
                    const g = findByTitle(fluxTxtGroups, t);
                    return g ? { title: g.title, items: g.items } : null;
                }).filter(Boolean)
            };

            return [baseGroup, styleGroup, topicGroup];
        }

        if (isFlux && isImg2Img) {
            // 合并风格迁移相关子分组
            const stCommon = findByTitle(fluxImgGroups, '风格迁移 · 通用');
            const stArt = findByTitle(fluxImgGroups, '风格迁移 · 艺术流派');
            const stMedia = findByTitle(fluxImgGroups, '风格迁移 · 动漫/影视/游戏');
            const stExtra = findByTitle(fluxImgGroups, '风格/艺术迁移');
            const mergedCommon = {
                title: '风格迁移 · 通用',
                items: [
                    ...(stCommon?.items || []),
                    ...(stExtra?.items || [])
                ]
            };

            // 明确顺序：Kontext核心编辑 → 所有风格迁移 → 其它编辑类
            const core = findByTitle(fluxImgGroups, 'Kontext 核心编辑');
            const othersOrder = [
                '对象操作','文本编辑','增强与修复','背景与环境','环境/季节替换','人像一致性与美化','修复/外扩（Fill）','放大与细节'
            ];
            const others = othersOrder.map(t => {
                const g = findByTitle(fluxImgGroups, t);
                return g ? { title: g.title, items: g.items } : null;
            }).filter(Boolean);

            const ordered = [];
            if (core) ordered.push({ title: core.title, items: core.items });
            if (mergedCommon.items.length > 0) ordered.push(mergedCommon);
            if (stArt) ordered.push({ title: stArt.title, items: stArt.items });
            if (stMedia) ordered.push({ title: stMedia.title, items: stMedia.items });
            ordered.push(...others);

            return [{
                title: 'Kontext 图生图（编辑）',
                badges: ['Flux', 'img2img'],
                subgroups: ordered
            }];
        }

        if (!isFlux && isTxt2Img) {
            const gPhoto = findByTitle(stdTxtGroups, '写实摄影');
            const gIllus = findByTitle(stdTxtGroups, '插画艺术');
            const baseGroup = gPhoto ? { title: '基础构图与摄影（文生图）', badges: ['标准','txt2img'], subgroups: [{ title: gPhoto.title, items: gPhoto.items }] } : null;
            const styleGroup = gIllus ? { title: '艺术与风格（文生图）', badges: ['标准','txt2img'], subgroups: [{ title: gIllus.title, items: gIllus.items }] } : null;
            return [baseGroup, styleGroup].filter(Boolean);
        }

        if (!isFlux && isImg2Img) {
            const gRetouch = findByTitle(stdImgGroups, '修图增强');
            const gStylize = findByTitle(stdImgGroups, '风格化');
            const subs = [];
            if (gRetouch) subs.push({ title: gRetouch.title, items: gRetouch.items });
            if (gStylize) subs.push({ title: gStylize.title, items: gStylize.items });
            return [{ title: '图生图（编辑）', badges: ['标准','img2img'], subgroups: subs }];
        }

        return [];
    }
    recordShortcutUsage(item) {
        const key = `${item.label}|${(item.prompt || '').slice(0,200)}`;
        const store = this.getShortcutUsageStore();
        if (!store[key]) {
            store[key] = { label: item.label, prompt: item.prompt || '', count: 0, lastTs: 0 };
        }
        // 标注当前使用的工作流类型键，供"最近/最常用"筛选
        const ctx = this.shortcutContext || {};
        const typeKey = `${ctx.isFlux ? 'flux' : 'std'}:${ctx.isTxt2Img ? 'txt2img' : (ctx.isImg2Img ? 'img2img' : 'other')}`;
        store[key].typeKey = typeKey;
        store[key].count += 1;
        store[key].lastTs = Date.now();
        // 限制存储大小
        const entries = Object.entries(store);
        if (entries.length > 200) {
            // 删除最旧的多余项
            entries.sort((a,b)=>a[1].lastTs - b[1].lastTs);
            const toDelete = entries.slice(0, entries.length - 200);
            toDelete.forEach(([k])=>delete store[k]);
        }
        this.saveShortcutUsageStore(store);
    }
    getRecentShortcutGroup(max = 8, context) {
        const store = this.getShortcutUsageStore();
        const ctx = context || this.shortcutContext || {};
        const typeKey = `${ctx.isFlux ? 'flux' : 'std'}:${ctx.isTxt2Img ? 'txt2img' : (ctx.isImg2Img ? 'img2img' : 'other')}`;
        const items = Object.values(store)
            .filter(x => x.typeKey === typeKey)
            .sort((a,b)=>b.lastTs - a.lastTs)
            .slice(0, max)
            .map(x => ({ label: x.label, prompt: x.prompt }));
        if (items.length === 0) return null;
        return { title: '最近使用', badges: ['history'], items };
    }
    getFrequentShortcutGroup(max = 8, context) {
        const store = this.getShortcutUsageStore();
        const ctx = context || this.shortcutContext || {};
        const typeKey = `${ctx.isFlux ? 'flux' : 'std'}:${ctx.isTxt2Img ? 'txt2img' : (ctx.isImg2Img ? 'img2img' : 'other')}`;
        const items = Object.values(store)
            .filter(x => x.typeKey === typeKey)
            .sort((a,b)=>b.count - a.count)
            .slice(0, max)
            .map(x => ({ label: `${x.label} (${x.count})`, prompt: x.prompt }));
        if (items.length === 0) return null;
        return { title: '最常用', badges: ['star'], items };
    }
    
    showAllConfigSections() {
        // 显示主要配置区域（保持底部图像输入区隐藏，避免与顶部紧凑输入重复）
        const sections = ['outputSettingsSection', 'modelLoadersSection', 'controlnetConfigsSection'];
        sections.forEach(sectionId => {
            const section = document.getElementById(sectionId);
            if (section) {
                section.style.display = 'block';
            }
        });

        // 强制隐藏底部的图像输入设置区（顶部已有紧凑输入）
        const imgSection = document.getElementById('imageInputSection');
        if (imgSection) imgSection.style.display = 'none';
    }
    
    setDefaultValues(defaults) {
        const elements = {
            width: document.getElementById('width'),
            height: document.getElementById('height'),
            steps: document.getElementById('steps'),
            cfg: document.getElementById('cfg'),
            seed: document.getElementById('seed'),
            sampler: document.getElementById('sampler'),
            scheduler: document.getElementById('scheduler'),
            denoise: document.getElementById('denoise'),
            guidance: document.getElementById('guidance'),
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
            let defaultValue = defaults[key] !== undefined ? defaults[key] : this.getDefaultValue(key);
            // seed 默认显示为空，除非用户手动输入
            if (key === 'seed') defaultValue = '';
            if (element) {
                element.value = defaultValue;
                // 对于 select 元素，确保选中正确的 option
                if (element.tagName === 'SELECT') {
                    const option = element.querySelector(`option[value="${defaultValue}"]`);
                    if (option) {
                        option.selected = true;
                    }
                }
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
            sampler: 'euler', // 默认值，会被JSON文件中的实际值覆盖
            scheduler: 'normal',
            denoise: 1.0,
            guidance: 7.0
        };
        return defaults[key] || '';
    }
    
    generateImageInputs(imageInputs) {
        const container = document.getElementById('imageInputs');
        const compactWrap = document.getElementById('imageInputsCompact');
        const compactSection = document.getElementById('imageInputsCompactSection');
        if (!container && !compactWrap) return;
        
        if (!imageInputs || imageInputs.length === 0) {
            if (container) {
                container.innerHTML = `
                    <div class="no-image-inputs">
                        <i class="fas fa-info-circle"></i>
                        <p>此工作流不需要图像输入</p>
                    </div>
                `;
            }
            if (compactSection) compactSection.style.display = 'none';
            return;
        }
        
        // 对于 fill/outpaint 类型，限制只显示一个主图像输入
        let inputs = imageInputs.slice();
        try {
            const t = (this.selectedWorkflow && this.selectedWorkflow.filename || '').toLowerCase();
            if (t.includes('fill') || t.includes('outpaint')) {
                // 仅保留第一个必需或第一个输入
                const firstRequired = inputs.find(i => i.required) || inputs[0];
                inputs = firstRequired ? [firstRequired] : [];
            }
        } catch(_) {}

        // 按必选/可选排序：必选在前，可选在后
        const sortedInputs = inputs.sort((a, b) => {
            if (a.required && !b.required) return -1;
            if (!a.required && b.required) return 1;
            return 0;
        });
        
        // 检查是否有多个图像输入节点
        const showNodeIds = sortedInputs.length > 1;
        
        // 分组显示必选和可选
        const requiredInputs = sortedInputs.filter(input => input.required);
        const optionalInputs = sortedInputs.filter(input => !input.required);
        
        let html = '';
        
        // 生成必选图片输入
        if (requiredInputs.length > 0) {
            html += `
                <div class="image-input-section">
                    <h5 class="section-title required-section"><i class="fas fa-exclamation-circle"></i> 必需图像输入</h5>
                    ${requiredInputs.map(input => this.generateImageInputHTML(input, showNodeIds)).join('')}
                </div>
            `;
        }
        
        // 生成可选图片输入
        if (optionalInputs.length > 0) {
            html += `
                <div class="image-input-section">
                    <h5 class="section-title optional-section"><i class="fas fa-info-circle"></i> 可选图像输入</h5>
                    ${optionalInputs.map(input => this.generateImageInputHTML(input, showNodeIds)).join('')}
                </div>
            `;
        }
        
        if (container) container.innerHTML = html;

        // 渲染紧凑版（提示词上方）：两个以内并排，更多则自动换行
        if (compactWrap && compactSection) {
            compactSection.style.display = 'block';
            const compactItems = sortedInputs.map(input => this.generateCompactImageInputHTML(input)).join('');
            compactWrap.innerHTML = compactItems;
        }
    }
    
    generateImageInputHTML(input, showNodeIds) {
        return `
            <div class="image-input-group">
                <div class="input-header">
                    <h4>${input.name}</h4>
                    ${showNodeIds ? `<span class="node-id-badge">节点ID: ${input.node_id}</span>` : ''}
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
        `;
    }

    generateCompactImageInputHTML(input) {
        return `
            <div class="ci-item" title="${input.description}">
                <div class="ci-head">
                    <span class="ci-name">${input.name}${input.required ? ' *' : ''}</span>
                    <span class="ci-type">${input.type}</span>
                </div>
                <div class="ci-actions">
                    <button type="button" class="btn btn-xs btn-secondary" onclick="app.showImageSelectModal('${input.node_id}', '${input.type}')">
                        选择
                    </button>
                    <div class="ci-selected" id="selected-${input.node_id}" style="display:none;">
                        <img src="" alt="预览" id="preview-${input.node_id}"/>
                        <button type="button" class="btn btn-xs btn-secondary" onclick="app.clearImageSelection('${input.node_id}')">清除</button>
                    </div>
                </div>
            </div>
        `;
    }

    // 图像选择模态框相关函数
    showImageSelectModal(nodeId, imageType) {
        this.currentImageNodeId = nodeId;
        this.currentImageType = imageType;
        
        const modal = document.getElementById('imageSelectModal');
        if (modal) {
            modal.style.display = 'flex';
            // 每次打开模态框时都重新加载图片列表
            this.loadImages(true); // 传递 true 强制刷新
            this.setupImageModalEvents();
            
            // 启动定期刷新
            this.startImageListAutoRefresh();
        }
    }

    hideImageSelectModal() {
        const modal = document.getElementById('imageSelectModal');
        if (modal) {
            modal.style.display = 'none';
            // 停止定期刷新
            this.stopImageListAutoRefresh();
        }
    }

    // 启动图片列表自动刷新
    startImageListAutoRefresh() {
        // 清除之前的定时器
        this.stopImageListAutoRefresh();
        
        // 每30秒自动刷新一次图片列表
        this.imageListRefreshTimer = setInterval(() => {
            const modal = document.getElementById('imageSelectModal');
            if (modal && modal.style.display === 'flex') {
                console.log('自动刷新图片列表');
                this.loadImages(true);
            } else {
                // 如果模态框已关闭，停止刷新
                this.stopImageListAutoRefresh();
            }
        }, 30000); // 30秒
    }

    // 停止图片列表自动刷新
    stopImageListAutoRefresh() {
        if (this.imageListRefreshTimer) {
            clearInterval(this.imageListRefreshTimer);
            this.imageListRefreshTimer = null;
        }
    }

    async loadImages(forceRefresh = false) {
        try {
            // 显示加载状态
            this.showImageLoadingState(true);
            
            // 添加时间戳参数防止缓存
            const url = forceRefresh ? `/api/images?t=${Date.now()}` : '/api/images';
            const response = await fetch(url);
            const data = await response.json();
            
            if (data.success) {
                this.renderImageTabs(data.images);
            } else {
                console.error('加载图像失败:', data.error);
                this.showImageLoadingError('加载图像失败: ' + data.error);
            }
        } catch (error) {
            console.error('加载图像失败:', error);
            this.showImageLoadingError('网络错误，无法加载图像');
        } finally {
            this.showImageLoadingState(false);
        }
    }

    // 显示图片加载状态
    showImageLoadingState(loading) {
        const uploadedContainer = document.getElementById('uploadedImages');
        const generatedContainer = document.getElementById('generatedImages');
        
        if (loading) {
            const loadingHtml = `
                <div class="images-loading">
                    <div class="spinner"></div>
                    <p>正在加载图片...</p>
                </div>
            `;
            if (uploadedContainer) uploadedContainer.innerHTML = loadingHtml;
            if (generatedContainer) generatedContainer.innerHTML = loadingHtml;
        }
    }

    // 显示图片加载错误
    showImageLoadingError(errorMessage) {
        const uploadedContainer = document.getElementById('uploadedImages');
        const generatedContainer = document.getElementById('generatedImages');
        
        const errorHtml = `
            <div class="images-error">
                <i class="fas fa-exclamation-triangle"></i>
                <p>${errorMessage}</p>
                <button class="btn btn-secondary btn-sm" onclick="app.loadImages(true)">
                    <i class="fas fa-redo"></i>
                    重试
                </button>
            </div>
        `;
        
        if (uploadedContainer) uploadedContainer.innerHTML = errorHtml;
        if (generatedContainer) generatedContainer.innerHTML = errorHtml;
    }

    renderImageTabs(images) {
        // 存储图像数据供搜索使用
        this.allImages = images;
        
        // 渲染已上传的图像
        const uploadedContainer = document.getElementById('uploadedImages');
        if (uploadedContainer) {
            if (images.uploaded && images.uploaded.length > 0) {
                uploadedContainer.innerHTML = this.renderImageGrid(images.uploaded, 'uploaded');
            } else {
                uploadedContainer.innerHTML = `
                    <div class="no-images">
                        <i class="fas fa-image"></i>
                        <p>暂无已上传的图像</p>
                        <p class="no-images-hint">点击"上传新图像"标签页来添加图片</p>
                    </div>
                `;
            }
        }

        // 渲染已生成的图像
        const generatedContainer = document.getElementById('generatedImages');
        if (generatedContainer) {
            if (images.generated && images.generated.length > 0) {
                generatedContainer.innerHTML = this.renderImageGrid(images.generated, 'generated');
            } else {
                generatedContainer.innerHTML = `
                    <div class="no-images">
                        <i class="fas fa-image"></i>
                        <p>暂无已生成的图像</p>
                        <p class="no-images-hint">使用工作流生成图片后会在这里显示</p>
                    </div>
                `;
            }
        }
    }

    renderImageGrid(imageList, source) {
        
        return imageList.map(img => `
            <div class="image-item" onclick="app.selectImage('${img.path}', '${img.name}', '${source}')" 
                 data-name="${img.name.toLowerCase()}" data-size="${img.size}">
                <div class="image-preview">
                    <img src="/outputs/${img.path}" alt="${img.name}" loading="lazy" 
                         onerror="console.error('图片加载失败:', '/outputs/${img.path}')">
                    <div class="image-overlay">
                        <button class="preview-btn" onclick="event.stopPropagation(); app.previewImage('/outputs/${img.path}', '${img.name}')">
                            <i class="fas fa-search-plus"></i>
                        </button>
                        ${(() => {
                            try {
                                const t = (this.selectedWorkflow && this.selectedWorkflow.filename || '').toLowerCase();
                                if (t.includes('fill')) {
                                    return `<button class=\"preview-btn\" onclick=\"event.stopPropagation(); app.openMaskEditor('/outputs/${img.path}', '${img.name}', '${img.path}', '${source}')\"><i class=\"fas fa-pen\"></i></button>`;
                                }
                            } catch(_) {}
                            return '';
                        })()}
                        <button class="select-btn" onclick="event.stopPropagation(); app.selectImage('${img.path}', '${img.name}', '${source}')">
                            <i class="fas fa-check"></i>
                            选择
                        </button>
                        <button class="delete-btn" onclick="event.stopPropagation(); app.deleteImage('${img.name}', '${source}')">
                            <i class="fas fa-trash"></i>
                        </button>
                    </div>
                </div>
                <div class="image-info">
                    <span class="image-name" title="${img.name}">${this.truncateFileName(img.name)}</span>
                    <span class="image-size">${this.formatFileSize(img.size)}</span>
                </div>
            </div>
        `).join('');
    }

    // 画廊参数按钮：容错拉取元数据（新旧命名均支持），失败则提示
    async viewMetadataFallback(filename, imageUrl) {
        try {
            // 直接请求后端统一接口（已支持新旧命名）
            const resp = await fetch(`/api/image-metadata/${filename}`);
            const data = await resp.json();
            if (data.success) {
                // 复用 gallery.html 的展示逻辑：简单弹窗渲染
                const meta = data.metadata || {};
                const pretty = document.createElement('pre');
                pretty.style.maxHeight = '70vh';
                pretty.style.overflow = 'auto';
                pretty.style.whiteSpace = 'pre-wrap';
                pretty.textContent = JSON.stringify(meta, null, 2);
                const wrap = document.createElement('div');
                wrap.className = 'image-preview-modal';
                wrap.innerHTML = `
                    <div class="preview-content" style="max-width: 800px;">
                        <div class="preview-header">
                            <h3>生成参数</h3>
                            <button class="close-preview" onclick="this.closest('.image-preview-modal').remove()">
                                <i class="fas fa-times"></i>
                            </button>
                        </div>
                        <div class="preview-body" style="padding: 12px;">
                            ${imageUrl ? `<img src="${imageUrl}" alt="preview" style="max-width:100%; border-radius:8px; margin-bottom:12px;"/>` : ''}
                        </div>
                    </div>`;
                wrap.querySelector('.preview-body').appendChild(pretty);
                document.body.appendChild(wrap);
            } else {
                alert('获取元数据失败: ' + (data.error || '未知错误'));
            }
        } catch (e) {
            alert('获取元数据失败: ' + e.message);
        }
    }

    // ===== 遮罩编辑器（Fill 工作流） =====
    openMaskEditor(imageUrl, name, path, source='uploaded') {
        try {
            const modal = document.getElementById('maskEditorModal');
            const baseImg = document.getElementById('maskBaseImage');
            const canvas = document.getElementById('maskDrawCanvas');
            this.maskEditor.baseImageUrl = imageUrl;
            this.maskEditor.editing = { imageUrl, name, path, source };
            // 记录当前正在编辑的主图节点及来源，保存时自动选中该图
            // 由于 fill/outpaint 只有一个图像输入，我们取该 inputs 的 node_id
            try {
                const firstInput = (this.selectedWorkflow && this.selectedWorkflow.image_inputs && this.selectedWorkflow.image_inputs[0]) || null;
                if (firstInput) {
                    this.currentImageNodeId = String(firstInput.node_id);
                    this.currentImageType = firstInput.type || 'image';
                    // 覆盖当前选择为这张被编辑的图
                    this.selectImage(path, name, source);
                }
            } catch(_) {}
            baseImg.onload = () => {
                canvas.width = baseImg.clientWidth;
                canvas.height = baseImg.clientHeight;
                canvas.style.width = baseImg.clientWidth + 'px';
                canvas.style.height = baseImg.clientHeight + 'px';
                const ctx = canvas.getContext('2d');
                ctx.clearRect(0,0,canvas.width,canvas.height);
                this.bindMaskDrawing();
            };
            baseImg.src = imageUrl;
            modal.style.display = 'flex';
            document.getElementById('maskBrushSize').value = this.maskEditor.brushSize;
            document.getElementById('maskBrushSizeVal').innerText = this.maskEditor.brushSize;
            document.getElementById('maskFeather').value = this.maskEditor.feather;
            document.getElementById('maskInvert').checked = this.maskEditor.invert;
        } catch(e) { console.error(e); }
    }

    closeMaskEditor() {
        const modal = document.getElementById('maskEditorModal');
        if (modal) modal.style.display = 'none';
    }

    resetMaskEditor() {
        const canvas = document.getElementById('maskDrawCanvas');
        if (!canvas) return;
        const ctx = canvas.getContext('2d');
        ctx.clearRect(0,0,canvas.width,canvas.height);
    }

    setMaskTool(tool){ this.maskEditor.tool = tool; }
    updateMaskBrushSize(v){ this.maskEditor.brushSize = parseInt(v,10)||48; const el=document.getElementById('maskBrushSizeVal'); if(el) el.innerText=this.maskEditor.brushSize; }

    bindMaskDrawing() {
        const canvas = document.getElementById('maskDrawCanvas');
        if (!canvas) return;
        const ctx = canvas.getContext('2d');
        let drawing = false;
        const getPos = (e) => {
            const rect = canvas.getBoundingClientRect();
            const x = (e.touches?e.touches[0].clientX:e.clientX) - rect.left;
            const y = (e.touches?e.touches[0].clientY:e.clientY) - rect.top;
            return {x, y};
        };
        const start = (e) => { drawing = true; this.drawDot(ctx, getPos(e)); e.preventDefault(); };
        const move = (e) => { if (!drawing) return; this.drawDot(ctx, getPos(e)); e.preventDefault(); };
        const end = () => { drawing = false; };
        canvas.onmousedown = start; canvas.onmousemove = move; window.onmouseup = end;
        canvas.ontouchstart = start; canvas.ontouchmove = move; canvas.ontouchend = end;
    }

    drawDot(ctx, {x, y}) {
        const size = this.maskEditor.brushSize;
        ctx.save();
        if (this.maskEditor.tool === 'eraser') {
            ctx.globalCompositeOperation = 'destination-out';
            ctx.beginPath(); ctx.arc(x, y, size/2, 0, Math.PI*2); ctx.fill();
        } else {
            ctx.globalCompositeOperation = 'source-over';
            ctx.fillStyle = 'rgba(255,255,255,1)';
            ctx.beginPath(); ctx.arc(x, y, size/2, 0, Math.PI*2); ctx.fill();
        }
        ctx.restore();
    }

    async saveMask() {
        // 将绘制层导出为 PNG，结合羽化与反向设置生成最终遮罩；上传并替换当前已选图片
        try {
            const canvas = document.getElementById('maskDrawCanvas');
            if (!canvas || canvas.width === 0) { this.closeMaskEditor(); return; }
            // 导出当前 mask，使用"透明背景 + 白色前景"的Alpha通道作为遮罩
            const tmp = document.createElement('canvas'); tmp.width = canvas.width; tmp.height = canvas.height;
            const tctx = tmp.getContext('2d');
            // 保持透明背景，不要填充不透明底色
            tctx.clearRect(0,0,tmp.width,tmp.height);
            // 贴入用户绘制层（白色笔迹，透明背景）
            tctx.globalCompositeOperation = 'source-over';
            tctx.drawImage(canvas, 0, 0);
            // 默认：将"涂抹区域"视为需要重绘（alpha=1）。
            // 若勾选"反向遮罩"，表示涂抹区域保留（不重绘），此时不反转。
            const invertChecked = document.getElementById('maskInvert').checked;
            const shouldInvertAlpha = !invertChecked; // 默认反转，使涂抹区域=需要修改
            if (shouldInvertAlpha) {
                const imgData = tctx.getImageData(0,0,tmp.width,tmp.height);
                const d = imgData.data;
                for (let i=0;i<d.length;i+=4){
                    d[i+3] = 255 - d[i+3]; // 仅反转Alpha
                }
                tctx.putImageData(imgData,0,0);
            }
            // 羽化：使用 CSS blur 不精确，这里暂保持由后端按 mask_blur_radius 再羽化
            // 上传遮罩PNG
            const blob = await new Promise(res => tmp.toBlob(res, 'image/png'));
            const form = new FormData(); form.append('images', blob, 'mask_editor.png');
            const r = await fetch('/api/upload', { method:'POST', body: form });
            const jd = await r.json();
            if (jd.success && jd.files && jd.files[0]) {
                // 自动将当前选中的主图节点与遮罩绑定，无需用户再次选择
                this.selectedMaskPath = jd.files[0].path; // e.g. masks/xxx.png
                // 若还未有主图选择，强制以正在编辑的图片作为主图
                if (!this.selectedImages || Object.keys(this.selectedImages).length === 0) {
                    try {
                        const firstInput = (this.selectedWorkflow && this.selectedWorkflow.image_inputs && this.selectedWorkflow.image_inputs[0]) || null;
                        if (firstInput && this.maskEditor && this.maskEditor.editing) {
                            this.currentImageNodeId = String(firstInput.node_id);
                            this.currentImageType = firstInput.type || 'image';
                            const { path, name, source } = this.maskEditor.editing;
                            this.selectImage(path, name, source || 'uploaded');
                        }
                    } catch(_) {}
                }
                this.showUploadMessage('success', `遮罩已保存，并将随当前图像一起应用`);
            } else {
                alert('遮罩保存失败');
            }
        } catch(e) {
            console.error(e); alert('遮罩保存失败：' + e.message);
        } finally { this.closeMaskEditor(); }
    }

    // 截断文件名以适应显示
    truncateFileName(fileName) {
        if (fileName.length <= 20) return fileName;
        const ext = fileName.split('.').pop();
        const name = fileName.substring(0, fileName.lastIndexOf('.'));
        return name.substring(0, 15) + '...' + ext;
    }

    // 图片预览功能
    previewImage(imageSrc, imageName) {
        // 创建预览模态框
        const previewModal = document.createElement('div');
        previewModal.className = 'image-preview-modal';
        previewModal.innerHTML = `
            <div class="preview-content">
                <div class="preview-header">
                    <h3>${imageName}</h3>
                    <button class="close-preview" onclick="this.closest('.image-preview-modal').remove()">
                        <i class="fas fa-times"></i>
                    </button>
                </div>
                <div class="preview-body">
                    <img src="${imageSrc}" alt="${imageName}">
                </div>
                <div class="preview-actions">
                    <button class="btn btn-secondary" onclick="window.open('${imageSrc}', '_blank')">
                        <i class="fas fa-external-link-alt"></i>
                        新窗口打开
                    </button>
                    <button class="btn btn-primary" onclick="app.downloadImage('${imageSrc}'); this.closest('.image-preview-modal').remove();">
                        <i class="fas fa-download"></i>
                        下载图片
                    </button>
                </div>
            </div>
        `;
        
        // 点击背景关闭预览
        previewModal.onclick = (e) => {
            if (e.target === previewModal) {
                previewModal.remove();
            }
        };
        
        document.body.appendChild(previewModal);
        
        // ESC键关闭预览
        const handleEscape = (e) => {
            if (e.key === 'Escape') {
                previewModal.remove();
                document.removeEventListener('keydown', handleEscape);
            }
        };
        document.addEventListener('keydown', handleEscape);
    }

    // 搜索图片功能
    searchImages(query) {
        const searchInput = document.getElementById('imageSearchInput');
        const clearBtn = document.querySelector('.clear-search');
        
        if (clearBtn) {
            clearBtn.style.display = query ? 'block' : 'none';
        }
        
        if (!query.trim()) {
            this.showAllImages();
            return;
        }
        
        const currentTab = document.querySelector('.tab-btn.active')?.dataset.tab;
        if (!currentTab || !this.allImages) return;
        
        const images = this.allImages[currentTab] || [];
        const filteredImages = images.filter(img => 
            img.name.toLowerCase().includes(query.toLowerCase())
        );
        
        const container = document.getElementById(`${currentTab}Images`);
        if (container) {
            if (filteredImages.length > 0) {
                container.innerHTML = this.renderImageGrid(filteredImages, currentTab);
            } else {
                container.innerHTML = `
                    <div class="no-images">
                        <i class="fas fa-search"></i>
                        <p>未找到匹配的图片</p>
                        <p class="no-images-hint">尝试使用其他关键词搜索</p>
                    </div>
                `;
            }
        }
    }

    // 清除搜索
    clearImageSearch() {
        const searchInput = document.getElementById('imageSearchInput');
        const clearBtn = document.querySelector('.clear-search');
        
        if (searchInput) searchInput.value = '';
        if (clearBtn) clearBtn.style.display = 'none';
        
        this.showAllImages();
    }

    // 显示所有图片
    showAllImages() {
        if (!this.allImages) return;
        
        const currentTab = document.querySelector('.tab-btn.active')?.dataset.tab;
        if (!currentTab) return;
        
        const container = document.getElementById(`${currentTab}Images`);
        const images = this.allImages[currentTab] || [];
        
        if (container) {
            if (images.length > 0) {
                container.innerHTML = this.renderImageGrid(images, currentTab);
            } else {
                const emptyMessage = currentTab === 'uploaded' 
                    ? '暂无已上传的图像' 
                    : '暂无已生成的图像';
                const hintMessage = currentTab === 'uploaded'
                    ? '点击"上传新图像"标签页来添加图片'
                    : '使用工作流生成图片后会在这里显示';
                
                container.innerHTML = `
                    <div class="no-images">
                        <i class="fas fa-image"></i>
                        <p>${emptyMessage}</p>
                        <p class="no-images-hint">${hintMessage}</p>
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

        // 显示选择成功的提示
        this.showUploadMessage('success', `已选择图片: ${imageName}`);

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

    // 标签页切换函数
    switchImageTab(tabName) {
        // 移除所有标签页的活跃状态
        const tabBtns = document.querySelectorAll('.tab-btn');
        const tabContents = document.querySelectorAll('.image-grid, .image-upload');
        
        tabBtns.forEach(btn => btn.classList.remove('active'));
        tabContents.forEach(content => content.classList.remove('active'));
        
        // 激活选中的标签页
        const activeTabBtn = document.querySelector(`[data-tab="${tabName}"]`);
        if (activeTabBtn) {
            activeTabBtn.classList.add('active');
        }
        
        // 显示或隐藏搜索栏
        const searchBar = document.getElementById('imageSearchBar');
        if (searchBar) {
            if (tabName === 'uploaded' || tabName === 'generated') {
                searchBar.style.display = 'block';
            } else {
                searchBar.style.display = 'none';
                // 清除搜索
                this.clearImageSearch();
            }
        }
        
        // 显示对应的内容区域
        let contentId = '';
        switch (tabName) {
            case 'uploaded':
                contentId = 'uploadedImages';
                break;
            case 'generated':
                contentId = 'generatedImages';
                break;
            case 'upload':
                contentId = 'uploadNewImage';
                break;
        }
        
        const activeContent = document.getElementById(contentId);
        if (activeContent) {
            activeContent.classList.add('active');
        }
        
        // 刷新当前标签页的内容
        if (tabName !== 'upload') {
            this.showAllImages();
        }
    }

    async uploadImages(files) {
        // 显示上传进度
        this.showUploadProgress(true);
        
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
                // 显示成功消息
                this.showUploadMessage('success', `成功上传 ${data.files.length} 个文件`);
                // 重新加载图像列表
                await this.loadImages();
                // 切换到已上传标签页
                this.switchImageTab('uploaded');
            } else {
                this.showUploadMessage('error', `上传失败: ${data.error}`);
                console.error('上传失败:', data.error);
            }
        } catch (error) {
            this.showUploadMessage('error', `上传失败: ${error.message}`);
            console.error('上传失败:', error);
        } finally {
            this.showUploadProgress(false);
        }
    }

    // 显示上传进度
    showUploadProgress(show) {
        const uploadArea = document.querySelector('.upload-area');
        if (!uploadArea) return;
        
        if (show) {
            uploadArea.innerHTML = `
                <div class="upload-progress">
                    <div class="spinner"></div>
                    <p>正在上传图片...</p>
                </div>
            `;
        } else {
            uploadArea.innerHTML = `
                <i class="fas fa-cloud-upload-alt"></i>
                <p>拖拽图像到此处或点击选择</p>
                <input type="file" id="imageUploadInput" accept="image/*" multiple>
                <button class="btn btn-primary" onclick="document.getElementById('imageUploadInput').click()">
                    选择图像
                </button>
            `;
            // 重新绑定事件
            const uploadInput = document.getElementById('imageUploadInput');
            if (uploadInput) {
                uploadInput.onchange = (e) => this.handleImageUpload(e);
            }
        }
    }

    // 显示上传消息
    showUploadMessage(type, message) {
        const modal = document.getElementById('imageSelectModal');
        if (!modal) return;
        
        // 移除现有的消息
        const existingMessage = modal.querySelector('.upload-message');
        if (existingMessage) {
            existingMessage.remove();
        }
        
        // 创建新消息
        const messageDiv = document.createElement('div');
        messageDiv.className = `upload-message ${type}`;
        messageDiv.innerHTML = `
            <i class="fas ${type === 'success' ? 'fa-check-circle' : 'fa-exclamation-circle'}"></i>
            <span>${message}</span>
        `;
        
        // 插入到模态框顶部
        const modalBody = modal.querySelector('.modal-body');
        if (modalBody) {
            modalBody.insertBefore(messageDiv, modalBody.firstChild);
        }
        
        // 3秒后自动移除消息
        setTimeout(() => {
            if (messageDiv.parentNode) {
                messageDiv.remove();
            }
        }, 3000);
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
                            <select id="control_net_name_${config.node_id}" name="control_net_name_${config.node_id}" data-default="${params.control_net_name || ''}"></select>
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
                            <select id="text_encoder1_${loader.node_id}" name="text_encoder1_${loader.node_id}" data-default="${params.text_encoder1 || ''}"></select>
                        </div>
                        <div class="form-group">
                            <label for="text_encoder2_${loader.node_id}">文本编码器2</label>
                            <select id="text_encoder2_${loader.node_id}" name="text_encoder2_${loader.node_id}" data-default="${params.text_encoder2 || ''}"></select>
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
                            <select id="model_path_${loader.node_id}" name="model_path_${loader.node_id}" data-default="${params.model_path || ''}"></select>
                            <span class="default-value">默认: <span>${params.model_path || ''}</span></span>
                            <small class="form-hint">Nunchaku Flux 模型文件名或路径，通常为 .safetensors 格式。</small>
                        </div>
                        <div class="form-group">
                            <label for="cache_threshold_${loader.node_id}">缓存阈值</label>
                            <input type="number" id="cache_threshold_${loader.node_id}" name="cache_threshold_${loader.node_id}" 
                                   value="${params.cache_threshold || 0}" min="0" max="100">
                            <span class="default-value">默认: <span>${params.cache_threshold || 0}</span></span>
                            <small class="form-hint">模型缓存阈值，控制内存使用策略，0表示自动管理。</small>
                        </div>
                        <div class="form-group">
                            <label for="attention_${loader.node_id}">注意力机制</label>
                            <select id="attention_${loader.node_id}" name="attention_${loader.node_id}">
                                <option value="nunchaku-fp16" ${params.attention === 'nunchaku-fp16' ? 'selected' : ''}>Nunchaku FP16</option>
                                <option value="nunchaku-fp8" ${params.attention === 'nunchaku-fp8' ? 'selected' : ''}>Nunchaku FP8</option>
                                <option value="flash-attn" ${params.attention === 'flash-attn' ? 'selected' : ''}>Flash Attention</option>
                                <option value="torch-attn" ${params.attention === 'torch-attn' ? 'selected' : ''}>Torch Attention</option>
                            </select>
                            <span class="default-value">默认: <span>${params.attention || 'nunchaku-fp16'}</span></span>
                            <small class="form-hint">注意力计算方式：nunchaku优化内存，flash-attn速度快，torch-attn兼容性好。</small>
                        </div>
                        <div class="form-group">
                            <label for="cpu_offload_${loader.node_id}">CPU卸载</label>
                            <select id="cpu_offload_${loader.node_id}" name="cpu_offload_${loader.node_id}">
                                <option value="auto" ${params.cpu_offload === 'auto' ? 'selected' : ''}>自动</option>
                                <option value="enable" ${params.cpu_offload === 'enable' ? 'selected' : ''}>启用</option>
                                <option value="disable" ${params.cpu_offload === 'disable' ? 'selected' : ''}>禁用</option>
                            </select>
                            <span class="default-value">默认: <span>${params.cpu_offload || 'auto'}</span></span>
                            <small class="form-hint">是否将部分模型运算卸载到CPU，用于节省显存。auto根据显存自动决策。</small>
                        </div>
                        <div class="form-group">
                            <label for="device_id_${loader.node_id}">设备ID</label>
                            <input type="number" id="device_id_${loader.node_id}" name="device_id_${loader.node_id}" 
                                   value="${params.device_id || 0}" min="0" max="10">
                            <span class="default-value">默认: <span>${params.device_id || 0}</span></span>
                            <small class="form-hint">GPU设备编号，通常0为主显卡。多卡环境可指定不同设备。</small>
                        </div>
                        <div class="form-group">
                            <label for="data_type_${loader.node_id}">数据类型</label>
                            <select id="data_type_${loader.node_id}" name="data_type_${loader.node_id}">
                                <option value="bfloat16" ${params.data_type === 'bfloat16' ? 'selected' : ''}>BFloat16</option>
                                <option value="float16" ${params.data_type === 'float16' ? 'selected' : ''}>Float16</option>
                                <option value="float32" ${params.data_type === 'float32' ? 'selected' : ''}>Float32</option>
                                <option value="float8_e4m3fn" ${params.data_type === 'float8_e4m3fn' ? 'selected' : ''}>Float8 E4M3FN</option>
                                <option value="float8_e5m2" ${params.data_type === 'float8_e5m2' ? 'selected' : ''}>Float8 E5M2</option>
                            </select>
                            <span class="default-value">默认: <span>${params.data_type || 'bfloat16'}</span></span>
                            <small class="form-hint">计算精度：float32精度高但慢，float16/bfloat16平衡，float8节省显存。</small>
                        </div>
                        <div class="form-group">
                            <label for="i_2_f_mode_${loader.node_id}">I2F模式</label>
                            <select id="i_2_f_mode_${loader.node_id}" name="i_2_f_mode_${loader.node_id}">
                                <option value="enabled" ${params.i_2_f_mode === 'enabled' ? 'selected' : ''}>启用</option>
                                <option value="disabled" ${params.i_2_f_mode === 'disabled' ? 'selected' : ''}>禁用</option>
                            </select>
                            <span class="default-value">默认: <span>${params.i_2_f_mode || 'enabled'}</span></span>
                            <small class="form-hint">整数到浮点转换优化，启用可提升某些硬件的性能。</small>
                        </div>
                        <div class="form-group">
                            <label for="max_shift_${loader.node_id}">最大偏移 (max_shift)</label>
                            <input type="number" id="max_shift_${loader.node_id}" name="max_shift_${loader.node_id}" data-ml-param="true"
                                   value="${loader?.extra?.max_shift ?? params.max_shift ?? 1.15}" min="0" max="5" step="0.01">
                            <span class="default-value">默认: <span>${loader?.extra?.max_shift ?? params.max_shift ?? 1.15}</span></span>
                            <small class="form-hint">对应 ModelSamplingFlux 的 max_shift，控制 Flux 采样的偏移上限。</small>
                        </div>
                        <div class="form-group">
                            <label for="base_shift_${loader.node_id}">基础偏移 (base_shift)</label>
                            <input type="number" id="base_shift_${loader.node_id}" name="base_shift_${loader.node_id}" data-ml-param="true"
                                   value="${loader?.extra?.base_shift ?? params.base_shift ?? 0.5}" min="0" max="5" step="0.01">
                            <span class="default-value">默认: <span>${loader?.extra?.base_shift ?? params.base_shift ?? 0.5}</span></span>
                            <small class="form-hint">对应 ModelSamplingFlux 的 base_shift，控制 Flux 采样的基础偏移量。</small>
                        </div>
                    `;
                    break;
                    
                case 'NunchakuFluxLoraLoader':
                    paramHtml = `
                        <div class="form-group">
                            <label for="lora_name_${loader.node_id}">LoRA名称</label>
                            <select id="lora_name_${loader.node_id}" name="lora_name_${loader.node_id}" data-default="${params.lora_name || ''}"></select>
                            <span class="default-value">默认: <span>${params.lora_name || ''}</span></span>
                            <small class="form-hint">LoRA权重文件名，用于微调模型风格或特定效果。</small>
                        </div>
                        <div class="form-group">
                            <label for="lora_strength_${loader.node_id}">LoRA强度</label>
                            <div class="input-with-tip">
                                <input type="number" id="lora_strength_${loader.node_id}" name="lora_strength_${loader.node_id}" 
                                       value="${params.lora_strength || 1.0}" min="0.0" max="2.0" step="0.1">
                                <button type="button" class="icon-tip" id="lora_tip_btn_${loader.node_id}" title="暂无Tips">?</button>
                            </div>
                            <span class="default-value">默认: <span>${params.lora_strength || 1.0}</span></span>
                            <small class="form-hint">LoRA效果强度，1.0为完整效果，0.5为一半效果，可超过1.0增强。</small>
                        </div>
                    `;
                    break;
                    
                case 'VAELoader':
                    paramHtml = `
                        <div class="form-group">
                            <label for="vae_name_${loader.node_id}">VAE名称</label>
                            <select id="vae_name_${loader.node_id}" name="vae_name_${loader.node_id}" data-default="${params.vae_name || ''}"></select>
                            <span class="default-value">默认: <span>${params.vae_name || ''}</span></span>
                            <small class="form-hint">变分自编码器文件，负责潜在空间与图像的编解码转换。</small>
                        </div>
                    `;
                    break;
                    
                case 'DualCLIPLoader':
                    paramHtml = `
                        <div class="form-group">
                            <label for="clip_name1_${loader.node_id}">CLIP名称1</label>
                            <select id="clip_name1_${loader.node_id}" name="clip_name1_${loader.node_id}" data-default="${params.clip_name1 || ''}"></select>
                            <span class="default-value">默认: <span>${params.clip_name1 || ''}</span></span>
                            <small class="form-hint">第一个文本编码器模型，通常为 T5 系列（如 t5xxl_fp16.safetensors）。</small>
                        </div>
                        <div class="form-group">
                            <label for="clip_name2_${loader.node_id}">CLIP名称2</label>
                            <select id="clip_name2_${loader.node_id}" name="clip_name2_${loader.node_id}" data-default="${params.clip_name2 || ''}"></select>
                            <span class="default-value">默认: <span>${params.clip_name2 || ''}</span></span>
                            <small class="form-hint">第二个文本编码器模型，通常为 CLIP 系列（如 clip_l.safetensors）。</small>
                        </div>
                        <div class="form-group">
                            <label for="clip_type_${loader.node_id}">CLIP类型</label>
                            <select id="clip_type_${loader.node_id}" name="clip_type_${loader.node_id}">
                                <option value="flux" ${params.type === 'flux' ? 'selected' : ''}>Flux</option>
                                <option value="sdxl" ${params.type === 'sdxl' ? 'selected' : ''}>SDXL</option>
                                <option value="sd3" ${params.type === 'sd3' ? 'selected' : ''}>SD3</option>
                                <option value="sd1" ${params.type === 'sd1' ? 'selected' : ''}>SD1.5</option>
                                <option value="sd2" ${params.type === 'sd2' ? 'selected' : ''}>SD2.x</option>
                                <option value="hunyuan_video" ${params.type === 'hunyuan_video' ? 'selected' : ''}>Hunyuan Video</option>
                                <option value="hidream" ${params.type === 'hidream' ? 'selected' : ''}>HiDream</option>
                            </select>
                            <span class="default-value">默认: <span>${params.type || 'flux'}</span></span>
                            <small class="form-hint">指定模型架构类型，影响文本编码方式和兼容性。</small>
                        </div>
                        <div class="form-group">
                            <label for="clip_device_${loader.node_id}">运行设备</label>
                            <select id="clip_device_${loader.node_id}" name="device_${loader.node_id}">
                                <option value="default" ${params.device === 'default' ? 'selected' : ''}>默认</option>
                                <option value="cpu" ${params.device === 'cpu' ? 'selected' : ''}>CPU</option>
                                <option value="gpu" ${params.device === 'gpu' ? 'selected' : ''}>GPU</option>
                            </select>
                            <span class="default-value">默认: <span>${params.device || 'default'}</span></span>
                            <small class="form-hint">指定CLIP模型的运行设备，default根据系统自动选择。</small>
                        </div>
                    `;
                    break;

                case 'CLIPVisionLoader':
                    paramHtml = `
                        <div class="form-group">
                            <label for="clip_name_${loader.node_id}">CLIP视觉模型</label>
                            <select id="clip_name_${loader.node_id}" name="clip_name_${loader.node_id}" data-default="${params.clip_name || ''}"></select>
                            <span class="default-value">默认: <span>${params.clip_name || ''}</span></span>
                            <small class="form-hint">视觉编码器模型，用于理解和编码图像内容特征。</small>
                        </div>
                        <div class="form-group">
                            <label for="clip_vision_crop_${loader.node_id}">裁剪策略</label>
                            <select id="clip_vision_crop_${loader.node_id}" name="crop_${loader.node_id}" data-ml-param="true">
                                <option value="center" ${loader?.extra?.crop === 'center' || params.crop === 'center' ? 'selected' : ''}>中心裁剪</option>
                                <option value="none" ${loader?.extra?.crop === 'none' || params.crop === 'none' ? 'selected' : ''}>不裁剪</option>
                            </select>
                            <span class="default-value">默认: <span>${loader?.extra?.crop || params.crop || 'center'}</span></span>
                            <small class="form-hint">与后续 CLIPVisionEncode 的 crop 输入一致，决定特征提取的裁剪方式。</small>
                        </div>
                    `;
                    break;

                case 'StyleModelLoader':
                    paramHtml = `
                        <div class="form-group">
                            <label for="style_model_name_${loader.node_id}">风格模型</label>
                            <select id="style_model_name_${loader.node_id}" name="style_model_name_${loader.node_id}" data-default="${params.style_model_name || ''}"></select>
                            <span class="default-value">默认: <span>${params.style_model_name || ''}</span></span>
                            <small class="form-hint">风格迁移模型文件，如 Redux 风格模型（flux1-redux-dev.safetensors）。</small>
                        </div>
                        <div class="form-group">
                            <label for="style_strength_${loader.node_id}">风格强度</label>
                            <input type="number" id="style_strength_${loader.node_id}" name="strength_${loader.node_id}" data-ml-param="true"
                                   value="${params.strength ?? 1.0}" min="0" max="2" step="0.1">
                            <span class="default-value">默认: <span>${params.strength ?? 1.0}</span></span>
                            <small class="form-hint">对应 StyleModelApply 的 strength，控制风格效果的强度。</small>
                        </div>
                        <div class="form-group">
                            <label for="style_strength_type_${loader.node_id}">强度类型</label>
                            <select id="style_strength_type_${loader.node_id}" name="strength_type_${loader.node_id}" data-ml-param="true">
                                <option value="multiply" ${params.strength_type === 'multiply' ? 'selected' : ''}>乘性</option>
                                <option value="add" ${params.strength_type === 'add' ? 'selected' : ''}>加性</option>
                            </select>
                            <span class="default-value">默认: <span>${params.strength_type || 'multiply'}</span></span>
                            <small class="form-hint">对应 StyleModelApply 的 strength_type，乘性叠加vs加性混合。</small>
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
                        ${loader.type === 'NunchakuFluxLoraLoader' ? `
                        <div class="form-hint" id="loraInfo_${loader.node_id}" style="display:none;margin-top:6px;"></div>` : ''}
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
        this.stopResourceAutoRefresh();
        // 清理 URL 中的工作流/来源/提示词参数，避免刷新时又自动进入配置页
        try {
            if (window.history && typeof window.history.replaceState === 'function') {
                const url = new URL(window.location.href);
                url.searchParams.delete('workflow');
                url.searchParams.delete('from');
                url.searchParams.delete('positive');
                url.searchParams.delete('negative');
                const newSearch = url.searchParams.toString();
                const newUrl = url.pathname + (newSearch ? ('?' + newSearch) : '') + (url.hash || '');
                window.history.replaceState(null, '', newUrl);
            }
        } catch (_) {}
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
    
    // 提示词管理功能
    showPromptManager() {
        const modal = document.getElementById('promptManagerModal');
        if (modal) {
            modal.style.display = 'block';
            this.loadPromptManagerData();
        }
    }
    
    hidePromptManager() {
        const modal = document.getElementById('promptManagerModal');
        if (modal) {
            modal.style.display = 'none';
        }
    }
    
    loadPromptManagerData() {
        this.loadPromptStats();
        this.loadFavorites();
        this.setupPromptManagerTabs();
        this.loadTemplateCategories();
    }
    
    setupPromptManagerTabs() {
        const tabs = document.querySelectorAll('.prompt-manager-tabs .tab-btn');
        const panels = document.querySelectorAll('.prompt-panel');
        
        tabs.forEach(tab => {
            tab.addEventListener('click', () => {
                const targetTab = tab.getAttribute('data-tab');
                
                // 更新标签页状态
                tabs.forEach(t => t.classList.remove('active'));
                tab.classList.add('active');
                
                // 更新面板状态
                panels.forEach(panel => {
                    panel.classList.remove('active');
                    if (panel.id === `prompt${targetTab.charAt(0).toUpperCase() + targetTab.slice(1)}Panel`) {
                        panel.classList.add('active');
                    }
                });
            });
        });
    }
    
    loadPromptStats() {
        if (!this.promptSystem) return;
        
        const stats = this.promptSystem.getPromptStats();
        
        // 更新统计数字
        document.getElementById('totalUsage').textContent = stats.totalUsage;
        document.getElementById('uniquePrompts').textContent = stats.uniquePrompts;
        
        // 计算今日使用次数
        const today = new Date().toDateString();
        const todayUsage = stats.recentUsage.filter(item => 
            new Date(item.lastUsed).toDateString() === today
        ).reduce((sum, item) => sum + item.count, 0);
        document.getElementById('todayUsage').textContent = todayUsage;
        
        // 渲染最常用提示词
        this.renderPromptList('mostUsedPrompts', stats.mostUsed);
        
        // 渲染最近使用提示词
        this.renderPromptList('recentPrompts', stats.recentUsage);
    }
    
    renderPromptList(containerId, items) {
        const container = document.getElementById(containerId);
        if (!container) return;
        
        if (items.length === 0) {
            container.innerHTML = `
                <div class="empty-state">
                    <i class="fas fa-inbox"></i>
                    <h4>暂无数据</h4>
                    <p>开始使用提示词后，这里会显示使用统计</p>
                </div>
            `;
            return;
        }
        
        container.innerHTML = items.map(item => `
            <div class="prompt-item" onclick="app.applyPromptFromManager('${this.escapeHtml(item.label)}', '${this.escapeHtml(item.prompt || '')}')">
                <div class="prompt-item-header">
                    <div class="prompt-item-label">${this.escapeHtml(item.label)}</div>
                    <div class="prompt-item-actions">
                        <span class="prompt-item-count">${item.count}</span>
                        <span class="prompt-item-time">${this.formatTime(item.lastUsed)}</span>
                    </div>
                </div>
                <div class="prompt-item-content">${this.escapeHtml(item.prompt || '').substring(0, 100)}${(item.prompt || '').length > 100 ? '...' : ''}</div>
            </div>
        `).join('');
    }
    
    formatTime(timestamp) {
        const date = new Date(timestamp);
        const now = new Date();
        const diff = now - date;
        
        if (diff < 60000) return '刚刚';
        if (diff < 3600000) return `${Math.floor(diff / 60000)}分钟前`;
        if (diff < 86400000) return `${Math.floor(diff / 3600000)}小时前`;
        if (diff < 2592000000) return `${Math.floor(diff / 86400000)}天前`;
        
        return date.toLocaleDateString();
    }
    
    applyPromptFromManager(label, prompt) {
        const positiveEl = document.getElementById('positivePrompt');
        if (positiveEl) {
            positiveEl.value = prompt;
            positiveEl.dispatchEvent(new Event('input', { bubbles: true }));
            positiveEl.dispatchEvent(new Event('change', { bubbles: true }));
        }
        
        this.hidePromptManager();
        
        // 显示成功提示
        this.showToast(`已应用提示词: ${label}`, 'success');
    }
    
    loadFavorites() {
        const favorites = this.getFavorites();
        const container = document.getElementById('favoritesList');
        
        if (!container) return;
        
        if (favorites.length === 0) {
            container.innerHTML = `
                <div class="empty-state">
                    <i class="fas fa-heart"></i>
                    <h4>收藏夹为空</h4>
                    <p>点击"添加当前提示词"来收藏常用的提示词</p>
                </div>
            `;
            return;
        }
        
        container.innerHTML = favorites.map(fav => `
            <div class="prompt-item">
                <div class="prompt-item-header">
                    <div class="prompt-item-label">${this.escapeHtml(fav.label)}</div>
                    <div class="prompt-item-actions">
                        <button class="btn btn-sm btn-secondary" onclick="app.applyPromptFromManager('${this.escapeHtml(fav.label)}', '${this.escapeHtml(fav.prompt)}')">
                            <i class="fas fa-play"></i>
                        </button>
                        <button class="btn btn-sm btn-secondary" onclick="app.removeFromFavorites('${this.escapeHtml(fav.label)}')">
                            <i class="fas fa-trash"></i>
                        </button>
                    </div>
                </div>
                <div class="prompt-item-content">${this.escapeHtml(fav.prompt).substring(0, 100)}${fav.prompt.length > 100 ? '...' : ''}</div>
            </div>
        `).join('');
    }
    
    addToFavorites() {
        const positiveEl = document.getElementById('positivePrompt');
        const negativeEl = document.getElementById('negativePrompt');
        
        if (!positiveEl || !positiveEl.value.trim()) {
            this.showToast('请先输入提示词', 'warning');
            return;
        }
        
        const label = prompt('请输入提示词名称:', '我的提示词');
        if (!label) return;
        
        const favorites = this.getFavorites();
        const newFavorite = {
            label: label,
            prompt: positiveEl.value.trim(),
            negative: negativeEl ? negativeEl.value.trim() : '',
            timestamp: Date.now()
        };
        
        favorites.push(newFavorite);
        this.saveFavorites(favorites);
        
        this.loadFavorites();
        this.showToast(`已添加到收藏夹: ${label}`, 'success');
    }
    
    removeFromFavorites(label) {
        if (!confirm(`确定要删除收藏的提示词"${label}"吗？`)) return;
        
        const favorites = this.getFavorites();
        const filtered = favorites.filter(fav => fav.label !== label);
        this.saveFavorites(filtered);
        
        this.loadFavorites();
        this.showToast(`已删除收藏: ${label}`, 'success');
    }
    
    getFavorites() {
        try {
            return JSON.parse(localStorage.getItem('cw_prompt_favorites') || '[]');
        } catch (_) {
            return [];
        }
    }
    
    saveFavorites(favorites) {
        try {
            localStorage.setItem('cw_prompt_favorites', JSON.stringify(favorites));
        } catch (_) {}
    }
    
    searchFavorites(query) {
        const favorites = this.getFavorites();
        const filtered = favorites.filter(fav => 
            fav.label.toLowerCase().includes(query.toLowerCase()) ||
            fav.prompt.toLowerCase().toLowerCase().includes(query.toLowerCase())
        );
        
        const container = document.getElementById('favoritesList');
        if (!container) return;
        
        if (filtered.length === 0) {
            container.innerHTML = `
                <div class="empty-state">
                    <i class="fas fa-search"></i>
                    <h4>未找到匹配的收藏</h4>
                    <p>尝试使用不同的关键词搜索</p>
                </div>
            `;
            return;
        }
        
        container.innerHTML = filtered.map(fav => `
            <div class="prompt-item">
                <div class="prompt-item-header">
                    <div class="prompt-item-label">${this.escapeHtml(fav.label)}</div>
                    <div class="prompt-item-actions">
                        <button class="btn btn-sm btn-secondary" onclick="app.applyPromptFromManager('${this.escapeHtml(fav.label)}', '${this.escapeHtml(fav.prompt)}')">
                            <i class="fas fa-play"></i>
                        </button>
                        <button class="btn btn-sm btn-secondary" onclick="app.removeFromFavorites('${this.escapeHtml(fav.label)}')">
                            <i class="fas fa-trash"></i>
                        </button>
                    </div>
                </div>
                <div class="prompt-item-content">${this.escapeHtml(fav.prompt).substring(0, 100)}${fav.prompt.length > 100 ? '...' : ''}</div>
            </div>
        `).join('');
    }
    
    searchPrompts(query) {
        if (!query.trim()) {
            document.getElementById('searchResults').innerHTML = `
                <div class="empty-state">
                    <i class="fas fa-search"></i>
                    <h4>搜索提示词</h4>
                    <p>输入关键词来搜索提示词库</p>
                </div>
            `;
            return;
        }
        
        // 从提示词系统中搜索
        const searchType = document.getElementById('promptSearchType').value;
        const results = this.searchPromptLibrary(query, searchType);
        
        const container = document.getElementById('searchResults');
        if (!container) return;
        
        if (results.length === 0) {
            container.innerHTML = `
                <div class="empty-state">
                    <i class="fas fa-search"></i>
                    <h4>未找到匹配的提示词</h4>
                    <p>尝试使用不同的关键词搜索</p>
                </div>
            `;
            return;
        }
        
        container.innerHTML = results.map(item => `
            <div class="prompt-item" onclick="app.applyPromptFromManager('${this.escapeHtml(item.label)}', '${this.escapeHtml(item.prompt)}')">
                <div class="prompt-item-header">
                    <div class="prompt-item-label">${this.escapeHtml(item.label)}</div>
                    <div class="prompt-item-actions">
                        <span class="prompt-item-count">${item.badge || ''}</span>
                    </div>
                </div>
                <div class="prompt-item-content">${this.escapeHtml(item.prompt).substring(0, 100)}${item.prompt.length > 100 ? '...' : ''}</div>
            </div>
        `).join('');
    }
    
    searchPromptLibrary(query, type) {
        if (!this.promptSystem) return [];
        
        const results = [];
        const context = {
            isFlux: this.selectedWorkflow?.filename?.toLowerCase().includes('flux') || false,
            isTxt2Img: !this.selectedWorkflow?.filename?.toLowerCase().includes('kontext') && 
                      !this.selectedWorkflow?.filename?.toLowerCase().includes('fill') && 
                      !this.selectedWorkflow?.filename?.toLowerCase().includes('outpaint'),
            isImg2Img: this.selectedWorkflow?.filename?.toLowerCase().includes('kontext') || 
                      this.selectedWorkflow?.filename?.toLowerCase().includes('fill') || 
                      this.selectedWorkflow?.filename?.toLowerCase().includes('outpaint')
        };
        
        const groups = this.promptSystem.buildPromptShortcutGroups(context);
        
        groups.forEach(group => {
            if (type === 'all' || 
                (type === 'flux' && group.badges?.includes('Flux')) ||
                (type === 'traditional' && group.badges?.includes('传统'))) {
                
                group.items.forEach(item => {
                    if (item.label.toLowerCase().includes(query.toLowerCase()) ||
                        item.prompt.toLowerCase().includes(query.toLowerCase())) {
                        results.push({
                            ...item,
                            badge: group.badges?.[0] || ''
                        });
                    }
                });
            }
        });
        
        return results.slice(0, 20); // 限制结果数量
    }
    
    clearPromptStats() {
        if (!confirm('确定要清除所有提示词使用统计吗？此操作不可恢复。')) return;
        
        if (this.promptSystem && this.promptSystem.clearPromptStats()) {
            this.loadPromptStats();
            this.showToast('已清除使用统计', 'success');
        } else {
            this.showToast('清除失败', 'error');
        }
    }
    
    showToast(message, type = 'info') {
        // 简单的toast提示实现
        const toast = document.createElement('div');
        toast.className = `toast toast-${type}`;
        toast.textContent = message;
        toast.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            background: ${type === 'success' ? '#10b981' : type === 'error' ? '#ef4444' : type === 'warning' ? '#f59e0b' : '#6366f1'};
            color: white;
            padding: 12px 20px;
            border-radius: 8px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
            z-index: 10000;
            font-size: 14px;
            font-weight: 500;
        `;
        
        document.body.appendChild(toast);
        
        setTimeout(() => {
            toast.style.opacity = '0';
            toast.style.transform = 'translateX(100%)';
            toast.style.transition = 'all 0.3s ease';
            
            setTimeout(() => {
                if (toast.parentNode) {
                    toast.parentNode.removeChild(toast);
                }
            }, 300);
        }, 3000);
    }
    
    // 模板库功能
    loadTemplateCategories() {
        if (!this.promptTemplates) return;
        
        const categorySelect = document.getElementById('templateCategory');
        if (!categorySelect) return;
        
        // 分类已经在HTML中预定义了
        categorySelect.value = '';
        this.loadTemplateSubcategories();
    }
    
    loadTemplateSubcategories() {
        if (!this.promptTemplates) return;
        
        const categorySelect = document.getElementById('templateCategory');
        const subcategorySelect = document.getElementById('templateSubcategory');
        
        if (!categorySelect || !subcategorySelect) return;
        
        const category = categorySelect.value;
        if (!category) {
            subcategorySelect.innerHTML = '<option value="">选择子分类...</option>';
            this.loadTemplateTypes();
            return;
        }
        
        const templates = this.promptTemplates.templates[category];
        if (!templates) return;
        
        const subcategories = Object.keys(templates);
        subcategorySelect.innerHTML = '<option value="">选择子分类...</option>' +
            subcategories.map(sub => `<option value="${sub}">${this.promptTemplates.getSubcategoryName(sub)}</option>`).join('');
        
        this.loadTemplateTypes();
    }
    
    loadTemplateTypes() {
        if (!this.promptTemplates) return;
        
        const categorySelect = document.getElementById('templateCategory');
        const subcategorySelect = document.getElementById('templateSubcategory');
        const templateList = document.getElementById('templateList');
        
        if (!categorySelect || !subcategorySelect || !templateList) return;
        
        const category = categorySelect.value;
        const subcategory = subcategorySelect.value;
        
        if (!category || !subcategory) {
            templateList.innerHTML = `
                <div class="empty-state">
                    <i class="fas fa-layer-group"></i>
                    <h4>选择模板分类</h4>
                    <p>请先选择分类和子分类来查看可用的模板</p>
                </div>
            `;
            return;
        }
        
        const templates = this.promptTemplates.templates[category]?.[subcategory];
        if (!templates) return;
        
        const templateItems = Object.entries(templates).map(([type, prompt]) => ({
            type,
            prompt,
            label: this.promptTemplates.getTypeName(type)
        }));
        
        templateList.innerHTML = templateItems.map(item => `
            <div class="prompt-item" onclick="app.applyPromptFromManager('${this.escapeHtml(item.label)}', '${this.escapeHtml(item.prompt)}')">
                <div class="prompt-item-header">
                    <div class="prompt-item-label">${this.escapeHtml(item.label)}</div>
                    <div class="prompt-item-actions">
                        <span class="prompt-item-count">模板</span>
                    </div>
                </div>
                <div class="prompt-item-content">${this.escapeHtml(item.prompt).substring(0, 100)}${item.prompt.length > 100 ? '...' : ''}</div>
            </div>
        `).join('');
    }
    
    applyRandomTemplate() {
        if (!this.promptTemplates) return;
        
        const randomPrompt = this.promptTemplates.generateRandomCombination();
        if (!randomPrompt) {
            this.showToast('无法生成随机模板', 'error');
            return;
        }
        
        const positiveEl = document.getElementById('positivePrompt');
        if (positiveEl) {
            positiveEl.value = randomPrompt;
            positiveEl.dispatchEvent(new Event('input', { bubbles: true }));
            positiveEl.dispatchEvent(new Event('change', { bubbles: true }));
        }
        
        this.hidePromptManager();
        this.showToast('已应用随机模板', 'success');
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
    console.log('DOM加载完成，开始初始化应用...');
    try {
        app = new ComfyWebApp();
        console.log('应用初始化成功');
    } catch (error) {
        console.error('应用初始化失败:', error);
    }
});
