#!/usr/bin/env python3
"""把 544 份设计规范全部生成成「浏览器原生界面语言」的文档站页面。

设计语言（取自 Chrome 内置页面）：
  纯白底 / 系统字体 / 单栏窄 / 左对齐 / 蓝色只用于链接和主按钮
  无卡片阴影 / 无渐变 / 分隔线 + 留白分区 / 胶囊按钮 / 8px 卡片圆角
"""
import json, re, html
from pathlib import Path

# ---------- 颜色工具（用完整解析器，支持 lab/oklch/color-mix）----------
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "designspec"))
from colorparse import to_hex, contrast

def wcag(r):
    if r is None: return "—"
    if r >= 7: return "AAA"
    if r >= 4.5: return "AA"
    if r >= 3: return "AA-large"
    return "未达标"

E = lambda s: html.escape(str(s if s is not None else ""))

# ---------- 页面骨架 ----------
CSS = """
:root{
  --bg:#fff; --ink:#202124; --ink-2:#3c4043; --ink-3:#5f6368; --ink-4:#80868b;
  --line:#dadce0; --line-2:#e8eaed; --blue:#1a73e8; --blue-h:#1765cc; --blue-bg:#e8f0fe;
  --red:#d93025; --green:#1e8e3e; --yellow:#f9ab00;
  --font:system-ui,-apple-system,"Segoe UI",Roboto,"Helvetica Neue",Arial,sans-serif;
  --mono:ui-monospace,SFMono-Regular,"SF Mono",Menlo,Consolas,monospace;
}
*{box-sizing:border-box}
html{scroll-behavior:smooth}
body{margin:0;background:var(--bg);color:var(--ink);font-family:var(--font);
  font-size:14px;line-height:1.6;-webkit-font-smoothing:antialiased}
a{color:var(--blue);text-decoration:none}
a:hover{text-decoration:underline}
.col{width:min(720px,calc(100% - 48px));margin:0 auto}
.col-wide{width:min(960px,calc(100% - 48px));margin:0 auto}

.bar{border-bottom:1px solid var(--line-2);position:sticky;top:0;background:#fff;z-index:50}
.bar-in{height:56px;display:flex;align-items:center;gap:24px;
  width:min(960px,calc(100% - 48px));margin:0 auto}
.brand{display:flex;align-items:center;gap:8px;font-size:15px;color:var(--ink);font-weight:500}
.bar-nav{display:flex;gap:20px;margin-left:auto}
.bar-nav a{font-size:13px;color:var(--ink-3)}
.bar-nav a:hover{color:var(--ink);text-decoration:none}

.hero{padding:80px 0 56px}
.crumb{font-size:13px;color:var(--ink-3);margin:0 0 16px}
.crumb a{color:var(--ink-3)}
.hero h1{margin:0 0 16px;font-size:34px;line-height:1.24;font-weight:400;letter-spacing:-.005em}
.hero h1 b{font-weight:500}
.hero p{margin:0 0 10px;max-width:560px;font-size:15px;line-height:1.65;color:var(--ink-2)}
.hero .meta{margin-top:20px;font-size:13px;color:var(--ink-3)}
.hero .meta span + span::before{content:" · ";color:var(--ink-4)}

.btn-row{display:flex;gap:12px;flex-wrap:wrap;margin-top:28px}
.btn{display:inline-flex;align-items:center;justify-content:center;gap:8px;
  height:36px;padding:0 24px;border-radius:100px;font-family:inherit;font-size:14px;
  font-weight:500;border:1px solid transparent;cursor:pointer;text-decoration:none;
  transition:background-color .15s ease,box-shadow .15s ease,border-color .15s ease}
.btn:hover{text-decoration:none}
.btn-fill{background:var(--blue);color:#fff}
.btn-fill:hover{background:var(--blue-h);box-shadow:0 1px 2px rgba(60,64,67,.3),0 1px 3px 1px rgba(60,64,67,.15)}
.btn-out{background:#fff;color:var(--blue);border-color:var(--line)}
.btn-out:hover{background:#f8f9fa}

.sec{padding:56px 0;border-top:1px solid var(--line-2)}
.sec:first-of-type{border-top:0}
.sec h2{margin:0 0 8px;font-size:22px;line-height:1.35;font-weight:400}
.sec .lead{margin:0 0 32px;max-width:560px;font-size:14px;line-height:1.65;color:var(--ink-3)}

.rows{margin:0;padding:0;list-style:none}
.row{display:grid;grid-template-columns:200px 1fr;gap:24px;padding:18px 0;
  border-bottom:1px solid var(--line-2);align-items:start}
.row:first-child{border-top:1px solid var(--line-2)}
.row .k{font-size:14px;color:var(--ink);font-weight:500}
.row .v{margin:0;font-size:14px;line-height:1.65;color:var(--ink-2)}
.row .v code{font-family:var(--mono);font-size:12.5px;background:#f1f3f4;
  padding:1px 5px;border-radius:3px;color:var(--ink-2)}

.swatches{display:flex;flex-wrap:wrap;gap:10px;margin:4px 0 20px}
.sw{width:88px}
.sw i{display:block;height:56px;border-radius:8px;border:1px solid rgba(0,0,0,.08)}
.sw code{display:block;margin-top:6px;font-family:var(--mono);font-size:11px;color:var(--ink-3);word-break:break-all}
.sw small{display:block;font-size:10px;color:var(--ink-4)}

.tbl{width:100%;border-collapse:collapse;font-size:13.5px}
.tbl th{text-align:left;padding:9px 12px;font-size:12px;font-weight:500;
  color:var(--ink-3);border-bottom:1px solid var(--line);white-space:nowrap}
.tbl td{padding:11px 12px;border-bottom:1px solid var(--line-2);color:var(--ink-2);vertical-align:middle}
.tbl td:first-child{color:var(--ink);font-weight:500}
.tbl .mono{font-family:var(--mono);font-size:12.5px}
.tbl .num{text-align:right;font-family:var(--mono);font-size:12.5px;color:var(--ink-3)}
.tbl tr:last-child td{border-bottom:1px solid var(--line-2)}

.typeRow td:nth-child(2){font-family:var(--mono)}
.typeSample{max-width:200px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;
  font-family:var(--font)!important;color:var(--ink-3);font-size:12px!important}

.bars{display:grid;gap:6px}
.barRow{display:grid;grid-template-columns:72px 1fr 44px;gap:12px;align-items:center;font-size:12.5px}
.barRow .lb{font-family:var(--mono);font-size:11.5px;color:var(--ink-3)}
.barRow .tr{height:6px;background:var(--line-2);border-radius:3px;overflow:hidden}
.barRow .tr i{display:block;height:100%;background:var(--blue);border-radius:3px;opacity:.75}
.barRow .n{text-align:right;font-family:var(--mono);font-size:11.5px;color:var(--ink-4)}

.radiusRow{display:flex;flex-wrap:wrap;gap:14px;margin:4px 0 16px}
.radiusItem{display:flex;flex-direction:column;align-items:center;gap:6px}
.radiusItem i{width:52px;height:52px;background:#f1f3f4;border:1px solid var(--line)}
.radiusItem code{font-family:var(--mono);font-size:10.5px;color:var(--ink-3)}
.radiusItem small{font-size:9.5px;color:var(--ink-4)}

.code{background:#f8f9fa;border:1px solid var(--line-2);border-radius:8px;overflow:hidden;margin:16px 0}
.code-h{display:flex;align-items:center;justify-content:space-between;padding:9px 16px;
  border-bottom:1px solid var(--line-2)}
.code-h span{font-size:12px;color:var(--ink-3);font-family:var(--mono)}
.code-h button{border:0;background:transparent;color:var(--blue);font-size:12px;
  font-family:inherit;cursor:pointer;padding:2px 6px;border-radius:3px}
.code-h button:hover{background:var(--blue-bg)}
.code pre{margin:0;padding:14px 16px;overflow:auto;font-family:var(--mono);
  font-size:12.5px;line-height:1.8;color:var(--ink-2);text-align:left;white-space:pre}

.note{background:#f8f9fa;border-radius:8px;padding:18px 22px;margin:20px 0}
.note p{margin:0;font-size:13px;line-height:1.7;color:var(--ink-2)}
.note p + p{margin-top:8px}
.note strong{font-weight:500;color:var(--ink)}

.callout{background:var(--blue-bg);border-radius:8px;padding:14px 18px;margin:16px 0;
  display:flex;gap:10px;align-items:flex-start}
.callout p{margin:0;font-size:13px;line-height:1.65;color:var(--ink-2)}
.callout svg{flex:none;margin-top:2px}

.status{display:inline-flex;align-items:center;gap:6px;font-size:12px;color:var(--ink-3)}
.status i{width:7px;height:7px;border-radius:50%;display:inline-block}
.status.ok i{background:var(--green)}
.status.warn i{background:var(--yellow)}
.status.err i{background:var(--red)}

.fold{border-bottom:1px solid var(--line-2)}
.fold summary{padding:16px 0;cursor:pointer;list-style:none;display:flex;
  justify-content:space-between;align-items:center;gap:16px;
  font-size:14px;color:var(--ink);font-weight:500}
.fold summary::-webkit-details-marker{display:none}
.fold summary::after{content:"";width:7px;height:7px;flex:none;
  border-right:1.5px solid var(--ink-4);border-bottom:1.5px solid var(--ink-4);
  transform:rotate(45deg);transition:transform .2s ease}
.fold[open] summary::after{transform:rotate(-135deg)}
.fold .body{padding:0 0 18px;font-size:14px;line-height:1.7;color:var(--ink-2)}

.foot{border-top:1px solid var(--line-2);padding:36px 0 56px;margin-top:24px}
.foot-in{width:min(960px,calc(100% - 48px));margin:0 auto;display:flex;
  justify-content:space-between;gap:20px;flex-wrap:wrap;font-size:12.5px;color:var(--ink-4)}
.foot-links{display:flex;gap:18px;flex-wrap:wrap}
.foot-links a{color:var(--ink-3);font-size:12.5px}
.foot-links a:hover{color:var(--ink);text-decoration:none}

@media(max-width:720px){
  .hero{padding:48px 0 36px}
  .hero h1{font-size:26px}
  .sec{padding:40px 0}
  .row{grid-template-columns:1fr;gap:6px;padding:14px 0}
  .bar-nav{display:none}
  .foot-in{flex-direction:column;gap:14px}
}
@media print{.bar,.btn-row,.foot{display:none}.sec{page-break-inside:avoid}}
"""

