#!/usr/bin/env python3
"""Deob de obf_4 (bootstrapper Luarmor v4, Luraph v14.8) — REPLAY v3 = v2 + SPIES.

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

STUB_ORIG = open(QODUMP + "/qodump_1790732004_01_api.luarmor.net_files_v4_loaders_0ae9fe4cf963e",
                 encoding="latin-1").read()
BOOT_SRC = open(SAMPLES + "/obf_4.lua", encoding="latin-1").read()


def extract_bsdata(src):
    m = re.search(r"_bsdata0=\{(.*?)\};", src, re.S)
    assert m, "_bsdata0 no encontrado en el stub"
    return m.group(1)


def body_of(n):
    src = open(f"{MITM}/resp_{n}.luau", encoding="latin-1").read()
    i = src.find("__body = [")
    j = i + len("__body = ")
    k = j
    while src[k] == "=":
        k += 1
    body_start = k + 1
    closer = "]" + src[j:k] + "]"
    body_end = src.find(closer, body_start)
    return src[body_start:body_end]


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


PLUGIN_RT = r'''
-- ================== SPIES (v3) ==================
local arg = ...
local E, R, CFG = arg.E, arg.R, arg.CFG
local __SPYN = 0
local function spy(tag, msg)
        __SPYN += 1
        if __SPYN <= 4000 then R.print("\0SPY " .. tag .. " " .. tostring(msg)) end
end

-- buffer.create / fromstring
local realbuf = E.buffer
local nb = {}
for k, v in pairs(realbuf) do nb[k] = v end
local nbc, nbfs = 0, 0
nb.create = function(n)
        nbc += 1
        if nbc <= 300 or (type(n) == "number" and (n < 0 or n > 1000000000)) then
                spy("BC", "#" .. nbc .. " create(" .. tostring(n) .. ")")
        end
        return realbuf.create(n)
end
nb.fromstring = function(s)
        nbfs += 1
        if nbfs <= 300 then
                local hex = ""
                if type(s) == "string" and #s > 0 then
                        for i = 1, math.min(10, #s) do hex = hex .. string.format("%02x", string.byte(s, i)) end
                end
                spy("BFS", "#" .. nbfs .. " fromstring len=" .. tostring(type(s) == "string" and #s or -1) .. " " .. hex)
        end
        return realbuf.fromstring(s)
end
E.buffer = nb

-- os.time / clock / date (campos RAW: los VM usan rawget)
local realos = E.os
local nos = {}
for k, v in pairs(realos) do
        local cnt = 0
        nos[k] = function(...)
                cnt += 1
                if cnt <= 80 then spy("OS", k .. " -> " .. tostring((...))) end
                return v(...)
        end
end
E.os = nos

-- request / http_request / http.request
local function wrapreq(fname)
        local f = E[fname]
        if type(f) == "function" then
                E[fname] = function(...)
                        local o = ...
                        local u = type(o) == "table" and tostring(o.Url) or tostring(o)
                        spy("REQ", fname .. " " .. string.sub(u, 1, 140))
                        return f(...)
                end
        end
end
wrapreq("request")
wrapreq("http_request")
if type(E.http) == "table" then
        local hf = E.http.request
        E.http = { request = function(...)
                local o = ...
                local u = type(o) == "table" and tostring(o.Url) or ""
                spy("REQ", "http.request " .. string.sub(u, 1, 140))
                return hf(...)
        end }
end

-- writefile
local wf = E.writefile
if type(wf) == "function" then
        E.writefile = function(p, c)
                spy("WF", tostring(p) .. " len=" .. tostring(type(c) == "string" and #c or -1))
                return wf(p, c)
        end
end

-- Random.new (semillas)
local rn = E.Random and E.Random.new
if type(rn) == "function" then
        E.Random = { new = function(...)
                spy("RND", "new n=" .. tostring(select("#", ...)) .. " seed=" .. tostring((...)))
                return rn(...)
        end }
end

-- syn reconstruida con las funciones envueltas
local synv = { request = E.request, http_request = E.http_request }
for _, k in ipairs({ "writefile", "readfile", "isfile", "isfolder", "appendfile",
                "listfiles", "delfile", "delfolder", "makefolder", "queue_on_teleport",
                "queueonteleport", "setclipboard", "toclipboard", "getgenv",
                "getexecutorname", "identifyexecutor", "fireclickdetector" }) do
        if E[k] ~= nil then synv[k] = E[k] end
end
synv.protect_gui = function(gui) return gui end
rawset(E, "syn", synv)
spy("INIT", "spies instalados")
'''


def main():
    bsdata = extract_bsdata(STUB_ORIG)
    toks = re.findall(r'"([0-9a-f]{16,})"', bsdata)
    d1 = toks[-1][:16]
    assert d1 == "929c04812ef86ea4", f"d1 inesperado: {d1}"

    bodies = [body_of(n) for n in (1, 2, 3, 4)]
    hdrs = [headers_of(n) for n in (1, 2, 3, 4)]
    d2, d3, d4 = "3f1863b183c7fee0", "4965dbdba942502b", "fc92fbc3419fa60d"

    http_responses = [d1, bodies[0], d2, bodies[1], d3, bodies[2], d4, bodies[3]]
    print(f"[*] v3 spies + patches; REQ1~{d1} REQ2~{d2} REQ3~{d3} REQ4~{d4}", file=sys.stderr)

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
        "rawset(env,'fireserver',function(...) end)"
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

    # readfile -> nil
    old_readfile = 'E.readfile = function(p) return callP("readfile(" .. fmt(p) .. ")", "contents", "string") end'
    new_readfile = 'E.readfile = function(p) comment("readfile(" .. fmt(p) .. ") -> nil"); return nil end'

    # onCall JSON hook: ancla = la linea de comentario falsy
    falsy_anchor = re.search(r'\n([ \t]*)-- --cfg falsy=a,b: calls of these names return false \(explore other branches\)', envlog_src)
    assert falsy_anchor, "ancla falsy no encontrada"
    hook_block = "\n" + json_hook

    orig_build = H.build_harness

    def patched_build(source, cfg, chunks=None):
        hsrc = orig_build(source, cfg, chunks)
        # A) JSON + headers antes de START (json_code usa R; ambos top-level)
        anchor_start = "\nlocal START = R.clock()\n"
        assert anchor_start in hsrc, "START no encontrado"
        hsrc = hsrc.replace(anchor_start, "\n" + json_code + "\n" + hdr_block + anchor_start, 1)
        # B) hook JSONDecode/JSONEncode en onCall
        hsrc = hsrc.replace(falsy_anchor.group(0), hook_block + falsy_anchor.group(0), 1)
        # C) readfile -> nil
        assert old_readfile in hsrc, "readfile anchor"
        hsrc = hsrc.replace(old_readfile, new_readfile, 1)
        # D) delivery con headers reales
        assert old_label in hsrc and old_name in hsrc, "delivery anchors en harness"
        hsrc = hsrc.replace(old_label, new_label, 1)
        hsrc = hsrc.replace(old_name, new_name, 1)
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
        "--raw", SAMPLES + "/output/obf_4_v3.raw.txt",
        "-o", SAMPLES + "/output/obf_4_v3.deobf.luau",
    ]
    import deob  # noqa: E402
    deob.main()


if __name__ == "__main__":
    main()
