"""DesignSpec query layer: pure functions over the raw JSON corpus."""
import json, re
from pathlib import Path

ROOT = Path(__file__).resolve().parent
RAW = ROOT / "specs_sem"
INDEX = ROOT / "index.json"

_cache = {"all": None, "ts": 0}

def all_specs():
    import time
    if _cache["all"] is not None and time.time() - _cache["ts"] < 5:
        return _cache["all"]
    rows = []
    for p in sorted(RAW.glob("*.json")):
        try:
            rows.append(json.loads(p.read_text()))
        except Exception:
            continue
    rows.sort(key=lambda d: ((d.get("section") or ""), (d.get("name") or "").lower()))
    _cache["all"] = rows
    _cache["ts"] = time.time()
    return rows

def get(spec_id):
    p = RAW / f"{spec_id}.json"
    if not p.exists():
        return None
    return json.loads(p.read_text())

def _hay(spec):
    parts = [spec.get("name",""), spec.get("url",""), spec.get("section",""), spec.get("id","")]
    page = spec.get("page") or {}
    parts += [page.get("title","") or "", page.get("bodyFont","") or ""]
    for fam in (spec.get("typography") or {}).get("families", [])[:10]:
        parts.append(fam.get("family",""))
    for bucket in ("backgrounds","text","borders"):
        for c in (spec.get("colors") or {}).get(bucket, [])[:30]:
            parts.append(c.get("value",""))
    parts += list((spec.get("cssVariables") or {}).keys())
    parts += list((spec.get("cssVariables") or {}).values())
    return " ".join(parts).lower()

def search(query="", section=None, limit=20):
    words = [w for w in re.split(r"\s+", (query or "").lower()) if w]
    out = []
    for spec in all_specs():
        if section and spec.get("section") != section:
            continue
        if words:
            hay = _hay(spec)
            if not all(w in hay for w in words):
                continue
        out.append(summarize(spec))
        if len(out) >= limit:
            break
    return out

def summarize(spec):
    page = spec.get("page") or {}
    typo = (spec.get("typography") or {}).get("scale") or []
    families = [f["family"] for f in (spec.get("typography") or {}).get("families", [])[:3]]
    bgs = (spec.get("colors") or {}).get("backgrounds", [])[:6]
    radii = (spec.get("radii") or [])[:5]
    durs = (spec.get("motion") or {}).get("durations", [])[:3]
    eases = (spec.get("motion") or {}).get("easings", [])[:2]
    return {
        "id": spec.get("id"), "name": spec.get("name"), "url": spec.get("url"),
        "section": spec.get("section"),
        "body": {"font": page.get("bodyFont"), "size": page.get("bodySize"), "lineHeight": page.get("bodyLineHeight")},
        "fontFamilies": families,
        "topTypeSizes": [{"size": t["size"], "weight": t["weight"], "count": t["count"]} for t in typo[:5]],
        "backgrounds": [{"value": c["value"], "count": c["count"]} for c in bgs],
        "radii": radii,
        "motion": {"durations": durs, "easings": eases},
        "cssVariableCount": len(spec.get("cssVariables") or {}),
        "quality": quality_of(spec),
        "breakpoints": spec.get("breakpoints") or []
    }

def compare(ids):
    rows = [get(i) for i in ids]
    rows = [r for r in rows if r]
    if not rows:
        return {"error": "no matching ids"}
    def collect(path):
        vals = {}
        for r in rows:
            cur = r
            for key in path.split("."):
                cur = (cur or {}).get(key) if isinstance(cur, dict) else None
            if isinstance(cur, list):
                for item in cur[:20]:
                    v = item.get("value") if isinstance(item, dict) else item
                    if v: vals.setdefault(v, []).append(r["id"])
            elif isinstance(cur, dict):
                for k in list(cur)[:40]:
                    vals.setdefault(k, []).append(r["id"])
            elif cur:
                vals.setdefault(str(cur), []).append(r["id"])
        return {k: v for k, v in sorted(vals.items(), key=lambda x: -len(x[1]))[:20]}
    return {
        "ids": [r["id"] for r in rows],
        "names": [r.get("name") for r in rows],
        "sharedRadii": collect("radii"),
        "sharedDurations": collect("motion.durations"),
        "sharedEasings": collect("motion.easings"),
        "fontFamilies": collect("typography.families"),
    }

