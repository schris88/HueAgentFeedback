# Hue Task MCP

Use the Philips Hue lightstrip behind your monitor as an AI task indicator:

| Tool | Signal |
| --- | --- |
| `task_done` | One dim blue pulse, then restore the previous light state |
| `needs_input` | One slow brightness dip in the existing color, then restore |
| `light_status` | Read state and supported color/effect/gradient capabilities |

Works with local stdio MCP clients such as Antigravity CLI. Also serves Streamable HTTP for a ChatGPT Secure MCP Tunnel. No OpenAI API key is needed for the Hue server itself.

## Install and pair

Requires Python 3.11+ and a Hue Bridge on the same LAN. Bluetooth-only lights are not supported. Hue Sync does not need to be running.

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e .
.\.venv\Scripts\python.exe -m hue_task_mcp discover
.\.venv\Scripts\python.exe -m hue_task_mcp pair --bridge YOUR_BRIDGE_IP
```

Press the physical Bridge button during pairing. A separate application key is saved in `hue.local.json`, which Git ignores. Do not upload that file. This application key is authorized at Bridge level, not restricted by Hue to a single light; the MCP tools restrict their actions to the configured light.

```powershell
.\.venv\Scripts\python.exe -m hue_task_mcp lights
.\.venv\Scripts\python.exe -m hue_task_mcp select LIGHT_UUID
.\.venv\Scripts\python.exe -m hue_task_mcp signal done
.\.venv\Scripts\python.exe -m hue_task_mcp signal question
```

The config path can be changed with `HUE_TASK_CONFIG` or `--config PATH` **before** the subcommand. Keep the same config path for all clients so their blink sequences share the same OS lock.

## Antigravity CLI

Merge `examples/mcp_config.json` into the `mcpServers` object of `~/.gemini/config/mcp_config.json`, replacing the example paths with this repository's absolute paths. Preserve other servers. Antigravity also supports workspace `.agents/mcp_config.json`. Restart the CLI or use `/mcp` to reload and inspect the server.

Add `examples/agent-instructions.md` to the agent's loaded instructions (for example, your global `~/.gemini/GEMINI.md`). The MCP server also supplies these instructions in its initialization response. Approve notification tools according to your client's normal permissions.

**Automatic notifications:** MCP exposes callable tools. It does not subscribe to the chat UI's task lifecycle. The agent must call `task_done` or `needs_input` according to its instructions. Client permission dialogs, crashes, and questions the agent never signals cannot reliably trigger these tools. If your client offers documented lifecycle hooks, invoke `python -m hue_task_mcp signal done` or `signal question` from the relevant hook. No unverified hook names are installed by this project.

Official configuration reference: https://antigravity.google/docs/mcp?tab=cli

## ChatGPT

ChatGPT needs a reachable MCP connection; an Antigravity stdio config does not register a tool in ChatGPT.

The private connection option documented by OpenAI is Secure MCP Tunnel:

1. In OpenAI Platform tunnel settings, create a tunnel that includes the intended ChatGPT workspace. Appropriate tunnel permissions and a runtime key are required.
2. Install/configure the official `tunnel-client` following OpenAI's current onboarding guide. Point it to this server's stdio command, or start the HTTP listener below and point the tunnel at `http://127.0.0.1:8765/mcp`.
3. In ChatGPT on the web, open Plugins, add a custom MCP server, and choose the tunnel connection. Install the resulting plugin in the conversation.
4. Add the notification instructions from `examples/agent-instructions.md` to your conversation or loaded instructions, and test both tools.

```powershell
.\.venv\Scripts\python.exe -m hue_task_mcp serve --transport streamable-http --port 8765
```

The HTTP listener binds only to `127.0.0.1`. It has no application-level authentication and is intended for local clients or an access-controlled private tunnel. Do not forward this port publicly. Public deployment would require an authenticated HTTPS gateway and matching MCP/OAuth configuration. This project does not provision a tunnel or change your OpenAI account settings.

Official guides:
- https://developers.openai.com/api/docs/guides/custom-mcp-server
- https://developers.openai.com/api/docs/guides/secure-mcp-tunnels

## Control available on Hue

The Bridge's v2 API can control power, brightness, color coordinates, supported white temperatures, transitions, supported built-in effects, and supported gradients. Available properties depend on the exact light. `light_status` reads the chosen light's actual reported capabilities.

This MCP server intentionally exposes the two indicators and read-only status. It does not expose arbitrary Bridge API requests, other household lights, scene editing, or continuous animation. Additional color/effect tools can be added using the same adapter. A gradient strip exposes supported control points/zones, which are not necessarily individually addressable LEDs.

For fast, continuous animations or audio/video synchronization, Hue requires the Entertainment streaming API, an entertainment area, and the appropriate client key/DTLS implementation. This server uses occasional REST commands instead. Hue Sync can take control of an entertainment light; this server refuses to signal while the light reports streaming mode rather than taking over your Sync session.

Hue references:
- https://developers.meethue.com/develop/get-started-2/
- https://developers.meethue.com/new-hue-api/

## Behavior and limits

- Completion: one blue pulse at at most 20% brightness (12% when previously off), with a 450 ms fade in, 1.1 seconds total before restoration, and an 800 ms fade back. Question: dim to 65% of current brightness over one second, then fade back over 800 ms. No red flashes or black-out lead-in. Questions do not wake an off light.
- Snapshots/restores power, brightness, active white temperature or color, gradients, and the active basic effect when exposed by the light. Advanced effect parameters and dynamic-scene playback cannot be reconstructed; pause dynamic scenes first.
- Restoration runs after ordinary errors and cancellation, with up to three attempts. Power loss, process termination, or persistent network failure can prevent it. A concurrent change in the Hue app during a signal may be overwritten by restoration.
- OS file locks serialize signals across local stdio/HTTP server processes. A waiting signal times out after 60 seconds.
- Bridge requests use HTTPS with a private IPv4 address. By default, local Bridge certificate verification is disabled because Hue uses a local certificate. For validated TLS, provide a trusted Bridge CA bundle as `ca_file` in the local configuration. No global TLS settings are changed.
- Credentials never appear in tool output, URL paths, or committed examples. Protect the local config with your OS user permissions. Other users/processes with access to that file can control the Bridge.

## Test

```powershell
python -m unittest discover -s tests -v
```

Tests cover pulse counts/colors, restoration from on/off, write failure, cancellation, restoration retry, rejected unsupported/streaming/dynamic lights, gradients/effects, and serialization. They do not require a real Bridge. CI runs on Windows and Linux.

## Create the private GitHub repository

From a normal PowerShell terminal where your GitHub `git push` works:

```powershell
powershell -ExecutionPolicy Bypass -File .\Publish-PrivateRepo.ps1
```

The script reuses Git's configured credential helper, creates `hue-task-mcp` under the authenticated GitHub account with `private: true`, stages an explicit source-file allowlist, and pushes `main`. It refuses an existing public repo, a mismatched remote, or tracked credentials. It never force-pushes and never prints or persists the GitHub token.
