// 优化的提示词快捷系统模块
class PromptShortcutSystem {
    constructor() {
        this.lastPresetLabel = '';
        this.shortcutContext = {};
        this.favorites = this.loadFavorites();
    }

    // 加载收藏的提示词
    loadFavorites() {
        try {
            return JSON.parse(localStorage.getItem('cw_prompt_favorites') || '[]');
        } catch (_) {
            return [];
        }
    }

    // 保存收藏的提示词
    saveFavorites() {
        try {
            localStorage.setItem('cw_prompt_favorites', JSON.stringify(this.favorites));
        } catch (_) {}
    }

    // 添加收藏
    addToFavorites(item) {
        const key = `${item.label}|${(item.prompt || '').slice(0,200)}`;
        if (!this.favorites.find(f => f.key === key)) {
            this.favorites.unshift({
                key,
                label: item.label,
                prompt: item.prompt || '',
                negative: item.negative || '',
                category: item.category || '收藏',
                timestamp: Date.now()
            });
            this.saveFavorites();
        }
    }

    // 移除收藏
    removeFromFavorites(key) {
        this.favorites = this.favorites.filter(f => f.key !== key);
        this.saveFavorites();
    }

    // 全新提示词系统 - 清晰分类，符合Flux自然语言原则
    buildPromptShortcutGroups({ isFlux, isTxt2Img, isImg2Img }) {
        const filename = (this.selectedWorkflow?.filename || '').toLowerCase();

        // ============== 收藏提示词 ==============
        const favoritesGroup = this.favorites.length > 0 ? [{
            title: '⭐ 我的收藏', badges: ['收藏'], items: this.favorites.map(f => ({
                label: f.label,
                prompt: f.prompt,
                negative: f.negative,
                category: f.category
            }))
        }] : [];

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
                    { label: '建筑摄影', prompt: 'An architectural photograph emphasizing geometric forms, interesting perspectives, natural and artificial lighting' },
                    { label: '夜景摄影', prompt: 'A night photography with long exposure, city lights, star trails, dramatic low-light atmosphere' },
                    { label: '黑白摄影', prompt: 'A black and white photograph with high contrast, dramatic shadows, timeless monochromatic aesthetic' }
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
                    { label: '漫画风格', prompt: 'A comic book style illustration with bold outlines, dynamic poses, expressive features, vibrant colors' },
                    { label: '像素艺术', prompt: 'A pixel art illustration with retro gaming aesthetic, limited color palette, nostalgic 8-bit or 16-bit style' },
                    { label: '极简主义', prompt: 'A minimalist artwork with clean geometric shapes, limited color palette, sophisticated simplicity' },
                    { label: '抽象艺术', prompt: 'An abstract artwork with non-representational forms, emotional color expression, contemporary artistic style' }
                ]
            },
            {
                title: '💡 创意场景', badges: ['Flux'], items: [
                    { label: '科幻场景', prompt: 'A futuristic science fiction scene with advanced technology, sleek designs, atmospheric lighting, imaginative concepts' },
                    { label: '奇幻世界', prompt: 'A fantasy world scene with magical elements, ethereal atmosphere, rich storytelling details, mystical quality' },
                    { label: '历史重现', prompt: 'A historical scene accurately depicting period details, authentic costumes, appropriate architecture, documentary realism' },
                    { label: '日常生活', prompt: 'A slice of life scene capturing ordinary moments with warmth, authenticity, relatable human experiences' },
                    { label: '抽象概念', prompt: 'An abstract visual representation of ideas or emotions through color, form, and composition, non-literal interpretation' },
                    { label: '超现实主义', prompt: 'A surreal scene blending reality with impossible elements, dreamlike quality, thought-provoking imagery' },
                    { label: '赛博朋克', prompt: 'A cyberpunk scene with neon lights, futuristic technology, urban decay, high-tech low-life aesthetic' },
                    { label: '蒸汽朋克', prompt: 'A steampunk scene with Victorian-era aesthetics, brass and copper machinery, retro-futuristic technology' },
                    { label: '后启示录', prompt: 'A post-apocalyptic scene showing abandoned civilization, overgrown nature, atmospheric decay and survival themes' },
                    { label: '太空探索', prompt: 'A space exploration scene with cosmic vistas, alien worlds, advanced spacecraft, interstellar adventure' }
                ]
            },
            {
                title: '🌟 质量优化', badges: ['Flux'], items: [
                    { label: '专业品质', prompt: 'Professional quality with meticulous attention to detail, perfect technical execution, commercial grade standards' },
                    { label: '艺术精品', prompt: 'Masterpiece quality with exceptional artistic merit, museum-worthy craftsmanship, timeless aesthetic appeal' },
                    { label: '高分辨率', prompt: 'Ultra high resolution with crystal clear details, sharp focus throughout, suitable for large format printing' },
                    { label: '电影质感', prompt: 'Cinematic quality with dramatic lighting, professional color grading, film-like depth and atmosphere' },
                    { label: '纪实风格', prompt: 'Documentary style with authentic, unposed moments, natural lighting, journalistic integrity' },
                    { label: '商业级', prompt: 'Commercial grade with market-ready quality, professional presentation, industry standard excellence' },
                    { label: '艺术级', prompt: 'Fine art quality with gallery-worthy presentation, sophisticated composition, artistic mastery' }
                ]
            },
            {
                title: '🎭 人物角色', badges: ['Flux'], items: [
                    { label: '现代女性', prompt: 'A modern woman with natural beauty, contemporary fashion, confident expression, professional appearance' },
                    { label: '现代男性', prompt: 'A modern man with natural features, contemporary style, confident demeanor, professional look' },
                    { label: '儿童', prompt: 'A child with innocent expression, natural curiosity, age-appropriate clothing, wholesome appearance' },
                    { label: '老年人', prompt: 'An elderly person with wisdom in their eyes, natural aging features, dignified appearance, life experience' },
                    { label: '职业人士', prompt: 'A professional person in business attire, confident posture, workplace environment, career-focused appearance' },
                    { label: '艺术家', prompt: 'A creative person with artistic flair, expressive features, studio environment, creative energy' },
                    { label: '运动员', prompt: 'An athletic person with fit physique, dynamic pose, sports environment, physical vitality' },
                    { label: '学生', prompt: 'A young student with academic appearance, learning environment, intellectual curiosity, youthful energy' }
                ]
            },
            {
                title: '🏠 室内场景', badges: ['Flux'], items: [
                    { label: '现代客厅', prompt: 'A modern living room with contemporary furniture, clean lines, natural lighting, comfortable atmosphere' },
                    { label: '厨房场景', prompt: 'A well-equipped kitchen with modern appliances, warm lighting, home cooking atmosphere' },
                    { label: '卧室', prompt: 'A cozy bedroom with comfortable bedding, soft lighting, peaceful atmosphere, personal space' },
                    { label: '书房', prompt: 'A study room with bookshelves, desk setup, intellectual atmosphere, focused environment' },
                    { label: '浴室', prompt: 'A clean bathroom with modern fixtures, good lighting, hygienic appearance' },
                    { label: '餐厅', prompt: 'A dining room with elegant table setting, ambient lighting, social gathering atmosphere' },
                    { label: '办公室', prompt: 'A professional office with desk setup, business environment, productive atmosphere' },
                    { label: '工作室', prompt: 'An artist studio with creative tools, natural lighting, artistic workspace' }
                ]
            },
            {
                title: '🌍 户外场景', badges: ['Flux'], items: [
                    { label: '城市街道', prompt: 'A busy city street with urban architecture, people walking, dynamic city life' },
                    { label: '公园绿地', prompt: 'A peaceful park with green spaces, walking paths, natural beauty, outdoor recreation' },
                    { label: '海滩', prompt: 'A beautiful beach with golden sand, ocean waves, coastal atmosphere, seaside tranquility' },
                    { label: '山区', prompt: 'A mountain landscape with rugged peaks, hiking trails, natural wilderness, outdoor adventure' },
                    { label: '森林', prompt: 'A dense forest with tall trees, natural paths, wildlife habitat, woodland atmosphere' },
                    { label: '乡村', prompt: 'A rural countryside with farmland, traditional buildings, peaceful village life' },
                    { label: '沙漠', prompt: 'A vast desert with sand dunes, dramatic lighting, arid landscape, desert beauty' },
                    { label: '雪景', prompt: 'A winter scene with snow-covered landscape, crisp air, seasonal beauty, cold weather atmosphere' }
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
                    { label: '添加元素', prompt: 'Add new objects or elements to the scene while preserving the existing composition and main subjects unchanged' },
                    { label: '移除元素', prompt: 'Remove unwanted objects or elements from the scene while maintaining the overall composition and remaining subjects' },
                    { label: '颜色调整', prompt: 'Adjust the color scheme and lighting while keeping the same composition, subjects, and overall structure' },
                    { label: '季节转换', prompt: 'Change the season while maintaining the same location, composition, and main subjects' },
                    { label: '时间转换', prompt: 'Change the time of day while keeping the same location, composition, and subjects' }
                ]
            },
            {
                title: '🎨 风格转换', badges: ['Flux'], items: [
                    { label: '艺术风格', prompt: 'Transform into an artistic painting style while preserving the subject\'s identity and basic composition structure' },
                    { label: '水彩效果', prompt: 'Convert to watercolor painting style with soft, flowing edges and translucent washes while keeping the composition intact' },
                    { label: '油画效果', prompt: 'Transform into oil painting style with rich textures and classical techniques while maintaining subject recognition' },
                    { label: '素描效果', prompt: 'Convert to detailed pencil sketch with fine line work and shading while preserving all recognizable features' },
                    { label: '漫画风格', prompt: 'Transform into comic book illustration style with bold outlines and stylized features while keeping character identity' },
                    { label: '黑白处理', prompt: 'Convert to black and white with enhanced contrast and dramatic lighting while maintaining all compositional elements' },
                    { label: '复古风格', prompt: 'Apply vintage aesthetic with retro color grading and period-appropriate styling while preserving subject identity' },
                    { label: '未来风格', prompt: 'Transform into futuristic aesthetic with high-tech elements and modern styling while maintaining core composition' },
                    { label: '梦幻风格', prompt: 'Apply dreamy, ethereal aesthetic with soft lighting and magical atmosphere while preserving subject features' },
                    { label: '写实风格', prompt: 'Enhance realistic appearance with detailed textures and natural lighting while maintaining authentic representation' }
                ]
            },
            {
                title: '⚡ 质量提升', badges: ['Flux'], items: [
                    { label: '细节增强', prompt: 'Enhance all details and textures while maintaining the exact same composition, colors, and subject matter' },
                    { label: '清晰度提升', prompt: 'Improve image sharpness and clarity throughout while preserving all original elements and characteristics' },
                    { label: '色彩增强', prompt: 'Enhance color saturation and vibrancy while keeping the same lighting conditions and overall mood' },
                    { label: '光线优化', prompt: 'Improve lighting quality and balance while maintaining the same scene composition and subject positioning' },
                    { label: '去噪处理', prompt: 'Remove noise and artifacts while preserving all fine details and maintaining image authenticity' },
                    { label: '对比度优化', prompt: 'Enhance contrast and dynamic range while maintaining natural appearance and avoiding over-processing' },
                    { label: '分辨率提升', prompt: 'Increase image resolution and detail level while preserving all original content and proportions' },
                    { label: '质感增强', prompt: 'Enhance material textures and surface details while maintaining realistic appearance' }
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
                    { label: '边缘优化', prompt: 'Edge refinement and sharpening while maintaining natural appearance and avoiding over-processing artifacts' },
                    { label: '纹理增强', prompt: 'Surface texture enhancement with realistic material properties and natural detail preservation' },
                    { label: '结构重建', prompt: 'Structural reconstruction with improved geometric accuracy and natural form preservation' }
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
                    { label: '语义分割', prompt: 'Semantic segmentation guided creation with accurate object boundaries and realistic textures' },
                    { label: '线条控制', prompt: 'Line-guided generation following precise structural lines while maintaining natural appearance' },
                    { label: '形状控制', prompt: 'Shape-guided generation with accurate geometric forms and realistic detail integration' }
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
                    { label: '背景延续', prompt: 'Continue the background patterns and textures naturally while preserving the original scene\'s mood and style' },
                    { label: '空间扩展', prompt: 'Extend the spatial environment while maintaining architectural consistency and realistic proportions' },
                    { label: '细节延续', prompt: 'Continue fine details and textures seamlessly while preserving the original image\'s quality and style' }
                ]
            }
        ];

        // ============== Kontext 专用提示词库 ==============
        const kontextSpecificGroups = [
            {
                title: '🧠 Kontext智能', badges: ['Kontext'], items: [
                    { label: '智能编辑', prompt: 'Intelligent editing that understands context and maintains consistency across all elements' },
                    { label: '上下文感知', prompt: 'Context-aware generation that considers the relationship between all elements in the scene' },
                    { label: '语义理解', prompt: 'Semantic understanding that accurately interprets and maintains the meaning of visual elements' },
                    { label: '逻辑一致性', prompt: 'Logical consistency that maintains realistic relationships and spatial coherence' },
                    { label: '智能补全', prompt: 'Intelligent completion that fills missing areas with contextually appropriate content' },
                    { label: '关系保持', prompt: 'Relationship preservation that maintains the connections and interactions between elements' }
                ]
            }
        ];

        // ============== 传统模型提示词库 ==============
        const legacyGroups = [
            {
                title: '📷 经典摄影', badges: ['传统'], items: [
                    { label: '人像摄影', prompt: '8k, ultra detailed, high dynamic range, portrait, natural skin texture, softbox lighting, catchlight in eyes, sharp focus, masterpiece, best quality' },
                    { label: '风景摄影', prompt: '8k, ultra detailed, landscape photography, dramatic lighting, wide angle, natural colors, atmospheric perspective, sharp focus, masterpiece, best quality' },
                    { label: '产品摄影', prompt: '8k, ultra detailed, product photography, clean background, studio lighting, commercial quality, sharp focus, masterpiece, best quality' },
                    { label: '建筑摄影', prompt: '8k, ultra detailed, architectural photography, geometric forms, interesting perspectives, natural lighting, sharp focus, masterpiece, best quality' },
                    { label: '微距摄影', prompt: '8k, ultra detailed, macro photography, shallow depth of field, beautiful bokeh, scientific precision, sharp focus, masterpiece, best quality' }
                ]
            },
            {
                title: '🎨 传统绘画', badges: ['传统'], items: [
                    { label: '数字绘画', prompt: 'digital painting, concept art, detailed illustration, rich colors, dynamic composition, professional artwork, masterpiece, best quality' },
                    { label: '动漫风格', prompt: 'anime style, manga, detailed character design, vibrant colors, clean line art, professional illustration, masterpiece, best quality' },
                    { label: '油画风格', prompt: 'oil painting, classical art, rich textures, sophisticated color mixing, fine art quality, masterpiece, best quality' },
                    { label: '水彩风格', prompt: 'watercolor painting, soft edges, translucent washes, artistic spontaneity, masterpiece, best quality' },
                    { label: '素描风格', prompt: 'pencil drawing, fine line work, subtle shading, classical draftsmanship, monochromatic tones, masterpiece, best quality' }
                ]
            },
            {
                title: '🌟 质量标签', badges: ['传统'], items: [
                    { label: '高质量', prompt: 'masterpiece, best quality, ultra detailed, high resolution, sharp focus, professional photography' },
                    { label: '艺术级', prompt: 'masterpiece, artistic, fine art, gallery quality, sophisticated composition, professional artwork' },
                    { label: '商业级', prompt: 'commercial quality, professional, market ready, high standard, polished appearance' },
                    { label: '电影级', prompt: 'cinematic, film quality, dramatic lighting, professional color grading, movie-like atmosphere' }
                ]
            }
        ];

        // ============== 智能路由逻辑 ==============
        let groups = [];

        // 添加收藏组
        groups.push(...favoritesGroup);

        if (isFlux) {
            if (isTxt2Img) {
                // Flux文生图：基础库
                groups = [...groups, ...fluxTextToImageGroups];
                
                // 根据工作流名称添加特定提示词
                if (filename.includes('redux')) {
                    groups.push(...reduxSpecificGroups);
                }
                if (filename.includes('controlnet')) {
                    groups.push(...controlnetSpecificGroups);
                }
                if (filename.includes('kontext')) {
                    groups.push(...kontextSpecificGroups);
                }
            } else if (isImg2Img) {
                // Flux图生图：编辑优化库
                groups = [...groups, ...fluxImageToImageGroups];
                
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
                if (filename.includes('kontext')) {
                    groups.push(...kontextSpecificGroups);
                }
            } else {
                // 默认Flux提示词
                groups = [...groups, ...fluxTextToImageGroups];
            }
        } else {
            // 传统模型：使用关键词堆叠风格的提示词
            groups = [...groups, ...legacyGroups];
        }
        
        return groups;
    }

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

    // 添加收藏功能
    toggleFavorite(item) {
        const key = `${item.label}|${(item.prompt || '').slice(0,200)}`;
        const existing = this.favorites.find(f => f.key === key);
        
        if (existing) {
            this.removeFromFavorites(key);
            return false; // 已移除
        } else {
            this.addToFavorites(item);
            return true; // 已添加
        }
    }

    // 添加收藏功能
    toggleFavorite(item) {
        const key = `${item.label}|${(item.prompt || '').slice(0,200)}`;
        const existing = this.favorites.find(f => f.key === key);
        
        if (existing) {
            this.removeFromFavorites(key);
            return false; // 已移除
        } else {
            this.addToFavorites(item);
            return true; // 已添加
        }
    }

    recordShortcutUsage(item) {
        const key = `${item.label}|${(item.prompt || '').slice(0,200)}`;
        const store = this.getShortcutUsageStore();
        if (!store[key]) {
            store[key] = { label: item.label, prompt: item.prompt || '', count: 0, lastTs: 0 };
        }
        const ctx = this.shortcutContext || {};
        const typeKey = `${ctx.isFlux ? 'flux' : 'std'}:${ctx.isTxt2Img ? 'txt2img' : (ctx.isImg2Img ? 'img2img' : 'other')}`;
        store[key].typeKey = typeKey;
        store[key].count += 1;
        store[key].lastTs = Date.now();
        
        const entries = Object.entries(store);
        if (entries.length > 200) {
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

    // 获取推荐提示词
    getRecommendedPrompts(limit = 5) {
        const store = this.getShortcutUsageStore();
        const ctx = this.shortcutContext || {};
        const typeKey = `${ctx.isFlux ? 'flux' : 'std'}:${ctx.isTxt2Img ? 'txt2img' : (ctx.isImg2Img ? 'img2img' : 'other')}`;
        
        const relevant = Object.entries(store)
            .filter(([_, data]) => data.typeKey === typeKey)
            .sort((a, b) => b[1].count - a[1].count)
            .slice(0, limit)
            .map(([_, data]) => ({
                label: data.label,
                prompt: data.prompt,
                count: data.count
            }));
        
        return relevant;
    }

    prependLoraPromptShortcuts(words, loraName, attempt = 0) {
        try {
            const container = document.getElementById('promptShortcuts');
            if (!Array.isArray(words) || words.length === 0) return;
            if (!container) {
                if (attempt < 20) {
                    setTimeout(() => this.prependLoraPromptShortcuts(words, loraName, attempt + 1), 150);
                }
                return;
            }
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
            const self = this;
            words.forEach(w => {
                const btn = document.createElement('button');
                btn.type = 'button';
                btn.className = 'shortcut-btn';
                btn.textContent = w;
                btn.addEventListener('click', () => {
                    self.lastPresetLabel = w;
                    if (typeof self.applyPromptShortcut === 'function') {
                        try { self.applyPromptShortcut({ label: w, prompt: w }); return; } catch (_) {}
                    }
                    // 兜底直写
                    try {
                        const positiveEl = document.getElementById('positivePrompt');
                        const negativeEl = document.getElementById('negativePrompt');
                        const overwrite = document.getElementById('promptOverwriteSwitch')?.checked;
                        const text = w;
                        if (positiveEl) {
                            const trimmed = (positiveEl.value || '').trim();
                            if (overwrite || !trimmed) positiveEl.value = text; else positiveEl.value = positiveEl.value + (trimmed.endsWith(',') ? ' ' : ', ') + text;
                            positiveEl.dispatchEvent(new Event('input', { bubbles: true }));
                            positiveEl.dispatchEvent(new Event('change', { bubbles: true }));
                        }
                    } catch (_) {}
                });
                btns.appendChild(btn);
            });
            block.appendChild(btns);
            container.prepend(block);
        } catch (_) {}
    }
}

// 导出类供主应用使用
window.PromptShortcutSystem = PromptShortcutSystem;



