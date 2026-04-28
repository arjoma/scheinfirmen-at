# Changelog

Alle nennenswerten Änderungen an diesem Projekt werden in dieser Datei dokumentiert.

Das Format basiert auf [Keep a Changelog](https://keepachangelog.com/de/1.0.0/),
und dieses Projekt hält sich an [Semantic Versioning](https://semver.org/lang/de/).

## [1.5.0] - 2026-04-28

### Hinzugefügt
- **Auto-Korrektur fehlplatzierter Felder (`normalize.py`):** Vor der Validierung erkennt und repariert das Tool jetzt vier häufige BMF-Tippfehler in den Feldern UID, Firmenbuch und Kennziffer. Ziel: nachgelagerte Tools (z. B. UID-Lookups) bekommen konsistente Daten, auch wenn das BMF Werte in die falsche Spalte tippt.
  - **UID ↔ Kennziffer tauschen:** wenn jede Spalte einen Wert nach dem Muster der jeweils anderen enthält (oder eine leer ist und die andere fehlplatziert).
  - **Doppelte Kennziffer löschen:** wenn die Kennziffer ein exaktes Duplikat von UID oder Firmenbuch-Nr ist.
  - **Ausländische EU-VAT in UID übernehmen:** wenn in der Kennziffer-Spalte eine Nicht-AT-VAT-Nummer steht (z. B. `RO38488384`) und die UID-Spalte leer ist.
  - Jeder angewandte Fix wird mit `WARNING: NORMALIZE: …` geloggt.
- **README:** Neuer Abschnitt "Auto-Korrektur fehlplatzierter Felder" mit Beispielen.

### Geändert
- **Validierung:** UID-Werte werden jetzt sowohl im österreichischen Format (`ATU` + 8 Ziffern) als auch im allgemeinen EU-VAT-Format (`[A-Z]{2}[A-Z0-9]{6,12}`, z. B. `RO38488384`, `DE123456789`) als gültig akzeptiert. Komplett unbekannte Formate werden als Warnung (nicht mehr Fehler) gemeldet, sodass der tägliche Update-Workflow nicht mehr durch BMF-Tippfehler blockiert wird.
- **JSON-Schema:** Das `uid`-Pattern wurde von `^ATU\d{8}$` auf `^[A-Z]{2}[A-Z0-9]{6,12}$` erweitert, damit ausländische EU-VAT-Nummern in der UID-Spalte zulässig sind.

## [1.4.0] - 2026-02-18

### Geändert
- **Statistiken:** Umstellung von wöchentlicher (git-basierter) auf monatliche (veröffentlichungsdatum-basierte) Auswertung in `STATS.md`.
- **Statistiken:** Blockquote-Header durch Tabelle ersetzt, Anzahl-Fußzeile entfernt.
- **Codequalität:** Diverse Code-Quality-Verbesserungen, Testabdeckung auf 96 % erhöht.

### Behoben
- **Statistiken:** Mermaid-Syntaxfehler bei leeren x-Achsen-Labels und kategorischer vs. numerischer Achse behoben.

### Hinzugefügt
- **Release-Prozess:** Dokumentation und `/release`-Skill für automatisierte Releases.

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
