"""Behavioral fake-Xwayland tests. Never touch the user's display or filters."""
import asyncio
import io
from contextlib import ExitStack
import logging
import subprocess
import threading
import types
import unittest
from unittest.mock import patch

from test_hdr_visibility import backend

backend.decky.logger = logging.getLogger("sharp-tests")
SID = "GAMESCOPE_XWAYLAND_SERVER_ID"
FILTER = "GAMESCOPE_NEW_SCALING_FILTER"
SCALER = "GAMESCOPE_NEW_SCALING_SCALER"


class Roots:
    def __init__(self, sgsr=True):
        self.plugin = backend.Plugin()
        self.plugin._is_steamos = lambda: True
        self.plugin._gamescope_capabilities = lambda: {"pid": 42, "supportsSGSR": sgsr}
        # QAM is intentionally not the lowest display or first item.
        self.states = {":1": {SID: 1, FILTER: 0, SCALER: 0},
                       ":7": {SID: 0, FILTER: 2, SCALER: 2}}
        self.writes = []
        self.plugin._steamos_targets = lambda: [
            (d, 1000, 1000, {"DISPLAY": d}, "xwayland") for d in self.states]
        self.plugin._steamos_read_qam_state = lambda target: dict(self.states[target[0]])
        self.plugin._steamos_write_to_targets = self.write
        self.plugin._hdr_state = lambda: {"hdrInput": False}

    def write(self, targets, properties):
        for target in targets:
            for name, value in properties:
                self.writes.append((target[0], name, value))
                self.states[target[0]][name] = value
        return [t[0] for t in targets], []

    def sync(self):
        self.plugin._steamos_sync_qam_once()


class SteamOSBridgeTests(unittest.TestCase):
    def test_qam_sharp_becomes_sgsr_on_all_roots_and_preserves_scaler(self):
        roots = Roots()
        roots.sync()
        self.assertEqual(roots.states[":7"][SCALER], 2)
        self.assertTrue(all(s[FILTER] == 5 and s[SCALER] == 2 for s in roots.states.values()))
        self.assertNotIn((":7", SCALER, 2), roots.writes)
        self.assertTrue(all(name in (FILTER, SCALER) for _, name, _ in roots.writes))

    def test_complete_filter_scaler_and_override_matrix(self):
        for selected in range(6):
            for scaler in range(5):
                for override, expected in ((None, 5 if selected == 2 else selected),
                                           ("nis", 3), ("fsr", 2)):
                    with self.subTest(filter=selected, scaler=scaler, override=override):
                        roots = Roots()
                        roots.states[":7"].update({FILTER: selected, SCALER: scaler})
                        roots.plugin._nis_requested = override == "nis"
                        roots.plugin._fsr_override_requested = override == "fsr"
                        roots.sync()
                        for state in roots.states.values():
                            self.assertEqual((state[FILTER], state[SCALER]), (expected, scaler))

    def test_no_rewrites_when_roots_agree(self):
        roots = Roots()
        roots.sync()
        roots.writes.clear()
        for _ in range(4):
            roots.sync()
        self.assertEqual(roots.writes, [])

    def test_changing_qam_after_sharp_is_not_latched(self):
        roots = Roots()
        for selected, expected in ((2, 5), (0, 0), (4, 4), (1, 1), (2, 5)):
            roots.states[":7"][FILTER] = selected
            roots.sync()
            self.assertTrue(all(s[FILTER] == expected for s in roots.states.values()))

    def test_missing_or_ambiguous_qam_root_never_guesses(self):
        for first_id, second_id in ((1, 2), (None, None), (0, 0)):
            roots = Roots()
            roots.states[":1"][SID], roots.states[":7"][SID] = first_id, second_id
            roots.sync()
            self.assertEqual(roots.writes, [])

    def test_unidentified_root_is_not_written(self):
        roots = Roots()
        roots.states[":1"][SID] = None
        roots.sync()
        self.assertFalse(any(d == ":1" for d, _, _ in roots.writes))

    def test_invalid_filter_never_writes(self):
        for value in (None, -1, 6, 100):
            roots = Roots()
            roots.states[":7"][FILTER] = value
            roots.sync()
            self.assertEqual(roots.writes, [])

    def test_invalid_scaler_is_not_mirrored(self):
        for value in (None, -1, 5, 100):
            roots = Roots()
            roots.states[":7"][SCALER] = value
            roots.sync()
            self.assertTrue(all(name != SCALER for _, name, _ in roots.writes))
            self.assertEqual(roots.states[":7"][FILTER], 5)

    def test_ubuntu_and_old_gamescope_are_inert(self):
        for steamos, sgsr in ((False, True), (False, False), (True, False)):
            roots = Roots(sgsr)
            roots.plugin._is_steamos = lambda: steamos
            roots.plugin._steamos_targets = lambda: self.fail("Entered SteamOS bridge")
            roots.sync()

    def test_session_can_disappear_and_return(self):
        roots = Roots()
        roots.plugin._steamos_targets = lambda: []
        roots.sync()
        self.assertEqual(roots.writes, [])
        roots.plugin._steamos_targets = lambda: [
            (d, 1000, 1000, {}, "xwayland") for d in roots.states]
        roots.sync()
        self.assertEqual(roots.states[":7"][FILTER], 5)

    def test_failed_writes_are_retried_next_pass(self):
        roots = Roots()
        roots.plugin._steamos_write_to_targets = lambda *args: ([], ["Xwayland unavailable"])
        with self.assertLogs("sharp-tests", level="WARNING"):
            roots.sync()
        self.assertEqual(roots.states[":7"][FILTER], 2)
        roots.plugin._steamos_write_to_targets = roots.write
        roots.sync()
        self.assertEqual(roots.states[":7"][FILTER], 5)

    def test_authenticated_batch_read_and_missing_properties(self):
        target = (":7", 1000, 1000, {"DISPLAY": ":7", "XAUTHORITY": "/session/auth"}, "xwayland")
        output = f"{SID}(CARDINAL) = 0\n{FILTER}(CARDINAL) = 2\n{SCALER}: no such atom on any window.\n"
        completed = subprocess.CompletedProcess([], 0, output, "")
        with patch.object(backend.subprocess, "run", return_value=completed) as run:
            result = backend.Plugin._steamos_read_qam_state(target)
        self.assertEqual(result, {SID: 0, FILTER: 2, SCALER: None})
        self.assertEqual(run.call_args.kwargs["env"]["XAUTHORITY"], "/session/auth")
        self.assertNotIn("preexec_fn", run.call_args.kwargs)
        self.assertEqual(run.call_args.args[0][-3:], [SID, FILTER, SCALER])

    def test_failed_batch_read_is_unknown(self):
        target = (":7", 1000, 1000, {}, "xwayland")
        for failure in (OSError("gone"), subprocess.TimeoutExpired("xprop", 3)):
            with patch.object(backend.subprocess, "run", side_effect=failure):
                self.assertEqual(backend.Plugin._steamos_read_qam_state(target), dict.fromkeys((SID, FILTER, SCALER)))


