# MCP 配置

## 服务器在哪

```
/绝对路径/designspec/mcp_stdio.py
```

零依赖版本，Python 3.8+ 可用。**不要用 `server.py`**，它需要 `mcp` 包（要求 Python ≥3.10）。

## 配置内容

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

## 配置位置

| 工具 | 路径 |
|---|---|
| Claude Desktop (macOS) | `~/Library/Application Support/Claude/claude_desktop_config.json` |
| Cursor | `~/.cursor/mcp.json` |
| 其他 | 查该工具的 MCP 文档 |

改完重启工具。

## 验证是否连上

在工具里问：

> 列出 designeer-designspec 的工具

应该看到 16 个。或者直接问：

> Cursor 官网用什么字体和字号？

## 16 个工具

### 查询类

| 工具 | 参数 | 说明 |
|---|---|---|
| `list_specs` | — | 列出所有站（544 个，返回较大） |
| `search_specs` | `query`, `section`, `limit` | 按名字/域名/字体/颜色/变量名搜 |
| `get_spec` | `spec_id` | 一个站的完整原始数据（约 190KB） |
| `get_section` | `section` | 某分类下所有站 |
| `corpus_stats` | — | 语料规模统计 |

### 规范类

| 工具 | 参数 | 说明 |
|---|---|---|
| `get_design_spec` | `spec_id` | 归纳后的 9 章规范（约 27KB） |
| `list_design_specs` | — | 所有规范 + 覆盖度评分 |
| `get_semantics` | `spec_id` | 语义 token 映射 |

### 组件类

| 工具 | 参数 | 说明 |
|---|---|---|
| `get_components` | `spec_id`, `kind` | 组件变体与尺寸 |
| `get_states` | `spec_id`, `state` | 实测 hover/focus/active |

### Token 类

| 工具 | 参数 | 说明 |
|---|---|---|
| `get_tokens` | `spec_id`, `role` | 语义色 token |
| `export_theme` | `spec_id`, `fmt` | 导出 CSS/JSON 主题 |

### 建议类（最实用）

| 工具 | 参数 | 说明 |
|---|---|---|
| `suggest_tokens` | `purpose`, `limit` | 按用途返回行业分布 |
| `compare_sites` | `ids` | 多站横向对比 |
| `audit_page` | `url`, `timeout`, `platform` | 任意 URL 体检 |

### 对比类

| 工具 | 参数 | 说明 |
|---|---|---|
| `compare_specs` | `ids` | 多站共有特征（圆角/动效/字体交集） |

## `suggest_tokens` 的可用用途

```
button      按钮
button-sm   小按钮
input       输入框
card        卡片
badge       徽标
nav         导航
tab         标签页
heading     标题
body        正文
radius      圆角
shadow      阴影
spacing     间距
duration    动效时长
easing      缓动曲线
primary     主色
```

## `audit_page` 的 platform 参数

| 值 | 点击目标基准 | 适用 |
|---|---|---|
| `desktop`（默认） | 32px | 桌面网站 |
| `mobile` | 44px | 移动端页面 |

## 返回体积注意

| 工具 | 返回大小 | 建议 |
|---|---|---|
| `list_specs` | ~90KB | 只在需要全清单时用 |
| `get_spec` | ~190KB | 只要部分数据时用专用工具 |
| `get_design_spec` | ~27KB | 推荐，够用且小 |
| `suggest_tokens` | ~4KB | 轻量 |
| `compare_sites` | ~2KB | 轻量 |

## 常见问题

**连不上** → 检查 `python3` 路径。用 `which python3` 确认，必要时写绝对路径。

**工具报错** → 先手动跑一次确认数据和代码没问题：

```bash
cd designspec
python3 server.py stats
```

**返回空** → 检查 `spec_id` 对不对。ID 格式是 `t001`–`t427`（工具站）、`p001`–`p132`（设计师）。
