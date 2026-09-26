# TODO: Scheinfirmen Österreich

## Erledigt

- [x] Python-Paket `scheinfirmen-at` mit CLI
- [x] Download von BMF mit Retry-Logik
- [x] Strenge Validierung (Fehlermeldungen + Warnungen)
- [x] CSV-Output (UTF-8 BOM, kommagetrennt, Excel-kompatibel)
- [x] JSONL-Output (Metadaten erste Zeile, JSON Schema)
- [x] XML-Output (mit XSD)
- [x] Kreuz-Format-Verifizierung
- [x] GitHub CI (Lint + Tests, Python 3.10/3.13, Ubuntu + Windows)
- [x] GitHub Action: tägliches Update um 3 Uhr MEZ
- [x] PyPI-Veröffentlichung als `scheinfirmen-at` (Trusted Publishing via OIDC)
- [x] Release-Workflow (`.github/workflows/release.yml`, Tag-basiert `v*`)

- [x] Tests für CLI (`test_cli.py`)
- [x] CLI `--stats`: `STATS.md` mit Monatsverlauf und neuesten Einträgen
- [x] Auto-Korrektur fehlplatzierter UID/Firmenbuch/Kennziffer-Werte (`normalize.py`)
- [x] Abgänge protokollieren (`scheinfirmen-entfernt.jsonl`) und in `STATS.md` anzeigen
- [x] `geaendert`-Zeitstempel (echter Datenstand statt BMF-Abrufzeit)

## Offen
- [ ] Atomares Schreiben: Ausgaben erst nach erfolgreicher Verifizierung ins Zielverzeichnis verschieben
- [ ] SQLite-Output als zusätzliches Format
