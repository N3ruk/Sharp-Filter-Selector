# Sharp Filter Selector

SGSR, FSR and NIS controls for **Decky Loader** on SteamOS and Ubuntu/UGM.
The plugin uses the running Gamescope; it does not install or replace it.

**[Español](README_ES.md)** · [Download](https://github.com/N3ruk/Sharp-Filter-Selector/releases/latest) · [Changelog](CHANGELOG.md)

## Requirements

- Decky Loader and an active Gamescope/Xwayland gaming session.
- The system `xprop` command.
- A game rendered below output resolution to see an upscaling effect.
- An SGSR-capable **running** Gamescope for SGSR and the separate FSR override.

## Install

Download the ZIP and its `.sha256` file from [Releases](https://github.com/N3ruk/Sharp-Filter-Selector/releases/latest), then:

```bash
sha256sum -c sharp-filter-selector-v1.2.0.zip.sha256
unzip sharp-filter-selector-v1.2.0.zip
cd sharp-filter-selector
./install.sh
```

The installer updates `~/homebrew/plugins/sharp-filter-selector`.
Reload the plugin through Decky, or restart Steam/Gaming Mode to load it.
Existing plugin selections are retained. To remove it, run `./uninstall.sh`.

## Use

Open **QAM → Decky → Sharp Filter Selector** while a game is running.

| Selection | Result |
| --- | --- |
| Both overrides off | QAM Sharp uses SGSR when supported; otherwise native FSR |
| **Use NIS** on | NVIDIA Image Scaling |
| **Use FSR** on | Explicit AMD FSR instead of SGSR |
| **Sharpness** 0–5 | Shared sharpening for explicit NIS or FSR |

Only one override can be on. To use SGSR, turn both off and choose **Sharp**
in Steam's QAM. SteamOS promotion to SGSR is periodic (~750 ms plus X11 response),
not an atomic Gamescope modification. QAM's scaling mode remains under QAM control
on Ubuntu and modern SGSR-capable SteamOS.

## If something is missing

- **Waiting for Gamescope:** enter a real Gaming session; Desktop/Big Picture
  alone does not establish Gamescope support.
- **FSR control hidden:** the active Gamescope may lack SGSR, detection may have
  failed, or the application is supplying HDR input. Read the plugin's SGSR status.
- **HDR:** SGSR uses Gamescope's FSR fallback for HDR input. HDR output alone
  does not hide the FSR override for an SDR game.
- **No visible difference:** lower the game's render resolution below the display.

## Documentation

- [Compatibility, 1.1.0 → 1.2.0 changes and validation](docs/COMPATIBILITY.md)
- [Source layout, build, tests and packaging](docs/DEVELOPMENT.md)
- [Version history](CHANGELOG.md)

The installation ZIP contains the plugin, installer and user documentation.
The complete frontend source, build configuration and tests are in this repository.

## License

[BSD-3-Clause](LICENSE). Independent project, not affiliated with Valve, AMD or NVIDIA.
