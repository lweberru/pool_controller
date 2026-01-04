import logging
from homeassistant.components.climate import (
    ClimateEntity,
    ClimateEntityFeature,
    HVACMode,
    HVACAction,
)
from homeassistant.const import UnitOfTemperature, ATTR_TEMPERATURE
from .const import DOMAIN, CONF_MAIN_SWITCH, CONF_AUX_HEATING_SWITCH

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass, entry, async_add_entities):
    """Setzt die Climate-Plattform auf."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([WhirlpoolClimate(coordinator)])

class WhirlpoolClimate(ClimateEntity):
    """Repräsentation der Whirlpool-Steuerung."""

    _attr_has_entity_name = True
    _attr_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_hvac_modes = [HVACMode.OFF, HVACMode.HEAT]
    _attr_supported_features = ClimateEntityFeature.TARGET_TEMPERATURE
    _attr_min_temp = 10
    _attr_max_temp = 40

    def __init__(self, coordinator):
        self.coordinator = coordinator
        self._attr_unique_id = f"{coordinator.entry.entry_id}_climate"
        self._attr_name = "Whirlpool Steuerung"
        self._target_temp = 38.0

    @property
    def current_temperature(self):
        """Gibt die aktuelle Wassertemperatur vom Coordinator zurück."""
        return self.coordinator.data.get("water_temp")

    @property
    def target_temperature(self):
        """Gibt die Zieltemperatur zurück."""
        return self._target_temp

    @property
    def hvac_mode(self):
        """Gibt den aktuellen Modus zurück (basierend auf dem Hauptschalter)."""
        main_switch = self.hass.states.get(self.coordinator.entry.data.get(CONF_MAIN_SWITCH))
        if main_switch and main_switch.state == "on":
            return HVACMode.HEAT
        return HVACMode.OFF

    @property
    def hvac_action(self):
        """Zeigt an, ob gerade aktiv geheizt wird."""
        if self.hvac_mode == HVACMode.OFF:
            return HVACAction.OFF
        if self.current_temperature is not None and self.current_temperature < self.target_temperature:
            return HVACAction.HEATING
        return HVACAction.IDLE

    async def async_set_hvac_mode(self, hvac_mode):
        """Schaltet den Pool ein oder aus."""
        main_switch_id = self.coordinator.entry.data.get(CONF_MAIN_SWITCH)
        if hvac_mode == HVACMode.HEAT:
            await self.hass.services.async_call("switch", "turn_on", {"entity_id": main_switch_id})
        else:
            # Sicherheitscheck: Nicht ausschalten, wenn Frostgefahr oder Bade-Event
            if not self.coordinator.data.get("frost_danger"):
                await self.hass.services.async_call("switch", "turn_off", {"entity_id": main_switch_id})

    async def async_set_temperature(self, **kwargs):
        """Setzt eine neue Zieltemperatur."""
        if (temp := kwargs.get(ATTR_TEMPERATURE)) is not None:
            self._target_temp = temp
            await self.coordinator.async_request_refresh()