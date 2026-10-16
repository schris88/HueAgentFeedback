# Entwicklung und Wartung

[Zur README](../README.md)

## Lokale Entwicklungsumgebung

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e .
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Das Paket benötigt Python 3.11+ und hat **keine externen Abhängigkeiten**. Es nutzt ausschließlich die Python-Standardbibliothek (`urllib`, `ssl`, `asyncio`, `json`, `pathlib`, `argparse`).

## Testumfang

* `tests/test_indicator.py`: Testet Signalabläufe, Farbmischungen in CIE-xy, Wiederherstellung, das sofortige Überspringen ausgeschalteter Leuchten, Fehlerbehandlung und Dateisperren mit Fake-Bridges.
* `tests/test_cli.py`: Testet Antigravity Lifecycle Hooks (`hook Stop`, `hook PreToolUse`), Stdin-Verarbeitung, Fehlerresilienz und den automatischen Konfigurationsassistenten (`setup`).

Alle Tests laufen asynchron und verändern keine physischen Leuchten.

## CI

Die CI unter `.github/workflows/tests.yml` installiert das Projekt und führt die Tests unter Windows/Linux mit Python 3.11/3.13 aus.
