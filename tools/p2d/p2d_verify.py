"""Independent float32 reimplementation of the engine's Path2D model.

Goal: verify that the Lua model (envlog.luau CHAIN.p2d) computes what its own
spec says. If Python f32 == Lua model answers, the model is internally
consistent (and the -442 divergence, if it is Path2D, is a Roblox-side
difference). If they differ, the Lua model has an arithmetic bug to fix.
"""
import math
import struct
import sys

import numpy as np

f32 = np.float32


def fmt17g(v):
    # Lua/Python both use C printf %.17g
    return ("%.17g" % float(v))


# --- the script's setup (from the trace) ---
W, H = f32(118), f32(255)

# UDim2: (xScale, xOffset, yScale, yOffset)
CP = [
    # (pos, left, right)
    ((0, 9, 0, -8), (0, 0, 0, 0), (0, -7, 0, -7)),
    ((0, 0, 0.3125, -2), (-0.0625, -5, 0, 6), (0, -8, -0.125, 7)),
    ((0.25, 2, 0.3125, 1), (0, 0, 0, 0), (0, -4, 0, 1)),
]


def resolve(u):
    return f32(f32(f32(u[0]) * W) + f32(u[1])), f32(f32(f32(u[2]) * H) + f32(u[3]))


pts = []
for pos, left, right in CP:
    px, py = resolve(pos)
    lx, ly = resolve(left)
    rx, ry = resolve(right)
    pts.append((float(px), float(py), float(lx), float(ly), float(rx), float(ry)))


def coeffs(s):
    n = len(s) // 2
    x0, y0 = s[0], s[1]
    c = {"n": n, "x0": f32(x0), "y0": f32(y0)}
    if n == 2:
        c["c1x"], c["c1y"] = f32(f32(s[2] - x0)), f32(f32(s[3] - y0))
    elif n == 3:
        x1, y1, x2, y2 = s[2], s[3], s[4], s[5]
        c["c1x"], c["c1y"] = f32(f32(x1 - x0) * f32(2)), f32(f32(y1 - y0) * f32(2))
        c["c2x"] = f32(f32(f32(x0 - f32(x1 * f32(2))) + f32(x2)))
        c["c2y"] = f32(f32(f32(y0 - f32(y1 * f32(2))) + f32(y2)))
    else:
        x1, y1, x2, y2, x3, y3 = s[2], s[3], s[4], s[5], s[6], s[7]
        c["c1x"] = f32(f32(x1 - x0) * f32(3))
        c["c1y"] = f32(f32(y1 - y0) * f32(3))
        c["c2x"] = f32(f32(f32(x0 - f32(x1 * f32(2))) + f32(x2)) * f32(3))
        c["c2y"] = f32(f32(f32(y0 - f32(y1 * f32(2))) + f32(y2)) * f32(3))
        c["c3x"] = f32(f32(f32(x3 - x0) + f32(x1 * f32(3))) - f32(x2 * f32(3)))
        c["c3y"] = f32(f32(f32(y3 - y0) + f32(y1 * f32(3))) - f32(y2 * f32(3)))
    return c


segs = []
for i in range(len(pts) - 1):
    a, b = pts[i], pts[i + 1]
    s = [a[0], a[1]]
    if a[4] != 0 or a[5] != 0:
        s += [f32(a[0] + a[4]), f32(a[1] + a[5])]
    if b[2] != 0 or b[3] != 0:
        s += [f32(b[0] + b[2]), f32(b[1] + b[3])]
    s += [b[0], b[1]]
    segs.append(coeffs(s))

print("segments:", [(c["n"], float(c["x0"]), float(c["y0"])) for c in segs])


def ev(c, u, eval0=False):
    u = f32(u)
    if c["n"] == 2:
        if eval0:
            return f32(c["c1x"] * u), f32(c["c1y"] * u)
        return f32(c["x0"] + f32(c["c1x"] * u)), f32(c["y0"] + f32(c["c1y"] * u))
    if c["n"] == 3:
        if eval0:
            return (f32(f32(c["c1x"] + f32(c["c2x"] * u)) * u),
                    f32(f32(c["c1y"] + f32(c["c2y"] * u)) * u))
        return (f32(c["x0"] + f32(f32(c["c1x"] + f32(c["c2x"] * u)) * u)),
                f32(c["y0"] + f32(f32(c["c1y"] + f32(c["c2y"] * u)) * u)))
    ix, iy = f32(c["c2x"] + f32(c["c3x"] * u)), f32(c["c2y"] + f32(c["c3y"] * u))
    if eval0:
        return f32(f32(c["c1x"] + f32(ix * u)) * u), f32(f32(c["c1y"] + f32(iy * u)) * u)
    return (f32(c["x0"] + f32(f32(c["c1x"] + f32(ix * u)) * u)),
            f32(c["y0"] + f32(f32(c["c1y"] + f32(iy * u)) * u)))


def tangent(c, u):
    u = f32(u)
    if c["n"] == 2:
        return c["c1x"], c["c1y"]
    if c["n"] == 3:
        k = f32(u * f32(2))
        return f32(c["c1x"] + f32(c["c2x"] * k)), f32(c["c1y"] + f32(c["c2y"] * k))
    k = f32(f32(3) * u)
    return (f32(c["c1x"] + f32(u * f32(f32(c["c2x"] * f32(2)) + f32(c["c3x"] * k)))),
            f32(c["c1y"] + f32(u * f32(f32(c["c2y"] * f32(2)) + f32(c["c3y"] * k)))))


