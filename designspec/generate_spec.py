"""把采集数据归纳成一份标准设计规范文档（而非罗列 token）。

输出结构遵循常见企业级设计规范（TDesign / Ant Design 那种）的章节：
  1 概览      2 设计原则    3 色彩    4 字体    5 间距与栅格
  6 圆角与阴影  7 动效      8 组件规范   9 无障碍   10 使用建议
每一节都标注数据来源与置信度；缺失的明确写「未采集到」，不臆造。
"""
import json, re
from pathlib import Path
from collections import Counter, defaultdict

# ---------- 工具 ----------
def num(v):
    m = re.match(r'(-?[\d.]+)\s*(px|rem|em|ms|s)?$', str(v).strip())
    if not m: return None
    n = float(m.group(1)); u = m.group(2) or ""
    if u in ("rem", "em"): n *= 16
    if u == "s": n *= 1000
    return n

def to_hex(v):
    if not isinstance(v, str): return None
    s = v.strip()
    m = re.match(r'#([0-9a-f]{6})(?:[0-9a-f]{2})?$', s, re.I)
    if m: return "#" + m.group(1).lower()
    m = re.match(r'#([0-9a-f]{3})$', s, re.I)
    if m: return "#" + "".join(c*2 for c in m.group(1)).lower()
    m = re.match(r'rgba?\(\s*([\d.]+)[,\s]+([\d.]+)[,\s]+([\d.]+)', s)
    if m: return "#%02x%02x%02x" % tuple(min(255,int(float(x))) for x in m.groups())
    return None

def lum(hexv):
    if not hexv or not hexv.startswith("#") or len(hexv) != 7: return None
    def ch(c):
        c = c/255
        return c/12.92 if c <= .03928 else ((c+.055)/1.055)**2.4
    r,g,b = int(hexv[1:3],16), int(hexv[3:5],16), int(hexv[5:7],16)
    return .2126*ch(r)+.7152*ch(g)+.0722*ch(b)

def contrast(a, b):
    la, lb = lum(a), lum(b)
    if la is None or lb is None: return None
    hi, lo = max(la,lb), min(la,lb)
    return round((hi+.05)/(lo+.05), 2)

def wcag(ratio):
    if ratio is None: return "—"
    if ratio >= 7: return "AAA"
    if ratio >= 4.5: return "AA"
    if ratio >= 3: return "AA-large"
    return "fail"

# ---------- 归纳 ----------
def scale_of(values, labels):
    """把数值集合压成有序阶梯，返回 [(label, value, px)]"""
    clean = []
    for v in values:
        n = num(v)
        if n is None or n <= 0: continue
        clean.append((n, v))
    uniq = {}
    for n, v in clean:
        if n not in uniq: uniq[n] = v
    ordered = sorted(uniq.items())
    out = []
    for i, (n, v) in enumerate(ordered[:len(labels)]):
        out.append((labels[i], v, n))
    return out

def component_spec(spec, kind, label):
    """归纳一个组件的规范：变体、尺寸、状态、尺寸规则"""
    comps = (spec.get("design") or {}).get("components") or {}
    raw = comps.get(kind)
    if not raw or not isinstance(raw, dict):
        return None

    variants = {}
    # 收集所有样本行
    rows = []
    if isinstance(raw.get("variants"), dict):
        for vname, sizes in raw["variants"].items():
            for sname, srows in (sizes or {}).items():
                for r in (srows or []):
                    if isinstance(r, dict): rows.append((vname, sname, r))
    if isinstance(raw.get("samples"), dict):
        for vname, sizes in raw["samples"].items():
            for sname, srows in (sizes or {}).items():
                for r in (srows or []):
                    if isinstance(r, dict): rows.append((vname, sname, r))
    elif isinstance(raw.get("samples"), list):
        for r in raw["samples"]:
            if isinstance(r, dict): rows.append(("default", "md", r))

    if not rows:
        return None

    for vname, sname, r in rows:
        h = r.get("height")
        if isinstance(h, (int,float)) and h > 0:
            bucket = "sm" if h <= 32 else "md" if h <= 40 else "lg" if h <= 48 else "xl"
        else:
            bucket = sname if sname in ("sm","md","lg","xl") else "md"
        variants.setdefault(vname, {}).setdefault(bucket, []).append({
            "height": h,
            "padding": r.get("padding"),
            "radius": r.get("radius"),
            "background": r.get("background"),
            "color": r.get("color"),
            "border": r.get("border"),
            "fontSize": r.get("fontSize"),
            "fontWeight": r.get("fontWeight"),
            "shadow": r.get("shadow"),
            "contrast": r.get("contrast"),
            "text": (r.get("text") or "")[:24],
        })

    # 每个变体×尺寸只留一个代表
    compact = {}
    for v, sizes in variants.items():
        compact[v] = {}
        for s, list_ in sizes.items():
            # 优先选有文字的样本（更像真实按钮）
            pick = max(list_, key=lambda x: (bool(x["text"]), x["contrast"] or 0))
            compact[v][s] = pick

    # 该组件的实测状态
    states = {}
    for s in ((spec.get("design") or {}).get("interactiveStates") or []):
        if s.get("tag") != ("button" if kind == "button" else "a"):
            if kind != "link": continue
        if kind == "link" and s.get("tag") != "a": continue
        for st, ch in (s.get("states") or {}).items():
            for prop, val in ch.items():
                states.setdefault(st, Counter())[prop] += 1

    return {
        "kind": kind,
        "label": label,
        "variants": compact,
        "sizeCount": len({b for v in compact.values() for b in v}),
        "stateChanges": {st: dict(c.most_common(5)) for st, c in states.items()},
    }

