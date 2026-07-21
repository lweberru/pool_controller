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
  "ha_local_url": "http://192.168.1.196:8123",
  "ha_token": "DEIN_LONG_LIVED_ACCESS_TOKEN",
  "insecure": true
}
```

Sicherheits-Hinweise:

- Token-Datei nicht in Git einchecken.
- Tokens rotieren, falls sie offengelegt wurden.

## Globale Optionen

- `--timeout <sekunden>`: HTTP-Timeout (Default `20`)
- `--compact`: kompakte Einzeilen-JSON-Ausgabe
- `--insecure`: TLS-Zertifikatsprüfung deaktivieren (nur in vertrauenswürdigen lokalen Umgebungen)
- `--url <url>`: Home-Assistant-URL für einen einzelnen Befehl überschreiben
- `--local`: `ha_local_url` / `local_url` aus Config oder `HA_LOCAL_URL` verwenden
Globale Optionen dürfen vor oder nach dem Subcommand stehen:

```bash
python3 tools/ha_api_read.py --compact states --contains whirlpool
python3 tools/ha_api_read.py states --compact --contains whirlpool
python3 tools/ha_api_read.py --local pool --entity-id climate.whirlpool --compact
python3 tools/ha_api_read.py --url http://192.168.1.196:8123 pool --entity-id climate.whirlpool --compact
```

Im eigenen Netz bevorzugt die direkte Home-Assistant-URL (`ha_local_url`) statt Reverse Proxy nutzen. Das vermeidet nginx-WebSocket-/TLS-Effekte bei Diagnosen.

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

### pool

Liest eine fokussierte Pool-Zusammenfassung: Climate-Entity, Dynamic-Target-Diagnose, Wetter-Entities, verwandte Pool-Entities und lokale Config-Entry-Optionen, falls verfügbar.

```bash
python3 tools/ha_api_read.py pool --entity-id climate.whirlpool --compact
python3 tools/ha_api_read.py pool --device-id <ha_device_id> --compact
python3 tools/ha_api_read.py pool --name whirlpool --full
```

Diesen Befehl bei pool_controller-Live-Debugging zuerst nutzen, statt mit breiten `states`-Dumps zu beginnen.

### pool-config

Liest `pool_controller`-Config-`data` und `options` von der remote Home-Assistant-Instanz.

Der Befehl ruft zuerst den read-only Service `pool_controller.get_options` über Home-Assistant-WebSocket-Service-Response auf. Wenn die remote Instanz noch nicht auf eine Version mit diesem Service aktualisiert wurde, fällt er auf Home Assistants `config_entries/get`-WebSocket-Metadaten zurück.

```bash
python3 tools/ha_api_read.py pool-config --entity-id climate.whirlpool
python3 tools/ha_api_read.py pool-config --device-id <ha_device_id>
```

Home Assistants Core-WebSocket-Config-Entry-API gibt `data`/`options` nicht heraus; die echte Quelle für Optionswerte ist deshalb der Integrations-Service.

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

Bei Self-Signed oder unvollständiger Zertifikatskette wiederholt das Tool den Request automatisch ohne TLS-Prüfung und schreibt einmalig eine Warnung auf stderr.

Explizit geht weiterhin:

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
