# Änderungsverlauf

## Unreleased

- Antigravity CLI Lifecycle Hooks (`hook` und `setup` Unterbefehle) nach dem Vorbild von Tiny Engineer implementiert.
- Deterministische Signale auf Systemebene: `Stop` (Aufgabe beendet -> Blau) und `PreToolUse: ask_question` (Rückfrage -> Rot) ganz ohne Prompt-Regeln oder Tokenverbrauch.
- Vollautomatisches Setup via `python -m hue_task_mcp setup [--global]`.
- Ausgeschaltete Leuchten werden sofort übersprungen und bleiben garantiert aus.
- Umfassende Unit-Tests für Hooks und Setup in `tests/test_cli.py`.
- Vollständige deutsche Einrichtungsanleitung für neue Nutzer ergänzt.
- Codex-, Antigravity- und Linux/macOS-Konfigurationsvorlagen sowie eine Konfiguration mit Platzhaltern ergänzt.
- CLI-/MCP-Referenz, Architektur, Sicherheitsmodell, Fehlerhilfe und Entwicklungsanleitung hinzugefügt.
- Optionales Publish-Skript: GitHub-Benutzername ist nicht mehr fest eingebaut; Dokumentation wird beim Staging berücksichtigt.
- README in die Python-Paketbeschreibung aufgenommen.

## 0.1.0 — ursprüngliche lokale Implementierung

- Hue-Bridge-Pairing, Leuchtenauswahl und drei MCP-Werkzeuge.
- Zwei sanfte blaue/rote Farbmischungen bei unveränderter Helligkeit.
- Gradient-Punkte, lokale Prozesssperren und bestmögliche Zustandswiederherstellung.
- stdio und lokales Streamable HTTP.
- Asynchrone Tests und CI-Definition für Windows/Linux.

Die Versionsnummer beschreibt den Quellstand; es wird damit keine Veröffentlichung auf PyPI oder eine GitHub-Release behauptet.
