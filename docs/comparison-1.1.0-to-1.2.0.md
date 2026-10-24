# Comparison: Sharp Filter Selector 1.1.0 → 1.2.0

## Verified baseline

The previous published release is [1.1.0](https://github.com/N3ruk/Sharp-Filter-Selector/releases/tag/v1.1.0),
tagged at commit `7e95ec9`. Its downloaded ZIP and published SHA256 were checked:

```text
sharp-filter-selector-v1.1.0.zip
97997565f68d076e7f30ca3f12c80bf79dd928e0466ef6b900f56f5b1a0b01cb
```

The four runtime files in that ZIP match the 1.1.0 Git tag. This comparison is
against the actual public release, not an earlier locally patched candidate.

## Behavior and implementation

| Area | Published 1.1.0 | Release 1.2.0 |
| --- | --- | --- |
| Ubuntu/UGM QAM bridge | Server 0 authority; Sharp 2 → SGSR 5 when supported | Preserved; all 12 `_ubuntu*` methods are AST-identical |
| SteamOS QAM bridge | No continuous native-Sharp promotion | Separate SteamOS-only bridge, gated on active SGSR support |
| SteamOS Sharp selection | QAM can stay at FSR 2 despite SGSR-capable Gamescope | Native mode translates 2 → 5 and synchronizes sibling roots |
| Translation timing | No SteamOS native bridge | Poll interval 750 ms plus X11 response; not an atomic Gamescope patch |
| Linear/Nearest/Pixel | No new SteamOS SGSR bridge | Not promoted to SGSR when both overrides are off |
| Modern SteamOS scaler | Filter switches can write Auto | Filter switches preserve QAM's chosen scaler; siblings mirror server 0 |
| Modern SteamOS overrides | Legacy transition/enforcement machinery | NIS 3 / FSR 2 share the modern bridge and avoid competing legacy writes |
| Old SteamOS Gamescope | Validated LINEAR → NIS / legacy property path | Preserved for builds without SGSR |
| Restricted `/proc/PID/exe` | Capability probe can fail on file-capability Gamescope | SteamOS-only observed-absolute-argv ELF fallback, with ownership, timestamp and identity checks |
| Privileges / executable selection | Unprivileged plugin; active-process probe | Still unprivileged; no PATH fallback, Gamescope replacement or capability removal |
| Frontend availability | Failed initial restore can prevent periodic detection | Refresh starts before initialization and survives failed restoration |
| SGSR feedback to user | Native label depends on successful detection | Explicit SGSR status and bridge-state logging |
| FSR visibility / HDR | Fresh application HDR feedback; unknown fails open | Same policy; display HDR alone still does not hide FSR |
| Sharpening | Shared 0–5 FSR/NIS range | Same mapping and input validation |
| Automated suite | 5 Python tests | 41 Python + 7 frontend tests, including 90 selector/scaler/override cases |
| Release ZIP | Runtime, frontend source and portable installer/docs | Also includes tests, lockfile, packaging script, validation report and this comparison |

## What changed on disk

- `main.py`: SteamOS bridge, restricted-process capability detection,
  serialized modern override writes, recovery/shutdown handling and diagnostics.
- `src/index.tsx` / `dist/index.js`: explicit SGSR status and reliable refresh;
  the committed bundle is built from the checked-in frontend source.
- `package.json` / lockfile: version 1.2.0, test/typecheck commands and the
  missing development-only React Router types. Runtime dependency declarations
  are unchanged.
- Tests, packaging and documentation: regression coverage and reviewable
  validation/release evidence.
- The existing GitHub build/package workflow is retained unchanged. The full
  `npm test` and `npm run typecheck` checks were also run locally before release;
  they are not newly added steps in that existing GitHub workflow.
- `plugin.json`: unchanged, including flags. No root privilege is requested.
- No files in `N3ruk/Ubuntu-Gaming-Mode` or the system Gamescope installation
  are modified by this release.

## Validation and limits

The maintainer confirmed correct operation of the corrected plugin on
2026-10-24 and requested publication. The environment investigated was SteamOS
3.9.5 with Gamescope package `3.16.30.1-2`.

The permission failure was reproduced with the real Gamescope executable and
then retested through the installed Decky backend. The 48 automated tests and
build/package checks cover detailed compatibility behavior. The maintainer's
functional confirmation is not an independent GPU trace or a claim that all
HDR/scaler combinations were physically measured. See the
[validation report](validation-1.2.0.md) for the evidence boundary and retest list.

## Resumen en español

La 1.2.0 añade el puente que faltaba en SteamOS y corrige el bloqueo de detección
causado por los permisos de `/proc`. Por eso SGSR puede detectarse y FSR aparece
cuando corresponde. No cambia la ruta Ubuntu/UGM ni la política HDR de la 1.1.0,
no parchea Gamescope y no concede root al plugin. El mantenedor confirmó su
funcionamiento; la publicación incluye 48 pruebas automáticas y documentación
que distingue esa confirmación de las comprobaciones no realizadas en GPU.