LOGO = '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#202124" stroke-width="1.8"><path d="M13 2L4 14h6l-1 8 9-12h-6l1-8z"/></svg>'
INFO_ICON = '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#1a73e8" stroke-width="2"><circle cx="12" cy="12" r="9"/><path d="M12 8v5M12 16h.01"/></svg>'

def shell(title, body, nav_right=""):
    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{E(title)}</title>
<style>{CSS}</style>
</head>
<body>
<div class="bar">
  <div class="bar-in">
    <a class="brand" href="../index.html" style="text-decoration:none">{LOGO}Designeer 规范</a>
    <nav class="bar-nav">{nav_right}</nav>
  </div>
</div>
{body}
<footer class="foot">
  <div class="foot-in">
    <span>数据取自运行态计算样式 · 2026-10-21</span>
    <div class="foot-links">
      <a href="../index.html">全部规范</a>
      <a href="https://designeer.xyz" target="_blank" rel="noreferrer">原目录</a>
    </div>
  </div>
</footer>
<script>
document.querySelectorAll("[data-copy]").forEach(b=>{{
  b.addEventListener("click", async()=>{{
    const t=b.textContent;
    try{{ await navigator.clipboard.writeText(b.dataset.copy); b.textContent="已复制"; }}
    catch{{ b.textContent="复制失败"; }}
    setTimeout(()=>b.textContent=t,1500);
  }});
}});
</script>
</body>
</html>"""

def build_page(doc):
    o = doc["overview"]
    c = doc["colors"]
    t = doc["typography"]
    s = doc["spacing"]
    sh = doc["shape"]
    comps = doc["components"]
    a11y = doc.get("accessibility") or {}
    roles = c.get("roles") or {}

    bg = to_hex((roles.get("background") or {}).get("hex") or (roles.get("background") or {}).get("value"))
    fg = to_hex((roles.get("foreground") or {}).get("hex") or (roles.get("foreground") or {}).get("value"))
    body_c = contrast(fg, bg)

    # ---- 色彩表 ----
    ORDER = [("primary","主色"),("secondary","次色"),("success","成功"),("warning","警告"),
             ("danger","危险"),("info","信息"),("foreground","正文"),("background","背景"),
             ("border","边框"),("muted","弱化"),("link","链接"),("disabled","禁用")]
    color_rows = []
    for key, label in ORDER:
        r = roles.get(key)
        if not r: continue
        hx = to_hex(r.get("hex") or r.get("value")) or r.get("value")
        ratio = r.get("contrastOnBg")
        lvl = wcag(ratio) if ratio is not None else "—"
        color_rows.append(f"""<tr>
          <td>{label}</td>
          <td class="mono">{E(hx)}</td>
          <td class="mono">{E(ratio) if ratio is not None else "—"}</td>
          <td>{E(lvl)}</td>
          <td class="mono" style="color:var(--ink-4);font-size:11.5px">{E(r.get("token") or "—")}</td>
        </tr>""")
    color_table = "\n".join(color_rows) or '<tr><td colspan="5" style="color:var(--ink-4)">未采集到语义色</td></tr>'

    # ---- 色板 ----
    ramp = c.get("neutralRamp") or []
    swatches = "".join(
        f'<div class="sw"><i style="background:{E(x["hex"])}"></i><code>{E(x["hex"])}</code><small>×{x.get("count","")}</small></div>'
        for x in ramp[:12]
    ) or '<p style="color:var(--ink-4);font-size:13px">未采集到</p>'

    # ---- 排版表 ----
    ladder = t.get("ladder") or []
    type_rows = "\n".join(f"""<tr class="typeRow">
      <td>{E(x.get("size"))}</td>
      <td>{E(x.get("weight") or "—")}</td>
      <td class="mono">{E(x.get("lineHeight") or "—")}</td>
      <td class="mono">{E(x.get("letterSpacing") or "—")}</td>
      <td class="mono">{E(x.get("family") or "—")}</td>
      <td class="num">{x.get("count","")}</td>
      <td class="typeSample">{E((x.get("samples") or [""])[0] or "")}</td>
    </tr>""" for x in ladder[:30]) or '<tr><td colspan="7" style="color:var(--ink-4)">未采集到</td></tr>'

    # ---- 间距 ----
    sp_ladder = s.get("ladder") or []
    sp_max = max([x.get("count") or 1 for x in sp_ladder] + [1])
    sp_bars = "".join(f"""<div class="barRow">
      <span class="lb">{E(x.get("value"))}</span>
      <span class="tr"><i style="width:{round((x.get("count") or 1)/sp_max*100)}%"></i></span>
      <span class="n">{x.get("count","")}</span>
    </div>""" for x in sp_ladder[:14]) or '<p style="color:var(--ink-4);font-size:13px">未采集到</p>'

    # ---- 圆角 ----
    radii = sh.get("radiusLadder") or []
    radius_items = "".join(
        f'<div class="radiusItem"><i style="border-radius:{E(x["value"])}"></i><code>{E(x["value"])}</code><small>×{x.get("count","")}</small></div>'
        for x in radii[:8]
    ) or '<p style="color:var(--ink-4);font-size:13px">未采集到</p>'

    # ---- 阴影 ----
    shadows = sh.get("shadows") or []
    shadow_items = "".join(
        f'<div class="radiusItem"><i style="border-radius:8px;box-shadow:{E(x["value"])};background:#fff;width:64px;height:44px"></i><code style="font-size:9.5px">×{x.get("count","")}</code></div>'
        for x in shadows[:6]
    ) or ""

    # ---- 组件 ----
    comp_blocks = []
    for kind, data in list(comps.items())[:10]:
        samples = data.get("samples") or {}
        size_names = list(samples.keys())
        rows = []
        for sz in size_names:
            for r in (samples[sz] or [])[:3]:
                rows.append(f"""<tr>
                  <td>{E(sz)}</td>
                  <td class="mono">{E(r.get("height"))}px</td>
                  <td class="mono">{E(r.get("padding") or "—")}</td>
                  <td class="mono">{E(r.get("radius") or "—")}</td>
                  <td class="mono">{E(r.get("fontSize") or "—")}/{E(r.get("fontWeight") or "—")}</td>
                  <td class="mono" style="font-size:11px">{E((r.get("background") or "")[:26])}</td>
                  <td class="typeSample">{E((r.get("text") or "")[:20])}</td>
                </tr>""")
        if not rows: continue
        comp_blocks.append(f"""<h3 style="margin:28px 0 10px;font-size:16px;font-weight:500">
          {E(data.get("label") or kind)} <span style="color:var(--ink-4);font-weight:400;font-size:12.5px">（{data.get("count",0)} 个样本）</span>
        </h3>
        <table class="tbl">
          <thead><tr><th>尺寸</th><th>高度</th><th>内边距</th><th>圆角</th><th>字号/字重</th><th>背景</th><th>示例</th></tr></thead>
          <tbody>{''.join(rows)}</tbody>
        </table>""")

    # ---- 区块 ----
    secs = doc.get("sections") or []
    sec_rows = "".join(f"""<tr>
      <td class="mono" style="color:var(--ink-4)">{i+1}</td>
      <td>{E(x.get("tag"))}</td>
      <td class="mono">{E(x.get("height"))}px</td>
      <td class="mono">{E(x.get("padding") or "—")}</td>
      <td class="typeSample">{E((x.get("heading") or "")[:32])}</td>
    </tr>""" for i, x in enumerate(secs[:16])) or '<tr><td colspan="5" style="color:var(--ink-4)">未采集到</td></tr>'

    # ---- 动效 ----
    mo = doc.get("motion") or {}
    dur = mo.get("durations") or []
    eas = mo.get("easings") or []
    if dur or eas:
        dur_bars = "".join(f"""<div class="barRow">
          <span class="lb">{E(x.get("value"))}</span>
          <span class="tr"><i style="width:{round((x.get("count") or 1)/max([y.get("count") or 1 for y in dur]+[1])*100)}%"></i></span>
          <span class="n">{x.get("count","")}</span>
        </div>""" for x in dur[:8])
        eas_rows = "".join(f'<li class="row"><span class="k mono" style="font-size:12px">{E(x.get("value"))}</span>'
                           f'<span class="v">出现 {x.get("count","")} 次</span></li>' for x in eas[:6])
        motion_section = f"""<section class="sec">
  <div class="col">
    <h2>动效</h2>
    <p class="lead">页面上实际使用的过渡时长与缓动曲线。</p>
    <h3 style="margin:0 0 12px;font-size:15px;font-weight:500">时长</h3>
    <div class="bars">{dur_bars or '<p style="color:var(--ink-4);font-size:13px">未采集到</p>'}</div>
    <h3 style="margin:24px 0 12px;font-size:15px;font-weight:500">缓动</h3>
    <ul class="rows">{eas_rows or '<li class="row"><span class="k">—</span><span class="v">未采集到</span></li>'}</ul>
  </div>
