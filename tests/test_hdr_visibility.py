"""Offline tests: no X11 writes, no filter changes and no running Decky needed."""
import asyncio
import importlib.util
from pathlib import Path
import sys
import types
import unittest

sys.modules.setdefault("decky", types.ModuleType("decky"))
spec = importlib.util.spec_from_file_location("sharp_backend", Path(__file__).resolve().parents[1] / "main.py")
backend = importlib.util.module_from_spec(spec)
spec.loader.exec_module(backend)


class HDRVisibilityTests(unittest.TestCase):
    def capabilities(self, app, output, sgsr=True):
        plugin = backend.Plugin()
        plugin._gamescope_capabilities = lambda: {"pid": 42, "supportsSGSR": sgsr}
        plugin._is_steamos = lambda: False
        plugin._session_property_values = lambda key: app if key == "GAMESCOPE_COLOR_APP_WANTS_HDR_FEEDBACK" else output
        return asyncio.run(plugin.get_capabilities())

    def test_visibility_matrix(self):
        for output in ([], [0], [1]):
            for app, known, hdr in (([], False, False), ([0], True, False),
                                    ([1], True, True), ([0, 0], True, False),
                                    ([1, 1], True, True), ([0, 1], False, False),
                                    ([2], False, False), ([1, 2], False, False)):
                with self.subTest(app=app, output=output):
                    result = self.capabilities(app, output)
                    self.assertEqual(result["hdrInputKnown"], known)
                    self.assertEqual(result["hdrInput"], hdr)
                    self.assertEqual(result["showFsrOverride"], not hdr)
                    self.assertEqual(result["hdrSource"], "app" if known else "unknown")

    def test_old_gamescope_has_no_redundant_fsr_override(self):
        for app in ([], [0], [1]):
            self.assertFalse(self.capabilities(app, [1], False)["showFsrOverride"])

    def test_no_stale_state_across_game_and_qam_transitions(self):
        plugin = backend.Plugin()
        state = {"app": [1]}
        plugin._session_property_values = lambda key: state["app"] if "APP_WANTS" in key else [1]
        # Opening QAM without changing base-layer feedback retains HDR. Leaving
        # the game, missing feedback and starting SDR must not retain old HDR.
        for values, expected in (([1], True), ([1], True), ([], False), ([0], False), ([1], True)):
            state["app"] = values
            self.assertEqual(plugin._hdr_state()["hdrInput"], expected)

    def test_sharpness_mapping_both_backends(self):
        for steamos in (False, True):
            for level, raw in enumerate((20, 16, 12, 8, 4, 0)):
                with self.subTest(steamos=steamos, level=level):
                    plugin = backend.Plugin()
                    writes = []
                    def record(properties):
                        writes.extend(properties)
                        return [":0", ":1"], []
                    plugin._is_steamos = lambda: steamos
                    plugin._ubuntu_write_all = record
                    plugin._steamos_targets = lambda: []
                    plugin._steamos_write_to_targets = lambda targets, props: record(props)
                    result = asyncio.run(plugin.set_nis_sharpness(level))
                    self.assertTrue(result["success"])
                    self.assertEqual(writes, [("GAMESCOPE_SHARPNESS", raw), ("GAMESCOPE_FSR_SHARPNESS", raw)])

    def test_invalid_sharpness_never_writes(self):
        plugin = backend.Plugin()
        plugin._is_steamos = lambda: self.fail("Invalid input reached backend")
        for value in (-1, 6, True, "3", 2.5):
            self.assertFalse(asyncio.run(plugin.set_nis_sharpness(value))["success"])

if __name__ == "__main__":
    unittest.main()
