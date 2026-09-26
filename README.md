# Scheinfirmen Österreich

[![CI](https://github.com/arjoma/scheinfirmen-at/actions/workflows/ci.yml/badge.svg)](https://github.com/arjoma/scheinfirmen-at/actions/workflows/ci.yml)
[![Daten Aktualisieren](https://github.com/arjoma/scheinfirmen-at/actions/workflows/update.yml/badge.svg)](https://github.com/arjoma/scheinfirmen-at/actions/workflows/update.yml)
[![PyPI](https://img.shields.io/pypi/v/scheinfirmen-at)](https://pypi.org/project/scheinfirmen-at/)

Automatischer Download und Konvertierung der österreichischen BMF **Scheinfirmenliste**
(Liste der Scheinunternehmen) in maschinenlesbare Formate.

> [!NOTE]
> Die Daten werden zweimal täglich automatisch aktualisiert (geplant 06:17 und 14:17 UTC;
> GitHub Actions startet geplante Läufe teils mehrere Stunden verspätet).
> Siehe [**Statistik & neueste Einträge**](data/STATS.md) für den neuesten Stand.

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

Rechtsgrundlage der Veröffentlichung ist § 8 Sozialbetrugsbekämpfungsgesetz (SBBG).
Zur Lizenz der Daten siehe [Lizenz](#lizenz).

## Output-Dateien

Die konvertierten und täglich aktualisierten Daten befinden sich im `data/` Verzeichnis:

| Datei | Format | Beschreibung |
|-------|--------|--------------|
| [`scheinfirmen.csv`](https://raw.githubusercontent.com/arjoma/scheinfirmen-at/main/data/scheinfirmen.csv) | CSV (UTF-8 mit BOM) | Komma-getrennt, Excel-kompatibel ([CSVW](https://raw.githubusercontent.com/arjoma/scheinfirmen-at/main/data/scheinfirmen.csv-metadata.json)) |
| [`scheinfirmen.jsonl`](https://raw.githubusercontent.com/arjoma/scheinfirmen-at/main/data/scheinfirmen.jsonl) | JSONL | Eine JSON-Zeile pro Eintrag, erste Zeile Metadaten ([Schema](https://raw.githubusercontent.com/arjoma/scheinfirmen-at/main/data/scheinfirmen.json-schema.json)) |
| [`scheinfirmen.xml`](https://raw.githubusercontent.com/arjoma/scheinfirmen-at/main/data/scheinfirmen.xml) | XML | `<scheinfirma>`-Elemente mit Attributen ([XSD](https://raw.githubusercontent.com/arjoma/scheinfirmen-at/main/data/scheinfirmen.xsd)) |
| [`scheinfirmen-entfernt.jsonl`](https://raw.githubusercontent.com/arjoma/scheinfirmen-at/main/data/scheinfirmen-entfernt.jsonl) | JSONL | Protokoll der von der Liste entfernten Einträge (siehe [Abgänge](#abgänge-entfernte-einträge)) |
| [`STATS.md`](data/STATS.md) | Markdown | Statistiken, neue und entfernte Einträge, Verlauf |

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

### Metadaten: `stand` vs. `geaendert`

Die erste JSONL-Zeile (`_metadata`) und das XML-Wurzelelement enthalten zwei Zeitstempel:

| Feld | Bedeutung |
|------|-----------|
| `stand` | Die „Stand"-Zeile der BMF-CSV. Das BMF erzeugt sie **bei jedem Abruf neu** — sie ist also der Download-Zeitpunkt, nicht der Datenstand. (XML: `stand` + `zeit`) |
| `geaendert` | Zeitpunkt, an dem sich die Einträge zuletzt tatsächlich geändert haben (ermittelt durch Vergleich mit dem vorherigen Stand). |

Für „wie aktuell ist die Liste?" ist `geaendert` das richtige Feld.

## Abgänge (entfernte Einträge)

Das BMF entfernt Einträge wieder von der Liste. Das Tool vergleicht jeden Download mit
dem vorherigen Stand und hängt verschwundene Einträge an
`data/scheinfirmen-entfernt.jsonl` an — jeweils der vollständige letzte Datensatz plus
Feld `entfernt` (Datum). Korrekturen (z. B. Schreibweise des Namens) werden als Änderung
erkannt und *nicht* als Abgang gezählt. Das Protokoll wurde rückwirkend aus der
Git-History ab Februar 2026 befüllt (`scripts/backfill_removals.py`).

Beobachtung aus den bisherigen Daten: Die meisten Einträge verschwinden ziemlich genau
**fünf Jahre nach der Veröffentlichung**; einige wenige bereits nach Tagen oder Wochen.
Ältere Einträge (ab 2016) sind jedoch weiterhin gelistet — eine feste Regel ist das nicht.

Als Schutz gegen abgeschnittene Downloads bricht das Update ab, wenn mehr als
`--max-removals` Einträge (Standard: 25) auf einmal verschwinden; üblich sind 0–2 pro Tag.

## Voraussetzungen

Dieses Projekt verwendet [uv](https://docs.astral.sh/uv/) für das Paket- und Dependency-Management. Falls Sie `uv` noch nicht installiert haben, wird dies empfohlen:

```bash
# Installation unter macOS/Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Installation unter Windows (PowerShell)
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

Ausführliche Informationen finden Sie in der [uv-Dokumentation](https://docs.astral.sh/uv/getting-started/installation/).

## Direkte Ausführung (ohne Installation)

```bash
uvx scheinfirmen-at@latest -o data/
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

# Statistik-Bericht erzeugen
scheinfirmen-at -o data/ --stats data/STATS.md

# Bewusst viele Abgänge zulassen (z. B. nach einer BMF-Bereinigung)
scheinfirmen-at -o data/ --max-removals 500

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
cd scheinfirmen-at

# Abhängigkeiten installieren (uv)
uv sync

# Tests ausführen
uv run pytest tests/ -v

# Lint
uv run ruff check src/ tests/

# Type-Check
uv run mypy src/
```

Siehe [CHANGELOG.md](CHANGELOG.md) für die Versionshistorie.

## Auto-Korrektur fehlplatzierter Felder

Die BMF-Liste wird manuell gepflegt und enthält gelegentlich Tippfehler in den
Feldern **UID-Nr.**, **Firmenbuch-Nr** und **Kennziffer des UR**.
Vor der Validierung erkennt das Tool diese Muster und korrigiert sie
automatisch (mit Warnung im Log), damit nachgelagerte Tools (z. B. Lookups
nach UID) konsistente Daten erhalten:

| Regel | Beispiel (BMF-Eingabe) | Korrektur |
|-------|------------------------|-----------|
| **UID ↔ Kennziffer tauschen** | `uid="R134I594W"`, `kennziffer=""` | → `uid=null`, `kennziffer="R134I594W"` |
| **Firmenbuch ↔ Kennziffer tauschen** | `fbnr="R120R501J"`, `kennziffer=""` | → `fbnr=null`, `kennziffer="R120R501J"` |
| **Doppelten UID-Wert in Kennziffer löschen** | `uid="ATU80457319"`, `kennziffer="ATU80457319"` | → `kennziffer=null` |
| **Doppelten Firmenbuch-Wert in Kennziffer löschen** | `fbnr="636821b"`, `kennziffer="636821b"` | → `kennziffer=null` |
| **Ausländische EU-VAT-Nummer in UID übernehmen** | `kennziffer="RO38488384"`, `uid=null` | → `uid="RO38488384"`, `kennziffer=null` |
| **Firmenbuch-Prüfbuchstabe kleinschreiben** | `fbnr="436634I"` | → `fbnr="436634i"` |

Erkannte Fixe werden mit `WARNING: NORMALIZE: …` ins Log geschrieben.
Die UID-Spalte wird auch für Nicht-AT-VAT-Nummern offen gehalten
(rumänische, deutsche etc.), da die Firmen trotzdem als Scheinfirmen geführt
werden und in nachgelagerten Tools per UID auffindbar sein sollen.

## Technische Details

- **Abhängigkeiten:** Keine (reines Python stdlib, >= 3.10)
- **Quell-Encoding:** ISO-8859-1 (Tilde-getrennt, CRLF)
- **Output-Encoding:** UTF-8 (CSV mit BOM für Excel-Kompatibilität)
- **Validierung:** Strenge Feldvalidierung mit Fehlern und Warnungen, dazu
  Plausibilitätswarnungen (Rechtskraft nach Veröffentlichung, Datum in der Zukunft,
  unplausibles Alter, dieselbe UID/Firmenbuch-Nr/Kennziffer bei mehreren Einträgen)
- **Änderungsverfolgung:** Vergleich mit dem vorherigen Stand (`geaendert`, Abgänge,
  Schutz gegen abgeschnittene Downloads)
- **Daten-Reparatur:** Auto-Korrektur fehlplatzierter UID/Kennziffer/Firmenbuch-Werte (siehe oben)
- **Schema-Prüfung:** Automatische Validierung gegen XSD (XML) und JSON Schema (JSONL)
- **Verifizierung:** Kreuz-Format-Prüfung (alle Formate müssen gleiche Zeilenanzahl haben)

## Lizenz

**Code:** Apache License 2.0 — siehe [LICENSE](LICENSE)

**Daten:** Die Scheinfirmenliste ist eine amtliche Veröffentlichung des BMF gemäß
§ 8 SBBG. Das BMF gibt dafür keine ausdrückliche Lizenz an. Als amtliche Bekanntmachung
genießt sie voraussichtlich keinen urheberrechtlichen Schutz (§ 7 UrhG) — dies ist keine
Rechtsberatung. Rechtsverbindlich ist ausschließlich die Liste auf der BMF-Website.
Dieselbe Angabe steht als `dc:rights` in den CSVW-Metadaten.