</section>"""
    else:
        motion_section = ""

    pages = o.get("pagesScanned") or []
    pages_line = " · ".join(E(p.replace("https://","").replace("http://","")) for p in pages[:4])

    body = f"""
<header class="hero">
  <div class="col">
    <p class="crumb"><a href="../index.html">全部规范</a> / {E(o.get("section") or "")}</p>
    <h1>{E(o.get("name"))}<b> 的设计规范</b></h1>
    <p>从 {len(pages)} 个页面的运行态采集：{o.get("componentSamples",0)} 个组件样本、{o.get("typeSteps",0)} 档排版、{o.get("sectionCount",0)} 个页面区块。</p>
    <p class="meta">
      <span>正文 {E(t.get("bodySize") or (max(ladder, key=lambda x: x.get("count") or 0).get("size") if ladder else "—"))}</span>
      <span>主色 {E(to_hex((roles.get("primary") or {}).get("hex")) or "中性")}</span>
      <span>{len(comps)} 类组件</span>
    </p>
    <div class="btn-row">
      <a class="btn btn-fill" href="{E(o.get("url"))}" target="_blank" rel="noreferrer">打开原站</a>
      <a class="btn btn-out" href="#components">查看组件</a>
    </div>
  </div>
</header>

<section class="sec">
  <div class="col">
    <h2>概览</h2>
    <p class="lead">采集范围与页面基本信息。</p>
    <ul class="rows">
      <li class="row"><span class="k">站点</span><span class="v"><a href="{E(o.get("url"))}" target="_blank" rel="noreferrer">{E(o.get("url"))}</a></span></li>
      <li class="row"><span class="k">分类</span><span class="v">{E(o.get("section"))}</span></li>
      <li class="row"><span class="k">扫描页面</span><span class="v">{pages_line or "—"}</span></li>
      <li class="row"><span class="k">组件样本</span><span class="v">{o.get("componentSamples",0)} 个</span></li>
      <li class="row"><span class="k">排版组合</span><span class="v">{t.get("totalSteps",0)} 种</span></li>
      <li class="row"><span class="k">页面区块</span><span class="v">{o.get("sectionCount",0)} 个</span></li>
    </ul>
  </div>
