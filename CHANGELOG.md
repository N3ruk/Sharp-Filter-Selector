# Changelog

All notable changes to Sharp Filter Selector are documented here.

## [1.0.0] - 2026-09-28

### Added

- Added native SGSR capability detection against the Gamescope process that
  owns the active Xwayland session, rather than an unrelated binary in `PATH`.
- Added an explicit FSR override for SGSR-capable Gamescope builds and a shared
  0–5 sharpening control for explicit FSR/NIS operation.
- Added HDR input/output awareness: native Sharp uses SGSR for SDR input and
  reports the Gamescope FSR fallback when the application supplies HDR input.
- Added Ubuntu multi-Xwayland discovery and continuous synchronization of the
  QAM-owned scaler/filter state from authoritative server 0 to sibling roots.
- Added modern selector support for NIS (`3`), FSR (`2`) and SGSR (`5`).

### Changed

- Ubuntu no longer writes `GAMESCOPE_NEW_SCALING_SCALER` when selecting a
  filter. Scaling mode remains owned by Steam/QAM (`Auto`, `Fit`, `Integer`,
  `Stretch`).
- Steam's historical Sharp value (`2`) is translated to native SGSR (`5`) when
  the running Gamescope advertises SGSR, while explicit plugin overrides remain
  NIS or FSR.
- Frontend state is restored without passive writes that would override the
  user's current Gamescope/QAM state.
- Packaged releases now include the installer, uninstaller, changelog, source
  frontend and AI disclosure, plus a SHA256 checksum.

### Fixed

- Fixed NIS becoming ineffective on modern Gamescope/Xwayland layouts.
- Fixed QAM scaling modes being overwritten by filter selection.
- Fixed divergence between Gamescope's multiple Xwayland roots.
- Fixed false filter reporting around SGSR, explicit FSR and HDR fallback.

### Validated

- Ubuntu 26.04 Gaming Mode with Gamescope 3.16.30, NVIDIA RTX 2060 and multiple
  Xwayland roots.
- Native SGSR in SDR, explicit FSR and NIS, HDR fallback reporting, QAM scaling
  modes, 4K output and VRR.

## [0.3.4] - 2026-09-24

### Added

- Added a SteamOS-specific multi-Xwayland path that discovers Gamescope Xwayland targets and their authentication context.
- Added an explicit LINEAR → NIS transition on SteamOS before applying the final NIS selector state.
- Added richer in-plugin diagnostics for Gamescope filter state, Xwayland server IDs and FSR feedback.
- Added TypeScript/Rollup source and build configuration for the modern Decky frontend.

### Changed

- Migrated the frontend to Decky's supported public packages: `@decky/api`, `@decky/ui` and `@decky/rollup`.
- Kept Ubuntu/generic Linux on its validated compatibility path using `GAMESCOPE_SHARP_FILTER` for FSR/NIS selection, isolated from SteamOS-specific logic.
- Preserved the plugin's own 0–5 NIS sharpness slider, mapping the full Gamescope sharpness range independently of Steam's native FSR control.
- Updated repository checks and release packaging for the TypeScript/Rollup frontend.

### Fixed

- NIS activation is now confirmed working by the maintainer on both Ubuntu and SteamOS with the v0.3.4 backend/frontend combination.
- SteamOS filter application now targets multiple Gamescope Xwayland roots instead of assuming a single display.

## [0.3.1] - 2026-09-22

### Fixed

- Added persistent NIS enforcement for SteamOS/Game Mode when Steam/QAM re-applies FSR after the plugin selects NIS.
- Explicitly applies Gamescope's AUTO scaler together with the modern and legacy NIS filter selectors.
- Removed the speculative compatibility selector from the active filter-write path and now relies on upstream Gamescope properties.
- Added Gamescope FSR feedback checks so the plugin can detect when FSR is still the effective scaler.
- Added in-plugin verification messages after enabling NIS, so Steam Deck testing no longer requires terminal commands.

## [0.3.0] - 2026-09-21

### Added

- FSR/NIS switching from the Decky Quick Access Menu.
- NIS sharpness control with a 0–5 user-facing scale.
- Automatic discovery of active Gamescope/Xwayland displays.
- Persistent frontend selection for filter and sharpness.
- Portable local install and uninstall scripts.
- Release packaging script for GitHub Releases.

### Changed

- Gamescope state detection now prefers the official scaling selectors when available.
- Public documentation and user-facing messages have been simplified for general use.
