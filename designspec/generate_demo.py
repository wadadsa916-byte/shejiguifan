"""为每份设计规范生成一个可运行的样式示范页（demo）。

示范页用该站的 token 渲染一整套真实组件：按钮全变体、输入框、卡片、
标签页、徽标、表格、提示条、表单、分页、空状态等，让规范「看得见」。
"""
import json, html
from pathlib import Path

def pick(ladder, idx, default):
    try:
        return ladder[idx].get("value") or default
    except Exception:
        return default

def build_demo(doc):
    o = doc["overview"]
    c = doc["colors"]["roles"]
    t = doc["typography"]
    s = doc["spacing"]
    sh = doc["shape"]
    m = doc["motion"]
    comps = doc["components"]

    bg = (c.get("background") or {}).get("hex") or "#ffffff"
    fg = (c.get("foreground") or {}).get("hex") or "#111111"
    primary = (c.get("primary") or {}).get("hex")
    secondary = (c.get("secondary") or {}).get("hex")
    danger = (c.get("danger") or {}).get("hex") or "#c0392b"
    success = (c.get("success") or {}).get("hex") or "#2e7d32"
    warning = (c.get("warning") or {}).get("hex") or "#b7791f"
    border = (c.get("border") or {}).get("hex")

    if not primary:
        # 中性站：用前景色做「主色」，靠深浅区分
        primary = fg

    # 中性阶：从 neutralRamp 取
    ramp = [x["hex"] for x in (doc["colors"].get("neutralRamp") or [])]
    def neutral(i, fallback):
        return ramp[i] if len(ramp) > i else fallback
    surface = neutral(0, "#f7f7f7")
    border_c = border or neutral(1, "rgba(0,0,0,.12)")

    # 字体
    fam = (t.get("families") or [])
    font_stack = t.get("bodyFont") or (", ".join(fam) if fam else "system-ui, sans-serif")
    body_size = t.get("bodySize") or "16px"
    body_lh = t.get("bodyLineHeight") or "1.5"

    # 字号档
    ladder = t.get("sizeLadder") or []
    def size_at(frac, fallback):
        if not ladder: return fallback
        i = min(len(ladder)-1, int(len(ladder) * frac))
        return ladder[i].get("value") or fallback
    fs_h1 = size_at(0.95, "40px")
    fs_h2 = size_at(0.8, "28px")
    fs_h3 = size_at(0.65, "20px")
    fs_sm = size_at(0.2, "13px")

    # 圆角
    rl = [x.get("value") for x in (sh.get("radiusLadder") or [])]
    r_sm = rl[0] if rl else "6px"
    r_md = rl[min(1, len(rl)-1)] if rl else "8px"
    r_lg = rl[min(2, len(rl)-1)] if rl else "12px"
    r_full = "9999px"

    # 间距
    sp = [x.get("value") for x in (s.get("ladder") or [])]
    def gap(i, fb):
        return sp[i] if len(sp) > i else fb
    g1, g2, g3, g4 = gap(0,"4px"), gap(2,"8px"), gap(4,"16px"), gap(6,"24px")

    # 动效
    dur = (m.get("durations") or [])
    d_fast = dur[0]["value"] if dur else ".15s"
    d_norm = dur[min(1,len(dur)-1)]["value"] if dur else ".25s"
    ease = (m.get("easings") or [{}])[0].get("value") or "ease"
    if "cubic" not in str(ease) and "ease" not in str(ease): ease = "ease"

    # 组件尺寸参考
    btn = comps.get("button") or {}
    btn_variants = list((btn.get("variants") or {}).keys())
    btn_sizes = {}
    for v, sizes in (btn.get("variants") or {}).items():
        for sz, r in sizes.items():
            btn_sizes.setdefault(sz, r)
    h_md = btn_sizes.get("md", {}).get("height") or 40
    h_sm = btn_sizes.get("sm", {}).get("height") or 32
    h_lg = btn_sizes.get("lg", {}).get("height") or 48
    pad_md = btn_sizes.get("md", {}).get("padding") or f"0 16px"
    btn_radius = btn_sizes.get("md", {}).get("radius") or r_md
    btn_weight = btn_sizes.get("md", {}).get("fontWeight") or "500"

    name = html.escape(o.get("name") or "")
    url = html.escape(o.get("url") or "")
    section = html.escape(o.get("section") or "")

    css_vars = f"""
  --bg:{bg}; --surface:{surface}; --text:{fg}; --primary:{primary};
  --danger:{danger}; --success:{success}; --warning:{warning};
  --border:{border_c}; --radius-sm:{r_sm}; --radius-md:{r_md}; --radius-lg:{r_lg}; --radius-full:{r_full};
  --space-1:{g1}; --space-2:{g2}; --space-3:{g3}; --space-4:{g4};
  --font:{font_stack}; --fs-body:{body_size}; --lh-body:{body_lh};
  --fs-h1:{fs_h1}; --fs-h2:{fs_h2}; --fs-h3:{fs_h3}; --fs-sm:{fs_sm};
  --dur-fast:{d_fast}; --dur:{d_norm}; --ease:{ease};
  --btn-h:{h_md}px; --btn-h-sm:{h_sm}px; --btn-h-lg:{h_lg}px;
  --btn-pad:{pad_md}; --btn-radius:{btn_radius}; --btn-weight:{btn_weight};
"""

    # 该站真实抓到的变体
    captured = [v for v in btn_variants if v in ("primary","secondary","outline","text","danger")]
    # 规范示范总是补齐到 four 种（真实变体标实心，其余为推导）
    show = list(dict.fromkeys(captured + ["primary","secondary","outline","text"]))
    LABEL = {"primary":"主按钮","secondary":"次按钮","outline":"描边","text":"文字按钮","danger":"危险"}
    variant_buttons = "".join(
        f'<button class="btn btn-{v}">{LABEL.get(v, v.title())}'
        + ('' if v in captured else '<sup style="opacity:.45;font-size:9px">推算</sup>')
        + '</button>'
        for v in show
    )

    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{name} · 设计规范示范</title>