</section>

<section class="sec">
  <div class="col">
    <h2>色彩</h2>
    <p class="lead">按功能角色归类。对比度以背景色为基准，遵循 WCAG 2.1。</p>
    <table class="tbl">
      <thead><tr><th>角色</th><th>色值</th><th>对比度</th><th>等级</th><th>原始 token</th></tr></thead>
      <tbody>{color_table}</tbody>
    </table>
    <h3 style="margin:28px 0 12px;font-size:15px;font-weight:500">实测色板</h3>
    <div class="swatches">{swatches}</div>
  </div>
</section>

<section class="sec">
  <div class="col-wide">
    <h2>排版</h2>
    <p class="lead">全站文字元素的字号 / 字重 / 行高 / 字距组合，按出现频次排序。共 {t.get("totalSteps",0)} 种。</p>
    <table class="tbl">
      <thead><tr><th>字号</th><th>字重</th><th>行高</th><th>字距</th><th>字族</th><th style="text-align:right">出现</th><th>示例</th></tr></thead>
      <tbody>{type_rows}</tbody>
    </table>
    <div class="note">
      <p><strong>字族：</strong>{E(" · ".join(t.get("families") or ["系统默认"]))}</p>
      <p><strong>字重：</strong>{E(" · ".join(t.get("weights") or ["—"]))}</p>
    </div>
  </div>
