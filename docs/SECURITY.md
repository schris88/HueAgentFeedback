# Sicherheit und Datenschutz

[Zur README](../README.md)

## Berechtigungen und Datenfluss

Der Pairing-Befehl registriert nach einem physischen Tastendruck eine eigene Anwendung bei der Hue Bridge. Der resultierende Schlüssel erlaubt Bridge-weite Steuerung. Hue beschränkt diesen Schlüssel nicht auf eine einzelne Leuchte. Die drei MCP-Werkzeuge wählen ausschließlich das lokal konfigurierte Licht; bei Änderung des Codes oder Diebstahl des Schlüssels gilt diese Beschränkung nicht.

Die Bridge-IP, der Schlüssel und die Ziel-UUID werden lokal gespeichert. Normale Bridge-Requests senden den Schlüssel im Header `hue-application-key` über HTTPS an die konfigurierte Bridge, nicht in einem URL-Pfad. Die automatische Suche ruft `discovery.meethue.com` auf. Python-Paketinstallation greift auf Paketquellen zu. Das optionale Publish-Skript greift nur bei Ausführung auf GitHub zu.

Es gibt keine eingebaute Telemetrie, Chat-Aufzeichnung oder Screenshot-Erfassung. MCP-Clients und ein eventuell genutzter Tunnel haben eigene Daten-/Protokollierungsregeln. `light_status` gibt den Leuchtennamen, Status und Fähigkeiten an den Client weiter, aber keine Bridge-Anmeldedaten.

## Lokale Dateien

`*.local.json`, `.env`, `*.lock` und `.venv` sind in Git ignoriert. Das schützt nicht gegen `git add -f`, bereits getrackte Dateien, anders benannte eigene Konfigurationen oder manuelles Hochladen. Beispielkonfigurationen enthalten ausschließlich Platzhalter.

`save_config` schreibt zunächst eine temporäre Datei mit der Endung `.tmp` und ersetzt dann die Zielkonfiguration. Solche temporären Dateien können bei einem Fehler liegen bleiben. Vor einer Veröffentlichung auch diese prüfen. Unter POSIX erhält die fertige Konfiguration Modus `0600`; es gibt keine entsprechende eigene Windows-ACL-Konfiguration. Unter Windows gelten die vorhandenen Ordnerberechtigungen. Der Schlüssel wird nicht verschlüsselt gespeichert.

Die Konfiguration nicht in einen allgemein beschreibbaren oder öffentlich synchronisierten Ordner legen. Ein anderer lokaler Prozess mit Dateizugriff kann den Schlüssel lesen oder das Ziel ändern. Für neue Installationen `--config` mit einem geschützten Benutzerordner verwenden, wenn der Projektordner geteilt wird.

## Bridge-TLS

Standardmäßig wird für die Bridge ein HTTPS-Kontext ohne Zertifikatsprüfung verwendet. Das vermeidet Probleme mit lokalen Bridge-Zertifikaten, authentifiziert die Bridge aber nicht kryptografisch. Ein manipulierter Netzwerkpfad kann daher ein Risiko darstellen.

Optional `ca_file` auf ein geeignetes vertrauenswürdiges Bundle setzen. Dann nutzt der Runtime-Adapter `ssl.create_default_context`: Zertifikatskette und Host-/IP-Identität werden geprüft. Nicht jede Bridge-/Firmware-Konfiguration lässt sich allein durch Hinzufügen einer CA damit verbinden. Das Projekt automatisiert weder Zertifikatsbeschaffung noch Fingerprint-Pinning. Der **Pairing-Pfad** verwendet unabhängig davon derzeit weiterhin deaktivierte Zertifikatsprüfung.

Keine globale TLS-Einstellung wird verändert. Adressen werden mit `ipaddress` auf eine private IPv4-Adresse geprüft. Dies ist keine zusätzliche Firewall und kein Schutz gegen unbefugte Änderungen der lokalen Konfiguration.

## MCP- und HTTP-Zugriff

stdio ist für lokale Clients vorgesehen. Der HTTP-Modus bindet nur an `127.0.0.1`; er implementiert keinen eigenen Login, API-Token oder OAuth-Server. Andere lokale Prozesse können einen erreichbaren Loopback-Dienst ansprechen. Er gehört nicht direkt ins öffentliche Internet.

Eine private ChatGPT-Verbindung kann über den offiziellen Secure MCP Tunnel hergestellt werden. Der Tunnel und die zugehörigen Kontoberechtigungen müssen separat eingerichtet werden. Einen öffentlichen Zugang erst mit geeigneter Authentifizierung, TLS, Zugriffsregeln und passender MCP-Konfiguration betreiben; dies ist keine mitgelieferte Deployment-Variante.

## Betrieb und Widerruf

Der Server führt echte Lichtänderungen aus. Die Wiederherstellung hat Grenzen bei Stromausfall, hartem Prozessende, Netzwerkfehlern und konkurrierenden Apps. Keine sicherheitskritischen Alarme darauf aufbauen.

Wenn eine Konfiguration versehentlich geteilt wurde, den Bridge-Schlüssel über eine geeignete Bridge-Verwaltung widerrufen und die Anwendung erneut koppeln. Nur aus Git zu entfernen löscht ihn nicht aus der Historie und widerruft ihn nicht. GitHub-Zugangsdaten des Publish-Skripts stammen aus dem Git-Credential-Helper, werden im Speicher genutzt und nicht absichtlich als Datei oder Log ausgegeben.
