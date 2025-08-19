

# **Flux.1权威指南：精通文本到图像与图像到图像生成**

## **第一部分：Flux.1生态系统：架构与模型**

### **1.1 新的业界标杆：Black Forest Labs的Flux.1简介**

Flux.1是由Black Forest Labs（BFL）开发的最新一代文本到图像（Text-to-Image）模型，标志着人工智能生成领域的一个重要里程碑 1。该实验室由Stability AI的前核心研究团队成员创立，其中包括了著名模型Stable Diffusion的原始研究者 2。这一背景不仅为Flux.1注入了深厚的技术底蕴，也使其在设计上直接瞄准并解决了其前辈模型的诸多痛点。

自发布以来，Flux.1在多项基准测试中展现出卓越的性能，其表现在提示词遵循度、视觉质量、细节丰富度和文本渲染能力上，均优于或媲美业界领先的模型，如Midjourney v6、DALL-E 3和Stable Diffusion 3（SD3）1。特别是在处理复杂构图、手部细节和图像内文字生成等长期困扰AI图像生成模型的难题上，Flux.1取得了显著的突破，极大地提升了生成图像的准确性和可用性 2。

Flux.1的诞生可以被视为其创始团队在Stable Diffusion基础上的一次技术和理念的演进。它继承了潜在扩散模型（Latent Diffusion Models）的核心思想，但在架构上进行了大胆的革新，旨在系统性地解决先前模型在语言理解和精细控制上的局限性。因此，Flux.1不仅是一个新的模型，更是一个旨在重新定义开源AI图像生成质量与控制力标准的旗舰级项目，为创作者和开发者社区带来了前所未有的强大工具 3。

### **1.2 深入核心：双编码器架构与修正流变换器**

Flux.1的卓越性能源于其创新的底层架构。该模型基于一种名为“修正流变换器”（Rectified Flow Transformer）的结构，并采用流匹配（Flow Matching）方法进行训练 3。与传统的扩散模型训练方式相比，流匹配更为高效，能够显著提升图像的连贯性和风格多样性 4。

然而，Flux.1最核心的创新在于其独特的**双文本编码器架构** 1。这一设计是其能够精准理解复杂、冗长和描述性提示词的关键所在。系统摒弃了单一编码器处理所有语言任务的传统模式，而是将任务分解，由两个专门的编码器协同工作：

* **T5编码器 (Text-to-Text Transfer Transformer):** T5编码器负责提供“密集”的、基于每个词元（token）的嵌入表示 1。这意味着它能够深入分析提示词的语法结构、上下文关系以及词语间的逻辑联系。当用户输入一个长句子，如“一个宇航员站在一辆红色汽车的左边，背景是日落时分的火星”，T5能够精确解析“左边”这个空间关系，确保生成的图像构图准确无误。正是这种对语言细微之处的深刻理解，赋予了Flux.1无与伦比的提示词遵循能力。  
* **CLIP编码器 (Contrastive Language-Image Pre-training):** CLIP编码器则提供“池化”的嵌入表示，即为整个提示词生成一个单一的、概括性的向量 1。这个向量捕捉了提示词的整体语义和美学概念。它不关注具体的语法细节，而是把握整体的“感觉”或“风格”，例如“电影感摄影”、“水彩画风格”或“赛博朋克氛围”。CLIP的作用是为图像的整体艺术方向和氛围定下基调。

这种双编码器系统通过任务分离实现了协同增效。它允许模型在两个层面上同时处理提示词：通过T5的结构化嵌入理解精确的指令，同时通过CLIP的池化嵌入把握整体的艺术风格。这种双流并行的处理方式，从根本上解决了单一编码器在处理复杂指令时容易顾此失彼、忽略细节的问题，从而使其在提示词保真度方面远超前代模型。这一架构上的飞跃，正是Flux.1重新定义“提示词工程”——从语法技巧转向语义表达——的底气所在。

### **1.3 选择你的工具：Flux.1模型家族对比分析**

Flux.1并非单一模型，而是一个包含多个版本和工具的庞大生态系统，旨在满足从专业商业制作到学术研究和快速原型设计的不同需求。了解每个模型的特性、性能和授权方式，是高效利用Flux.1的第一步 9。

* **官方核心模型:**  
  * FLUX.1 \[pro\]: 旗舰商业版，提供最顶级的图像质量、细节表现和提示词遵循度。专为需要最高标准视觉效果的商业项目设计，通常通过API授权使用 1。  
  * FLUX.1 \[dev\]: 开发者与研究版。该模型通过指导蒸馏技术从Pro版衍生而来，质量与Pro版相近，但授权严格限制于非商业用途，为学术研究和个人探索提供了强大的开源工具 1。  
  * FLUX.1 \[schnell\]: 速度优化版。“Schnell”在德语中意为“快速”。该模型同样从Pro版蒸馏而来，但目标是大幅缩短推理时间，可在1至4步内生成高质量图像。它采用宽容的Apache 2.0许可证，允许完全的商业使用，是实时应用和需要快速迭代场景的理想选择 1。  
* **图像编辑与控制套件:**  
  * FLUX.1 Kontext: 专为图像到图像（Image-to-Image）编辑而设计，能够理解图像上下文，实现角色一致性保持、局部编辑、风格迁移和文字修改等高级功能 13。  
  * FLUX.1 Fill: 专用的修复模型，用于图像的内补（Inpainting）和外扩（Outpainting），能够无缝地填充或扩展图像区域 15。  
  * FLUX.1 Redux: 一个适配器模型，用于生成图像的变体或进行风格重塑，可以结合文本提示词对输入图像进行修改 16。  
  * FLUX.1 Canny & Depth: ControlNet类模型，允许用户通过Canny边缘图或深度图来精确控制生成图像的结构和构图 17。  
* **合作与美学模型:**  
  * FLUX.1 Krea \[dev\]: 与Krea AI合作开发，专注于生成具有独特美学风格和自然细节的图像，旨在避免传统AI图像的“塑料感”和过曝高光，提供卓越的真实感 18。  
* **社区优化版本:**  
  * 由于Flux.1模型参数量巨大（120亿），对硬件要求较高，开源社区迅速推出了多种量化版本，如FP8、GGUF和NF4。这些版本通过降低模型精度来大幅减少显存（VRAM）占用，使得在消费级GPU上运行成为可能，尽管可能会有轻微的质量损失 6。

为了帮助用户快速选择最适合其需求的模型，下表对主要模型进行了详细比较。

**表1：Flux.1模型家族对比**

| 模型名称 | 主要用例 | 图像质量 | 速度 | 许可证 | 核心特性 |
| :---- | :---- | :---- | :---- | :---- | :---- |
| **FLUX.1 \[pro\]** | 商业制作、高端艺术创作 | 顶级 | 标准 | 商业授权 | 最高的提示词保真度和视觉细节 1 |
| **FLUX.1 \[dev\]** | 学术研究、个人项目、非商业开发 | 接近Pro | 标准 | 非商业 11 | 质量与Pro相当的开源权重模型 1 |
| **FLUX.1 \[schnell\]** | 实时应用、快速原型、低延迟服务 | 良好 | 极快 | Apache 2.0 | 1-4步快速生成，完全开放商业使用 1 |
| **FLUX.1 Kontext \[dev\]** | 图像编辑、角色一致性、风格迁移 | 优秀 | 快速 | 非商业 | 强大的上下文理解和迭代式编辑能力 14 |
| **FLUX.1 Fill \[dev\]** | 图像修复（内补/外扩） | 优秀 | 标准 | 非商业 | 专为无缝填充和扩展图像而训练 15 |
| **FLUX.1 Krea \[dev\]** | 追求独特美学、高级真实感 | 卓越 | 标准 | 非商业 | 避免“AI感”，生成自然的细节和光影 18 |

## **第二部分：文本到图像生成的艺术**

掌握了Flux.1的模型生态后，下一步是精通其核心功能：从文本生成图像。这一部分将深入探讨提示词的构建哲学、高级参数的运用，并提供一个丰富的模板库，助您将想象力转化为精准的视觉作品。

### **2.1 高效提示词的基础：从自然语言到层级结构**

Flux.1的提示词工程哲学与许多早期模型截然不同。它不再依赖于“关键词堆砌”或“标签轰炸”的策略，而是推崇使用清晰、描述性强、符合逻辑的自然语言，就像与一位人类艺术家沟通一样 22。这种转变的背后，是其强大的T5文本编码器在发挥作用，它使得模型能够真正“读懂”句子的含义而非仅仅识别关键词。

要构建高效的Flux.1提示词，需遵循以下核心原则：

