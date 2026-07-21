# 截图像素级复刻

## 核心规则

把参考像素和录制行为作为验收标准。页面只能使用原生 HTML、CSS 和 JavaScript。没有实际审计证据，不能声称 1:1 完成。

实现前必须把交付范围定义为 `visible_frame`（只复刻可见帧）或 `full_component`（完整组件）。被截图截断的区域不能证明隐藏内容，禁止补写不可见文案、控件、素材、状态或布局并把它们当作已验证还原。

实现前还要给依赖背景的像素分类。半透明前景如果已经和未知背景或不在实现范围内的背景合成，就可能无法从单张截图唯一反推，必须标记为 `non_identifiable`。这类区域保持严格 1:1 失败；现有证据无法判断唯一结果时，停止无效调参。

用户明确批准全局安装前，始终保持本地 Skill。不得在本地开发或审查阶段写入全局 Skill 目录。

## 必读文档

- 开始实现前阅读 [visual-analysis.zh-CN.md](references/visual-analysis.zh-CN.md)。
- 图层重叠、插画凸出、轮廓有凹口或组合关系，或者透明/阴影/模糊依赖背景时，阅读 [layer-topology-and-compositing.zh-CN.md](references/layer-topology-and-compositing.zh-CN.md)。
- 裁剪或抠图前阅读 [asset-extraction.zh-CN.md](references/asset-extraction.zh-CN.md)。
- 用户提供修改意见、标注截图或要求继续优化时，阅读 [feedback-iteration.zh-CN.md](references/feedback-iteration.zh-CN.md)。
- 输入包含 GIF 或录屏时阅读 [motion-reconstruction.zh-CN.md](references/motion-reconstruction.zh-CN.md)。
- 报告完成前阅读 [verification-gates.zh-CN.md](references/verification-gates.zh-CN.md)。

## 工作流

1. 盘点全部输入。运行 `scripts/analyze_reference.py`；GIF 和录屏还要运行 `scripts/extract_reference_frames.py`。
2. 定义交付范围，并把所有依赖背景的区域分类为 `recoverable`、`source_composited` 或 `non_identifiable`。
3. 创建中英双语视觉拆解、实现基线和 `VISUAL_MODEL.json`。写代码前登记所属容器、层级、裁切归属、凸出图层、最外轮廓成员、开口和禁止描边的内部接缝。
4. 创建 `REFERENCE_BASELINE.json`、`REFERENCE_COVERAGE.json`、`ASSET_LEDGER.json`、`STRUCTURE_AUDIT.json`、`AUDIT_MAP.json`、`INTERACTION_SCENARIOS.json` 和 `ITERATION_LEDGER.json`；按需增加可达性与动效规格。冻结 `core_scope` 的参考图、审计地图、范围蒙版、字体和素材哈希。
5. 运行 `validate_reference_coverage.py` 和 `validate_visual_model.py`。证据不完整时阻断 `full_component`；`non_identifiable` 区域阻断严格像素声明。
6. 使用参考图原始尺寸建立舞台。容器、卡片、实时文字、数值、描述、进度条、角标、按钮、状态和重复列表必须使用真实 DOM/CSS；需要复用时由数据驱动生成。
7. 图片只允许承载 CSS 无法忠实复现的独立图形，禁止同时带上周围卡片、文案、控件、进度、状态或布局容器。
8. 禁止使用整页、区块或卡片截图承载本可用代码实现的界面，禁止用截图覆盖层掩盖缺失实现。
9. 可复用前景必须抠成 RGBA 真透明素材，只生成 Alpha 并保留源 RGB，禁止烘焙棋盘格或网格。
10. 使用原生 JavaScript 实现状态和交互；审计时固定动态数据。登记真实滚动容器，禁止用装饰灰条冒充滚动能力。
11. 每次收到用户修改意见时，先把标记区域写入 `AUDIT_MAP.json`，截取当前实现作为修改前候选图，更新 `ITERATION_LEDGER.json`，再改代码。禁止改完后才补审计区域。
12. 动效页面提供 `window.__setAuditTime(milliseconds)`，按相同相对时间捕获每个登记帧。
13. 按需执行覆盖范围、视觉模型、结构、素材、可达性、浏览器、交互、像素、透明矩阵、响应式和逐帧审计。视觉迭代使用 `run_visual_audits.py --baseline-candidate`；`core_scope` 和 `expanded_scope` 指标分开报告。证据能够区分结果时才继续迭代，否则登记限制并保持严格失败。
14. 使用全部必需报告运行 `scripts/validate_delivery.py`。任意检查失败时写入 `passed: false` 并报告证据，不能声称完成。

