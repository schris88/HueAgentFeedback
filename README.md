# HueAgentFeedback

Dezente Philips-Hue-Lichtsignale für KI-Coding-Assistenten über native Lifecycle Hooks. Der Monitor-Lightstrip signalisiert auf einen Blick, ob dein Agent fertig ist oder auf deine Antwort wartet.

| Event / Hook | Wirkung |
| --- | --- |
| **Aufgabe beendet** (`Stop`) | Zweimal langsam sanftes Blau in die aktuelle Farbe mischen |
| **Rückfrage an Nutzer** (`PreToolUse: ask_question` / `Notification`) | Zweimal langsam sanftes Rot in die aktuelle Farbe mischen |
| **Statusabfrage** (`status`) | Zustand und Fähigkeiten der ausgewählten Leuchte anzeigen |

### Highlights
* **Reine Lifecycle Hooks statt MCP**: Deterministische Steuerung auf System-/CLI-Ebene (wie bei [Tiny Engineer](https://github.com/jamro/tiny-engineer)). Keine Prompt-Regeln in `GEMINI.md`, kein Tokenverbrauch und keine vergessenen Tool-Aufrufe.
* **Ausgeschaltete Leuchten bleiben aus**: Ist die Leuchte im Raum ausgeschaltet, wird **kein** Befehl an die Bridge gesendet. Ein dunkler Raum bleibt dunkel.
* **Nahtlose Farbwiederherstellung**: Ausgangsfarbe, Farbtemperatur und Gradient-Punkte werden nach dem Signal exakt wiederhergestellt. Helligkeit bleibt unberührt.
* **Zero Dependencies**: Keine externen Frameworks oder MCP-Bibliotheken erforderlich. 100 % Python-Standardbibliothek (Python 3.11+).

---

## Voraussetzungen

- Python **3.11 oder neuer**
- Philips Hue Bridge (v2-API) im lokalen Netzwerk
- Eine **farbfähige** Hue-Leuchte oder ein farbfähiger Lightstrip
- Physischer Zugriff auf die Bridge-Taste für die einmalige Kopplung

---

## 1. Installieren

```powershell
git clone https://github.com/schris88/HueAgentFeedback.git
cd HueAgentFeedback
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -e .
```

*Unter Linux/macOS `.venv/Scripts/python.exe` durch `.venv/bin/python` ersetzen.*

---

## 2. Bridge koppeln & Leuchte auswählen

```powershell
# 1. Bridge im Netzwerk finden
hue-agent-feedback discover

# 2. Koppeln (Taste auf der physischen Hue Bridge drücken, wenn der Befehl wartet)
hue-agent-feedback pair --bridge 192.168.x.x

# 3. Farbfähige Leuchte auflisten und auswählen
hue-agent-feedback lights
hue-agent-feedback select DEINE_LIGHT_UUID

# 4. Status und Signale testen
hue-agent-feedback status
hue-agent-feedback signal done
hue-agent-feedback signal question
```

Die Zugangsdaten werden sicher in `hue.local.json` (automatisch von Git ignoriert) gespeichert.

---

## 3. Lifecycle Hooks für deinen Provider einrichten

### A. Antigravity CLI (Global – empfohlen)

Richtet die Hooks global für alle Projekte auf deinem System ein:

```powershell
hue-agent-feedback setup --global
```

*Oder nur für das aktuelle Projekt:*
```powershell
hue-agent-feedback setup
```

Der Befehl trägt automatisch folgende Konfiguration in `%USERPROFILE%\.gemini\config\hooks.json` (bzw. `.agents/hooks.json`) ein:

```json
{
  "hue-agent-feedback": {
    "Stop": [
      {
        "type": "command",
        "command": "C:/PATH/TO/HueAgentFeedback/.venv/Scripts/python.exe -m hue_agent_feedback --config C:/PATH/TO/HueAgentFeedback/hue.local.json hook Stop",
        "timeout": 15
      }
    ],
    "PreToolUse": [
      {
        "matcher": "ask_question",
        "hooks": [
          {
            "type": "command",
            "command": "C:/PATH/TO/HueAgentFeedback/.venv/Scripts/python.exe -m hue_agent_feedback --config C:/PATH/TO/HueAgentFeedback/hue.local.json hook PreToolUse",
            "timeout": 15
          }
        ]
      }
    ]
  }
}
```

> [!NOTE]
> **Windows-Hinweis:** Antigravity führt Hook-Befehle unter Windows über `cmd.exe /c` aus. Die Pfade zu `python.exe` und der Konfiguration dürfen in `command` **nicht** zusätzlich in Anführungszeichen eingeschlossen werden (außer wenn ein Pfad tatsächlich Leerzeichen enthält), da `cmd.exe` den Befehl sonst mit `Der Befehl "\"..." ist entweder falsch geschrieben` abweist. Der `setup`-Befehl formatiert dies automatisch korrekt.

* **`Stop`**: Feuert automatisch, sobald Antigravity eine Aufgabe erfolgreich oder mit finaler Antwort beendet (**Blau**).
* **`PreToolUse` (Matcher: `ask_question`)**: Feuert unmittelbar vor dem Öffnen eines Nutzer-Fragedialogs (**Rot**).

*Zum Entfernen:* `hue-agent-feedback setup --uninstall`

---

### B. Claude Code

Claude Code unterstützt Lifecycle Hooks in `~/.claude/settings.json` (global) oder `.claude/settings.json` (projektbezogen):

```json
{
  "hooks": {
    "Stop": [
      {
        "type": "command",
        "command": "hue-agent-feedback signal done"
      }
    ],
    "Notification": [
      {
        "type": "command",
        "command": "hue-agent-feedback signal question"
      }
    ]
  }
}
```

Vorlage: [`examples/claude_settings.json`](examples/claude_settings.json)

---

### C. Cursor

Cursor unterstützt Hooks in `.cursor/hooks.json`:

```json
{
  "stop": [
    {
      "command": "hue-agent-feedback signal done"
    }
  ]
}
```

Vorlage: [`examples/cursor_hooks.json`](examples/cursor_hooks.json)

---

### D. OpenAI & andere Clients

* **ChatGPT im Webbrowser**: Läuft in der Cloud und bietet keine lokalen Lifecycle-Hooks.
* **CLI-Agenten (Codex CLI, Aider, Skripte)**: Können die CLI-Befehle direkt vor/nach Ausführungen aufrufen:
  * `hue-agent-feedback signal done`
  * `hue-agent-feedback signal question`

---

## CLI-Referenz

| Befehl | Argumente | Beschreibung |
| --- | --- | --- |
| `discover` | Keine | Hue Bridges im lokalen Netzwerk suchen |
| `pair` | `--bridge IP` | Mit Bridge koppeln (Taste an der Bridge drücken) |
| `lights` | Keine | Verfügbare farbfähige Leuchten auflisten |
| `select` | `LIGHT_UUID` | Ziel-Leuchte auswählen |
| `status` | Keine | Aktuellen Status (Ein/Aus, Helligkeit, Farbe) anzeigen |
| `signal` | `done` oder `question` | Signal manuell auslösen |
| `hook` | `Stop`, `PreToolUse`, `done`, `question` | Antigravity Lifecycle Hook Handler (gibt `{"decision": "allow"}` aus) |
| `setup` | Optional `--global`, `--path PATH`, `--uninstall` | Automatische Einrichtung von `hooks.json` |

---

## Signalstärke anpassen

In `hue.local.json` kann optional `color_mix` angepasst werden (Standard `0.22` = 22 % Farbmischung):

```json
{
  "bridge_ip": "192.168.1.20",
  "application_key": "YOUR_BRIDGE_KEY",
  "light_id": "00000000-0000-0000-0000-000000000001",
  "color_mix": 0.22
}
```

* `0.10`: Sehr dezente Farbverschiebung
* `0.22`: Standard (sanft, gut sichtbar)
* `0.35`: Deutlich kräftigere Farbverschiebung

---

## Tests

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

16 automatisierte Tests prüfen Signal-Timing, Farbmischung, Gradient-Erhaltung, Hook-Entscheidungen und das Überspringen ausgeschalteter Leuchten – ganz ohne physische Bridge.
