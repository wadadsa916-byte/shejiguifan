"""Reorganise raw captures into a TDesign-shaped, AI-consumable design spec."""
import json, re
from pathlib import Path
from collections import Counter, defaultdict

COMPONENTS = {
    "button": "按钮", "link": "链接", "input": "输入框", "card": "卡片",
    "nav": "导航", "badge": "徽标", "avatar": "头像", "table": "表格",
    "modal": "对话框", "tabs": "标签页", "tooltip": "文字提示", "dropdown": "下拉菜单",
}
STATES = ["default", "hover", "focus", "active", "disabled", "checked"]

NOISE_RE = re.compile(r'(\\:|group-hover|data-\[|aria-\[|\[&|:where\(|:is\(\.group|peer-|\[\&\>)')

def meaningful(selector):
    """Keep selectors that name a real component, drop utility-class permutations."""
    if NOISE_RE.search(selector):
        return False
    if len(selector) > 120:
        return False
    return True

def pick_state_rules(spec):
    out = {}
    for state in STATES:
        rules = (spec.get("componentStates") or {}).get(state) or []
        keep = []
        for r in rules:
            if not meaningful(r["selector"]):
                continue
            keep.append({
                "selector": r["selector"][:100],
                "changes": r["declarations"],
            })
            if len(keep) >= 12:
                break
        if keep:
            out[state] = keep
    return out

def style_of(row):
    """v3 rows nest under 'style'; v2 rows are flat."""
    if isinstance(row.get("style"), dict):
        return row["style"]
    return row

def normalise_variants(rows):
    """Group rendered components by variant then size."""
    grouped = defaultdict(lambda: defaultdict(list))
    for row in rows:
        row = {**row, "style": style_of(row)}
        v = row.get("variant") or "default"
        s = row.get("size") or "md"
        grouped[v][s].append({
            "text": row.get("text", "")[:30],
            "height": row["style"]["height"],
            "padding": row["style"]["padding"],
            "radius": row["style"]["borderRadius"],
            "background": row["style"]["background"],
            "color": row["style"]["color"],
            "border": row["style"]["border"],
            "fontSize": row["style"]["fontSize"],
            "fontWeight": row["style"]["fontWeight"],
            "shadow": row["style"]["boxShadow"],
            "transition": row["style"]["transition"],
            "contrast": row["style"]["contrastTextOnBg"],
        })
    return {v: {s: rows2[:4] for s, rows2 in sizes.items()} for v, sizes in grouped.items()}

def build(spec):
    comps = spec.get("components") or {}
    components = {}
    for key, zh in COMPONENTS.items():
        rows = comps.get(key) or []
        if not rows:
            continue
        if key == "button":
            components[key] = {
                "label": zh,
                "variants": normalise_variants(rows),
                "sizeTable": (spec.get("sizeTables") or {}).get("button") or {},
            }
        elif key == "input":
            components[key] = {
                "label": zh,
                "samples": normalise_variants(rows),
                "sizeTable": (spec.get("sizeTables") or {}).get("input") or {},
            }
        else:
            components[key] = {
                "label": zh,
                "count": len(rows),
                "samples": [{
                    "height": style_of(r).get("height"),
                    "padding": style_of(r).get("padding"),
                    "radius": style_of(r).get("borderRadius"),
                    "background": style_of(r).get("background"),
                    "color": style_of(r).get("color"),
                    "border": style_of(r).get("border"),
                    "fontSize": style_of(r).get("fontSize"),
                } for r in rows[:6]],
            }
    return {
        "components": components,
        "states": pick_state_rules(spec),
        "a11y": spec.get("a11y") or {},
        "grid": spec.get("grid") or {},
        "scaleTokens": spec.get("scaleTokens") or {},
        "semanticTokens": spec.get("semanticTokens") or {},
    }

def main():
    src = Path("specs")
    out = Path("specs_v2")
    out.mkdir(exist_ok=True)
    n = 0
    stat = Counter()
    for p in sorted(src.glob("*.json")):
        spec = json.loads(p.read_text())
        extra = build(spec)
        spec["design"] = extra
        (out / p.name).write_text(json.dumps(spec, ensure_ascii=False))
        n += 1
        if extra["components"]: stat["withComponents"] += 1
        if extra["states"]: stat["withStates"] += 1
        if extra["a11y"]: stat["withA11y"] += 1
    print("built", n, dict(stat))

if __name__ == "__main__":
    main()
