"""Experimento: ¿qué respuestas Path2D alimentan el table.create(-442)?

Inyecta en __P2D del harness una respuesta perturbada por vez y observa
si los tamaños malos de table.create cambian (baseline: -442, -62920, -188760).
Si una respuesta perturbada cambia los tamaños => esa respuesta está en la key.
"""
import re
import subprocess
import sys

BASE = "samples/output/exp2.luau"
LUAU = "deobf/bin/luau"
BASELINE = ("-442", "-62920", "-188760")

# respuestas del modelo (de debug_run1.txt, tag 'model')
ANSWERS = {
    "GetLength": "n:138.62068176269531",
    "GetPositionOnCurve|0.2142857164144516": "u:-0.011674169450998306,0,0.096768006682395935,0",
    "GetPositionOnCurve|0.55555558204650879": "u:-0.010096256621181965,0,0.28553315997123718,0",
    "GetPositionOnCurve|0.92857140302658081": "u:0.17952263355255127,0,0.28941076993942261,0",
    "GetTangentOnCurve|0.1666666716337204": "v:-24.375,120.25",
    "GetTangentOnCurve|0.80000001192092896": "v:41.000003814697266,13.550003051757812",
    "GetTangentOnCurve|0.625": "v:7.75,-23.375",
    "GetPositionOnCurveArcLength|0.625": "u:-0.029926817864179611,0,0.29498803615570068,0",
    "GetPositionOnCurveArcLength|0.66666668653488159": "u:-0.0017578528495505452,0,0.30205968022346497,0",
    "GetTangentOnCurveArcLength|0.5": "v:-3.8972949981689453,118.71534729003906",
    "GetTangentOnCurveArcLength|0.5625": "v:4.3236103057861328,96.916694641113281",
}


def perturb(val):
    """Perturba el primer número de la respuesta de forma visible."""
    kind, rest = val.split(":", 1)
    nums = rest.split(",")
    nums[0] = "%.17g" % (float(nums[0]) + 1.5)
    return kind + ":" + ",".join(nums)


def run_with(harness_path, injections, tag):
    text = open(BASE, encoding="latin-1").read()
    entries = "".join("[%s] = %s,\n" % (lua_str(k), lua_str(v)) for k, v in injections.items())
    old = "local __P2D = {\n}"
    # el harness tiene "local __P2D = {" seguido de "}" con newline
    m = re.search(r"local __P2D = \{\s*\}", text)
    assert m, "no se encontró __P2D vacío"
    text = text[:m.start()] + "local __P2D = {\n" + entries + "}" + text[m.end():]
    open(harness_path, "w", encoding="latin-1").write(text)
    try:
        r = subprocess.run([LUAU, harness_path], capture_output=True, timeout=45)
        out = r.stdout.decode("latin-1")
    except subprocess.TimeoutExpired:
        print("[%-4s] *** TIMEOUT (cuelga: bucle VM infinito) => ESTA EN LA KEY ***" % tag)
        return ["TIMEOUT"]
    bads = re.findall(r"\x00CREATEBAD size=([-\d.]+)", out)
    status = re.findall(r"-- run status: (.*)", out)
    print("[%-4s] bads=%s status=%s" % (tag, bads or "NINGUNO", (status[0][:60] if status else "?")))
    return bads


def lua_str(s):
    return '"%s"' % s.replace("\\", "\\\\").replace('"', '\\"')


print("=== BASELINE (sin inyecciones) ===")
base = run_with("samples/output/pert_base.luau", {}, "base")
print()
print("=== PERTURBACIÓN INDIVIDUAL ===")
for key, val in ANSWERS.items():
    run_with("samples/output/pert_one.luau", {key: perturb(val)}, key[:22])
print()
print("=== TODAS PERTURBADAS ===")
run_with("samples/output/pert_all.luau",
         {k: perturb(v) for k, v in ANSWERS.items()}, "all")
