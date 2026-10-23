"""完整 CSS 颜色解析：支持 lab / lch / oklab / oklch / color() / color-mix()。

浏览器已经能用这些函数，但采集时拿到的是字符串，直接正则只能认 rgb/hex。
这里补上到 sRGB 的转换，让对比度能算出来。
"""
import math, re

def _clamp01(x): return max(0.0, min(1.0, x))

def _srgb_from_linear(c):
    c = _clamp01(c)
    return 12.92*c if c <= 0.0031308 else 1.055*(c**(1/2.4)) - 0.055

def _linear_from_srgb(c):
    c = _clamp01(c)
    return c/12.92 if c <= 0.04045 else ((c+0.055)/1.055)**2.4

def _lab_to_xyz(L, a, b):
    """CIELAB (D65) -> XYZ"""
    fy = (L + 16) / 116
    fx = fy + a / 500
    fz = fy - b / 200
    def finv(t):
        return t**3 if t**3 > 0.008856 else (t - 16/116) / 7.787
    xr, yr, zr = finv(fx), finv(fy), finv(fz)
    # D65 白点
    return (xr*0.95047, yr*1.0, zr*1.08883)

def _xyz_to_srgb(x, y, z):
    r =  3.2404542*x - 1.5371385*y - 0.4985314*z
    g = -0.9692660*x + 1.8760108*y + 0.0415560*z
    b =  0.0556434*x - 0.2040259*y + 1.0572252*z
    return (_srgb_from_linear(r), _srgb_from_linear(g), _srgb_from_linear(b))

def _oklab_to_srgb(L, a, b):
    l_ = L + 0.3963377774*a + 0.2158037573*b
    m_ = L - 0.1055613458*a - 0.0638541728*b
    s_ = L - 0.0894841775*a - 1.2914855480*b
    l, m, s = l_**3, m_**3, s_**3
    r =  4.0767416621*l - 3.3077115913*m + 0.2309699292*s
    g = -1.2684380046*l + 2.6097574011*m - 0.3413193965*s
    bb = -0.0041960863*l - 0.7034186147*m + 1.7076147010*s
    return (_srgb_from_linear(r), _srgb_from_linear(g), _srgb_from_linear(bb))

def _num(tok):
    """解析数字，支持百分比和 none。"""
    if tok is None: return 0.0
    tok = tok.strip()
    if tok == "none": return 0.0
    if tok.endswith("%"):
        return float(tok[:-1]) / 100
    return float(tok)

def _hue(tok):
    tok = tok.strip()
    if tok == "none": return 0.0
    m = re.match(r'(-?[\d.]+)(deg|rad|turn|grad)?$', tok)
    if not m: return 0.0
    v = float(m.group(1)); u = m.group(2) or "deg"
    if u == "rad": return math.degrees(v)
    if u == "turn": return v * 360
    if u == "grad": return v * 0.9
    return v

def _alpha(part):
    """从 ' / 0.5' 里取 alpha"""
    m = re.search(r'/\s*([\d.]+%?|none)', part)
    if not m: return 1.0
    t = m.group(1)
    if t == "none": return 1.0
    if t.endswith("%"): return float(t[:-1]) / 100
    return float(t)

