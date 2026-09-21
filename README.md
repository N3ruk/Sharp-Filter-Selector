# Sharp Filter Selector

**Sharp Filter Selector** is a Decky Loader plugin that lets you switch Gamescope's active upscaling filter between **AMD FidelityFX Super Resolution (FSR)** and **NVIDIA Image Scaling (NIS)** directly from the Quick Access Menu.

It also provides a simple **0–5 NIS sharpness control** and remembers the selected state between Decky sessions.

## Features

- Switch Gamescope scaling between **FSR** and **NIS** without editing launch options.
- Adjust NIS sharpening from **0 (minimum)** to **5 (maximum)**.
- Applies the selected filter to active Gamescope/Xwayland sessions.
- Remembers the selected filter and sharpness level.
- Does **not** replace, patch or install Gamescope.
- No per-game configuration files are required.

## Requirements

- **Decky Loader**.
- A Linux gaming session running **Gamescope**.
- `xprop` available on the system.
- A game/resolution setup where Gamescope is actually performing scaling.

> If the game is already rendering at the final display resolution, changing the scaling filter may produce little or no visible difference. The plugin selects the filter; it does not change the game's render resolution or Gamescope scaling mode.

## Installation

### From a release ZIP

1. Download the latest `sharp-filter-selector-vX.Y.Z.zip` from **Releases**.
2. Install it through Decky Loader's developer/plugin installation flow, or extract the `sharp-filter-selector` folder into your Decky plugins directory.
3. Reload Decky Loader or restart Gaming Mode/Steam.

Typical Decky plugin directory:

```text
~/homebrew/plugins/sharp-filter-selector/
```

### From source

Clone the repository and run:

```bash
git clone <repository-url>
cd Sharp-Filter-Selector
./install.sh
```

To uninstall:

```bash
./uninstall.sh
```

You can override the destination when testing:

```bash
DECKY_PLUGIN_DIR=/path/to/sharp-filter-selector ./install.sh
```

## Usage

1. Start a game through a Gamescope session.
2. Open the **Quick Access Menu**.
3. Open **Decky Loader** → **Sharp Filter Selector**.
4. Enable **Use NIS** to switch from FSR to NIS.
5. Set **NIS sharpness** from `0` to `5`.
6. Disable **Use NIS** to switch back to FSR.

The status line shows the currently applied filter and the Gamescope display targets that were updated.

## How it works

Sharp Filter Selector updates Gamescope's X11 root properties for the active Gamescope/Xwayland session. It uses the scaling-filter selectors exposed by Gamescope and the corresponding sharpness properties.

The plugin does not inject a graphics library, modify game files or replace Gamescope. This keeps the plugin small and makes uninstalling it straightforward.

## Troubleshooting

**The plugin says that no Gamescope session was found.**  
Make sure you are using it from a Gamescope gaming session and that a Gamescope/Xwayland display is active.

**The filter changes but the image looks the same.**  
Gamescope must be scaling the game for FSR/NIS to matter. Try running the game below the display's output resolution.

**The plugin reports that `xprop` is missing.**  
Install the package that provides `xprop` for your distribution, then reload Decky Loader.

**My setting changed after using Steam's own scaling controls.**  
Steam/Gamescope controls can update the same scaling state. Open the plugin again and re-apply the filter you want.

## Development

The runtime frontend is kept in `src/index.js` and copied to `dist/index.js` for distribution:

```bash
npm run build
```

Create a release-ready ZIP with:

```bash
npm run package
```

The resulting archive is written to:

```text
release/sharp-filter-selector-vX.Y.Z.zip
```

### Repository layout

```text
.
├── dist/index.js       # Decky frontend loaded at runtime
├── src/index.js        # Readable frontend source
├── main.py             # Python backend
├── plugin.json         # Decky metadata
├── package.json        # Version and build scripts
├── install.sh          # Local/source installation helper
├── uninstall.sh        # Local uninstall helper
├── scripts/package.sh  # Release ZIP builder
└── LICENSE
```

## Releases

When publishing a new version:

1. Update `version` in `package.json`.
2. Add the changes to `CHANGELOG.md`.
3. Run `npm run build`.
4. Run `npm run package`.
5. Create a Git tag such as `v0.3.0` and attach the generated ZIP to the GitHub Release.

## License

BSD 3-Clause. See [LICENSE](LICENSE).

## Acknowledgements

Built for [Decky Loader](https://github.com/SteamDeckHomebrew/decky-loader) and [Gamescope](https://github.com/ValveSoftware/gamescope).

FSR is an AMD technology. NIS is an NVIDIA technology. This project is an independent community plugin and is not affiliated with or endorsed by Valve, AMD or NVIDIA.