<style>
:root {{{css_vars}}}
* {{ box-sizing: border-box; }}
body {{
  margin:0; background:var(--bg); color:var(--text);
  font-family:var(--font); font-size:var(--fs-body); line-height:var(--lh-body);
  padding: 0 0 80px;
}}
.wrap {{ width:min(1080px, calc(100% - 40px)); margin:0 auto; }}
.demo-head {{
  padding: 48px 0 28px; border-bottom:1px solid var(--border);
}}
.crumb {{ font-size:var(--fs-sm); color:var(--text); opacity:.55; margin-bottom:10px; }}
h1 {{ font-size:var(--fs-h1); line-height:1.1; margin:0 0 12px; font-weight:700; letter-spacing:-.02em; }}
h2 {{ font-size:var(--fs-h2); line-height:1.2; margin:44px 0 8px; font-weight:600; }}
h3 {{ font-size:var(--fs-h3); margin:26px 0 10px; font-weight:600; }}
.lead {{ opacity:.7; margin:0; max-width:44rem; }}
.chips {{ display:flex; gap:6px; flex-wrap:wrap; margin-top:16px; }}
.chip {{
  padding: 3px 9px; border-radius:var(--radius-full);
  border:1px solid var(--border); font-size:var(--fs-sm); opacity:.8;
}}

