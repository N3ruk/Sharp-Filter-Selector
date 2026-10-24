# Development / Desarrollo

[English](#english) · [Español](#español) · [README](../README.md)

## English

### Repository layout

```text
main.py                 Decky backend entry point
src/index.tsx           Frontend source
dist/index.js          Committed frontend bundle (required by Decky)
tests/                  Backend and frontend regressions
scripts/package.sh      Installation ZIP builder
docs/COMPATIBILITY.md   Supported paths, version comparison and validation
docs/DEVELOPMENT.md     This guide
README.md / README_ES.md User installation and usage
CHANGELOG.md / LICENSE  Plugin history and license
```

`main.py`, `plugin.json`, `package.json` and `dist/index.js` stay in Decky's expected
layout. Node/TypeScript configuration stays at repository root. Do not relocate
entry points or rebuild the installed plugin just to reorganize documentation.

### Build and check

```bash
npm ci
npm test
npm run typecheck
npm run build
python3 -m py_compile main.py
npm run package
```

`npm test` runs the Python and frontend suites. The existing GitHub workflow
checks syntax, build and packaging; it does not run the complete local suite.
Review the generated `dist/index.js` before committing it. Do not change the
Ubuntu/UGM or old-SteamOS paths as a side effect of a platform-specific fix.

### Packages and releases

`npm run package` writes `release/sharp-filter-selector-vX.Y.Z.zip` and `.zip.sha256`.
The ZIP has one `sharp-filter-selector/` directory containing runtime, portable
installer/uninstaller, EN/ES user documentation, compact technical guides, changelog and
license. Frontend sources, tests and build tools stay in Git; use the repository
or GitHub's source archives for development.

For a new functional version, update package/lockfile versions, changelog and user
instructions; run the checks above, commit, push main and wait for CI. Tag that
commit and publish the ZIP/checksum with **equivalent Spanish and English notes**.
Download both published assets and compare their hashes and runtime files.

A documentation-only archive refresh may retain the version and tag if runtime
is unchanged. Record the packaging commit in the release notes, replace ZIP and
checksum together, and never move an existing tag. Historical source archives
continue to describe the original tag.

### Bug reports and contributions

Include distribution, Decky/Gamescope versions, selected filter, application HDR
state and relevant plugin logs. Never post tokens or private system details.
Keep changes focused, run the checks and test real Gamescope behavior when a
filter path changes. Report security-sensitive issues privately to the maintainer
rather than publishing exploit details in a public issue.

## Español

### Organización

- `main.py`: entrada del backend que espera Decky.
- `src/`: fuente del frontend; `dist/`: bundle compilado que utiliza Decky.
- `tests/`: pruebas; `scripts/`: empaquetado; `docs/`: dos guías técnicas.
- Raíz: README español/inglés, changelog, licencia y configuración necesaria.

### Desarrollo y publicación

Ejecuta los comandos de la sección inglesa: instalación bloqueada con `npm ci`,
pruebas, tipos, build, sintaxis Python y empaquetado. La automatización GitHub
existente comprueba build/paquetes, no toda la batería local. Conserva las rutas
Ubuntu/UGM y SteamOS antiguo al corregir una plataforma concreta.

El ZIP es para **instalar**; fuentes frontend, pruebas y herramientas de desarrollo
permanecen en el repositorio. Para publicar una versión funcional nueva, actualiza
versiones y changelog, verifica, sube main, espera CI y crea tag/release con notas
completas en **español e inglés**. Comprueba las descargas y sus hashes.

Si solo cambia documentación/empaquetado, puede mantenerse versión y tag siempre
que el runtime sea idéntico. Documenta el commit del paquete, actualiza ZIP y
checksum juntos y no muevas tags históricos.

Al informar de un fallo, incluye versiones, filtro/HDR y logs pertinentes, sin
credenciales ni datos privados. Las incidencias de seguridad se comunican al
mantenedor de forma privada.
