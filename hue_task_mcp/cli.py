import argparse
import asyncio
import json
import os
import ssl
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


def make_server(config_path):
    from mcp.server import MCPServer
    from .locking import file_lock
    server = MCPServer("hue-task-mcp", version="0.1.0", instructions=(
        "Call task_done once immediately before the final answer for a completed task (one soft blue pulse). "
        "Call needs_input once immediately before asking a question that requires the user's response. "
        "Never signal completion for an incomplete task. Do not signal routine progress updates."))
    # Read configuration for every call so pairing/selection does not need a restart.
    def indicator():
        return Indicator(Bridge(load_config(config_path)), config_path.with_suffix(".lock"))

    @server.tool()
    async def task_done() -> dict:
        """Show one soft, dim blue pulse, then restore the monitor light. Call before the final answer when the task is complete."""
        return await indicator().signal("done")

    @server.tool()
    async def needs_input() -> dict:
        """Slowly dip and restore brightness in the current color once. Skip when off. Call immediately before asking the user a question requiring a reply."""
        return await indicator().signal("question")

    @server.tool()
    async def light_status() -> dict:
        """Read the configured monitor light's state and supported capabilities. Makes no lighting changes."""
        bridge = Bridge(load_config(config_path))
        if not bridge.config.get("light_id"):
            return {"paired": True, "light_selected": False}
        light = await bridge.light(bridge.config["light_id"])
        return {"name": light.get("metadata", {}).get("name"), "state": light.get("on"),
                "mode": light.get("mode"), "color": "color" in light,
                "brightness": light.get("dimming", {}).get("brightness"),
                "temperature": "color_temperature" in light,
                "gradient": "gradient" in light,
                "effects": light.get("effects", {}).get("effect_values", [])}
    return server


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


def main():
    parser = argparse.ArgumentParser(description="Philips Hue MCP task indicators")
    parser.add_argument("--config", type=Path, default=Path(os.getenv("HUE_TASK_CONFIG", DEFAULT_CONFIG)))
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("discover")
    pair = sub.add_parser("pair")
    pair.add_argument("--bridge", required=True)
    sub.add_parser("lights")
    select = sub.add_parser("select")
    select.add_argument("light_id")
    signal = sub.add_parser("signal")
    signal.add_argument("event", choices=["done", "question"])
    serve = sub.add_parser("serve")
    serve.add_argument("--transport", choices=["stdio", "streamable-http"], default="stdio")
    serve.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()
    try:
        if args.command == "serve":
            server = make_server(args.config.resolve())
            if args.transport == "stdio":
                server.run()
            else:
                server.run(transport="streamable-http", host="127.0.0.1", port=args.port,
                           stateless_http=True, json_response=True)
        else:
            asyncio.run(local_action(args))
    except (RuntimeError, ValueError, KeyError) as exc:
        parser.exit(1, str(exc) + "\n")


if __name__ == "__main__":
    main()