* **精确与清晰 (Precision and Clarity):** 避免使用“好看的”、“漂亮的”等模糊词汇。应使用具体的描述词来定义你想要的画面。例如，将“一张美丽的风光照”改进为“一张描绘白雪皑皑的山脉上空，橙色与粉色交织的绚烂日落，前景平静的湖面反射着柔和云彩的 vibrant 风光照” 23。  
* **层级结构 (Hierarchical Structure):** 为了精确控制画面构图，应按照逻辑顺序描述场景，通常遵循“前景-中景-背景”的顺序。这有助于模型理解各个元素在空间中的位置关系，避免构图混乱。如果你先描述了前景，然后描述了背景，最后又想起前景还需要添加一个物体，不要将这个新描述附加在末尾，而应将其插入到前景的描述部分，保持结构的完整性 22。  
* **动态语言 (Dynamic Language):** 使用动词和面向动作的描述，能让生成的图像更具生命力和动感。静态的描述容易产生平淡的画面。例如，将“一座山峰”改进为“一座雄伟的山峰从缭绕的晨雾中浮现，金色的日出光芒捕捉到其上晶莹的冰晶构造” 23。

Flux.1对自然语言的偏好，实际上正在重塑“提示词工程师”这一角色的技能要求。精通Flux.1不再意味着要掌握晦涩的语法权重和特殊符号，而是要成为一名优秀的“视觉描述者”或“场景导演”。这种转变降低了技术门槛，让更多不具备深厚AI技术背景的艺术家、设计师和作家也能充分发挥模型的潜力，实现精准的创意控制。

### **2.2 掌握高级参数与常见误区**

除了提示词本身，一系列技术参数也为生成过程提供了精细的控制。同时，了解并避开一些常见于其他模型的“习惯性”错误，对于在Flux.1上获得最佳效果至关重要。

**核心生成参数**

| 参数 | 功能 | 常见范围 | 推荐用例 |
| :---- | :---- | :---- | :---- |
| guidance\_scale | 控制生成图像与提示词的符合程度。值越高，越严格遵循提示词，但可能牺牲创造性和自然感；值越低，模型自由度越高 1。 | 1 \- 15 | 短而精确的提示词可使用较高值（如4-7）；长而富有诗意的描述性提示词建议使用较低值（如1-3.5），以获得更自然、和谐的效果 25。 |
| num\_inference\_steps | 推理步数。决定了去噪过程的迭代次数。步数越多，细节越丰富，但生成时间也越长 1。 | 1 \- 50 | schnell模型设计为在1-4步内工作。dev模型通常需要更多步数（如20-40步）以达到最佳质量 1。 |
| seed | 随机种子。一个固定的种子值可以在其他参数不变的情况下，生成完全相同的图像，便于复现和微调 26。 | 0 \- 2147483647 | 设为-1或随机值以探索不同结果。当你找到一个满意的构图时，固定种子值，然后调整提示词或其它参数进行迭代。 |
| width / height | 生成图像的宽度和高度，单位为像素。 | 256 \- 2048 | Flux.1支持多种宽高比。常见设置为1024x1024。为避免主体重复或构图异常，建议初始生成时分辨率不要超过200万像素（约1414x1414）26。 |

**常见误区与解决方案**

* **误区一：使用权重语法:** Flux.1不支持Stable Diffusion中常见的权重语法，如 (word:1.2) 或 \[word\] 来强调某个词。在提示词中加入这些符号不会起作用 22。  
  * **解决方案:** 使用自然语言替代。如果你想强调“一朵玫瑰”，不要写 a garden with (a single rose)++，而应写 a garden with a strong emphasis on a single rose（一个花园，重点突出单单一朵玫瑰）22。  
* **误区二：在\[dev\]模型中使用“白色背景”:** 一个特定的怪癖是，当使用 FLUX.1 \[dev\] 模型并明确要求“white background”（白色背景）时，生成的图像（尤其是Logo和图标）有时会变得模糊或质量下降 22。  
  * **解决方案:**  
    1. **避免该短语:** 最直接的方法是完全不在提示词中提及背景，让模型自行决定。  
    2. **使用同义词:** 如果必须指定背景，可以尝试使用“clean design”（简洁设计）、“minimal backdrop”（极简背景）或直接指定其他颜色，如“light gray background”（浅灰色背景）28。  
    3. **添加质量词:** 在提示词中加入“4K”、“UHD”、“high resolution”、“sharp and detailed”等词语，可以引导模型生成更清晰的图像 28。  
* **误区三：原生负向提示词:** Flux.1的基础模型本身不直接支持负向提示词（Negative Prompt）输入框。  
  * **解决方案 (ComfyUI):** 在ComfyUI工作流中，可以通过社区开发的自定义节点 Dynamic Thresholding 来实现负向提示词功能。这需要将模型连接到 DynamicThresholdingFull 节点，再将该节点的输出连接到采样器（KSampler）。通过这种方式，可以利用负向提示词来排除不希望出现的元素，例如“blurry”（模糊）、“deformed”（畸形）等 29。

### **2.3 提示词库：T2I模板与精选案例**

本节提供一系列结构化的提示词模板和丰富的实例，覆盖了从写实摄影到UI设计的多个领域。每个模板都旨在成为一个可扩展的框架，您可以根据自己的创意需求进行填充和修改。

#### **2.3.1 模板一：写实摄影（人像与风光）**

此模板专注于模拟真实世界的摄影效果，强调光影、相机参数和环境氛围的细节描述。

**通用模板:**

\[照片类型\] of a \[主体\], \[主体细节描述\]. Shot on a \[相机/镜头类型\], aperture \[光圈值\], \[快门速度\], ISO \[感光度\]. Lighting is \[光照描述\], creating a \[氛围\] mood. The scene is set in \[场景描述\], with \[前景/背景细节\]. The color palette is dominated by \[主要色调\]..

**精选案例:**

* **人像摄影:**An impressive portrait of an African young woman, with an expression that reveals profound sadness and resilience. Her expressive and detailed eyes reflect the complexity of her emotions. The background consists of a foggy and melancholic setting, with soft colors and deep shadows that create an atmosphere of introspection and quiet hope. Shot on a Canon EOS R5 with an 85mm f/1.2 lens. The visual elements are rendered in 4K, with realistic lighting and textures that enhance every detail.  
  (一幅令人印象深刻的非洲年轻女性肖像，表情流露出深深的悲伤与坚韧。她富有表现力且细节丰富的眼睛反映了她复杂的情感。背景是雾气弥漫的忧郁场景，柔和的色彩和深邃的阴影营造出一种内省和静谧希望的氛围。使用佳能EOS R5相机和85mm f/1.2镜头拍摄。视觉元素以4K渲染，逼真的光照和纹理增强了每一个细节。) 30  
* **风光摄影:**A vibrant orange and pink sunset over a snow-capped mountain range, with soft, wispy clouds reflecting off a calm lake in the foreground. Shot on a Sony Alpha 7R IV, capturing the vibrant colors and sharp details of the scene. The lighting is the golden hour, casting long soft shadows. The mood is serene and majestic. Photorealistic, ultra HD.  
  (白雪皑皑的山脉上空，橙色与粉色交织的绚烂日落，前景平静的湖面反射着柔和的云彩。使用索尼Alpha 7R IV相机拍摄，捕捉了场景中鲜艳的色彩和锐利的细节。光线是黄金时刻，投下长长的柔和阴影。氛围宁静而雄伟。照片般逼真，超高清。) 23

#### **2.3.2 模板二：动漫与插画**

此模板专注于复现特定的动漫或插画风格，强调角色设计、线条、色彩和标志性元素。

**通用模板:**

\[动漫风格\] illustration of a \[角色原型\], featuring \[发型/发色\], \[眼睛颜色/形状\], and a \[表情\]. The character wears \[服装描述\]. The background is a \[场景描述\], with \[场景元素\]. The color palette consists of \[主要颜色\]. Style is characterized by \[线条/上色风格描述\].

**精选案例:**

* **赛博朋克黑客:**Cyberpunk anime style. A tech-savvy hacker with neon green hair styled into a mohawk, glowing goggles, and a mischievous grin. They wear a futuristic jacket adorned with LED patterns and fingerless gloves. The background is a dimly lit, high-tech room filled with holographic displays and wires. Use neon greens, purples, and metallic silvers to create a cyberpunk aesthetic with sharp line work.  
  (赛博朋克动漫风格。一个精通技术的黑客，留着霓虹绿色的莫霍克发型，戴着发光的护目镜，脸上挂着恶作剧般的笑容。他们穿着一件装饰有LED图案的未来派夹克和无指手套。背景是一个光线昏暗的高科技房间，充满了全息显示屏和电线。使用霓虹绿、紫色和金属银来营造赛博朋克美学和锐利的线条。) 33  
* **奇幻魔法师:**Fantasy anime style. An elegant sorceress with flowing white hair, violet eyes, and intricate magical tattoos glowing softly on her arms. She wears a regal robe with golden trim and a floating crystal crown. The background is a mystical mountain peak surrounded by swirling clouds. The style is reminiscent of high-quality anime art, with crisp linework and semi-realistic shading.  
  (奇幻动漫风格。一位优雅的女巫，拥有飘逸的白发、紫罗兰色的眼睛，手臂上复杂的魔法纹身发出柔和的光芒。她穿着带有金色镶边的庄严长袍，头戴一顶漂浮的水晶皇冠。背景是云雾缭绕的神秘山峰。风格让人联想到高品质的动漫艺术，线条清晰，阴影半写实。) 33

