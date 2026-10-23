"""Merge v2 (base tokens) with v3 (components/states/sizes) into the final corpus."""
import json, re
from pathlib import Path

BASE = Path("raw")
V3 = Path("raw_v3")
OUT = Path("specs")

def load(p):
    try:
        d = json.loads(p.read_text())
        return d if d else None
    except Exception:
        return None

def norm_radius(v):
    if not isinstance(v, str): return v
    return re.sub(r'[\d.]+e[+-]?\d+px', '9999px', v)

def merge(base, v3):
    out = dict(base)
    if not v3:
        return out
    comps = v3.get("components") or {}
    # 只保留有内容的组件类型
    out["components"] = {k: v for k, v in comps.items() if v}
    out["componentStates"] = v3.get("stateRules") or {}
    out["sizeTables"] = v3.get("sizeTables") or {}
    out["semanticTokens"] = v3.get("semanticTokens") or {}
    out["scaleTokens"] = v3.get("scaleTokens") or {}
    out["a11y"] = v3.get("a11y") or {}
    out["grid"] = v3.get("grid") or {}
    out["fontFaces"] = v3.get("fontFaces") or out.get("fontFaces") or []
    if v3.get("page"):
        out["page"] = {**out.get("page", {}), **{k:v for k,v in v3["page"].items() if v is not None}}
    # 清理 radius 异常
    for r in out.get("radii") or []:
        r["value"] = norm_radius(r.get("value"))
    for kind, rows in (out.get("components") or {}).items():
        for row in rows:
            st = row.get("style")
            if st:
                st["borderRadius"] = norm_radius(st.get("borderRadius"))
    return out

def main():
    OUT.mkdir(exist_ok=True)
    ids = sorted({p.stem for p in BASE.glob("*.json")})
    merged = 0
    for sid in ids:
        b = load(BASE / f"{sid}.json")
        if not b: continue
        v = load(V3 / f"{sid}.json")
        out = merge(b, v)
        (OUT / f"{sid}.json").write_text(json.dumps(out, ensure_ascii=False))
        merged += 1
    print("merged", merged, "->", OUT)
    # 统计
    stats = {"withStates":0,"withComponents":0,"withSizes":0,"withSemantic":0,"withA11y":0}
    for p in OUT.glob("*.json"):
        d = json.loads(p.read_text())
        if any((d.get("componentStates") or {}).values()): stats["withStates"] += 1
        if any((d.get("components") or {}).values()): stats["withComponents"] += 1
        if any(v for k,v in (d.get("sizeTables") or {}).items()): stats["withSizes"] += 1
        if d.get("semanticTokens"): stats["withSemantic"] += 1
        if d.get("a11y"): stats["withA11y"] += 1
    print(stats)

if __name__ == "__main__":
    main()
