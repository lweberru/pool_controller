# Troubleshooting

[← Back to README](../README.md)

## Language Support

The integration includes full translations for:
- 🇩🇪 **Deutsch** (German)
- 🇬🇧 **English**
- 🇪🇸 **Español** (Spanish)
- 🇫🇷 **Français** (French)

All entity names, buttons, and configuration labels are translated automatically based on your Home Assistant language setting.

## "Unknown entity" errors during setup
- Verify sensor entity IDs exist in your HA instance
- Optional sensors can be left empty if not configured
- Check entity IDs spelling (case-sensitive)

## Pool not turning on
- Check `binary_sensor.pool_should_main_on` and `binary_sensor.pool_should_pump_on`
- For “requested vs physical” debugging, compare:
  - `binary_sensor.pool_should_main_on` vs `binary_sensor.pool_main_switch_on`
  - `binary_sensor.pool_should_pump_on` vs `binary_sensor.pool_pump_switch_on`
- Review quiet hours and calendar events
- Verify frost protection not active
- Check `sensor.pool_status` for current state

## Heating not working
- Verify power sensor is configured and reporting
- Check heating thermostat target (default 38°C)
- Ensure calendar event is active (if required)
- Review PV thresholds if solar-dependent

## Water quality sensor not updating
- Confirm Blueriiot sensor in range and powered
- Check ESP32 WiFi connection and ESPHome status
- Verify BLE connection in ESP32 logs
- Try pressing "Start BLE Scan" button on ESP32

## Support

For issues, questions, or feature requests:
1. Check existing GitHub issues
2. Review Home Assistant logs (`Settings → System → Logs`)
3. Open a new GitHub issue with:
   - Pool Controller version
   - Home Assistant version
   - Integration setup details
   - Relevant logs/error messages
