# 实际使用案例

每个案例都跑了真实数据，可以直接复现。

---

## 案例一：用户要做一个按钮，问该多大

**用户说**：「我要做个主要按钮，多大合适？」

**错误做法**：直接说「40px」。

**正确做法**：先查分布。

```bash
python3 server.py suggest button
```

**真实输出**（499 站覆盖）：

```json
{
  "purpose": "按钮",
  "sitesCovered": 499,
  "distribution": {
    "height": [
      {"value": "32", "count": 472, "share": "12.5%"},
      {"value": "36", "count": 351, "share": "9.3%"},
      {"value": "40", "count": 349, "share": "9.2%"},
      {"value": "28", "count": 346, "share": "9.2%"},
      {"value": "44", "count": 167, "share": "4.4%"}
    ],
    "radius": [
      {"value": "9999px", "count": 546, "share": "20.8%"},
      {"value": "8px", "count": 529, "share": "20.1%"},
      {"value": "6px", "count": 326, "share": "12.4%"},
      {"value": "4px", "count": 184, "share": "7.0%"}
    ],
    "fontSize": [
      {"value": "16px", "count": 1245, "share": "33.0%"},
      {"value": "14px", "count": 1104, "share": "29.2%"}
    ],
    "fontWeight": [
      {"value": "400", "count": 54.1%},
      {"value": "500", "count": "32.9%"}
    ]
  }
}
```

**怎么回答**：

> 544 个站里，按钮高度最常见的是 32px（12.5%），36px 和 40px 各占 9% 左右。
>
> 建议：
> - 主操作区（首屏 CTA）→ 40–44px，视觉重量够
> - 常规表单 → 36px
> - 工具栏、表格内 → 32px
>
> 圆角两种主流：完全胶囊（9999px，20.8%）或 8px（20.1%）。这两种风格差异很大，看你要哪种感觉。
>
> 字号 16px 最常见（33%），但 14px 也很常见（29%）。
>
> 注意：这是「最常见」，不是「最佳」。分布本身就是答案。

---

## 案例二：用户问某个站的设计

**用户说**：「Cursor 官网用的什么设计？」

```bash
python3 server.py spec t189
```

**关键数据**：

| 项 | 值 |
|---|---|
| 主色 | `#f54e00` 橙（对比度 3.28） |
| 背景 | `#f7f7f4` 米白 |
| 正文色 | `#26251e`（对比度 14.33，AAA） |
| 字体 | CursorGothic / berkeleyMono / EB Garamond |
| 正文字号 | 14px（最高频） |
| 排版档位 | 40 种 |
| 间距基准 | 4px（出现 476 次） |
| 圆角 | 4px(354次) / 8px(39) / 9999px |
| 组件样本 | 346 个，15 类 |
| 扫描页面 | 4 个（首页/定价/文档/博客） |

**怎么回答**：

> Cursor 是暖色系：米白底 `#f7f7f4` 配深棕黑字 `#26251e`，强调色用橙 `#f54e00`。
>
> 圆角很不统一：按数值排是 1.5/2/3/4/6/8/10/12px 八种，但实际用得最多的是 4px（354 次），8px 只有 39 次。还有胶囊形。说明它不是一套严格系统，是按场景选的。
>
> 间距用 4px 基准，出现 476 次，体系比较稳。
>
> 字体是自研 CursorGothic，这个你用不了。
>
> 要注意：主色 `#f54e00` 在米白底上对比度只有 3.28，不达 AA 标准（4.5）。他们敢这么用是因为主色只做装饰和强调，不承载正文。

---

## 案例三：用户要对比几个站

**用户说**：「Linear 和 Vercel 设计有什么不同？」

```bash
python3 server.py compare-sites t189,t385
```

**真实输出**：

| 站点 | 主色 | 正文 | 间距基准 |
|---|---|---|---|
| Cursor | `#f54e00` | 14px | — |
| Vercel | `#0070f3` | 14px | 4px |

**怎么回答**：

> 两个站正文都是 14px，间距也都是 4px 网格，但气质完全不同：
>
> - Cursor 暖色（橙 `#f54e00` + 米白 `#f7f7f4`），圆角八种混用，主要用 4px
> - Vercel 冷色（蓝 `#0070f3` + 纯白），圆角克制
>
> 注意 `compare-sites` 里 Cursor 的间距基准显示为 `—`，因为 `inferredBaseUnit` 字段为空。手动算整除率可以推出来是 4px。

---

