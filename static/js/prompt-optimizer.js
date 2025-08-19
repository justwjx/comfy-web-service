// 提示词优化器
class PromptOptimizer {
    constructor() {
        this.init();
    }

    init() {
        this.createOptimizerUI();
        this.setupEventListeners();
    }

    createOptimizerUI() {
        const optimizerHTML = `
            <div id="promptOptimizer" class="prompt-optimizer" style="display: none;">
                <div class="optimizer-header">
                    <h3><i class="fas fa-magic"></i> 提示词优化器</h3>
                    <button class="btn btn-sm btn-secondary" onclick="promptOptimizer.close()">
                        <i class="fas fa-times"></i>
                    </button>
                </div>
                <div class="optimizer-content">
                    <div class="optimizer-section">
                        <h4>当前提示词分析</h4>
                        <div class="prompt-display">
                            <div class="prompt-section">
                                <label>正面提示词</label>
                                <div id="positiveAnalysis" class="prompt-analysis"></div>
                            </div>
                            <div class="prompt-section">
                                <label>负面提示词</label>
                                <div id="negativeAnalysis" class="prompt-analysis"></div>
                            </div>
                        </div>
                    </div>
                    
                    <div class="optimizer-section">
                        <h4>优化建议</h4>
                        <div id="optimizationSuggestions" class="suggestions-list"></div>
                    </div>
                    
                    <div class="optimizer-section">
                        <h4>快速优化</h4>
                        <div class="quick-optimization">
                            <button class="btn btn-primary" onclick="promptOptimizer.optimizeForFlux()">
                                <i class="fas fa-wand-magic-sparkles"></i> Flux优化
                            </button>
                            <button class="btn btn-secondary" onclick="promptOptimizer.optimizeForTraditional()">
                                <i class="fas fa-cog"></i> 传统优化
                            </button>
                            <button class="btn btn-secondary" onclick="promptOptimizer.simplifyPrompt()">
                                <i class="fas fa-compress"></i> 简化提示词
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        `;

        // 添加样式
        const style = document.createElement('style');
        style.textContent = `
            .prompt-optimizer {
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

            .optimizer-header {
                display: flex;
                justify-content: space-between;
                align-items: center;
                padding: 15px 20px;
                background: var(--bg-secondary);
                border-bottom: 1px solid var(--border-color);
            }

            .optimizer-header h3 {
                margin: 0;
                color: var(--text-primary);
            }

            .optimizer-content {
                padding: 20px;
                max-height: 70vh;
                overflow-y: auto;
            }

            .optimizer-section {
                margin-bottom: 30px;
            }

            .optimizer-section h4 {
                margin-bottom: 15px;
                color: var(--text-primary);
            }

            .prompt-display {
                display: flex;
                gap: 20px;
                margin-bottom: 20px;
            }

            .prompt-section {
                flex: 1;
            }

            .prompt-section label {
                display: block;
                font-weight: 600;
                margin-bottom: 10px;
                color: var(--text-primary);
            }

            .prompt-analysis {
                background: var(--bg-secondary);
                border: 1px solid var(--border-color);
                border-radius: 8px;
                padding: 15px;
                min-height: 100px;
                font-family: 'Courier New', monospace;
                font-size: 14px;
                line-height: 1.4;
                color: var(--text-primary);
            }

            .suggestions-list {
                display: flex;
                flex-direction: column;
                gap: 15px;
            }

            .suggestion-item {
                background: var(--bg-secondary);
                border: 1px solid var(--border-color);
                border-radius: 8px;
                padding: 15px;
            }

            .suggestion-text {
                color: var(--text-primary);
                line-height: 1.4;
            }

            .quick-optimization {
                display: flex;
                gap: 10px;
                flex-wrap: wrap;
            }

            .highlight {
                background: #ffeb3b;
                color: #333;
                padding: 2px 4px;
                border-radius: 3px;
            }

            .warning {
                background: #ff9800;
                color: white;
                padding: 2px 4px;
                border-radius: 3px;
            }

            .improvement {
                background: #4caf50;
                color: white;
                padding: 2px 4px;
                border-radius: 3px;
            }
        `;
        document.head.appendChild(style);

        // 添加到页面
        document.body.insertAdjacentHTML('beforeend', optimizerHTML);
    }