#### **2.3.3 模板三：幻想与科幻艺术**

此模板用于构建富有想象力的世界，侧重于氛围营造、概念融合和超现实元素的描述。

**通用模板:**

A \[类型: dark fantasy, epic sci-fi\] scene depicting \[核心场景\]. The environment is characterized by \[环境特征\], with \[标志性建筑/地貌\]. The atmosphere is \[氛围描述\], with lighting from \[光源\]. Key elements include \[关键物体/生物\]. The style is a blend of \[风格1\] and \[风格2\].

**精选案例:**

* **黑暗幻想:**An enchanting dark fantasy scene. A semi-transparent woman, her silhouette illuminated by a radiant blue hue, is surrounded by a mesmerizing array of glow-in-the-dark butterflies in vibrant neon colors. The butterflies fill her silhouette completely. The clean darkness of the background serves as a perfect contrast, evoking a sense of enchantment, wonder, and mystique. The style is a blend of conceptual art and cinematic aesthetics.  
  (一幅迷人的黑暗幻想场景。一个半透明的女人，她的轮廓被耀眼的蓝色光芒照亮，周围环绕着无数色彩鲜艳的霓虹色夜光蝴蝶。蝴蝶完全充满了她的轮廓。纯净的黑暗背景形成了完美的对比，唤起一种魔法、奇迹和神秘的感觉。风格融合了概念艺术和电影美学。) 35  
* **未来派城市景观:**A surreal fusion of a dreamlike cityscape and a painterly sky, where the horizon is split by swirling, luminescent strokes in bold blues and yellows. Futuristic skyscrapers stretch endlessly into the night, reflecting the celestial hues above them. This captivating image captures both the unsettling beauty of a world where the laws of physics are distorted and the emotional intensity of a landscape imbued with vibrant energy.  
  (一个梦幻般的城市景观与绘画般天空的超现实融合，地平线被大胆的蓝色和黄色漩涡状发光笔触分割。未来派的摩天大楼无尽地延伸至夜空，反射着上方的天体色彩。这幅迷人的图像捕捉了一个物理定律被扭曲的世界中令人不安的美，以及一个充满活力的景观所蕴含的情感强度。) 36

#### **2.3.4 模板四：商业与UI/UX设计（Logo、图标、模型）**

此模板专注于生成简洁、明确且符合品牌识别的商业设计资产。

**通用模板:**

A \[设计风格: minimalist, flat design, abstract\] logo for a \[行业\] company named "\[品牌名\]". The logo features a \[核心图形元素\]. The color palette is \[颜色\]. The design is set against a \[背景描述: clean white background, no background\]. \[关键词: modern, elegant, professional, vector\].

**精选案例:**

* **Logo设计:**A minimalist logo for a nature brand, in a circular shape, representing a nature brand with subtle green leaves and delicate water ripple textures. The design uses clean lines, simple details, and balanced white space. The style is modern and organic, suitable for eco-friendly products. Set against a clean white background.  
  (一个为自然品牌设计的极简主义圆形标志，以微妙的绿叶和精致的水波纹理为代表。设计采用简洁的线条、简单的细节和平衡的留白。风格现代而有机，适合环保产品。设置在干净的白色背景上。) 37  
* **App图标设计:**Modern flat-design circle icon featuring a stylized lotus flower. The color palette is a combination of bright, bold colors like teal and coral, adding a playful, artistic flair. Set against a clean design background, 4k, UHD.  
  (现代扁平化设计的圆形图标，以一朵程式化的莲花为特色。调色板是青色和珊瑚色等明亮、大胆的颜色组合，增添了俏皮的艺术气息。设置在简洁的设计背景上，4K，UHD。) 28

## **第三部分：使用Kontext进行图像到图像转换的科学**

Flux.1生态系统的另一大支柱是其强大的图像到图像（Image-to-Image, I2I）转换能力，这主要由FLUX.1 Kontext模型驱动。Kontext不仅仅是一个简单的图像滤镜或风格化工具，它代表了生成式编辑领域的一次范式转变，为用户提供了前所未有的控制力和灵活性。

### **3.1 统一编辑引擎：核心I2I能力**

FLUX.1 Kontext是一个统一的多模态模型，它能够同时将文本和图像作为输入，从而实现对图像内容的深度理解和上下文感知编辑 13。与传统I2I工作流（通常需要通过高强度的“去噪”来彻底改变图像）不同，

Kontext擅长进行精确的、外科手术式的修改。其核心能力包括：

* **角色一致性 (Character Consistency):** 这是Kontext最受赞誉的功能之一。它能够在多次编辑或跨场景生成中，精准地保持一个角色或物体的身份特征，如面部、发型和服装，无需进行额外的模型微调（Finetuning）14。  
* **局部与全局编辑 (Local & Global Editing):** 用户可以进行精细的局部修改，例如“把这辆红色的车变成蓝色”，也可以进行影响整个画面的全局变换，例如“将白天场景改为夜晚” 14。  
* **风格参考与迁移 (Style Referencing/Transfer):** Kontext能够从一张参考图中提取其独特的艺术风格，并将其应用到新的内容生成中，同时保持新内容的结构 14。  
* **文本编辑 (Text Editing):** 模型可以直接识别并修改图像中的文字内容，如路牌、标签或海报上的文字，且能尝试保持原有的字体风格 40。  
* **迭代式编辑 (Iterative Editing):** 得益于其极快的推理速度和高度的编辑一致性，Kontext非常适合进行逐步求精的迭代式工作流。用户可以先进行一项修改，然后在生成结果的基础上进行下一步修改，整个过程流畅且可控，就像与一位设计助理进行多轮对话 14。

Kontext模型的出现，标志着AI艺术创作正从“一次性生成”模式向“对话式创作”模式演进。传统的I2I更像一个自动售货机：投入一张图片和一个指令，得到一个结果。而Kontext则更像一个协作画布，用户可以与AI进行持续的、有状态的互动，其中“上下文”（Kontext）就是不断演变的图像本身。这种交互模式预示了未来AI创意工具的发展方向：更智能、更具协作性，也更符合人类艺术家的创作直觉。

### **3.2 I2I提示词框架与关键参数**

为了在Kontext中实现可控的编辑，需要采用一种基于“指令”的提示词风格。这种风格清晰、直接，明确告知模型要“做什么”以及要“保留什么”。

核心任务的提示词框架 40:

* **角色一致性:** \[指定变换:...is now in a tropical beach setting\]\[保留身份标记:...while maintaining the same facial features and expression\].  
* **风格迁移:** \[指定风格: Convert to pencil sketch\]\[描述特征: with natural graphite lines and cross-hatching\]\[保留构图: while preserving the original composition\].  
* **文本编辑:** 使用引号精确定位：Replace 'OPEN' with 'CLOSED' on the sign.  
* **构图控制:** 明确声明保留项：Change the background to a beach while keeping the person in the exact same position, scale, and pose.

**关键参数：strength / denoising\_strength**

在I2I流程中，最重要的控制参数是“强度”（在API中通常称为strength）或“去噪强度”（在ComfyUI中称为denoising\_strength）。该参数值范围为0.0到1.0，它决定了原始图像与文本提示词之间的平衡关系 46。

**表3：I2I强度/去噪参数指南**

| 强度/去噪值范围 | 对图像的影响 | 推荐用例 |
| :---- | :---- | :---- |
| **0.1 \- 0.3** | 对原始图像的改动极小，几乎只进行微调。 | 轻微的颜色校正、细节增强、修复微小瑕疵 46。 |
| **0.4 \- 0.6** | 显著改变，但仍保留原始图像的核心结构和构图。 | 改变物体颜色、材质，添加小型物体，轻度风格化 47。 |
| **0.7 \- 0.9** | 发生巨大变化，原始图像主要作为构图参考，提示词的主导性增强。 | 彻底的风格迁移（如照片变油画）、更换背景、大幅修改角色服装 46。 |
| **1.0** | 完全忽略原始图像内容，生成一个全新的图像，仅在构图上可能与原始图像有模糊的相似性。 | 相当于文生图，用于完全重新创作 47。 |

### **3.3 高级I2I技术：修复、扩展与多图参考**

除了基础编辑，Flux.1的I2I工具套件还支持更复杂和专业的工作流程，尤其是在ComfyUI这样的节点式环境中。

* 使用FLUX.1 Fill进行图像修复与扩展:  
  FLUX.1 Fill是专为内补（Inpainting）和外扩（Outpainting）任务训练的模型 15。相比使用标准模型进行修复，  
  Fill模型能在保持周围图像内容高度一致性的前提下，生成更自然、无缝的填充内容。  
  * **工作流程:** 在ComfyUI中，用户首先在Load Image节点中加载图片，并使用内置的MaskEditor绘制一个遮罩（mask），标记出需要修改或填充的区域。然后，将带有遮罩的图像和描述新内容的提示词输入到使用flux1-fill-dev.safetensors模型的工作流中。Fill模型的一个巨大优势是，它可以在去噪强度为1.0的情况下工作，这意味着它可以完全根据提示词生成全新的内容，而不会受到遮罩区域原始像素颜色的影响，同时完美地与未遮罩区域融合 50。  
