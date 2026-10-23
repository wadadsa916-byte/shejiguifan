# 数据字段说明

## 两套数据结构

库里有两种格式，用途不同。

### `generated_v2/<id>.json` — 归纳后的规范

9 个章节，适合直接读给人看。

```json
{
  "id": "t189",
  "overview": {
    "name": "Cursor",
    "url": "https://cursor.com/",
    "section": "开发环境",
    "pagesScanned": ["https://cursor.com/", ".../pricing", ".../docs", ".../blog"],
    "subpages": ["/pricing", "/docs", "/blog"],
    "sectionCount": 29,
    "componentSamples": 346,
    "typeSteps": 40
  },
  "colors": {
    "roles": {
      "primary":    { "hex": "#f54e00", "value": "...", "token": "--color-...", "source": "css-var", "contrastOnBg": 3.28 },
      "background": { "hex": "#f7f7f4", ... },
      "foreground": { "hex": "#26251e", ..., "contrastOnBg": 14.33 }
    },
    "neutralRamp": [ { "hex": "#292d32", "count": 38 }, ... ],
    "backgroundsTotal": 14,
    "textTotal": 12,
    "bordersTotal": 0
  },
  "typography": {
    "ladder": [
      { "size": "12px", "px": 12, "weight": "400", "lineHeight": "19.5px",
        "letterSpacing": "normal", "family": "CursorGothic",
        "count": 118, "tags": ["span"], "samples": ["..."] }
    ],
    "totalSteps": 55,
    "families": ["CursorGothic", "berkeleyMono", "EB Garamond"],
    "weights": ["400", "500", "510", "600", "700"]
  },
  "spacing": {
    "ladder": [ { "value": "8px", "px": 8, "count": 1400 }, ... ],
    "inferredBaseUnit": null,
    "containerWidths": [ { "value": "1200px", "count": 3 } ]
  },
  "shape": {
    "radiusLadder": [ { "value": "4px", "px": 4, "count": 354 }, ... ],
    "shadows": [ { "value": "rgba(0,0,0,0.1) 0px 4px 12px", "count": 3 } ],
    "zIndex": [ { "value": "10", "count": 5 } ]
  },
  "motion": {
    "durations": [ { "value": "0.15s", "count": 70 } ],
    "easings": [ { "value": "cubic-bezier(0.4, 0, 0.2, 1)", "count": 42 } ],
    "properties": ["color", "background-color"]
  },
  "components": {
    "button": {
      "label": "按钮",
      "count": 69,
      "sizeBuckets": { "sm": 9, "md": 3, "lg": 3, "xl": 3 },
      "samples": {
        "lg": [ {
          "height": 43, "padding": "12.48px 21.6px 12.8px",
          "radius": "9999px", "background": "rgb(38, 37, 30)",
          "color": "rgb(247, 247, 244)",
          "fontSize": "16px", "fontWeight": "400",
          "contrast": 14.33, "text": "Download for macOS"
        } ]
      }
    }
  },
  "sections": [
    { "tag": "header", "height": 52, "padding": "0px", "background": "rgb(247,247,244)",
      "heading": null, "children": 3 }
  ],
  "accessibility": {
    "bodyContrast": 14.33, "bodyContrastLevel": "AAA",
    "tapTargetMin": 13, "tapTargetMedian": 34
  }
}
```

### `specs_sem/<id>.json` — 原始采集数据

字段更多更细，包括 CSS 变量全表、断点、`@font-face`、交互状态。

```json
{
  "cssVariables": { "--color-primary": "#f54e00", ... },   // 最多 575 个
  "breakpoints": ["768px", "1024px", "1280px"],
  "typography": { "scale": [...], "families": [...] },
  "colors": { "backgrounds": [...], "text": [...], "borders": [...] },
  "radii": [...], "shadows": [...], "borders": [...],
  "motion": { "durations": [...], "easings": [...], "keyframes": [...] },
  "components": { ... },
  "design": { "interactiveStates": [...] },               // hover/focus/active 实测
  "fontFaces": [ { "family": "...", "src": "...", "weight": "400" } ],
  "layout": { "containerWidths": [...], "zIndex": [...] },
  "page": { "elementCount": 1113, "documentHeight": 5843 }
}
```

## 字段可靠性分级

| 字段 | 可靠性 | 说明 |
|---|---|---|
| `typography.ladder` | 高 | 直接读计算样式，准确 |
| `colors.roles.background` | 高 | 100% 覆盖 |
| `colors.roles.foreground` | 高 | 直接读 `color` |
| `colors.roles.primary` | **中** | 44% 覆盖，从变量名推断 |
| `components.*.samples` | 中 | 只含页面真实渲染的变体 |
| `spacing.inferredBaseUnit` | 中 | 按整除率推断，可能为 null |
| `shape.radiusLadder` | 高 | 但含 `9999px`/`50%` 这类特殊值 |
| `motion.durations` | 中 | 91% 覆盖，来自 transition 声明 |
| `accessibility.tapTarget*` | 中 | 只统计控件，不含文本链接 |
| `sections[].heading` | 低 | 40% 缺失，很多区块本来没标题 |

## 颜色值格式

原始值可能是任何 CSS 颜色函数：

```
#f54e00
rgb(38, 37, 30)
rgba(0, 0, 0, 0.5)
lab(66.9756 -58.27 19.5419)
oklch(0.145 0 0)
oklab(0.999998 -0.00000980496 0.0000234246 / 0.92)
color(display-p3 0.9176 0.2 0.1373)
color-mix(in srgb, red 50%, blue)
```

`designspec/colorparse.py` 能把它们全部转成 `#rrggbb` 并算对比度。写代码时如果只认 `rgb()`/`hex`，会漏掉 239 个值。

## 尺寸档位是怎么分的

组件的 `sizeBuckets` 按渲染高度分：

| 档位 | 高度范围 |
|---|---|
| `sm` | ≤ 28px |
| `md` | 29–36px |
| `lg` | 37–44px |
| `xl` | > 44px |

这是按像素分的，不对应设计系统里的命名。Cursor 的 `lg` 按钮 43px，Vercel 的 `md` 按钮 40px——档位名只表示大小顺序。
