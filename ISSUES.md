## 项目问题清单 (Issue List)

记录项目运行中的已知问题、根因、规避/修复方案与验证步骤，便于后续快速对照排查。

### 使用方式
- 新增问题时，复制下方“问题模板”，按实际情况填写。
- 为每个问题分配唯一编号，例如 Issue-0002、Issue-0003。
- 建议每次修复后补充“验证清单”与“修复版本”。

### 索引
- Issue-0001: 首页卡在“正在加载”（转圈）

---

### Issue-0001: 首页卡在“正在加载”（转圈）
- 编号: Issue-0001
- 状态: 已定位，已有规避方案
- 严重级别: 中
- 首次发现版本: a4e9d48
- 受影响版本: a4e9d48（以及任何包含同样引用但未提供定义的版本）
- 已知稳定版本: 5272915
- 关联提交: 5272915, a4e9d48

#### 现象
- 进入首页后，页面一直显示“正在加载”，无法正常展示工作流列表。

#### 复现步骤
1. 切换到提交 a4e9d48。
2. 启动服务并打开首页。
3. 页面停留在加载态；浏览器控制台可见报错。

#### 期望/实际
- 期望: 首页正常初始化并展示工作流入口。
- 实际: 页面初始化中断，停在加载转圈。

#### 根因分析
- 在 a4e9d48 的 `static/js/app.js` 中新增了对 `PromptTemplates` 的实例化：

```text
this.promptTemplates = new PromptTemplates();
```

- 但代码库中不存在 `PromptTemplates` 类定义（未找到 `class PromptTemplates` 或相关导入）。
- 运行时触发 `ReferenceError: PromptTemplates is not defined`，使应用初始化流程中断，导致页面卡住。

#### 影响面
- 首页初始化流程（`ComfyWebApp` 构造与后续初始化）被异常中止。

#### 临时规避
- 回退到稳定版本 `5272915`：

```bash
git reset --hard 5272915
```

- 或在问题版本中移除对 `PromptTemplates` 的直接引用与依赖调用，确保无未定义符号。

#### 永久修复建议
- 方案A：真正引入 `PromptTemplates` 模块（例如新增 `static/js/prompt-templates.js` 并在页面中加载），确保类定义与使用一致；
- 方案B：为模板相关能力做特性探测与懒加载，所有调用前增加存在性校验与降级路径；
- 方案C：如短期不需要该功能，彻底移除 `PromptTemplates` 的实例化与依赖方法（如模板分类/随机模板等 UI）。

#### 验证清单
- [ ] 首页能够正常渲染，不再停留在加载态；
- [ ] 浏览器控制台无 `ReferenceError` 或未定义类/函数报错；
- [ ] 模板管理相关入口（如仍保留）可正常显示或优雅降级；
- [ ] 主要交互（加载工作流、生成、切换模式）均正常。

#### 旁证与命令
- 差异对比（示例）：

```bash
git diff 5272915..a4e9d48 -- static/js/app.js
```

- 搜索未定义类：

```bash
rg "class\s+PromptTemplates|PromptTemplates\W" static/js
```

---

### 问题模板（复制使用）

```markdown
### Issue-XXXX: <简要标题>
- 编号: Issue-XXXX
- 状态: 待确认/处理中/已定位/已修复
- 严重级别: 低/中/高/致命
- 首次发现版本: <commit 或 tag>
- 受影响版本: <范围或列表>
- 已知稳定版本: <可回退版本>
- 关联提交: <提交哈希/PR/Issue 链接>

#### 现象
- <描述用户可见的表现>

#### 复现步骤
1. <步骤1>
2. <步骤2>
3. <步骤3>

#### 期望/实际
- 期望: <期望行为>
- 实际: <实际行为>

#### 根因分析
- <技术分析与定位结论>

#### 影响面
- <受影响模块/功能/用户群>

#### 临时规避
- <短期可落地的止血方案>

#### 永久修复建议
- <从架构/实现/流程上杜绝问题的方案>

#### 验证清单
- [ ] <验证点1>
- [ ] <验证点2>
- [ ] <验证点3>

#### 旁证与命令
```bash
<用于对照/排查的命令或日志位置>
```
```



## 2025-08-22 工作流页面卡死/图片选择不可用 - 诊断与修复

- 症状：
  - 首页“正在加载工作流...”转圈；
  - 进入工作流时报 `PromptTemplates is not defined`；
  - 进一步修复后，进入详情时报 `setDefaultValues is not a function`、`generateImageInputs is not a function`；
  - 弹出图片选择弹窗后，无图片且报 `this.loadImages is not a function`。

- 根因：
  - `static/js/app.js` 中存在一大段旧版内联提示词分组被误保留在类体外（早前），后续清理时又误删了多处必需方法；
  - 新增了对 `PromptTemplates` 的直接实例化，但仓库并未提供该类，导致初始化 ReferenceError；
  - 与图片选择相关的一系列方法缺失，导致弹窗功能不完整。

- 修复：
  1) 删除旧版内联分组，补齐“最近/最常用”方法：`getRecentShortcutGroup`、`getFrequentShortcutGroup`。
  2) 将 `PromptTemplates` 改为可选依赖：`this.promptTemplates = typeof PromptTemplates!=="undefined" ? new PromptTemplates() : null`，并保证调用前判空。
  3) 恢复与参数区相关的方法：`setDefaultValues`、`getDefaultValue`、`showAllConfigSections`。
  4) 恢复图片选择相关完整实现：
     - `generateImageInputs`、`generateImageInputHTML`、`generateCompactImageInputHTML`
     - `showImageSelectModal`、`hideImageSelectModal`、`startImageListAutoRefresh`、`stopImageListAutoRefresh`
     - `loadImages`、`showImageLoadingState`、`showImageLoadingError`、`renderImageTabs`、`renderImageGrid`
  5) 事件监听与UI：确保按钮点击与模态框交互均生效。

- 预防：
  - 大文件编辑前后务必运行 ESLint/基本功能自测；
  - 对可选模块使用前判空；
  - 移除大段旧代码时，检查是否连带删掉被调用的方法；
  - 为关键JS建立最小冒烟测试清单（首页加载、进入工作流、打开图片选择、应用快捷提示）。

- 备份：
  - 已创建备份目录 `backups/20250822_223355/`，包含：
    - `static/js/app.js`
    - `static/js/prompt-shortcuts.js`
    - `templates/prompt-manager.html`

