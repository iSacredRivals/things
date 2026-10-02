# INICIO RAPIDO — AURORA DEOB SYSTEM (DevAurora Code)

## 1. Autotest (30 s)

```bash
cd AURORA_DEOB_SYSTEM
python deobf/deob.py samples/001_vm_like_dispatch-obfuscated.lua --detect
python deobf/deob.py samples/001_vm_like_dispatch-obfuscated.lua
head -3 samples/output/001_vm_like_dispatch-obfuscated.lua
#   -- By DevAurora Code
#   -- Detected obfuscation: Luraph v15
```

## 2. Desofuscar un script cualquiera

```bash
python deobf/deob.py /ruta/al/script.lua
# resultado → /ruta/al/output/script.lua
```

Flags que más se usan:

```bash
--detect                 # solo identificar la protección
--debug                  # guarda .protos.json / .devirt.luau / harness
--raw crudo.txt          # trace crudo del runtime
--executor Delta         # emulate Delta como executor
--cfg http_responses=@json:pares.json   # replay HTTP con cuerpos reales
```

## 3. Cadena LuaArmor (loadstring HttpGet api.luarmor.net)

→ leer `luarmor_bypass/GUIA_LUARMOR.md` y seguir el paso a paso.

## 4. Script que muere en table.create(negativo) / spin / exit silencioso

→ gate de device (Path2D). Correr el grabador `tools/grabadores/` en el
executor real, pegar el bloque `==P2D==`, convertir con
`tools/p2d/parse_p2d_paste.py` y re-ejecutar el motor.

## 5. Para ponerle una IA encima

→ entregar `GUIA_PARA_IA.md` + este zip a la IA. Documentación profunda:
`CLAUDE.md`.
