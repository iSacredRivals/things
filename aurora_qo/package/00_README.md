# DevAurora-Scripts / Luarmor_Obfuscated.zip — Desofuscación completa

**Objetivo**: el zip `Luarmor_Obfuscated.zip` del repo `AteneaNyx/DevAurora-Scripts`.
**Resultado**: la cadena se desmonta por completo; el payload real (Blox Fruits)
queda desofuscado (14.170 líneas legibles, compila limpio) y además resulta ser
**público en el GitHub del propio desarrollador**.

> **Free vs Premium**: el script del GitHub es la **v.Freemium** (keyless, con
> AutoFarm/ESP/aimbot/server-hop — prácticamente todo). La variante Premium NO
> está en el zip: la API la entrega como `authData.script` tras validar una key
> de pago (`POST api.quantumonyx.cc/api/v1/authenticate` con key/hwid/executor),
> o vía el loader Luarmor si la VPS cae. Sin key válida no hay forma de
> descargarla del servidor; lo más cercano disponible es este Freemium completo.

---

## 1. Qué había en el zip (7 archivos)

| Archivo | Qué es realmente | Estado |
|---|---|---|
| `obf_1.lua` (37 KB) | Keysystem UI de **Quantum Onyx** (por flazhy) — sin ofuscar | ✅ legible tal cual |
| `obf_1_namecall.lua` (1,2 KB) | Stub bootstrap Luarmor V4 (`_bsdata0`), variante | ✅ legible tal cual |
| `obf_1_namecall_http.lua` | Copia de obf_1 | ✅ legible |
| `obf_2.lua` (6 KB) | **Librería key-check de Luarmor** (ofuscación ligera: cadenas partidas + comentarios) | ✅ limpia estáticamente |
| `obf_3.lua` (1,2 KB) | Stub bootstrap Luarmor V4 (`_bsdata0`) | ✅ legible tal cual |
| `obf_4.lua` (764 KB) | **Bootstrapper V4 de Luarmor** — VM "superflow" (familia Luraph v14.8) con `superflow_bytecode` embebido | ⚠️ trace parcial (ver §4) |
| `obf_5.lua` (980 KB) | **Loader de whitelist Luarmor** para el script `0ae9fe4cf963e3a13d25eed0e2ce5940` (Quantum Onyx / bloxfruits, build "0056") — Luraph v14.8 | ⚠️ trace parcial: 165 stmts + 307 strings (ver §4) |

## 2. La cadena de carga (reconstruida)

```
usuario ejecuta el keysystem (obf_1, público en GitHub flazhy/QuantumOnyx)
   │  anuncios de key: ads.luarmor.net/get_key?for=Quantum_Onyx_*
   ▼
obf_1 valida la key contra api.quantumonyx.cc (fallback 165.232.169.51:22527)
   │  usa la librería key-check de Luarmor (obf_2):
   │    1) GET https://sdkapi-public.luarmor.net/sync        → lista de nodos + reloj del server
   │    2) GET {nodo}/check_key?key=K&script_id=G            → headers anti-tamper:
   │       "clienttime" = hora ajustada, "catcat128" = hash custom 128-bit de (key..script_id..time)
   │    3) hash de despacho: las funciones se piden por NOMBRE que se hashea y se compara
   │       (30F75B19…=check_key, 2BCEA36E…=invalidate, 75624F56…=load script)
   ▼
stub _bsdata0 (obf_3): mira el cache static_content_170926/init-f07dbcbe19a-sephal.lua
   │  si no está → GET https://cdn.luarmor.net/v4_init_sephal.lua   (= obf_4)
   ▼
bootstrapper V4 (obf_4, VM superflow): gestiona el cache cifrado de Luarmor
   │  (fetch + update + encrypt + decrypt de los scripts servidos)
   ▼
loader de whitelist (obf_5, Luraph v14.8): fingerprinting del entorno
   │  (GetTutorialState x80, país, DevConsole anti-debug, identifyexecutor,
   │   globals script_key/syn/FLUXUS_LOADED) + banner "Luarmor - Lua whitelist service"
   ▼
y el SCRIPT REAL no viene de Luarmor: el propio obf_1 lo carga del GitHub
PÚBLICO del desarrollador:
   https://raw.githubusercontent.com/flazhy/QuantumOnyx/refs/heads/main/Games/BloxFruits.lua
```

**Conclusión clave**: Luarmor aquí es solo la capa de whitelist/anti-tamper.
El contenido "protegido" (el cheat) está servido en un repo público.

## 3. Payloads desofuscados (Luraph v15 → devirtualizado)

