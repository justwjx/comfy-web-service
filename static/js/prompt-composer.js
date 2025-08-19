// 提示词组合器
class PromptComposer {
    constructor() {
        this.compositions = this.loadCompositions();
        this.currentComposition = null;
        this.init();
    }

    init() {
        this.createComposerUI();
        this.setupEventListeners();
    }

    loadCompositions() {
        try {
            return JSON.parse(localStorage.getItem('cw_prompt_compositions') || '[]');
        } catch (_) {
            return [];
        }
    }

    saveCompositions() {
        try {
            localStorage.setItem('cw_prompt_compositions', JSON.stringify(this.compositions));
        } catch (_) {}
    }

    createComposerUI() {
        const composerHTML = `
            <div id="promptComposer" class="prompt-composer" style="display: none;">
                <div class="composer-header">
                    <h3><i class="fas fa-layer-group"></i> 提示词组合器</h3>
                    <button class="btn btn-sm btn-secondary" onclick="promptComposer.close()">
                        <i class="fas fa-times"></i>
                    </button>
                </div>
                <div class="composer-content">
                    <div class="composition-list">
                        <h4>我的组合</h4>
                        <div id="compositionList" class="composition-items"></div>
                        <button class="btn btn-sm btn-primary" onclick="promptComposer.createNew()">
                            <i class="fas fa-plus"></i> 新建组合
                        </button>
                    </div>
                    <div class="composition-editor" id="compositionEditor" style="display: none;">
                        <h4>编辑组合</h4>
                        <div class="form-group">
                            <label>组合名称</label>
                            <input type="text" id="compositionName" placeholder="输入组合名称">
                        </div>
                        <div class="form-group">
                            <label>描述</label>
                            <textarea id="compositionDescription" placeholder="描述这个组合的用途"></textarea>
                        </div>
                        <div class="form-group">
                            <label>提示词组件</label>
                            <div id="compositionParts" class="composition-parts"></div>
                            <button class="btn btn-sm btn-secondary" onclick="promptComposer.addPart()">
                                <i class="fas fa-plus"></i> 添加组件
                            </button>
                        </div>
                        <div class="form-group">
                            <label>预览结果</label>
                            <textarea id="compositionPreview" readonly></textarea>
                        </div>
                        <div class="composer-actions">
                            <button class="btn btn-sm btn-primary" onclick="promptComposer.saveComposition()">
                                <i class="fas fa-save"></i> 保存
                            </button>
                            <button class="btn btn-sm btn-secondary" onclick="promptComposer.cancelEdit()">
                                取消
                            </button>
                            <button class="btn btn-sm btn-success" onclick="promptComposer.applyComposition()">
                                <i class="fas fa-check"></i> 应用
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        `;

        // 添加样式
        const style = document.createElement('style');
        style.textContent = `
            .prompt-composer {
                position: fixed;
                top: 50%;
                left: 50%;
                transform: translate(-50%, -50%);
                width: 90%;
                max-width: 800px;
                max-height: 80vh;
                background: var(--bg-primary);
                border: 1px solid var(--border-color);
                border-radius: 12px;
                box-shadow: 0 10px 30px rgba(0,0,0,0.3);
                z-index: 1000;
                overflow: hidden;
            }

            .composer-header {
                display: flex;
                justify-content: space-between;
                align-items: center;
                padding: 15px 20px;
                background: var(--bg-secondary);
                border-bottom: 1px solid var(--border-color);
            }

            .composer-header h3 {
                margin: 0;
                color: var(--text-primary);
            }

            .composer-content {
                display: flex;
                height: 60vh;
            }

            .composition-list {
                width: 300px;
                padding: 20px;
                border-right: 1px solid var(--border-color);
                overflow-y: auto;
            }

            .composition-items {
                margin-bottom: 15px;
            }

            .composition-item {
                background: var(--bg-secondary);
                border: 1px solid var(--border-color);
                border-radius: 8px;
                padding: 12px;
                margin-bottom: 10px;
                cursor: pointer;
                transition: all 0.3s ease;
            }

            .composition-item:hover {
                background: var(--primary-color);
                color: white;
            }

            .composition-item.active {
                background: var(--primary-color);
                color: white;
            }

            .composition-editor {
                flex: 1;
                padding: 20px;
                overflow-y: auto;
            }

            .composition-parts {
                margin-bottom: 15px;
            }

            .composition-part {
                display: flex;
                gap: 10px;
                margin-bottom: 10px;
                align-items: center;
            }

            .part-input {
                flex: 1;
                padding: 8px;
                border: 1px solid var(--border-color);
                border-radius: 6px;
                background: var(--bg-primary);
                color: var(--text-primary);
            }

            .part-weight {
                width: 60px;
                padding: 8px;
                border: 1px solid var(--border-color);
                border-radius: 6px;
                background: var(--bg-primary);
                color: var(--text-primary);
            }

            .remove-part {
                padding: 8px 12px;
                border: none;
                background: #ff6b6b;
                color: white;
                border-radius: 6px;
                cursor: pointer;
            }

            .composer-actions {
                display: flex;
                gap: 10px;
                margin-top: 20px;
            }

            #compositionPreview {
                min-height: 100px;
                resize: vertical;
            }
        `;
        document.head.appendChild(style);

        // 添加到页面
        document.body.insertAdjacentHTML('beforeend', composerHTML);
    }