def dist(ax, ay, bx, by):
    dx, dy = f32(bx - ax), f32(by - ay)
    return f32(math.sqrt(f32(f32(dx * dx) + f32(dy * dy))))


TOL = f32(1e-5)
sys.setrecursionlimit(10000)


def seglen(c):
    def rec(t0, t1, x0, y0, x1, y1, depth):
        tm = f32(f32(t0 + t1) * f32(0.5))
        xm, ym = ev(c, tm, eval0=True)
        a = dist(x0, y0, x1, y1)
        b = f32(dist(x0, y0, xm, ym) + dist(xm, ym, x1, y1))
        if depth >= 30 or f32(b - a) < TOL:
            return b
        return f32(rec(t0, tm, x0, y0, xm, ym, depth + 1) +
                   rec(tm, t1, xm, ym, x1, y1, depth + 1))
    x0, y0 = ev(c, 0, eval0=True)
    x1, y1 = ev(c, 1, eval0=True)
    return rec(f32(0), f32(1), x0, y0, x1, y1, 0)


SIXTH = f32(f32(1) / f32(6))


def arcU(c, s):
    d2x, d2y = f32(c["c2x"] * f32(2)), f32(c["c2y"] * f32(2))
    d3x = d3y = None
    if c["n"] == 4:
        d3x, d3y = f32(c["c3x"] * f32(3)), f32(c["c3y"] * f32(3))

    def inv(u):
        if c["n"] == 3:
            dx, dy = f32(c["c1x"] + f32(d2x * u)), f32(c["c1y"] + f32(d2y * u))
        else:
            dx = f32(c["c1x"] + f32(u * f32(d2x + f32(u * d3x))))
            dy = f32(c["c1y"] + f32(u * f32(d2y + f32(u * d3y))))
        return math.sqrt(f32(f32(dx * dx) + f32(dy * dy)))  # f64 sqrt, f32'd by callers

    h = f32(s / f32(32))
    u = f32(0)
    for _ in range(32):
        k1 = f32(h / f32(inv(u)))
        k2 = f32(h / f32(inv(f32(u + f32(k1 * f32(0.5))))))
        k3 = f32(h / f32(inv(f32(u + f32(k2 * f32(0.5))))))
        k4 = f32(h / f32(inv(f32(u + k3))))
        u = f32(u + f32(f32(f32(k1 + f32(f32(2) * f32(k2 + k3))) + k4) * SIXTH))
    return u


def length(segs):
    t = f32(0)
    for c in segs:
        if "len" not in c:
            c["len"] = seglen(c)
        t = f32(t + c["len"])
    return t


def locate(segs, t):
    t = f32(t)
    if t < 0:
        t = f32(0)
    elif t > 1:
        t = f32(1)
    n = len(segs)
    x = f32(t * f32(n))
    k = min(math.floor(x), n - 1)
    return segs[k], f32(x - k)


def locateArc(segs, t):
    t = f32(t)
    if t < 0:
        t = f32(0)
    elif t > 1:
        t = f32(1)
    L = length(segs)
    s = f32(t * L)
    for c in segs:
        if s <= c["len"]:
            if c["n"] == 2:
                return c, f32(s / c["len"])
            return c, arcU(c, s)
        s = f32(s - c["len"])
    return segs[0], f32(0)


QUERIES = [
    ("GetLength", None),
    ("GetPositionOnCurve", 0.2142857164144516),
    ("GetPositionOnCurve", 0.55555558204650879),
    ("GetPositionOnCurve", 0.92857140302658081),
    ("GetTangentOnCurve", 0.1666666716337204),
    ("GetTangentOnCurve", 0.80000001192092896),
    ("GetTangentOnCurve", 0.625),
    ("GetPositionOnCurveArcLength", 0.625),
    ("GetPositionOnCurveArcLength", 0.66666668653488159),
    ("GetTangentOnCurveArcLength", 0.5),
    ("GetTangentOnCurveArcLength", 0.5625),
]

MODEL_ANSWERS = [
    "n:138.62068176269531",
    "u:-0.011674169450998306,0,0.096768006682395935,0",
    "u:-0.010096256621181965,0,0.28553315997123718,0",
    "u:0.17952263355255127,0,0.28941076993942261,0",
    "v:-24.375,120.25",
    "v:41.000003814697266,13.550003051757812",
    "v:7.75,-23.375",
    "u:-0.029926817864179611,0,0.29498803615570068,0",
    "u:-0.0017578528495505452,0,0.30205968022346497,0",
    "v:-3.8972949981689453,118.71534729003906",
    "v:4.3236103057861328,96.916694641113281",
]

ok = 0
for (name, t), expect in zip(QUERIES, MODEL_ANSWERS):
    if name == "GetLength":
        got = "n:" + fmt17g(length(segs))
    else:
        if name in ("GetPositionOnCurve", "GetTangentOnCurve"):
            c, u = locate(segs, t)
        else:
            c, u = locateArc(segs, t)
        if name.startswith("GetPosition"):
            x, y = ev(c, u)
            got = "u:%s,0,%s,0" % (fmt17g(f32(x / W)), fmt17g(f32(y / H)))
        else:
            x, y = tangent(c, u)
            got = "v:%s,%s" % (fmt17g(x), fmt17g(y))
    match = got == expect
    ok += match
    print("%-38s %s  %s" % (name + ("|" + fmt17g(t) if t is not None else ""), "OK" if match else "DIFF",
                            "" if match else "\n  python: %s\n  lua   : %s" % (got, expect)))

print("\n%d/11 match the Lua model" % ok)
