import argparse
import asyncio
import json
import os
import ssl
import sys
from pathlib import Path

from .bridge import Bridge, Indicator, request_json

DEFAULT_CONFIG = Path(__file__).resolve().parent.parent / "hue.local.json"


def load_config(path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise RuntimeError("Not paired yet. Run: hue-agent-feedback pair --bridge BRIDGE_IP")


def save_config(path, config):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(".tmp")
    temp.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")
    temp.replace(path)
    if os.name != "nt":
        path.chmod(0o600)




async def local_action(args):
    path = args.config.resolve()
    if args.command == "discover":
        print(json.dumps(await asyncio.to_thread(request_json, "https://discovery.meethue.com"), indent=2))
    elif args.command == "pair":
        import ipaddress
        address = ipaddress.ip_address(args.bridge)
        if address.version != 4 or not address.is_private:
            raise ValueError("Use the Bridge's local IPv4 address")
        print("Press the physical Hue Bridge button now. Waiting up to 90 seconds...", flush=True)
        for _ in range(45):
            result = await asyncio.to_thread(request_json, f"https://{address}/api", "POST",
                {"devicetype": "hue-task-mcp#pc"}, None, ssl._create_unverified_context())
            success = next((x["success"] for x in result if "success" in x), None)
            if success:
                config = {"bridge_ip": str(address), "application_key": success["username"]}
                if path.exists():
                    old = load_config(path)
                    if old.get("bridge_ip") == str(address):
                        config["light_id"] = old.get("light_id")
                save_config(path, config)
                print("Paired. Key saved locally (excluded from Git). Run the lights command next.")
                return
            errors = [x["error"] for x in result if "error" in x]
            if any(e.get("type") != 101 for e in errors):
                raise RuntimeError("Pairing rejected by Bridge")
            await asyncio.sleep(2)
        raise RuntimeError("Pairing timed out. Press the Bridge button and run pair again.")
    else:
        bridge = Bridge(load_config(path))
        if args.command == "lights":
            for light in await bridge.lights():
                print(json.dumps({"id": light["id"], "name": light.get("metadata", {}).get("name"),
                    "color": "color" in light, "gradient": "gradient" in light,
                    "mode": light.get("mode")}, ensure_ascii=False))
        elif args.command == "select":
            light = await bridge.light(args.light_id)
            if "color" not in light:
                raise RuntimeError("Select a color-capable light for blue/red signals")
            bridge.config["light_id"] = light["id"]
            save_config(path, bridge.config)
            print("Selected: " + light.get("metadata", {}).get("name", light["id"]))
        elif args.command == "signal":
            print(json.dumps(await Indicator(bridge, path.with_suffix(".lock")).signal(args.event)))
        elif args.command == "status":
            if not bridge.config.get("light_id"):
                print(json.dumps({"paired": True, "light_selected": False}))
            else:
                light = await bridge.light(bridge.config["light_id"])
                print(json.dumps({
                    "name": light.get("metadata", {}).get("name"),
                    "state": light.get("on"),
                    "mode": light.get("mode"),
                    "color": "color" in light,
                    "brightness": light.get("dimming", {}).get("brightness"),
                    "temperature": "color_temperature" in light,
                    "gradient": "gradient" in light,
                    "effects": light.get("effects", {}).get("effect_values", [])
                }, indent=2))


def resolve_hook_python_executable(python_path: Path | None = None) -> Path:
    py_path = python_path if python_path is not None else Path(sys.executable)
    if os.name == "nt":
        pyw = py_path.with_name("pythonw.exe")
        if pyw.exists():
            return pyw
    return py_path


def spawn_detached_signal(config_path: Path, signal_type: str):
    import subprocess
    py_exec = sys.executable
    kwargs = {}
    if os.name == "nt":
        pyw = Path(py_exec).with_name("pythonw.exe")
        if pyw.exists():
            py_exec = str(pyw)
        kwargs["creationflags"] = (
            subprocess.DETACHED_PROCESS
            | subprocess.CREATE_NEW_PROCESS_GROUP
            | getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)
        )
    else:
        kwargs["start_new_session"] = True

    subprocess.Popen(
        [py_exec, "-m", "hue_agent_feedback", "--config", str(config_path), "signal", signal_type],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        stdin=subprocess.DEVNULL,
        close_fds=True,
        **kwargs
    )


