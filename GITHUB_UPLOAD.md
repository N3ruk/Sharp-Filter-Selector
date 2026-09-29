# GitHub release workflow

The repository is already published at:

```text
https://github.com/N3ruk/Sharp-Filter-Selector
```

## Build the release assets

```bash
npm ci
npm run build
python3 -m unittest discover -s tests -v
npm run package
```

The package command creates a portable ZIP and its SHA256 file:

```text
release/sharp-filter-selector-vX.Y.Z.zip
release/sharp-filter-selector-vX.Y.Z.zip.sha256
```

## Publish

After updating `package.json`, `package-lock.json`, `CHANGELOG.md` and both
README files, verify that the packaged version and changelog heading match.
Then publish the commit and annotated tag:

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

The release title is `Sharp Filter Selector X.Y.Z`. Use the matching changelog
entry as release notes and state separately which behaviors were physically
validated in Gaming Mode and which were covered only by automated tests.

Suggested repository topics:

```text
decky decky-loader steam-deck steamos gamescope sgsr fsr nis linux-gaming
```
