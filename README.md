# designspec — 544 个真实网站的设计规范库

用 headless Chrome 实测 544 个设计水准高的网站，把它们的**运行态样式**（`getComputedStyle`）
聚合成可查询、可对比、AI 可直接调用的设计规范。

不是抄的设计文档——是量出来的事实数据。

```
按钮该做多高？   → 32px (12.5%) / 36px (9.3%) / 40px (9.2%)
圆角用什么？     → 全圆 20.8% / 8px 20.1% / 6px 12.4%
正文字号？       → 16px 33.0% / 14px 29.2%
动效时长？       → 0.15s 26.1% / 0.2s 20.3%
间距基准？       → 8px 23.9% / 4px 15.1% / 12px 13.0%
```

## 数据规模

| 指标 | 值 |
|---|---|
| 站点 | 544（18 个分类） |
| 组件样本 | 56,258 |
| 排版阶梯 | 13,719 |
| 页面区块 | 5,124 |
| 每站平均扫描页数 | 2.9 |

## 快速开始

**环境：Python 3.9+，零第三方依赖。**

```bash
cd designspec
python3 server.py stats                # 库统计
python3 server.py suggest button       # 按钮的行业分布
python3 server.py spec t189            # Cursor 的 9 章规范
python3 server.py theme t189 --raw > theme.css   # 导出 CSS 变量
```

**接进 AI 工具（MCP）：**

```json
{
  "mcpServers": {
    "designspec": {
      "command": "python3",
      "args": ["/绝对路径/designspec/mcp_stdio.py"]
    }
  }
}
```

16 个工具：单站查询、行业推荐、跨站对比、任意网址设计体检、CSS 导出等。详见 [docs/usage.md](docs/usage.md)。

## 站点从哪来

- **目录来源**：收录范围基于 [Designeer](https://designeer.xyz)（Dhruv Jaradi 维护的策展目录）的工具列表与人物列表，外加 `llms-full.txt` 数据。感谢原目录的策展工作。
- **数据采集**：headless Chrome + CDP，每站扫描首页 + 最多 3 个子页面，全页滚动采样，展开 `<details>`，触发 hover/focus/active 状态，逐元素读 `getComputedStyle`。

## 目录结构

```
designspec/
├── specs_sem/        551 份原始实测数据（每站一份 JSON）
├── generated_v2/     544 份归纳规范（9 章：概览/色彩/排版/间距/圆角阴影/动效/组件/结构/无障碍）
├── themes/           每站 CSS 变量表
├── server.py         16 个查询工具 + CLI + MCP 入口
├── mcp_stdio.py      零依赖 MCP 服务器（stdio, JSON-RPC 2.0）
├── advice.py         suggest_tokens / compare_sites / audit_page
├── colorparse.py     完整 CSS 颜色解析（支持 lab/oklch/p3/color-mix）
├── queries.py        查询层
├── semantics.py      语义角色映射
├── gen_native.py     文档站生成器
└── taxonomy.py       分类体系
docs/                 schema / 局限性 / MCP 配置 / 用法
examples/             两个用本库推导的设计规范包（微信小程序 / 订货商城）
```

## 使用规范数据前，请读

1. **值是量出来的，不是设计意图。** 能告诉你"按钮高 43px"，不能告诉你为什么。
2. **组件不完整。** 只采到页面真实渲染的变体。
3. **主色 44% 是推断的**（240 站有推断主色；304 站本身是纯黑白灰设计，没有主色——这是正常的）。
4. **`suggest_tokens` 给的是"最常见"，不是"最佳"。**
5. **字体只有名字**，商业字体文件不在数据里。

完整局限见 [docs/limitations.md](docs/limitations.md)。

## 隐私说明

数据在发布前经过扫描：邮箱、电话等个人信息已替换为 `[REDACTED-EMAIL]` /
`[REDACTED-PHONE]` 占位符。如仍发现遗漏，请开 issue，会立即修复。

## 许可

- 代码：MIT
- 数据：CC BY 4.0（引用出处即可自由使用）

详见 [LICENSE](LICENSE)。
