"""三个面向实际使用的分析工具：
   suggest_tokens  —— 按用途推荐 token（基于 544 站的实际分布）
   compare_sites   —— 多站横向对比
   audit_page      —— 抓一个 URL，检查它偏离行业惯例的地方
"""
import json, re, statistics

import queries as _queries
from pathlib import Path
from collections import Counter, defaultdict

ROOT = Path(__file__).resolve().parent
GEN = ROOT / "generated_v2"

_cache = {"docs": None, "ts": 0}

def docs():
    import time
    if _cache["docs"] is not None and time.time() - _cache["ts"] < 10:
        return _cache["docs"]
    out = []
    for p in sorted(GEN.glob("*.json")):
        try:
            d = json.loads(p.read_text())
            if d.get("id"): out.append(d)
        except Exception:
            continue
    _cache["docs"] = out
    _cache["ts"] = time.time()
    return out

# ---------- 用途 → 采集路径 的映射 ----------
PURPOSES = {
    "button":   ("components.button", "按钮"),
    "button-sm":("components.button", "小按钮"),
    "input":    ("components.input", "输入框"),
    "card":     ("components.card", "卡片"),
    "badge":    ("components.badge", "徽标"),
    "nav":      ("components.nav", "导航"),
    "tab":      ("components.tabs", "标签页"),
    "heading":  ("components.heading", "标题"),
    "body":     ("typography", "正文"),
    "radius":   ("shape.radiusLadder", "圆角"),
    "shadow":   ("shape.shadows", "阴影"),
    "spacing":  ("spacing.ladder", "间距"),
    "duration": ("motion.durations", "动效时长"),
    "easing":   ("motion.easings", "缓动曲线"),
    "primary":  ("colors.roles.primary", "主色"),
}

def _get_path(doc, path):
    cur = doc
    for key in path.split("."):
        if not isinstance(cur, dict): return None
        cur = cur.get(key)
        if cur is None: return None
    return cur

def suggest_tokens(purpose, limit=10):
    """按用途统计全库的实际取值分布。"""
    key = (purpose or "").strip().lower()
    if key not in PURPOSES:
        return {"error": f"未知用途：{purpose}", "available": sorted(PURPOSES.keys())}
    path, label = PURPOSES[key]

    scalar = Counter()          # 标量型用途
    fieldCounters = defaultdict(Counter)   # 组件型用途：字段 → 值
    per_site = 0

    for d in docs():
        node = _get_path(d, path)
        if not node: continue
        found = False

        if path.startswith("components."):
            samples = (node or {}).get("samples") or {}
            for sz, rows in samples.items():
                for r in (rows or []):
                    if not isinstance(r, dict): continue
                    for field in ("height", "radius", "fontSize", "fontWeight"):
                        v = r.get(field)
                        if v in (None, "", "0px", 0, "0"): continue
                        fieldCounters[field][str(v)] += 1
                        found = True
        elif path == "shape.radiusLadder":
            for x in node[:8]:
                v = x.get("value")
                if v: scalar[v] += x.get("count", 1); found = True
        elif path == "spacing.ladder":
            for x in node[:12]:
                v = x.get("value")
                if v: scalar[v] += x.get("count", 1); found = True
        elif path == "motion.durations":
            for x in node[:8]:
                v = x.get("value")
                if v: scalar[v] += x.get("count", 1); found = True
        elif path == "motion.easings":
            for x in node[:6]:
                v = x.get("value")
                if v: scalar[v] += x.get("count", 1); found = True
        elif path == "shape.shadows":
            for x in node[:5]:
                v = x.get("value")
                if v: scalar[v] += x.get("count", 1); found = True
        elif path == "typography":
            for x in (node.get("ladder") or [])[:20]:
                v = x.get("size")
                if v: scalar[v] += x.get("count", 1); found = True
        elif path.startswith("colors.roles."):
            v = (node or {}).get("hex")
            if v: scalar[v] += 1; found = True

        if found: per_site += 1

    if fieldCounters:
        out = {}
        for f, counter in fieldCounters.items():
            total = sum(counter.values()) or 1
            out[f] = [{"value": v, "count": c, "share": f"{c/total*100:.1f}%"}
                      for v, c in counter.most_common(limit)]
        return {
            "purpose": label, "sitesCovered": per_site,
            "distribution": out,
            "note": "按字段分别统计，0px 与空值已排除。值是页面上真实渲染的结果，不代表最佳实践。",
        }

    total = sum(scalar.values()) or 1
    return {
        "purpose": label, "sitesCovered": per_site,
        "totalObservations": total,
        "distribution": [{"value": v, "count": c, "share": f"{c/total*100:.1f}%"}
                         for v, c in scalar.most_common(limit)],
        "note": "统计的是 544 个站页面上真实渲染出来的值，不代表最佳实践。",
    }