class OverrideTests(unittest.IsolatedAsyncioTestCase):
    async def test_hdr_fallback_remains_gamescopes_decision(self):
        roots = Roots()
        roots.plugin._hdr_state = lambda: {"hdrInput": True}
        result = await roots.plugin.set_nis_enabled(False)
        self.assertEqual(result["selectedEngine"], "sgsr")
        self.assertEqual(result["engine"], "fsr")
        self.assertTrue(all(s[FILTER] == 5 for s in roots.states.values()))

    async def test_modern_override_cycle_never_resets_scaler_or_uses_legacy(self):
        roots = Roots()
        plugin = roots.plugin
        for method, enabled, expected in ((plugin.set_nis_enabled, True, 3),
                                          (plugin.set_fsr_override, True, 2),
                                          (plugin.set_fsr_override, False, 5),
                                          (plugin.set_nis_enabled, True, 3),
                                          (plugin.set_nis_enabled, False, 5)):
            result = await method(enabled)
            self.assertTrue(result["success"])
            self.assertTrue(all(s[FILTER] == expected for s in roots.states.values()))
            self.assertEqual(roots.states[":7"][SCALER], 2)
        self.assertTrue(all(name == FILTER for _, name, _ in roots.writes))
        self.assertIsNone(plugin._enforce_task)
        self.assertIsNone(plugin._fsr_enforce_task)

    async def test_explicit_overrides_are_exclusive_and_bridge_retains_them(self):
        roots = Roots()
        await roots.plugin.set_nis_enabled(True)
        await roots.plugin.set_fsr_override(True)
        self.assertFalse(roots.plugin._nis_requested)
        roots.states[":7"][FILTER] = 0
        roots.sync()
        self.assertEqual(roots.states[":7"][FILTER], 2)
        await roots.plugin.set_nis_enabled(True)
        self.assertFalse(roots.plugin._fsr_override_requested)
        roots.states[":7"][FILTER] = 2
        roots.sync()
        self.assertEqual(roots.states[":7"][FILTER], 3)

    async def test_old_steamos_nis_transition_unchanged(self):
        roots = Roots(False)
        roots.plugin._start_enforcer = lambda: None
        await roots.plugin.set_nis_enabled(True)
        for display in roots.states:
            actual = [(name, value) for d, name, value in roots.writes if d == display]
            self.assertEqual(actual, [(SCALER, 0), (FILTER, 0), ("GAMESCOPE_SCALING_FILTER", 0),
                                      (SCALER, 0), (FILTER, 3), ("GAMESCOPE_SCALING_FILTER", 4),
                                      ("GAMESCOPE_SHARP_FILTER", 1)])

    async def test_rejected_fsr_on_old_gamescope_does_not_mutate_flags(self):
        roots = Roots(False)
        roots.plugin._nis_requested = True
        result = await roots.plugin.set_fsr_override(True)
        self.assertFalse(result["success"])
        self.assertTrue(roots.plugin._nis_requested)
        self.assertFalse(roots.plugin._fsr_override_requested)
        self.assertEqual(roots.writes, [])

    async def test_api_waits_for_inflight_bridge(self):
        roots = Roots()
        await roots.plugin._steamos_sync_lock.acquire()
        task = asyncio.create_task(roots.plugin.set_nis_enabled(True))
        await asyncio.sleep(0)
        self.assertFalse(task.done())
        self.assertEqual(roots.writes, [])
        roots.plugin._steamos_sync_lock.release()
        await task
        self.assertEqual(roots.states[":7"][FILTER], 3)

    async def test_lifecycle_starts_only_matching_platform_and_cleans_up(self):
        for steamos in (False, True):
            plugin = backend.Plugin()
            plugin._is_steamos = lambda: steamos
            await plugin._main()
            self.assertEqual(plugin._ubuntu_sync_task is not None, not steamos)
            self.assertEqual(plugin._steamos_sync_task is not None, steamos)
            await plugin._unload()
            self.assertIsNone(plugin._steamos_sync_task)
            self.assertIsNone(plugin._ubuntu_sync_task)

    async def test_stop_drains_worker_before_returning(self):
        roots = Roots()
        started, finish = threading.Event(), threading.Event()
        writes = []
        def slow_pass():
            started.set()
            finish.wait(3)
            writes.append("completed")
        roots.plugin._steamos_sync_qam_once = slow_pass
        with patch.object(backend, "STEAMOS_SYNC_INTERVAL", 0.001):
            roots.plugin._start_steamos_sync()
            await asyncio.to_thread(started.wait, 3)
            stopping = asyncio.create_task(roots.plugin._stop_steamos_sync())
            await asyncio.sleep(0.01)
            self.assertFalse(stopping.done())
            finish.set()
            await stopping
        self.assertEqual(writes, ["completed"])

    async def test_exception_does_not_kill_future_bridge_passes(self):
        roots = Roots()
        reached = threading.Event()
        attempts = []
        def pass_once():
            attempts.append(1)
            if len(attempts) == 1:
                raise OSError("Xwayland restarted")
            reached.set()
        roots.plugin._steamos_sync_qam_once = pass_once
        with self.assertLogs("sharp-tests", level="ERROR"):
            with patch.object(backend, "STEAMOS_SYNC_INTERVAL", 0.001):
                roots.plugin._start_steamos_sync()
                self.assertTrue(await asyncio.to_thread(reached.wait, 3))
                await roots.plugin._stop_steamos_sync()
        self.assertGreaterEqual(len(attempts), 2)

    async def test_failing_inflight_worker_cannot_swallow_shutdown(self):
        roots = Roots()
        started, finish = threading.Event(), threading.Event()
        def fail_pass():
            started.set()
            finish.wait(3)
            raise OSError("Xwayland disappeared during unload")
        roots.plugin._steamos_sync_qam_once = fail_pass
        with self.assertLogs("sharp-tests", level="ERROR"):
            with patch.object(backend, "STEAMOS_SYNC_INTERVAL", 0.001):
                roots.plugin._start_steamos_sync()
                self.assertTrue(await asyncio.to_thread(started.wait, 3))
                stopping = asyncio.create_task(roots.plugin._stop_steamos_sync())
                await asyncio.sleep(0.01)
                finish.set()
                await asyncio.wait_for(stopping, 2)
        self.assertIsNone(roots.plugin._steamos_sync_task)


