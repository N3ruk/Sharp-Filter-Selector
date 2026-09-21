# Changelog

All notable changes to Sharp Filter Selector are documented here.

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
