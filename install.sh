#!/usr/bin/env bash
set -euo pipefail

base="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
target_user="${SUDO_USER:-${USER:-}}"

if [[ -z "$target_user" || "$target_user" == "root" ]]; then
    target_home="${HOME}"
else
    target_home="$(getent passwd "$target_user" 2>/dev/null | cut -d: -f6)"
    [[ -n "$target_home" ]] || target_home="${HOME}"
fi

plugin_dir="${DECKY_PLUGIN_DIR:-${target_home}/homebrew/plugins/sharp-filter-selector}"

for required in plugin.json package.json main.py dist/index.js; do
    [[ -f "$base/$required" ]] || {
        echo "Missing plugin file: $base/$required" >&2
        exit 1
    }
done

install_file() {
    local mode="$1"
    local source="$2"
    local destination="$3"

    if [[ -w "$(dirname -- "$destination")" ]]; then
        install -m "$mode" "$source" "$destination"
    else
        command -v sudo >/dev/null || {
            echo "Cannot write to $destination and sudo is not available." >&2
            exit 1
        }
        sudo install -m "$mode" "$source" "$destination"
    fi
}

if [[ -w "$(dirname -- "$plugin_dir")" || -w "$plugin_dir" ]]; then
    install -d -m 0755 "$plugin_dir/dist"
else
    command -v sudo >/dev/null || {
        echo "Cannot create $plugin_dir and sudo is not available." >&2
        exit 1
    }
    sudo install -d -m 0755 "$plugin_dir/dist"
fi

install_file 0644 "$base/plugin.json" "$plugin_dir/plugin.json"
install_file 0644 "$base/package.json" "$plugin_dir/package.json"
install_file 0644 "$base/main.py" "$plugin_dir/main.py"
install_file 0644 "$base/dist/index.js" "$plugin_dir/dist/index.js"

if [[ -n "$target_user" && "$target_user" != "root" ]] && command -v id >/dev/null; then
    target_group="$(id -gn "$target_user" 2>/dev/null || true)"
    if [[ -n "$target_group" ]] && command -v sudo >/dev/null; then
        sudo chown -R "$target_user:$target_group" "$plugin_dir" 2>/dev/null || true
    fi
fi

echo "Sharp Filter Selector installed to: $plugin_dir"
echo "Reload Decky Loader or restart Gaming Mode/Steam to load it."
