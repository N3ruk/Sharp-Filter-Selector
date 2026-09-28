# GitHub release workflow

The repository is already published at:

```text
https://github.com/N3ruk/Sharp-Filter-Selector
```

## Build the release assets

```bash
npm run build
npm run package
```

The package command creates a portable ZIP and its SHA256 file:

```text
release/sharp-filter-selector-vX.Y.Z.zip
release/sharp-filter-selector-vX.Y.Z.zip.sha256
```

## Publish

After updating `package.json`, `CHANGELOG.md` and both README files:

```bash
git add .
git commit -m "Release Sharp Filter Selector X.Y.Z"
git push origin main
git tag -a vX.Y.Z -m "Sharp Filter Selector X.Y.Z"
git push origin vX.Y.Z
```

Create the GitHub Release for that tag and attach both generated files. The ZIP
must contain a single top-level `sharp-filter-selector` directory with
`install.sh`, `uninstall.sh`, `main.py`, `plugin.json`, `package.json` and
`dist/index.js`.

Suggested repository topics:

```text
decky decky-loader steam-deck steamos gamescope sgsr fsr nis linux-gaming
```
