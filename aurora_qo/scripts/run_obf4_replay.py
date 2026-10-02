#!/usr/bin/env python3
"""Deob de obf_4 (bootstrapper Luarmor v4, Luraph v14.8) con replay offline
de la sesion VIVA capturada (Task 61).

Ingredientes:
  1. _bsdata0 REAL del stub fresco (los tokens de sesion que alimentan el
     d-param del REQ#1 -> la stage key del VM del bootstrapper).
  2. http_responses con los 4 cuerpos capturados (challenge + 3 chunks),
     emparejados por el prefijo del d-param que el VM construira:
       REQ#1 d = _bsdata0[5].._bsdata0[7] (tokens del stub fresco)
       REQ#2 d = token del body de resp_1 (81f89075...)
       REQ#3 d = token del body de resp_2 (4e5482be...)
       REQ#4 d = token del body de resp_3 (9ee963db...)
  3. prelude fiel de Delta (key del user, hwid, syn tabla, gates falsos).
  4. cache P2D real del bootstrapper (samples/obf_4.path2d, 12 valores).

Nota: el header kkr del challenge NO viaja en el replay del engine
(Headers={}); si el VM lo necesita para el b-param del REQ#2 lo veremos
morir exactamente ahi (informacion igualmente valiosa).
"""
import os
import re
import sys

ENGINE = "/home/z/my-project/deobf/deobf"
HERE = "/home/z/my-project/deobf/aurora"
MITM = HERE + "/analysis/replay/mitm"
SAMPLES = "/home/z/my-project/deobf/samples"

sys.path.insert(0, ENGINE)
os.chdir(ENGINE)

import harness as H  # noqa: E402

KEY = "LbdcJNWbjhlelJHknRFNRcbBzibDAyTl"
HWID = "d3b14c1f2a9b7e8c4d5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c"
STUB = open(SAMPLES + "/luarmor_loader.lua", encoding="latin-1").read()


def extract_bsdata(src):
    m = re.search(r"_bsdata0=\{(.*?)\};", src, re.S)
    assert m, "_bsdata0 no encontrado en el stub"
    return m.group(1)


def body_of(n):
    src = open(f"{MITM}/resp_{n}.luau", encoding="latin-1").read()
    i = src.find("__body = [")
    assert i > 0, f"resp_{n} sin __body"
    # nivel de bracket variable: [=[ o [==[
    j = i + len("__body = ")
    k = j
    while src[k] == "=":
        k += 1
    assert src[k] == "["
    lvl = src[j:k]  # "=" o "=="
    body_start = k + 1
    closer = "]" + lvl + "]"
    body_end = src.find(closer, body_start)
    assert body_end > 0, f"resp_{n} sin cierre"
    return src[body_start:body_end]


def token_of(body):
    # el cuerpo es un JSON array (posible \n inicial): ["<token-hex>", ...
    m = re.search(r'\["([0-9a-f]{16})', body)
    assert m, "token del body no encontrado"
    return m.group(1)


def main():
    bsdata = extract_bsdata(STUB)
    # tokens hex del stub fresco (132-hex y 400-hex) para el patron del REQ#1
    toks = re.findall(r'"([0-9a-f]{16,})"', bsdata)
    assert len(toks) >= 2, "tokens del stub insuficientes"
    d1 = toks[0][:16]

    bodies = [body_of(n) for n in (1, 2, 3, 4)]
    d2 = token_of(bodies[0])
    d3 = token_of(bodies[1])
    d4 = token_of(bodies[2])

    http_responses = [
        d1, bodies[0],
        d2, bodies[1],
        d3, bodies[2],
        d4, bodies[3],
    ]
    print(f"[*] replay http: REQ1~{d1} REQ2~{d2} REQ3~{d3} REQ4~{d4}", file=sys.stderr)

    prelude = (
        "rawset(env,'_bsdata0',{" + bsdata + "}) "
        "rawset(env,'ldrupd8m',false) "
        "rawset(env,'script_key','" + KEY + "') "
        "genv.script_key='" + KEY + "' rawset(G,'script_key','" + KEY + "') "
        "rawset(env,'key','" + KEY + "') genv.key='" + KEY + "' "
        "rawset(shared,'script_key','" + KEY + "') rawset(shared,'key','" + KEY + "') "
        "genv.key_expire=0 genv.key_note='' genv.key_executions=0 "
        "rawset(env,'gethwid',function() return '" + HWID + "' end) "
        "rawset(env,'getexecutorname',function() return 'Delta' end) "
        "rawset(env,'delfolder',function() end) "
        "rawset(env,'FLUXUS_LOADED',false) rawset(env,'EVON_LOADED',false) "
        "rawset(env,'devsignature_sig',false) "
        "rawset(env,'LUARMOR_SkipAntidebugDevMode',false) "
        "rawset(env,'LUARMOR_AllowKeyCheckSkip',false) "
        "rawset(env,'USE_NON_SSL_NODE',false) "
        "rawset(env,'l_fastload_enabled',false) "
        "rawset(env,'syn',{request=env.request,writefile=env.writefile,"
        "readfile=env.readfile,isfile=env.isfile,isfolder=env.isfolder,"
        "delfile=env.delfile,delfolder=env.delfolder,makefolder=env.makefolder,"
        "setclipboard=env.setclipboard,toclipboard=env.toclipboard,"
        "getgenv=env.getgenv,identifyexecutor=env.identifyexecutor,"
        "getexecutorname=env.getexecutorname})"
    )

    orig_user_cfg = H.user_cfg

    def patched_user_cfg(args, cfg):
        cfg = orig_user_cfg(args, cfg)
        cfg["http_responses"] = list(http_responses)
        cfg["prelude"] = prelude
        # parches del harness MITM: el VM decode del bootstrapper genera
        # bloques larguisimos de __LC[21]() (el default 25000 los ahoga)
        cfg["max_block"] = 100000000
        cfg["max_stmts"] = 50000000
        return cfg

    H.user_cfg = patched_user_cfg

    sys.argv = [
        "deob.py", SAMPLES + "/obf_4_arg.lua",
        "--obfuscator", "luraph_v14",
        "--executor", "Delta",
        "--strings",
        "--no-pypy",
        "--timeout", "520",
        "--budget", "420",
        "-o", SAMPLES + "/output/obf_4_arg.deobf.luau",
    ]
    import deob  # noqa: E402
    deob.main()


if __name__ == "__main__":
    main()
