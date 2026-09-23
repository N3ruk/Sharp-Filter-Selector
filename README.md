# Sharp Filter Selector — FSR / NIS Switcher for Decky Loader & Gamescope

**Sharp Filter Selector** is a **Decky Loader plugin for Gamescope** that lets you switch the active upscaling filter between **AMD FidelityFX Super Resolution (FSR)** and **NVIDIA Image Scaling (NIS)** directly from the Quick Access Menu.

It is designed for **Steam Deck / SteamOS and compatible Linux gaming sessions using Decky Loader + Gamescope**, and provides a simple **0–5 NIS sharpness control** without editing per-game launch options.

If you are looking for a **Decky NIS plugin**, a way to switch **FSR vs NIS in Gamescope**, or a **Steam Deck scaling filter selector**, this plugin is built for that workflow.

## Features

- Switch Gamescope scaling between **FSR** and **NIS** from Decky Loader.
- Adjust **NIS sharpness** from **0 (minimum)** to **5 (maximum)**.
- Apply the selected filter to active Gamescope/Xwayland sessions, including SteamOS multi-Xwayland setups.
- Remember the selected filter and sharpness level.
- No per-game launch-option editing required.
- Does **not** replace, patch or install Gamescope.

## Requirements

- **Decky Loader**.
- A Linux gaming session running **Gamescope**.
- `xprop` available on the system.
- A game/render resolution where Gamescope is actually performing scaling.

> If the game is already rendering at the final display resolution, changing the scaling filter may produce little or no visible difference. Sharp Filter Selector chooses the scaling filter; it does not force a lower render resolution.

## Installation

### From GitHub Releases

1. Open the repository's **Releases** section.
2. Download the latest `sharp-filter-selector-vX.Y.Z.zip`.
3. Install it through Decky Loader's developer/plugin installation flow, or extract the `sharp-filter-selector` folder into the Decky plugins directory.
4. Reload Decky Loader or restart Gaming Mode/Steam.

Typical Decky plugin directory:

```text
~/homebrew/plugins/sharp-filter-selector/
```

### From source

```bash
git clone https://github.com/N3ruk/Sharp-Filter-Selector.git
cd Sharp-Filter-Selector
./install.sh
```

To uninstall:

```bash
./uninstall.sh
```

For custom test locations:

```bash
DECKY_PLUGIN_DIR=/path/to/sharp-filter-selector ./install.sh
```

## Usage

1. Start a game in a Gamescope gaming session.
2. Open the **Quick Access Menu**.
3. Open **Decky Loader** → **Sharp Filter Selector**.
4. Enable **Use NIS** to switch from FSR to NVIDIA Image Scaling.
5. Set **NIS sharpness** from `0` to `5`.
6. Disable **Use NIS** to return to FSR.

The status line shows the selected filter and the Gamescope display targets that were updated.

## FSR vs NIS in Gamescope

Sharp Filter Selector does not implement its own scaler. It controls the scaling-filter state exposed by Gamescope.

- **FSR** = AMD FidelityFX Super Resolution spatial upscaling.
- **NIS** = NVIDIA Image Scaling spatial upscaling.
- The sharpness slider controls the sharpening value used by Gamescope.
- Steam/Gamescope's own scaling controls can update the same state.

This makes the plugin useful for quickly comparing **Gamescope FSR and NIS** without maintaining separate launch-option strings for each game.

## How it works

The backend uses separate compatibility paths so SteamOS-specific handling does not alter the validated generic-Linux/Ubuntu behavior.

- **SteamOS:** discovers Gamescope Xwayland targets, applies the Gamescope scaling selectors across them and performs an explicit LINEAR → NIS transition before selecting NIS.
- **Ubuntu / generic Linux:** keeps the validated compatibility path based on `GAMESCOPE_SHARP_FILTER`.
- **Sharpness:** the plugin keeps its own 0–5 NIS control and maps it to Gamescope's full sharpening range.

The frontend uses Decky's supported public packages (`@decky/api`, `@decky/ui` and `@decky/rollup`).

The plugin does not inject a graphics library, modify game files or replace Gamescope, so removing it does not require restoring a modified Gamescope installation.

## Compatibility

The plugin is intended for:

- **Decky Loader** environments.
- **Steam Deck / SteamOS** gaming sessions.
- Linux gaming systems running **Gamescope** and compatible Xwayland sessions.

Version 0.3.4 has been validated by the maintainer on both Ubuntu + Gamescope and SteamOS / Steam Deck. Actual support on other systems depends on the Gamescope session exposing the expected scaling properties and on `xprop` being available.

## Troubleshooting

**The plugin says that no Gamescope session was found.**  
Make sure the plugin is being used from a Gamescope gaming session and that an active Gamescope/Xwayland display exists.

**The filter changes but the image looks the same.**  
Gamescope must be scaling the game for FSR/NIS to have a visible effect. Try rendering the game below the final output resolution.

**The plugin reports that `xprop` is missing.**  
Install the package that provides `xprop` for your distribution, then reload Decky Loader.

**The filter changed after using Steam's own scaling controls.**  
Steam/Gamescope can write the same scaling state. Open Sharp Filter Selector and apply the filter again.

## Development

The frontend source lives in `src/index.tsx` and is built with TypeScript + Rollup using Decky's supported packages.

```bash
npm install
npm run build
```

The compiled Decky frontend is written to `dist/index.js`.

Create a release-ready ZIP with:

```bash
npm run package
```

Output:

```text
release/sharp-filter-selector-vX.Y.Z.zip
```

### Repository layout

```text
.
├── dist/index.js       # Compiled Decky frontend loaded at runtime
├── src/index.tsx       # TypeScript/React frontend source
├── main.py             # Python backend
├── plugin.json         # Decky metadata
├── package.json        # Version, Decky dependencies and build scripts
├── rollup.config.js    # Decky Rollup configuration
├── tsconfig.json       # TypeScript configuration
├── install.sh          # Local/source installation helper
├── uninstall.sh        # Local uninstall helper
├── scripts/package.sh  # Release ZIP builder
└── LICENSE
```

## Search-friendly project summary

Sharp Filter Selector is a **Decky Loader Gamescope plugin** for switching **FSR and NIS on Steam Deck and Linux**. It provides a Quick Access Menu toggle for **AMD FSR / NVIDIA Image Scaling** plus NIS sharpness control.

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

## AI usage disclosure

This project was developed with substantial generative-AI assistance. A majority of the current codebase was written with AI assistance and then iteratively tested and refined on real systems by the maintainer. See **[AI_DISCLOSURE.md](AI_DISCLOSURE.md)** for the full provenance statement.
