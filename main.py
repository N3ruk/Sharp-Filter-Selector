"""Decky backend for switching Gamescope scaling between FSR and NIS.

Compatibility policy:

- Ubuntu / generic Linux uses the exact control model from the user's known-working
  Ubuntu plugin: GAMESCOPE_SHARP_FILTER is the sole FSR/NIS selector.
- SteamOS uses a separate multi-Xwayland path with standard Gamescope selectors,
  LINEAR -> NIS transition and diagnostic state.

SteamOS experiments are deliberately isolated so they cannot alter Ubuntu's
known-working behavior.
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

# SteamOS / upstream Gamescope selectors.
LEGACY_SCALING_LINEAR = 0
LEGACY_SCALING_FSR = 3
LEGACY_SCALING_NIS = 4

NEW_SCALING_LINEAR = 0
NEW_SCALING_FSR = 2
NEW_SCALING_NIS = 3

NEW_SCALER_AUTO = 0

# Ubuntu custom-build selector: this is the known-working mechanism.
UBUNTU_SHARP_FILTER_FSR = 0
UBUNTU_SHARP_FILTER_NIS = 1

FAST_ENFORCE_PASSES = 6
FAST_ENFORCE_INTERVAL = 0.20
STEADY_ENFORCE_INTERVAL = 0.75
TRANSITION_DELAY = 0.08


class Plugin:
    def __init__(self):
        self._nis_requested = False
        self._enforce_task: asyncio.Task | None = None

    # ------------------------------------------------------------------
    # PLATFORM
    # ------------------------------------------------------------------

    @staticmethod
    def _is_steamos() -> bool:
        try:
            text = Path("/etc/os-release").read_text(
                encoding="utf-8", errors="ignore"
            ).lower()
        except OSError:
            return False

        markers = (
            "id=steamos",
            'id="steamos"',
            "variant_id=steamdeck",
            'variant_id="steamdeck"',
            "name=steamos",
            'name="steamos',
        )
        return any(marker in text for marker in markers)

    # ------------------------------------------------------------------
    # UBUNTU / GENERIC LINUX
    # Exact behavior preserved from the uploaded working Ubuntu plugin.
    # ------------------------------------------------------------------

    @staticmethod
    def _ubuntu_displays() -> list[tuple[str, int, int, dict[str, str]]]:
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
    def _ubuntu_xenv(environment: dict[str, str]) -> dict[str, str]:
        # Preserve the known-working minimal environment exactly.
        xenv = {"DISPLAY": environment.get("DISPLAY", "")}
        if environment.get("XAUTHORITY"):
            xenv["XAUTHORITY"] = environment["XAUTHORITY"]
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
    def _ubuntu_write_property(
        cls,
        display: str,
        uid: int,
        gid: int,
        environment: dict[str, str],
        name: str,
        value: int,
    ) -> tuple[bool, str]:
        try:
            completed = subprocess.run(
                [
                    "/usr/bin/xprop",
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
                env=cls._ubuntu_xenv(environment),
                preexec_fn=cls._drop_privileges(uid, gid),
            )
        except (FileNotFoundError, subprocess.TimeoutExpired, OSError) as exc:
            return False, str(exc)

        if completed.returncode != 0:
            return False, (completed.stderr or completed.stdout).strip()
        return True, ""

    @classmethod
    def _ubuntu_read_property(
        cls,
        display: str,
        uid: int,
        gid: int,
        environment: dict[str, str],
        name: str,
    ) -> int | None:
        try:
            completed = subprocess.run(
                ["/usr/bin/xprop", "-display", display, "-root", name],
                check=False,
                capture_output=True,
                text=True,
                timeout=3,
                env=cls._ubuntu_xenv(environment),
                preexec_fn=cls._drop_privileges(uid, gid),
            )
        except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
            return None

        if completed.returncode != 0:
            return None

        match = re.search(r"=\s*(-?\d+)\s*$", completed.stdout)
        return int(match.group(1)) if match else None

    @classmethod
    def _ubuntu_write_all(
        cls,
        properties: tuple[tuple[str, int], ...],
    ) -> tuple[list[str], list[str]]:
        displays = cls._ubuntu_displays()
        applied: list[str] = []
        errors: list[str] = []

        for display, uid, gid, environment in displays:
            display_errors: list[str] = []
            for name, value in properties:
                ok, error = cls._ubuntu_write_property(
                    display, uid, gid, environment, name, value
                )
                if not ok:
                    display_errors.append(f"{name}: {error}")

            if display_errors:
                errors.append(f"{display}: {'; '.join(display_errors)}")
            else:
                applied.append(display)

        return applied, errors

    async def _ubuntu_set_nis_enabled(self, enabled: bool) -> dict:
        value = UBUNTU_SHARP_FILTER_NIS if enabled else UBUNTU_SHARP_FILTER_FSR
        applied, errors = self._ubuntu_write_all(
            (("GAMESCOPE_SHARP_FILTER", value),)
        )

        if not applied:
            error = (
                "No accessible Gamescope session was found"
                if not errors
                else "; ".join(errors)
            )
            return {"success": False, "error": error}

        return {
            "success": True,
            "enabled": enabled,
            "engine": "nis" if enabled else "fsr",
            "displays": applied,
            "errors": errors,
            "steamos": False,
            "ubuntuCompat": True,
        }

    async def _ubuntu_set_sharpness(self, level: int) -> dict:
        raw_value = 20 - (level * 4)
        applied, errors = self._ubuntu_write_all(
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

        return {
            "success": True,
            "level": level,
            "rawValue": raw_value,
            "displays": applied,
            "errors": errors,
        }

    async def _ubuntu_get_status(self) -> dict:
        displays = self._ubuntu_displays()
        if not displays:
            return {
                "success": False,
                "error": "No accessible Gamescope session was found",
                "steamos": False,
                "ubuntuCompat": True,
            }

        nis_enabled = False
        raw_sharpness: int | None = None
        available: list[str] = []

        for display, uid, gid, environment in displays:
            available.append(display)

            engine_value = self._ubuntu_read_property(
                display,
                uid,
                gid,
                environment,
                "GAMESCOPE_SHARP_FILTER",
            )
            if engine_value == UBUNTU_SHARP_FILTER_NIS:
                nis_enabled = True

            for property_name in (
                "GAMESCOPE_SHARPNESS",
                "GAMESCOPE_FSR_SHARPNESS",
            ):
                value = self._ubuntu_read_property(
                    display, uid, gid, environment, property_name
                )
                if value is not None:
                    raw_sharpness = max(0, min(20, value))
                    break

        level = (
            round((20 - raw_sharpness) / 4)
            if raw_sharpness is not None
            else None
        )

        return {
            "success": True,
            "enabled": nis_enabled,
            "requested": nis_enabled,
            "engine": "nis" if nis_enabled else "fsr",
            "level": level,
            "rawValue": raw_sharpness,
            "displays": available,
            "diagnostics": [],
            "steamos": False,
            "ubuntuCompat": True,
            "enforcing": False,
        }

    # ------------------------------------------------------------------
    # STEAMOS
    # Separate experimental path; no code below is used on Ubuntu.
    # ------------------------------------------------------------------

    @staticmethod
    def _xprop_binary() -> str | None:
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
    def _read_proc_environment(proc: Path) -> dict[str, str]:
        environment: dict[str, str] = {}
        try:
            entries = (proc / "environ").read_bytes().split(b"\0")
        except (FileNotFoundError, PermissionError, ProcessLookupError, OSError):
            return environment

        for entry in entries:
            if b"=" not in entry:
                continue
            key, value = entry.split(b"=", 1)
            environment[key.decode("ascii", "ignore")] = value.decode(
                "utf-8", "ignore"
            )
        return environment

    @staticmethod
    def _ppid(proc: Path) -> int | None:
        try:
            for line in (proc / "status").read_text(
                encoding="utf-8", errors="ignore"
            ).splitlines():
                if line.startswith("PPid:"):
                    return int(line.split(":", 1)[1].strip())
        except (
            FileNotFoundError,
            PermissionError,
            ProcessLookupError,
            OSError,
            ValueError,
        ):
            pass
        return None

    @staticmethod
    def _proc_name(proc: Path) -> str:
        try:
            return (proc / "comm").read_text(
                encoding="utf-8", errors="ignore"
            ).strip()
        except (FileNotFoundError, PermissionError, ProcessLookupError, OSError):
            return ""

    @staticmethod
    def _proc_cmdline(proc: Path) -> list[str]:
        try:
            return [
                part.decode("utf-8", "ignore")
                for part in (proc / "cmdline").read_bytes().split(b"\0")
                if part
            ]
        except (FileNotFoundError, PermissionError, ProcessLookupError, OSError):
            return []

    @classmethod
    def _steamos_env_displays(
        cls,
    ) -> list[tuple[str, int, int, dict[str, str], str]]:
        displays: dict[str, tuple[int, int, dict[str, str], str]] = {}

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
            except (FileNotFoundError, PermissionError, ProcessLookupError, OSError):
                continue

            environment = cls._read_proc_environment(proc)
            desktop = environment.get("XDG_CURRENT_DESKTOP", "").lower()
            if "gamescope" not in desktop and not environment.get(
                "GAMESCOPE_WAYLAND_DISPLAY"
            ):
                continue

            display = environment.get("DISPLAY", "")
            if DISPLAY_RE.fullmatch(display):
                displays[display] = (
                    stat.st_uid,
                    stat.st_gid,
                    environment,
                    "environment",
                )

        return [
            (display, *details)
            for display, details in sorted(
                displays.items(),
                key=lambda item: int(item[0][1:].split(".", 1)[0]),
            )
        ]

    @classmethod
    def _steamos_xwaylands(
        cls,
    ) -> list[tuple[str, int, int, dict[str, str], str]]:
        displays: dict[str, tuple[int, int, dict[str, str], str]] = {}

        try:
            proc_entries = list(Path("/proc").iterdir())
        except OSError:
            return []

        for proc in proc_entries:
            if not proc.name.isdigit():
                continue

            name = cls._proc_name(proc).lower()
            cmdline = cls._proc_cmdline(proc)
            argv0 = Path(cmdline[0]).name.lower() if cmdline else ""

            if "xwayland" not in name and "xwayland" not in argv0:
                continue

            try:
                stat = proc.stat()
                if stat.st_uid == 0:
                    continue
            except (FileNotFoundError, PermissionError, ProcessLookupError, OSError):
                continue

            display = next(
                (arg for arg in cmdline[1:] if DISPLAY_RE.fullmatch(arg)),
                "",
            )
            if not display:
                continue

            environment = cls._read_proc_environment(proc)

            parent_is_gamescope = False
            parent = cls._ppid(proc)
            if parent:
                parent_proc = Path("/proc") / str(parent)
                parent_name = cls._proc_name(parent_proc).lower()
                parent_cmd = " ".join(cls._proc_cmdline(parent_proc)).lower()
                parent_is_gamescope = (
                    "gamescope" in parent_name or "gamescope" in parent_cmd
                )

            wayland_marker = " ".join(
                (
                    environment.get("WAYLAND_DISPLAY", ""),
                    environment.get("GAMESCOPE_WAYLAND_DISPLAY", ""),
                )
            ).lower()

            if not parent_is_gamescope and "gamescope" not in wayland_marker:
                continue

            if "-auth" in cmdline:
                try:
                    auth = cmdline[cmdline.index("-auth") + 1]
                    if auth:
                        environment["XAUTHORITY"] = auth
                except (ValueError, IndexError):
                    pass

            environment["DISPLAY"] = display
            displays[display] = (
                stat.st_uid,
                stat.st_gid,
                environment,
                "xwayland",
            )

        return [
            (display, *details)
            for display, details in sorted(
                displays.items(),
                key=lambda item: int(item[0][1:].split(".", 1)[0]),
            )
        ]

    @classmethod
    def _steamos_targets(
        cls,
    ) -> list[tuple[str, int, int, dict[str, str], str]]:
        merged: dict[str, tuple[int, int, dict[str, str], str]] = {}

        for display, uid, gid, environment, source in cls._steamos_env_displays():
            merged[display] = (uid, gid, environment, source)

        for display, uid, gid, environment, source in cls._steamos_xwaylands():
            merged[display] = (uid, gid, environment, source)

        return [
            (display, *details)
            for display, details in sorted(
                merged.items(),
                key=lambda item: int(item[0][1:].split(".", 1)[0]),
            )
        ]

    @staticmethod
    def _steamos_xenv(environment: dict[str, str]) -> dict[str, str]:
        xenv = os.environ.copy()
        xenv["DISPLAY"] = environment.get("DISPLAY", "")
        if environment.get("XAUTHORITY"):
            xenv["XAUTHORITY"] = environment["XAUTHORITY"]
        else:
            xenv.pop("XAUTHORITY", None)
        return xenv

    @classmethod
    def _steamos_write_property(
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
                env=cls._steamos_xenv(environment),
                preexec_fn=cls._drop_privileges(uid, gid),
            )
        except (FileNotFoundError, subprocess.TimeoutExpired, OSError) as exc:
            return False, str(exc)

        if completed.returncode != 0:
            return False, (completed.stderr or completed.stdout).strip()
        return True, ""

    @classmethod
    def _steamos_read_property(
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
                env=cls._steamos_xenv(environment),
                preexec_fn=cls._drop_privileges(uid, gid),
            )
        except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
            return None

        if completed.returncode != 0:
            return None

        match = re.search(r"=\s*(-?\d+)\s*$", completed.stdout)
        return int(match.group(1)) if match else None

    @classmethod
    def _steamos_write_to_targets(
        cls,
        targets: list[tuple[str, int, int, dict[str, str], str]],
        properties: tuple[tuple[str, int], ...],
    ) -> tuple[list[str], list[str]]:
        applied: list[str] = []
        errors: list[str] = []

        for display, uid, gid, environment, _source in targets:
            display_errors: list[str] = []
            for name, value in properties:
                ok, error = cls._steamos_write_property(
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
    def _steamos_properties(enabled: bool) -> tuple[tuple[str, int], ...]:
        if enabled:
            return (
                ("GAMESCOPE_NEW_SCALING_SCALER", NEW_SCALER_AUTO),
                ("GAMESCOPE_NEW_SCALING_FILTER", NEW_SCALING_NIS),
                ("GAMESCOPE_SCALING_FILTER", LEGACY_SCALING_NIS),
                ("GAMESCOPE_SHARP_FILTER", UBUNTU_SHARP_FILTER_NIS),
            )

        return (
            ("GAMESCOPE_NEW_SCALING_SCALER", NEW_SCALER_AUTO),
            ("GAMESCOPE_NEW_SCALING_FILTER", NEW_SCALING_FSR),
            ("GAMESCOPE_SCALING_FILTER", LEGACY_SCALING_FSR),
            ("GAMESCOPE_SHARP_FILTER", UBUNTU_SHARP_FILTER_FSR),
        )

    async def _force_steamos_nis_transition(
        self,
    ) -> tuple[list[str], list[str]]:
        targets = self._steamos_targets()
        if not targets:
            return [], []

        self._steamos_write_to_targets(
            targets,
            (
                ("GAMESCOPE_NEW_SCALING_SCALER", NEW_SCALER_AUTO),
                ("GAMESCOPE_NEW_SCALING_FILTER", NEW_SCALING_LINEAR),
                ("GAMESCOPE_SCALING_FILTER", LEGACY_SCALING_LINEAR),
            ),
        )

        await asyncio.sleep(TRANSITION_DELAY)

        return self._steamos_write_to_targets(
            targets,
            self._steamos_properties(True),
        )

    @classmethod
    def _steamos_state_on_target(
        cls,
        display: str,
        uid: int,
        gid: int,
        environment: dict[str, str],
        source: str,
    ) -> dict:
        compat = cls._steamos_read_property(
            display, uid, gid, environment, "GAMESCOPE_SHARP_FILTER"
        )
        legacy = cls._steamos_read_property(
            display, uid, gid, environment, "GAMESCOPE_SCALING_FILTER"
        )
        modern = cls._steamos_read_property(
            display, uid, gid, environment, "GAMESCOPE_NEW_SCALING_FILTER"
        )
        scaler = cls._steamos_read_property(
            display, uid, gid, environment, "GAMESCOPE_NEW_SCALING_SCALER"
        )
        fsr_feedback = cls._steamos_read_property(
            display, uid, gid, environment, "GAMESCOPE_FSR_FEEDBACK"
        )
        server_id = cls._steamos_read_property(
            display, uid, gid, environment, "GAMESCOPE_XWAYLAND_SERVER_ID"
        )

        if modern is not None:
            display_nis = modern == NEW_SCALING_NIS
        elif legacy is not None:
            display_nis = legacy == LEGACY_SCALING_NIS
        else:
            display_nis = compat == UBUNTU_SHARP_FILTER_NIS

        return {
            "display": display,
            "source": source,
            "serverId": server_id,
            "legacy": legacy,
            "modern": modern,
            "compat": compat,
            "scaler": scaler,
            "fsrFeedback": fsr_feedback,
            "displayNis": display_nis,
        }

    def _start_enforcer(self) -> None:
        if not self._is_steamos():
            return

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
        fast_passes = FAST_ENFORCE_PASSES

        try:
            while self._nis_requested and self._is_steamos():
                delay = (
                    FAST_ENFORCE_INTERVAL
                    if fast_passes > 0
                    else STEADY_ENFORCE_INTERVAL
                )
                await asyncio.sleep(delay)

                if not self._nis_requested:
                    break

                targets = self._steamos_targets()
                needs_reapply = fast_passes > 0

                for target in targets:
                    state = self._steamos_state_on_target(*target)
                    if not state["displayNis"] or state["fsrFeedback"] == 1:
                        needs_reapply = True
                        break

                if needs_reapply and targets:
                    self._steamos_write_to_targets(
                        targets,
                        self._steamos_properties(True),
                    )

                if fast_passes > 0:
                    fast_passes -= 1

        except asyncio.CancelledError:
            raise
        except Exception:
            decky.logger.exception(
                "Sharp Filter Selector: SteamOS NIS enforcement loop failed"
            )

    async def _steamos_set_nis_enabled(self, enabled: bool) -> dict:
        self._nis_requested = enabled

        if not enabled:
            await self._stop_enforcer()

        if enabled:
            applied, errors = await self._force_steamos_nis_transition()
        else:
            applied, errors = self._steamos_write_to_targets(
                self._steamos_targets(),
                self._steamos_properties(False),
            )

        if enabled:
            self._start_enforcer()

        if not applied:
            error = (
                "No accessible Gamescope/Xwayland target was found"
                if not errors
                else "; ".join(errors)
            )
            return {
                "success": False,
                "error": error,
                "enabled": enabled,
                "engine": "nis" if enabled else "fsr",
                "steamos": True,
            }

        return {
            "success": True,
            "enabled": enabled,
            "engine": "nis" if enabled else "fsr",
            "displays": applied,
            "errors": errors,
            "steamos": True,
            "enforcing": bool(
                self._enforce_task and not self._enforce_task.done()
            ),
        }

    async def _steamos_set_sharpness(self, level: int) -> dict:
        raw_value = 20 - (level * 4)
        applied, errors = self._steamos_write_to_targets(
            self._steamos_targets(),
            (
                ("GAMESCOPE_SHARPNESS", raw_value),
                ("GAMESCOPE_FSR_SHARPNESS", raw_value),
            ),
        )

        if not applied:
            error = (
                "No accessible Gamescope/Xwayland target was found"
                if not errors
                else "; ".join(errors)
            )
            return {"success": False, "error": error}

        return {
            "success": True,
            "level": level,
            "rawValue": raw_value,
            "displays": applied,
            "errors": errors,
        }

    async def _steamos_get_status(self) -> dict:
        targets = self._steamos_targets()
        if not targets:
            return {
                "success": False,
                "error": "No accessible Gamescope/Xwayland target was found",
                "requested": self._nis_requested,
                "steamos": True,
            }

        nis_enabled = False
        raw_sharpness: int | None = None
        available: list[str] = []
        diagnostics: list[dict] = []

        for target in targets:
            display, uid, gid, environment, source = target
            state = self._steamos_state_on_target(*target)
            available.append(display)

            display_nis = state["displayNis"]
            if state["fsrFeedback"] == 1:
                display_nis = False
            nis_enabled = nis_enabled or display_nis

            for property_name in (
                "GAMESCOPE_SHARPNESS",
                "GAMESCOPE_FSR_SHARPNESS",
            ):
                value = self._steamos_read_property(
                    display, uid, gid, environment, property_name
                )
                if value is not None:
                    raw_sharpness = max(0, min(20, value))
                    break

            diagnostics.append(
                {
                    "display": display,
                    "source": source,
                    "serverId": state["serverId"],
                    "legacyFilter": state["legacy"],
                    "newFilter": state["modern"],
                    "compatFilter": state["compat"],
                    "newScaler": state["scaler"],
                    "fsrFeedback": state["fsrFeedback"],
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
            "steamos": True,
            "enforcing": bool(
                self._enforce_task and not self._enforce_task.done()
            ),
        }

    # ------------------------------------------------------------------
    # DECKY API
    # ------------------------------------------------------------------

    async def set_nis_enabled(self, enabled: bool) -> dict:
        if not isinstance(enabled, bool):
            return {"success": False, "error": "Invalid NIS state"}

        if self._is_steamos():
            return await self._steamos_set_nis_enabled(enabled)

        return await self._ubuntu_set_nis_enabled(enabled)

    async def set_nis_sharpness(self, level: int) -> dict:
        if (
            isinstance(level, bool)
            or not isinstance(level, int)
            or not SHARPNESS_MIN <= level <= SHARPNESS_MAX
        ):
            return {
                "success": False,
                "error": "Sharpness must be between 0 and 5",
            }

        if self._is_steamos():
            return await self._steamos_set_sharpness(level)

        return await self._ubuntu_set_sharpness(level)

    async def get_status(self) -> dict:
        if self._is_steamos():
            return await self._steamos_get_status()

        return await self._ubuntu_get_status()

    async def _main(self):
        decky.logger.info(
            "Sharp Filter Selector loaded (SteamOS=%s, Ubuntu compatibility path=%s)",
            self._is_steamos(),
            not self._is_steamos(),
        )

    async def _unload(self):
        self._nis_requested = False
        await self._stop_enforcer()
        decky.logger.info("Sharp Filter Selector unloaded")