El pipeline v15 (devirt de 3 rondas) levantó el bytecode de la VM a Luau legible:

- **`02_payloads_desofuscados/05_BloxFruits_DEOBFUSCADO.lua`** — 14.170 líneas, 746 funciones
  caminadas, 4.702 constantes decodificadas. Contenido: espera de carga y selección de
  equipo (Pirates/Marines), módulos CoreSetup / CombatHooks / RuntimeServices /
  LoadLibrary, AutoFarm (Level, Pirate Raid), ESP (Player/Island/DevilFruit/Chest/
  Berries/RealFruit), aimbot, server-hop/AFK, notificaciones "Quantum Fully Loaded" y el
  anti-skid final `warn("stop skidding - flazhy")`. Compila limpio (luau-compile exit 0).
- **`02_payloads_desofuscados/06_Weebo_DEOBFUSCADO.lua`** — 1.089 líneas, desofuscación
  COMPLETA (run "finished", 51 funciones, 487 constantes). Módulo de preload con
  detección de mapa (Sea1/2/3) y **secretos de API expuestos**:
  - `https://api.quantumonyx.cc`
  - `secretkey-wqe231weqweqweqweqweqwe` (clave interna del backend)
  - `QnTmOnyX`
- `07_CutTrees_sin_desof.lua` — usa OTRO ofuscador (string-array, no Luraph): el trace
  genérico y el plugin ironbrew1 no lo cubren. Script trivial (cortar árboles), prioridad baja.

Fuentes adicionales del repo (públicas), incluidas en el paquete:

- `08_Data.lua` — **plano** (tablas de quests/enemigos/islas de las 3 mares).
- `09_Visuals_original_ofuscado.lua` (189 KB) — Prometheus-multi-capa. Su capa 1
  descifra con **semillas leídas de globals canario** (`JmLpWBY56TXTs`,
  `RrlLEq6Z0n7HVw`, `Q4SUQ8GdKTOi5O`...): valores erróneos → loop de cómputo
  infinito o castigo `stop tampering - stop skidding`. Mismo patrón de stage-key
  que Luraph v14.8. Interceptado con un harness luau (loadstring hook), pero el
  decode necesita el valor real de la semilla.
- `10_testers_UIlib_original_ofuscado.lua` (435 KB) — la UI library ("Quantum").
  Su **capa 2 (531 KB) sí fue interceptada y capturada** (`11_testers_capa2_interceptada.lua`):
  se extrajo vía hook de loadstring en luau crudo; contiene la VM (dispatch
  w==2..5) y el anti-tamper "(Quantum Error Log:)" con `error(...,0)`.

## 4. Lo que quedó parcial: los dos VM de Luarmor

`obf_4` (bootstrapper) y `obf_5` (loader) son VM de la familia Luraph v14.8 con el mismo
mecanismo de bloqueo ya documentado para Cokeboys v14.8: la clave de fase se deriva de
respuestas del engine (Path2D: GetLength/GetPositionOnCurve/GetTangentOnCurve + variantes
ArcLength — las 12/13 consultas aparecen en las strings de obf_5) y el VM ejecuta un
cómputo bignum estilo RSA (>2.000M de iteraciones de dispatcher) antes de revelar nada.

Del trace de `obf_5` (165 statements + 307 strings) se recuperó igualmente su lógica:
banner, fingerprinting GetTutorialState("nil  nil  N"), gate de país
(GetCountryRegionForPlayerAsync), anti-debug del DevConsole (lectura de
CoreGui.DevConsoleMaster…ClientLog), y los globals de debug que Lee lee:
`LUARMOR_SkipAntidebugDevMode`, `LUARMOR_AllowKeyCheckSkip`, `devsignature_sig`,
`ce_like_loadstring_fn`, `USE_NON_SSL_NODE`, `l_fastload_enabled` (interruptores internos
de Luarmor — `LUARMOR_AllowKeyCheckSkip` en un entorno controlado saltaría la validación).

Para el objetivo de este zip no importa: el payload no depende de esos VM.

## 5. Contenido del paquete

```
01_fuentes_limpias/           4 archivos tal cual + librería limpiada
02_payloads_desofuscados/     BloxFruits (14.170 líneas) + Weebo (completo) + CutTrees raw
03_capa_luarmor/              loader original + trace + 307 strings + bootstrapper trace
```

Cómo se hizo: pipeline propio de desofuscación (detector Luraph v14/v15 → trace dinámico
con guards → devirtualizador de 3 rondas → render con nombres inferidos) sobre el payload
v15; limpieza estática AST (plegado de cadenas partidas) para la librería key-check.
