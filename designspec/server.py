#!/usr/bin/env python3
"""DesignSpec MCP server + CLI over the local design-token corpus.

Tools (all read-only):
  list_specs        - every catalogued site with a spec
  search_specs      - lexical search across names, hosts, fonts, colours, CSS vars
  get_spec          - the complete spec for one site (all fields, no truncation)
  get_components    - variants, size tables and rendered samples per component
  get_states        - measured hover/focus/active deltas
  get_tokens        - semantic colour tokens by role
  get_semantics     - full semantic map incl. scale ladders
  get_design_spec   - standard-format spec (10 chapters)
  suggest_tokens    - recommended values for a purpose
  compare_sites     - side-by-side site comparison
  audit_page        - audit any URL against the corpus baseline
  get_section       - every spec in one catalogue section
  compare_specs     - what several sites share in radii / motion / fonts
  export_theme      - emit a ready-to-paste CSS/JSON theme for one site
  corpus_stats      - corpus size and covered sections

Run as MCP (stdio):
  python server.py
CLI:
  python server.py list
  python server.py search "Inter" --limit 5
  python server.py get t001
  python server.py theme t001 --format css
"""
import json, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import queries
import advice

SPEC_FIELDS = ["id","name","url","section","capturedAt","page","cssVariables",
  "breakpoints","mediaQueryCount","typography","colors","spacing","radii","shadows",
  "borders","motion","components","layout","fontFaces"]

def tool_list_specs():
    return {"specs": [
        {"id": s.get("id"), "name": s.get("name"), "url": s.get("url"),
         "section": s.get("section"), "cssVariableCount": len(s.get("cssVariables") or {})}
        for s in queries.all_specs()
    ]}

def tool_search_specs(query="", section=None, limit=20):
    limit = max(1, min(int(limit or 20), 100))
    return {"query": query, "section": section, "results": queries.search(query, section, limit)}

def tool_get_spec(spec_id):
    spec = queries.get(spec_id)
    if not spec:
        return {"error": f"no spec with id {spec_id}", "hint": "call search_specs or list_specs first"}
    return {k: spec.get(k) for k in SPEC_FIELDS if k in spec}

def tool_get_section(section):
    rows = [queries.summarize(s) for s in queries.all_specs() if s.get("section") == section]
    return {"section": section, "count": len(rows), "specs": rows}

def tool_compare_specs(ids):
    if isinstance(ids, str):
        ids = [x.strip() for x in ids.split(",") if x.strip()]
    return queries.compare(ids)

def tool_export_theme(spec_id, fmt="css"):
    out = queries.export_theme(spec_id, fmt)
    if out is None:
        return {"error": f"no spec with id {spec_id}"}
    return {"id": spec_id, "format": fmt, "theme": out}

def tool_get_components(spec_id, kind=None):
    out = queries.components_of(spec_id, kind)
    if out is None:
        return {"error": f"no spec with id {spec_id}"}
    return {"id": spec_id, "kind": kind, "components": out}

def tool_get_states(spec_id, state=None):
    out = queries.states_of(spec_id, state)
    if out is None:
        return {"error": f"no spec with id {spec_id}"}
    return {"id": spec_id, "state": state, **out}

def tool_get_tokens(spec_id, role=None):
    out = queries.tokens_of(spec_id, role)
    if out is None:
        return {"error": f"no spec with id {spec_id}"}
    return {"id": spec_id, "role": role, "tokens": out}

def tool_get_semantics(spec_id):
    """Semantic token mapping for one spec: colours by role, scale ladders."""
    spec = queries.get(spec_id)
    if not spec:
        return {"error": f"no spec with id {spec_id}"}
    sem = spec.get("semantics") or {}
    return {
        "id": spec_id, "name": spec.get("name"), "url": spec.get("url"),
        "colors": sem.get("colors"), "radius": sem.get("radius"),
        "spacing": sem.get("spacing"), "fontSize": sem.get("fontSize"),
        "duration": sem.get("duration"), "easing": sem.get("easing"),
        "shadow": sem.get("shadow"),
    }

def tool_get_design_spec(spec_id):
    """Standard-format design specification document (10 chapters)."""
    d = queries.get_generated(spec_id)
    if not d:
        return {"error": f"no generated spec for {spec_id}"}
    return d

def tool_list_design_specs():
    return {"specs": queries.list_generated()}

def tool_suggest_tokens(purpose, limit=10):
    """Recommend tokens by purpose, based on the 544-site distribution."""
    return advice.suggest_tokens(purpose, int(limit))

def tool_compare_sites(ids):
    """Side-by-side comparison of several sites."""
    if isinstance(ids, str):
        ids = [x.strip() for x in ids.split(",") if x.strip()]
    return advice.compare_sites(ids)

def tool_audit_page(url, timeout=30, platform="desktop"):
    """Fetch a URL and audit it against the corpus baseline."""
    return advice.audit_page(url, int(timeout), platform)

def tool_corpus_stats():
    return queries.stats()

