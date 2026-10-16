"""Small Hue v2 adapter; no bridge credentials in URLs or logs."""
import asyncio
import copy
import ipaddress
import json
import ssl
import urllib.error
import urllib.request
from pathlib import Path


def request_json(url, method="GET", body=None, key=None, context=None):
    headers = {"Content-Type": "application/json"}
    if key:
        headers["hue-application-key"] = key
    req = urllib.request.Request(url, data=None if body is None else json.dumps(body).encode(),
                                 headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, context=context, timeout=8) as response:
            return json.load(response)
    except (urllib.error.URLError, TimeoutError) as exc:
        raise RuntimeError("Hue request failed; check bridge address, pairing, and network.") from exc


class Bridge:
    def __init__(self, config):
        self.config = config
        address = ipaddress.ip_address(config["bridge_ip"])
        if address.version != 4 or not address.is_private:
            raise ValueError("bridge_ip must be a private IPv4 address")
        # Hue uses a local certificate. Supply a trusted CA bundle when available.
        self.context = (ssl.create_default_context(cafile=config["ca_file"])
                        if config.get("ca_file") else ssl._create_unverified_context())
        self.url = f"https://{address}/clip/v2/resource"

    async def request(self, method, path, body=None):
        result = await asyncio.to_thread(request_json, self.url + path, method, body,
                                         self.config["application_key"], self.context)
        if result.get("errors"):
            raise RuntimeError("Hue rejected the request: " + "; ".join(
                e.get("description", "unknown error") for e in result["errors"]))
        return result.get("data", [])

    async def lights(self):
        return await self.request("GET", "/light")

    async def light(self, light_id):
        # Never accept a path supplied by a model.
        import uuid
        uuid.UUID(light_id)
        data = await self.request("GET", "/light/" + light_id)
        if not data:
            raise RuntimeError("Configured light was not found")
        return data[0]

    async def put(self, light_id, body):
        import uuid
        uuid.UUID(light_id)
        return await self.request("PUT", "/light/" + light_id, body)


def restore_state(light):
    state = {"on": copy.deepcopy(light["on"])}
    if "dimming" in light:
        state["dimming"] = {"brightness": light["dimming"]["brightness"]}
    temperature = light.get("color_temperature", {})
    if temperature.get("mirek_valid") and temperature.get("mirek") is not None:
        state["color_temperature"] = {"mirek": temperature["mirek"]}
    elif "xy" in light.get("color", {}):
        state["color"] = {"xy": copy.deepcopy(light["color"]["xy"])}
    gradient = light.get("gradient", {})
    if gradient.get("points"):
        state["gradient"] = {"points": copy.deepcopy(gradient["points"])}
        if "mode" in gradient:
            state["gradient"]["mode"] = gradient["mode"]
    effect = light.get("effects", {}).get("status")
    if effect and effect != "no_effect":
        state["effects"] = {"effect": effect}
    return state


class Indicator:
    def __init__(self, bridge, lock_path, sleeper=asyncio.sleep):
        self.bridge, self.lock_path, self.sleep = bridge, Path(lock_path), sleeper
        self.lock = asyncio.Lock()

    async def signal(self, event):
        if event not in ("done", "question"):
            raise ValueError("event must be done or question")
        # OS lock coordinates separate stdio/HTTP processes on this computer.
        from .locking import file_lock
        async with self.lock:
            async with file_lock(self.lock_path):
                light_id = self.bridge.config.get("light_id")
                if not light_id:
                    raise RuntimeError("Select your monitor light first with the select command")
                light = await self.bridge.light(light_id)
                # Keep an intentionally dark room dark: skip if light is turned off
                if not light.get("on", {}).get("on", False):
                    return {"event": event, "skipped": True, "reason": "light_is_off"}
                if "color" not in light:
                    raise RuntimeError("This light cannot display blue and red; select a color light")
                if light.get("mode") == "streaming":
                    raise RuntimeError("Hue Sync is streaming to this light. Stop syncing, then retry.")
                if light.get("dynamics", {}).get("status") not in (None, "none"):
                    raise RuntimeError("Pause the dynamic scene first so its state can be preserved")
                original = restore_state(light)
                target = {"x": 0.153, "y": 0.048} if event == "done" else {"x": 0.675, "y": 0.322}
                amount = float(self.bridge.config.get("color_mix", 0.22))
                if not 0.05 <= amount <= 0.5:
                    raise ValueError("color_mix must be between 0.05 and 0.5")
                def mix(xy):
                    return {axis: xy[axis] + amount * (target[axis] - xy[axis]) for axis in ("x", "y")}
                pulse = {"color": {"xy": mix(light["color"]["xy"])},
                         "dynamics": {"duration": 1000}}
                gradient = light.get("gradient", {})
                if gradient.get("points"):
                    pulse["gradient"] = {"points": [
                        {"color": {"xy": mix(point["color"]["xy"])}}
                        for point in gradient["points"]]}
                    if "mode" in gradient:
                        pulse["gradient"]["mode"] = gradient["mode"]
                if "effects" in light:
                    pulse["effects"] = {"effect": "no_effect"}
                try:
                    # Two eased color swells, preserving brightness and avoiding on/off flashes.
                    for _ in range(2):
                        await self.bridge.put(light_id, pulse)
                        await self.sleep(1.25)
                        await self.bridge.put(light_id, {**original, "dynamics": {"duration": 1000}})
                        await self.sleep(1.15)
                finally:
                    # Shield cleanup from normal MCP cancellation. Power loss cannot be handled.
                    async def restore():
                        for attempt in range(3):
                            try:
                                await self.bridge.put(light_id, {**original, "dynamics": {"duration": 800}})
                                await self.sleep(0.8)
                                return
                            except RuntimeError:
                                if attempt == 2:
                                    raise RuntimeError("Could not restore the light; check it in the Hue app")
                                await self.sleep(0.5)
                    task = asyncio.create_task(restore())
                    try:
                        await asyncio.shield(task)
                    except asyncio.CancelledError:
                        await task
                        raise
                return {"event": event, "pattern": "blue_color_blend" if event == "done" else "red_color_blend",
                        "pulses": 2, "mix": amount, "restored": True}