async def run_hook(args):
    event = args.event
    path = args.config.resolve()

    signal_type = None
    if event in ("Stop", "stop", "done"):
        signal_type = "done"
    elif event in ("PreToolUse", "pre_tool_use", "question"):
        signal_type = "question"

    if signal_type:
        try:
            cfg = load_config(path)
            if cfg.get("light_id"):
                if getattr(args, "sync", False):
                    bridge = Bridge(cfg)
                    await Indicator(bridge, path.with_suffix(".lock")).signal(signal_type)
                else:
                    spawn_detached_signal(path, signal_type)
        except Exception as exc:
            if sys.stderr is not None:
                sys.stderr.write(f"[hue-agent-feedback] Hook signal error: {exc}\n")

    # Antigravity hook contract: Always emit JSON on stdout
    if sys.stdout is not None:
        print(json.dumps({"decision": "allow"}))
        try:
            sys.stdout.flush()
        except Exception:
            pass


def generate_hook_config(python_path: Path, config_path: Path) -> dict:
    resolved_py = resolve_hook_python_executable(python_path)
    py_exec = resolved_py.resolve().as_posix()
    cfg_posix = config_path.resolve().as_posix()
    py_str = f'"{py_exec}"' if " " in py_exec else py_exec
    cfg_str = f'"{cfg_posix}"' if " " in cfg_posix else cfg_posix
    base_cmd = f"{py_str} -m hue_agent_feedback --config {cfg_str} hook"
    return {
        "Stop": [
            {
                "type": "command",
                "command": f"{base_cmd} Stop",
                "timeout": 15
            }
        ],
        "PreToolUse": [
            {
                "matcher": "ask_question",
                "hooks": [
                    {
                        "type": "command",
                        "command": f"{base_cmd} PreToolUse",
                        "timeout": 15
                    }
                ]
            }
        ]
    }


def run_setup(args):
    config_path = args.config.resolve()
    py_path = Path(sys.executable)

    if args.path:
        target_file = args.path.resolve()
    elif args.is_global:
        target_file = Path.home() / ".gemini" / "config" / "hooks.json"
    else:
        target_file = Path.cwd() / ".agents" / "hooks.json"

    target_file.parent.mkdir(parents=True, exist_ok=True)

    data = {}
    if target_file.exists():
        try:
            data = json.loads(target_file.read_text(encoding="utf-8"))
            if not isinstance(data, dict):
                data = {}
        except Exception:
            data = {}

    if args.uninstall:
        removed = False
        for key in ("hue-agent-feedback", "hue-task"):
            if key in data:
                del data[key]
                removed = True
        if removed:
            target_file.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
            print(f"Removed hue-agent-feedback hooks from: {target_file}")
        else:
            print(f"No hue-agent-feedback entry found in: {target_file}")
        return

    # Clean up legacy key if present
    data.pop("hue-task", None)
    data["hue-agent-feedback"] = generate_hook_config(py_path, config_path)
    target_file.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    print(f"Configured hue-agent-feedback hooks in: {target_file}")


def main():
    parser = argparse.ArgumentParser(description="Philips Hue agent indicators and lifecycle hooks")
    parser.add_argument("--config", type=Path, default=Path(os.getenv("HUE_AGENT_FEEDBACK_CONFIG", os.getenv("HUE_TASK_CONFIG", DEFAULT_CONFIG))))
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("discover", help="Discover Hue Bridges on the local network")
    pair = sub.add_parser("pair", help="Pair with a Hue Bridge")
    pair.add_argument("--bridge", required=True, help="Bridge IP address")
    sub.add_parser("lights", help="List available color-capable lights")
    select = sub.add_parser("select", help="Select target monitor light by UUID")
    select.add_argument("light_id", help="Light UUID")
    signal = sub.add_parser("signal", help="Trigger a signal manually")
    signal.add_argument("event", choices=["done", "question"])
    sub.add_parser("status", help="Show current state of selected light")
    hook = sub.add_parser("hook", help="Handle Antigravity lifecycle events")
    hook.add_argument("event", choices=["Stop", "stop", "PreToolUse", "pre_tool_use", "done", "question"])
    hook.add_argument("--sync", action="store_true", help="Run signal synchronously instead of detached in background")
    setup = sub.add_parser("setup", help="Configure Antigravity CLI lifecycle hooks")
    setup.add_argument("--global", dest="is_global", action="store_true", help="Install hooks globally in ~/.gemini/config/hooks.json")
    setup.add_argument("--path", type=Path, default=None, help="Target hooks.json path")
    setup.add_argument("--uninstall", action="store_true", help="Remove hue-task hooks from target file")
    args = parser.parse_args()
    try:
        if args.command == "hook":
            asyncio.run(run_hook(args))
        elif args.command == "setup":
            run_setup(args)
        else:
            asyncio.run(local_action(args))
    except (RuntimeError, ValueError, KeyError) as exc:
        parser.exit(1, str(exc) + "\n")


if __name__ == "__main__":
    main()
