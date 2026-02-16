# Changelog

Alle nennenswerten Änderungen an diesem Projekt werden in dieser Datei dokumentiert.

Das Format basiert auf [Keep a Changelog](https://keepachangelog.com/de/1.0.0/),
und dieses Projekt hält sich an [Semantic Versioning](https://semver.org/lang/de/).

## [1.3.0] - 2026-02-16

### Hinzugefügt
- **`--stats` Flag:** Neues CLI-Flag zur Erzeugung eines `STATS.md`-Berichts mit Statistiken über die Scheinfirmen-Daten.
- **W3C CSVW-Metadaten:** Die CSV-Ausgabe wird nun von einer `scheinfirmen.csv-metadata.json` begleitet (W3C CSVW-Standard).
- **CLI-Integrationstests:** 9 neue Tests für die vollständige CLI-Pipeline.

### Behoben
- **CI/CD:** `STATS.md` löst keine falschen Commits im automatisierten Update-Workflow mehr aus.
- **CI/CD:** Shallow-Clone-Behandlung im Update-Workflow korrigiert.

## [1.2.1] - 2026-02-12

### Behoben
- **Abhängigkeiten:** `uv.lock` wurde mit der aktuellen Projektversion synchronisiert.
- **CI/CD:** Der automatisierte Update-Workflow wurde robuster gestaltet (Fehlerbehandlung bei Push-Konflikten).

## [1.2.0] - 2026-02-11

### Hinzugefügt
- **Windows-Support:** Die CI-Pipeline testet nun auch auf Windows, um Kompatibilität sicherzustellen.
- **Dokumentation:** Hinweis zur Installation unter Windows (PowerShell ExecutionPolicy) hinzugefügt.

### Geändert
- **CSV-Format:** Die Kommentarzeile (`# Stand: ...`) in der CSV-Ausgabe wurde entfernt. Dies verbessert die direkte Kompatibilität mit Microsoft Excel, da die Header-Zeile nun korrekt als erste Zeile erkannt wird.
- **Metadaten:** Der Zeitstempel für die automatisierte Aktualisierung wird nun aus der `scheinfirmen.jsonl` (Metadaten-Objekt) extrahiert.
- **User-Agent:** Der User-Agent beim Download wurde korrigiert und zeigt nun auf das `arjoma`-Repository.
- **CI-Zeitplan:** Der automatische Update-Job wurde auf 02:15 UTC (03:15 MEZ) verschoben, um Überlastungen zu vermeiden.

## [1.1.0] - 2026-02-10

### Hinzugefügt
- **XML-Schema:** Die XML-Ausgabe referenziert nun das XSD-Schema (`xsi:noNamespaceSchemaLocation`).
- **Lizenz:** Copyright und Lizenz-Header zu allen Quellcode-Dateien hinzugefügt.

### Behoben
- Diverse kleine Korrekturen in der Konfiguration und Dokumentation.
