#!/usr/bin/env bash
set -euo pipefail

root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)"
version="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["version"])' "$root/package.json")"
name="sharp-filter-selector"
out_dir="$root/release"
stage="$(mktemp -d)"
trap 'rm -rf "$stage"' EXIT

mkdir -p "$out_dir" "$stage/$name/dist" "$stage/$name/docs"

# Installation payload only. Full sources, tests and build tools stay in Git.
files=(
    main.py plugin.json package.json dist/index.js
    install.sh uninstall.sh LICENSE CHANGELOG.md
    README.md README_ES.md
    docs/COMPATIBILITY.md docs/DEVELOPMENT.md
)
for file in "${files[@]}"; do
    cp "$root/$file" "$stage/$name/$file"
done
chmod +x "$stage/$name/install.sh" "$stage/$name/uninstall.sh"

archive="$out_dir/${name}-v${version}.zip"
# Build a fresh archive so removed documentation cannot survive an update.
(
    cd "$stage"
    zip -qr "$stage/$name.zip" "$name"
)
mv -- "$stage/$name.zip" "$archive"
(cd "$out_dir" && sha256sum "$(basename -- "$archive")" > "$(basename -- "$archive").sha256")

echo "Created: $archive"
echo "Checksum: $archive.sha256"