## 案例四：用户要体检自己的网站

**用户说**：「帮我看看我这个网站设计有什么问题。」

```bash
python3 server.py audit https://vercel.com
```

**真实输出**：

```json
{
  "url": "https://vercel.com",
  "platform": "desktop",
  "measured": {
    "body": {
      "fontSize": "16px",
      "contrast": 17.18,
      "fontFamily": "GeistSans"
    },
    "typeSteps": 8,
    "radii": ["9999px", "6px", "20px", "4px", "8px"],
    "tap": {"total": 5, "under44": 5, "under32": 2, "iconTotal": 0}
  },
  "findings": [],
  "summary": {"errors": 0, "warnings": 0, "infos": 0}
}
```

**怎么回答**：

> Vercel 首页体检：0 个问题。
>
> - 正文 16px，对比度 17.18:1（远超 AAA 的 7:1）
> - 字号只有 8 种，很克制
> - 圆角 5 种，标准范围
> - 5 个控件里 2 个小于 32px，比例 40%，低于告警阈值

**另一个例子**（Cursor，真实输出）：

```
[warn] 主要操作尺寸: 58/79 小于 32px
[info] 图标按钮尺寸: 13/21 小于 24px
```

> Cursor 有 58 个小于 32px 的按钮。查了一下，主要是页面里编辑器模拟区的演示元素——那些小按钮是「假装是编辑器 UI」的一部分，不是真实操作。
>
> 所以这个警告要看语境，不能机械地改。

---

## 案例五：用户要一套 CSS 变量

**用户说**：「给我一套 CSS 变量，我要做暗色科技风。」

```bash
python3 server.py theme t247 --raw > theme.css
```

**真实输出**（Motion）：

```css
/* Motion — https://motion.dev/ */
:root {
  --color-bg: #0e1312;  /* css-var: --background */
  --color-text: #ededec;  /* css-var: --foreground */
  --color-primary: #ffdb2a;  /* css-var: --accent */
  --color-danger: #ff5f57;  /* css-var: --error */
  --color-border: #1e2623;  /* css-var: --border */
  --radius-xs: 3px;
  --radius-sm: 4px;
  --radius-md: 6px;
  --space-1: 20px;
  --text-xs: 11px;
  --text-sm: 12px;
  --text-base: 15px;
  --ease-1: ease;
  --ease-2: cubic-bezier(0.25, 1, 0.5, 1);
  --font-sans: "TASA Orbiter", sans-serif;
}
```

**怎么回答**：

> 这是 Motion（motion.dev）的实测 token。暗色 + 亮黄，对比度 13.76:1，很清晰。
>
> 但**建议改**：
> - 主色 `#ffdb2a` 换成你品牌的颜色
> - 背景 `#0e1312` 带一点绿，要纯黑就改 `#0a0a0a`
>
> 直接抄会撞脸，抄结构不抄色值。

---

## 案例六：用户按用途查 token

**用户说**：「动效时长用多少合适？」

```bash
python3 server.py suggest duration
```

**真实输出**（496 站）：

```
0.15s  26.1%
0.2s   20.3%
0.16s  10.4%
0.3s    9.4%
0.5s    4.3%
```

**怎么回答**：

> 0.15s 是最主流的（26%），0.2s 紧随其后（20%）。
>
> 规律：
> - 微交互（hover、颜色变化）→ 0.15s
> - 元素进出场 → 0.2–0.3s
> - 大区块转场 → 0.5s+
>
> 超过 0.5s 会让人觉得卡。

---

## 案例七：找特定字体用在哪些站

**用户说**：「有哪些站用 Inter 字体？」

```bash
python3 server.py search "Inter"
```

返回所有用 Inter 的站。可以用来判断这个字体的适用场景。

---

## 反向案例：什么情况不该用这个库

**用户说**：「帮我写一个按钮组件的完整代码。」

→ 库里没有代码。应该说：「库里只有尺寸和颜色，代码我按查到的值写给你。」

**用户说**：「为什么 Cursor 的按钮是 43px？」

→ 库里只有 what，没有 why。应该说：「数据里只有 43px 这个值，设计原因原站没公开。」

**用户说**：「给我 CursorGothic 字体文件。」

→ 库里只有名字。应该说：「CursorGothic 是自研字体，拿不到文件，建议用替代品。」

**用户说**：「帮我设计一个全新的品牌视觉。」

→ 库里是别人的设计。应该说：「库里可以做参考和约束，但原创设计得另外做。」
