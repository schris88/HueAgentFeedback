# Konfiguration und Schnittstellen

[Zur README](../README.md)

## Konfigurationsdatei

Standard: `hue.local.json` eine Ebene über dem Python-Paket. Bei der empfohlenen editable Installation ist das der Projektordner. Bei einer regulären Wheel-Installation kann der Standardpfad im Installationsverzeichnis liegen; dann unbedingt einen beschreibbaren eigenen Pfad angeben.

Priorität: explizites `--config PATH`, sonst Umgebungsvariable `HUE_TASK_CONFIG`, sonst Standardpfad. Relative Pfade beziehen sich auf das Arbeitsverzeichnis des Prozesses. Für MCP-Clients sind absolute Pfade am zuverlässigsten.

```powershell
.\.venv\Scripts\python.exe -m hue_task_mcp --config C:/HueConfig/hue.local.json pair --bridge 192.168.1.20
.\.venv\Scripts\python.exe -m hue_task_mcp --config C:/HueConfig/hue.local.json lights
.\.venv\Scripts\python.exe -m hue_task_mcp --config C:/HueConfig/hue.local.json select LIGHT_UUID
.\.venv\Scripts\python.exe -m hue_task_mcp --config C:/HueConfig/hue.local.json serve
```

`--config` ist ein globales Argument und muss **vor dem Unterbefehl** stehen. Alternativ:

```powershell
$env:HUE_TASK_CONFIG = 'C:/HueConfig/hue.local.json'
.\.venv\Scripts\python.exe -m hue_task_mcp serve
```

| Feld | Pflicht | Bedeutung |
| --- | --- | --- |
| `bridge_ip` | Ja | Vom Code akzeptierte private IPv4-Adresse; keine URL, kein Port, kein Hostname oder IPv6 |
| `application_key` | Ja | Durch `pair` erzeugter Bridge-Schlüssel |
| `light_id` | Für Signale | v2-Light-UUID, gespeichert durch `select` |
| `color_mix` | Nein | Fließkommazahl von `0.05` bis `0.5`, Standard `0.22` |
| `ca_file` | Nein | Pfad zu einem passenden vertrauenswürdigen CA-Bundle für Bridge-HTTPS |

Vorlage: [hue.example.json](../examples/hue.example.json). Nur Beispielwerte sind dort enthalten. Unbekannte Felder werden nicht als Schemafehler zurückgewiesen, bewirken aber nichts. `color_mix` wird beim Signal geprüft, nicht beim Laden.

`pair` schreibt eine neue Konfiguration. Bei gleicher Bridge-IP wird eine vorhandene `light_id` übernommen. Optionale Felder wie `color_mix` und `ca_file` werden nicht übernommen. Ein Serverneustart ist für Dateianpassungen nicht nötig, da jedes MCP-Werkzeug die Datei neu lädt.

## CLI

Aufruf: `python -m hue_task_mcp [--config PATH] BEFEHL`. Nach der Paketinstallation ist auch `hue-task-mcp` als Konsolenbefehl verfügbar.

| Befehl | Argumente | Verhalten |
| --- | --- | --- |
| `discover` | Keine | JSON-Liste aus `https://discovery.meethue.com` ausgeben |
| `pair` | `--bridge IP` | Neue Bridge-Autorisierung über physischen Tastendruck erstellen |
| `lights` | Keine | Pro Leuchte eine JSON-Zeile: UUID, Name, Farbe, Gradient, Modus |
| `select` | `LIGHT_UUID` | Farbfähigkeit prüfen und Ziel-UUID speichern |
| `signal` | `done` oder `question` | Ein Signal ausführen und Ergebnis ausgeben |
| `serve` | `--transport stdio` oder `streamable-http`, optional `--port` | MCP-Server starten |
| `hook` | `Stop`, `PreToolUse`, `done` oder `question` | Antigravity Lifecycle Hook Handler (signalisiert und gibt `{"decision": "allow"}` aus) |
| `setup` | Optional `--global`, `--path PATH`, `--uninstall` | Automatische Einrichtung der `hooks.json` für Antigravity CLI |

