"""语义 token 映射：把各站杂乱的 CSS 变量归到统一的角色命名。

分四层，置信度从高到低：
  1. explicit  —— 变量名里直接带角色词（--primary / --color-danger / --foreground）
  2. scale     —— 尺度阶梯（--radius-lg / --space-4 / --text-sm / --duration-200）
  3. palette   —— 色板阶（--color-blue-500 / --ds-gray-1000）
  4. derived   —— 从实测统计推断（背景色、文字色、圆角分布、动效时长）
"""
import json, re
from pathlib import Path
from collections import defaultdict

# ---------- 角色关键词 ----------
# 角色词必须在变量名末尾，或后面只跟一个状态/变体后缀（hover/active/light/dark…）
STATE_SUFFIX = r'(?:-(?:hover|active|focus|pressed|selected|default|base|light|lighter|dark|darker|subtle|strong|weak|50|100|200|300|400|500|600|700|800|900|950))?'
def role_rx(words):
    return re.compile(r'(?:^|[-_])' + r'(?:' + words + r')' + STATE_SUFFIX + r'$', re.I)

ROLE_WORDS = [
    ("primary",    role_rx(r'primary|brand|accent'), 10),
    ("secondary",  role_rx(r'secondary'), 9),
    ("success",    role_rx(r'success|positive'), 9),
    ("warning",    role_rx(r'warning|caution|warn'), 9),
    ("danger",     role_rx(r'danger|error|negative|destructive|critical'), 9),
    ("info",       role_rx(r'info|notice'), 8),
    ("foreground", role_rx(r'foreground|text|fg|ink'), 7),
    ("background", role_rx(r'background|bg|surface|canvas'), 7),
    ("border",     role_rx(r'border|stroke|divider|outline|line'), 7),
    ("muted",      role_rx(r'muted|subtle|faint|dim'), 6),
    ("disabled",   role_rx(r'disabled|inactive'), 6),
    ("hover",      role_rx(r'hover'), 5),
    ("active",     role_rx(r'active|pressed'), 5),
    ("focus",      role_rx(r'focus|ring'), 5),
    ("link",       role_rx(r'link|anchor'), 5),
]
ROLE_RE = [(role, rx, pri) for role, rx, pri in ROLE_WORDS]

# 语义角色互斥：一个 token 只归一个角色，按优先级取胜
EMPHASIS_ROLES = {"primary", "secondary", "success", "warning", "danger", "info"}
STATE_ROLES = {"hover", "active", "focus", "disabled", "link"}

# ---------- 尺度阶梯 ----------
SCALE_STEPS = {
    "3xs":0, "2xs":1, "xs":2, "sm":3, "md":4, "base":4, "lg":5, "xl":6,
    "2xl":7, "3xl":8, "4xl":9, "5xl":10, "6xl":11, "7xl":12, "8xl":13, "9xl":14,
    "full":99, "pill":99, "round":99,
}
SCALE_TOKEN_RE = re.compile(
    r'(radius|rounded|corner|space|spacing|gap|pad|padding|margin|'
    r'font-?size|text|type|size|'
    r'shadow|elevation|'
    r'duration|transition|motion|ease|easing|curve)', re.I)

NUM_SCALE_RE = re.compile(r'(?:^|-)(\d{1,3})(?:$|-)')

def parse_color(v):
    """把颜色值归一成 #rrggbb（失败返回 None）"""
    if not isinstance(v, str): return None
    s = v.strip()
    m = re.match(r'#([0-9a-f]{6})(?:[0-9a-f]{2})?$', s, re.I)
    if m: return "#" + m.group(1).lower()
    m = re.match(r'#([0-9a-f]{3})$', s, re.I)
    if m:
        h = m.group(1)
        return "#" + "".join(c*2 for c in h).lower()
    m = re.match(r'rgba?\(\s*([\d.]+)[,\s]+([\d.]+)[,\s]+([\d.]+)', s)
    if m:
        r, g, b = [min(255, int(float(x))) for x in m.groups()]
        return "#%02x%02x%02x" % (r, g, b)
    return None

def is_color(v):
    return parse_color(v) is not None

def scale_step(name):
    """从变量名里抽出尺度档位，返回 (step_name, numeric) 或 (None, None)"""
    low = name.lower()
    for key, rank in SCALE_STEPS.items():
        if re.search(r'(?:^|-)' + re.escape(key) + r'(?:$|-)', low):
            return key, rank
    m = NUM_SCALE_RE.search(low)
    if m:
        n = int(m.group(1))
        return str(n), n
    return None, None

