# Sharp Filter Selector 1.2.0 validation

## Compatibility boundary

- Baseline: Sharp-Filter-Selector `7e95ec9` (1.1.0).
- UGM reference: `N3ruk/Ubuntu-Gaming-Mode`, bundled
  `integrations/decky/sharp-filter-selector/main.py`, read on 2026-10-24.
  SHA256 `9545747bef4dfefbe2101e6e5751ff744bd8e3a808bebcfc155b93db15c543bb`.
- All twelve `_ubuntu*` methods match both that UGM source and 1.1.0. No UGM
  repository files are modified. Existing frontend HDR gating is unchanged.
- Old SteamOS retains legacy selectors and the LINEAR → NIS transition.

## Environment evidence — not a rendering test

- SteamOS 3.9.5; package `gamescope 3.16.30.1-2`.
- `/usr/bin/gamescope --help` lists SGSR and Snapdragon Game Super Resolution.
- Upstream [filter enum](https://github.com/ValveSoftware/gamescope/blob/3.16.30.1/src/main.hpp)
  defines Linear 0, Nearest 1, FSR 2, NIS 3, Pixel 4, SGSR 5.
- Its [property handler](https://github.com/ValveSoftware/gamescope/blob/3.16.30.1/src/steamcompmgr.cpp)
  consumes the modern selector directly. Supporting SGSR does not itself make
  Steam's FSR selector 2 mean SGSR.
- Inspection occurred in Desktop Mode without active Gamescope/Xwayland.
  This does not prove SGSR was rendering during inspection.
- Stored NIS was enabled; the update preserves that preference.
- Installed through Decky's native update flow; the four runtime files match
  the verified 1.2.0 ZIP. Decky loads the backend/frontend without a plugin error.
  Initially NIS=true, FSR=false and sharpening=5 were preserved. The user later
  disabled both overrides for native SGSR; those subsequent choices were also
  preserved. An update never restores an earlier snapshot over new user choices.

## Automated checks

Run `npm ci`, `npm test`, `npm run typecheck`, `npm run build`, `npm run package`.

Release suite: **48 passing tests** (41 Python + 7 frontend), including the
permission-boundary regressions added after the initial candidate failed.

Actual backend tests use fake authenticated Xwayland roots; actual TSX runs in
a Decky/hooks harness. Coverage includes:

- Six selectors × five scalers × native/NIS/FSR modes (90 cases).
- Server-ID authority instead of display order; missing/ambiguous roots.
- Linear/Nearest/Pixel after SGSR; stable passes without unnecessary rewrites.
- Session disappearance/recovery, failed reads/writes, worker exceptions.
- Exclusive overrides, serialized API/bridge writes and shutdown draining the
  worker before returning, preventing late writes after unloading.
- Legacy SteamOS property transition; Ubuntu writes and QAM synchronization.
- Active-executable capability detection, binary fallback, absent-session cache.
- HDR reporting leaves selector 5 to Gamescope's native format fallback rules.
- FSR visibility for SDR/HDR/unknown, SDR on HDR output, failed refresh and
  saved-NIS restore failure before Gaming Mode becomes available.
- Full sharpening range, invalid inputs, TypeScript and Rollup checks.

These verify selection and compatibility logic, **not GPU image quality**.

## Follow-up: real SteamOS permission failure reproduced and fixed

The first candidate failed the user's Gaming Mode test: SGSR/FSR controls did
not appear and QAM remained FSR. The original automated suite did **not** cover
the real kernel permission boundary, so its passing result was insufficient.

`getcap /usr/bin/gamescope` reports `cap_sys_nice=eip`; Decky runs this plugin
as UID 1000. A controlled `/usr/bin/gamescope --help` process, held at a full
stdout pipe without starting a compositor, reproduced EACCES for both its
`/proc/PID/exe` and environment, although cmdline remained readable. The old
probe returned supportsSGSR=false and PermissionError for both help/version.

The corrected SteamOS-only fallback correlates the process's absolute argv ELF
with root ownership, a non-writable directory chain and metadata predating the
process. Identity is checked again after probing. It does not consult PATH or
run the plugin as root; Ubuntu keeps its original probing path.

Repeating the controlled test with the corrected source returned:
`supportsSGSR=true`, version `3.16.30.1`, executable `/usr/bin/gamescope`,
evidence `process-argv-help`. This controlled reproduction proves the
permission-detection fix, **not** live QAM promotion or a running SGSR shader.

Additional regressions cover restricted proc access, changed/replaced binaries,
relative argv, writable/non-root paths, non-ELF targets, Ubuntu isolation and
an explicit SGSR status line when FSR controls are hidden.

## Maintainer's Gaming confirmation — 2026-10-24

After installing the corrected candidate and being asked to test the Gaming
workflow with native Sharp/SGSR, the maintainer reported that it now works
correctly and authorized documenting the result and publishing 1.2.0.

Record this as **maintainer-confirmed functional operation** on the investigated
SteamOS 3.9.5 / Gamescope 3.16.30.1 system. The report did not enumerate every
toggle, scaler, input colorspace or game. No independent live GPU/shader trace
or full physical HDR matrix was captured; do not imply otherwise.

The initial automated result alone was insufficient: the real permission failure
was reproduced, corrected, covered by regressions, and then followed by the
maintainer's successful functional test. Ubuntu/UGM's historical 1.1.0 hardware
validation remains historical; it was not repeated on this SteamOS machine.

## Detailed physical regression checklist — for future retests

The maintainer's overall confirmation above is complete. The following is the
repeatable extended checklist, not a claim that all seven items were separately
observed during this release validation.

Do not restart or switch the user's session automatically for these checks.

1. Enter Gaming Mode; confirm active executable/version and SGSR capability
   from `get_capabilities`, not from the installed Desktop Mode binary.
2. Use an SDR game below output resolution, so upscaling actually takes place.
3. Disable both overrides; select QAM Sharp. Root filter should briefly be FSR 2
   then SGSR 5 on server 0 and siblings (~750 ms plus X11 response time).
   Confirm the effective upscale path through Gamescope feedback when available;
   a root property alone does not prove the shader is rendering.
4. Select Linear, Nearest and Pixel: no later SGSR rewrite. Test QAM Auto, Fit,
   Integer, Fill and Stretch: changing filters must not reset the chosen scaler.
5. Enable NIS then FSR: selectors 3 and 2, exclusive toggles, sharpening 0/5 and
   survival of QAM writes. Turn both off: restore SGSR.
6. SDR on HDR output retains FSR/NIS; real application HDR hides redundant FSR
   and reports FSR fallback. No stale gating after exiting the game.
7. Check plugin close/reopen, game change and Decky reload for conflicting writes.

## Rollback

Reinstall verified 1.1.0, or restore the four runtime files from the preserved
pre-update backup and reload only this Decky plugin. Steam localStorage retains
preferences. No Gamescope binary, UGM install, audio or monitor rules are changed.
