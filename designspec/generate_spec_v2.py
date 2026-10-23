"""基于深度扫描（多页面）重新生成设计规范文档。"""
import json, re
from pathlib import Path
from collections import Counter, defaultdict

def num(v):
    m = re.match(r'(-?[\d.]+)\s*(px|rem|em|ms|s)?$', str(v).strip())
    if not m: return None
    n = float(m.group(1)); u = m.group(2) or ""
    if u in ("rem","em"): n *= 16
    if u == "s": n *= 1000
    return n

def to_hex(v):
    if not isinstance(v,str): return None
    s = v.strip()
    m = re.match(r'#([0-9a-f]{6})(?:[0-9a-f]{2})?$', s, re.I)
    if m: return "#"+m.group(1).lower()
    m = re.match(r'#([0-9a-f]{3})$', s, re.I)
    if m: return "#"+"".join(c*2 for c in m.group(1)).lower()
    m = re.match(r'rgba?\(\s*([\d.]+)[,\s]+([\d.]+)[,\s]+([\d.]+)', s)
    if m: return "#%02x%02x%02x" % tuple(min(255,int(float(x))) for x in m.groups())
    return None

def lum(h):
    if not h or not h.startswith("#") or len(h)!=7: return None
    def ch(c):
        c=c/255
        return c/12.92 if c<=.03928 else ((c+.055)/1.055)**2.4
    r,g,b = int(h[1:3],16),int(h[3:5],16),int(h[5:7],16)
    return .2126*ch(r)+.7152*ch(g)+.0722*ch(b)

def contrast(a,b):
    la,lb = lum(a),lum(b)
    if la is None or lb is None: return None
    hi,lo = max(la,lb),min(la,lb)
    return round((hi+.05)/(lo+.05),2)

def wcag(r):
    if r is None: return "—"
    if r>=7: return "AAA"
    if r>=4.5: return "AA"
    if r>=3: return "AA-large"
    return "fail"

