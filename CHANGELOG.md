# Changelog

## 1.2.0 — 2026-10-24

- SteamOS-only QAM Sharp `2` → SGSR `5` bridge for compatible active Gamescope.
- Restricted `/proc/PID/exe` detection corrected without root or PATH substitution.
- Modern SteamOS filter changes preserve QAM scaling; NIS/FSR share one bridge.
- Explicit SGSR status, reliable capability refresh and full Gamescope version display.
- Ubuntu/UGM's twelve `_ubuntu*` methods, legacy SteamOS behavior and HDR policy preserved.
- 48 automated tests; maintainer-confirmed operation on SteamOS 3.9.5 / Gamescope 3.16.30.1.
- Documentation refresh: concise EN/ES README, two technical guides, bilingual release
  notes and a lean installation ZIP. Runtime/version/tag unchanged by this cleanup.

[Compatibility, comparison with 1.1.0 and validation](docs/COMPATIBILITY.md)

## 1.1.0 — 2026-09-29

- FSR visibility follows fresh application HDR feedback, not display HDR mode.
- SDR on HDR output retains FSR/NIS; missing/conflicting feedback fails open.
- Existing filter/scaler/sharpening behavior preserved; Ubuntu Gaming validation.

## 1.0.0 — 2026-09-28

- Active-process SGSR capability detection, explicit FSR override and HDR awareness.
- Ubuntu QAM/server-0 synchronization and modern FSR/NIS/SGSR selectors.
- Shared 0–5 sharpening; QAM scaler ownership and passive frontend initialization.

## 0.3.4 — 2026-09-24

- Multi-Xwayland SteamOS discovery and LINEAR → NIS transition.
- Modern Decky frontend and richer filter diagnostics.
- Separate Ubuntu compatibility route; NIS confirmed on Ubuntu and SteamOS.

## 0.3.1 — 2026-09-22

- SteamOS NIS enforcement, legacy/modern selectors and FSR feedback verification.

## 0.3.0 — 2026-09-21

- Initial FSR/NIS selection, sharpening, session discovery and portable installer.