# 产品模块/组件级前缀：这些变量是该模块自己的配色，不代表全局语义
MODULE_PREFIX = re.compile(
    r'^--(ship|comp|component|btn|button|card|nav|header|footer|tab|modal|dialog|'
    r'toast|tooltip|chart|code|prose|marketing|pricing|banner|hero|sidebar|'
    r'develop|next|ds|internal|icon|console|app|page)'
    r'([-.])', re.I)

def semantic_of(name, value):
    """返回 [(role, confidence, reason)]，可能多个角色（如 primary-hover）"""
    out = []
    low = name.lower()
    # 跳过框架内部与产品模块级变量
    if re.match(r'--tw-', low): return out
    if MODULE_PREFIX.match(low): return out
    # 层级过深的通常是局部变量
    if low.count("-") > 4: return out
    # 局部 UI 部件词直接排除
    if re.search(r'(preview|dropdown|triangle|arrow|triangle|caret|bullet|dot|badge|avatar|skeleton|spinner|placeholder|scrollbar|selection)', low):
        return out
    COLORWORD = re.compile(r'(violet|purple|pink|orange|teal|cyan|indigo|amber|lime|emerald|sky|rose|fuchsia|bronze|gold|silver|red|green|blue|yellow|gray|grey|neutral|slate|zinc|stone)', re.I)
    BASE_ROLES = {"foreground", "background", "border", "muted"}
    for role, rx, pri in ROLE_RE:
        if not rx.search(low):
            continue
        # 基础角色不能来自色板级变量（如 --geist-pink-foreground）
        if role in BASE_ROLES and COLORWORD.search(low):
            continue
        out.append((role, "explicit", pri, name))
    return out

