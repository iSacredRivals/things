# AURORA DEOB SYSTEM — Sistema completo de desofuscación de scripts Roblox

**Firma: DevAurora Code** — todo resultado generado por los motores VM de este
sistema lleva la cabecera `-- By DevAurora Code`.

Este paquete contiene **todo** el sistema de desofuscación construido y
validado en combate: el motor de desofuscación dinámica (Luraph v15, v14,
IronBrew1, genérico), el **bypass completo de cadenas LuaArmor** (MITM con
replay de auth), los drivers profundos por proyecto (QO, hermanos-hub,
cokeboys), los grabadores de dispositivo (Path2D / entorno) y todo el corpus
de muestras y datos grabados.

---

## Mapa del paquete

| Carpeta | Qué es | Uso principal |
|---|---|---|
| `deobf/` | **El motor** (Python puro, cero dependencias pip) + binarios Luau estáticos | `python deobf/deob.py <script.lua>` |
| `samples/` | Corpus de scripts protegidos reales (Luraph v14.5/v14.8/v15, Luarmor, chains QO/hermanos) + **caches P2D grabadas del device real** (`.path2d`, `hermanos_env_real.txt`) | Entradas de prueba / comparación |
| `luarmor_bypass/` | **Bypass LuaArmor**: MITM de la cadena de autenticación (stub → v4_init → challenge → chunks → loader) | Romper `loadstring(HttpGet("api.luarmor.net/..."))` |
| `aurora_qo/` | Proyecto QuantumOnyx/Blox Fruits completo: drivers MITM, cadena extraída, P2D del device real, payloads desofuscados | Referencia de una cadena rota end-to-end |
| `tools/` | Herramientas reutilizables: deep-drivers, P2D, análisis VM, replay, infra, grabadores | Piezas de los flujos especiales |
| `docs raíz` | `CLAUDE.md` (doc profunda del motor, pensada para IA), `LURAPH.md`, `LURAPH_V14.md`, `IRONBREW1.md`, `README_DEOB.txt` | Documentación técnica |

## Requisitos

- Linux x64 con Python 3.8+ (el motor usa **solo stdlib**, nada que instalar)
- Los binarios `deobf/bin/luau`, `luau-ast`, `luau-compile` ya vienen compilados
  y con permiso de ejecución (Luau 0.739 parcheado)
- Para recompilar los binarios: `tools/infra/build_luau_full.sh` (fuente no
  incluida por peso; el script la descarga)

## Inicio en 30 segundos

```bash
cd AURORA_DEOB_SYSTEM
python deobf/deob.py samples/001_vm_like_dispatch-obfuscated.lua
# → samples/output/001_vm_like_dispatch-obfuscated.lua
#   (cabecera: "-- By DevAurora Code")
```

Detección de obfuscador:

```bash
python deobf/deob.py script.lua --detect
# → luraph_v15  1.00  Luraph v15
```

Desofuscación de una cadena LuaArmor completa: ver `luarmor_bypass/GUIA_LUARMOR.md`.

## Firma DevAurora Code

Dos puntos del motor escriben la firma; todo resultado pasa por uno de ellos:

- `deobf/obfuscators/base.py` → `credit_header()` — salida devirtualizada
- `deobf/traceout.py` → `header()` — salida de trace dinámico

Ambos ya están configurados como `-- By DevAurora Code`. Si algún día se
recompila o bifurca el motor, verificar que esas dos líneas sigan firmadas.

## Para usar con una IA

Entrega a la IA el archivo **`GUIA_PARA_IA.md`** junto con este zip: es la
instrucción de sistema completa (árbol de decisión por protección, comandos
exactos, flujos especiales y límites conocidos). El motor además trae
`CLAUDE.md`, la documentación profunda de su arquitectura interna.
