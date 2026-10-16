# HueAgentFeedback

Dezente Philips-Hue-Lichtsignale für KI-Assistenten: Der Monitor-Lightstrip zeigt an, dass eine Aufgabe fertig ist oder eine Rückfrage auf deine Antwort wartet.

| Werkzeug / Event | Wirkung |
| --- | --- |
| `task_done` / `Stop` | Zweimal langsam etwas Blau in die aktuelle Farbe mischen |
| `needs_input` / `PreToolUse` | Zweimal langsam etwas Rot in die aktuelle Farbe mischen |
| `light_status` | Zustand und Fähigkeiten der ausgewählten Leuchte lesen |

Die Helligkeit bleibt unverändert. Statt harter Blitze gibt es sanfte Farbverläufe mit anschließender Wiederherstellung des vorherigen Zustands. Standardmäßig werden 22 % der Zielfarbe in die aktuellen CIE-xy-Farbkoordinaten gemischt. Vorhandene Gradient-Farbpunkte werden einzeln gemischt. **Ausgeschaltete Leuchten bleiben garantiert aus** (kein Aufwecken oder Verändern eines dunklen Raums).

### Zwei Betriebsmodi
1. **Antigravity CLI Lifecycle Hooks (empfohlen)**: Wie beim [Tiny Engineer](https://github.com/jamro/tiny-engineer) klinkt sich `HueAgentFeedback` direkt in die Antigravity-Lebenszyklus-Events ein (`Stop` und `PreToolUse: ask_question`). Das Signal erfolgt **100 % deterministisch auf Systemebene**, ganz ohne Tokenverbrauch oder Prompt-Regeln. Einrichtung: `python -m hue_task_mcp setup --global`.
2. **Klassische MCP-Werkzeuge**: Für Clients wie Codex oder manuelle Werkzeugaufrufe (`task_done`, `needs_input`, `light_status`). Hierbei instruieren Agent-Anweisungen das Sprachmodell.

## Dokumentation

- [Konfiguration, CLI und MCP-Referenz](docs/REFERENCE.md)
- [Architektur und Ablauf](docs/ARCHITECTURE.md)
- [Fehlerbehebung und Betrieb](docs/TROUBLESHOOTING.md)
- [Sicherheit und Datenschutz](docs/SECURITY.md)
- [Entwicklung, Tests und Erweiterungen](docs/DEVELOPMENT.md)
- [Agent-Anweisungen zum Kopieren](examples/agent-instructions.md)
- [Änderungsverlauf](CHANGELOG.md)

## Voraussetzungen

- Python **3.11 oder neuer**, `pip` und `venv`.
- Hue Bridge mit v2-API und lokaler IPv4-Adresse im erreichbaren Netzwerk.
- Eine an der Bridge angemeldete **farbfähige** Hue-Leuchte oder ein farbfähiger Lightstrip. Reine Weißlicht-Leuchten reichen nicht aus.
- Zugriff auf die physische Bridge-Taste für die erste Kopplung.
- Ein MCP-Client mit lokaler stdio-Unterstützung, beispielsweise Antigravity CLI oder Codex. ChatGPT im Browser benötigt eine separate Verbindung.
- Internet zum Installieren der Abhängigkeiten. Die Bridge-Suche verwendet ebenfalls einen Internetdienst; mit bekannter IP erfolgen Kopplung und Lichtsteuerung lokal.

Die Hue-Sync-PC-App muss nicht laufen. Bluetooth ohne Bridge wird nicht unterstützt. Aktives Entertainment/Sync und dynamische Szenen müssen für die ausgewählte Leuchte pausiert sein.

Die Anleitung verwendet **Windows PowerShell**. Unter Linux/macOS `.venv/Scripts/python.exe` durch `.venv/bin/python` ersetzen. Physisch getestet wurde unter Windows; die CI ist für Windows und Linux konfiguriert.

## 1. Installieren

```powershell
git clone https://github.com/schris88/HueAgentFeedback.git
cd HueAgentFeedback
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -e .
.\.venv\Scripts\python.exe -m hue_task_mcp --help
```
.\.venv\Scripts\python.exe -m hue_task_mcp --help
```

Die virtuelle Umgebung muss nicht aktiviert werden. Alle Befehle verwenden den Interpreter direkt. Bei einem späteren Umzug des Projektordners die venv neu erstellen und Client-Pfade anpassen.

## 2. Bridge finden und koppeln

```powershell
.\.venv\Scripts\python.exe -m hue_task_mcp discover
```

Die Ausgabe enthält `internalipaddress`. Alternativ die Bridge-IP in der Hue-App oder im Router nachsehen. `192.168.1.20` ist hier nur ein Beispiel:

```powershell
.\.venv\Scripts\python.exe -m hue_task_mcp pair --bridge 192.168.1.20
```

**Während der Befehl wartet, die physische Bridge-Taste drücken.** Es gibt 45 Kopplungsversuche mit jeweils zwei Sekunden Abstand; Netzwerkwartezeiten können die Gesamtdauer verlängern.

Bei Erfolg wird im Projektordner `hue.local.json` gespeichert. Sie enthält deinen persönlichen Bridge-Schlüssel und wird von Git ignoriert. Jeder Nutzer koppelt seine eigene Bridge. Die Datei nicht weitergeben.

## 3. Leuchte auswählen und testen

```powershell
.\.venv\Scripts\python.exe -m hue_task_mcp lights
```

Die Zeile der gewünschten Leuchte mit `"color": true` suchen. Ihre `id` ist eine **v2-Light-UUID**, keine alte numerische Hue-ID. Im folgenden Befehl `LIGHT_UUID` durch diesen vollständigen Wert ersetzen:

```powershell
.\.venv\Scripts\python.exe -m hue_task_mcp select LIGHT_UUID
.\.venv\Scripts\python.exe -m hue_task_mcp signal done
.\.venv\Scripts\python.exe -m hue_task_mcp signal question
```

Zum Test die gewählte Leuchte einschalten. Erwartet werden zuerst zwei blaue, danach zwei rote Farbschwenks, jeweils mit Rückkehr zum vorherigen Zustand. Ein Signal dauert ohne Netzwerkverzögerung ungefähr **5,6 Sekunden**. Wenn die CLI funktioniert, ist die Bridge-Verbindung bereit; die Client-Integration folgt separat.

## 4. Codex einrichten

In `%USERPROFILE%\.codex\config.toml` diesen Abschnitt ergänzen. Vorhandene Konfiguration erhalten, Pfade ersetzen und denselben Abschnitt nicht doppelt anlegen:

```toml
[mcp_servers.hue-task]
command = 'C:/dev/hue-task-mcp/.venv/Scripts/python.exe'
args = ["-m", "hue_task_mcp", "serve"]
cwd = 'C:/dev/hue-task-mcp'
startup_timeout_sec = 20
tool_timeout_sec = 60
```

Die [Agent-Anweisungen](examples/agent-instructions.md) an `%USERPROFILE%\.codex\AGENTS.md` anhängen. Bestehende Regeln erhalten. Eine nicht leere globale `AGENTS.override.md` hat Vorrang; die Regeln müssen in der tatsächlich geladenen Datei stehen.

**Codex vollständig neu starten und einen neuen Chat öffnen.** Testprompt:

> Verwende das Hue-MCP-Werkzeug needs_input einmal und stelle mir danach eine kurze Testfrage.

Es sollten drei Werkzeuge verfügbar sein: `task_done`, `needs_input`, `light_status`. Die normalen Berechtigungsdialoge des Clients beachten. Codex startet den stdio-Server bei Bedarf; kein eigenes Terminal, Autostart, Tunnel oder OpenAI-API-Schlüssel ist für diese lokale Integration erforderlich.

[Offizielle MCP-Anleitung](https://learn.chatgpt.com/docs/extend/mcp?surface=cli) · [Agent-Anweisungen](https://learn.chatgpt.com/docs/agent-configuration/agents-md) · [Konfigurationsvorlage](examples/codex-config.toml)

## 5. Antigravity CLI einrichten

Für Antigravity CLI gibt es zwei Einbindungsvarianten:

### Variante A: Lifecycle Hooks (empfohlen, wie Tiny Engineer)

Wie beim [Tiny Engineer](https://github.com/jamro/tiny-engineer) reagiert das System direkt auf Lebenszyklus-Ereignisse der CLI über `hooks.json`. Dadurch signalisiert das Licht **vollautomatisch und deterministisch**, ohne dass Prompt-Regeln (`GEMINI.md`) oder LLM-Entscheidungen nötig sind:
* **`Stop`**: Löst bei Aufgabenabschluss automatisch blaues Blinken aus.
* **`PreToolUse` auf `ask_question`**: Löst vor Benutzer-Rückfragen automatisch rotes Blinken aus.

Die Einrichtung erfolgt mit einem einzigen Befehl:

```powershell
# Global für alle Projekte einrichten (~/.gemini/config/hooks.json):
.\.venv\Scripts\python.exe -m hue_task_mcp setup --global

# Oder nur für das aktuelle Projekt (.agents/hooks.json):
.\.venv\Scripts\python.exe -m hue_task_mcp setup
```

Der Befehl erstellt oder ergänzt die Konfiguration in `hooks.json` automatisch:

```json
{
  "hue-task": {
    "Stop": [
      {
        "type": "command",
        "command": "\"C:/dev/hue-task-mcp/.venv/Scripts/python.exe\" -m hue_task_mcp --config \"C:/dev/hue-task-mcp/hue.local.json\" hook Stop",
        "timeout": 15
      }
    ],
    "PreToolUse": [
      {
        "matcher": "ask_question",
        "hooks": [
          {
            "type": "command",
            "command": "\"C:/dev/hue-task-mcp/.venv/Scripts/python.exe\" -m hue_task_mcp --config \"C:/dev/hue-task-mcp/hue.local.json\" hook PreToolUse",
            "timeout": 15
          }
        ]
      }
    ]
  }
}
```

Zum Deinstallieren der Hooks einfach `--uninstall` an den Setup-Befehl übergeben.

### Variante B: Klassischer MCP-Server

Alternativ kann `hue-task` als klassischer MCP-Server in `%USERPROFILE%\.gemini\config\mcp_config.json` unter `mcpServers` registriert werden:

```json
{
  "mcpServers": {
    "hue-task": {
      "command": "C:/dev/hue-task-mcp/.venv/Scripts/python.exe",
      "args": ["-m", "hue_task_mcp", "serve"],
      "cwd": "C:/dev/hue-task-mcp"
    }
  }
}
```

Hierbei müssen die [Agent-Anweisungen](examples/agent-instructions.md) in `%USERPROFILE%\.gemini\GEMINI.md` aufgenommen werden, damit das Modell weiß, wann es die Werkzeuge aufrufen soll. Mit `/mcp` kann der Serverstatus geprüft werden.

[Offizielle Antigravity-Anleitung](https://antigravity.google/docs/mcp?tab=cli) · [JSON-Vorlage](examples/mcp_config.json)

## Andere lokale Clients und Linux/macOS

Ein stdio-Client braucht Programm, Argumente und möglichst das Arbeitsverzeichnis. Beispiel: `.venv/Scripts/python.exe`, Argumente `-m hue_task_mcp serve`, Arbeitsverzeichnis der Projektordner. Die jeweiligen Feldnamen hängen vom Client ab.

Unter Linux/macOS `.venv/bin/python` verwenden: [POSIX-Konfigurationsvorlage](examples/mcp_config.posix.json). Falls ein Client kein Arbeitsverzeichnis unterstützt, die editable Installation beibehalten und `HUE_TASK_CONFIG` als absoluten Pfad setzen. Details in der [Referenz](docs/REFERENCE.md).

## ChatGPT im Browser

Ein lokaler Codex-/Antigravity-Eintrag verbindet **nicht automatisch ChatGPT im Browser**. Dort einen eigenen erreichbaren MCP-Zugang einrichten.

Eine von OpenAI dokumentierte private Verbindung ist **Secure MCP Tunnel**. Dafür werden passende Platform-/Workspace-Berechtigungen, eine Tunnel-Konfiguration und ein Runtime-Schlüssel für den offiziellen `tunnel-client` benötigt. Dieser Schlüssel gehört zum Tunnel, nicht zu diesem Hue-Server.

1. In OpenAI Platform einen Tunnel für den vorgesehenen ChatGPT-Workspace einrichten.
2. Den offiziellen `tunnel-client` gemäß OpenAI-Anleitung konfigurieren. Er kann den stdio-Server oder den unten gestarteten HTTP-Server erreichen.
3. In ChatGPT einen eigenen MCP-Server über die angebotene Tunnel-Verbindung hinzufügen und für den Chat verfügbar machen.
4. Die Agent-Anweisungen laden und die Werkzeuge testen.

```powershell
cd C:\dev\hue-task-mcp
.\.venv\Scripts\python.exe -m hue_task_mcp serve --transport streamable-http --port 8765
```

Endpunkt: `http://127.0.0.1:8765/mcp`. Der Prozess muss während der HTTP-Nutzung laufen. Er bietet selbst keine Benutzeranmeldung und bindet nur an Loopback. Keine öffentliche Portweiterleitung einrichten. Verfügbarkeit und Dialoge richten sich nach dem aktuellen OpenAI-Angebot.

[Tunnel-Anleitung](https://developers.openai.com/api/docs/guides/secure-mcp-tunnels) · [Eigenen MCP-Server hinzufügen](https://developers.openai.com/api/docs/guides/custom-mcp-server)

## Signalstärke anpassen

In der bestehenden `hue.local.json` das Feld `color_mix` ändern oder ergänzen. Den echten Schlüssel und die UUID erhalten:

```json
{
  "bridge_ip": "192.168.1.20",
  "application_key": "YOUR_LOCAL_BRIDGE_KEY",
  "light_id": "00000000-0000-0000-0000-000000000001",
  "color_mix": 0.22
}
```

Das ist ein Muster, keine nutzbare Zugangskonfiguration. Mit `pair` und `select` die echten Werte erzeugen.

| Wert | Wirkung |
| --- | --- |
| `0.10` | Schwächere Farbverschiebung |
| `0.22` | Standard |
| `0.35` | Deutlichere Farbverschiebung |

Erlaubt sind `0.05` bis `0.5`. Die Wahrnehmung hängt von Ausgangsfarbe und Leuchte ab. Pulszahl, Zeiten und Zielfarben sind derzeit im Code festgelegt. Die Konfiguration wird pro Werkzeugaufruf neu gelesen. Nach erneutem Pairing optionale Felder prüfen, da diese nicht übernommen werden.

## Grenzen und Sicherheit

- Ein Ziellicht pro Konfigurationsdatei. Der Bridge-Schlüssel selbst hat trotzdem Bridge-weite Berechtigungen; die Anwendung beschränkt ihre MCP-Werkzeuge auf das gewählte Licht.
- Wiederherstellung erfolgt bestmöglich. Stromausfall, Prozessabbruch, anhaltende Netzwerkfehler und gleichzeitige Änderungen anderer Apps können sie verhindern beziehungsweise überschrieben werden.
- `restored: true` bedeutet, dass die Wiederherstellungsbefehle ohne gemeldeten API-Fehler angenommen wurden. Der Server liest den Zustand danach nicht zur Bestätigung zurück.
- Streaming und dynamische Szenen werden abgelehnt. Erweiterte Effektparameter werden nicht vollständig gesichert.
- Bridge-Zertifikate werden standardmäßig nicht geprüft. Ein passendes CA-Bundle kann als `ca_file` hinterlegt werden; Zertifikatskette und IP-Identität müssen passen. [Details](docs/SECURITY.md)
- Schnelles Video-/Musik-Sync gehört zur separaten Hue-Entertainment-Streaming-API. [Hue-Hinweise](https://developers.meethue.com/new-hue-api/)

## Tests, Updates und Entfernen

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Die Tests brauchen keine echte Bridge und verändern kein Licht. Die CI-Datei definiert Windows/Linux und Python 3.11/3.13; lokale Tests belegen keine Ausführung der gesamten Matrix. [Entwicklungsanleitung](docs/DEVELOPMENT.md)

Nach einem Update `pip install -e .` mit dem venv-Interpreter erneut ausführen und Clients neu starten. Lokale Konfiguration erhalten und den Änderungsverlauf prüfen.

Zum Entfernen den MCP-Eintrag und die hinzugefügten Regeln aus den Clients löschen und laufende Server beenden. Danach kann der Projektordner entfernt werden. Bei Bedarf die Bridge-Autorisierung zusätzlich über eine geeignete Bridge-Verwaltung widerrufen. Nur die lokale Datei zu löschen widerruft den Schlüssel nicht.

## Optional: privates GitHub-Repository

GitHub ist zum Betrieb nicht erforderlich. Zum Erstellen und Pushen eines privaten Repositorys gibt es ein optionales Skript:

```powershell
powershell -ExecutionPolicy Bypass -File .\Publish-PrivateRepo.ps1
```

Es verwendet den Git-Credential-Helper und das authentifizierte persönliche GitHub-Konto. Optional: `-GitHubUsername DEIN_LOGIN` bei mehreren Konten und `-RepositoryName NAME` für einen anderen Namen. Ein funktionierender Git-Push garantiert nicht, dass der gespeicherte Token auch Repositorys per API erstellen darf.

Das Skript verweigert öffentliche Zielrepositorys, abweichende Remotes und getrackte Standard-Konfigurationsdateien; es pusht ohne Force. Es berücksichtigt die Dokumentation. Vor dem Push `git status` und `git diff --cached` prüfen. Keine lokalen Schlüssel oder Logdateien hochladen.

Eine Weitergabe-Lizenz wurde noch nicht festgelegt. Vor einer öffentlichen Veröffentlichung die gewünschte Lizenz ausdrücklich auswählen.
