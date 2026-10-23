# 怎么用

三种用法，按需要选。

---

## 一、看网页

最直接，不用装任何东西。

先构建网页（可选，也可直接用命令行/MCP）：

```bash
cd designspec
python3 gen_native.py          # 生成 544 个站点页 + 索引页到 ../site/
```

然后起个本地服务：

```bash
python3 -m http.server 8899 --bind 127.0.0.1
```

打开 http://127.0.0.1:8899/site/index.html

544 个站按 18 个分类列出，点进去是完整规范：概览、色彩、排版、间距、圆角阴影、动效、组件、页面结构、无障碍。

---

## 二、命令行查

不想开浏览器的时候用。

```bash
cd designspec
```

### 查某个站

```bash
python3 server.py get t189            # 完整数据（JSON）
python3 server.py spec t189           # 归纳后的 9 章规范
python3 server.py components t189     # 只要组件
python3 server.py tokens t189         # 只要语义色
python3 server.py theme t189          # 导出 CSS 变量
```

### 找站

```bash
python3 server.py list                # 全部 544 个
python3 server.py search "cursor"     # 按名字搜
python3 server.py search "Geist"      # 按字体搜
python3 server.py search "#0070f3"    # 按颜色搜
```

### 问「该用什么值」

```bash
python3 server.py suggest button      # 按钮尺寸分布
python3 server.py suggest radius      # 圆角分布
python3 server.py suggest duration    # 动效时长分布
python3 server.py suggest body        # 正文字号分布
```

输出示例：

```
按钮（499 站）
  height:   32(12.5%)  36(9.3%)  40(9.2%)  28(9.2%)
  radius:   9999px(20.8%)  8px(20.1%)  6px(12.4%)
  fontSize: 16px(33.0%)  14px(29.2%)  12px(10.0%)
```

### 对比几个站

```bash
python3 server.py compare t189,t385,t247        # 共有特征（圆角/动效/字体交集）
python3 server.py compare-sites t189,t385,t247  # 横向对比（主色/正文/间距）
```

### 体检任意网址

```bash
python3 server.py audit https://example.com              # 桌面基准
python3 server.py audit https://example.com --mobile     # 触屏基准
```

会抓页面、量尺寸，然后报出偏离行业惯例的地方。

---

## 三、接到 AI 工具里（MCP）

让 Claude Desktop、Cursor 这类工具直接调用这 544 份数据。

### 配置

把 `mcp.json` 的内容加到你的 MCP 配置文件里。

**Claude Desktop** 的配置位置：

- macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`

**Cursor** 的配置位置：

- `~/.cursor/mcp.json`

内容：

```json
{
  "mcpServers": {
    "designeer-designspec": {
      "command": "python3",
      "args": ["/绝对路径/designspec/mcp_stdio.py"]
    }
  }
}
```

改完重启工具。

### 配好之后能问什么

配好后直接对 AI 说：

- 「Cursor 官网用什么字体、字号、圆角？」
- 「设计一个按钮，按行业惯例该用多大？」
- 「对比一下 Linear 和 Vercel 的设计差异」
- 「帮我体检 https://mysite.com」

AI 会自动调对应的工具。

### 16 个工具

| 工具 | 干什么 |
|---|---|
| `list_specs` | 列出所有站 |
| `search_specs` | 按名字/域名/字体/颜色/变量名搜 |
| `get_spec` | 一个站的完整原始数据 |
| `get_section` | 某个分类下的所有站 |
| `get_design_spec` | 一个站归纳好的 9 章规范 |
| `list_design_specs` | 所有规范 + 覆盖度评分 |
| `get_components` | 组件变体与尺寸 |
| `get_states` | 实测的 hover/focus/active |
| `get_tokens` | 语义色 token |
| `get_semantics` | 语义映射后的完整 token 表 |
| `export_theme` | 导出 CSS 变量主题 |
| `compare_specs` | 多站共有特征 |
| **`suggest_tokens`** | **按用途推荐值** |
| **`compare_sites`** | **多站横向对比** |
| **`audit_page`** | **任意 URL 体检** |
| `corpus_stats` | 语料规模统计 |

---

## 四、直接拿 CSS 变量

```bash
python3 server.py theme t189 --raw > my-theme.css
```

生成的是标准化的变量集：

```css
:root{
  --color-primary: #f54e00;
  --color-background: #f7f7f4;
  --color-foreground: #26251e;
  --radius-sm: 4px;
  --radius-md: 8px;
  --radius-full: 9999px;
  --space-1: 4px;
  --space-2: 8px;
  ...
}
```

粘到项目里就能用。但**记得改**：这些是别人的设计，直接抄会撞脸。

---

## 用之前要知道的事

**1. 数据是「算出来的」，不是「问出来的」**

所有值来自浏览器 `getComputedStyle()`。原站没有设计文档，所以我们量了它们实际渲染成什么样。这意味着：

- ✅ 「这个按钮高 43px」——准确
- ❌ 「这个按钮为什么是 43px」——不知道

**2. 组件不完整**

只采到页面上真实出现的那几个变体。原站可能有 20 种按钮，页面上只展示了 5 种，我们就只有 5 种。

**3. 语义色有推断成分**

`primary` 这个角色，240 个站是从 CSS 变量名推断的，不是原站定义的。纯黑白灰的站（304 个）没有主色，这是对的，不是缺数据。

**4. 单页站数据少**

123 个站只扫到 1 页（它们确实没有子页面）。组件样本中位数 77 个，但这些站可能只有 9 个。

**5. 字体只有名字**

`figmaSans`、`Pin Sans` 这些是商业字体，数据里有名字但没有字体文件。

**6. 建议配合判断用**

`suggest_tokens` 给的是「行业最常见」，不是「最佳」。最常见的按钮高度是 32px，不代表 32px 最好。

---

## 出问题怎么办

**网页打不开** → 服务停了，重跑第一节的命令。

**MCP 连不上** → 检查 `python3` 路径对不对（`which python3`），确认文件存在。

**`audit` 超时** → 目标站太慢或反爬。换一个站试试。

**数据看起来不对** → 用 `python3 server.py get <id>` 看原始值，和网页对比。
