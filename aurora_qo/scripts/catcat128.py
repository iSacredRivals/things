#!/usr/bin/env python3
"""Port exacto del hash catcat128 de la SDK de Luarmor (obf_2_clean.lua) a Python.
Semántica de doubles replicada: l() usa multiplicación float (rounding IEEE754 a >2^53,
crítico en el rotate final x=4 con A=28), igual que Lua 5.1/Luau."""
import math, sys

MASK = 4294967296.0

def c(d):
    return d % MASK  # floor-mod, igual que Lua % para positivos

def e(f, g):
    # XOR bit a bit; los valores son enteros-valuados < 2^32 -> int() exacto
    return float(int(f) ^ int(g))

def l(d, m):
    # c(d * (2^m)) con mult float de IEEE754 (rounding cuando d*2^m > 2^53)
    prod = float(d) * (2.0 ** m)
    return prod % MASK

def n(d, m):
    return math.floor(float(d) / (2.0 ** m)) % MASK

def catcat128(o: str) -> str:
    ob = o.encode('utf-8')
    p = [1524013928.0, 62333482.0, 755453430.0, 3411017517.0]
    q = [451, 41992, 38477, 17184]
    r = len(ob)
    s = 1
    while s <= r:
        t = 0.0
        for u in range(4):
            v = (s - 1) + u
            if v < r:
                w = ob[v]
                t = t + (w * (2.0 ** (8 * u)))
        t = c(t)
        for x in range(1, 5):
            y = e(p[x-1], t)
            z = p[x % 4]            # lua p[(x%4)+1]
            y = e(y, z)
            y = c((l(y, 5) + n(y, 2)) + q[x-1])
            A = ((x - 1) * 5) % 32
            B = n(t, A)
            y = e(y, B)
            y = c(y)
            C = p[(x + 1) % 4]      # lua p[((x+1)%4)+1]
            y = c(y + C)
            p[x-1] = c(y)
        s = s + 4
    for x in range(1, 5):
        y = p[x-1]
        D = p[x % 4]                # lua p[(x%4)+1]
        E = p[(x + 2) % 4]          # lua p[((x+2)%4)+1]
        y = c(y + D)
        y = e(y, E)
        A = (x * 7) % 32
        y = c(l(y, A) + n(y, 32 - A))
        p[x-1] = y
    return "".join(f"{int(pv):08X}" for pv in p)

if __name__ == "__main__":
    inputs = [
        "test",
        "abcdefgh12345678",
        "x" * 100,
        "LbdcJNWbjhlelJHknRFNRcbBzibDAyTl_cfver1.0_0ae9fe4cf963e3a13d25eed0e2ce5940_time_1759190000",
        "KEY_cfver1.0_0123456789abcdef0123456789abcdef_time_1",
        "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa_cfver1.0_0ae9fe4cf963e3a13d25eed0e2ce5940_time_9999999999",
        "z",
        "ab",
        "abc",
        "abcd",
    ]
    for inp in inputs:
        print(catcat128(inp))