`serve` verwendet standardmäßig stdio. `--port` gilt nur für HTTP, Standard `8765`. HTTP bindet fest an `127.0.0.1`, Pfad `/mcp`; es gibt keinen `--host`-Parameter. Erfolgreiche einmalige Befehle enden mit Status 0. Abgefangene Konfigurations-/Bridge-Fehler enden mit Status 1. Nicht alle Betriebssystem- und Bibliotheksfehler werden in kurze CLI-Meldungen umgewandelt.

`setup` richtet Antigravity Lifecycle Hooks in `.agents/hooks.json` (lokal) oder mit `--global` in `%USERPROFILE%\.gemini\config\hooks.json` ein. Dadurch werden `Stop` (Aufgabe beendet -> Blau) und `PreToolUse` (Rückfrage via `ask_question` -> Rot) deterministisch auf Systemebene ausgelöst, ohne dass LLM-Regeln erforderlich sind.

## MCP-Werkzeuge

Alle Werkzeuge haben **keine Eingabeparameter**. Bridge-IP, Schlüssel, Licht und Intensität stammen ausschließlich aus der lokalen Datei. Der Agent kann kein beliebiges Ziellicht anfordern.

### `task_done`

Genau einmal unmittelbar vor der Abschlussantwort für eine erfolgreich abgeschlossene Aufgabe aufrufen. Typisches Nutzdatenergebnis:

```json
{
  "event": "done",
  "pattern": "blue_color_blend",
  "pulses": 2,
  "mix": 0.22,
  "restored": true
}
```

### `needs_input`

Genau einmal unmittelbar vor einer Frage aufrufen, für die eine Nutzerantwort erforderlich ist. Dasselbe Ergebnisschema mit `event: "question"` und `pattern: "red_color_blend"`.

Bei ausgeschaltetem Licht liefern beide Werkzeuge stattdessen:

```json
{"event": "question", "skipped": true, "reason": "light_is_off"}
```

Farb-, Streaming- und Szenenprüfungen erfolgen vor der Aus-Prüfung. Eine ausgeschaltete Leuchte kann deshalb bei einem unzulässigen Modus trotzdem einen Fehler melden.

`restored: true` bestätigt angenommene Wiederherstellungsbefehle, keine zusätzliche Messung des endgültigen physischen Zustands. Die MCP-SDK-Version bestimmt den äußeren Content-/Fehler-Envelope; oben steht nur das fachliche Nutzdatenergebnis.

### `light_status`

Liest die ausgewählte Leuchte ohne Lichtänderung. Rückgabefelder: `name`, `state` mit `on`, `mode`, `color`, `brightness`, `temperature`, `gradient`, `effects`. Die letzten drei Fähigkeitsfelder und die Effektliste hängen von der Bridge-Antwort ab. Ohne ausgewähltes Licht: `{"paired": true, "light_selected": false}`. Ohne Pairing-Konfiguration wird ein Fehler gemeldet; der Server bietet keinen anonymen Hardwarestatus.

## Feste Signalparameter

| Parameter | Implementierung |
| --- | --- |
| Blaue Zielfarbe | CIE xy `(0.153, 0.048)` |
| Rote Zielfarbe | CIE xy `(0.675, 0.322)` |
| Mischung | `aktuell + color_mix * (ziel - aktuell)` je Achse |
| Farbverläufe | Zwei je Aufruf |
| Hinweg | Bridge-Transition 1.000 ms, danach 1,25 s warten |
| Rückweg | Originalzustand mit 1.000 ms Transition, danach 1,15 s warten |
| Abschließende Sicherung | Originalzustand mit 800 ms Transition, danach 0,8 s warten |
| Wiederholungen der Sicherung | Bis zu drei Versuche, 0,5 s Abstand nach Fehler |
| HTTP-Anfrage an Bridge | Acht Sekunden Timeout pro Anfrage |
| Prozessübergreifende Sperre | Bis zu 60 s warten, alle 0,1 s erneut versuchen |

Die Übergangskurve wird von Hue ausgeführt; es gibt keine selbst berechnete Easing-Kurve, FPS-Steuerung oder konfigurierbare Pulszahl. Die sichtbare Mischung ist keine lineare RGB-/Prozent-Helligkeitsmischung. Bei Weißtemperaturbetrieb verwendet der Hinweis die gemeldete `color.xy`; danach wird die ursprüngliche gültige Weißtemperatur wiederhergestellt.