def build(spec):
    page = spec.get("page") or {}
    typo = spec.get("typography") or {}
    colors = spec.get("colors") or {}
    sem = spec.get("semantics") or {}
    motion = spec.get("motion") or {}
    a11y = (spec.get("design") or {}).get("a11y") or {}
    des = spec.get("design") or {}

    bg = (sem.get("colors") or {}).get("background") or {}
    fg = (sem.get("colors") or {}).get("foreground") or {}

    # ---- 1 概览 ----
    overview = {
        "name": spec.get("name"),
        "url": spec.get("url"),
        "section": spec.get("section"),
        "title": page.get("title"),
        "elementCount": page.get("elementCount"),
        "documentHeight": page.get("documentHeight"),
        "colorScheme": page.get("colorScheme"),
        "darkMode": page.get("darkMode"),
    }

    # ---- 3 色彩 ----
    roles = {}
    for role, info in (sem.get("colors") or {}).items():
        hexv = to_hex(info.get("value"))
        roles[role] = {
            "value": info.get("value"),
            "hex": hexv,
            "token": info.get("token"),
            "source": info.get("source"),
            "confidence": info.get("confidence"),
            "contrastOnBg": contrast(hexv, to_hex(bg.get("value"))) if role in ("foreground","primary","danger","success","warning","info") else None,
        }
    # 语义角色缺失时，从实测色里补中性阶
    neutral_ramp = []
    seen = set()
    for c in (colors.get("backgrounds") or []) + (colors.get("text") or []):
        h = to_hex(c.get("value"))
        if h and h not in seen:
            seen.add(h)
            neutral_ramp.append({"hex": h, "count": c.get("count")})
        if len(neutral_ramp) >= 8: break

    color_section = {
        "roles": roles,
        "neutralRamp": neutral_ramp,
        "backgroundsTotal": len(colors.get("backgrounds") or []),
        "textTotal": len(colors.get("text") or []),
        "bordersTotal": len(colors.get("borders") or []),
    }

    # ---- 4 字体 ----
    sizes = []
    for t in (typo.get("scale") or [])[:20]:
        n = num(t.get("size"))
        if n and n not in [x["px"] for x in sizes]:
            sizes.append({"value": t.get("size"), "px": n,
                          "weight": t.get("weight"), "lineHeight": t.get("lineHeight"),
                          "letterSpacing": t.get("letterSpacing"),
                          "count": t.get("count")})
    sizes.sort(key=lambda x: x["px"])
    families = [f.get("family") for f in (typo.get("families") or [])[:5] if f.get("family")]
    type_section = {
        "families": families,
        "bodyFont": page.get("bodyFont"),
        "bodySize": page.get("bodySize"),
        "bodyLineHeight": page.get("bodyLineHeight"),
        "sizeLadder": sizes[:12],
        "weights": sorted({t.get("weight") for t in (typo.get("scale") or []) if t.get("weight")})[:8],
    }

    # ---- 5 间距 ----
    spacing_vals = []
    for s in (spec.get("spacing") or []):
        n = num(s.get("value"))
        # 只保留真正的布局间距（>=4px），排除 1-3px 的边框/描边误差
        if n and n >= 4 and n <= 320: spacing_vals.append((n, s.get("value")))
    uniq = {}
    for n, v in spacing_vals:
        uniq.setdefault(n, v)
    space_ladder = [{"value": v, "px": n} for n, v in sorted(uniq.items())[:12]]
    # 推断基础单位
    # 推断基础间距单位：统计 8 / 4 / 6 的整除率，取最高者
    base_unit = None
    if space_ladder:
        px_vals = [round(x["px"]) for x in space_ladder if x["px"] >= 4]
        if len(px_vals) >= 3:
            best, best_rate = None, 0
            for cand in (8, 4, 6, 5):
                rate = sum(1 for x in px_vals if x % cand == 0) / len(px_vals)
                if rate > best_rate:
                    best, best_rate = cand, rate
            # 整除率至少 60% 才认定为系统化间距
            if best_rate >= 0.6:
                base_unit = best

    spacing_section = {"ladder": space_ladder, "inferredBaseUnit": base_unit,
                       "containerWidths": (spec.get("layout") or {}).get("containerWidths", [])[:5],
                       "breakpoints": (spec.get("breakpoints") or [])[:10]}

    # ---- 6 圆角与阴影 ----
    radius_vals = []
    for r in (spec.get("radii") or []):
        n = num(r.get("value"))
        if n is not None and n >= 0: radius_vals.append((n, r.get("value"), r.get("count")))
    uniq_r = {}
    for n, v, c in radius_vals:
        if n not in uniq_r: uniq_r[n] = (v, c)
    radius_ladder = [{"value": v, "px": n, "count": c} for n, (v, c) in sorted(uniq_r.items())[:8]]
    shape_section = {
        "radiusLadder": radius_ladder,
        "shadows": [{"value": x.get("value"), "count": x.get("count")} for x in (spec.get("shadows") or [])[:6]],
        "borders": [{"value": x.get("value"), "count": x.get("count")} for x in (spec.get("borders") or [])[:5]],
    }

    # ---- 7 动效 ----
    durations = []
    for d in (motion.get("durations") or []):
        n = num(d.get("value"))
        if n and n > 0: durations.append((n, d.get("value")))
    uniq_d = {}
    for n, v in durations: uniq_d.setdefault(n, v)
    motion_section = {
        "durations": [{"value": v, "ms": n} for n, v in sorted(uniq_d.items())[:8]],
        "easings": [{"value": e.get("value"), "count": e.get("count")} for e in (motion.get("easings") or [])[:6]],
        "properties": [{"value": p.get("value"), "count": p.get("count")} for p in (motion.get("properties") or [])[:8]],
        "keyframes": (motion.get("keyframes") or [])[:5],
        "recommendedDuration": (sorted(uniq_d.items())[0][1] if uniq_d else None),
    }

    # ---- 8 组件 ----
    component_section = {}
    for kind, label in [("button","按钮"),("input","输入框"),("link","链接"),("card","卡片"),
                        ("nav","导航"),("badge","徽标"),("avatar","头像"),("table","表格"),
                        ("modal","对话框"),("tabs","标签页"),("tooltip","提示"),("dropdown","下拉菜单")]:
        c = component_spec(spec, kind, label)
        if c: component_section[kind] = c

    # ---- 9 无障碍 ----
    fg_hex, bg_hex = to_hex(fg.get("value")), to_hex(bg.get("value"))
    body_contrast = contrast(fg_hex, bg_hex)
    a11y_section = {
        "bodyContrast": body_contrast,
        "bodyContrastLevel": wcag(body_contrast),
        "tapTargetMedian": a11y.get("tapTargetMedian"),
        "tapTargetMin": a11y.get("tapTargetMin"),
        "tapTargetsUnder44": a11y.get("tapTargetsUnder44"),
        "tapTargetsTotal": a11y.get("tapTargetsTotal"),
        "imgWithoutAlt": a11y.get("imgWithoutAlt"),
        "headingOrder": (a11y.get("headingOrder") or [])[:12],
        "landmarks": a11y.get("landmarks"),
        "issues": [],
    }
    if a11y.get("tapTargetsUnder44") and a11y.get("tapTargetsTotal"):
        ratio = a11y["tapTargetsUnder44"] / max(a11y["tapTargetsTotal"],1)
        if ratio > 0.5:
            a11y_section["issues"].append(f"{a11y['tapTargetsUnder44']}/{a11y['tapTargetsTotal']} 个点击目标小于 44px")
    if a11y.get("imgWithoutAlt"):
        a11y_section["issues"].append(f"{a11y['imgWithoutAlt']} 张图片缺 alt")
    if body_contrast and body_contrast < 4.5:
        a11y_section["issues"].append(f"正文对比度 {body_contrast}:1，低于 AA")

    return {
        "id": spec.get("id"),
        "overview": overview,
        "colors": color_section,
        "typography": type_section,
        "spacing": spacing_section,
        "shape": shape_section,
        "motion": motion_section,
        "components": component_section,
        "accessibility": a11y_section,
        "meta": {
            "generatedFrom": "runtime computed styles",
            "capturedAt": spec.get("capturedAt"),
            "elementCount": page.get("elementCount"),
            "coverage": {},
        },
    }

def main():
    src = Path("specs_sem")
    out = Path("generated")
    out.mkdir(exist_ok=True)
    n = 0
    for p in sorted(src.glob("*.json")):
        spec = json.loads(p.read_text())
        doc = build(spec)
        # 覆盖度
        cov = {
            "colors": bool(doc["colors"]["roles"]),
            "typography": bool(doc["typography"]["sizeLadder"]),
            "spacing": bool(doc["spacing"]["ladder"]),
            "shape": bool(doc["shape"]["radiusLadder"]),
            "motion": bool(doc["motion"]["durations"]),
            "components": bool(doc["components"]),
            "accessibility": doc["accessibility"]["bodyContrast"] is not None,
        }
        doc["meta"]["coverage"] = cov
        doc["meta"]["coverageScore"] = round(sum(cov.values()) / len(cov) * 100)
        (out / f"{spec['id']}.json").write_text(json.dumps(doc, ensure_ascii=False, indent=1))
        n += 1
    print("生成规范文档:", n)

if __name__ == "__main__":
    main()
