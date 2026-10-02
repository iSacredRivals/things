# tools/ — Herramientas reutilizables (DevAurora Code)

Herramientas de los flujos especiales del sistema. El motor (`../deobf/`),
el bypass (`../luarmor_bypass/`) y los grabadores (`grabadores/`) son
**portables** (rutas relativas al paquete, listos para usar). El resto de
esta carpeta conserva algunas rutas absolutas del entorno de desarrollo
originales (`/home/z/my-project/...`): son material de referencia probado
en combate — copia el driver que necesites y ajusta la ruta de entrada.

## Carpetas

| Carpeta | Contenido |
|---|---|
| `deep_drivers/` | Drivers de cadenas completas: `run_dump5_deep.py` (hermanos stage-1 con --no-flat-env/--hide/--cfg), `run_herm_loader.py` (obf_3 363KB), `run_obf3_v15.py`, `herm_exp.py` (experimentos de env-check), `run_herm_v3..v5` (iteraciones del loader) |
| `p2d/` | Path2D: `p2d_verify.py` (verificación bit-exacta del modelo), `p2d_validate.py`, `make_p2d_recorder.py` + `parse_p2d_paste.py` (roundtrip grabador→cache), `perturb_p2d.py`/`perturb_v148.py` (experimentos de sensibilidad de stage key) |
| `analisis_vm/` | Análisis estático de VMs: `analyze_loops.py` (clasifica dispatchers), `parse_dispatcher.py` (con `../data/v148_opcodes_full.json`), `extract_chunks.py`/`extract_index.py`, `decode_herm_lph.py`, `inject_loopguards.py` |
| `replay/` | Replay de cadenas: `replay_loader.py`, `replay_qo_chain.py`, `replay_wrapper.py` |
| `v148/` | Suite Luraph v14.8 (cokeboys): modelos `vmpc_*.py/.luau`, `bare_v148.luau`, P2D real del device (`cokeboys_raw_realp2d.txt`) |
| `infra/` | `build_luau_full.sh` (recompila binarios Luau 0.739 + parche), `daemonize.py` (procesos persistentes doble-fork), `gofile_get.py`/`upload_grabador.py` (publicar grabadores), `bot_up.sh`/`bot_watchdog.sh` (bot Discord, opcional) |
| `data/` | `luaprot.json`, `luraph_macros.json` (macros oficiales LPH v15), `v148_opcodes_full.json` |
| `grabadores/` | **Listos para el usuario**: `p2d_recorder.luau`, `p2d_recorder_v148.luau`, `grabador_luraph.luau`, `hermanos_env_grabador.lua`, `hermanos_loader_p2d.lua`, `cokeboys_counter_probe.lua` + `LEEME_GRABADOR.txt` |
| `tests/` | Tests y probes de motor |

## Uso típico

```bash
# 1) cadena Luraph v14.5 con env-check (hermanos):
cd <raíz del paquete>
python tools/deep_drivers/run_dump5_deep.py samples/hermanos_v145.lua --no-flat-env --cfg executor=Delta

# 2) roundtrip P2D: el user corre el grabador → pega ==P2D==... →
python tools/p2d/parse_p2d_paste.py paste.txt samples/cokeboys_v148.path2d
# (la cache .path2d junto al input se aplica sola en la siguiente corrida)

# 3) verificación del modelo P2D offline:
python tools/p2d/p2d_verify.py
```

Los drivers que referencian `v148_suite/datasets/...` necesitan ese dataset
(no incluido); los modelos de `v148/` funcionan con lo incluido.