* 使用Kontext进行多图像参考:  
  Kontext模型在ComfyUI中支持使用多张图像作为参考，这为创意合成开辟了新的可能性。主要有两种实现方法 51：  
  1. **图像拼接 (Image Stitching):** 这是更简单、更快速的方法。用户可以使用Image Stitch节点将多张参考图（如一张人物肖像和一张服装平铺图）拼接成一张更大的图像。然后将这张拼接后的图像作为Kontext的单一输入。这种方法的优点是速度快，但对各参考图的控制力较弱 51。  
  2. **参考潜在空间链接 (ReferenceLatent Chaining):** 这是更高级、控制更精确的方法。每张参考图分别通过一个VAE Encode节点编码成潜在空间表示（latent），然后通过串联多个ReferenceLatent节点，将这些不同的潜在空间信息流合并到同一个处理管线中。这种方法允许模型独立地“看到”每一张参考图，从而在最终生成时更好地融合它们的特征，例如将A图的人物精确地穿上B图的衣服，并置于C图的背景中。虽然处理速度较慢且消耗更多显存，但它提供了无与伦比的合成控制力 51。

### **3.4 视觉案例研究：前后效果对比**

理论的讲解最终需要通过直观的视觉效果来验证。以下案例展示了Kontext和Fill在实际应用中的强大能力。

* **风格迁移:**  
  * **原始图像:** 一张猫头鹰的写实照片。  
  * **提示词:** Convert to quick pencil sketch (转换为快速铅笔素描)。  
  * **生成结果:** 照片被成功转换为一幅具有清晰铅笔线条和阴影纹理的素描画 45。  
* **局部编辑:**  
  * **原始图像:** 一位戴着蓝色头巾的女性。  
  * **提示词:** Make the woman's blue headscarf into a green headscarf (将女士的蓝色头巾变成绿色)。  
  * **生成结果:** 头巾的颜色变为绿色，而女性的面部特征、表情以及图像的其他部分保持不变 45。  
* **角色一致性与全局编辑:**  
  * **原始图像:** 上一步中戴着绿色头巾的女性。  
  * **提示词:** Put the woman with the green headscarf in a jungle (将戴绿色头巾的女士放入丛林中)。  
  * **生成结果:** 背景被成功替换为茂密的丛林，而人物的身份、姿态和绿色头巾都得到了完美的保留，展示了跨场景的角色一致性 45。  
* **文本编辑:**  
  * **原始图像:** 一副太阳镜，镜片上印有文字“Almost Famous”。  
  * **提示词:** Change the text in the sunglasses to be 'FLUX' and 'Kontrast' (将太阳镜中的文字改为'FLUX'和'Kontrast')。  
  * **生成结果:** 镜片上的文字被准确地替换为“FLUX Kontrast”，同时保持了文字在镜片上的位置和风格 45。  
* **复杂变换（迭代编辑）:**  
  * **原始图像:** 一幅描绘城市夜景的画作。  
  * **第一步提示词:** Change to daytime while maintaining the same style of the painting (在保持同样绘画风格的同时改为白天)。  
  * **第二步提示词 (基于上一步结果):** add a lot of people walking the sidewalk (在人行道上增加许多行人)。  
  * **最终结果:** 场景成功从夜晚变为白天，并且人行道上出现了符合场景风格的行人，整个过程保持了原始画作的艺术风格 40。

## **第四部分：实践应用：高级ComfyUI工作流**

对于追求极致控制和灵活性的高级用户而言，ComfyUI是运行Flux.1的首选平台。本部分将提供详细的技术指南，帮助您在ComfyUI中搭建、配置并运行高级的Flux.1工作流。

### **4.1 搭建你的Flux.1实验室：安装、模型管理与必备节点**

在ComfyUI中成功运行Flux.1需要正确配置环境和模型文件。

**安装与模型配置:**

1. **更新ComfyUI:** 在开始之前，请确保您的ComfyUI已更新至最新版本。这可以通过在ComfyUI根目录下运行git pull或使用ComfyUI Manager中的更新功能来完成 6。  
2. **下载核心模型文件:** Flux.1的原始工作流需要多个独立的模型文件协同工作 54。  
   * **UNET/Diffusion Model:** 这是模型的主体。根据您选择的版本（如flux1-dev.safetensors或flux1-schnell.safetensors），下载后放入ComfyUI/models/unet/或ComfyUI/models/diffusion\_models/文件夹 6。  
   * **CLIP文本编码器:** Flux.1需要两个CLIP模型。将clip\_l.safetensors和t5xxl\_fp16.safetensors（或低显存版本t5xxl\_fp8\_e4m3fn.safetensors）下载并放入ComfyUI/models/clip/文件夹 6。  
   * **VAE (Variational Autoencoder):** 下载ae.safetensors并放入ComfyUI/models/vae/文件夹 6。  
3. **管理社区优化版本:**  
   * **Checkpoint版本 (FP8):** Comfy-Org等社区贡献者将所有必需文件打包成一个单一的.safetensors文件（如flux1-dev-fp8.safetensors）。这种版本使用起来更方便，只需将其放入ComfyUI/models/checkpoints/目录，并使用标准的Load Checkpoint节点即可加载 6。  
   * **GGUF版本:** GGUF是为在低显存GPU上运行而设计的量化格式。要使用GGUF模型（如flux1-dev-Q6\_K.gguf），您需要先安装ComfyUI-GGUF这个自定义节点包，然后将模型文件放入ComfyUI/models/unet/，并使用Unet Loader (GGUF)节点加载 6。

**必备自定义节点:**

为了解锁Flux.1的全部潜力并简化工作流程，强烈建议安装以下自定义节点包（可通过ComfyUI Manager安装）：

* ComfyUI Manager: 用于安装和管理其他所有自定义节点和缺失模型，是ComfyUI生态的基石 50。  
* ComfyUI Impact Pack: 提供了包括FaceDetailer（面部修复）、Detailer和高级升采样器在内的强大图像后处理工具，对于提升Flux.1生成图像的最终质量至关重要 57。  
* ComfyUI-GGUF: 如果您计划使用GGUF量化模型，则必须安装此节点包 20。  
* rgthree-comfy: 提供了一系列工作流效率工具，如Muter/Reroute节点，可以方便地启用或禁用工作流的某些部分，便于测试和调试 56。

### **4.2 高级工作流蓝图：高清放大、面部精修与ControlNet集成**

本节将介绍几种高级工作流的构建思路，这些工作流能够解决标准文生图之外的复杂需求。

* 高分辨率放大工作流:  
  直接生成超高分辨率的图像通常效率低下且效果不佳。更优的策略是先生成一张中等分辨率（如1024x1024）的图像，然后通过一个专门的放大工作流来提升其分辨率和细节。这通常涉及Ultimate SD Upscale节点或结合ControlNet的放大技术。例如，可以使用Tile ControlNet模型将图像分块处理，对每个分块进行细节重绘，最后再拼接起来，从而在不爆显存的情况下实现4K甚至更高分辨率的输出 59。  
* 面部细节修复工作流:  
  尽管Flux.1在解剖结构上表现出色，但在较低分辨率或复杂场景中，面部细节仍可能模糊不清。FaceDetailer节点（来自Impact Pack）可以自动解决这个问题。该工作流在主生成流程之后添加FaceDetailer节点。它会自动检测图像中的面部，然后对该区域进行一次局部的、高分辨率的修复（inpainting），显著提升眼睛、皮肤纹理等细节的清晰度，而无需手动创建遮罩 57。  
* ControlNet集成工作流:  
  社区已经为Flux.1开发了专用的ControlNet模型，如Canny和Depth 64。这些工具允许用户以前所未有的精度控制生成图像的构图。  
  * **工作流程:** 首先，使用Canny或Depth预处理器节点从一张参考图像中提取边缘图或深度图。然后，将这个控制图与提示词一起输入到Apply ControlNet节点中。最后，将ControlNet的输出连接到采样器。这样，模型在生成图像时，不仅会遵循文本提示词的语义描述，还必须严格遵守控制图所定义的结构布局，非常适合用于建筑可视化、产品设计或保持特定姿势的角色生成 17。

## **第五部分：拓展视野与问题解决**

本部分将Flux.1置于更广阔的AI生态系统中进行考量，涵盖社区增强功能、与主要竞争对手的深入比较，以及针对已知问题的实用解决方案。

### **5.1 LoRA生态系统：增强与定制Flux.1**

低秩适应（Low-Rank Adaptation, LoRA）是一种高效的模型微调技术，它允许用户在不修改庞大基础模型的前提下，通过训练一个小型附加文件（通常只有几十到几百MB）来教导模型新的风格、角色或概念 68。LoRA极大地扩展了Flux.1的能力和灵活性。