</section>

<section class="sec">
  <div class="col">
    <h2>间距</h2>
    <p class="lead">{("推断基准单位 <b>" + str(s.get("inferredBaseUnit")) + "px</b>，下列档位多数是其整数倍。") if s.get("inferredBaseUnit") else "未形成统一基准网格。"}</p>
    <div class="bars">{sp_bars}</div>
  </div>
</section>

<section class="sec">
  <div class="col">
    <h2>圆角与阴影</h2>
    <p class="lead">页面上实际出现的圆角值与阴影。</p>
    <div class="radiusRow">{radius_items}</div>
    {('<h3 style="margin:24px 0 12px;font-size:15px;font-weight:500">阴影</h3><div class="radiusRow">' + shadow_items + '</div>') if shadow_items else ''}
  </div>
</section>

{motion_section}

<section class="sec" id="components">
  <div class="col-wide">
    <h2>组件</h2>
    <p class="lead">共 {len(comps)} 类组件。每类按尺寸档列出实际样式。</p>
    {''.join(comp_blocks) if comp_blocks else '<p style="color:var(--ink-4);font-size:13px">未采集到组件</p>'}
  </div>
</section>

<section class="sec">
  <div class="col">
    <h2>页面结构</h2>
    <p class="lead">按文档顺序排列的主要区块，反映页面的节奏与分区方式。</p>
    <table class="tbl">
      <thead><tr><th>#</th><th>区块</th><th>高度</th><th>内边距</th><th>标题</th></tr></thead>
      <tbody>{sec_rows}</tbody>
    </table>
  </div>
