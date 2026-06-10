# Home Assistant API Helper Skript

[English](../ha-api-read.md) | **Deutsch**

[← Zurück zur README](../../README.de.md)

## Zweck

`tools/ha_api_read.py` ist ein Helfer, um Home Assistant REST API Daten schnell auszulesen und optional Services aufzurufen.

Typische Einsätze:

- Aktuelle Entity-Zustände schnell prüfen.
- Historienfenster zur Korrelation analysieren.
- Verfügbare Services und Roh-Endpunkte inspizieren.
- Debugging zwischen Backend und Frontend deutlich beschleunigen.

Das Skript unterstützt `GET`-Requests sowie explizite Service-Aufrufe (`POST /api/services/...`).

## Credentials und Konfiguration

Credentials werden in folgender Reihenfolge aufgelöst:

1. `--config path/to/file.json`
2. Umgebungsvariablen `HA_URL` und `HA_TOKEN`
3. Lokale Default-Datei `tools/.ha_api.local.json`

Beispiel für die Config-Datei:

```json
{
  "ha_url": "https://home.example.local/",
  "ha_token": "DEIN_LONG_LIVED_ACCESS_TOKEN"
}
```

Sicherheits-Hinweise:

- Token-Datei nicht in Git einchecken.
- Tokens rotieren, falls sie offengelegt wurden.

## Globale Optionen

- `--timeout <sekunden>`: HTTP-Timeout (Default `20`)
- `--compact`: kompakte Einzeilen-JSON-Ausgabe
- `--insecure`: TLS-Zertifikatsprüfung deaktivieren (nur in vertrauenswürdigen lokalen Umgebungen)

## Befehle

### states

Liest `/api/states` mit optionalen Filtern.

```bash
python3 tools/ha_api_read.py states
python3 tools/ha_api_read.py --compact states --domain sensor --contains whirlpool
python3 tools/ha_api_read.py --compact states --contains alkal --limit 50
```

### state

Liest eine Entity über `/api/states/<entity_id>`.

```bash
python3 tools/ha_api_read.py state climate.whirlpool
```

### history

Liest Entity-Historie über `/api/history/period`.

```bash
python3 tools/ha_api_read.py history sensor.garten_whirlpool_alkalinitats_aktion --hours 24
python3 tools/ha_api_read.py --compact history sensor.garten_whirlpool_alkalinitats_status --hours 24 --minimal --no-attributes
python3 tools/ha_api_read.py --compact history sensor.garten_whirlpool_geschatzte_alkalinitat --hours 12 --significant-only
```

### services

Liest `/api/services`.

```bash
python3 tools/ha_api_read.py services
```

### get

Liest beliebige GET-Endpunkte.

```bash
python3 tools/ha_api_read.py get /api/config
python3 tools/ha_api_read.py get /api/logbook --query entity=sensor.garten_whirlpool_alkalinitats_aktion
```

### call

Ruft einen Home Assistant Service direkt auf.

```bash
python3 tools/ha_api_read.py call pool_controller set_options --target-entity climate.whirlpool --data enable_dynamic_target=true --data dynamic_target_weather_entity=weather.openweathermap
```

### apply-dynamic-target-defaults

Komfort-Befehl, um die pool_controller Dynamic-Target-Defaults auf eine Pool-Instanz anzuwenden.

```bash
python3 tools/ha_api_read.py apply-dynamic-target-defaults climate.whirlpool --weather-entity weather.openweathermap --enable
```

## Praktischer Analyse-Workflow

Für Empfehlungen wie `measure_first` dieselbe Zeitspanne vergleichen:

1. Historie von `sensor.<pool>_alkalinitats_aktion`
2. Historie von `sensor.<pool>_alkalinitats_status`
3. Historie von `sensor.<pool>_geschatzte_alkalinitat`
4. Historie von `climate.<pool>`

So siehst du schnell, ob Übergänge durch Neustart-Fenster, unavailable-Zustände oder normalen Laufzeitwechsel entstanden sind.

## Hinweis zu SSL

Bei Self-Signed oder unvollständiger Zertifikatskette kann `CERTIFICATE_VERIFY_FAILED` auftreten.

Dann nutzbar:

```bash
python3 tools/ha_api_read.py --insecure states --contains whirlpool
```

`--insecure` nur in vertrauenswürdigen Umgebungen verwenden.

## Fehlerbehandlung

Das Skript gibt verständliche Fehler auf stderr aus bei:

- fehlenden Credentials
- HTTP-Fehlern inklusive Body
- Verbindungsfehlern
- ungültigen JSON-Antworten

Damit eignet es sich gut für Shell-Pipelines und schnelle Diagnosen.