TOOLS = {
    "list_specs": (tool_list_specs, "List every catalogued site that has a design spec.", {}),
    "search_specs": (tool_search_specs, "Search specs by name, host, font family, colour value or CSS variable name.",
        {"query": "search terms", "section": "optional exact section label", "limit": "1..100, default 20"}),
    "get_spec": (tool_get_spec, "Return the COMPLETE design spec for one site id, every field included.",
        {"spec_id": "id from search_specs"}),
    "get_section": (tool_get_section, "Return every spec in one catalogue section.",
        {"section": "exact section label, e.g. 组件库"}),
    "compare_specs": (tool_compare_specs, "Show what several sites share: radii, durations, easings, fonts.",
        {"ids": "comma separated spec ids"}),
    "export_theme": (tool_export_theme, "Emit a ready-to-paste CSS variable theme (or JSON) for one site.",
        {"spec_id": "id", "fmt": "css or json"}),
    "get_components": (tool_get_components, "Component specs: variants, size tables, rendered samples.",
        {"spec_id": "id", "kind": "optional: button, input, link, card, nav, badge, avatar, table, modal, tabs, tooltip, dropdown"}),
    "get_states": (tool_get_states, "Measured interaction states (hover/focus/active) with the CSS properties that change.",
        {"spec_id": "id", "state": "optional: hover, focus, active"}),
    "get_tokens": (tool_get_tokens, "Semantic colour tokens grouped by role (primary/danger/success/warning/info/neutral).",
        {"spec_id": "id", "role": "optional role"}),
    "get_design_spec": (tool_get_design_spec, "Standard-format design specification: overview, principles, colours, typography, spacing, shape, motion, components, a11y, usage.",
        {"spec_id": "id"}),
    "list_design_specs": (tool_list_design_specs, "All generated design specifications with coverage score.", {}),
    "get_semantics": (tool_get_semantics, "Semantic token map: colours by role (primary/danger/...), radius/spacing/font/duration ladders.",
        {"spec_id": "id"}),
    "suggest_tokens": (tool_suggest_tokens, "Recommend token values for a purpose (button/radius/spacing/duration/body/...), ranked by how often they appear across 544 real sites.",
        {"purpose": "button | button-sm | input | card | badge | nav | tab | heading | body | radius | shadow | spacing | duration | easing | primary", "limit": "1..30, default 10"}),
    "compare_sites": (tool_compare_sites, "Side-by-side comparison of several sites: colours, type, radius, spacing, motion, components.",
        {"ids": "comma separated spec ids"}),
    "audit_page": (tool_audit_page, "Fetch any URL, measure it, and report where it deviates from the 544-site baseline (contrast, type scale, tap targets, h1, alt).",
        {"url": "http(s) URL", "timeout": "seconds, default 30", "platform": "desktop | mobile, default desktop"}),
    "corpus_stats": (tool_corpus_stats, "Corpus size and covered sections.", {}),
}

def run_mcp():
    try:
        from mcp.server.fastmcp import FastMCP
    except ImportError:
        print("mcp 包未安装（需要 Python >=3.10）。改用零依赖版本：", file=sys.stderr)
        print("  python3 mcp_stdio.py", file=sys.stderr)
        sys.exit(2)
    mcp = FastMCP("designeer-designspec")
    for name, (fn, desc, params) in TOOLS.items():
        mcp.tool(name=name, description=desc)(fn)
    mcp.run(transport="stdio")

def main():
    if len(sys.argv) == 1:
        run_mcp()
        return
    cmd = sys.argv[1]
    args = sys.argv[2:]
    if cmd == "list":
        print(json.dumps(tool_list_specs(), ensure_ascii=False, indent=2))
    elif cmd == "search":
        q = args[0] if args else ""
        limit = 20
        if "--limit" in args:
            limit = int(args[args.index("--limit") + 1])
        sec = args[args.index("--section") + 1] if "--section" in args else None
        print(json.dumps(tool_search_specs(q, sec, limit), ensure_ascii=False, indent=2))
    elif cmd == "get":
        print(json.dumps(tool_get_spec(args[0]), ensure_ascii=False, indent=2))
    elif cmd == "section":
        print(json.dumps(tool_get_section(args[0]), ensure_ascii=False, indent=2))
    elif cmd == "compare":
        ids = []
        for a in args:
            ids.extend([x.strip() for x in a.split(",") if x.strip()])
        print(json.dumps(tool_compare_specs(ids), ensure_ascii=False, indent=2))
    elif cmd == "theme":
        fmt = args[args.index("--format") + 1] if "--format" in args else "css"
        res = tool_export_theme(args[0], fmt)
        if "--raw" in args:
            # 直接输出 CSS 正文，方便重定向到文件
            print(res.get("theme") or res.get("css") or json.dumps(res, ensure_ascii=False))
        else:
            print(json.dumps(res, ensure_ascii=False, indent=2))
    elif cmd == "components":
        print(json.dumps(tool_get_components(args[0], args[1] if len(args)>1 else None), ensure_ascii=False, indent=2))
    elif cmd == "states":
        print(json.dumps(tool_get_states(args[0], args[1] if len(args)>1 else None), ensure_ascii=False, indent=2))
    elif cmd == "tokens":
        print(json.dumps(tool_get_tokens(args[0], args[1] if len(args)>1 else None), ensure_ascii=False, indent=2))
    elif cmd == "spec":
        print(json.dumps(tool_get_design_spec(args[0]), ensure_ascii=False, indent=2))
    elif cmd == "semantics":
        print(json.dumps(tool_get_semantics(args[0]), ensure_ascii=False, indent=2))
    elif cmd == "suggest":
        print(json.dumps(tool_suggest_tokens(args[0] if args else "button"), ensure_ascii=False, indent=2))
    elif cmd in ("compare-sites", "compare_sites"):
        ids = []
        for a in args:
            ids.extend([x.strip() for x in a.split(",") if x.strip()])
        print(json.dumps(tool_compare_sites(ids), ensure_ascii=False, indent=2))
    elif cmd == "audit":
        url = args[0]
        plat = "desktop"
        if "--mobile" in args: plat = "mobile"
        print(json.dumps(tool_audit_page(url, 30, plat), ensure_ascii=False, indent=2))
    elif cmd == "stats":
        print(json.dumps(tool_corpus_stats(), ensure_ascii=False, indent=2))
    else:
        print(__doc__)
        sys.exit(1)

if __name__ == "__main__":
    main()
