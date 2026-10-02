#!/usr/bin/env python3
"""Deob de obf_4 (bootstrapper Luarmor v4, Luraph v14.8) — REPLAY v14 = v13 + diagnostico SUBNIL en wrapLib (traceback cuando el VM llama string.sub(nil)).

v2 corrigio _bsdata0/patrones http/ldrupd8m y sigue muriendo en
buffer.create "size out of range" ANTES de cualquier request visible. v3 anade:

  1. plugin_rt con SPIES (print directo \0SPY, invisible al throttle):
     buffer.create/fromstring (tamanos), os.time/clock (valores),
     request/http_request (URLs), Random.new (semillas), writefile (paths).
  2. Parches de texto al harness (los PROBADOS de make_mitm, Task 61):
     - __JSON real + hook HttpService:JSONDecode/JSONEncode en onCall
       (el generico de envlog devuelve proxies y la cadena moria)
     - readfile -> nil (estado primera corrida; el proxy truthy corrompe)
     - delivery http_responses con Headers REALES (Kkr incluido) + RESPTOUCH
  3. --raw para capturar TODA la salida cruda del run final.

Con esto vemos exactamente QUE lee el VM antes del buffer.create y por donde
entra el valor corrupto.
"""
import ast
import os
import re
import sys

ENGINE = "/home/z/my-project/deobf/deobf"
HERE = "/home/z/my-project/deobf/aurora"
MITM = HERE + "/analysis/replay/mitm"
SAMPLES = "/home/z/my-project/deobf/samples"
QODUMP = HERE + "/workspace_zip"
MAKE_MITM = HERE + "/scripts/make_mitm.py"

sys.path.insert(0, ENGINE)
os.chdir(ENGINE)

import harness as H  # noqa: E402

KEY = "LbdcJNWbjhlelJHknRFNRcbBzibDAyTl"
HWID = "d3b14c1f2a9b7e8c4d5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c"

STUB_ORIG = open(MITM + "/stub_session.lua", encoding="latin-1").read()
BOOT_SRC = open(SAMPLES + "/obf_4.lua", encoding="latin-1").read()


def extract_bsdata(src):
    m = re.search(r"_bsdata0=\{(.*?)\};", src, re.S)
    assert m, "_bsdata0 no encontrado en el stub"
    return m.group(1)


def body_of(n):
    src = open(f"{MITM}/resp_{n}.luau", encoding="latin-1").read()
    i = src.find("__body = [")
    j = i + len("__body = ")
    assert src[j] == "["
    k = j + 1                      # past the first '['
    while src[k] == "=":
        k += 1
    assert src[k] == "[", "opener"
    lvl = src[j + 1:k]             # the '='s
    body_start = k + 1
    closer = "]" + lvl + "]"
    body_end = src.find(closer, body_start)
    body = src[body_start:body_end]
    if body.startswith("\n"):      # Lua drops the leading newline
        body = body[1:]
    return body


def headers_of(n):
    src = open(f"{MITM}/resp_{n}.luau", encoding="latin-1").read()
    i = src.find("__headers = {")
    j = i + len("__headers = ")
    k = j
    depth = 0
    while k < len(src):
        if src[k] == "{":
            depth += 1
        elif src[k] == "}":
            depth -= 1
            if depth == 0:
                break
        k += 1
    return src[j:k + 1]


def mitm_assignments():
    """Extract json_code and the JSON-hook new-text from make_mitm.py (proven)."""
    tree = ast.parse(open(MAKE_MITM, encoding="latin-1").read())
    out = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and isinstance(node.value, ast.Constant) \
                and isinstance(node.value.value, str):
            v = node.value.value
            if "__jsonDec" in v and "json_code" not in out:
                out["json_code"] = v
            if "JSON real (patch MITM): HttpService:JSONDecode" in v:
                out["json_hook"] = v
    assert "json_code" in out and "json_hook" in out, f"make_mitm assigns: {list(out)}"
    return out


PLUGIN_RT = ''