* 查找与使用LoRA:  
  Civitai和Hugging Face是寻找Flux.1兼容LoRA的主要平台。在ComfyUI中，使用Load LoRA节点，将其连接在主模型和CLIP编码器之间，即可加载LoRA并调整其影响权重（通常在0.5到1.0之间）68。  
* 推荐的社区LoRA:  
  社区已经为Flux.1贡献了大量高质量的LoRA，以下是一些必备的类别和范例：  
  * **写实/摄影风格:**  
    * UltraRealistic LoRA: 显著提升图像的真实感，增加皮肤纹理和自然光影 70。  
    * Amateur Photography: 模拟业余摄影的质感，减少AI的“完美感”，增加照片的生活气息 70。  
    * Eldritch Photography / 35mm Film: 赋予图像复古胶片或特定电影质感 70。  
  * **艺术风格:**  
    * Anime Style LoRA: 专门用于生成高质量的日式动漫风格图像，通常比基础模型直接生成的效果更地道 73。  
    * Retro Comic LoRA: 模拟复古美式漫画的风格，包括网点纸效果和粗犷的线条 75。  
  * **角色/概念:**  
    * 用户可以训练特定角色的LoRA，以实现跨图像的完美一致性，这在故事叙述和系列创作中至关重要 76。  
  * **功能/修复:**  
    * SameFace Fix: 旨在解决基础模型在生成人物时容易出现的“千人一面”（sameface）问题，增加面部多样性 72。  
    * Anti-Blur: 锐化背景，对抗Flux模型有时产生的过度焦外模糊（Bokeh）效果 72。  
* 训练你自己的LoRA:  
  对于需要高度一致性的特定角色或风格，训练自定义LoRA是最佳解决方案。基本流程如下 78：  
  1. **准备数据集:** 收集15-30张高质量、高分辨率（建议1024x1024）且多样化（不同姿势、表情、光照）的训练图像。  
  2. **图像标注:** 为每张图片编写详细的描述性标题（caption），并设定一个独特的触发词（trigger word），如ohwxman。  
  3. **在线训练:** 使用Civitai或Replicate等平台提供的在线LoRA训练器，上传数据集，设置训练参数（如步数，通常1000-1500步），然后开始训练。  
  4. **测试与应用:** 训练完成后，下载LoRA文件，在提示词中包含你的触发词来调用你训练好的角色或风格。

### **5.2 基准测试：Flux.1与Midjourney、DALL-E 3、SDXL的对比**

为了客观评估Flux.1的性能，下表将其与当前主流模型在几个关键维度上进行了对比，综合了多项测试的结果。

**表4：Flux.1与主要竞品特性矩阵**

| 特性 | FLUX.1 | Midjourney v6 | DALL-E 3 | SDXL |
| :---- | :---- | :---- | :---- | :---- |
| **复杂提示词遵循度** | 卓越 | 良好 | 较好 | 一般 |
| **写实主义与解剖学** | 卓越 | 优秀（偏风格化） | 良好（偶有错误） | 良好（依赖微调） |
| **图像内文字渲染** | 卓越 | 差 | 较差 | 差 |
| **艺术风格多样性** | 优秀 | 卓越（艺术感强） | 良好 | 极高（依赖微调） |
| **图像编辑能力(I2I)** | 卓越 (Kontext) | 良好 | 有限 | 良好 |
| **开放性与定制化** | 极高 | 无（封闭） | 无（封闭） | 极高 |

**分析概要:**

* **提示词遵循度与文字渲染:** 这是Flux.1最显著的优势。它能够精确理解并执行包含复杂空间关系、多主体互动和长段文字的提示词，而竞争对手在这些方面常常出现遗漏或错误 79。  
* **写实主义:** Flux.1生成的写实图像在细节和解剖学准确性上通常优于DALL-E 3和基础SDXL。Midjourney虽然也能生成逼真的图像，但其输出往往带有一种独特的、经过美化的“MJ风格” 5。  
* **艺术性与灵活性:** Midjourney以其强大的艺术表现力和创造意外惊喜的能力而闻名，非常适合寻求艺术灵感的用户 5。而Flux.1和SDXL作为开源模型，通过庞大的LoRA和微调模型生态系统，提供了无与伦比的风格定制能力 24。  
* **编辑能力:** FLUX.1 Kontext提供了目前开源模型中最强大的原生图像编辑能力，尤其是在角色一致性方面，远超其他模型 14。

### **5.3 常见挑战与专家解决方案**

尽管Flux.1性能强大，但在使用过程中仍可能遇到一些问题。了解这些局限性并掌握相应的解决方法至关重要。

* **问题：图像模糊**  
  * **原因:** 最常见的原因是在\[dev\]模型中使用了“white background”提示词 28。此外，过低的推理步数或不合适的采样器也可能导致模糊。  
  * **解决方案:** 避免使用“white background”，改用“clean design”或增加质量词 28。增加推理步数（对于  
    dev模型，建议20-40步）。在ComfyUI中，尝试使用dpmpp\_2m或deis等采样器，避免使用某些可能导致模糊的DPM++系列采样器 82。  
* **问题：角色一致性失败**  
  * **原因:** 过于复杂的场景描述可能会分散模型对角色核心特征的注意力。在I2I编辑中，不恰当的动词（如“transform”）或模糊的指代（如“her”）也可能导致身份漂移 44。  
  * **解决方案:** 简化提示词，将重点放在角色描述上。在I2I中，使用明确的指令，如“Change the clothes to...”而非“Transform the person into...”，并明确指出要保留的特征 44。对于长期项目，最佳解决方案是训练一个该角色的专用LoRA 78。  
* **问题：风格僵化与纹理单一**  
  * **原因:** Flux.1基础模型有一种内在的“Flux风格”，倾向于生成干净、高对比度、有时略带过饱和的图像，并且难以生成“丑陋”、“破损”或“肮脏”的纹理 83。  
  * **解决方案:** 降低guidance\_scale值（如1.3-1.75），给予模型更多自由度来偏离其默认风格 84。使用专门的风格LoRA，如胶片、复古或特定艺术风格的LoRA，来覆盖基础模型的风格偏好 70。  
* **问题：解剖学错误**  
  * **原因:** 尽管已大为改善，但Flux.1偶尔仍会生成解剖学上不完美的手部，例如手指过长 85。  
  * **解决方案:** 在提示词中更详细地描述手部（如“beautiful hands”、“detailed fingers”）。使用ComfyUI中的FaceDetailer或类似的手部修复节点进行后处理。如果问题持续存在，可以尝试使用负向提示词排除“deformed hands”等。

## **第六部分：结论与未来展望**

### **6.1 综合评定：Flux.1的核心优势**

Flux.1的问世不仅是开源社区的一次胜利，更是AI图像生成技术发展道路上的一个重要节点。它通过一系列关键创新，成功地将闭源商业模型的顶尖质量与开源生态的无限灵活性结合在一起。

其核心优势可以归结为以下几点：

1. **架构上的突破:** 创新的双文本编码器架构，从根本上解决了长期困扰扩散模型的“指令脱节”问题，实现了对自然语言前所未有的深度理解和精确执行。  
2. **质量上的标杆:** 在提示词遵循度、写实主义细节和图像内文字生成等多个关键维度上，Flux.1树立了新的行业标杆，其表现足以挑战甚至超越最优秀的闭源模型。  
3. **生态上的活力:** 围绕Flux.1迅速形成的庞大社区生态，包括各种量化版本、功能强大的LoRA、ControlNet以及先进的ComfyUI工作流，共同构成了其强大生命力的源泉。它不仅是一个工具，更是一个充满活力的创作平台。

### **6.2 生成式AI的前路展望**

Flux.1的成功也揭示了未来生成式AI发展的几个重要趋势：

* **从“生成”到“交互”:** 以Kontext为代表的上下文感知编辑模型预示着，未来的AI工具将不再是简单的“提示-输出”机器，而是能够与用户进行多轮、有状态对话的智能创作伙伴。迭代式编辑将成为主流。  
* **语言理解的深化:** 对高质量文本编码器的重视将成为主流。未来的模型竞争将不仅是视觉质量的竞争，更是对人类语言细微之处理解能力的竞争。  
* **官方与社区的共生:** Flux.1的模式——由顶尖团队发布强大的基础模型，再由全球社区进行快速的创新、优化和扩展——将被证明是推动技术进步和应用普及的最有效路径。官方提供“引擎”，社区则为其装上“各种轮子”，共同驱动整个领域向前发展。

总而言之，Flux.1不仅是当下最强大的开源图像生成工具之一，更是一位重要的引路者，为我们描绘了下一代生成式AI的清晰蓝图。

#### **引用的著作**