class UbuntuRegressionTests(unittest.IsolatedAsyncioTestCase):
    async def test_ubuntu_overrides_keep_existing_property_contract(self):
        for sgsr in (False, True):
            plugin = backend.Plugin()
            plugin._is_steamos = lambda: False
            plugin._gamescope_capabilities = lambda: {"supportsSGSR": sgsr}
            plugin._hdr_state = lambda: {"hdrInput": False}
            writes = []
            plugin._ubuntu_write_all = lambda props: (writes.append(props) or [":0"], [])
            plugin._steamos_targets = lambda: self.fail("Ubuntu entered SteamOS path")
            await plugin.set_nis_enabled(True)
            self.assertEqual(writes[-1], (("GAMESCOPE_SHARP_FILTER", 1), (FILTER, 3)))
            await plugin.set_nis_enabled(False)
            self.assertEqual(writes[-1], (("GAMESCOPE_SHARP_FILTER", 0), (FILTER, 5)) if sgsr else (("GAMESCOPE_SHARP_FILTER", 0),))
            self.assertFalse(any(name == SCALER for props in writes for name, _ in props))

    async def test_ubuntu_qam_loop_still_translates_and_preserves_scaler(self):
        plugin = backend.Plugin()
        active = [True]
        plugin._is_steamos = lambda: not active[0]
        plugin._gamescope_capabilities = lambda: {"supportsSGSR": True}
        displays = [(":3", 1000, 1000, {}), (":9", 1000, 1000, {})]
        states = {":3": {SID: 1, FILTER: 0, SCALER: 0}, ":9": {SID: 0, FILTER: 2, SCALER: 4}}
        plugin._ubuntu_displays = lambda: displays
        plugin._ubuntu_read_properties = lambda d, *args: states[d]
        writes = []
        def write(d, u, g, env, name, value):
            writes.append((d, name, value))
            active[0] = False
            return True, ""
        plugin._ubuntu_write_property = write
        with patch.object(backend, "UBUNTU_SYNC_INTERVAL", 0):
            await plugin._ubuntu_sync_qam_loop()
        self.assertIn((":9", FILTER, 5), writes)
        self.assertIn((":3", SCALER, 4), writes)
        self.assertNotIn((":9", SCALER, 0), writes)


