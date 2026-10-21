import io
import json
import tempfile
import unittest
import os
import subprocess
from pathlib import Path
from unittest.mock import patch, AsyncMock

from hue_agent_feedback.cli import (
    generate_hook_config,
    run_setup,
    run_hook,
    resolve_hook_python_executable,
    spawn_detached_signal
)


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
        self.assertIn("hue-agent-feedback", data)

        # Uninstall
        class ArgsUninstall:
            path = target
            config = config_path
            uninstall = True
            is_global = False

        run_setup(ArgsUninstall)
        data = json.loads(target.read_text(encoding="utf-8"))
        self.assertNotIn("hue-agent-feedback", data)

    def test_resolve_hook_python_executable_prefers_pythonw_on_windows(self):
        py_bin = self.dir_path / "python.exe"
        pyw_bin = self.dir_path / "pythonw.exe"
        py_bin.touch()
        pyw_bin.touch()

        with patch("os.name", "nt"):
            resolved = resolve_hook_python_executable(py_bin)
            self.assertEqual(resolved, pyw_bin)

    def test_spawn_detached_signal_flags(self):
        with patch("subprocess.Popen") as mock_popen:
            spawn_detached_signal(Path("test.json"), "done")
            mock_popen.assert_called_once()
            _, kwargs = mock_popen.call_args
            self.assertTrue(kwargs.get("close_fds"))
            if os.name == "nt":
                flags = kwargs.get("creationflags", 0)
                self.assertTrue(flags & subprocess.DETACHED_PROCESS)
                self.assertTrue(flags & subprocess.CREATE_NEW_PROCESS_GROUP)
                self.assertTrue(flags & getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000))


class RunHookTests(unittest.IsolatedAsyncioTestCase):
    async def test_run_hook_stop_emits_allow_and_signals_sync(self):
        class Args:
            event = "Stop"
            config = Path("hue.local.json")
            sync = True

        with patch("hue_agent_feedback.cli.Bridge") as mock_bridge, \
             patch("hue_agent_feedback.cli.Indicator") as mock_indicator, \
             patch("hue_agent_feedback.cli.load_config", return_value={"light_id": "123"}), \
             patch("sys.stdout", new_callable=io.StringIO) as mock_stdout:
            mock_inst = AsyncMock()
            mock_indicator.return_value = mock_inst

            await run_hook(Args)

            mock_inst.signal.assert_awaited_once_with("done")
            output = json.loads(mock_stdout.getvalue())
            self.assertEqual(output.get("decision"), "allow")

    async def test_run_hook_pre_tool_use_with_ask_question_sync(self):
        class Args:
            event = "PreToolUse"
            config = Path("hue.local.json")
            sync = True

        payload = {"toolCall": {"name": "ask_question", "args": {}}}
        with patch("hue_agent_feedback.cli.Bridge") as mock_bridge, \
             patch("hue_agent_feedback.cli.Indicator") as mock_indicator, \
             patch("hue_agent_feedback.cli.load_config", return_value={"light_id": "123"}), \
             patch("sys.stdin", io.StringIO(json.dumps(payload))), \
             patch("sys.stdout", new_callable=io.StringIO) as mock_stdout:
            mock_inst = AsyncMock()
            mock_indicator.return_value = mock_inst

            await run_hook(Args)

            mock_inst.signal.assert_awaited_once_with("question")
            output = json.loads(mock_stdout.getvalue())
            self.assertEqual(output.get("decision"), "allow")

    async def test_run_hook_detached_default(self):
        class Args:
            event = "Stop"
            config = Path("hue.local.json")
            sync = False

        with patch("hue_agent_feedback.cli.load_config", return_value={"light_id": "123"}), \
             patch("hue_agent_feedback.cli.spawn_detached_signal") as mock_spawn, \
             patch("sys.stdout", new_callable=io.StringIO) as mock_stdout:
            await run_hook(Args)

            mock_spawn.assert_called_once_with(Path("hue.local.json").resolve(), "done")
            output = json.loads(mock_stdout.getvalue())
            self.assertEqual(output.get("decision"), "allow")

    async def test_run_hook_error_resilience(self):
        class Args:
            event = "Stop"
            config = Path("nonexistent.json")
            sync = True

        with patch("sys.stdout", new_callable=io.StringIO) as mock_stdout, \
             patch("sys.stderr", new_callable=io.StringIO) as mock_stderr:
            await run_hook(Args)

            # Still emits allow so Antigravity doesn't break
            output = json.loads(mock_stdout.getvalue())
            self.assertEqual(output.get("decision"), "allow")
            self.assertIn("Hook signal error", mock_stderr.getvalue())


if __name__ == "__main__":
    unittest.main()
