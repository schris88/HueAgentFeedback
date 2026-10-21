# Änderungsverlauf

## 0.2.1 — Lautlose Hintergrundausführung unter Windows

- Unter Windows wird für Hooks nun automatisch `pythonw.exe` statt `python.exe` konfiguriert.
- Dadurch öffnet sich bei Hook-Aufrufen (`Stop`, `PreToolUse`) kein CMD- oder Terminal-Fenster mehr im Vordergrund.
- Hintergrund-Signale nutzen `CREATE_NO_WINDOW` und `close_fds=True`, wodurch Hooks sofort (~100 ms) ohne Blockieren oder Fensterbildung zurückkehren.

## 0.2.0 — HueAgentFeedback (Lifecycle Hooks)

- Projekt umbenannt in **HueAgentFeedback** (`hue-agent-feedback`).
- Umstellung auf reine **Lifecycle Hooks** (Antigravity CLI, Claude Code, Cursor) ohne MCP-Server-Overhead.
- Vollständige Entfernung externer Bibliotheken (**Zero Dependencies** — 100 % Python-Standardbibliothek).
- Antigravity CLI Lifecycle Hooks (`hook Stop` -> Blau, `hook PreToolUse: ask_question` -> Rot).
- Vollautomatisches Setup via `hue-agent-feedback setup [--global]`.
- Neuer Befehl `hue-agent-feedback status` zum Auslesen des Lampenzustands.
- Ausgeschaltete Leuchten werden sofort erkannt und bleiben garantiert aus.
- Umfassende Unit-Tests für Hooks, Status und Setup (`tests/test_cli.py`).
- Detaillierte Dokumentation für Antigravity CLI, Claude Code, Cursor und CLI-Agenten.

## 0.1.0 — ursprüngliche lokale Implementierung

- Hue-Bridge-Pairing, Leuchtenauswahl und MCP-Werkzeuge.
- Zwei sanfte blaue/rote Farbmischungen bei unveränderter Helligkeit.
- Gradient-Punkte, lokale Prozesssperren und bestmögliche Zustandswiederherstellung.
- Asynchrone Tests und CI-Definition für Windows/Linux.