def _component_report(label, fields, sites):
    out = {}
    for f, counter in fields.items():
        total = sum(counter.values()) or 1
        out[f] = [{"value": v, "count": c, "share": f"{c/total*100:.1f}%"}
                  for v, c in counter.most_common(8)]
    return {
        "purpose": label,
        "sitesCovered": sites,
        "distribution": out,
        "note": "按字段分别统计；0px 与空值已排除。这些是页面上真实渲染的值，不代表最佳实践。",
    }

def _pick_spacing(gen):
    sp = ((gen or {}).get("spacing") or {})
    base = sp.get("inferredBaseUnit")
    if base: return base
    # 没有就按整除率推
    vals = []
    for x in (sp.get("ladder") or [])[:12]:
        try:
            v = float(str(x.get("value","")).replace("px",""))
            if v >= 4: vals.append(int(v))
        except Exception: pass
    if len(vals) < 3: return None
    best, rate = None, 0
    for cand in (8, 4, 6, 5):
        r = sum(1 for v in vals if v % cand == 0) / len(vals)
        if r > rate: best, rate = cand, r
    return best if rate >= 0.6 else None

def _pick_body(ladder):
    """正文档：14-18px 之间出现次数最多的字号；没有就取全表最高频。"""
    if not ladder: return None
    cand = [x for x in ladder if 14 <= (x.get("px") or 0) <= 18]
    pool = cand or ladder
    best = max(pool, key=lambda x: x.get("count") or 0)
    return best.get("size")

def compare_sites(ids, dimensions=None):
    """多站横向对比：颜色、圆角、间距、排版、动效、组件。"""
    get_spec = _queries.get
    rows = []
    for sid in ids:
        d = get_spec(sid)
        if not d: continue
        gen = None
        p = GEN / f"{sid}.json"
        if p.exists():
            try: gen = json.loads(p.read_text())
            except Exception: pass
        sem = (d.get("semantics") or {})
        roles = (sem.get("colors") or {})
        typo = (gen or {}).get("typography") or {}
        ladder = typo.get("ladder") or []
        rows.append({
            "id": sid,
            "name": d.get("name"),
            "url": d.get("url"),
            "primary": (roles.get("primary") or {}).get("value"),
            "background": (roles.get("background") or {}).get("value"),
            "foreground": (roles.get("foreground") or {}).get("value"),
            "bodySize": _pick_body(ladder),
            "typeSteps": len(ladder),
            "fontFamilies": (typo.get("families") or [])[:3],
            "radiusSteps": [x.get("value") for x in ((gen or {}).get("shape") or {}).get("radiusLadder", [])[:5]],
            "spacingBase": _pick_spacing(gen),
            "durations": [x.get("value") for x in ((gen or {}).get("motion") or {}).get("durations", [])[:4]],
            "componentKinds": list(((gen or {}).get("components") or {}).keys()),
            "componentSamples": (gen or {}).get("overview", {}).get("componentSamples"),
        })

    if not rows:
        return {"error": "没有找到可用站点"}

    # 共同点 / 差异点
    def common(field):
        vals = [r.get(field) for r in rows if r.get(field)]
        return vals[0] if vals and len(set(map(str, vals))) == 1 else None

    diffs = {}
    for f in ("primary", "bodySize", "spacingBase"):
        vals = {r["id"]: r.get(f) for r in rows}
        if len(set(map(str, vals.values()))) > 1:
            diffs[f] = vals

    return {
        "sites": rows,
        "shared": {f: common(f) for f in ("primary", "bodySize", "spacingBase") if common(f)},
        "differences": diffs,
        "note": "值来自各站运行态实测；同一字段为空表示该站没暴露这个 token。",
    }

