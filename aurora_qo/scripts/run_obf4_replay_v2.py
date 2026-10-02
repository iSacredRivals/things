#!/usr/bin/env python3
"""Deob de obf_4 (bootstrapper Luarmor v4, Luraph v14.8) — REPLAY v2 CORREGIDO.

Errores del v1 (Task 64) que esta version arregla:
  1. _bsdata0 del stub FRESCO (Task 63) mezclado con los bodies de la sesion
     VIVA (Task 61) -> tokens de sesion inconsistentes -> stage key basura.
     v2: _bsdata0 del stub ORIGINAL de la sesion capturada
     (workspace_zip/qodump_1790732004_01_...), el mismo que genero los 4 bodies.
  2. Patrones http_responses equivocados: el v1 usaba _bsdata0[5] (campo
     equivocado; REQ#1 lleva d=_bsdata0[7]) y tokens del INTERIOR de los bodies
     (81f89075...) que NUNCA aparecen en las URLs reales. Los 4 requests no
     recibieron NINGUN body -> decode basura -> buffer.create "size out of
     range". v2: los prefijos d REALES de las URLs capturadas (meta files):
       REQ#1 d=929c0481... (= _bsdata0[7] del stub original)
       REQ#2 d=3f1863b1...  REQ#3 d=4965dbdb...  REQ#4 d=fc92fbc3...
  3. ldrupd8m=false: en la cadena capturada el stub parcheado tomo el path CDN
     (ldr upd8m = <fuente del init> + a(b) con arg). v2: ldrupd8m = la fuente
     ORIGINAL de obf_4.lua (764123 B == qodump_03, MD5 verificado).

La cache P2D (obf_4_arg.path2d) queda igual: hoy se valido que el modelo
offline es BIT-EXACTO contra los valores reales del device (13/13 same, sonda
del loader Frame 193x224 con p2d_check).
"""
import os
import re
import sys

ENGINE = "/home/z/my-project/deobf/deobf"
HERE = "/home/z/my-project/deobf/aurora"
MITM = HERE + "/analysis/replay/mitm"
SAMPLES = "/home/z/my-project/deobf/samples"
QODUMP = HERE + "/workspace_zip"

sys.path.insert(0, ENGINE)
os.chdir(ENGINE)

import harness as H  # noqa: E402

KEY = "LbdcJNWbjhlelJHknRFNRcbBzibDAyTl"
HWID = "d3b14c1f2a9b7e8c4d5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c"

# el stub de la SESION CAPTURADA (qodump 01, 1259 B) — NO el fresco de Task 63
STUB_ORIG = open(QODUMP + "/qodump_1790732004_01_api.luarmor.net_files_v4_loaders_0ae9fe4cf963e",
                 encoding="latin-1").read()
# la fuente original del init (== qodump 03 == samples/obf_4.lua, MD5 1b6abc28...)
BOOT_SRC = open(SAMPLES + "/obf_4.lua", encoding="latin-1").read()


def extract_bsdata(src):
    m = re.search(r"_bsdata0=\{(.*?)\};", src, re.S)
    assert m, "_bsdata0 no encontrado en el stub"
    return m.group(1)


def body_of(n):
    src = open(f"{MITM}/resp_{n}.luau", encoding="latin-1").read()
    i = src.find("__body = [")
    assert i > 0, f"resp_{n} sin __body"
    j = i + len("__body = ")
    k = j
    while src[k] == "=":
        k += 1
    assert src[k] == "["
    lvl = src[j:k]
    body_start = k + 1
    closer = "]" + lvl + "]"
    body_end = src.find(closer, body_start)
    assert body_end > 0, f"resp_{n} sin cierre"
    return src[body_start:body_end]


def main():
    bsdata = extract_bsdata(STUB_ORIG)
    # REQ#1 d = _bsdata0[7] (el token de 400 hex; verificado contra la URL del meta 04)
    toks = re.findall(r'"([0-9a-f]{16,})"', bsdata)
    assert len(toks) >= 2, "tokens del stub insuficientes"
    d1 = toks[-1][:16]  # [7] = el token LARGO (400 hex) = el d del REQ#1
    assert d1 == "929c04812ef86ea4", f"d1 inesperado: {d1}"

    bodies = [body_of(n) for n in (1, 2, 3, 4)]
    # prefijos d REALES de las URLs capturadas (meta 05/06/07)
    d2, d3, d4 = "3f1863b183c7fee0", "4965dbdba942502b", "fc92fbc3419fa60d"

    http_responses = [
        d1, bodies[0],
        d2, bodies[1],
        d3, bodies[2],
        d4, bodies[3],
    ]
    print(f"[*] replay http: REQ1~{d1} REQ2~{d2} REQ3~{d3} REQ4~{d4}", file=sys.stderr)
    print(f"[*] ldrupd8m = fuente original obf_4.lua ({len(BOOT_SRC)} bytes)", file=sys.stderr)

    prelude = (
        "rawset(env,'_bsdata0',{" + bsdata + "}) "
        "rawset(env,'ldrupd8m'," + H.long_string(BOOT_SRC) + ") "
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
        "-o", SAMPLES + "/output/obf_4_v2.deobf.luau",
    ]
    import deob  # noqa: E402
    deob.main()


if __name__ == "__main__":
    main()
