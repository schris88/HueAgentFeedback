import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, AsyncMock

from hue_task_mcp.cli import generate_hook_config, run_setup, run_hook


class HookCliTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.dir_path = Path(self.temp_dir.name)

    def test_generate_hook_config_structure(self):
        cfg = generate_hook_config(Path("C:/test/python.exe"), Path("C:/test/hue.local.json"))
        self.assertIn("Stop", cfg)
        self.assertIn("PreToolUse", cfg)
        self.assertEqual(len(cfg["Stop"]), 1)
        self.assertEqual(cfg["Stop"][0]["type"], "command")
        self.assertEqual(cfg["Stop"][0]["timeout"], 15)
        self.assertIn("hook Stop", cfg["Stop"][0]["command"])

        self.assertEqual(len(cfg["PreToolUse"]), 1)
        self.assertEqual(cfg["PreToolUse"][0]["matcher"], "ask_question")
        self.assertEqual(cfg["PreToolUse"][0]["hooks"][0]["type"], "command")
        self.assertIn("hook PreToolUse", cfg["PreToolUse"][0]["hooks"][0]["command"])

    def test_run_setup_install_and_uninstall(self):
        target = self.dir_path / "hooks.json"
        config_path = self.dir_path / "hue.local.json"

        # Install
        class ArgsInstall:
            path = target
            config = config_path
            uninstall = False
            is_global = False

        run_setup(ArgsInstall)
        self.assertTrue(target.exists())
        data = json.loads(target.read_text(encoding="utf-8"))
        self.assertIn("hue-task", data)

        # Uninstall
        class ArgsUninstall:
            path = target
            config = config_path
            uninstall = True
            is_global = False

        run_setup(ArgsUninstall)
        data = json.loads(target.read_text(encoding="utf-8"))
        self.assertNotIn("hue-task", data)


class RunHookTests(unittest.IsolatedAsyncioTestCase):
    async def test_run_hook_stop_emits_allow_and_signals(self):
        class Args:
            event = "Stop"
            config = Path("hue.local.json")

        with patch("hue_task_mcp.cli.Bridge") as mock_bridge, \
             patch("hue_task_mcp.cli.Indicator") as mock_indicator, \
             patch("hue_task_mcp.cli.load_config", return_value={"light_id": "123"}), \
             patch("sys.stdout", new_callable=io.StringIO) as mock_stdout:
            mock_inst = AsyncMock()
            mock_indicator.return_value = mock_inst

            await run_hook(Args)

            mock_inst.signal.assert_awaited_once_with("done")
            output = json.loads(mock_stdout.getvalue())
            self.assertEqual(output.get("decision"), "allow")

    async def test_run_hook_pre_tool_use_with_ask_question(self):
        class Args:
            event = "PreToolUse"
            config = Path("hue.local.json")

        payload = {"toolCall": {"name": "ask_question", "args": {}}}
        with patch("hue_task_mcp.cli.Bridge") as mock_bridge, \
             patch("hue_task_mcp.cli.Indicator") as mock_indicator, \
             patch("hue_task_mcp.cli.load_config", return_value={"light_id": "123"}), \
             patch("sys.stdin", io.StringIO(json.dumps(payload))), \
             patch("sys.stdout", new_callable=io.StringIO) as mock_stdout:
            mock_inst = AsyncMock()
            mock_indicator.return_value = mock_inst

            await run_hook(Args)

            mock_inst.signal.assert_awaited_once_with("question")
            output = json.loads(mock_stdout.getvalue())
            self.assertEqual(output.get("decision"), "allow")

    async def test_run_hook_error_resilience(self):
        class Args:
            event = "Stop"
            config = Path("nonexistent.json")

        with patch("sys.stdout", new_callable=io.StringIO) as mock_stdout, \
             patch("sys.stderr", new_callable=io.StringIO) as mock_stderr:
            await run_hook(Args)

            # Still emits allow so Antigravity doesn't break
            output = json.loads(mock_stdout.getvalue())
            self.assertEqual(output.get("decision"), "allow")
            self.assertIn("Hook signal error", mock_stderr.getvalue())


if __name__ == "__main__":
    unittest.main()