def audit_page(url, timeout=30, platform="desktop"):
    """抓一个页面，检查偏离行业惯例的地方。

    platform: desktop 用 32px 作点击目标基准，mobile 用 44px。
    """
    import subprocess, time, urllib.request, tempfile, os

    CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
    probe = r'''
(() => {
  const out = {};
  const toRGB = v => {
    const m = (v||"").match(/rgba?\(([\d.]+),\s*([\d.]+),\s*([\d.]+)/);
    return m ? {r:+m[1],g:+m[2],b:+m[3]} : null;
  };
  const lum = c => { if(!c) return null;
    const f=x=>{x/=255;return x<=.03928?x/12.92:Math.pow((x+.055)/1.055,2.4)};
    return .2126*f(c.r)+.7152*f(c.g)+.0722*f(c.b); };
  const contrast = (a,b) => { const la=lum(a),lb=lum(b);
    if(la===null||lb===null) return null;
    const hi=Math.max(la,lb),lo=Math.min(la,lb);
    return Math.round((hi+.05)/(lo+.05)*100)/100; };

  const body = getComputedStyle(document.body);
  out.body = {
    fontSize: body.fontSize, lineHeight: body.lineHeight,
    color: body.color, background: body.backgroundColor,
    fontFamily: body.fontFamily.split(",")[0].replace(/["']/g,"").trim(),
    contrast: contrast(toRGB(body.color), toRGB(body.backgroundColor))
  };

  const sizes = new Map(), radii = new Map();
  let tapSmall = 0, tapSmall32 = 0, tapTotal = 0;
  let iconTotal = 0, iconSmall = 0;

  // 只取有文字的元素来统计字号，避免遍历全部节点
  document.querySelectorAll("h1,h2,h3,h4,h5,h6,p,span,a,button,li,label,td,th,input,textarea,select").forEach(el => {
    const txt = el.textContent;
    if (!txt || !txt.trim()) return;
    const cs = getComputedStyle(el);
    if (cs.display === "none") return;
    sizes.set(cs.fontSize, (sizes.get(cs.fontSize)||0)+1);
  });

  // 圆角只看有背景或边框的元素
  document.querySelectorAll("div,button,a,section,article,header,footer,aside,input,textarea,img,span").forEach(el => {
    const cs = getComputedStyle(el);
    if (cs.borderRadius === "0px" || cs.display === "none") return;
    let rv = cs.borderRadius;
    if (/e\+/.test(rv)) rv = "9999px";
    radii.set(rv, (radii.get(rv)||0)+1);
  });

  // 控件单独一轮
  document.querySelectorAll("button,input,select,textarea").forEach(el => {
    const r = el.getBoundingClientRect();
    if (r.width <= 0 || r.height <= 0) return;
    const label = (el.textContent || el.value || el.getAttribute("aria-label") || "").trim();
    const isIcon = label.length <= 2;
    const side = Math.min(r.width, r.height);
    if (isIcon) {
      iconTotal++;
      if (side < 24) iconSmall++;
    } else {
      tapTotal++;
      if (side < 44) tapSmall++;
      if (side < 32) tapSmall32++;
    }
  });
  out.typeSteps = sizes.size;
  out.topSizes = [...sizes.entries()].sort((a,b)=>b[1]-a[1]).slice(0,6).map(([v,c])=>({value:v,count:c}));
  out.radii = [...radii.entries()].sort((a,b)=>b[1]-a[1]).slice(0,6).map(([v,c])=>({value:v,count:c}));
  out.tap = { total: tapTotal, under44: tapSmall, under32: tapSmall32,
               iconTotal: iconTotal, iconUnder24: iconSmall };
  out.h1Count = document.querySelectorAll("h1").length;
  out.imgNoAlt = [...document.images].filter(i=>!i.hasAttribute("alt")).length;
  return JSON.stringify(out);
})()
'''

    try:
        import websocket
    except ImportError:
        return {"error": "缺少 websocket-client，无法执行页面审计"}

    port = 9860 + (os.getpid() % 80)
    prof = tempfile.mkdtemp(prefix="audit-")
    proc = subprocess.Popen([CHROME,"--headless=new","--hide-scrollbars","--no-first-run",
      "--no-default-browser-check","--disable-extensions","--mute-audio",
      "--enable-unsafe-swiftshader","--use-gl=angle","--use-angle=swiftshader",
      f"--remote-debugging-port={port}","--remote-allow-origins=*",
      "--window-size=1440,900",f"--user-data-dir={prof}","about:blank"],
      stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        tgt = None
        for _ in range(70):
            try:
                with urllib.request.urlopen(f"http://127.0.0.1:{port}/json", timeout=2) as r:
                    ts = json.loads(r.read())
                pg = [t for t in ts if t.get("type") == "page"]
                if pg: tgt = pg[0]; break
            except Exception:
                time.sleep(0.3)
        if not tgt: return {"error": "浏览器没起来"}

        ws = websocket.create_connection(tgt["webSocketDebuggerUrl"], timeout=90, suppress_origin=True)
        n = [0]
        def send(m, p=None):
            n[0] += 1
            ws.send(json.dumps({"id": n[0], "method": m, "params": p or {}}))
            while True:
                msg = json.loads(ws.recv())
                if msg.get("id") == n[0]: return msg

        send("Page.enable"); send("Runtime.enable")
        send("Page.navigate", {"url": url})
        dl = time.time() + timeout
        while time.time() < dl:
            time.sleep(1.2)
            try:
                r = send("Runtime.evaluate", {"expression":
                    "document.readyState+'|'+(document.body?document.body.innerText.length:0)",
                    "returnByValue": True})
                st, ch = str(r["result"]["result"]["value"]).split("|")
                if st == "complete" and int(ch) > 100: break
            except Exception:
                pass
        time.sleep(1.5)
        r = send("Runtime.evaluate", {"expression": probe, "returnByValue": True})
        val = r["result"]["result"].get("value")
        if not val: return {"error": "采样失败"}
        page = json.loads(val)
    finally:
        proc.terminate()
        try: proc.wait(timeout=6)
        except Exception: proc.kill()

    # ---- 对照行业惯例 ----
    findings = []

    # 1. 正文字号
    body_px = None
    m = re.match(r"([\d.]+)px", page["body"].get("fontSize") or "")
    if m: body_px = float(m.group(1))
    if body_px:
        if body_px < 14:
            findings.append({"level":"warn","field":"正文字号",
                "value": f"{body_px}px", "norm":"16px 是主流（544 站中位）",
                "note":"小于 14px 的正文在移动端可读性偏弱"})
        elif body_px > 20:
            findings.append({"level":"info","field":"正文字号",
                "value": f"{body_px}px", "norm":"16px", "note":"偏大，可能是文章型页面"})

    # 2. 正文对比度
    c = page["body"].get("contrast")
    if c is not None and c < 4.5:
        findings.append({"level":"err","field":"正文对比度",
            "value": f"{c}:1", "norm":"≥4.5:1（WCAG AA）",
            "note":"低于 AA 标准，正文可读性不达标"})

    # 3. 字号档位数量
    if page.get("typeSteps", 0) > 18:
        findings.append({"level":"warn","field":"字号种类",
            "value": f"{page['typeSteps']} 种", "norm":"8–14 种",
            "note":"字号太多，排版容易失去节奏"})
    elif page.get("typeSteps", 0) < 4:
        findings.append({"level":"info","field":"字号种类",
            "value": f"{page['typeSteps']} 种", "norm":"8–14 种",
            "note":"字号很少，层级可能不够清楚"})

    # 4. 圆角种类
    if len(page.get("radii") or []) > 6:
        findings.append({"level":"info","field":"圆角种类",
            "value": f"{len(page['radii'])} 种", "norm":"3–5 种",
            "note":"圆角不统一，视觉上容易显得零散"})

    # 5. 点击目标（按平台取不同基准）
    tap = page.get("tap") or {}
    min_tap = 44 if platform == "mobile" else 32
    if tap.get("total") and tap["total"] > 0:
        under = tap.get("under32", 0) if platform == "desktop" else tap.get("under44", 0)
        ratio = under / tap["total"]
        if ratio > 0.6:
            findings.append({"level":"warn","field":"主要操作尺寸",
                "value": f"{under}/{tap['total']} 小于 {min_tap}px",
                "norm": f"{'触屏' if platform=='mobile' else '桌面'}基准 ≥{min_tap}×{min_tap}px",
                "note": "触屏容易点错" if platform == "mobile" else "桌面鼠标精度更高，一般可接受"})
    # 图标按钮单独看
    if tap.get("iconTotal") and tap["iconTotal"] > 0:
        iratio = tap.get("iconUnder24", 0) / tap["iconTotal"]
        if iratio > 0.5:
            findings.append({"level":"info","field":"图标按钮尺寸",
                "value": f"{tap['iconUnder24']}/{tap['iconTotal']} 小于 24px",
                "norm": "图标按钮建议 ≥24×24px",
                "note": "图标按钮本可以更小，这里只是提示"})

    # 6. 标题层级
    if page.get("h1Count", 0) == 0:
        findings.append({"level":"warn","field":"h1",
            "value":"没有 h1", "norm":"每页 1 个 h1", "note":"影响可访问性与 SEO"})
    elif page.get("h1Count", 0) > 1:
        findings.append({"level":"info","field":"h1",
            "value": f"{page['h1Count']} 个", "norm":"1 个",
            "note":"多个 h1 会让结构变模糊"})

    # 7. 图片 alt
    if page.get("imgNoAlt", 0) > 0:
        findings.append({"level":"warn","field":"图片 alt",
            "value": f"{page['imgNoAlt']} 张缺 alt", "norm":"全部有 alt",
            "note":"读屏软件无法描述这些图片"})

    return {
        "url": url,
        "platform": platform,
        "measured": page,
        "findings": findings,
        "summary": {
            "errors": sum(1 for f in findings if f["level"] == "err"),
            "warnings": sum(1 for f in findings if f["level"] == "warn"),
            "infos": sum(1 for f in findings if f["level"] == "info"),
        },
        "note": "对照基准是 544 个站点的实测分布，不是绝对标准。",
    }
