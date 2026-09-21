"""Decky backend for switching Gamescope scaling between FSR and NIS.

The backend writes the official Gamescope X11 properties used by Steam/Game Mode
and keeps the requested NIS state enforced while enabled. This is intentional:
on SteamOS, Steam/QAM can re-assert its own FSR selection after another client
changes the Gamescope filter.
"""

from __future__ import annotations

import asyncio
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

# GamescopeUpscaleScaler enum: 0 = AUTO.
NEW_SCALER_AUTO = 0

# Fast retries catch Steam/QAM immediately re-applying FSR after our first write.
FAST_ENFORCE_PASSES = 5
FAST_ENFORCE_INTERVAL = 0.20
STEADY_ENFORCE_INTERVAL = 0.75


class Plugin:
    """Control Gamescope scaling properties on active Xwayland roots."""

    def __init__(self):
        self._nis_requested = False
        self._enforce_task: asyncio.Task | None = None

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
        """Discover DISPLAYs that belong to a Gamescope session."""
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
        """Return only official upstream Gamescope properties.

        Set the modern scaler/filter first and the legacy Steam/QAM selector
        last. The legacy selector sets AUTO + NIS/FSR in Gamescope.
        """
        if enabled:
            return (
                ("GAMESCOPE_NEW_SCALING_SCALER", NEW_SCALER_AUTO),
                ("GAMESCOPE_NEW_SCALING_FILTER", NEW_SCALING_NIS),
                ("GAMESCOPE_SCALING_FILTER", LEGACY_SCALING_NIS),
            )

        return (
            ("GAMESCOPE_NEW_SCALING_SCALER", NEW_SCALER_AUTO),
            ("GAMESCOPE_NEW_SCALING_FILTER", NEW_SCALING_FSR),
            ("GAMESCOPE_SCALING_FILTER", LEGACY_SCALING_FSR),
        )

    @classmethod
    def _nis_state_on_display(
        cls,
        display: str,
        uid: int,
        gid: int,
        environment: dict[str, str],
    ) -> dict:
        legacy = cls._read_property(
            display, uid, gid, environment, "GAMESCOPE_SCALING_FILTER"
        )
        modern = cls._read_property(
            display, uid, gid, environment, "GAMESCOPE_NEW_SCALING_FILTER"
        )
        scaler = cls._read_property(
            display, uid, gid, environment, "GAMESCOPE_NEW_SCALING_SCALER"
        )
        fsr_feedback = cls._read_property(
            display, uid, gid, environment, "GAMESCOPE_FSR_FEEDBACK"
        )

        selectors_are_nis = (
            legacy == LEGACY_SCALING_NIS and modern == NEW_SCALING_NIS
        )

        return {
            "legacy": legacy,
            "modern": modern,
            "scaler": scaler,
            "fsrFeedback": fsr_feedback,
            "selectorsAreNis": selectors_are_nis,
        }

    def _start_enforcer(self) -> None:
        task = self._enforce_task
        if task and not task.done():
            task.cancel()
        self._enforce_task = asyncio.create_task(self._enforce_nis_loop())

    async def _stop_enforcer(self) -> None:
        task = self._enforce_task
        self._enforce_task = None
        if not task:
            return
        if not task.done():
            task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

    async def _enforce_nis_loop(self) -> None:
        """Keep NIS selected if Steam/QAM reasserts FSR."""
        fast_passes = FAST_ENFORCE_PASSES

        try:
            while self._nis_requested:
                delay = (
                    FAST_ENFORCE_INTERVAL
                    if fast_passes > 0
                    else STEADY_ENFORCE_INTERVAL
                )
                await asyncio.sleep(delay)

                if not self._nis_requested:
                    break

                displays = self._displays()
                needs_reapply = fast_passes > 0

                for display, uid, gid, environment in displays:
                    state = self._nis_state_on_display(
                        display, uid, gid, environment
                    )
                    if (
                        not state["selectorsAreNis"]
                        or state["fsrFeedback"] == 1
                    ):
                        needs_reapply = True
                        break

                if needs_reapply and displays:
                    applied, errors = self._write_all(
                        self._engine_properties(True)
                    )
                    if applied:
                        decky.logger.info(
                            "Sharp Filter Selector: reinforced NIS on %s",
                            ", ".join(applied),
                        )
                    if errors:
                        decky.logger.warning(
                            "Sharp Filter Selector: NIS reinforcement errors: %s",
                            "; ".join(errors),
                        )

                if fast_passes > 0:
                    fast_passes -= 1

        except asyncio.CancelledError:
            raise
        except Exception:
            decky.logger.exception(
                "Sharp Filter Selector: NIS enforcement loop failed"
            )

    async def set_nis_enabled(self, enabled: bool) -> dict:
        if not isinstance(enabled, bool):
            return {"success": False, "error": "Invalid NIS state"}

        self._nis_requested = enabled

        if not enabled:
            await self._stop_enforcer()

        applied, errors = self._write_all(self._engine_properties(enabled))

        if enabled:
            self._start_enforcer()

        if not applied:
            error = (
                "No accessible Gamescope session was found"
                if not errors
                else "; ".join(errors)
            )
            return {
                "success": False,
                "error": error,
                "enabled": enabled,
                "engine": "nis" if enabled else "fsr",
                "enforcing": enabled,
            }

        engine = "nis" if enabled else "fsr"
        decky.logger.info(
            "Sharp Filter Selector: %s applied on %s%s",
            engine,
            ", ".join(applied),
            " (persistent enforcement enabled)" if enabled else "",
        )
        return {
            "success": True,
            "enabled": enabled,
            "engine": engine,
            "displays": applied,
            "errors": errors,
            "enforcing": enabled,
        }

    async def set_nis_sharpness(self, level: int) -> dict:
        if (
            isinstance(level, bool)
            or not isinstance(level, int)
            or not SHARPNESS_MIN <= level <= SHARPNESS_MAX
        ):
            return {"success": False, "error": "Sharpness must be between 0 and 5"}

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
            return {
                "success": False,
                "error": "No accessible Gamescope session was found",
                "requested": self._nis_requested,
                "enforcing": bool(
                    self._enforce_task and not self._enforce_task.done()
                ),
            }

        nis_enabled = False
        raw_sharpness: int | None = None
        available: list[str] = []
        diagnostics: list[dict] = []

        for display, uid, gid, environment in displays:
            available.append(display)
            state = self._nis_state_on_display(display, uid, gid, environment)

            display_nis = (
                state["selectorsAreNis"] and state["fsrFeedback"] != 1
            )
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
                    "legacyFilter": state["legacy"],
                    "newFilter": state["modern"],
                    "newScaler": state["scaler"],
                    "fsrFeedback": state["fsrFeedback"],
                    "selectorsAreNis": state["selectorsAreNis"],
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
            "requested": self._nis_requested,
            "engine": "nis" if nis_enabled else "fsr",
            "level": level,
            "rawValue": raw_sharpness,
            "displays": available,
            "diagnostics": diagnostics,
            "xprop": self._xprop_binary(),
            "enforcing": bool(
                self._enforce_task and not self._enforce_task.done()
            ),
        }

    async def _main(self):
        decky.logger.info("Sharp Filter Selector loaded")

    async def _unload(self):
        self._nis_requested = False
        await self._stop_enforcer()
        decky.logger.info("Sharp Filter Selector unloaded")
