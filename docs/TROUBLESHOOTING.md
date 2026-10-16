# Fehlerbehebung und Betrieb

[Zur README](../README.md)

## Diagnose in sinnvoller Reihenfolge

1. Im Projektordner mit dem venv-Interpreter `--help` starten.
2. Die Bridge-IP und Erreichbarkeit prüfen; gegebenenfalls `discover` ausführen.
3. `lights` ausführen. Das prüft Pairing und API-Zugriff.
4. Die richtige v2-Light-UUID mit `select` wählen.
5. Leuchte einschalten, Sync/dynamische Szene pausieren und `signal question` manuell testen.
6. Im MCP-Client prüfen, ob alle drei Werkzeuge geladen sind. `light_status` ist der erste Test ohne Lichtänderung.
7. Geladene Agent-Anweisungen und Berechtigungen prüfen, dann den Rückfrage-Testprompt aus der README verwenden.

Erst wenn ein Schritt funktioniert, zur nächsten Ebene wechseln. Kopplung ist nach einem Client-Neustart nicht erneut nötig.

## Häufige Probleme

| Symptom | Ursache / Lösung |
| --- | --- |
| Python wird nicht gefunden oder ist zu alt | Python 3.11+ installieren; `python --version` prüfen. Gegebenenfalls den Windows-Python-Launcher verwenden. |
| `No module named hue_agent_feedback` | Den richtigen venv-Interpreter benutzen und `-m pip install -e .` erneut ausführen. |
| `discover` liefert nichts | Bridge-IP aus Hue-App/Router verwenden. Discovery benötigt Internet und ist keine lokale Netzwerksuche. |
| Pairing läuft ab | Taste während des wartenden Befehls drücken; IP, Bridge-Zugang und lokale Firewall prüfen. |
| `Not paired yet` | Die vom Prozess geladene Konfigurationsdatei fehlt. `cwd`, `--config` und `HUE_TASK_CONFIG` vergleichen. |
| `Select your monitor light first` | `lights` und danach `select UUID` ausführen. |
| UUID-Fehler oder Licht nicht gefunden | Die v2-Light-UUID aus diesem Bridge-`lights`-Aufruf verwenden, keine Geräte-/Raum-ID. |
| Nicht farbfähig | Leuchte mit `color: true` wählen. Weißlicht-Geräte können die Signale nicht anzeigen. |
| `Hue Sync is streaming` | Sync/Entertainment für die Leuchte stoppen und erneut versuchen. Der Server übernimmt den Stream nicht. |
| `Pause the dynamic scene first` | Dynamische Szene in der Hue-App pausieren oder eine statische Einstellung wählen. |
| Erfolg, aber kein sichtbares Signal | `skipped` und `reason` prüfen; ausgeschaltete Leuchten bleiben aus. Bei eingeschaltetem Licht Intensität und Ausgangsfarbe beachten. |
| Farbe ist kaum sichtbar | `color_mix` vorsichtig erhöhen, etwa von `0.22` auf `0.30`; nicht über `0.5`. |
| Licht bleibt verändert | Netzwerk prüfen und ursprüngliche Einstellung in der Hue-App herstellen. Prozess-/Stromausfälle können die Bereinigung verhindern. |
| `Another Hue signal is still running` | Ein Aufruf hält die Sperre länger als 60 s. Netzwerkfehler oder wiederholte Aufrufe prüfen und später einmal erneut versuchen. |
| Sperrdatei bleibt liegen | Normal. Eine vorhandene Datei bedeutet nicht, dass noch eine aktive OS-Sperre besteht. Nicht während laufender Signale löschen. |
| `color_mix must be ...` | JSON-Wert als Zahl zwischen `0.05` und `0.5` setzen. |
| JSON-Fehler | Gültiges JSON ohne Kommentare/Trailing Commas und UTF-8 verwenden. |
| Zertifikatsfehler mit `ca_file` | CA-Bundle, Pfad, Zertifikatskette und IP-Identität prüfen. Ein fremdes Root-Zertifikat reicht nicht aus. |
| CLI funktioniert, Client nicht | Absoluten Interpreterpfad, `cwd`, Tools, Berechtigungen und Agent-Regeln prüfen; Client neu starten. |
| Nur ein Client funktioniert | Beide müssen denselben Code und denselben absoluten Konfigurationspfad laden. |
| HTTP-Port belegt | Anderen Port mit `--port` wählen und den Tunnel-/Client-Endpunkt entsprechend ändern. |
| Git-Push geht, Publish-Skript nicht | API-Berechtigung zum Erstellen privater Repositorys kann fehlen. Auch kann ein Sandbox-Prozess keinen Zugriff auf den Windows-Credential-Store haben. Im eigenen authentifizierten Terminal ausführen oder normal per GitHub Desktop veröffentlichen. |

## Nach Neustart oder Update

Die Bridge-Autorisierung bleibt in der lokalen Konfiguration erhalten. stdio-Clients starten den Server neu. Für HTTP muss der Prozess wieder gestartet werden. Änderungen an Python-Code oder MCP-Einträgen erfordern einen Client-/Serverneustart; Änderungen an `color_mix` werden beim nächsten Aufruf gelesen.

Nach Umzug des Projekts die venv neu erstellen, das Paket erneut editable installieren und alle Client-Pfade anpassen. Die alte Konfiguration nicht versehentlich parallel weiterverwenden.

## Informationen für einen Fehlerbericht

Python-Version, Betriebssystem, Client/Version, genauer Befehl ohne Schlüssel, Fehlermeldung, Streaming-/Szenenstatus und Ergebnis der automatisierten Tests angeben. Keine `hue.local.json`, Bridge-Schlüssel, GitHub-Token oder kompletten Client-Konfigurationen mit Geheimnissen veröffentlichen. Bridge-IP und persönliche Leuchtennamen bei Bedarf schwärzen.
