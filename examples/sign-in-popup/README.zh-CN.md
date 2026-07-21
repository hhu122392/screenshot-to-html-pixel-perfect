# 签到奖励弹窗审计案例

[English](README.md) | 简体中文

这个案例只实现参考图里的签到弹窗，原页面背景不在复刻范围。页面使用原生 HTML、CSS 和 JavaScript，卡片、文字、角标、按钮、勾选和关闭控件都是真实 DOM；图片只承载日历、奖品等独立插画。

> 审计结论：结构、Alpha、交互和响应式通过；严格像素门槛未通过。弹窗审计裁图 MAE 为 `5.458677`，高于 `<2` 门槛。本案例用于展示可复现实现、问题复盘和证据边界，不宣称严格 1:1 完成。

![签到弹窗移动端演示](demo/mobile-preview.png)

## 本地运行

在本目录启动静态服务器：

```powershell
python -m http.server 4198 --bind 127.0.0.1
```

打开：

- 自适应演示：`http://127.0.0.1:4198/`
- 1179×2556 审计视图：`http://127.0.0.1:4198/?audit=1`

## 已实现

- 7 天奖励使用数据驱动渲染。
- 第 1 天已签、第 2 天选中与“稀有”角标、第 7 天跨两列“大奖”卡片。
- 领取按钮、提醒开关、关闭按钮。
- 点击关闭、按 Escape 关闭、切换提醒状态。
- 360×780、390×846、430×932 三个视口完整显示。

## 原图、实现和差异

下图从左到右依次为参考裁图、当前实现和差异图。差异图不是装饰图，它保留了仍未通过的字体、外沿和角标边缘差异。

![参考、实现与差异](demo/comparison.png)

## 这次复盘解决了什么

1. **外沿属于整个组合轮廓。** 黄色头图、绿色区域、凸出的日历和白色主体共同决定弹窗轮廓，不能只给单个矩形容器加边框。
2. **凸出元素必须进入轮廓并集。** 日历顶部外沿缺失，是因为原实现只画了黄色和绿色两段开放路径，中间没有覆盖凸出的日历。
3. **曲线连接不能用硬切片代替。** 黄色、日历和绿色之间的凹口需要保留开口并排除内部接缝，硬三角会制造明显切割感。
4. **角标需要独立建模。** “稀有”是卡片右上标签，“大奖”是带折尾的旗形，不能共用同一种裁切形状。
5. **用户标注必须在修改前登记。** `AUDIT_MAP.json` 把外沿、曲线、绿色面和两个角标列为目标区域，其余区域作为保护区域。
6. **单张合成截图不能反推唯一 Alpha。** 左右和底部半透明外沿已经与复杂背景混合，因此保持 `non_identifiable`，不能把猜出的透明度说成严格正确。

## 审计结果

| 检查 | 结果 | 证据 |
|---|---:|---|
| DOM/图片边界 | 通过 | 7 张奖励卡和全部文字均为真实 DOM |
| Alpha 素材 | 5/5 通过 | 源 RGB 不匹配数为 0 |
| 交互 | 3/3 通过 | 点击关闭、Escape、提醒切换；浏览器错误 0 |
| 响应式 | 3/3 通过 | 360、390、430 三种宽度 |
| 严格像素 | 未通过 | 弹窗审计裁图 MAE `5.458677`，门槛 `<2` |

机器可读结果见 [`audit/AUDIT_STATUS.json`](audit/AUDIT_STATUS.json)，图层和组合轮廓见 [`audit/VISUAL_MODEL.json`](audit/VISUAL_MODEL.json)。

从仓库根目录运行核心校验：

```powershell
python scripts/validate_reference_coverage.py --spec examples/sign-in-popup/audit/REFERENCE_COVERAGE.json --output examples/sign-in-popup/evidence/reference-coverage.json
python scripts/validate_visual_model.py --model examples/sign-in-popup/audit/VISUAL_MODEL.json --audit-map examples/sign-in-popup/audit/AUDIT_MAP.json --iteration-ledger examples/sign-in-popup/audit/ITERATION_LEDGER.json --output examples/sign-in-popup/evidence/visual-model.json
node scripts/validate_implementation_structure.cjs --spec examples/sign-in-popup/audit/STRUCTURE_AUDIT.json --output-dir examples/sign-in-popup/evidence/structure
node scripts/run_interaction_scenarios.cjs --spec examples/sign-in-popup/audit/INTERACTION_SCENARIOS.json --output-dir examples/sign-in-popup/evidence/interactions
node examples/sign-in-popup/tools/responsive_audit.cjs
node scripts/capture_transparency_matrix.cjs --url http://127.0.0.1:4198 --output-dir examples/sign-in-popup/evidence/transparency --background-selector .stage --component-selector .popup-shell
```

## 证据边界

- 交付范围是 `visible_frame`，只证明参考图中的打开态。
- 关闭后、领取后和提醒关闭后的视觉没有来源，不能作为像素级结论。
- 原字体、头图矢量源文件和透明弹窗分层缺失。
- 半透明外沿属于 `non_identifiable` 区域，严格交付保持失败。

## 文件结构

- `index.html`、`styles.css`、`app.js`：可运行实现。
- `assets/`：独立插画和 Noto Sans SC 字体。
- `demo/`：原图、移动端演示、修改前基线和对比图。
- `audit/`：范围、区域、图层拓扑、交互和审计状态。
- `tools/`：案例自己的响应式审计脚本。