</section>

<section class="sec">
  <div class="col">
    <h2>无障碍</h2>
    <p class="lead">按 WCAG 2.1 检查正文对比度与点击目标。</p>
    <ul class="rows">
      <li class="row"><span class="k">正文对比度</span><span class="v">{E(body_c) if body_c is not None else "—"} {("（" + wcag(body_c) + "）") if body_c is not None else ""}</span></li>
      <li class="row"><span class="k">点击目标中位</span><span class="v">{E(a11y.get("tapTargetMedian")) if a11y.get("tapTargetMedian") is not None else "—"} px</span></li>
      <li class="row"><span class="k">点击目标最小</span><span class="v">{E(a11y.get("tapTargetMin")) if a11y.get("tapTargetMin") is not None else "—"} px</span></li>
    </ul>
    <div class="callout">
      {INFO_ICON}
      <p>这些值是浏览器算出来的，不是原站的设计文档。原站没写规范，就没有「官方规范」可搬。</p>
    </div>
  </div>
</section>
"""
    return shell(f"{o.get('name')} 的设计规范 · Designeer", body,
                 f'<a href="../index.html">全部规范</a>')

def build_index(docs):
    """索引页：544 份规范，按分类分组"""
    from collections import defaultdict
    groups = defaultdict(list)
    for d in docs:
        groups[d["overview"].get("section") or "未分类"].append(d)

    order = sorted(groups.keys(), key=lambda k: -len(groups[k]))
    blocks = []
    for sec in order:
        rows = []
        for d in sorted(groups[sec], key=lambda x: (x["overview"].get("name") or "").lower()):
            o = d["overview"]
            roles = d["colors"].get("roles") or {}
            primary = to_hex((roles.get("primary") or {}).get("hex"))
            dot = f'<span style="display:inline-block;width:8px;height:8px;border-radius:50%;background:{primary};margin-right:8px;vertical-align:middle"></span>' if primary else ""
            rows.append(f"""<tr>
              <td>{dot}<a href="site/{E(d["id"])}.html">{E(o.get("name"))}</a></td>
              <td class="mono" style="font-size:12px;color:var(--ink-3)">{E((o.get("url") or "").replace("https://","").replace("http://","")[:40])}</td>
              <td class="num">{o.get("componentSamples",0)}</td>
              <td class="num">{o.get("typeSteps",0)}</td>
            </tr>""")
        blocks.append(f"""