class CapabilityProbeTests(unittest.TestCase):
    def probe(self, help_text, binary=b"", denied=False):
        completed = [subprocess.CompletedProcess([], 0, help_text, ""),
                     subprocess.CompletedProcess([], 0, "gamescope version 3.16.30.1+", "")]
        with patch.object(backend.subprocess, "run", side_effect=completed) as run:
            with patch.object(backend.os, "readlink", return_value="/usr/bin/gamescope"):
                with patch("builtins.open", side_effect=PermissionError if denied else lambda *a, **kw: io.BytesIO(binary)):
                    result = backend.Plugin._probe_gamescope_process(42, 1000, 1000, {"LD_PRELOAD": "unwanted"})
        self.assertEqual(run.call_args_list[0].args[0], ["/proc/42/exe", "--help"])
        self.assertNotIn("LD_PRELOAD", run.call_args.kwargs["env"])
        self.assertEqual(result["version"], "3.16.30.1")
        return result

    def test_steam_os_help_detects_sgsr_without_version_guessing(self):
        result = self.probe("upscaler filter (linear, nearest, fsr, nis, pixel, sgsr)")
        self.assertTrue(result["supportsSGSR"])
        self.assertEqual(result["evidence"], "help")

    def test_binary_fallback_when_help_omits_sgsr(self):
        result = self.probe("upscaler filter", b"SGSR shader\x00Snapdragon Game Super Resolution")
        self.assertTrue(result["supportsSGSR"])
        self.assertEqual(result["evidence"], "binary")

    def test_version_alone_or_unknown_binary_never_enables_sgsr(self):
        self.assertFalse(self.probe("upscaler filter (linear, fsr, nis)")["supportsSGSR"])
        self.assertFalse(self.probe("", denied=True)["supportsSGSR"])

    def test_absent_session_invalidates_previous_cache(self):
        plugin = backend.Plugin()
        plugin._gamescope_probe_cache = {"pid": 42, "supportsSGSR": True}
        plugin._active_gamescope_candidates = lambda: []
        result = plugin._gamescope_capabilities()
        self.assertFalse(result["supportsSGSR"])
        self.assertIsNone(plugin._gamescope_probe_cache)


