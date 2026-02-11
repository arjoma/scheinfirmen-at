# Changelog

Alle nennenswerten Änderungen an diesem Projekt werden in dieser Datei dokumentiert.

Das Format basiert auf [Keep a Changelog](https://keepachangelog.com/de/1.0.0/),
und dieses Projekt hält sich an [Semantic Versioning](https://semver.org/lang/de/).

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