<section class="sec">
  <div class="col-wide">
    <h2>{E(sec)} <span style="color:var(--ink-4);font-weight:400;font-size:14px">{len(groups[sec])} 份</span></h2>
    <table class="tbl">
      <thead><tr><th>站点</th><th>域名</th><th style="text-align:right">组件样本</th><th style="text-align:right">排版档</th></tr></thead>
      <tbody>{''.join(rows)}</tbody>
    </table>
  </div>
</section>""")

    body = f"""
<header class="hero">
  <div class="col">
    <h1>设计规范库<b>：{len(docs)} 个站</b></h1>
    <p>每个站扫描首页加最多 3 个子页面，全页滚动采样。共 {sum(d["overview"].get("componentSamples",0) for d in docs):,} 个组件样本。</p>
    <p class="meta"><span>{len(order)} 个分类</span><span>{sum(len(d.get("components") or {}) for d in docs):,} 条组件记录</span></p>
  </div>
</header>
{''.join(blocks)}
"""
    return shell("设计规范库 · Designeer", body, f'<a href="index.html">全部规范</a>')

def main():
    root = Path(__file__).resolve().parent.parent
    src = root / "designspec" / "generated_v2"
    out = root / "site"
    (out / "site").mkdir(parents=True, exist_ok=True)

    docs = []
    for p in sorted(src.glob("*.json")):
        try:
            d = json.loads(p.read_text())
            if d.get("id"): docs.append(d)
        except Exception:
            continue

    n = 0
    for d in docs:
        try:
            (out / "site" / f"{d['id']}.html").write_text(build_page(d))
            n += 1
        except Exception as e:
            print("skip", d.get("id"), type(e).__name__, e)

    (out / "index.html").write_text(build_index(docs))
    print(f"生成 {n} 个站点页 + 1 个索引页")
    total = sum(p.stat().st_size for p in (out / "site").glob("*.html"))
    print(f"总体积 {total/1024/1024:.1f} MB")

if __name__ == "__main__":
    main()