1. Demystifying Flux Architecture \- arXiv, 访问时间为 八月 8, 2025， [https://arxiv.org/html/2507.09595v1](https://arxiv.org/html/2507.09595v1)  
2. Flux (text-to-image model) \- Wikipedia, 访问时间为 八月 8, 2025， [https://en.wikipedia.org/wiki/Flux\_(text-to-image\_model)](https://en.wikipedia.org/wiki/Flux_\(text-to-image_model\))  
3. Black Forest Labs' Flux.1 Outperforms Top Text-to-Image Models \- DeepLearning.AI, 访问时间为 八月 8, 2025， [https://www.deeplearning.ai/the-batch/black-forest-labs-flux-1-outperforms-top-text-to-image-models/](https://www.deeplearning.ai/the-batch/black-forest-labs-flux-1-outperforms-top-text-to-image-models/)  
4. Comparing Flux.1 and Stable Diffusion \- A Technical Deep Dive \- E2E Networks, 访问时间为 八月 8, 2025， [https://www.e2enetworks.com/blog/comparing-flux-1-and-stable-diffusion---a-technical-deep-dive](https://www.e2enetworks.com/blog/comparing-flux-1-and-stable-diffusion---a-technical-deep-dive)  
5. Flux AI vs. MidJourney: Which AI Tool is Best for Your Needs \- Institute of Ai Studies, 访问时间为 八月 8, 2025， [https://www.instituteofaistudies.com/insights/flux-ai-vs-midjourney](https://www.instituteofaistudies.com/insights/flux-ai-vs-midjourney)  
6. Flux.1 ComfyUI Guide, workflow and example, 访问时间为 八月 8, 2025， [https://comfyui-wiki.com/en/tutorial/advanced/flux1-comfyui-guide-workflow-and-examples](https://comfyui-wiki.com/en/tutorial/advanced/flux1-comfyui-guide-workflow-and-examples)  
7. FLUX.1 Kontext: Flow Matching for In-Context Image Generation and Editing in Latent Space \- arXiv, 访问时间为 八月 8, 2025， [https://arxiv.org/html/2506.15742v2](https://arxiv.org/html/2506.15742v2)  
8. \[2507.09595\] Demystifying Flux Architecture \- arXiv, 访问时间为 八月 8, 2025， [https://www.arxiv.org/abs/2507.09595](https://www.arxiv.org/abs/2507.09595)  
9. Discover the Power of FLUX Models: Tools, Pro, Dev, and Schnell Explained \- Eachlabs, 访问时间为 八月 8, 2025， [https://www.eachlabs.ai/blog/discover-the-power-of-flux-models-tools-pro-dev-and-schnell-explained](https://www.eachlabs.ai/blog/discover-the-power-of-flux-models-tools-pro-dev-and-schnell-explained)  
10. Comparing FLUX Models: Pro, Dev, and Schnell Explained, 访问时间为 八月 8, 2025， [https://stockimg.ai/blog/ai-and-technology/what-is-flux-and-models-comparison](https://stockimg.ai/blog/ai-and-technology/what-is-flux-and-models-comparison)  
11. black-forest-labs/FLUX.1-dev \- Hugging Face, 访问时间为 八月 8, 2025， [https://huggingface.co/black-forest-labs/FLUX.1-dev](https://huggingface.co/black-forest-labs/FLUX.1-dev)  
12. black-forest-labs/FLUX.1-schnell \- Hugging Face, 访问时间为 八月 8, 2025， [https://huggingface.co/black-forest-labs/FLUX.1-schnell](https://huggingface.co/black-forest-labs/FLUX.1-schnell)  
13. FLUX.1 Kontext's Consistent Characters, Benchmarking Costs Climb, and more... \- DeepLearning.AI, 访问时间为 八月 8, 2025， [https://www.deeplearning.ai/the-batch/issue-305/](https://www.deeplearning.ai/the-batch/issue-305/)  
14. Black Forest Labs \- Frontier AI Lab, 访问时间为 八月 8, 2025， [https://bfl.ai/](https://bfl.ai/)  
15. black-forest-labs/FLUX.1-Fill-dev \- Hugging Face, 访问时间为 八月 8, 2025， [https://huggingface.co/black-forest-labs/FLUX.1-Fill-dev](https://huggingface.co/black-forest-labs/FLUX.1-Fill-dev)  
16. black-forest-labs/FLUX.1-Redux-dev \- Hugging Face, 访问时间为 八月 8, 2025， [https://huggingface.co/black-forest-labs/FLUX.1-Redux-dev](https://huggingface.co/black-forest-labs/FLUX.1-Redux-dev)  
17. FLUX.1-dev Model by Black-forest-labs \- NVIDIA NIM APIs, 访问时间为 八月 8, 2025， [https://build.nvidia.com/black-forest-labs/flux\_1-dev/modelcard](https://build.nvidia.com/black-forest-labs/flux_1-dev/modelcard)  
18. black-forest-labs/FLUX.1-Krea-dev \- Hugging Face, 访问时间为 八月 8, 2025， [https://huggingface.co/black-forest-labs/FLUX.1-Krea-dev](https://huggingface.co/black-forest-labs/FLUX.1-Krea-dev)  
19. Flux.1 Krea Dev ComfyUI Workflow Tutorial, 访问时间为 八月 8, 2025， [https://docs.comfy.org/tutorials/flux/flux1-krea-dev](https://docs.comfy.org/tutorials/flux/flux1-krea-dev)  
20. GGUF Quantization support for native ComfyUI models \- GitHub, 访问时间为 八月 8, 2025， [https://github.com/city96/ComfyUI-GGUF](https://github.com/city96/ComfyUI-GGUF)  
21. Introducing FLUX.1 Kontext and the BFL Playground \- Black Forest Labs, 访问时间为 八月 8, 2025， [https://bfl.ai/announcements/flux-1-kontext](https://bfl.ai/announcements/flux-1-kontext)  
22. FLUX.1 Prompt Guide: Pro Tips and Common Mistakes to Avoid | getimg.ai, 访问时间为 八月 8, 2025， [https://getimg.ai/blog/flux-1-prompt-guide-pro-tips-and-common-mistakes-to-avoid](https://getimg.ai/blog/flux-1-prompt-guide-pro-tips-and-common-mistakes-to-avoid)  
23. FLUX.1 Prompt Manual: A Foundational Guide : r/FluxAI \- Reddit, 访问时间为 八月 8, 2025， [https://www.reddit.com/r/FluxAI/comments/1imha0t/flux1\_prompt\_manual\_a\_foundational\_guide/](https://www.reddit.com/r/FluxAI/comments/1imha0t/flux1_prompt_manual_a_foundational_guide/)  
24. Flux vs. SDXL. Agree or disagree....? : r/StableDiffusion \- Reddit, 访问时间为 八月 8, 2025， [https://www.reddit.com/r/StableDiffusion/comments/1im6ycd/flux\_vs\_sdxl\_agree\_or\_disagree/](https://www.reddit.com/r/StableDiffusion/comments/1im6ycd/flux_vs_sdxl_agree_or_disagree/)  
25. Flux.1 Kontext Prompting Guide \- YouTube, 访问时间为 八月 8, 2025， [https://www.youtube.com/watch?v=RXzeRfvH3\_w](https://www.youtube.com/watch?v=RXzeRfvH3_w)  
26. FLUX.1 \[dev\] \- a Hugging Face Space by black-forest-labs, 访问时间为 八月 8, 2025， [https://huggingface.co/spaces/black-forest-labs/FLUX.1-dev](https://huggingface.co/spaces/black-forest-labs/FLUX.1-dev)  
27. Comparative Analysis of Image Resolutions with FLUX-1.dev Model : r/StableDiffusion, 访问时间为 八月 8, 2025， [https://www.reddit.com/r/StableDiffusion/comments/1ejr20p/comparative\_analysis\_of\_image\_resolutions\_with/](https://www.reddit.com/r/StableDiffusion/comments/1ejr20p/comparative_analysis_of_image_resolutions_with/)  
28. FLUX.1 Generating Blurry Images? Here's How to Fix It | getimg.ai, 访问时间为 八月 8, 2025， [https://getimg.ai/blog/flux-1-generating-blurry-images-heres-how-to-fix-it](https://getimg.ai/blog/flux-1-generating-blurry-images-heres-how-to-fix-it)  
29. Master Negative Prompts in FLUX: A Comprehensive Guide \- Merlio, 访问时间为 八月 8, 2025， [https://merlio.app/blog/negative-prompts-in-flux-guide](https://merlio.app/blog/negative-prompts-in-flux-guide)  
30. FLUX.1: Prompt Guide for Beginners \- LaPrompt Blog, 访问时间为 八月 8, 2025， [https://blog.laprompt.com/ai-news/flux1-prompt-guide-for-beginners](https://blog.laprompt.com/ai-news/flux1-prompt-guide-for-beginners)  
31. Top 10 Prompts for Flux.1: Master the Art of AI \- AI/ML Blog \- AIML API, 访问时间为 八月 8, 2025， [https://aimlapi.com/blog/master-the-art-of-ai-top-10-prompts-for-flux-1-by-black-forests-labs](https://aimlapi.com/blog/master-the-art-of-ai-top-10-prompts-for-flux-1-by-black-forests-labs)  
32. Creating images with Flux: Your prompt guide \- Nebius, 访问时间为 八月 8, 2025， [https://nebius.com/blog/posts/creating-images-with-flux-prompt-guide](https://nebius.com/blog/posts/creating-images-with-flux-prompt-guide)  
33. How to Best Flux 1 Prompts for Anime Character | Enhance AI, 访问时间为 八月 8, 2025， [https://enhanceai.art/blogs/top-10-best-flux-1-prompts-anime-character](https://enhanceai.art/blogs/top-10-best-flux-1-prompts-anime-character)  
34. Best Prompts of Flux.1 AI for Flux Images — July 20, 2025 | flux-ai.io, 访问时间为 八月 8, 2025， [https://flux-ai.io/blog/detail/Best-Prompts-of-Flux1-AI-for-Flux-Images-%E2%80%94-July-20-2025-055a17283ee3/](https://flux-ai.io/blog/detail/Best-Prompts-of-Flux1-AI-for-Flux-Images-%E2%80%94-July-20-2025-055a17283ee3/)  
35. Best Flux.1 Prompts: Create Breathtaking Images with Ease, 访问时间为 八月 8, 2025， [https://blog.segmind.com/best-flux-1-prompts/](https://blog.segmind.com/best-flux-1-prompts/)  
36. k-mktr/improved-flux-prompts · Datasets at Hugging Face, 访问时间为 八月 8, 2025， [https://huggingface.co/datasets/k-mktr/improved-flux-prompts](https://huggingface.co/datasets/k-mktr/improved-flux-prompts)  
37. FLUX.1 Graphic Design Use Cases: Pushing Creative Boundaries with AI | getimg.ai, 访问时间为 八月 8, 2025， [https://getimg.ai/blog/flux-1-graphic-design-use-cases-pushing-creative-boundaries-with-ai](https://getimg.ai/blog/flux-1-graphic-design-use-cases-pushing-creative-boundaries-with-ai)  
38. Flux 1 Prompts for Logo Design | Enhance AI, 访问时间为 八月 8, 2025， [https://enhanceai.art/blogs/flux-ai-prompts-logo-design](https://enhanceai.art/blogs/flux-ai-prompts-logo-design)  
39. Top 5 Flux Prompts for Realistic Design | Enhance AI, 访问时间为 八月 8, 2025， [https://enhanceai.art/blogs/top-5-flux-prompts-for-realistic-design](https://enhanceai.art/blogs/top-5-flux-prompts-for-realistic-design)  
40. Prompting Guide \- Image-to-Image \- Black Forest Labs, 访问时间为 八月 8, 2025， [https://docs.bfl.ai/guides/prompting\_guide\_kontext\_i2i](https://docs.bfl.ai/guides/prompting_guide_kontext_i2i)  
41. How to Keep Your AI Characters Consistent Using FLUX AI \- YouTube, 访问时间为 八月 8, 2025， [https://www.youtube.com/watch?v=tqn4TJqi0AM](https://www.youtube.com/watch?v=tqn4TJqi0AM)  
42. How to Style Transfer using Flux Kontext \- YouTube, 访问时间为 八月 8, 2025， [https://www.youtube.com/watch?v=7bJX5pwPdxo](https://www.youtube.com/watch?v=7bJX5pwPdxo)  
43. FLUX.1 Kontext \[pro\] | Image to Image \- Fal.ai, 访问时间为 八月 8, 2025， [https://fal.ai/models/fal-ai/flux-pro/kontext](https://fal.ai/models/fal-ai/flux-pro/kontext)  
44. Usage Guide: FLUX.1 Kontext Image Editing \- NightCafe Studio, 访问时间为 八月 8, 2025， [https://help.nightcafe.studio/portal/en/kb/articles/usage-guide-flux-1-kontext-image-editing](https://help.nightcafe.studio/portal/en/kb/articles/usage-guide-flux-1-kontext-image-editing)  
45. Use FLUX.1 Kontext to edit images with words – Replicate blog, 访问时间为 八月 8, 2025， [https://replicate.com/blog/flux-kontext](https://replicate.com/blog/flux-kontext)  
46. FLUX.1 \[dev\] Image-to-Image Editing | AI Image Editor | fal.ai, 访问时间为 八月 8, 2025， [https://fal.ai/models/fal-ai/flux/dev/image-to-image](https://fal.ai/models/fal-ai/flux/dev/image-to-image)  
47. CFG Scale vs Denoising Strength Explained : r/StableDiffusion \- Reddit, 访问时间为 八月 8, 2025， [https://www.reddit.com/r/StableDiffusion/comments/1bs4lg9/cfg\_scale\_vs\_denoising\_strength\_explained/](https://www.reddit.com/r/StableDiffusion/comments/1bs4lg9/cfg_scale_vs_denoising_strength_explained/)  
48. What is denoising strength? \- Stable Diffusion Art, 访问时间为 八月 8, 2025， [https://stable-diffusion-art.com/denoising-strength/](https://stable-diffusion-art.com/denoising-strength/)  
49. flux \- image to image @ComfyUI : r/StableDiffusion \- Reddit, 访问时间为 八月 8, 2025， [https://www.reddit.com/r/StableDiffusion/comments/1ei7ffl/flux\_image\_to\_image\_comfyui/](https://www.reddit.com/r/StableDiffusion/comments/1ei7ffl/flux_image_to_image_comfyui/)  
50. How to use Flux.1 Fill model for inpainting \- Stable Diffusion Art, 访问时间为 八月 8, 2025， [https://stable-diffusion-art.com/flux1-fill-inpaint/](https://stable-diffusion-art.com/flux1-fill-inpaint/)  
51. Multi-Image Flux Kontext Dev Workflows in ComfyUI \- Next Diffusion, 访问时间为 八月 8, 2025， [https://www.nextdiffusion.ai/tutorials/flux-kontext-dev-multi-image-workflows-comfyui](https://www.nextdiffusion.ai/tutorials/flux-kontext-dev-multi-image-workflows-comfyui)  
52. How To Use Multi-Image In FLUX Kontext (ComfyUI) \- YouTube, 访问时间为 八月 8, 2025， [https://www.youtube.com/watch?v=kqbqKGBqf8s](https://www.youtube.com/watch?v=kqbqKGBqf8s)  
53. ComfyUI Flux Kontext Dev Native Workflow Example, 访问时间为 八月 8, 2025， [https://docs.comfy.org/tutorials/flux/flux-1-kontext-dev](https://docs.comfy.org/tutorials/flux/flux-1-kontext-dev)  
54. Flux Examples | ComfyUI\_examples \- GitHub Pages, 访问时间为 八月 8, 2025， [https://comfyanonymous.github.io/ComfyUI\_examples/flux/](https://comfyanonymous.github.io/ComfyUI_examples/flux/)  
55. ComfyUI Flux.1 Text-to-Image Workflow Example, 访问时间为 八月 8, 2025， [https://docs.comfy.org/tutorials/flux/flux-1-text-to-image](https://docs.comfy.org/tutorials/flux/flux-1-text-to-image)  
56. Free ComfyUI Workflow to Upscale & AI Enhance Your Images\! Hope you enjoy clean workflows \- Reddit, 访问时间为 八月 8, 2025， [https://www.reddit.com/r/comfyui/comments/1h4tqru/free\_comfyui\_workflow\_to\_upscale\_ai\_enhance\_your/](https://www.reddit.com/r/comfyui/comments/1h4tqru/free_comfyui_workflow_to_upscale_ai_enhance_your/)  
57. ComfyUI Face Detailer \- Learn Think Diffusion, 访问时间为 八月 8, 2025， [https://learn.thinkdiffusion.com/comfyui-face-detailer/](https://learn.thinkdiffusion.com/comfyui-face-detailer/)  
58. ltdrdata/ComfyUI-Impact-Pack: Custom nodes pack for ComfyUI This custom node helps to conveniently enhance images through Detector, Detailer, Upscaler, Pipe, and more. \- GitHub, 访问时间为 八月 8, 2025， [https://github.com/ltdrdata/ComfyUI-Impact-Pack](https://github.com/ltdrdata/ComfyUI-Impact-Pack)  
59. Flux.1 Dev ControlNet Upscaler | ComfyUI Workflow \- OpenArt, 访问时间为 八月 8, 2025， [https://openart.ai/workflows/ailab/flux1-dev-controlnet-upscaler/zYap54CA62AZNrX7Mxxs](https://openart.ai/workflows/ailab/flux1-dev-controlnet-upscaler/zYap54CA62AZNrX7Mxxs)  
60. ComfyUI: Flux with LLM, 5x Upscale Part 1 (Workflow Tutorial) \- YouTube, 访问时间为 八月 8, 2025， [https://www.youtube.com/watch?v=6ZUJ18wR\_Bo](https://www.youtube.com/watch?v=6ZUJ18wR_Bo)  
61. How To Use Flux 1 Dev ControlNet Upscaler In ComfyUI \- A Simple And Easy Way, 访问时间为 八月 8, 2025， [https://www.youtube.com/watch?v=dJwZ1\_cm-Ks](https://www.youtube.com/watch?v=dJwZ1_cm-Ks)  
62. Flux and Face Detailer : r/StableDiffusion \- Reddit, 访问时间为 八月 8, 2025， [https://www.reddit.com/r/StableDiffusion/comments/1euz0h8/flux\_and\_face\_detailer/](https://www.reddit.com/r/StableDiffusion/comments/1euz0h8/flux_and_face_detailer/)  
63. Simple Flux.1 \+ Lora \+ Updetailer \+ Face Swap \+ Face Detailer Workflow \- OpenArt, 访问时间为 八月 8, 2025， [https://openart.ai/workflows/javawock7618/simple-flux1-lora-updetailer-face-swap-face-detailer-workflow/zrQAxxA7gmgxqtQRMCH5](https://openart.ai/workflows/javawock7618/simple-flux1-lora-updetailer-face-swap-face-detailer-workflow/zrQAxxA7gmgxqtQRMCH5)  
64. XLabs-AI/x-flux-comfyui \- GitHub, 访问时间为 八月 8, 2025， [https://github.com/XLabs-AI/x-flux-comfyui](https://github.com/XLabs-AI/x-flux-comfyui)  
65. Ling-APE/ComfyUI-All-in-One-FluxDev-Workflow \- GitHub, 访问时间为 八月 8, 2025， [https://github.com/Ling-APE/ComfyUI-All-in-One-FluxDev-Workflow](https://github.com/Ling-APE/ComfyUI-All-in-One-FluxDev-Workflow)  
66. black-forest-labs/FLUX.1-Canny-dev-lora \- Hugging Face, 访问时间为 八月 8, 2025， [https://huggingface.co/black-forest-labs/FLUX.1-Canny-dev-lora](https://huggingface.co/black-forest-labs/FLUX.1-Canny-dev-lora)  
67. alimama-creative/FLUX-Controlnet-Inpainting \- GitHub, 访问时间为 八月 8, 2025， [https://github.com/alimama-creative/FLUX-Controlnet-Inpainting](https://github.com/alimama-creative/FLUX-Controlnet-Inpainting)  
68. How to Use LoRA with FLUX AI: A Comprehensive Guide | by Amdad H | Towards AGI, 访问时间为 八月 8, 2025， [https://medium.com/towards-agi/how-to-use-lora-with-flux-ai-a-comprehensive-guide-5adff95271b4](https://medium.com/towards-agi/how-to-use-lora-with-flux-ai-a-comprehensive-guide-5adff95271b4)  
69. XLabs-AI/flux-lora-collection \- Hugging Face, 访问时间为 八月 8, 2025， [https://huggingface.co/XLabs-AI/flux-lora-collection](https://huggingface.co/XLabs-AI/flux-lora-collection)  
70. FLUX Realism LORAs \- What's Working for YOU? : r/StableDiffusion \- Reddit, 访问时间为 八月 8, 2025， [https://www.reddit.com/r/StableDiffusion/comments/1hu4dp6/flux\_realism\_loras\_whats\_working\_for\_you/](https://www.reddit.com/r/StableDiffusion/comments/1hu4dp6/flux_realism_loras_whats_working_for_you/)  
71. Flux UltraRealistic LoRA V2: Lifelike AI Images \- RunComfy, 访问时间为 八月 8, 2025， [https://www.runcomfy.com/comfyui-workflows/flux-ultrarealistic-lora-v2-lifelike-ai-images](https://www.runcomfy.com/comfyui-workflows/flux-ultrarealistic-lora-v2-lifelike-ai-images)  
72. "Best" Flux Loras? : r/StableDiffusion \- Reddit, 访问时间为 八月 8, 2025， [https://www.reddit.com/r/StableDiffusion/comments/1g0i1zx/best\_flux\_loras/](https://www.reddit.com/r/StableDiffusion/comments/1g0i1zx/best_flux_loras/)  
73. Nishitbaria/LoRa-Flux-Anime-Style \- Hugging Face, 访问时间为 八月 8, 2025， [https://huggingface.co/Nishitbaria/LoRa-Flux-Anime-Style](https://huggingface.co/Nishitbaria/LoRa-Flux-Anime-Style)  
74. I trained an (anime) aesthetic LoRA for Flux : r/StableDiffusion \- Reddit, 访问时间为 八月 8, 2025， [https://www.reddit.com/r/StableDiffusion/comments/1enuib1/i\_trained\_an\_anime\_aesthetic\_lora\_for\_flux/](https://www.reddit.com/r/StableDiffusion/comments/1enuib1/i_trained_an_anime_aesthetic_lora_for_flux/)  
75. What is your favorite Lora's on Flux 1D? : r/FluxAI \- Reddit, 访问时间为 八月 8, 2025， [https://www.reddit.com/r/FluxAI/comments/1i8fcuk/what\_is\_your\_favorite\_loras\_on\_flux\_1d/](https://www.reddit.com/r/FluxAI/comments/1i8fcuk/what_is_your_favorite_loras_on_flux_1d/)  
76. ComfyUI Tutorial Series Ep 28: Create Consistent Characters with Flux \+ Train Loras Online, 访问时间为 八月 8, 2025， [https://www.youtube.com/watch?v=n\_x44pTLpak\&pp=0gcJCfwAo7VqN5tD](https://www.youtube.com/watch?v=n_x44pTLpak&pp=0gcJCfwAo7VqN5tD)  
77. FLUX Character Lora Guide \- Help with settings : r/civitai \- Reddit, 访问时间为 八月 8, 2025， [https://www.reddit.com/r/civitai/comments/1hvqlpi/flux\_character\_lora\_guide\_help\_with\_settings/](https://www.reddit.com/r/civitai/comments/1hvqlpi/flux_character_lora_guide_help_with_settings/)  
78. Fine-Tune FLUX.1 for Consistent Character Generation | by Richárd ..., 访问时间为 八月 8, 2025， [https://pub.towardsai.net/fine-tune-flux-1-for-consistent-character-generation-2af7731c91e1](https://pub.towardsai.net/fine-tune-flux-1-for-consistent-character-generation-2af7731c91e1)  
79. FLUX.1 vs Midjourney: Text to Image AI Showdown | getimg.ai, 访问时间为 八月 8, 2025， [https://getimg.ai/blog/flux-1-vs-midjourney-ultimate-text-to-image-ai-showdown](https://getimg.ai/blog/flux-1-vs-midjourney-ultimate-text-to-image-ai-showdown)  
80. FLUX vs MidJourney vs DALL·E vs Stable Diffusion: Which AI Image Generator Should You Choose? | by Amdad H | Towards AGI | Medium, 访问时间为 八月 8, 2025， [https://medium.com/towards-agi/flux-vs-midjourney-vs-dall-e-vs-stable-diffusion-which-ai-image-generator-should-you-choose-30e35c3c680c](https://medium.com/towards-agi/flux-vs-midjourney-vs-dall-e-vs-stable-diffusion-which-ai-image-generator-should-you-choose-30e35c3c680c)  
81. FLUX.1 vs DALL-E 3: What is the Best AI Text to Image Model? | getimg.ai, 访问时间为 八月 8, 2025， [https://getimg.ai/blog/flux-1-vs-dall-e-3-what-is-the-best-ai-text-to-image-model](https://getimg.ai/blog/flux-1-vs-dall-e-3-what-is-the-best-ai-text-to-image-model)  
82. What is your experience with Flux so far? : r/FluxAI \- Reddit, 访问时间为 八月 8, 2025， [https://www.reddit.com/r/FluxAI/comments/1f82x5p/what\_is\_your\_experience\_with\_flux\_so\_far/](https://www.reddit.com/r/FluxAI/comments/1f82x5p/what_is_your_experience_with_flux_so_far/)  
83. Things Flux Does Poorly? : r/StableDiffusion \- Reddit, 访问时间为 八月 8, 2025， [https://www.reddit.com/r/StableDiffusion/comments/1eyito9/things\_flux\_does\_poorly/](https://www.reddit.com/r/StableDiffusion/comments/1eyito9/things_flux_does_poorly/)  
84. Things I can't get on Flux generated pictures, no matter how I try : r/StableDiffusion \- Reddit, 访问时间为 八月 8, 2025， [https://www.reddit.com/r/StableDiffusion/comments/1geccgh/things\_i\_cant\_get\_on\_flux\_generated\_pictures\_no/](https://www.reddit.com/r/StableDiffusion/comments/1geccgh/things_i_cant_get_on_flux_generated_pictures_no/)  
85. List of issues with Flux : r/FluxAI \- Reddit, 访问时间为 八月 8, 2025， [https://www.reddit.com/r/FluxAI/comments/1ex6mki/list\_of\_issues\_with\_flux/](https://www.reddit.com/r/FluxAI/comments/1ex6mki/list_of_issues_with_flux/)