#!/usr/bin/env bash
set -euo pipefail

target_user="${SUDO_USER:-${USER:-}}"
if [[ -z "$target_user" || "$target_user" == "root" ]]; then
    target_home="${HOME}"
else
    target_home="$(getent passwd "$target_user" 2>/dev/null | cut -d: -f6)"
    [[ -n "$target_home" ]] || target_home="${HOME}"
fi

plugin_dir="${DECKY_PLUGIN_DIR:-${target_home}/homebrew/plugins/sharp-filter-selector}"

if [[ ! -e "$plugin_dir" ]]; then
    echo "Sharp Filter Selector is not installed at: $plugin_dir"
    exit 0
fi

if [[ -w "$(dirname -- "$plugin_dir")" ]]; then
    rm -rf -- "$plugin_dir"
else
    command -v sudo >/dev/null || {
        echo "Cannot remove $plugin_dir and sudo is not available." >&2
        exit 1
    }
    sudo rm -rf -- "$plugin_dir"
fi

echo "Sharp Filter Selector removed from: $plugin_dir"
