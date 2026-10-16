import asyncio
import copy
import tempfile
import unittest
from pathlib import Path

from hue_task_mcp.bridge import Indicator, restore_state

LIGHT = {"id": "3b6e747a-d4ff-49cc-8180-cf345819d3f5", "on": {"on": True},
         "dimming": {"brightness": 38}, "color": {"xy": {"x": 0.4, "y": 0.3}},
         "color_temperature": {"mirek": 250, "mirek_valid": True},
         "effects": {"status": "no_effect"}, "mode": "normal"}


class FakeBridge:
    def __init__(self, light=None, fail_at=None):
        self.config = {"light_id": LIGHT["id"]}
        self.state = copy.deepcopy(light or LIGHT)
        self.writes = []
        self.fail_at = fail_at

    async def light(self, light_id):
        return copy.deepcopy(self.state)

    async def put(self, light_id, body):
        self.writes.append(copy.deepcopy(body))
        if len(self.writes) == self.fail_at:
            raise RuntimeError("simulated bridge failure")


async def no_wait(seconds):
    pass


class IndicatorTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "hue.lock"

    async def test_two_color_blends_preserve_brightness_and_restore(self):
        for event in ["done", "question"]:
            bridge = FakeBridge()
            result = await Indicator(bridge, self.path, no_wait).signal(event)
            self.assertEqual(len(bridge.writes), 5)
            target_x = 0.153 if event == "done" else 0.675
            for i in [0, 2]:
                self.assertAlmostEqual(bridge.writes[i]["color"]["xy"]["x"], 0.4 + 0.22 * (target_x - 0.4))
                self.assertNotIn("on", bridge.writes[i])
                self.assertNotIn("dimming", bridge.writes[i])
                self.assertEqual(bridge.writes[i]["dynamics"]["duration"], 1000)
            self.assertEqual(bridge.writes[-1], {**restore_state(LIGHT), "dynamics": {"duration": 800}})
            self.assertEqual(result["pulses"], 2)

    async def test_off_light_returns_off(self):
        light = copy.deepcopy(LIGHT)
        light["on"]["on"] = False
        bridge = FakeBridge(light)
        result = await Indicator(bridge, self.path, no_wait).signal("done")
        self.assertTrue(result["skipped"])
        self.assertEqual(bridge.writes, [])

    async def test_restore_after_write_failure(self):
        bridge = FakeBridge(fail_at=1)
        with self.assertRaisesRegex(RuntimeError, "simulated"):
            await Indicator(bridge, self.path, no_wait).signal("done")
        self.assertEqual(bridge.writes[-1], {**restore_state(LIGHT), "dynamics": {"duration": 800}})

    async def test_retry_restore(self):
        bridge = FakeBridge(fail_at=5)
        await Indicator(bridge, self.path, no_wait).signal("done")
        self.assertEqual(len(bridge.writes), 6)
        self.assertEqual(bridge.writes[-1], {**restore_state(LIGHT), "dynamics": {"duration": 800}})

    async def test_restore_on_cancellation(self):
        started = asyncio.Event()
        async def pause(seconds):
            if not started.is_set():
                started.set()
                await asyncio.sleep(10)
        bridge = FakeBridge()
        task = asyncio.create_task(Indicator(bridge, self.path, pause).signal("done"))
        await started.wait()
        task.cancel()
        with self.assertRaises(asyncio.CancelledError):
            await task
        self.assertEqual(bridge.writes[-1], {**restore_state(LIGHT), "dynamics": {"duration": 800}})

    async def test_refuse_streaming_or_dynamic_or_white_light(self):
        for change in [{"mode": "streaming"}, {"dynamics": {"status": "dynamic_palette"}}, {"color": None}]:
            light = copy.deepcopy(LIGHT)
            light.update(change)
            if light["color"] is None:
                del light["color"]
            bridge = FakeBridge(light)
            with self.assertRaises(RuntimeError):
                await Indicator(bridge, self.path, no_wait).signal("done")
            self.assertEqual(bridge.writes, [])

    async def test_invalid_event_and_unselected_light(self):
        bridge = FakeBridge()
        with self.assertRaises(ValueError):
            await Indicator(bridge, self.path, no_wait).signal("other")
        del bridge.config["light_id"]
        with self.assertRaises(RuntimeError):
            await Indicator(bridge, self.path, no_wait).signal("done")

    async def test_concurrent_signals_do_not_interleave(self):
        bridge = FakeBridge()
        async def yield_time(seconds):
            await asyncio.sleep(0)
        a = Indicator(bridge, self.path, yield_time)
        b = Indicator(bridge, self.path, yield_time)
        await asyncio.gather(a.signal("done"), b.signal("question"))
        self.assertEqual(bridge.writes[4], {**restore_state(LIGHT), "dynamics": {"duration": 800}})
        self.assertEqual(bridge.writes[9], {**restore_state(LIGHT), "dynamics": {"duration": 800}})
        self.assertLess(bridge.writes[0]["color"]["xy"]["x"], 0.4)
        self.assertGreater(bridge.writes[5]["color"]["xy"]["x"], 0.4)

    async def test_question_does_not_wake_off_light(self):
        light = copy.deepcopy(LIGHT)
        light["on"]["on"] = False
        bridge = FakeBridge(light)
        result = await Indicator(bridge, self.path, no_wait).signal("question")
        self.assertTrue(result["skipped"])
        self.assertEqual(bridge.writes, [])

    async def test_blend_preserves_gradient_shape(self):
        light = copy.deepcopy(LIGHT)
        light["gradient"] = {"points": [{"color": {"xy": {"x": 0.5, "y": 0.4}}},
                                         {"color": {"xy": {"x": 0.3, "y": 0.3}}}],
                             "mode": "interpolated_palette"}
        bridge = FakeBridge(light)
        await Indicator(bridge, self.path, no_wait).signal("question")
        points = bridge.writes[0]["gradient"]["points"]
        self.assertEqual(len(points), 2)
        self.assertAlmostEqual(points[0]["color"]["xy"]["x"], 0.5 + 0.22 * (0.675 - 0.5))
        self.assertNotEqual(points[0], points[1])
        self.assertEqual(bridge.writes[-1]["gradient"]["points"], light["gradient"]["points"])

    def test_gradient_and_effect_snapshot(self):
        light = copy.deepcopy(LIGHT)
        light["gradient"] = {"points": [{"color": {"xy": {"x": 0.5, "y": 0.4}}}],
                             "mode": "interpolated_palette", "points_capable": 5}
        light["effects"] = {"status": "candle"}
        state = restore_state(light)
        self.assertEqual(state["effects"], {"effect": "candle"})
        self.assertNotIn("points_capable", state["gradient"])
        self.assertIn("color_temperature", state)
        self.assertNotIn("color", state)


if __name__ == "__main__":
    unittest.main()