    setupEventListeners() {
        // 监听键盘事件
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && this.isOpen()) {
                this.close();
            }
        });
    }

    open() {
        document.getElementById('promptComposer').style.display = 'block';
        this.renderCompositionList();
    }

    close() {
        document.getElementById('promptComposer').style.display = 'none';
        this.currentComposition = null;
    }

    isOpen() {
        return document.getElementById('promptComposer').style.display !== 'none';
    }

    renderCompositionList() {
        const list = document.getElementById('compositionList');
        if (this.compositions.length === 0) {
            list.innerHTML = '<p style="color: var(--text-secondary); text-align: center;">暂无组合</p>';
            return;
        }

        list.innerHTML = this.compositions.map((comp, index) => `
            <div class="composition-item" onclick="promptComposer.editComposition(${index})">
                <div style="font-weight: 600;">${comp.name}</div>
                <div style="font-size: 12px; color: inherit; opacity: 0.8;">${comp.description || '无描述'}</div>
                <div style="font-size: 11px; color: inherit; opacity: 0.6;">${comp.parts.length} 个组件</div>
            </div>
        `).join('');
    }

    createNew() {
        this.currentComposition = {
            name: '',
            description: '',
            parts: [{ text: '', weight: 1 }]
        };
        this.showEditor();
    }

    editComposition(index) {
        this.currentComposition = { ...this.compositions[index] };
        this.showEditor();
    }

    showEditor() {
        document.getElementById('compositionEditor').style.display = 'block';
        this.renderEditor();
    }

    renderEditor() {
        if (!this.currentComposition) return;

        document.getElementById('compositionName').value = this.currentComposition.name;
        document.getElementById('compositionDescription').value = this.currentComposition.description || '';
        this.renderParts();
        this.updatePreview();
    }

    renderParts() {
        const container = document.getElementById('compositionParts');
        container.innerHTML = this.currentComposition.parts.map((part, index) => `
            <div class="composition-part">
                <input type="text" class="part-input" placeholder="输入提示词" 
                       value="${part.text}" onchange="promptComposer.updatePart(${index}, 'text', this.value)">
                <input type="number" class="part-weight" placeholder="权重" min="0.1" max="2" step="0.1"
                       value="${part.weight}" onchange="promptComposer.updatePart(${index}, 'weight', parseFloat(this.value))">
                <button class="remove-part" onclick="promptComposer.removePart(${index})">
                    <i class="fas fa-trash"></i>
                </button>
            </div>
        `).join('');
    }

    updatePart(index, field, value) {
        if (!this.currentComposition || !this.currentComposition.parts[index]) return;
        this.currentComposition.parts[index][field] = value;
        this.updatePreview();
    }

    addPart() {
        if (!this.currentComposition) return;
        this.currentComposition.parts.push({ text: '', weight: 1 });
        this.renderParts();
    }

    removePart(index) {
        if (!this.currentComposition || this.currentComposition.parts.length <= 1) return;
        this.currentComposition.parts.splice(index, 1);
        this.renderParts();
        this.updatePreview();
    }

    updatePreview() {
        if (!this.currentComposition) return;
        
        const preview = this.currentComposition.parts
            .filter(part => part.text.trim())
            .map(part => {
                const text = part.text.trim();
                return part.weight === 1 ? text : `(${text}:${part.weight})`;
            })
            .join(', ');
        
        document.getElementById('compositionPreview').value = preview;
    }

    saveComposition() {
        if (!this.currentComposition) return;
        
        const name = document.getElementById('compositionName').value.trim();
        if (!name) {
            alert('请输入组合名称');
            return;
        }

        this.currentComposition.name = name;
        this.currentComposition.description = document.getElementById('compositionDescription').value.trim();
        this.currentComposition.lastModified = Date.now();

        // 检查是否已存在
        const existingIndex = this.compositions.findIndex(c => c.name === name);
        if (existingIndex >= 0) {
            this.compositions[existingIndex] = { ...this.currentComposition };
        } else {
            this.compositions.unshift(this.currentComposition);
        }

        this.saveCompositions();
        this.renderCompositionList();
        this.cancelEdit();
    }

    cancelEdit() {
        document.getElementById('compositionEditor').style.display = 'none';
        this.currentComposition = null;
    }

    applyComposition() {
        if (!this.currentComposition) return;
        
        const preview = document.getElementById('compositionPreview').value;
        if (!preview.trim()) {
            alert('请先添加一些提示词组件');
            return;
        }

        // 应用到主界面的提示词输入框
        const positiveEl = document.getElementById('positivePrompt');
        if (positiveEl) {
            const overwrite = document.getElementById('promptOverwriteSwitch')?.checked;
            if (overwrite) {
                positiveEl.value = preview;
            } else {
                const current = positiveEl.value.trim();
                positiveEl.value = current ? `${current}, ${preview}` : preview;
            }
            positiveEl.dispatchEvent(new Event('input', { bubbles: true }));
            positiveEl.dispatchEvent(new Event('change', { bubbles: true }));
        }

        this.close();
    }

    deleteComposition(index) {
        if (confirm('确定要删除这个组合吗？')) {
            this.compositions.splice(index, 1);
            this.saveCompositions();
            this.renderCompositionList();
        }
    }
}

// 创建全局实例
window.promptComposer = new PromptComposer();
