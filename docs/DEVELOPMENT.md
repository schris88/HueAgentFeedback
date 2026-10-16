# Entwicklung und Wartung

[Zur README](../README.md)

## Lokale Entwicklungsumgebung

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e .
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Das Paket benötigt Python 3.11+ und `mcp>=2.2,<3`. Der Code verwendet `MCPServer` aus MCP SDK v2; Beispiele für SDK-v1-`FastMCP` nicht ungeprüft übernehmen. Build-Backend ist setuptools; `pyproject.toml` enthält den Konsolenbefehl und die README als Paketbeschreibung. Es gibt derzeit keine vollständig gesperrte Dependency-Lockdatei und keine veröffentlichte Paketversion auf PyPI.

## Testumfang

`tests/test_indicator.py` verwendet `unittest.IsolatedAsyncioTestCase` und einen Fake-Bridge-Adapter. Statt echter Wartezeiten werden Test-Sleeper eingesetzt. Die Tests verändern keine physische Leuchte.

Abgedeckt sind zwei Farbmischungen ohne Helligkeitsänderung, Wiederherstellung, ausgeschaltete Leuchten, Fehler beim Schreiben, Wiederholungen der Sicherung, Cancellation, Streaming-/Szenen-/Farbprüfungen, ungültige Events, fehlende Auswahl, konkurrierende Indicator-Instanzen sowie Gradient- und Effektsnapshots.

Nicht vollständig abgedeckt sind die reale Hue-Firmware, alle Gerätemodelle, Pairing/Discovery-Responses, harte Prozessabbrüche, jeder Fehler des MCP-Transports und sämtliche GitHub-Publish-Pfade. Die physische Windows-Leuchte und beide Transportarten wurden im ursprünglichen lokalen Setup geprüft; das ist kein genereller Hardware-Kompatibilitätsnachweis.

Die CI unter `.github/workflows/tests.yml` installiert das Projekt und führt die Tests unter Windows/Linux mit Python 3.11/3.13 aus. macOS-Locks sind implementiert, aber nicht Teil dieser Matrix. Ein vorhandener Workflow ist kein Nachweis eines bereits erfolgreichen Remote-Laufs.

## MCP-Verbindung ohne Lichtänderung prüfen

Im Projektordner mit dem venv-Python ausführen:

```python
import asyncio
import pathlib
import sys
from mcp import Client
from mcp.client.stdio import StdioServerParameters

async def main():
    params = StdioServerParameters(
        command=sys.executable,
        args=["-m", "hue_task_mcp", "serve"],
        cwd=str(pathlib.Path.cwd()),
    )
    async with Client(params) as client:
        tools = await client.list_tools()
        print([tool.name for tool in tools.tools])
        result = await client.call_tool("light_status", {})
        print(result.model_dump_json())

asyncio.run(main())
```

Erwartete Werkzeuge: `task_done`, `needs_input`, `light_status`. Der Statusaufruf benötigt eine gekoppelte Bridge, die reine Werkzeugliste nicht. Ein zusätzlicher Live-Test mit `task_done` oder `needs_input` verändert die echte Leuchte und sollte bewusst durchgeführt werden.

Für HTTP zuerst den Server gemäß README starten, dann statt der stdio-Parameter `Client("http://127.0.0.1:8765/mcp")` verwenden.

## Erweiterungen

Weitere Signalstärken lassen sich über `color_mix` konfigurieren. Für andere Zeiten, Pulszahlen oder Ziele `Indicator.signal` anpassen und die Referenz sowie Tests aktualisieren. Die Mischung erfolgt in CIE xy, nicht in RGB. Sie ist nicht wahrnehmungslinear und hat keine eigene Gamut-Projektion.

Zusätzliche MCP-Werkzeuge können in `make_server` registriert werden. Lichtänderungen sollten dieselbe Dateisperre nutzen, Eingaben begrenzen und die Zustandswiederherstellung bewusst behandeln. Keine frei wählbaren URLs oder ungeprüften API-Pfade aus Modellargumenten übernehmen. Gegenwärtig prüft `Bridge.light/put` UUIDs und die Tools bieten keine Zielparameter.

Ein frei auswählbarer Effekt, Szenenverwaltung, mehrere Ziellichter, ein persistenter Wiederherstellungsdienst, Echtzeit-Entertainment oder Lifecycle-Hooks wären neue Funktionen; sie sind nicht vorhanden. Reine Hue-Fähigkeit bedeutet nicht, dass ein passendes MCP-Werkzeug bereits implementiert ist.

## Dokumentation und Veröffentlichung pflegen

Bei Änderungen CLI-Hilfe, README, Referenz, Beispiele, Agent-Regeln und Changelog gemeinsam prüfen. Keine persönlichen IPs, UUIDs, Leuchtennamen oder Schlüssel in generische Beispiele aufnehmen.

Das optionale PowerShell-Publish-Skript benutzt eine explizite Pfadliste einschließlich `docs`, `examples` und `CHANGELOG.md`. Neue top-level-Dateien gegebenenfalls ergänzen. Es erstellt Repositorys im persönlichen Konto, nicht in einer frei wählbaren Organisation. Einen bestehenden fremden Branch/Remote niemals durch Force-Push ersetzen.

Vor einer öffentlichen Weitergabe eine Lizenz festlegen, Paket-/Versionsmetadaten prüfen, Tests ausführen und gestagte Dateien auf lokale Konfigurationen kontrollieren. Dieses Projekt hat derzeit keine festgelegte Weitergabe-Lizenz.
