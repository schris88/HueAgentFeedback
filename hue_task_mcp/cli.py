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
        raise RuntimeError("Not paired yet. Run: python -m hue_task_mcp pair --bridge BRIDGE_IP")


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
            bridge = Bridge(load_config(path))
            await Indicator(bridge, path.with_suffix(".lock")).signal(signal_type)
        except Exception as exc:
            sys.stderr.write(f"[hue-task-mcp] Hook signal error: {exc}\n")

    # Antigravity hook contract: Always emit JSON on stdout
    print(json.dumps({"decision": "allow"}))


def generate_hook_config(python_path: Path, config_path: Path) -> dict:
    py_exec = python_path.resolve().as_posix()
    cfg_arg = f' --config "{config_path.resolve().as_posix()}"'
    base_cmd = f'"{py_exec}" -m hue_task_mcp{cfg_arg} hook'
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
        if "hue-task" in data:
            del data["hue-task"]
            target_file.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
            print(f"Removed hue-task hooks from: {target_file}")
        else:
            print(f"No hue-task entry found in: {target_file}")
        return

    data["hue-task"] = generate_hook_config(py_path, config_path)
    target_file.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    print(f"Configured hue-task hooks in: {target_file}")


def main():
    parser = argparse.ArgumentParser(description="Philips Hue agent indicators and lifecycle hooks")
    parser.add_argument("--config", type=Path, default=Path(os.getenv("HUE_TASK_CONFIG", DEFAULT_CONFIG)))
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