/* 按钮 */
.btn {{
  height:var(--btn-h); padding:var(--btn-pad); border-radius:var(--btn-radius);
  font-family:inherit; font-size:var(--fs-body); font-weight:var(--btn-weight);
  border:1px solid transparent; cursor:pointer; display:inline-flex; align-items:center;
  transition: background var(--dur-fast) var(--ease), color var(--dur-fast) var(--ease),
              border-color var(--dur-fast) var(--ease), transform var(--dur-fast) var(--ease);
}}
.btn:active {{ transform: scale(.98); }}
.btn-primary {{ background:var(--primary); color:#fff; }}
.btn-primary:hover {{ opacity:.9; }}
.btn-secondary {{ background:var(--surface); color:var(--text); border-color:var(--border); }}
.btn-secondary:hover {{ background:var(--bg); }}
.btn-outline {{ background:transparent; color:var(--primary); border-color:var(--primary); }}
.btn-outline:hover {{ background:var(--primary); color:#fff; }}
.btn-text {{ background:transparent; color:var(--primary); padding-left:0; padding-right:0; }}
.btn-danger {{ background:var(--danger); color:#fff; }}
.btn[disabled] {{ opacity:.45; cursor:not-allowed; }}
.btn-sm {{ height:var(--btn-h-sm); font-size:var(--fs-sm); }}
.btn-lg {{ height:var(--btn-h-lg); }}
.row {{ display:flex; gap:var(--space-2); flex-wrap:wrap; align-items:center; }}

/* 表单 */
.field {{ margin-bottom:var(--space-3); max-width:420px; }}
.field label {{ display:block; font-size:var(--fs-sm); font-weight:600; margin-bottom:6px; }}
.field input, .field select, .field textarea {{
  width:100%; height:var(--btn-h); padding:0 12px; font-family:inherit; font-size:var(--fs-body);
  color:var(--text); background:var(--bg); border:1px solid var(--border);
  border-radius:var(--radius-md); outline:none;
  transition: border-color var(--dur-fast) var(--ease), box-shadow var(--dur-fast) var(--ease);
}}
.field input:focus {{ border-color:var(--primary); box-shadow:0 0 0 3px color-mix(in srgb, var(--primary) 18%, transparent); }}
.field .hint {{ font-size:var(--fs-sm); opacity:.55; margin-top:5px; }}
.field.error input {{ border-color:var(--danger); }}
.field.error .hint {{ color:var(--danger); opacity:1; }}

/* 卡片 */
.cards {{ display:grid; grid-template-columns:repeat(auto-fill,minmax(260px,1fr)); gap:var(--space-3); }}
.card {{
  background:var(--surface); border:1px solid var(--border); border-radius:var(--radius-lg);
  padding:var(--space-3); transition: transform var(--dur) var(--ease), box-shadow var(--dur) var(--ease);
}}
.card:hover {{ transform:translateY(-2px); box-shadow:0 10px 24px rgba(0,0,0,.08); }}
.card h4 {{ margin:0 0 6px; font-size:var(--fs-h3); font-weight:600; }}
.card p {{ margin:0; font-size:var(--fs-sm); opacity:.7; }}

/* 徽标 */
.badge {{ display:inline-block; padding:2px 9px; border-radius:var(--radius-full);
  font-size:var(--fs-sm); font-weight:600; }}
.badge-primary {{ background:color-mix(in srgb, var(--primary) 14%, transparent); color:var(--primary); }}
.badge-success {{ background:color-mix(in srgb, var(--success) 14%, transparent); color:var(--success); }}
.badge-warning {{ background:color-mix(in srgb, var(--warning) 14%, transparent); color:var(--warning); }}
.badge-danger  {{ background:color-mix(in srgb, var(--danger) 14%, transparent); color:var(--danger); }}

/* 标签页 */
.tabs {{ display:flex; gap:var(--space-1); border-bottom:1px solid var(--border); margin-bottom:var(--space-3); }}
.tab {{ padding:10px 14px; font-size:var(--fs-body); color:var(--text); opacity:.6;
  cursor:pointer; border:none; background:none; border-bottom:2px solid transparent;
  font-family:inherit; transition: color var(--dur-fast) var(--ease), border-color var(--dur-fast) var(--ease); }}
.tab.active {{ opacity:1; color:var(--primary); border-bottom-color:var(--primary); font-weight:600; }}

/* 表格 */
table {{ width:100%; border-collapse:collapse; font-size:var(--fs-sm); }}
th, td {{ text-align:left; padding:10px 12px; border-bottom:1px solid var(--border); }}
th {{ font-weight:600; opacity:.7; }}

/* 提示条 */
.alert {{ padding:12px 14px; border-radius:var(--radius-md); border:1px solid var(--border);
  font-size:var(--fs-sm); display:flex; gap:10px; align-items:flex-start; margin-bottom:var(--space-2); }}
.alert-success {{ border-color:var(--success); background:color-mix(in srgb, var(--success) 8%, transparent); }}
.alert-warning {{ border-color:var(--warning); background:color-mix(in srgb, var(--warning) 8%, transparent); }}
.alert-danger  {{ border-color:var(--danger);  background:color-mix(in srgb, var(--danger) 8%, transparent); }}

/* 其他 */
.kv {{ display:grid; grid-template-columns:120px 1fr; gap:8px 16px; font-size:var(--fs-sm); }}
.kv dt {{ opacity:.55; }}
.kv dd {{ margin:0; }}
footer {{ margin-top:56px; padding-top:20px; border-top:1px solid var(--border); font-size:var(--fs-sm); opacity:.55; }}
footer a {{ color:var(--primary); }}
</style>
</head>
<body>
<div class="wrap">
  <header class="demo-head">
    <div class="crumb">设计规范示范 · {section}</div>
    <h1>{name} 的界面示范</h1>
    <p class="lead">这个页面只用 {name} 的规范变量渲染：配色、字体、圆角、间距、动效全部取自该站实测数据。</p>
    <div class="chips">
      <span class="chip">正文 {body_size}</span>
      <span class="chip">主色 {primary}</span>
      <span class="chip">圆角 {r_md}</span>
      <span class="chip">间距基准 {s.get("inferredBaseUnit") or "—"}px</span>
    </div>
  </header>

  <h2>按钮</h2>
  <p class="lead">该站实际采集到的按钮变体与尺寸。</p>
  <div class="row" style="margin-top:14px">{variant_buttons}</div>
  <div class="row" style="margin-top:12px">
    <button class="btn btn-primary btn-sm">小号</button>
    <button class="btn btn-primary">中号</button>
    <button class="btn btn-primary btn-lg">大号</button>
    <button class="btn btn-primary" disabled>禁用</button>
  </div>

  <h2>表单</h2>
  <div class="field">
    <label>项目名称</label>
    <input type="text" placeholder="输入名称">
    <div class="hint">用于标识这个项目</div>
  </div>
  <div class="field error">
    <label>邮箱</label>
    <input type="email" value="not-an-email">
    <div class="hint">邮箱格式不正确</div>
  </div>
  <div class="field">
    <label>描述</label>
    <textarea rows="3" placeholder="补充说明"></textarea>
  </div>

  <h2>卡片</h2>
  <div class="cards">
    <div class="card"><h4>开始使用</h4><p>用模板快速搭建第一个项目。</p></div>
    <div class="card"><h4>团队协作</h4><p>邀请成员，共享同一份设计规范。</p></div>
    <div class="card"><h4>发布上线</h4><p>一键部署，自动同步变量。</p></div>
  </div>

  <h2>徽标</h2>
  <div class="row">
    <span class="badge badge-primary">默认</span>
    <span class="badge badge-success">已完成</span>
    <span class="badge badge-warning">待处理</span>
    <span class="badge badge-danger">已失败</span>
  </div>

  <h2>标签页</h2>
  <div class="tabs">
    <button class="tab active">全部</button>
    <button class="tab">进行中</button>
    <button class="tab">已完成</button>
  </div>

  <h2>提示条</h2>
  <div class="alert alert-success"><strong>成功</strong><span>变更已保存。</span></div>
  <div class="alert alert-warning"><strong>注意</strong><span>该操作会影响 3 个项目。</span></div>
  <div class="alert alert-danger"><strong>错误</strong><span>保存失败，请重试。</span></div>

  <h2>表格</h2>
  <table>
    <thead><tr><th>名称</th><th>状态</th><th>更新时间</th></tr></thead>
    <tbody>
      <tr><td>首页改版</td><td><span class="badge badge-success">已完成</span></td><td>2 小时前</td></tr>
      <tr><td>组件库升级</td><td><span class="badge badge-warning">待处理</span></td><td>昨天</td></tr>
      <tr><td>文档整理</td><td><span class="badge badge-primary">进行中</span></td><td>3 天前</td></tr>
    </tbody>
  </table>

  <h2>规范摘要</h2>
  <dl class="kv">
    <dt>正文字号</dt><dd>{body_size} / 行高 {body_lh}</dd>
    <dt>字体</dt><dd>{" · ".join(fam) if fam else "系统默认"}</dd>
    <dt>圆角</dt><dd>{" · ".join(rl[:5]) if rl else "—"}</dd>
    <dt>间距</dt><dd>{" · ".join(sp[:8]) if sp else "—"}</dd>
    <dt>动效</dt><dd>{d_fast} · {d_norm} · {ease}</dd>
  </dl>

  <footer>
    示范页由 <a href="{url}" target="_blank" rel="noreferrer">{name}</a> 的实测规范生成。
    规范来源：运行态计算样式，2026-10-21。
  </footer>
</div>
</body>
</html>"""

def main():
    src = Path("generated")
    out = Path("demos")
    out.mkdir(exist_ok=True)
    n = 0
    for p in sorted(src.glob("*.json")):
        doc = json.loads(p.read_text())
        (out / f"{doc['id']}.html").write_text(build_demo(doc))
        n += 1
    print("生成示范页:", n)

if __name__ == "__main__":
    main()