## 硬门槛

- 全图平均绝对通道差：`< 2`。
- 每个登记区域：`< 2`。
- 每个关键元素：`< 2`。
- 每个动效帧：`< 2`。
- 所有凸出图层、裁切归属、最外轮廓成员、开口和排除的内部接缝都已登记到 `VISUAL_MODEL.json`。
- 每个用户标记问题都有正式区域、修改前候选图、当前候选图和同一冻结范围下的带正负号指标变化。
- 目标区域必须改善或已经通过；保护区域不得超过登记的回退额度。
- 参考图、审计地图、蒙版、字体、素材或视口哈希不同的指标不得串成一条趋势。
- `source_composited` 和 `non_identifiable` 区域保持证据受限；取得足够源材料前阻断严格 1:1 通过。
- P0 问题：`0`；P1 问题：`0`。
- 所有交互断言通过，浏览器没有未处理控制台错误或页面错误。
- `full_component` 证据完整，不存在部分、未知、推断或无依据的延续与必需字段。
- 所有静态登记文案完整可见且未被祖先裁剪；所有可滚列表行和必需控件都能通过登记的滚轮与触摸路径完整进入可视区。
- 首项和末项都可达，真实输入能改变登记滚动容器，固定内容不会跟随列表移动。
- 图片不得覆盖登记的实时文案区域；确有需要时必须在结构规格中明确登记并说明允许的选择器。
- 不存在把可复用界面结构、实时文字或状态合并进图片的素材。
- 不存在错误人物、错误素材、缺失模块、整页/区块/卡片截图背景或假透明素材。
- 不存在把截图边缘残缺碎片当作完整可复用素材的情况。

这是严格小于门槛；差异等于 `2` 也算失败。

## 快速索引

| 需求 | 工具或产物 |
|---|---|
| 源文件事实和色板 | `analyze_reference.py` |
| 图层、轮廓、裁切和透明合成合同 | `VISUAL_MODEL.json` + `validate_visual_model.py` |
| 可见帧/完整组件证据 | `validate_reference_coverage.py` |
| GIF/录屏完整帧 | `extract_reference_frames.py` |
| 保留源 RGB 的透明素材 | `extract_alpha_assets.py` |
| 透明边缘和 RGB 审计 | `validate_alpha_assets.py` |
| DOM 与图片职责边界 | `validate_implementation_structure.cjs` |
| 滚轮/触摸和末项可达性 | `validate_content_reachability.cjs` |
| 全图/区域/元素差异 | `run_visual_audits.py` |
| 修改前后回归变化 | `run_visual_audits.py --baseline-candidate` |
| 页面实际透明效果 | `capture_transparency_matrix.cjs` |
| 逐帧差异 | `compare_frame_sequence.py` |
| 浏览器截图 | `capture_preview.cjs` |
| 交互模拟 | `run_interaction_scenarios.cjs` |
| 可控时间轴截图 | `capture_interaction_frames.cjs` |
| 最终门禁 | `validate_delivery.py` |

使用 `--help` 查看每个脚本的准确命令参数。

## 常见失败