    setupEventListeners() {
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && this.isOpen()) {
                this.close();
            }
        });
    }

    open() {
        document.getElementById('promptOptimizer').style.display = 'block';
        this.analyzeCurrentPrompts();
        this.generateSuggestions();
    }

    close() {
        document.getElementById('promptOptimizer').style.display = 'none';
    }

    isOpen() {
        return document.getElementById('promptOptimizer').style.display !== 'none';
    }

    analyzeCurrentPrompts() {
        const positiveEl = document.getElementById('positivePrompt');
        const negativeEl = document.getElementById('negativePrompt');
        
        const positiveText = positiveEl ? positiveEl.value : '';
        const negativeText = negativeEl ? negativeEl.value : '';

        // 分析正面提示词
        const positiveAnalysis = this.analyzePrompt(positiveText, 'positive');
        document.getElementById('positiveAnalysis').innerHTML = positiveAnalysis;

        // 分析负面提示词
        const negativeAnalysis = this.analyzePrompt(negativeText, 'negative');
        document.getElementById('negativeAnalysis').innerHTML = negativeAnalysis;
    }

    analyzePrompt(text, type) {
        if (!text.trim()) {
            return '<em style="color: var(--text-secondary);">暂无内容</em>';
        }

        let analysis = text;
        const modelType = this.detectModelType();

        // Flux模型分析
        if (modelType === 'flux') {
            // 标记不必要的标签
            const unnecessaryTags = ['masterpiece', 'best quality', 'ultra detailed', '8k', '4k'];
            unnecessaryTags.forEach(tag => {
                const regex = new RegExp(`\\b${tag}\\b`, 'gi');
                if (text.match(regex)) {
                    analysis = analysis.replace(regex, `<span class="warning" title="Flux模型不需要此标签">${tag}</span>`);
                }
            });
        } else {
            // 传统模型分析
            const qualityTags = ['masterpiece', 'best quality', 'ultra detailed'];
            qualityTags.forEach(tag => {
                const regex = new RegExp(`\\b${tag}\\b`, 'gi');
                if (text.match(regex)) {
                    analysis = analysis.replace(regex, `<span class="improvement" title="质量标签">${tag}</span>`);
                }
            });
        }

        // 添加统计信息
        const wordCount = text.split(/\s+/).length;
        const charCount = text.length;
        
        analysis += `<div style="margin-top: 10px; padding-top: 10px; border-top: 1px solid var(--border-color); font-size: 12px; color: var(--text-secondary);">
            字数: ${wordCount} | 字符: ${charCount}
        </div>`;

        return analysis;
    }

    detectModelType() {
        const workflowName = window.app?.selectedWorkflow?.filename?.toLowerCase() || '';
        if (workflowName.includes('flux')) {
            return 'flux';
        }
        return 'traditional';
    }

    generateSuggestions() {
        const positiveEl = document.getElementById('positivePrompt');
        const negativeEl = document.getElementById('negativePrompt');
        
        const positiveText = positiveEl ? positiveEl.value : '';
        const negativeText = negativeEl ? negativeEl.value : '';

        const suggestions = [];
        const modelType = this.detectModelType();

        // Flux模型建议
        if (modelType === 'flux') {
            if (positiveText.match(/\b(masterpiece|best quality|ultra detailed|8k|4k)\b/gi)) {
                suggestions.push('建议移除"masterpiece"、"best quality"等传统标签，Flux模型会自动处理质量');
            }
            if (!positiveText.match(/\b(natural|soft|dramatic)\s+lighting\b/gi)) {
                suggestions.push('考虑添加具体的照明描述，如"natural lighting"或"soft lighting"');
            }
        } else {
            // 传统模型建议
            if (!positiveText.match(/\b(masterpiece|best quality)\b/gi)) {
                suggestions.push('建议添加"masterpiece, best quality"等质量标签');
            }
            if (!positiveText.match(/\b(ultra detailed|sharp focus)\b/gi)) {
                suggestions.push('考虑添加"ultra detailed, sharp focus"等细节标签');
            }
        }

        // 通用建议
        if (!negativeText.trim()) {
            suggestions.push('建议添加负面提示词以避免常见问题，如"blurry, low quality, bad anatomy"');
        }

        if (positiveText.match(/\b(very|really|extremely)\b/gi)) {
            suggestions.push('避免使用"very"等强调词，直接描述特征更有效');
        }

        this.renderSuggestions(suggestions);
    }

    renderSuggestions(suggestions) {
        const container = document.getElementById('optimizationSuggestions');
        
        if (suggestions.length === 0) {
            container.innerHTML = '<p style="color: var(--text-secondary); text-align: center;">暂无建议</p>';
            return;
        }

        container.innerHTML = suggestions.map(suggestion => `
            <div class="suggestion-item">
                <div class="suggestion-text">${suggestion}</div>
            </div>
        `).join('');
    }

    optimizeForFlux() {
        const positiveEl = document.getElementById('positivePrompt');
        if (!positiveEl) return;

        let optimized = positiveEl.value;
        
        // 移除传统标签
        optimized = optimized.replace(/\b(masterpiece|best quality|ultra detailed|8k|4k)\b/gi, '');
        
        // 添加自然语言描述
        if (!optimized.match(/\b(natural|soft|dramatic)\s+lighting\b/gi)) {
            optimized += ', natural lighting';
        }

        // 清理格式
        optimized = optimized.replace(/\s*,\s*/g, ', ').replace(/^,\s*/, '').replace(/\s*,$/, '');
        
        positiveEl.value = optimized;
        positiveEl.dispatchEvent(new Event('input', { bubbles: true }));
        positiveEl.dispatchEvent(new Event('change', { bubbles: true }));

        this.showNotification('已优化为Flux风格');
        this.close();
    }

    optimizeForTraditional() {
        const positiveEl = document.getElementById('positivePrompt');
        if (!positiveEl) return;

        let optimized = positiveEl.value;
        
        // 添加质量标签
        if (!optimized.match(/\b(masterpiece|best quality)\b/gi)) {
            optimized = 'masterpiece, best quality, ' + optimized;
        }
        
        if (!optimized.match(/\b(ultra detailed|sharp focus)\b/gi)) {
            optimized += ', ultra detailed, sharp focus';
        }

        // 清理格式
        optimized = optimized.replace(/\s*,\s*/g, ', ').replace(/^,\s*/, '').replace(/\s*,$/, '');
        
        positiveEl.value = optimized;
        positiveEl.dispatchEvent(new Event('input', { bubbles: true }));
        positiveEl.dispatchEvent(new Event('change', { bubbles: true }));

        this.showNotification('已优化为传统风格');
        this.close();
    }

    simplifyPrompt() {
        const positiveEl = document.getElementById('positivePrompt');
        if (!positiveEl) return;

        let simplified = positiveEl.value;
        
        // 移除重复词汇
        const words = simplified.split(/\s*,\s*/);
        const uniqueWords = [...new Set(words)];
        simplified = uniqueWords.join(', ');
        
        // 移除不必要的强调词
        simplified = simplified.replace(/\b(very|really|extremely)\b/gi, '');
        
        // 清理格式
        simplified = simplified.replace(/\s*,\s*/g, ', ').replace(/^,\s*/, '').replace(/\s*,$/, '');
        
        positiveEl.value = simplified;
        positiveEl.dispatchEvent(new Event('input', { bubbles: true }));
        positiveEl.dispatchEvent(new Event('change', { bubbles: true }));

        this.showNotification('已简化提示词');
        this.close();
    }

    showNotification(message) {
        const notification = document.createElement('div');
        notification.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            background: var(--primary-color);
            color: white;
            padding: 12px 20px;
            border-radius: 8px;
            z-index: 1001;
            animation: slideIn 0.3s ease;
        `;
        notification.textContent = message;
        document.body.appendChild(notification);
        
        setTimeout(() => {
            notification.remove();
        }, 3000);
    }
}

// 创建全局实例
window.promptOptimizer = new PromptOptimizer();
