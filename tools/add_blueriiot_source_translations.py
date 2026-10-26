"""Add the optional BlueRiiot integration source to all supported translations."""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "custom_components/pool_controller"
TEXT = {
    "en": (
        "Measurement source", "BlueRiiot Bluetooth device",
        ["Sensor entities", "Direct Bluetooth reader", "BlueRiiot Bluetooth integration"],
        "Choose who reads the measurements. With the BlueRiiot integration, Pool Controller uses its entities and never opens its own Bluetooth connection. MAC address, calibration and day/night intervals below apply only to the direct reader.",
        "Select a device configured in BlueRiiot Bluetooth. Measurements, reachability and the refresh button are assigned automatically. Configure polling and salt calibration in BlueRiiot Bluetooth.",
        ["Select a BlueRiiot Bluetooth device.", "The selected device does not belong to BlueRiiot Bluetooth.", "Select a valid measurement source."],
    ),
    "de": (
        "Messwertquelle", "Gerät aus BlueRiiot Bluetooth",
        ["Sensor-Entitäten", "Direkte Bluetooth-Auslesung", "Integration BlueRiiot Bluetooth"],
        "Wähle, wer die Messwerte ausliest. Bei Nutzung der BlueRiiot-Integration übernimmt Pool Controller deren Entitäten und baut keine eigene Bluetooth-Verbindung auf. MAC-Adresse, Kalibrierung und Tag-/Nachtintervalle unten gelten nur für die direkte Auslesung.",
        "Wähle ein eingerichtetes Gerät aus BlueRiiot Bluetooth. Messwerte, Erreichbarkeit und die Auslesen-Schaltfläche werden automatisch zugeordnet. Abfrageintervall und Salzkalibrierung werden in BlueRiiot Bluetooth eingestellt.",
        ["Bitte ein Gerät aus BlueRiiot Bluetooth auswählen.", "Das gewählte Gerät gehört nicht zu BlueRiiot Bluetooth.", "Bitte eine gültige Messwertquelle auswählen."],
    ),
    "es": (
        "Origen de las mediciones", "Dispositivo de BlueRiiot Bluetooth",
        ["Entidades de sensores", "Lectura Bluetooth directa", "Integración BlueRiiot Bluetooth"],
        "Elige quién obtiene las mediciones. Con la integración BlueRiiot, Pool Controller utiliza sus entidades sin abrir otra conexión Bluetooth. La dirección MAC, la calibración y los intervalos diurnos/nocturnos solo se aplican a la lectura directa.",
        "Selecciona un dispositivo configurado en BlueRiiot Bluetooth. Las mediciones, la conectividad y el botón de lectura se asignan automáticamente. Configura el intervalo y la calibración de sal en BlueRiiot Bluetooth.",
        ["Selecciona un dispositivo de BlueRiiot Bluetooth.", "El dispositivo no pertenece a BlueRiiot Bluetooth.", "Selecciona un origen de mediciones válido."],
    ),
    "fr": (
        "Source des mesures", "Appareil BlueRiiot Bluetooth",
        ["Entités de capteurs", "Lecture Bluetooth directe", "Intégration BlueRiiot Bluetooth"],
        "Choisissez qui relève les mesures. Avec l’intégration BlueRiiot, Pool Controller utilise ses entités sans ouvrir une autre connexion Bluetooth. L’adresse MAC, l’étalonnage et les intervalles jour/nuit concernent uniquement la lecture directe.",
        "Sélectionnez un appareil configuré dans BlueRiiot Bluetooth. Les mesures, la connectivité et le bouton de lecture sont associés automatiquement. Réglez l’intervalle et l’étalonnage du sel dans BlueRiiot Bluetooth.",
        ["Sélectionnez un appareil BlueRiiot Bluetooth.", "L’appareil ne fait pas partie de BlueRiiot Bluetooth.", "Sélectionnez une source de mesures valide."],
    ),
}


def update_json_text(original, updated):
    """Keep formatting of unrelated JSON while adding translated keys."""
    decoder = json.JSONDecoder()
    previous = json.loads(original)
    replacements = []

    def visit(start, end, old, new, depth):
        if old == new:
            return
        if not isinstance(old, dict) or not isinstance(new, dict):
            replacements.append((start, end, json.dumps(new, ensure_ascii=False)))
            return
        cursor = start + 1
        for key, old_value in old.items():
            while original[cursor].isspace() or original[cursor] == ',':
                cursor += 1
            _, cursor = decoder.raw_decode(original, cursor)
            while original[cursor].isspace() or original[cursor] == ':':
                cursor += 1
            _, value_end = decoder.raw_decode(original, cursor)
            visit(cursor, value_end, old_value, new[key], depth + 1)
            cursor = value_end
        additions = [(key, value) for key, value in new.items() if key not in old]
        if additions:
            indent_width = len(original.splitlines()[1]) - len(original.splitlines()[1].lstrip())
            indent = ' ' * (indent_width * (depth + 1))
            addition = (',' if old else '') + '\n' + ',\n'.join(
                indent + json.dumps(key) + ': ' + json.dumps(value, ensure_ascii=False)
                for key, value in additions
            )
            replacements.append((cursor, cursor, addition))

    start = len(original) - len(original.lstrip())
    _, end = decoder.raw_decode(original, start)
    visit(start, end, previous, updated, 0)
    for start, end, replacement in sorted(replacements, reverse=True):
        original = original[:start] + replacement + original[end:]
    assert json.loads(original) == updated
    return original


def main():
    for path in [ROOT / "strings.json", *sorted((ROOT / "translations").glob("*.json"))]:
        language = path.stem if path.stem in TEXT else "en"
        source, device, options, source_help, device_help, errors = TEXT[language]
        original = path.read_text()
        data = json.loads(original)
        for flow in ("config", "options"):
            section = data.setdefault(flow, {})
            for step in ("measurement", "blueriiot"):
                form = section.setdefault("step", {}).setdefault(step, {})
                form.setdefault("data", {}).update(blueriiot_source=source, blueriiot_device=device)
                form.setdefault("data_description", {}).update(blueriiot_source=source_help, blueriiot_device=device_help)
                form["description"] = source_help
            section.setdefault("error", {}).update(zip(
                ("blueriiot_device_required", "invalid_blueriiot_device", "invalid_source"), errors
            ))
        data.setdefault("selector", {})["blueriiot_source"] = {
            "options": dict(zip(("entities", "native", "integration"), options))
        }
        path.write_text(update_json_text(original, data))


if __name__ == "__main__":
    main()