def main():
    bsdata = extract_bsdata(STUB_ORIG)
    toks = re.findall(r'"([0-9a-f]{16,})"', bsdata)
    d1 = toks[-1][:16]
    assert d1 == "3ef566691ee60c25", f"d1 inesperado: {d1}"

    bodies = [body_of(n) for n in (1, 2, 3, 4)]
    hdrs = [headers_of(n) for n in (1, 2, 3, 4)]
    d2, d3, d4 = "81f890753132dda2", "4e5482beea149563", "9ee963db61e75775"  # tokens de los bodies (d-chain empirica)

    http_responses = [d1, bodies[0], d2, bodies[1], d3, bodies[2], d4, bodies[3]]
    print(f"[*] v3 spies + patches; REQ1~{d1} REQ2~{d2} REQ3~{d3} REQ4~{d4}", file=sys.stderr)

    prelude = (
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
        "rawset(env,'fireserver',function(...) end) "
        "rawset(env,'syn',{request=env.request,http_request=env.http_request,"
        "writefile=env.writefile,readfile=env.readfile,isfile=env.isfile,isfolder=env.isfolder,"
        "delfile=env.delfile,delfolder=env.delfolder,makefolder=env.makefolder,"
        "appendfile=env.appendfile,listfiles=env.listfiles,"
        "queue_on_teleport=env.queue_on_teleport,queueonteleport=env.queueonteleport,"
        "setclipboard=env.setclipboard,toclipboard=env.toclipboard,"
        "getgenv=env.getgenv,identifyexecutor=env.identifyexecutor,"
        "getexecutorname=env.getexecutorname,protect_gui=function(gui) return gui end})"
    )

    assigns = mitm_assignments()
    json_code = assigns["json_code"]
    json_hook = assigns["json_hook"]
    # CERO locals top-level nuevos (el chunk envlog esta al limite de 200):
    # todo va como CAMPOS de R (R.JSON, R.XHDR, R.respHdrs)
    json_code = json_code.replace("local __JSON = (function()", "R.JSON = (function()", 1)
    json_hook = json_hook.replace("__JSON.", "R.JSON.")

    # ---- patches de texto sobre el harness generado ----
    envlog_src = open(os.path.join(ENGINE, "envlog.luau"), encoding="utf-8").read()

    # delivery: extraer la linea exacta con su indentacion (dos sitios: label y name)
    m_label = re.search(r'\n([ \t]*)comment\("HTTP " \.\. label \.\. " -> recorded body \(" \.\. #body \.\. " bytes\)"\)\n[ \t]*return \{ Body = body, StatusCode = 200, Success = true, Headers = \{\} \}',
                        envlog_src)
    m_name = re.search(r'\n([ \t]*)return \{ Body = body, StatusCode = 200, Success = true, Headers = \{\} \}\n[ \t]*end\n[ \t]*return body\n', envlog_src)
    assert m_label and m_name, "delivery anchors no encontrados"

    hdr_block = (
        "\nR.XHDR = { [\"929c0481\"] = " + hdrs[0] + ", [\"3f1863b1\"] = " + hdrs[1] + ",\n"
        "[\"4965dbdb\"] = " + hdrs[2] + ", [\"fc92fbc3\"] = " + hdrs[3] + " }\n"
        "R.respHdrs = function(url)\n"
        "\tif R.type(url) == \"string\" then\n"
        "\t\tfor k, v in R.pairs(R.XHDR) do\n"
        "\t\t\tif R.find(url, k, 1, true) then return v end\n"
        "\t\tend\n"
        "\tend\n"
        "\treturn {}\n"
        "end\n"
    )

    def delivery_new(url_expr, ind):
        return ("\n" + ind + 'comment("HTTP -> recorded body (" .. #body .. " bytes)")\n'
                + ind + "local __h = R.respHdrs(" + url_expr + ")\n"
                + ind + "local __rr = {}\n"
                + ind + 'R.rawset(__rr, "Body", body)\n'
                + ind + 'R.rawset(__rr, "StatusCode", 200)\n'
                + ind + 'R.rawset(__rr, "Success", true)\n'
                + ind + 'R.rawset(__rr, "Headers", __h)\n'
                + ind + 'R.rawset(__rr, "StatusMessage", "OK")\n'
                + ind + "R.setmetatable(__rr, { __index = function(_, k)\n"
                + ind + '\tR.print("\\0RESPTOUCH " .. R.tostring(k))\n'
                + ind + "\treturn nil end })\n"
                + ind + "return __rr")

    # sitio httpRequest (label): url = opts.Url (o nil)
    old_label = m_label.group(0)
    new_label = delivery_new("opts and opts.Url", m_label.group(1))
    # sitio onCall (name): el return + end + return body (mantiene la cola)
    old_name = m_name.group(0)
    ind_name = m_name.group(1)
    new_name = delivery_new('(type(a1) == "table" and a1.Url) or a1', ind_name) \
        + "\n" + ind_name + "end\n" + ind_name + "return body\n"

    # readfile: __BOOTFILE embebido como en el mitm 4e (2 locales top-level)
    boot_patch = ("\nlocal __BOOTFILE = " + H.long_string(BOOT_SRC) + "\n"
                  'local __BOOTPATH = "static_content_170926/init-f07dbcbe19a-sephal.lua"\n')
    old_readfile = 'E.readfile = function(p) return callP("readfile(" .. fmt(p) .. ")", "contents", "string") end'
    new_readfile = (
        'E.readfile = function(p)\n'
        '\tif R.type(p) == "string" and (p == __BOOTPATH or R.find(p, __BOOTPATH, 1, true)) then\n'
        '\t\tcomment("readfile(cache bootstrapper) -> " .. #__BOOTFILE .. " bytes")\n'
        '\t\treturn __BOOTFILE\n'
        '\tend\n'
        '\tcomment("readfile(" .. fmt(p) .. ") -> nil (no existe)")\n'
        '\treturn nil\n'
        'end')
    old_isfile = 'E.isfile = function(p) comment("isfile(" .. fmt(p) .. ") -> false"); return false end'
    new_isfile = (
        'E.isfile = function(p)\n'
        '\tif R.type(p) == "string" and R.find(p, "static_content_170926/init-f07dbcbe19a-sephal.lua", 1, true) then\n'
        '\t\tcomment("isfile(" .. fmt(p) .. ") -> true")\n'
        '\t\treturn true\n'
        '\tend\n'
        '\tcomment("isfile(" .. fmt(p) .. ") -> false"); return false\n'
        'end')

    # onCall JSON hook: ancla = la linea de comentario falsy
    falsy_anchor = re.search(r'\n([ \t]*)-- --cfg falsy=a,b: calls of these names return false \(explore other branches\)', envlog_src)
    assert falsy_anchor, "ancla falsy no encontrada"
    hook_block = "\n" + json_hook

    orig_build = H.build_harness

    def patched_build(source, cfg, chunks=None):
        hsrc = orig_build(source, cfg, chunks)
        # A0) __BOOTFILE + __BOOTPATH top-level (antes del runtime)
        rmarker = "\nlocal R = {\n"
        ridx = hsrc.find(rmarker)
        assert ridx > 0, "marcador R no encontrado"
        hsrc = hsrc[:ridx] + boot_patch + hsrc[ridx:]
        # A) JSON + headers antes de START (json_code usa R; ambos top-level)
        anchor_start = "\nlocal START = R.clock()\n"
        assert anchor_start in hsrc, "START no encontrado"
        hsrc = hsrc.replace(anchor_start, "\n" + json_code + "\n" + hdr_block + anchor_start, 1)
        # B0) chunkname nameless: el stub llamo loadstring(a) SIN nombre -> las
        # funciones del VM reportan source "[string ...]" (debug.info "s");
        # "=Script" rompe el self-check de Luraph
        old_cn = 'local chunk, cerr = R.loadstring(__SOURCE, "=Script")'
        assert old_cn in hsrc, "chunkname anchor"
        hsrc = hsrc.replace(old_cn, 'local chunk, cerr = R.loadstring(__SOURCE)', 1)
        # B) hook JSONDecode/JSONEncode en onCall
        hsrc = hsrc.replace(falsy_anchor.group(0), hook_block + falsy_anchor.group(0), 1)
        # C) readfile/isfile del cache del init (fiel al device y al mitm 4e/4g)
        assert old_readfile in hsrc, "readfile anchor"
        hsrc = hsrc.replace(old_readfile, new_readfile, 1)
        assert old_isfile in hsrc, "isfile anchor"
        hsrc = hsrc.replace(old_isfile, new_isfile, 1)
        # D) delivery con headers reales
        assert old_label in hsrc and old_name in hsrc, "delivery anchors en harness"
        hsrc = hsrc.replace(old_label, new_label, 1)
        hsrc = hsrc.replace(old_name, new_name, 1)
        # E) SUBNIL traceback en el wrapLib (que funcion del VM llama sub(nil)?)
        wl_old = """                                return f(...)
                        end
                else
                        out[k] = f"""
        wl_new = """                                if R.select("#", ...) > 0 and (...) == nil then
                                        R.print("\\0SUBNIL " .. label .. " " .. tostring(debug.traceback("", 2)))
                                end
                                return f(...)
                        end
                else
                        out[k] = f"""
        assert wl_old in hsrc, "wrapLib anchor"
        hsrc = hsrc.replace(wl_old, wl_new, 1)
        return hsrc

    H.build_harness = patched_build

    orig_user_cfg = H.user_cfg

    def patched_user_cfg(args, cfg):
        cfg = orig_user_cfg(args, cfg)
        cfg["http_responses"] = list(http_responses)
        cfg["prelude"] = prelude
        cfg["plugin_rt"] = PLUGIN_RT
        cfg["max_block"] = 100000000
        cfg["max_stmts"] = 50000000
        cfg["ptrace"] = True
        cfg["gsub_dump"] = True
        return cfg

    H.user_cfg = patched_user_cfg

    sys.argv = [
        "deob.py", SAMPLES + "/luarmor_stub_mitm.lua",
        "--obfuscator", "luraph_v14",
        "--executor", "Delta",
        "--no-pypy",
        "--timeout", "520",
        "--budget", "420",
        "--raw", SAMPLES + "/output/obf_4_v14.raw.txt",
        "-o", SAMPLES + "/output/obf_4_v14.deobf.luau",
    ]
    # ---- bisect: guards INJECT MINIMAL (vmc-style, como el harness que PASO) ----
    from obfuscators.luraph_v14 import guards as __g

    def inject_minimal(source, vm_cap=250_000_000, plain_cap=50_000_000, spin_seconds=0):
        mod = 50_000_000
        n = source.count("while true do")
        head = "while true do __VMC+=1;if __VMC%" + str(mod) + "==0 then print('[VM] '..__VMC..' steps') end;"
        patched = "local __VMC=0\n" + source.replace("while true do", head)
        print("[*] guards MINIMAL (vmc-style): %d loops" % n, file=sys.stderr)
        return patched, n, 0

    __g.inject = inject_minimal
    import deob  # noqa: E402
    deob.main()


if __name__ == "__main__":
    main()
