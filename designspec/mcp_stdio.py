#!/usr/bin/env python3
"""零依赖 MCP 服务器：直接实现 JSON-RPC 2.0 over stdio。

不需要 mcp 包，兼容 Python 3.8+。
用法：任何 MCP 客户端配置 command=python3, args=[本文件路径]
"""
import json, sys, traceback
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import server as S

PROTOCOL = "2024-11-05"
SERVER_INFO = {"name": "designeer-designspec", "version": "2.0.0"}

def log(*a):
    print(*a, file=sys.stderr, flush=True)

def tool_schemas():
    """把 TOOLS 里的参数说明转成 JSON Schema。"""
    out = []
    for name, (fn, desc, params) in S.TOOLS.items():
        props = {}
        required = []
        for pname, pdesc in (params or {}).items():
            props[pname] = {"type": "string", "description": str(pdesc)}
            required.append(pname)
        schema = {"type": "object", "properties": props}
        if required:
            schema["required"] = required
        out.append({
            "name": name,
            "description": desc,
            "inputSchema": schema,
        })
    return out

def call_tool(name, args):
    entry = S.TOOLS.get(name)
    if not entry:
        raise ValueError(f"unknown tool: {name}")
    fn = entry[0]
    try:
        result = fn(**args) if args else fn()
    except TypeError:
        # 参数不匹配时，尝试按位置传
        result = fn(*args.values()) if args else fn()
    if isinstance(result, (dict, list)):
        text = json.dumps(result, ensure_ascii=False, indent=1)
    else:
        text = str(result)
    return {"content": [{"type": "text", "text": text}]}

def handle(req):
    method = req.get("method")
    rid = req.get("id")
    params = req.get("params") or {}

    if method == "initialize":
        return {"jsonrpc":"2.0","id":rid,"result":{
            "protocolVersion": PROTOCOL,
            "capabilities": {"tools": {"listChanged": False}},
            "serverInfo": SERVER_INFO,
        }}

    if method == "notifications/initialized":
        return None   # 通知不需要回复

    if method == "tools/list":
        return {"jsonrpc":"2.0","id":rid,"result":{"tools": tool_schemas()}}

    if method == "tools/call":
        name = params.get("name")
        args = params.get("arguments") or {}
        try:
            return {"jsonrpc":"2.0","id":rid,"result": call_tool(name, args)}
        except Exception as e:
            log("tool error:", name, traceback.format_exc())
            return {"jsonrpc":"2.0","id":rid,"result":{
                "content": [{"type":"text","text": f"错误：{type(e).__name__}: {e}"}],
                "isError": True,
            }}

    if method in ("ping",):
        return {"jsonrpc":"2.0","id":rid,"result":{}}

    # 未知方法
    if rid is not None:
        return {"jsonrpc":"2.0","id":rid,"error":{"code":-32601,"message":f"method not found: {method}"}}
    return None

def main():
    log(f"designeer-designspec MCP server ready ({len(S.TOOLS)} tools)")
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            req = json.loads(line)
        except json.JSONDecodeError as e:
            print(json.dumps({"jsonrpc":"2.0","id":None,
                              "error":{"code":-32700,"message":f"parse error: {e}"}}), flush=True)
            continue

        # 支持批量
        if isinstance(req, list):
            outs = [handle(r) for r in req]
            outs = [o for o in outs if o is not None]
            if outs:
                print(json.dumps(outs, ensure_ascii=False), flush=True)
            continue

        resp = handle(req)
        if resp is not None:
            print(json.dumps(resp, ensure_ascii=False), flush=True)

if __name__ == "__main__":
    main()