def sanitise(step, info):
    """把变量名压成可读的 CSS 变量后缀"""
    tok = (info or {}).get("token") or ""
    s = str(tok).lstrip("-").lower().replace("--", "-")
    for pref in ("geist-", "ds-", "color-", "default-", "tw-"):
        if s.startswith(pref) and len(s) > len(pref) + 2:
            s = s[len(pref):]
    s = s.replace("-", "").strip()
    return s or str(step)

def export_theme(spec_id, fmt="css"):
    spec = get(spec_id)
    if not spec:
        return None
    sem = spec.get("semantics") or {}
    colors = sem.get("colors") or {}
    page = spec.get("page") or {}

    def pick(role):
        c = colors.get(role)
        return c.get("value") if c else None

    def line(name, val, comment=""):
        if val is None: return None
        return f"  --{name}: {val};" + (f"  /* {comment} */" if comment else "")

    css = [f"/* {spec.get('name')} — {spec.get('url')} */", "/* 语义映射自动生成，值来自运行态实测；token 名仅供参考 */", ":root {"]
    for role, name in [("background","color-bg"), ("foreground","color-text"),
                       ("primary","color-primary"), ("secondary","color-secondary"),
                       ("success","color-success"), ("warning","color-warning"),
                       ("danger","color-danger"), ("info","color-info"),
                       ("border","color-border"), ("muted","color-muted")]:
        c = colors.get(role)
        if c:
            src = c.get("source") or ""
            tok = c.get("token") or ""
            note = f"{src}: {tok}" if tok else src
            css.append(f"  --{name}: {c['value']};" + (f"  /* {note} */" if note else ""))

    # 尺度：按数值排序后重命名为语义档位，避免照搬原站乱名
    def numeric(v):
        import re as _re
        m = _re.match(r'(-?[\d.]+)\s*(px|rem|em|ms|s)?$', str(v).strip())
        if not m: return None
        n = float(m.group(1))
        unit = m.group(2) or ""
        if unit == "rem": n *= 16
        if unit == "em": n *= 16
        if unit == "s": n *= 1000
        return n

    def ladder(bucket, prefix, labels, unit_filter=None):
        table = sem.get(bucket) or {}
        vals = []
        for step, info in table.items():
            v = info.get("value")
            n = numeric(v)
            if n is None:
                continue
            if n <= 0:
                continue          # 负 margin / 0 值不进阶梯
            if bucket in ("spacing", "radius") and n < 1:
                continue          # 亚像素误差
            if bucket in ("duration",):
                # 时长必须带时间单位
                import re as _re
                if not _re.search(r'(ms|s)$', str(v).strip()):
                    continue
                if n < 50 or n > 3000:
                    continue
            if bucket in ("fontSize",) and (n < 10 or n > 120):
                continue
            if bucket in ("spacing",) and n > 400:
                continue
            if bucket in ("radius",) and n > 200:
                continue
            vals.append((n, v))
        if not vals: return
        vals = sorted(set(vals), key=lambda x: x[0])
        # 去重（同值）
        seen = set()
        uniq = []
        for n, v in vals:
            if n in seen: continue
            seen.add(n); uniq.append((n, v))
        for i, (n, v) in enumerate(uniq[:len(labels)]):
            css.append(f"  --{prefix}-{labels[i]}: {v};")

    RADIUS_LABELS = ["xs","sm","md","lg","xl","2xl","3xl","full"]
    SPACE_LABELS  = ["1","2","3","4","5","6","8","10","12","16"]
    TEXT_LABELS   = ["xs","sm","base","lg","xl","2xl","3xl","4xl"]
    DUR_LABELS    = ["fastest","fast","normal","slow","slower"]

    ladder("radius", "radius", RADIUS_LABELS)
    ladder("spacing", "space", SPACE_LABELS)
    ladder("fontSize", "text", TEXT_LABELS)
    ladder("duration", "duration", DUR_LABELS)

    # 缓动与阴影不排序，按出现顺序
    for bucket, prefix in [("easing","ease"), ("shadow","shadow")]:
        table = sem.get(bucket) or {}
        items = list(table.items())[:6]
        for i, (step, info) in enumerate(items, 1):
            v = info.get("value")
            if v is None: continue
            css.append(f"  --{prefix}-{i}: {v};")

    if page.get("bodyFont"):
        css.append(f'  --font-sans: {page["bodyFont"]};')
    if page.get("bodySize"):
        css.append(f'  --font-size-base: {page["bodySize"]};')
    if page.get("bodyLineHeight"):
        css.append(f'  --line-height-base: {page["bodyLineHeight"]};')
    css.append("}")

    if fmt == "json":
        return {
            "name": spec.get("name"), "url": spec.get("url"),
            "colors": {r: {"value": c["value"], "token": c.get("token"), "source": c.get("source"), "confidence": c.get("confidence")}
                       for r, c in colors.items()},
            "radius": sem.get("radius"), "spacing": sem.get("spacing"),
            "fontSize": sem.get("fontSize"), "duration": sem.get("duration"),
            "easing": sem.get("easing"),
            "fontFamily": page.get("bodyFont"), "bodySize": page.get("bodySize"),
        }
    return "\n".join(css)