def parse_color(v):
    """返回 (r,g,b,a) 各 0-255/0-1，或 None。"""
    if not isinstance(v, str): return None
    s = v.strip().lower()

    # hex
    m = re.fullmatch(r'#([0-9a-f]{3,8})', s)
    if m:
        h = m.group(1)
        if len(h) == 3: h = "".join(c*2 for c in h)
        elif len(h) == 4: h = "".join(c*2 for c in h)
        if len(h) not in (6, 8): return None
        r, g, b = int(h[0:2],16), int(h[2:4],16), int(h[4:6],16)
        a = int(h[6:8],16)/255 if len(h) == 8 else 1.0
        return (r, g, b, a)

    # rgb / rgba
    m = re.match(r'rgba?\(([^)]+)\)', s)
    if m:
        body = m.group(1)
        alpha = _alpha(body)
        parts = re.split(r'[\s,]+', re.sub(r'/\s*[\d.]+%?', '', body).strip())
        nums = [p for p in parts if p and p != "none"]
        if len(nums) < 3: return None
        def chan(t):
            if t.endswith("%"): return float(t[:-1]) / 100 * 255
            return float(t)
        try:
            r, g, b = (chan(t) for t in nums[:3])
        except ValueError:
            return None
        return (r, g, b, alpha)

    # lab()
    m = re.match(r'lab\(([^)]+)\)', s)
    if m:
        body = m.group(1)
        alpha = _alpha(body)
        parts = re.split(r'\s+', re.sub(r'/\s*[\d.]+%?', '', body).strip())
        if len(parts) < 3: return None
        try:
            L = float(parts[0].replace('%',''))  # lab L 是 0-100
            a = float(parts[1]) if parts[1] != "none" else 0.0
            b = float(parts[2]) if parts[2] != "none" else 0.0
        except ValueError:
            return None
        xyz = _lab_to_xyz(L, a, b)
        r, g, bb = _xyz_to_srgb(*xyz)
        return (r*255, g*255, bb*255, alpha)

    # lch()
    m = re.match(r'lch\(([^)]+)\)', s)
    if m:
        body = m.group(1)
        alpha = _alpha(body)
        parts = re.split(r'\s+', re.sub(r'/\s*[\d.]+%?', '', body).strip())
        if len(parts) < 3: return None
        try:
            L = float(parts[0].replace('%',''))
            C = float(parts[1]) if parts[1] != "none" else 0.0
            H = _hue(parts[2])
        except ValueError:
            return None
        a = C * math.cos(math.radians(H))
        b = C * math.sin(math.radians(H))
        xyz = _lab_to_xyz(L, a, b)
        r, g, bb = _xyz_to_srgb(*xyz)
        return (r*255, g*255, bb*255, alpha)

    # oklab()
    m = re.match(r'oklab\(([^)]+)\)', s)
    if m:
        body = m.group(1)
        alpha = _alpha(body)
        parts = re.split(r'\s+', re.sub(r'/\s*[\d.]+%?', '', body).strip())
        if len(parts) < 3: return None
        try:
            L = _num(parts[0]) if parts[0].endswith('%') else float(parts[0])
            if not parts[0].endswith('%'): L = float(parts[0])
            else: L = float(parts[0][:-1]) / 100
            a = float(parts[1]) if parts[1] != "none" else 0.0
            b = float(parts[2]) if parts[2] != "none" else 0.0
        except ValueError:
            return None
        r, g, bb = _oklab_to_srgb(L, a, b)
        return (r*255, g*255, bb*255, alpha)

    # oklch()
    m = re.match(r'oklch\(([^)]+)\)', s)
    if m:
        body = m.group(1)
        alpha = _alpha(body)
        parts = re.split(r'\s+', re.sub(r'/\s*[\d.]+%?', '', body).strip())
        if len(parts) < 3: return None
        try:
            L = float(parts[0][:-1]) / 100 if parts[0].endswith('%') else float(parts[0])
            C = float(parts[1]) if parts[1] != "none" else 0.0
            H = _hue(parts[2])
        except ValueError:
            return None
        a = C * math.cos(math.radians(H))
        b = C * math.sin(math.radians(H))
        r, g, bb = _oklab_to_srgb(L, a, b)
        return (r*255, g*255, bb*255, alpha)

    # color(display-p3 ...) / color(srgb ...)
    m = re.match(r'color\(\s*(display-p3|srgb|rec2020)\s+([^)]+)\)', s)
    if m:
        space = m.group(1)
        body = m.group(2)
        alpha = _alpha(body)
        parts = re.split(r'\s+', re.sub(r'/\s*[\d.]+%?', '', body).strip())
        if len(parts) < 3: return None
        try:
            c = [float(x) if x != "none" else 0.0 for x in parts[:3]]
        except ValueError:
            return None
        if space == "srgb":
            return (c[0]*255, c[1]*255, c[2]*255, alpha)
        if space == "display-p3":
            # P3 -> sRGB（近似，够算对比度）
            r = _linear_from_srgb(c[0]); g = _linear_from_srgb(c[1]); b = _linear_from_srgb(c[2])
            r2 =  1.2249401*r - 0.2249404*g
            g2 = -0.0420569*r + 1.0420571*g
            b2 = -0.0196376*r - 0.0786361*g + 1.0982735*b
            return (_srgb_from_linear(r2)*255, _srgb_from_linear(g2)*255, _srgb_from_linear(b2)*255, alpha)
        return (c[0]*255, c[1]*255, c[2]*255, alpha)

    # color-mix()
    m = re.match(r'color-mix\(in\s+(\w+)\s*,([^)]+)\)', s)
    if m:
        space = m.group(1)
        body = m.group(2)
        parts = [p.strip() for p in body.split(",")]
        if len(parts) != 2: return None
        def split_pct(t):
            mm = re.match(r'^(.*?)(?:\s+([\d.]+)%)?$', t.strip())
            return mm.group(1).strip(), (float(mm.group(2))/100 if mm.group(2) else None)
        c1, p1 = split_pct(parts[0])
        c2, p2 = split_pct(parts[1])
        a1 = parse_color(c1); a2 = parse_color(c2)
        if not a1 or not a2: return None
        if p1 is None and p2 is None: p1, p2 = 0.5, 0.5
        elif p1 is None: p1 = 1 - p2
        elif p2 is None: p2 = 1 - p1
        tot = p1 + p2
        if tot == 0: return None
        p1, p2 = p1/tot, p2/tot
        return tuple(a1[i]*p1 + a2[i]*p2 for i in range(4))

    # 命名色（常用）
    NAMED = {
        "white":(255,255,255,1), "black":(0,0,0,1), "transparent":(0,0,0,0),
        "red":(255,0,0,1), "blue":(0,0,255,1), "green":(0,128,0,1),
        "gray":(128,128,128,1), "grey":(128,128,128,1),
    }
    return NAMED.get(s)

def to_hex(v):
    """颜色字符串 -> #rrggbb，无法解析返回 None。"""
    c = parse_color(v)
    if not c: return None
    r, g, b = (max(0, min(255, round(x))) for x in c[:3])
    return "#%02x%02x%02x" % (r, g, b)

def luminance(v):
    c = parse_color(v)
    if not c: return None
    def ch(x):
        x = max(0, min(255, x)) / 255
        return x/12.92 if x <= 0.03928 else ((x+0.055)/1.055)**2.4
    return 0.2126*ch(c[0]) + 0.7152*ch(c[1]) + 0.0722*ch(c[2])

def contrast(a, b):
    la, lb = luminance(a), luminance(b)
    if la is None or lb is None: return None
    hi, lo = max(la, lb), min(la, lb)
    return round((hi+0.05)/(lo+0.05), 2)
