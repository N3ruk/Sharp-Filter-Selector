# Sharp Filter Selector — SGSR / FSR / NIS for Decky Loader

**Sharp Filter Selector** is a Decky Loader plugin that controls Gamescope's
Sharp scaling filter from the Quick Access Menu. On recent Gamescope builds it
keeps native **SGSR** as the default Sharp path and provides explicit overrides
for **AMD FSR** and **NVIDIA NIS**.

[Documentación en español](README_ES.md)

## Features

- Detects SGSR support from the Gamescope process that owns the active Xwayland
  session.
- Preserves native Sharp behavior: SGSR for SDR input and Gamescope's FSR
  fallback for HDR input.
- Provides explicit **Use NIS** and **Use FSR** overrides when supported.
- Provides a shared 0–5 sharpness control for explicit FSR/NIS operation.
- Keeps multiple Gamescope Xwayland roots synchronized.
- Leaves Steam/QAM scaling mode (`Auto`, `Fit`, `Integer`, `Stretch`) under QAM
  control; filter selection never changes the scaler on Ubuntu.
- Remembers explicit plugin selections without performing passive writes during
  frontend initialization.
- Does not patch, replace or install Gamescope.

## Requirements

- Decky Loader.
- An active Gamescope/Xwayland gaming session.
- `xprop` available on the host.
- A game rendered below the output resolution for scaling-filter differences to
  be visible.

SGSR support depends on the running Gamescope build. When SGSR is not available,
the plugin keeps the compatible FSR/NIS behavior.

## Installation

### GitHub Release ZIP

1. Download the ZIP matching your desired version (for example,
   `sharp-filter-selector-v1.1.0.zip`).
2. Extract it; the archive contains one `sharp-filter-selector` directory.
3. Run the included installer:

```bash
cd sharp-filter-selector
./install.sh
```

The default destination is:

```text
~/homebrew/plugins/sharp-filter-selector/
```

Reload Decky Loader or restart Steam/Gaming Mode after installation. A custom
test destination can be selected without root:

```bash
DECKY_PLUGIN_DIR=/path/to/plugins/sharp-filter-selector ./install.sh
```

To uninstall:

```bash
./uninstall.sh
```

### From source

```bash
git clone https://github.com/N3ruk/Sharp-Filter-Selector.git
cd Sharp-Filter-Selector
./install.sh
```

## Usage

1. Start a game in a Gamescope gaming session.
2. Open Quick Access Menu → Decky Loader → Sharp Filter Selector.
3. Leave both overrides disabled for Gamescope's native Sharp filter.
4. Enable **Use NIS** for NVIDIA Image Scaling.
5. On SGSR-capable builds, enable **Use FSR** for an explicit AMD FSR override.
6. Adjust **Sharpness** from 0 to 5 when using explicit FSR or NIS.

Only one explicit override can be active. The status line reports the effective
engine and the Gamescope targets that were updated.

## How it works

### Ubuntu / generic Linux

The backend discovers active Gamescope/Xwayland displays from process ancestry
and environment data. Xwayland server 0 is treated as the QAM authority. Its
valid scaler and filter values are mirrored to sibling roots without changing
the scaler selected by QAM.

On Gamescope 3.16.29+ the historical QAM Sharp value `2` is translated to native
SGSR selector `5` when the active Gamescope advertises SGSR. Explicit plugin
overrides retain NIS selector `3` or FSR selector `2`.

### SteamOS

The plugin retains its validated multi-Xwayland discovery and explicit
LINEAR → NIS transition, while also supporting native SGSR and explicit FSR on
compatible Gamescope builds.

### HDR

The restriction is HDR **input**, not merely an HDR-capable output. If the
application supplies HDR input, Gamescope uses its FSR fallback for native
Sharp. An HDR output carrying SDR input can continue using SGSR.

Since 1.1.0, only `GAMESCOPE_COLOR_APP_WANTS_HDR_FEEDBACK` controls HDR gating.
Missing, invalid or conflicting feedback is treated as unknown: both FSR and
NIS remain available on SGSR-capable builds, regardless of display HDR mode.
Opening QAM does not itself enable HDR gating; visibility follows the fresh
application feedback. No HDR-state cache is carried across game changes.

## Compatibility and validation

Version 1.1.0 was validated on Ubuntu 26.04 Gaming Mode with Gamescope 3.16.30,
an NVIDIA RTX 2060, multiple Xwayland roots, 4K output and VRR. A physical
game/QAM test confirmed that an SDR game on an HDR output keeps both FSR and
NIS available, while application HDR feedback—not the display HDR toggle—drives
the FSR visibility transition. Native SGSR, explicit FSR/NIS, the 0–5
sharpness mapping and all QAM scaling modes remain operational.

The automated suite additionally covers SDR, HDR, missing, invalid and
conflicting application feedback, frontend refresh failures and the complete
FSR/NIS sharpness mapping. It does not simulate Gamescope or replace the
physical Gaming Mode validation above.

Other systems require compatible Gamescope properties and `xprop`. SteamOS
support is retained but should be validated against the installed Gamescope and
Decky versions.

## Troubleshooting

**No Gamescope targets were found**

Use the plugin inside an active Gamescope gaming session and ensure `xprop` is
installed.

**The filter changes but the image looks the same**

Gamescope must actually upscale. Render the game below the final display
resolution.

**Native Sharp reports FSR instead of SGSR**

This is expected for HDR application input, or when the running Gamescope does
not advertise SGSR support.

**The QAM scaling mode does not change the image**

This plugin does not own that mode. Verify the running Gamescope and the QAM
integration; filter selection deliberately does not overwrite the scaler.

## Development and packaging

```bash
npm install
npm run build
npm run package
```

The package command creates:

```text
release/sharp-filter-selector-vX.Y.Z.zip
release/sharp-filter-selector-vX.Y.Z.zip.sha256
```

The ZIP includes the compiled runtime, source frontend, portable installer and
uninstaller, README files, changelog and license.

Release packages use the validated `dist/index.js` committed to the repository.
Because Decky build dependencies can change their generated loader wrapper,
review and test a fresh `npm run build` before replacing that validated bundle.

## License and disclosure

BSD 3-Clause. See [LICENSE](LICENSE).

Built for [Decky Loader](https://github.com/SteamDeckHomebrew/decky-loader) and
[Gamescope](https://github.com/ValveSoftware/gamescope). FSR, NIS and SGSR are
their respective owners' technologies. This independent community plugin is not
affiliated with or endorsed by Valve, AMD or NVIDIA.

See [AI_DISCLOSURE.md](AI_DISCLOSURE.md) for the project's AI-assistance
provenance.