def quality_of(spec):
    """full / partial / minimal, derived from rendered element count and captured fields."""
    els = (spec.get("page") or {}).get("elementCount") or 0
    has_type = bool((spec.get("typography") or {}).get("scale"))
    has_col = bool((spec.get("colors") or {}).get("backgrounds") or (spec.get("colors") or {}).get("text"))
    if els >= 300 and has_type and has_col:
        return "full"
    if els >= 100:
        return "partial"
    return "minimal"


def components_of(spec_id, kind=None):
    """Return the component dictionary (or one component type) for a spec."""
    spec = get(spec_id)
    if not spec:
        return None
    comps = (spec.get("design") or {}).get("components") or {}
    if kind:
        return {kind: comps.get(kind)} if kind in comps else {}
    return comps

def states_of(spec_id, state=None):
    """Return measured interactive states, optionally filtered to one state."""
    spec = get(spec_id)
    if not spec:
        return None
    rows = (spec.get("design") or {}).get("interactiveStates") or []
    if state:
        rows = [r for r in rows if state in (r.get("states") or {})]
    return {"count": len(rows), "elements": rows}

def tokens_of(spec_id, role=None):
    """Return semantic tokens grouped by role, or one role."""
    spec = get(spec_id)
    if not spec:
        return None
    sem = (spec.get("design") or {}).get("semanticTokens") or {}
    if role:
        return sem.get(role, [])
    return sem

def get_generated(spec_id):
    """The standard-format design spec document for one site."""
    p = ROOT / "generated" / f"{spec_id}.json"
    if not p.exists():
        return None
    return json.loads(p.read_text())

def list_generated():
    out = []
    for p in sorted((ROOT / "generated").glob("*.json")):
        d = json.loads(p.read_text())
        o = d.get("overview") or {}
        out.append({"id": d["id"], "name": o.get("name"), "section": o.get("section"),
                    "coverageScore": (d.get("meta") or {}).get("coverageScore")})
    return out

def stats():
    specs = all_specs()
    return {"sites": len(specs), "sections": sorted({s.get("section","") for s in specs if s.get("section")})}
