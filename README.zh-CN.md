# 截图像素级复刻 Skill

简体中文 | [English](README.md)

这是一套用于把截图、GIF 或录屏复刻成可复用原生 HTML、CSS 和 JavaScript 的 Codex Skill。它把参考像素和录制行为当作证据，并通过结构、真透明素材、滚动、交互、响应式和逐帧审计控制交付质量。

## 这套 Skill 强制检查什么

- 容器、卡片、实时文字、数值、描述、进度、按钮、状态和重复列表必须使用真实 DOM/CSS。
- 图片只允许承载 CSS 无法忠实实现的独立图形素材。
- 抠图必须是保留源 RGB 的 RGBA 真透明素材，禁止烘焙棋盘格、网格或纯色背景伪装透明。
- 开工前明确 `visible_frame`（只复刻可见帧）或 `full_component`（完整组件），不能根据截断截图编造隐藏内容。
- 使用真实滚轮和触摸滚动，并验证首项、末项和必需控件都能到达。
- 对交互和动效使用可重复的确定性截图，并按登记帧逐帧比较。
- 完成结论必须有证据：全图、区域、关键元素、Alpha、交互、控制台错误、P0/P1 和最终交付报告都要通过。

完整工作流和硬门槛见 [SKILL.zh-CN.md](SKILL.zh-CN.md)。

## 审计案例

### 签到奖励弹窗

这个可运行的原生 HTML/CSS/JavaScript 案例展示了本次 SKILL 迭代的完整问题链：组合轮廓的半透明外沿、凸出日历、需要保留的凹口，以及不能共用同一形状的“稀有”和“大奖”角标。

| 原始截图 | 本 SKILL 实现 |
|---|---|
| <img src="examples/sign-in-popup/demo/reference-full.png" alt="签到弹窗原始截图" width="390"> | <img src="examples/sign-in-popup/demo/mobile-preview.png" alt="本 SKILL 实现的签到弹窗" width="390"> |

左侧保留完整原图作为来源证据；右侧只实现签到弹窗，背景使用中性灰舞台。

- [查看案例说明和本地演示](examples/sign-in-popup/README.zh-CN.md)
- 范围：`visible_frame`，原页面背景不在实现范围。
- 已验证：DOM/图片边界通过、Alpha 素材 5/5、交互 3/3、响应式 3/3。
- 严格像素状态：**未通过**。弹窗审计裁图 MAE 为 `5.458677`，未达到 `<2`；缺少原字体、头图矢量层和可恢复的透明源图层。

仓库保留失败状态和对比证据，不把案例包装成严格 1:1 完成。它直接说明了为什么截图复刻需要图层拓扑、证据边界、修改前基线以及目标区/保护区审计。

## 仓库结构

- `SKILL.md` / `SKILL.zh-CN.md`：中英双语 Skill 规则。
- `references/`：中英双语实现与验收说明。
- `assets/templates/`：中英双语证据模板和机器可读审计规格。
- `scripts/`：参考图分析、真透明抠图、浏览器截图、结构/可达性检查、像素/逐帧对比和最终交付校验脚本。
- `tests/`：回归测试和浏览器测试夹具。
- `examples/`：可运行并带审计证据的复刻案例。
- `agents/openai.yaml`：Codex Skill 界面元数据。

## 本地验证

需要 Python 3.10+、Node.js 18+、Chromium 和 Playwright。

```powershell
python -m pip install -r requirements.txt
npm install
npx playwright install chromium
python -m unittest discover -s tests -v
```

每个脚本都可以使用 `--help` 查看准确参数。运行时生成的审计证据应放入 `evidence/`，该目录默认不提交到仓库。

## 安装为 Codex 全局 Skill

把本仓库复制到 Codex 全局 Skill 目录并命名为 `screenshot-to-html-pixel-perfect`，或使用 Codex Skill 安装器安装本仓库。安装后重启 Codex，让 Skill 列表重新加载。