class RestrictedProcTests(unittest.TestCase):
    def identity(self, argv=None, owner=0, mode=0o755, changed=999, elf=b"\x7fELF", argv_path="/usr/bin/gamescope"):
        def metadata(path, *args, **kwargs):
            return types.SimpleNamespace(st_mode=backend.stat.S_IFREG | mode,
                st_uid=owner, st_ctime=changed, st_mtime=changed,
                st_dev=1, st_ino=42, st_ctime_ns=changed * 10**9,
                st_mtime_ns=changed * 10**9)
        def read_text(path, *args, **kwargs):
            if str(path) == "/proc/stat":
                return "btime 1000\n"
            # field 22 is starttime; the comm field may contain ')' and spaces.
            return "42 (gamescope) worker) " + " ".join(["S"] + ["0"] * 18 + ["1000"])
        with ExitStack() as stack:
            stack.enter_context(patch.object(backend.Plugin, "_proc_cmdline", return_value=argv if argv is not None else [argv_path]))
            stack.enter_context(patch.object(backend.Path, "resolve", return_value=backend.Path(argv_path)))
            stack.enter_context(patch.object(backend.Path, "stat", metadata))
            stack.enter_context(patch.object(backend.Path, "read_text", read_text))
            stack.enter_context(patch.object(backend.Path, "open", return_value=io.BytesIO(elf)))
            stack.enter_context(patch.object(backend.os, "sysconf", return_value=100))
            return backend.Plugin._steamos_observed_executable(42)

    def test_accepts_only_observed_unchanged_root_owned_elf(self):
        result = self.identity()
        self.assertEqual(result[0], "/usr/bin/gamescope")
        self.assertEqual(result[1][-1], 1000)

    def test_relative_argv_never_uses_path_lookup(self):
        with patch.object(backend.shutil, "which", side_effect=AssertionError("PATH must not be consulted")):
            self.assertIsNone(self.identity(argv=["gamescope"]))
            self.assertIsNone(self.identity(argv=[]))

    def test_changed_or_recent_binary_is_rejected(self):
        for changed in (1009, 1010, 1020):
            self.assertIsNone(self.identity(changed=changed))

    def test_non_root_or_writable_or_non_elf_is_rejected(self):
        self.assertIsNone(self.identity(owner=1000))
        self.assertIsNone(self.identity(mode=0o775))
        self.assertIsNone(self.identity(mode=0o777))
        self.assertIsNone(self.identity(elf=b"#!/b"))
        self.assertIsNone(self.identity(argv_path="/usr/bin/another-program"))

    def restricted_probe(self, *, steamos=True, changed_during_probe=False):
        identity = ("/usr/bin/gamescope", (1, 42, 999, 999, 1000))
        snapshots = [identity, None if changed_during_probe else identity]
        completed = [subprocess.CompletedProcess([], 0, "filter (fsr, nis, sgsr)", ""),
                     subprocess.CompletedProcess([], 0, "gamescope version 3.16.30.1+", "")]
        with ExitStack() as stack:
            stack.enter_context(patch.object(backend.Plugin, "_is_steamos", return_value=steamos))
            stack.enter_context(patch.object(backend.os, "readlink", side_effect=PermissionError(13, "restricted")))
            observed = stack.enter_context(patch.object(backend.Plugin, "_steamos_observed_executable", side_effect=snapshots))
            run = stack.enter_context(patch.object(backend.subprocess, "run", side_effect=completed))
            result = backend.Plugin._probe_gamescope_process(42, 1000, 1000, {})
        return result, run, observed

    def test_steam_os_permission_failure_probes_exact_observed_path(self):
        result, run, observed = self.restricted_probe()
        self.assertTrue(result["supportsSGSR"])
        self.assertEqual(result["evidence"], "process-argv-help")
        self.assertEqual(result["executableEvidence"], "process-argv-unchanged")
        self.assertEqual(observed.call_count, 2)
        self.assertEqual(run.call_args_list[0].args[0], ["/usr/bin/gamescope", "--help"])

    def test_replacement_during_probe_cannot_claim_sgsr(self):
        result, _, _ = self.restricted_probe(changed_during_probe=True)
        self.assertFalse(result["supportsSGSR"])
        self.assertEqual(result["evidence"], "none")
        self.assertIsNone(result["version"])
        self.assertIn("changed", result["errors"][-1])

    def test_ubuntu_uses_original_proc_executable_probe(self):
        result, run, observed = self.restricted_probe(steamos=False)
        self.assertTrue(result["supportsSGSR"])
        observed.assert_not_called()
        self.assertEqual(run.call_args_list[0].args[0], ["/proc/42/exe", "--help"])
