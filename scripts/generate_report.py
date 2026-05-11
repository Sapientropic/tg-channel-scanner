#!/usr/bin/env python3
# -*- coding: utf-8 -*-

content = r"""# Signal Desk Pixel/Retro 组件库选型报告

**日期**: 2026-05-11  
**评估人**: Kimi Code CLI (技术顾问)  
**项目栈**: React 19 + Vite + TypeScript + OKLCH 色板 + 4px hard-shadow  
**核心需求**: 信号指示器、combo/achievement 动画、像素 toast、进度 HUD、卡片飞出动画

---

## 一、候选库逐个评估

### 1. Pxlkit — @pxlkit/core + @pxlkit/ui-kit

| 维度 | 评分 | 说明 |
|------|------|------|
| 组件完整度 | **9/10** | 40+ UI 组件 + 226+ SVG 像素图标分 10 个主题包（gamification/feedback/social/ui/effects/parallax/weather）+ PixelToast + 3D ParallaxIcon + AnimatedIcon |
| 代码质量 | **8/10** | TypeScript 5.7 strict, tsup 构建, ESM+CJS, tree-shakeable, 16x16 grid-based 图标系统可手编/AI 生成, CI/CD 自动发布 |
| 活跃度 | **9/10** | 持续活跃, 有自动 publish workflow, web app 完整, 多包 monorepo (Turborepo) |
| Signal Desk 契合度 | **9/10** | **直击需求**: gamification 包(奖杯/剑/药水/金币) + effects 包(爆炸/雷达 ping/火焰/冲击波) + feedback 包(徽章/盾牌/对勾) + 内置 PixelToast + animated icon 系统(支持 loop/hover/appear/ping-pong 触发器) |

**关键发现**:
- [x] **PixelToast** — 现成的像素风 toast，带 icon 插槽、位置控制、duration
- [x] **AnimatedPxlKitIcon** — 帧动画图标，支持 `trigger="appear"`（mount 时播放一次，适合 combo burst）
- [x] **Effects 包** — 含 `radar ping` 动画图标，直接对应「信号/雷达动画」需求
- [x] **Gamification 包** — 51 个 RPG/成就/奖励图标（奖杯、剑、药水、金币），直接对应「achievement」需求
- [x] **ParallaxPxlKitIcon** — 3D 视差图标，mouse tracking，可用于 HUD 装饰
- [ ] 图标资产为 source-available（需署名），代码包为 MIT
- [ ] 设计风格偏「明亮像素 RPG」，与 Signal Desk 的「纪律感信号扫描器」气质需适配

---

### 2. NES UI React — nes-ui-react

| 维度 | 评分 | 说明 |
|------|------|------|
| 组件完整度 | **8/10** | Hero, Hr, Container, Grid(Row/Col), Text, Heading, Badge, BadgeSplitted, PixelIcon, Button, IconButton, Radio, Checkbox, Input, TextArea, Toast, Select, List, Table, Progress, PixelBorder, Toolbar, Menu, Modal — 非常全 |
| 代码质量 | **7/10** | TypeScript + Sass, 从 NES.css fork 重构，dark/light 双模式，NTSC 调色板，但 Sass 构建链在现代 Vite 项目中略显沉重 |
| 活跃度 | **6/10** | 有维护但节奏偏慢，文档站点存在但更新不频繁 |
| Signal Desk 契合度 | **7/10** | PixelBorder 组件可直接包裹任意元素做像素边框；Toast 组件可用；PixelIcon 系统支持 8x8/16x16/32x32；但 **无游戏化动画、无 combo burst、无雷达动画** |

**关键发现**:
- [x] **PixelBorder** — 最实用的组件，可将任何现有 Signal Desk 组件瞬间「像素化」
- [x] **Progress** — 像素风进度条，可直接用于扫描 HUD
- [x] **Toast** — 带 bubblePosition 控制，可用作通知
- [x] **NTSC 调色板** — 与 Signal Desk 的 OKLCH 色板理念不同，需额外适配
- [ ] 无动画图标系统
- [ ] 无游戏化/成就/combo 相关组件
- [ ] 整体美学偏「NES 家用机怀旧」，与 Signal Desk 的「信号站扫描器」冷峻气质有差距

---

### 3. Pixelact UI — shadcn/ui 像素注册表

| 维度 | 评分 | 说明 |
|------|------|------|
| 组件完整度 | **6/10** | 基于 shadcn/ui 结构，Button/Input/Dialog 等基础组件有像素皮肤，但组件数量远少于 Pxlkit/NES UI |
| 代码质量 | **8/10** | shadcn 模式 = 代码复制到你项目里，完全可控，Tailwind-based，可深度定制 |
| 活跃度 | **7/10** | 2025-05 创建，2026-02 被加入官方 shadcn registry，有持续维护迹象 |
| Signal Desk 契合度 | **7/10** | 与现有 Tailwind + shadcn 项目集成最顺滑，但 **无游戏化动画、无特效图标、无 toast 系统** |

**关键发现**:
- [x] **shadcn registry 模式** — `npx shadcn add https://pixelactui.com/r/button.json`，组件直接进你的 codebase，零依赖风险
- [x] 与 Tailwind v4 天然兼容
- [x] 2026-02 被官方 shadcn registry 收录，有社区背书
- [ ] 组件覆盖较薄，仅基础 UI 皮肤
- [ ] 无动画系统、无图标库、无游戏化

---

### 4. ArcadeUI — arcadeui

| 维度 | 评分 | 说明 |
|------|------|------|
| 组件完整度 | **6/10** | Button, Badge, Card, Avatar, Breadcrumbs, Carousel, Chat Bubble, Input, Select, Calendar, Alert, Modal, Accordion, Chart, Table |
| 代码质量 | **6/10** | React 19 + TS + Tailwind v4 + Vite，但文档和 demo 较浅，代码细节难以验证 |
| 活跃度 | **5/10** | 2025-03 有记录，但 GitHub 信息获取时内容单薄，维护力度存疑 |
| Signal Desk 契合度 | **5/10** | 有 Chart/Table/Calendar 等数据组件，但 **无 pixel 特效、无动画系统、无游戏化** |

**淘汰理由**: 无差异化价值。基础组件 Signal Desk 已有 shadcn，像素风格不如 Pixelact UI 纯粹，数据可视化不如自己用 recharts 定制。

---

### 5. @joacod/pixel-ui — Base UI + Tailwind v4

| 维度 | 评分 | 说明 |
|------|------|------|
| 组件完整度 | **5/10** | 信息极少，README 几乎空白 |
| 代码质量 | **6/10** | Built on Base UI（可访问性底层好），但文档严重缺失 |
| 活跃度 | **4/10** | 仅 2 stars / 1 watcher / 0 forks，latest release Feb 2026 但社区 Adoption 几乎为零 |
| Signal Desk 契合度 | **5/10** | Base UI 可访问性好，但无像素特效、无动画、无图标 |

**淘汰理由**: 社区 adoption 极低，文档缺失，无法在生产环境承担风险。Base UI 的抽象层与 Signal Desk 现有的 shadcn/Radix 基础重复。

---

### 6. Pixel UI React — @duheng1992/pixel-ui-react (CSS Houdini)

| 维度 | 评分 | 说明 |
|------|------|------|
| 组件完整度 | **4/10** | Button, Icon, Overlay, Text, ConfigProvider, Input, Popconfirm, Tooltip — 仅 8 个组件 |
| 代码质量 | **6/10** | React 19 + TS + Vitest 100% 覆盖率 + Tree-shakable，技术底子好 |
| 活跃度 | **5/10** | 有中文社区讨论（掘金 2025-11），但组件迁移进度慢 |
| Signal Desk 契合度 | **3/10** | CSS Houdini Paint Worklet 的浏览器兼容性 **是致命伤** |

**淘汰理由**: CSS.paintWorklet 是实验性技术，仅 Chromium 系支持，Firefox/Safari 不兼容。Signal Desk 作为求职者工具必须跨浏览器可用。组件数量也少得可怜。

---

### 7. retro-react — retro-react

| 维度 | 评分 | 说明 |
|------|------|------|
| 组件完整度 | **5/10** | 20+ 组件：Alert, Box, Button, Card, Chip, Container, Input, Modal, ProgressBar, Text, MouseTrail, PixelatedImage |
| 代码质量 | **5/10** | Emotion 做样式，sx prop 支持，但架构偏旧（类 MUI v4 模式） |
| 活跃度 | **2/10** | 最后 release v1.3.2 在 2023-01-07，npm 最后发布在 2023-11，**已实质停更** |
| Signal Desk 契合度 | **4/10** | MouseTrail 和 PixelatedImage 有趣，但 **无 toast、无游戏化、无信号动画** |

**淘汰理由**: 实质停更超过 2 年，React 19 兼容性未知，Emotion 样式方案与 Signal Desk 的 Tailwind 方案冲突。MouseTrail 对 ADHD 用户反而可能造成注意力分散。

---

### 8. Retro8 UI — github.com/regiszaum/retro8-ui

| 维度 | 评分 | 说明 |
|------|------|------|
| 组件完整度 | **?/10** | **仓库无法访问** — 可能已删除、改名或设为私有 |
| 代码质量 | **?/10** | 无法验证 |
| 活跃度 | **0/10** | 无法获取任何有效信息 |
| Signal Desk 契合度 | **0/10** | 无法评估 |

**淘汰理由**: 仓库不可达。无论原因为何，都不具备作为生产依赖的可靠性。

---

## 二、淘汰总结

| 库 | 淘汰原因 | 一句话 |
|----|---------|--------|
| **Retro8 UI** | 仓库不可达 | 无法访问 = 无法信任 |
| **retro-react** | 停更 2 年+ | 考古级代码，React 19 兼容性未知 |
| **Pixel UI React (CSS Houdini)** | 浏览器兼容性致命 | Firefox/Safari 不支持 Paint Worklet |
| **@joacod/pixel-ui** | 社区 adoption 为零 | 2 stars，无文档，生产风险极高 |
| **ArcadeUI** | 无差异化价值 | 基础组件重复，无 pixel 特效 |

**存活候选**: Pxlkit、NES UI React、Pixelact UI

---

## 三、Top 3 推荐方案

### 推荐 A：Pxlkit — 游戏化特效首选（推荐指数：★★★★★）

**拿什么用**：

```bash
# 核心 + 游戏化 + 反馈 + 特效
npm install @pxlkit/core @pxlkit/gamification @pxlkit/feedback @pxlkit/effects @pxlkit/parallax
```

**具体用法**：

| Signal Desk 需求 | Pxlkit 对应方案 | 代码示例 |
|-----------------|----------------|---------|
| **信号/雷达动画** | `@pxlkit/effects` 的 radar ping 图标 | `<AnimatedPxlKitIcon icon={RadarPing} size={48} colorful trigger="loop" />` |
| **Achievement 弹出** | `@pxlkit/gamification` 的 Trophy + `@pxlkit/core` 的 PixelToast | `<PixelToast visible={show} icon={Trophy} title="Signal Locked!" message="New channel acquired" colorfulIcon />` |
| **Combo burst** | `@pxlkit/effects` 的 explosion/shockwave 图标 + `trigger="appear"` | `<AnimatedPxlKitIcon icon={Explosion} size={64} colorful trigger="appear" />` |
| **进度 HUD** | `@pxlkit/feedback` 的 shield/badge 图标 + 自定义进度条 | 用 `PxlKitIcon` 做 HUD 节点标记，配合 Framer Motion 做进度动画 |
| **卡片飞出** | `ParallaxPxlKitIcon` 或 `AnimatedPxlKitIcon` | 卡片内嵌 gamification 图标，用 Framer Motion 做 `layoutId` 飞出动画 |

**集成到现有项目**：

```tsx
// 1. 在 vite.config.ts 确保 ESM 兼容（tsup 已处理，通常无需额外配置）

// 2. 在组件中使用
import { PixelToast, AnimatedPxlKitIcon, PxlKitIcon } from '@pxlkit/core';
import { Trophy, FireSword } from '@pxlkit/gamification';
import { RadarPing, Explosion } from '@pxlkit/effects';
import { CheckCircle } from '@pxlkit/feedback';

// 3. 适配 Signal Desk OKLCH 色板
// PxlKitIcon 支持 color 属性覆盖单色
<PxlKitIcon icon={CheckCircle} size={32} color="oklch(70% 0.2 250)" />

// 4. 硬阴影适配
// PixelToast 本身有 pixel 风格，如需调整可用 sx 或包裹一层自定义 CSS
```

**注意事项**：
- 图标资产需署名（source-available），若商用无署名需购买 commercial terms
- gamification 图标风格偏 RPG 明亮感，建议用 `color` 属性统一为 Signal Desk 的冷峻 OKLCH 色系
- 动画图标的 `frameDuration` 可调，建议加快到 80-100ms 以匹配 Signal Desk 的「纪律感」

---

### 推荐 B：NES UI React — 像素边框基础设施（推荐指数：★★★★☆）

**拿什么用**：

```bash
npm install nes-ui-react
```

**具体用法**：

| Signal Desk 需求 | NES UI 对应方案 | 代码示例 |
|-----------------|----------------|---------|
| **任何组件像素化** | `<PixelBorder>` 包裹器 | `<PixelBorder doubleSize><YourCard /></PixelBorder>` |
| **进度 HUD** | `<Progress>` 组件 | `<Progress value={scanProgress} max={100} color="success" />` |
| **Toast 通知** | `<Toast>` 组件 | `<Toast bubblePosition="right">Signal acquired</Toast>` |
| **像素图标系统** | `<PixelIcon>` + 自制 16x16 图标 | 用 Pixilart 画 Signal Desk 专用图标，按 NES UI 规范导出 |

**集成到现有项目**：

```tsx
import { PixelBorder, Progress, Toast, PixelIcon } from 'nes-ui-react';
import 'nes-ui-react/dist/css/nes-ui-react.css'; // 或按需引入 Sass

// 将现有 shadcn Card 瞬间像素化
<PixelBorder doubleSize doubleRoundCorners>
  <Card>
    <CardHeader>Scanner Status</CardHeader>
    <Progress value={67} max={100} color="primary" />
  </Card>
</PixelBorder>
```

**注意事项**：
- Sass 构建链需确认与 Vite 兼容性（通常可用 `vite-plugin-sass-dts` 或直接引 CSS build）
- NTSC 调色板与 OKLCH 不兼容，建议禁用 NES UI 默认色板，用 CSS 变量注入 OKLCH 值
- 无动画系统，combo/achievement 的动效需配合 Framer Motion 自行实现

---

### 推荐 C：Pixelact UI — 基础 UI 皮肤化（推荐指数：★★★☆☆）

**拿什么用**：

```bash
# 已有 shadcn/ui 的前提下
npx shadcn@latest add https://pixelactui.com/r/button.json
npx shadcn@latest add https://pixelactui.com/r/input.json
npx shadcn@latest add https://pixelactui.com/r/dialog.json
```

**具体用法**：

| Signal Desk 需求 | Pixelact 对应方案 |
|-----------------|------------------|
| **像素风 Button** | `Button variant="retro"` |
| **像素风 Input** | `Input`（已带像素边框） |
| **像素风 Dialog** | `DialogContent`（已带像素边框） |

**集成到现有项目**：

```tsx
// 组件直接安装在项目内，路径通常为:
import { Button } from "@/components/ui/pixelact-ui/button";

// 与现有 shadcn 组件并存，不冲突
// 但 Pixelact 组件数量少，大量界面仍需自己写
```

**注意事项**：
- shadcn registry 模式 = 代码归你，但维护成本也归你
- 组件数量太少，无法覆盖 Signal Desk 的游戏化需求
- 建议仅作为「基础控件像素化」的补充方案，而非主力

---

## 四、最终建议：混合策略（Cherry-pick + 自研）

### 不推荐「直接全量使用某一个库」

原因：
1. Signal Desk 的「信号扫描器」美学是独特的——冷峻、纪律、军事化像素，而非 RPG 明亮风或 NES 怀旧风
2. 现有库无人同时覆盖「游戏化动画 + 像素 toast + 信号雷达 + 进度 HUD + 卡片飞出」完整需求
3. OKLCH 色板和 4px hard-shadow 的 DNA 需要保留，任何库的默认样式都需大量覆盖

### 推荐策略：「Pxlkit 为弹药库 + NES UI 为基础设施 + 自研动画层」

```
+-------------------------------------------------------------+
|                    Signal Desk 架构                          |
+-------------------------------------------------------------+
|  动画层（自研 / Framer Motion）                              |
|  +- ComboBurst --> AnimatedPxlKitIcon(effects/explosion)    |
|  +- Achievement --> PixelToast + Trophy icon                |
|  +- CardFlyout --> Framer Motion layoutId + AnimatePresence |
|  +- SignalRadar --> AnimatedPxlKitIcon(effects/radar)       |
+-------------------------------------------------------------+
|  图标层（Pxlkit）                                            |
|  +- @pxlkit/gamification --> 成就/奖杯/金币                 |
|  +- @pxlkit/effects --> 爆炸/雷达/火焰                      |
|  +- @pxlkit/feedback --> 对勾/盾牌/徽章                     |
|  +- @pxlkit/ui --> 搜索/设置/主页等控制图标                 |
+-------------------------------------------------------------+
|  组件基础设施（NES UI + 自研）                               |
|  +- PixelBorder --> NES UI（包裹器）                        |
|  +- Progress --> NES UI 或自研 OKLCH 进度条                 |
|  +- Toast --> Pxlkit PixelToast（优先）或 NES UI Toast      |
|  +- 其他基础控件 --> shadcn + Pixelact UI 补充              |
+-------------------------------------------------------------+
|  底层设计系统（Signal Desk 原生）                            |
|  +- OKLCH 色板 CSS 变量                                     |
|  +- 4px 4px 0 hard-shadow 工具类                            |
|  +- 网格背景 pattern                                        |
|  +- 像素字体 Press Start 2P / VT323                         |
+-------------------------------------------------------------+
```

### 特别关注项的最终答案

| 需求 | 现成方案？ | 具体实现 |
|------|-----------|---------|
| **游戏化动画（combo/burst/achievement）** | 有，Pxlkit 直接提供 | `@pxlkit/effects` 的 explosion + `@pxlkit/gamification` 的 Trophy，配合 `trigger="appear"` 和 Framer Motion 的 `scale` spring |
| **像素 toast/通知** | 有，Pxlkit 直接提供 | `@pxlkit/core` 的 `<PixelToast>`，icon 插槽塞 `@pxlkit/feedback` 的 CheckCircle 或 Shield |
| **信号/雷达动画** | 有，Pxlkit 直接提供 | `@pxlkit/effects` 的 radar ping 图标，`trigger="loop"`，无限旋转扫描 |
| **进度 HUD** | 部分提供 | NES UI `<Progress>` 做基底，但建议自研 OKLCH 渐变进度条 + Pxlkit 图标做节点标记 |
| **卡片飞出动画** | 需自研 | Framer Motion `layoutId` + `AnimatePresence`，飞出时挂载 `@pxlkit/effects` 的 shockwave 做 burst 尾效 |

### 实施优先级

1. **P0（本周）**: 安装 `@pxlkit/core + @pxlkit/effects + @pxlkit/gamification + @pxlkit/feedback`，验证 PixelToast 和 AnimatedPxlKitIcon 在 Signal Desk 色板下的表现
2. **P1（两周内）**: 安装 `nes-ui-react`，提取 `<PixelBorder>` 和 `<Progress>` 做 PoC，确认 Sass/CSS 与 Vite 的兼容性
3. **P2（一个月内）**: 基于 Framer Motion 实现 `ComboBurst` 和 `CardFlyout` 封装组件，将 Pxlkit 图标作为动效节点
4. **P3（持续）**: 评估是否用 Pixelact UI 替换部分 shadcn 基础控件的皮肤

---

## 五、风险提示

| 风险 | 库 | 缓解措施 |
|------|-----|---------|
| 图标资产 license 限制 | Pxlkit | 阅读 `LICENSE-ASSETS`，确认署名要求；如需无署名商用，联系作者购买 commercial terms |
| NES UI Sass 构建链 | NES UI React | 优先引用预编译 CSS build，避免引入 Sass 编译依赖 |
| Pxlkit 风格适配成本 | Pxlkit | 统一用 `color` 属性注入 OKLCH 值，覆盖默认明亮 palette；必要时用 `gridToSvg` 工具导出后自行调色 |
| 多库体积膨胀 | 全部 | 所有推荐库均 tree-shakeable，确保使用 ESM 导入（非 require）|

---

*报告结束。如需对某个库做更深度的源码审查或 PoC 代码，可继续展开。*
"""

with open(r'E:\SDY\Claude长期空间\单道杨\tg-channel-scanner\docs\pixel-ui-library-evaluation-report.md', 'w', encoding='utf-8') as f:
    f.write(content)
print('Report written successfully')