| 失败表现 | 必须采取的修正 |
|---|---|
| 只说“看起来接近”，没有差异报告 | 按源尺寸截图并生成像素证据。 |
| 流程对但画面结构错 | 重建素材账本，只保留源图派生的独立图形素材。 |
| 抠图带白边、绿边或网格残留 | 修正 Alpha 蒙版，保留源 RGB，重新执行白底和深蓝底检查。 |
| 候选动效漏帧 | 修正截图时序或审计时钟，禁止缩减源帧列表。 |
| 页面、区块、卡片、标题或描述由截图承载 | 用 DOM/CSS 重建容器和内容，图片只保留独立图形。 |
| 像素审计通过但任务行是图片 | 结果仍判失败；在 `STRUCTURE_AUDIT.json` 登记文字和列表选择器，并把任务行改成 DOM。 |
| 截图在列表、卡片或素材中间结束 | 在 `REFERENCE_COVERAGE.json` 标记部分延续，禁止补写隐藏内容或声称 `full_component`。 |
| 末项存在于 DOM 但触摸无法到达 | 在 `CONTENT_REACHABILITY.json` 登记真实滚动容器，修复溢出和触摸行为，重新执行滚轮与触摸测试。 |
| 灰条看起来像滚动条但没有和滚动状态绑定 | 在真实滚动归属和输入证据通过前，只能把它当装饰。 |
| 有损录屏用 DOM 重建后无法达到 `< 2` | 报告失败帧证据，禁止暗中放宽门槛。 |
| 凸出插画没有外沿或被裁掉 | 把它加入 `VISUAL_MODEL.json`，核对裁切归属，并按轮廓并集生成外沿。 |
| 删除内部接缝时连外沿一起删掉 | 改路径前先把禁止描边的内部接缝和最外轮廓成员分开登记。 |
| 凹口被填成整块灰色 | 改用轮廓并集外扩形成 `outer_ring`，保留登记开口。 |
| 旧审计通过后用户又标出问题 | 改代码前登记红框和修改前候选图，再运行迭代差异审计。 |
| 正确半透明边在另一背景上让全局 MAE 变差 | 标记 `source_composited` 或 `non_identifiable`，运行透明矩阵并保持严格失败，禁止继续猜 Alpha。 |
| 迭代时修改了审计范围 | 保留旧 `core_scope`，另建 `expanded_scope`，禁止直接比较两者全图指标。 |

## 最小命令示例

```powershell
python scripts/analyze_reference.py --input reference.png --output REFERENCE_BASELINE.json
python scripts/validate_reference_coverage.py --spec REFERENCE_COVERAGE.json --output evidence/reference-coverage.json
python scripts/validate_visual_model.py --model VISUAL_MODEL.json --audit-map AUDIT_MAP.json --iteration-ledger ITERATION_LEDGER.json --output evidence/visual-model-audit.json
node scripts/validate_implementation_structure.cjs --spec STRUCTURE_AUDIT.json --output-dir evidence/structure-audit
node scripts/validate_content_reachability.cjs --spec CONTENT_REACHABILITY.json --output-dir evidence/content-reachability
python scripts/run_visual_audits.py --reference reference.png --candidate evidence/page.png --baseline-candidate evidence/page-before.png --map AUDIT_MAP.json --output-dir evidence/visual-audit
node scripts/capture_transparency_matrix.cjs --url http://127.0.0.1:4173 --output-dir evidence/transparency-matrix --background-selector .stage --component-selector .component
python scripts/validate_delivery.py --report evidence/reference-coverage.json --report evidence/visual-model-audit.json --report evidence/structure-audit/structure-audit.json --report evidence/content-reachability/content-reachability.json --report evidence/visual-audit/visual-audit.json --report evidence/transparency-matrix/transparency-matrix.json --report evidence/interaction-audit.json --output DELIVERY_REPORT.json
```

## 完成报告

报告交付范围、范围与输入哈希、证据受限区域、未解决证据数、目标/保护区域变化、滚动契约和输入方式、可达列表项/控件数量、源尺寸、比较帧数、全图/区域/元素最大指标、交互数量、Alpha 失败数、P0/P1 数量、准确命令和退出码。没有执行的检查必须明说。本地审查完成后，仍需用户明确批准才能全局安装。
