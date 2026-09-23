# Changelog

All notable changes to Sharp Filter Selector are documented here.

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
