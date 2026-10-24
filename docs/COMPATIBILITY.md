# Compatibility / Compatibilidad

[English](#english) · [Español](#español) · [README](../README.md)

## English

### Supported paths

| Environment | Behavior |
| --- | --- |
| SteamOS with active SGSR-capable Gamescope | Dedicated QAM → SGSR bridge and modern NIS/FSR overrides |
| Older SteamOS Gamescope | Existing legacy FSR/NIS path and LINEAR → NIS transition |
| Ubuntu / UGM | Existing isolated backend and server-0 synchronization |
| No active Gamescope | No filter writes; SGSR status reports an unavailable session |

In native mode, Steam's Sharp selector `2` is promoted to SGSR `5` when supported.
NIS uses `3`, explicit FSR uses `2`; Linear `0`, Nearest `1` and Pixel `4` are not
promoted with both overrides off. Server 0 owns the QAM state; sibling roots follow
valid filter/scaler values. SGSR/HDR format fallback is performed by Gamescope.

SteamOS Gamescope may carry `cap_sys_nice`, preventing an unprivileged plugin from
reading `/proc/PID/exe`. The SteamOS fallback uses the absolute executable observed
in that process's argv only when it is an unchanged root-owned ELF, its directory
chain is non-writable and its metadata predates the process. Relative paths,
replacements and ambiguous identity fail closed. No PATH substitution, root plugin
permission or removal of Gamescope capabilities is involved.

### Changes from 1.1.0 to 1.2.0

| Area | 1.1.0 | 1.2.0 |
| --- | --- | --- |
| SteamOS native bridge | Missing | Sharp 2 → SGSR 5 on compatible running Gamescope |
| Restricted-process detection | Can fail with permission denied | Validated observed-executable fallback |
| Modern SteamOS scaler | Filter selection can reset Auto | Preserves QAM's selected scaler |
| Modern explicit overrides | Legacy enforcement machinery | One modern bridge, no competing legacy writes |
| Frontend | Initial failure can stop refresh | Persistent refresh and explicit SGSR status |
| Ubuntu / UGM | Validated route | Twelve `_ubuntu*` methods unchanged (AST comparison) |
| Application HDR and sharpness | Existing policy, shared 0–5 control | Preserved |
| Automated tests | 5 Python tests | 41 Python + 7 frontend tests |

### Validation

- SteamOS 3.9.5, Gamescope package `3.16.30.1-2`: the maintainer confirmed correct
  operation of the corrected plugin on **2026-10-24**.
- The permission failure was reproduced with a real `gamescope --help` process
  and the correction verified through the installed Decky backend.
- 48 automated tests cover selection, HDR visibility, recovery, permissions,
  shutdown and 90 filter/scaler/override combinations. Types/build/package checks pass.
- Historical Ubuntu validation: Gamescope 3.16.30, RTX 2060 and 4K HDR output.
  This was not repeated on the SteamOS machine.
- The maintainer's functional confirmation is not an independent GPU trace or
  a complete physical HDR/scaler test matrix. Real-game retests should cover
  native Sharp, Linear/Pixel, both overrides, scaling modes and HDR/SDR transitions.

The current repository cleanup changes documentation and packaging only. The
four runtime files remain identical to the original 1.2.0 release. Published tags
and older releases retain their historical source and package layouts.

## Español

### Compatibilidad

- **SteamOS moderno con SGSR:** puente Nitidez → SGSR y overrides modernos NIS/FSR.
- **SteamOS antiguo:** ruta legacy FSR/NIS y transición LINEAR → NIS conservadas.
- **Ubuntu/UGM:** backend aislado y sincronización desde servidor 0 conservados.
- **Sin Gamescope activo:** no se escriben filtros; el estado indica que falta sesión.

Con ambos overrides apagados, Nitidez `2` se convierte en SGSR `5` si hay soporte.
NIS utiliza `3`, FSR explícito `2`. Lineal, Nearest y Pixel no se convierten a SGSR.
El puente comprueba cada 750 ms más la respuesta X11; el servidor 0 mantiene la
autoridad del QAM. Gamescope conserva su fallback FSR para entrada HDR.

La 1.2.0 corrige la detección bloqueada por permisos de `/proc`: comprueba la ruta
absoluta observada del proceso con verificaciones de propiedad, permisos, fechas
e identidad. No elige otro Gamescope del PATH ni concede root al plugin.
También evita reiniciar el escalado QAM en SteamOS moderno y muestra el estado
SGSR explícitamente. La lógica HDR y la nitidez 0–5 se mantienen.

Se verificó que los 12 métodos `_ubuntu*` son idénticos a la 1.1.0 y la integración
UGM de referencia. El usuario confirmó funcionamiento en SteamOS el 24-10-2026.
Hay 48 pruebas automáticas y una matriz de 90 casos; no se atribuye una captura
GPU ni una prueba física completa HDR/escalado que no se haya realizado.

Esta reorganización solo cambia documentación y empaquetado. Los cuatro archivos
runtime siguen siendo los de la 1.2.0 validada. Los tags y releases anteriores
conservan su estructura histórica.
