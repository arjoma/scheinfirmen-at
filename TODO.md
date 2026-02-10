# TODO: Scheinfirmen Österreich

## Erledigt

- [x] Python-Paket `scheinfirmen-at` mit CLI
- [x] Download von BMF mit Retry-Logik
- [x] Strenge Validierung (Fehlermeldungen + Warnungen)
- [x] CSV-Output (UTF-8 BOM, kommagetrennt, Excel-kompatibel)
- [x] JSONL-Output (Metadaten erste Zeile, JSON Schema)
- [x] XML-Output (mit XSD)
- [x] Kreuz-Format-Verifizierung
- [x] GitHub CI (Lint + Tests, Python 3.10/3.11/3.12)
- [x] GitHub Action: tägliches Update um 3 Uhr MEZ

## Offen

- [ ] PyPI-Veröffentlichung als `scheinfirmen-at`
  - [ ] PyPI API Token in GitHub Secrets hinterlegen
  - [ ] Release-Workflow (`.github/workflows/release.yml`)
  - [ ] Versionierung (z.B. CalVer: `2026.02`)
- [ ] Historische Daten: Git-History enthält Zeitverlauf — Tools dafür?
- [ ] Differenz-Bericht: welche Firmen wurden hinzugefügt/entfernt?
  - [ ] Bei jedem Update ein Diff-Summary in der Commit-Message
- [ ] SQLite-Output als zusätzliches Format
- [ ] Tests für CLI (`test_cli.py`)
- [ ] Automatischer GitHub-Release bei Datenänderung
