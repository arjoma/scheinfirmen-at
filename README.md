# Scheinfirmen Österreich

[![CI](https://github.com/arjoma/scheinfirmen-at/actions/workflows/ci.yml/badge.svg)](https://github.com/arjoma/scheinfirmen-at/actions/workflows/ci.yml)
[![Daten Aktualisieren](https://github.com/arjoma/scheinfirmen-at/actions/workflows/update.yml/badge.svg)](https://github.com/arjoma/scheinfirmen-at/actions/workflows/update.yml)
[![PyPI](https://img.shields.io/pypi/v/scheinfirmen-at)](https://pypi.org/project/scheinfirmen-at/)

Automatischer Download und Konvertierung der österreichischen BMF **Scheinfirmenliste**
(Liste der Scheinunternehmen) in maschinenlesbare Formate.

Die Daten werden täglich um ca. 3:15 Uhr früh (MEZ) automatisch aktualisiert.

> [!WARNING]
> **Haftungsausschluss:** Dieses Projekt ist ein inoffizieller, automatisierter Spiegel
> der BMF-Scheinfirmenliste und steht in keiner Verbindung zum Bundesministerium für
> Finanzen (BMF) Österreich. Die Daten werden ohne jegliche Gewähr bereitgestellt.
> Weder die Vollständigkeit, Richtigkeit noch die Aktualität der Daten wird garantiert.
> Die offizielle und rechtsverbindliche Quelle ist ausschließlich die BMF-Website unter
> https://service.bmf.gv.at/service/allg/lsu/ — diese ist bei rechtlich relevanten
> Entscheidungen zu verwenden. Jegliche Haftung für Schäden, die aus der Verwendung
> dieser Daten entstehen, wird ausgeschlossen.

## Datenquelle

Das österreichische Bundesministerium für Finanzen (BMF) veröffentlicht eine Liste von
Scheinunternehmen (Unternehmen, die für Steuerbetrug oder andere illegale Aktivitäten
missbraucht werden) unter:

- **Webseite:** https://service.bmf.gv.at/service/allg/lsu/
- **CSV:** https://service.bmf.gv.at/service/allg/lsu/__Gen_Csv.asp

Die Daten stehen unter den Nutzungsbedingungen des BMF.

## Output-Dateien

Die konvertierten Daten befinden sich im `data/` Verzeichnis:

| Datei | Format | Beschreibung |
|-------|--------|--------------|
| [`scheinfirmen.csv`](https://raw.githubusercontent.com/arjoma/scheinfirmen-at/main/data/scheinfirmen.csv) | CSV (UTF-8 mit BOM) | Komma-getrennt, Excel-kompatibel |
| [`scheinfirmen.jsonl`](https://raw.githubusercontent.com/arjoma/scheinfirmen-at/main/data/scheinfirmen.jsonl) | JSONL | Eine JSON-Zeile pro Eintrag, erste Zeile Metadaten |
| [`scheinfirmen.xml`](https://raw.githubusercontent.com/arjoma/scheinfirmen-at/main/data/scheinfirmen.xml) | XML | `<scheinfirma>`-Elemente mit Attributen |
| [`scheinfirmen.json-schema.json`](https://raw.githubusercontent.com/arjoma/scheinfirmen-at/main/data/scheinfirmen.json-schema.json) | JSON Schema | Schema-Definition (Draft 2020-12) |
| [`scheinfirmen.xsd`](https://raw.githubusercontent.com/arjoma/scheinfirmen-at/main/data/scheinfirmen.xsd) | XSD | XML Schema Definition |

### Datenfelder

| Feld | Typ | Beschreibung |
|------|-----|--------------|
| `name` | String | Name des Unternehmens oder der natürlichen Person |
| `anschrift` | String | Adresse (PLZ Ort, Straße Nr) |
| `veroeffentlicht` | Datum | Veröffentlichungsdatum (ISO 8601) |
| `rechtskraeftig` | Datum | Datum der Rechtskraft des Bescheids (ISO 8601) |
| `seit` | Datum\|null | Zeitpunkt als Scheinunternehmen (ISO 8601) |
| `geburtsdatum` | Datum\|null | Geburtsdatum (nur bei natürlichen Personen) |
| `fbnr` | String\|null | Firmenbuchnummer (z.B. `597821z`) |
| `uid` | String\|null | UID-Nummer (z.B. `ATU79209223`) |
| `kennziffer` | String\|null | Kennziffer des Unternehmensregisters |

Alle Datumsfelder sind im ISO-8601-Format (`YYYY-MM-DD`).

## Voraussetzungen

Dieses Projekt verwendet [uv](https://docs.astral.sh/uv/) für das Paket- und Dependency-Management. Falls Sie `uv` noch nicht installiert haben, wird dies empfohlen:

```bash
# Installation unter macOS/Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Installation unter Windows (PowerShell)
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
```

Ausführliche Informationen finden Sie in der [uv-Dokumentation](https://docs.astral.sh/uv/getting-started/installation/).

## Direkte Ausführung (ohne Installation)

```bash
uvx scheinfirmen-at -o data/
```

Lädt das Paket von PyPI, führt es aus und cached es lokal — kein manuelles Installieren nötig (analog zu `npx`).

## Installation

```bash
pip install scheinfirmen-at
# oder mit uv:
uv add scheinfirmen-at
# oder als dauerhaftes CLI-Tool:
uv tool install scheinfirmen-at
```

## Verwendung

### Kommandozeile

```bash
# Aktuelle Daten herunterladen und in data/ konvertieren
scheinfirmen-at -o data/

# Mit ausführlicher Ausgabe
scheinfirmen-at -o data/ -v

# Lokale Datei konvertieren (kein Download)
scheinfirmen-at --input rohdaten.csv -o output/

# Hilfe
scheinfirmen-at --help
```

### Python API

```python
from scheinfirmen_at import download_csv, parse_bmf_csv, validate_records
from scheinfirmen_at.convert import write_csv, write_jsonl, write_xml

# Herunterladen und parsen
raw = download_csv()
result = parse_bmf_csv(raw)

# Validieren
validation = validate_records(result)
if not validation.ok:
    for err in validation.errors:
        print(f"Fehler: {err}")

# Ausgabe schreiben
write_csv(result, "scheinfirmen.csv")
write_jsonl(result, "scheinfirmen.jsonl")
write_xml(result, "scheinfirmen.xml")

# Zugriff auf einzelne Einträge
for rec in result.records:
    print(rec.name, rec.uid)
```

## Entwicklung

```bash
# Repository klonen
git clone https://github.com/arjoma/scheinfirmen-at.git
cd scheinfirmen-oesterreich

# Abhängigkeiten installieren (uv)
uv sync

# Tests ausführen
uv run pytest tests/ -v

# Lint
uv run ruff check src/ tests/

# Type-Check
uv run mypy src/
```

## Technische Details

- **Abhängigkeiten:** Keine (reines Python stdlib, >= 3.10)
- **Quell-Encoding:** ISO-8859-1 (Tilde-getrennt, CRLF)
- **Output-Encoding:** UTF-8 (CSV mit BOM für Excel-Kompatibilität)
- **Validierung:** Strenge Feldvalidierung mit Fehlern und Warnungen
- **Schema-Prüfung:** Automatische Validierung gegen XSD (XML) und JSON Schema (JSONL)
- **Verifizierung:** Kreuz-Format-Prüfung (alle Formate müssen gleiche Zeilenanzahl haben)

## Lizenz

Apache License 2.0 — siehe [LICENSE](LICENSE)

Die Scheinfirmenliste selbst ist eine öffentliche Verwaltungsinformation des BMF Österreich.