def build(spec):
    """为一个站建立语义映射表"""
    vars_ = spec.get("cssVariables") or {}
    page = spec.get("page") or {}
    colors = spec.get("colors") or {}
    radii = spec.get("radii") or []
    spacing = spec.get("spacing") or []
    motion = spec.get("motion") or {}
    typo = spec.get("typography") or {}

    result = {
        "colors": {},     # role -> {value, token, source, confidence}
        "radius": {},     # step -> {value, token}
        "spacing": {},
        "fontSize": {},
        "duration": {},
        "easing": {},
        "shadow": {},
        "unmapped": {"colors": 0, "scale": 0},
    }

    # ---- 1. 变量层：显式角色 ----
    role_hits = defaultdict(list)
    scale_hits = defaultdict(list)
    palette_hits = defaultdict(list)

    for name, value in vars_.items():
        if is_color(value):
            roles = semantic_of(name, value)
            hexv = parse_color(value)
            if roles:
                for role, conf, pri, tok in roles:
                    role_hits[role].append((pri, tok, hexv, conf))
            else:
                # 色板阶：--color-blue-500 / --ds-gray-1000
                if re.search(r'(color|palette|swatch)', name, re.I):
                    palette_hits["*"].append((name, hexv))
                else:
                    result["unmapped"]["colors"] += 1
        elif SCALE_TOKEN_RE.search(name):
            step, rank = scale_step(name)
            low = name.lower()
            if "radius" in low or "rounded" in low or "corner" in low:
                bucket = "radius"
            elif re.search(r'(space|spacing|gap|pad|margin)', low):
                bucket = "spacing"
            elif re.search(r'(font-?size|text|type)', low) and re.search(r'(size|scale)', low) or re.search(r'--text-(xs|sm|md|lg|xl|2xl)', low):
                bucket = "fontSize"
            elif "shadow" in low or "elevation" in low:
                bucket = "shadow"
            elif re.search(r'(duration|transition|motion)', low) and re.search(r'\d', value):
                bucket = "duration"
            elif re.search(r'(ease|easing|curve|bezier)', low):
                bucket = "easing"
            else:
                bucket = None
            if bucket:
                scale_hits[bucket].append((step or name, rank if rank is not None else 50, tok := name, value))

    def saturation(hexv):
        if not hexv or not hexv.startswith("#") or len(hexv) != 7: return 0
        r, g, b = int(hexv[1:3],16), int(hexv[3:5],16), int(hexv[5:7],16)
        mx, mn = max(r,g,b), min(r,g,b)
        return 0 if mx == 0 else (mx - mn) / mx

    # 统计每个 token 命中的角色数：命中多角色的通常是组合变量，优先级降低
    tok_roles = defaultdict(set)
    for role, hits in role_hits.items():
        for pri, tok, hexv, conf in hits:
            tok_roles[tok].add(role)

    # 选每个角色的最佳 token：先排除多角色词，再按优先级 + 名字长度
    for role, hits in role_hits.items():
        hits.sort(key=lambda x: (-x[0], len(x[1])))
        chosen = None
        for pri, tok, hexv, conf in hits:
            if len(tok_roles[tok]) > 1:
                continue      # 组合变量跳过
            low = tok.lower()
            # 含颜色修饰词（violet/blue/red…）的不是通用角色 token
            if re.search(r'(violet|purple|pink|orange|teal|cyan|indigo|amber|lime|emerald|sky|rose|fuchsia|bronze|gold|silver)', low):
                continue
            if role in EMPHASIS_ROLES and saturation(hexv) < 0.15:
                continue      # 灰阶不能当强调色
            chosen = (tok, hexv, conf)
            break
        if chosen:
            tok, hexv, conf = chosen
            result["colors"][role] = {"value": hexv, "token": tok, "source": "css-var", "confidence": "high"}

    # ---- 2. 尺度层 ----
    for bucket, hits in scale_hits.items():
        seen = {}
        for step, rank, tok, value in sorted(hits, key=lambda x: (x[1], len(x[2]))):
            if step in seen: continue
            seen[step] = {"value": value, "token": tok}
        result[bucket] = seen

    # ---- 3. 回退：从实测统计推 ----
    def top(list_, key="value"):
        return list_[0][key] if list_ else None

    bgs = colors.get("backgrounds") or []
    fgs = colors.get("text") or []
    if "background" not in result["colors"] and bgs:
        result["colors"]["background"] = {"value": parse_color(top(bgs)) or top(bgs), "token": None, "source": "measured", "confidence": "medium"}
    if "foreground" not in result["colors"] and fgs:
        result["colors"]["foreground"] = {"value": parse_color(top(fgs)) or top(fgs), "token": None, "source": "measured", "confidence": "medium"}
    if not result["radius"] and radii:
        for i, r in enumerate(radii[:6]):
            result["radius"][str(i+1)] = {"value": r["value"], "token": None}
    if not result["spacing"] and spacing:
        for i, s in enumerate(spacing[:8]):
            result["spacing"][str(i+1)] = {"value": s["value"], "token": None}
    if not result["duration"] and (motion.get("durations")):
        for i, d in enumerate(motion["durations"][:5]):
            result["duration"][str(i+1)] = {"value": d["value"], "token": None}
    if not result["easing"] and (motion.get("easings")):
        for i, e in enumerate(motion["easings"][:4]):
            result["easing"][str(i+1)] = {"value": e["value"], "token": None}
    if not result["fontSize"] and (typo.get("scale")):
        sizes = []
        for t in typo["scale"][:14]:
            if t["size"] not in sizes: sizes.append(t["size"])
        for i, s in enumerate(sizes[:8]):
            result["fontSize"][str(i+1)] = {"value": s, "token": None}

    # 色板兜底：primary 从最饱和的 palette 里挑
    if "primary" not in result["colors"] and palette_hits["*"]:
        best, best_score = None, -1
        for name, hexv in palette_hits["*"]:
            r, g, b = int(hexv[1:3],16), int(hexv[3:5],16), int(hexv[5:7],16)
            mx, mn = max(r,g,b), min(r,g,b)
            sat = 0 if mx == mn else (mx-mn)/mx
            if re.search(r'(9\d\d|950|900)', name): continue   # 跳过过深的
            if sat < 0.2: continue
            score = sat
            if score > best_score:
                best, best_score = (name, hexv), score
        if best:
            result["colors"]["primary"] = {"value": best[1], "token": best[0], "source": "palette", "confidence": "medium"}

    return result

def main():
    src = Path("specs_final")
    out = Path("specs_sem")
    out.mkdir(exist_ok=True)
    report = defaultdict(int)
    for p in sorted(src.glob("*.json")):
        spec = json.loads(p.read_text())
        sem = build(spec)
        spec["semantics"] = sem
        (out / p.name).write_text(json.dumps(spec, ensure_ascii=False))
        report["total"] += 1
        if sem["colors"].get("primary"): report["primary"] += 1
        if sem["colors"].get("background"): report["background"] += 1
        if sem["colors"].get("foreground"): report["foreground"] += 1
        if sem["radius"]: report["radius"] += 1
        if sem["spacing"]: report["spacing"] += 1
        if sem["fontSize"]: report["fontSize"] += 1
        if sem["duration"]: report["duration"] += 1
    print("生成:", dict(report))

if __name__ == "__main__":
    main()