def build(deep, sem):
    comps = deep.get("components") or {}
    typo = deep.get("typography") or []
    spacing = deep.get("spacing") or []
    colors = deep.get("colors") or {}
    layout = deep.get("layout") or {}
    sections = deep.get("sections") or []

    # ---- 色彩：从实测 + 语义映射 ----
    sem_colors = (sem.get("semantics") or {}).get("colors") or {}
    bg_hex = to_hex((sem_colors.get("background") or {}).get("value"))
    fg_hex = to_hex((sem_colors.get("foreground") or {}).get("value"))
    roles = {}
    for role, info in sem_colors.items():
        h = to_hex(info.get("value"))
        roles[role] = {
            "hex": h, "value": info.get("value"),
            "token": info.get("token"), "source": info.get("source"),
            "contrastOnBg": contrast(h, bg_hex) if role in ("foreground","primary","danger","success","warning","info","link") else None
        }
    # 补：从实测背景/文字色统计
    neutral = []
    seen = set()
    for c in (colors.get("backgrounds") or []) + (colors.get("text") or []):
        h = to_hex(c.get("value"))
        if h and h not in seen:
            seen.add(h); neutral.append({"hex": h, "count": c.get("count")})
        if len(neutral) >= 10: break

    # ---- 排版阶梯：按 px 排序去重 ----
    ladders = {}
    for t in typo:
        n = num(t.get("size"))
        if not n: continue
        if n < 8 or n > 200: continue        # 过滤异常字号
        n = round(n * 2) / 2                  # 归并到 0.5px 粒度
        lh = t.get("lineHeight") or ""
        lhn = num(lh) if lh and lh != "normal" else None
        if lhn:
            if lhn < n * 0.8 or lhn > n * 3:
                lh = "normal"
            else:
                lh = f"{round(lhn*2)/2:g}px"
        key = (n, t.get("weight"), lh, t.get("letterSpacing"))
        if key not in ladders:
            ladders[key] = {"size": f"{n:g}px", "px": n, "weight": t.get("weight"),
                            "lineHeight": lh, "letterSpacing": t.get("letterSpacing"),
                            "family": t.get("family"), "count": t.get("count",0),
                            "tags": t.get("tags",[]), "samples": t.get("samples",[])[:1]}
        else:
            ladders[key]["count"] += t.get("count",0)
    ladder = sorted(ladders.values(), key=lambda x: (x["px"], x["weight"] or ""))
    # 只保留出现次数 >=2 的档位，避免噪声
    ladder_main = [x for x in ladder if x["count"] >= 2][:40]

    # ---- 间距 ----
    sp = []
    for s in spacing:
        n = num(s.get("value"))
        # 只保留 >=4px 的布局间距，排除 1-3px 的描边/微调噪声
        if n and 4 <= n <= 320:
            n = round(n * 2) / 2        # 归并到 0.5px，去掉 em 换算的碎值
            sp.append((n, f"{n:g}px", s.get("count",0)))
    uniq_sp = {}
    for n,v,c in sp: uniq_sp.setdefault(n,(v,c))
    sp_ladder = [{"value":v,"px":n,"count":c} for n,(v,c) in sorted(uniq_sp.items())][:16]
    base = None
    if len(sp_ladder) >= 3:
        vals = [round(x["px"]) for x in sp_ladder if x["px"] >= 4]
        if vals:
            best, rate = None, 0
            for cand in (8,4,6,5):
                r = sum(1 for v in vals if v % cand == 0)/len(vals)
                if r > rate: best, rate = cand, r
            if rate >= 0.6: base = best

    # ---- 圆角 / 阴影 ----
    radii = []
    for r in (layout.get("radii") or []):
        v = r.get("value","")
        n = num(v)
        if "e+" in v: v = "9999px"; n = 9999
        if n is None and "%" in v: n = 50
        if n is not None and n >= 1: radii.append({"value": v, "px": n, "count": r.get("count",0)})
    radii.sort(key=lambda x: x["px"])

    # ---- 组件 ----
    component_spec = {}
    LABELS = {"button":"按钮","input":"输入框","link":"链接","card":"卡片","nav":"导航",
              "badge":"徽标","avatar":"头像","table":"表格","modal":"对话框","tabs":"标签页",
              "tooltip":"提示","dropdown":"下拉菜单","heading":"标题","para":"正文",
              "list":"列表","icon":"图标","divider":"分割线","breadcrumb":"面包屑",
              "pagination":"分页","alert":"提示条"}
    for kind, rows in comps.items():
        if not rows: continue
        by_size = defaultdict(list)
        for r in rows:
            st = r.get("style") or {}
            h = st.get("height") or 0
            sz = "sm" if h <= 28 else "md" if h <= 36 else "lg" if h <= 44 else "xl"
            by_size[sz].append({
                "text": (r.get("text") or "")[:30],
                "tag": r.get("tag"),
                "height": h, "width": st.get("width"),
                "padding": st.get("padding"), "margin": st.get("margin"),
                "radius": ("9999px" if "e+" in str(st.get("borderRadius")) else st.get("borderRadius")),
                "background": st.get("background"), "color": st.get("color"),
                "border": st.get("border"),
                "fontSize": st.get("fontSize"), "fontWeight": st.get("fontWeight"),
                "fontFamily": st.get("fontFamily"),
                "lineHeight": st.get("lineHeight"), "letterSpacing": st.get("letterSpacing"),
                "textTransform": st.get("textTransform"),
                "shadow": st.get("boxShadow"),
                "transition": st.get("transition"),
                "gap": st.get("gap"),
                "contrast": st.get("contrast"),
            })
        # 每档只留前 4 个代表
        compact = {sz: rows2[:4] for sz, rows2 in by_size.items()}
        component_spec[kind] = {
            "label": LABELS.get(kind, kind),
            "count": len(rows),
            "sizeBuckets": {sz: len(rows2) for sz, rows2 in by_size.items()},
            "samples": compact
        }

    # ---- 区块结构 ----
    sec_summary = []
    for s in sections[:20]:
        sec_summary.append({
            "tag": s.get("tag"), "height": s.get("height"),
            "heading": s.get("heading"), "background": s.get("background"),
            "padding": s.get("padding"), "children": s.get("childCount")
        })

    # ---- 无障碍估算 ----
    fg_h = fg_hex or "#000000"
    bg_h = bg_hex or "#ffffff"
    body_c = contrast(fg_h, bg_h)
    tap = []
    for kind in ("button","link"):
        for r in comps.get(kind) or []:
            h = (r.get("style") or {}).get("height")
            if h: tap.append(h)
    tap.sort()

    return {
        "id": deep.get("id"),
        "overview": {
            "name": deep.get("name"), "url": deep.get("homepage") or deep.get("url"),
            "section": deep.get("section"),
            "pagesScanned": deep.get("pages") or [],
            "subpages": deep.get("subpages") or [],
            "sectionCount": len(sections),
            "componentSamples": sum(len(v) for v in comps.values()),
            "typeSteps": len(ladder_main),
        },
        "colors": {"roles": roles, "neutralRamp": neutral,
                   "backgroundsTotal": len(colors.get("backgrounds") or []),
                   "textTotal": len(colors.get("text") or []),
                   "bordersTotal": len(colors.get("borders") or [])},
        "typography": {"ladder": ladder_main, "totalSteps": len(ladder),
                       "families": sorted({x["family"] for x in ladder if x.get("family")})[:8],
                       "weights": sorted({str(x["weight"]) for x in ladder if x.get("weight")})},
        "spacing": {"ladder": sp_ladder, "inferredBaseUnit": base,
                    "containerWidths": (layout.get("containerWidths") or [])[:6]},
        "shape": {"radiusLadder": radii[:10], "shadows": (layout.get("shadows") or [])[:8],
                  "zIndex": (layout.get("zIndex") or [])[:10]},
        "components": component_spec,
        "sections": sec_summary,
        "accessibility": {"bodyContrast": body_c, "bodyContrastLevel": wcag(body_c),
                          "tapTargetMin": tap[0] if tap else None,
                          "tapTargetMedian": tap[len(tap)//2] if tap else None},
    }

def main():
    deep_dir = Path("deep")
    sem_dir = Path("specs_sem")
    out = Path("generated_v2")
    out.mkdir(exist_ok=True)
    n = 0
    for p in sorted(deep_dir.glob("*.json")):
        try:
            deep = json.loads(p.read_text())
        except Exception:
            continue
        if not deep.get("id"): continue
        sid = deep["id"]
        sem = {}
        sp = sem_dir / f"{sid}.json"
        if sp.exists():
            try: sem = json.loads(sp.read_text())
            except Exception: pass
        doc = build(deep, sem)
        (out / f"{sid}.json").write_text(json.dumps(doc, ensure_ascii=False, indent=1))
        n += 1
    print("生成 v2 规范:", n)

if __name__ == "__main__":
    main()
