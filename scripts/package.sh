#!/usr/bin/env bash
set -euo pipefail

root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)"
version="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["version"])' "$root/package.json")"
name="sharp-filter-selector"
out_dir="$root/release"
stage="$(mktemp -d)"
trap 'rm -rf "$stage"' EXIT

mkdir -p "$out_dir" "$stage/$name/dist" "$stage/$name/src"

cp "$root/main.py" "$stage/$name/main.py"
cp "$root/plugin.json" "$stage/$name/plugin.json"
cp "$root/package.json" "$stage/$name/package.json"
cp "$root/README.md" "$stage/$name/README.md"
cp "$root/README_ES.md" "$stage/$name/README_ES.md"
cp "$root/LICENSE" "$stage/$name/LICENSE"
cp "$root/dist/index.js" "$stage/$name/dist/index.js"
cp "$root/src/index.tsx" "$stage/$name/src/index.tsx"
cp "$root/rollup.config.js" "$stage/$name/rollup.config.js"
cp "$root/tsconfig.json" "$stage/$name/tsconfig.json"

# Include the portable local installer/uninstaller so GitHub Release users
# can install the exact packaged build without cloning the repository.
cp "$root/install.sh" "$stage/$name/install.sh"
cp "$root/uninstall.sh" "$stage/$name/uninstall.sh"
chmod +x "$stage/$name/install.sh" "$stage/$name/uninstall.sh"

archive="$out_dir/${name}-v${version}.zip"
rm -f "$archive"
(
  cd "$stage"
  zip -qr "$archive" "$name"
)

echo "Created: $archive"
