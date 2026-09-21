"""Decky backend for switching Gamescope scaling between FSR and NIS.

The plugin writes Gamescope's scaling and sharpness properties to every active
Gamescope/Xwayland root it can discover. An additional compatibility selector
is written for Gamescope setups that expose it; systems that do not use that
property simply ignore it.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
from pathlib import Path

import decky


DISPLAY_RE = re.compile(r"^:[0-9]+(?:\.[0-9]+)?$")
SHARPNESS_MIN = 0
SHARPNESS_MAX = 5

# Steam/QAM-compatible selector:
# 0 linear, 1 nearest, 2 integer-nearest, 3 FSR, 4 NIS.
LEGACY_SCALING_FSR = 3
LEGACY_SCALING_NIS = 4

# Direct GamescopeUpscaleFilter enum:
# 0 linear, 1 nearest, 2 FSR, 3 NIS, ...
NEW_SCALING_FSR = 2
NEW_SCALING_NIS = 3

# Optional compatibility selector used by some Gamescope setups.
COMPAT_SCALING_FSR = 0
COMPAT_SCALING_NIS = 1


class Plugin:
    """Control Gamescope scaling properties on active Xwayland roots."""

    @staticmethod
    def _xprop_binary() -> str | None:
        """Find xprop without assuming a distribution-specific path."""
        for candidate in (
            shutil.which("xprop"),
            "/usr/bin/xprop",
            "/usr/local/bin/xprop",
            "/bin/xprop",
        ):
            if candidate and os.path.isfile(candidate) and os.access(candidate, os.X_OK):
                return candidate
        return None

    @staticmethod
    def _displays() -> list[tuple[str, int, int, dict[str, str]]]:
        """Discover DISPLAYs that belong to a Gamescope session.

        Decky may run with different privileges from Steam/Gamescope, so the
        process environment is inspected and xprop is later executed as the
        owner of the Gamescope session.
        """
        displays: dict[str, tuple[int, int, dict[str, str]]] = {}

        try:
            proc_entries = list(Path("/proc").iterdir())
        except OSError:
            return []

        for proc in proc_entries:
            if not proc.name.isdigit():
                continue

            try:
                stat = proc.stat()
                if stat.st_uid == 0:
                    continue
                environ = (proc / "environ").read_bytes().split(b"\0")
            except (FileNotFoundError, PermissionError, ProcessLookupError, OSError):
                continue

            environment: dict[str, str] = {}
            for entry in environ:
                if b"=" not in entry:
                    continue
                key, value = entry.split(b"=", 1)
                environment[key.decode("ascii", "ignore")] = value.decode(
                    "utf-8", "ignore"
                )

            desktop = environment.get("XDG_CURRENT_DESKTOP", "").lower()
            if "gamescope" not in desktop and not environment.get(
                "GAMESCOPE_WAYLAND_DISPLAY"
            ):
                continue

            display = environment.get("DISPLAY", "")
            if DISPLAY_RE.fullmatch(display):
                displays[display] = (stat.st_uid, stat.st_gid, environment)

        return [
            (display, *details)
            for display, details in sorted(
                displays.items(),
                key=lambda item: int(item[0][1:].split(".", 1)[0]),
            )
        ]

    @staticmethod
    def _xenv(environment: dict[str, str]) -> dict[str, str]:
        xenv = os.environ.copy()
        xenv["DISPLAY"] = environment.get("DISPLAY", "")
        if environment.get("XAUTHORITY"):
            xenv["XAUTHORITY"] = environment["XAUTHORITY"]
        else:
            xenv.pop("XAUTHORITY", None)
        return xenv

    @staticmethod
    def _drop_privileges(uid: int, gid: int):
        def drop() -> None:
            if os.geteuid() == 0:
                os.setgroups([])
                os.setgid(gid)
                os.setuid(uid)

        return drop

    @classmethod
    def _write_property(
        cls,
        display: str,
        uid: int,
        gid: int,
        environment: dict[str, str],
        name: str,
        value: int,
    ) -> tuple[bool, str]:
        xprop = cls._xprop_binary()
        if not xprop:
            return False, "xprop is not installed or could not be found in PATH"

        try:
            completed = subprocess.run(
                [
                    xprop,
                    "-display",
                    display,
                    "-root",
                    "-f",
                    name,
                    "32c",
                    "-set",
                    name,
                    str(value),
                ],
                check=False,
                capture_output=True,
                text=True,
                timeout=3,
                env=cls._xenv(environment),
                preexec_fn=cls._drop_privileges(uid, gid),
            )
        except (FileNotFoundError, subprocess.TimeoutExpired, OSError) as exc:
            return False, str(exc)

        if completed.returncode != 0:
            return False, (completed.stderr or completed.stdout).strip()
        return True, ""

    @classmethod
    def _read_property(
        cls,
        display: str,
        uid: int,
        gid: int,
        environment: dict[str, str],
        name: str,
    ) -> int | None:
        xprop = cls._xprop_binary()
        if not xprop:
            return None

        try:
            completed = subprocess.run(
                [xprop, "-display", display, "-root", name],
                check=False,
                capture_output=True,
                text=True,
                timeout=3,
                env=cls._xenv(environment),
                preexec_fn=cls._drop_privileges(uid, gid),
            )
        except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
            return None

        if completed.returncode != 0:
            return None

        match = re.search(r"=\s*(-?\d+)\s*$", completed.stdout)
        return int(match.group(1)) if match else None

    @classmethod
    def _write_all(
        cls,
        properties: tuple[tuple[str, int], ...],
    ) -> tuple[list[str], list[str]]:
        displays = cls._displays()
        applied: list[str] = []
        errors: list[str] = []

        for display, uid, gid, environment in displays:
            display_errors: list[str] = []
            for name, value in properties:
                ok, error = cls._write_property(
                    display, uid, gid, environment, name, value
                )
                if not ok:
                    display_errors.append(f"{name}: {error}")

            if display_errors:
                errors.append(f"{display}: {'; '.join(display_errors)}")
            else:
                applied.append(display)

        return applied, errors

    @staticmethod
    def _engine_properties(enabled: bool) -> tuple[tuple[str, int], ...]:
        if enabled:
            return (
                ("GAMESCOPE_SCALING_FILTER", LEGACY_SCALING_NIS),
                ("GAMESCOPE_NEW_SCALING_FILTER", NEW_SCALING_NIS),
                ("GAMESCOPE_SHARP_FILTER", COMPAT_SCALING_NIS),
            )

        return (
            ("GAMESCOPE_SCALING_FILTER", LEGACY_SCALING_FSR),
            ("GAMESCOPE_NEW_SCALING_FILTER", NEW_SCALING_FSR),
            ("GAMESCOPE_SHARP_FILTER", COMPAT_SCALING_FSR),
        )

    async def set_nis_enabled(self, enabled: bool) -> dict:
        if not isinstance(enabled, bool):
            return {"success": False, "error": "Invalid NIS state"}

        applied, errors = self._write_all(self._engine_properties(enabled))
        if not applied:
            error = (
                "No accessible Gamescope session was found"
                if not errors
                else "; ".join(errors)
            )
            return {"success": False, "error": error}

        engine = "nis" if enabled else "fsr"
        decky.logger.info(
            "Sharp Filter Selector: %s applied on %s",
            engine,
            ", ".join(applied),
        )
        return {
            "success": True,
            "enabled": enabled,
            "engine": engine,
            "displays": applied,
            "errors": errors,
        }

    async def set_nis_sharpness(self, level: int) -> dict:
        if (
            isinstance(level, bool)
            or not isinstance(level, int)
            or not SHARPNESS_MIN <= level <= SHARPNESS_MAX
        ):
            return {"success": False, "error": "Sharpness must be between 0 and 5"}

        # Gamescope's property scale is inverted: lower raw values are sharper.
        # The plugin exposes an intuitive 0..5 scale to the user.
        raw_value = 20 - (level * 4)
        applied, errors = self._write_all(
            (
                ("GAMESCOPE_SHARPNESS", raw_value),
                ("GAMESCOPE_FSR_SHARPNESS", raw_value),
            )
        )

        if not applied:
            error = (
                "No accessible Gamescope session was found"
                if not errors
                else "; ".join(errors)
            )
            return {"success": False, "error": error}

        decky.logger.info(
            "Sharp Filter Selector: sharpness %d/5 (Gamescope=%d) applied on %s",
            level,
            raw_value,
            ", ".join(applied),
        )
        return {
            "success": True,
            "level": level,
            "rawValue": raw_value,
            "displays": applied,
            "errors": errors,
        }

    async def get_status(self) -> dict:
        displays = self._displays()
        if not displays:
            return {"success": False, "error": "No accessible Gamescope session was found"}

        nis_enabled = False
        raw_sharpness: int | None = None
        available: list[str] = []
        diagnostics: list[dict] = []

        for display, uid, gid, environment in displays:
            available.append(display)

            compat = self._read_property(
                display, uid, gid, environment, "GAMESCOPE_SHARP_FILTER"
            )
            legacy = self._read_property(
                display, uid, gid, environment, "GAMESCOPE_SCALING_FILTER"
            )
            modern = self._read_property(
                display, uid, gid, environment, "GAMESCOPE_NEW_SCALING_FILTER"
            )

            # Prefer official selectors. Fall back to the optional compatibility
            # selector only if neither official property is available.
            if modern is not None:
                display_nis = modern == NEW_SCALING_NIS
            elif legacy is not None:
                display_nis = legacy == LEGACY_SCALING_NIS
            else:
                display_nis = compat == COMPAT_SCALING_NIS

            nis_enabled = nis_enabled or display_nis

            for property_name in (
                "GAMESCOPE_SHARPNESS",
                "GAMESCOPE_FSR_SHARPNESS",
            ):
                value = self._read_property(
                    display, uid, gid, environment, property_name
                )
                if value is not None:
                    raw_sharpness = max(0, min(20, value))
                    break

            diagnostics.append(
                {
                    "display": display,
                    "legacyFilter": legacy,
                    "newFilter": modern,
                    "compatFilter": compat,
                }
            )

        level = (
            round((20 - raw_sharpness) / 4)
            if raw_sharpness is not None
            else None
        )
        return {
            "success": True,
            "enabled": nis_enabled,
            "engine": "nis" if nis_enabled else "fsr",
            "level": level,
            "rawValue": raw_sharpness,
            "displays": available,
            "diagnostics": diagnostics,
            "xprop": self._xprop_binary(),
        }

    async def _main(self):
        decky.logger.info("Sharp Filter Selector loaded")

    async def _unload(self):
        decky.logger.info("Sharp Filter Selector unloaded")
