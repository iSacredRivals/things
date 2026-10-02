# GUIA LUAARMOR — Bypass completo de cadenas LuaArmor (DevAurora Code)

## Qué rompe este bypass

La cadena LuaArmor típica:

```
loadstring(game:HttpGet("https://api.luarmor.net/files/v3/loaders/<ID>.lua"))()
                                            + key del usuario
stub (1.2KB, tokens de sesión frescos)
  └─> bootstrapper v4 (cdn.luarmor.net/v4_init_*.lua, 764KB)   ← UNIVERSAL
        └─> auth: POST con key + HWID  → challenge (722B, header Kkr)
              └─> chunk cifrado (425KB)  → decodifica el LOADER
                    └─> loader VM (Luraph v14.5, gate Path2D)
                          └─> PAYLOAD (la lógica real, Luraph v15 dentro)
```

**Hallazgo clave (verificado MD5):** el bootstrapper v4 descargado con el
User-Agent `Roblox/WinInet` es **idéntico entre todos los scripts LuaArmor**
(`v4_init.lua` incluido aquí). Con UA normal el CDN sirve un stub "not
supported". Lo único que cambia por script es el `STUB_URL` y la `KEY`.

## Qué contiene esta carpeta

| Archivo | Rol |
|---|---|
| `v4_init.lua` | Bootstrapper universal cacheado (el que sirve el CDN con UA `Roblox/WinInet`) |
| `loader.lua` | Stub v3 de ejemplo (el del script de la Task 68) |
| `scripts/make_mitm2.py` | **Constructor del harness MITM**: descarga stub fresco, parchea el path de descarga simulado (`ldrupd8m=a`, `a(b)`), embebe el bootstrapper, parchea contadores VMC y genera `mitm/mitm_harness.luau` |
| `scripts/launch_mitm2.py` | Lanza harness + driver **persistentes** (`start_new_session=True` — sobreviven al cleanup de la sesión de la herramienta) |
| `scripts/mitm_driver2.py` | Driver: atiende las requests `\0MITM <N> <URL>` del harness reenviándolas a los servers reales y escribiendo `mitm/resp_N.luau` |
| `scripts/extract_chunks2.py` | Extrae los chunks del log `mitm_harness.log` |
| `mitm/` | Estado de la sesión viva: log del harness, requests, respuestas, PIDs |

## Paso a paso (script LuaArmor nuevo)

1. **Editar `scripts/make_mitm2.py`** — solo dos constantes:

```python
KEY = "<key del usuario>"                 # p.ej. uheDAutILiYSgLDdOGYOZLEghHghjvqA
STUB_URL = "https://api.luarmor.net/files/v3/loaders/<ID>.lua"
```

2. **Lanzar** (regenera stub fresco = tokens nuevos, limpia resp_* y arranca):

```bash
cd luarmor_bypass
python3 scripts/launch_mitm2.py
```

3. **Observar el protocolo** en `mitm/driver_console.log`:
   - REQ#1 `d=_bsdata0[7] + b=<104hex>` — computado por el VM con la KEY →
     el server contesta el challenge (HTTP 200, 722B + header `Kkr`).
     Si la key es válida y el HWID fake pasa, sigue.
   - REQ#2 `d=challenge` → HTTP 200, chunk grande (~425KB).
   - `MITMDONE x2` → el VM consumió ambas respuestas.
   - L2DSWAP dispara (~60s, `#src>200000`): el VM loadstring'a el LOADER.

4. **Esperar el decode** (CPU-bound, minutos en máquinas lentas; >13 min con
   2 núcleos). El loader decodifica su VM interna y escupe el payload.

5. **Extraer** el payload del log:

```bash
python3 scripts/extract_chunks2.py
```

6. **Desofuscar el payload** con el motor principal (ver `../INICIO_RAPIDO.md`):

```bash
cd ..
python deobf/deob.py <payload_extraido.lua>
```

## Notas de combate (lo aprendido rompiendo QO + este)

- El **HWID fake es aceptado** por el server (probado con 2 scripts distintos);
  no hace falta el HWID real del usuario, solo la key válida.
- El stub debe bajarse **fresco** cada corrida: sus tokens de sesión son de
  un solo uso; `launch_mitm2.py` lo regenera solo.
- El bootstrapper cacheado evita depender del CDN… pero si `v4_init.lua`
  caduca, bajarlo de nuevo con UA `Roblox/WinInet`:

```bash
curl -A "Roblox/WinInet" "https://cdn.luarmor.net/v4_init_sephal.lua" -o v4_init.lua
```
- El parche L2DSWAP es robusto: trigger `#src>200000` y NO contener
  "Luarmor V4 bootstrapper" (cubre loaders de tamaño distinto al de QO).
- Si el loader VM muere en `table.create(<negativo>)`: es el gate Path2D →
  grabar respuestas reales del device con `tools/grabadores/` y aplicarlas
  (el harness ya trae P2D cacheados de QO como referencia).
- Firmar todo resultado: `-- By DevAurora Code`.
