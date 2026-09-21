# First GitHub upload

Create an empty GitHub repository, then run these commands from this folder:

```bash
git init
git add .
git commit -m "Initial public release: Sharp Filter Selector 0.3.0"
git branch -M main
git remote add origin <YOUR_GITHUB_REPOSITORY_URL>
git push -u origin main
```

## Create the first release

Build the runtime frontend and release ZIP:

```bash
npm run build
npm run package
```

Then tag the release:

```bash
git tag -a v0.3.0 -m "Sharp Filter Selector 0.3.0"
git push origin v0.3.0
```

On GitHub, create a Release for tag `v0.3.0` and attach:

```text
release/sharp-filter-selector-v0.3.0.zip
```

Suggested release title:

```text
Sharp Filter Selector 0.3.0
```

Suggested repository topics:

```text
decky decky-loader steam-deck steamos gamescope fsr nis linux-gaming
```
