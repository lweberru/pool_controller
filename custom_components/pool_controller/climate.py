import logging
from homeassistant.components.climate import ClimateEntity, ClimateEntityFeature, HVACMode, HVACAction
from homeassistant.const import UnitOfTemperature, ATTR_TEMPERATURE
from homeassistant.helpers.device_registry import DeviceInfo
from .const import DOMAIN, MANUFACTURER, CONF_MAIN_SWITCH, CONF_AUX_HEATING_SWITCH, CONF_DEMO_MODE

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass, entry, async_add_entities):
    coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([WhirlpoolClimate(coordinator)])

class WhirlpoolClimate(ClimateEntity):
    _attr_has_entity_name = True
    _attr_translation_key = "pool_climate" # Ermöglicht Übersetzung via de.json
    _attr_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_hvac_modes = [HVACMode.OFF, HVACMode.HEAT]
    _attr_supported_features = ClimateEntityFeature.TARGET_TEMPERATURE
    _attr_min_temp = 10
    _attr_max_temp = 40

    def __init__(self, coordinator):
        self.coordinator = coordinator
        self._attr_unique_id = f"{coordinator.entry.entry_id}_climate"
        self._attr_name = None # Name kommt vom Device

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={(DOMAIN, self.coordinator.entry.entry_id)},
            name=self.coordinator.entry.data.get("name", "Whirlpool"),
            manufacturer=MANUFACTURER,
            model="Advanced Controller v1",
            sw_version="1.0.6",
        )

    @property
    def current_temperature(self):
        return self.coordinator.data.get("water_temp")

    @property
    def target_temperature(self):
        return self.coordinator.target_temp

    @property
    def hvac_mode(self):
        main_switch = self.hass.states.get(self.coordinator.entry.data.get(CONF_MAIN_SWITCH))
        return HVACMode.HEAT if main_switch and main_switch.state == "on" else HVACMode.OFF

    @property
    def hvac_action(self):
        if self.hvac_mode == HVACMode.OFF: return HVACAction.OFF
        if self.current_temperature and self.current_temperature < self.target_temperature:
            return HVACAction.HEATING
        return HVACAction.IDLE

    async def async_set_hvac_mode(self, hvac_mode):
        main_switch_id = self.coordinator.entry.data.get(CONF_MAIN_SWITCH)
        aux_switch_id = self.coordinator.entry.data.get(CONF_AUX_HEATING_SWITCH)
        demo = self.coordinator.entry.data.get(CONF_DEMO_MODE, False)

        if hvac_mode == HVACMode.HEAT:
            if demo:
                _LOGGER.debug("Demo mode active — skipping switch.turn_on for main")
            else:
                await self.hass.services.async_call("switch", "turn_on", {"entity_id": main_switch_id})
                # if coordinator suggests aux heating, enable it
                if self.coordinator.data.get("should_aux_on") and aux_switch_id:
                    if demo:
                        _LOGGER.debug("Demo mode active — skipping aux turn_on")
                    else:
                        await self.hass.services.async_call("switch", "turn_on", {"entity_id": aux_switch_id})
        else:
            # when turning off, do not disable main if bathing is active
            if self.coordinator.data.get("is_bathing"):
                _LOGGER.debug("Bathing active — skip turning off main switch")
                return
            if demo:
                _LOGGER.debug("Demo mode active — skipping switch.turn_off for main/aux")
                return
            await self.hass.services.async_call("switch", "turn_off", {"entity_id": main_switch_id})
            if aux_switch_id:
                await self.hass.services.async_call("switch", "turn_off", {"entity_id": aux_switch_id})

    async def async_set_temperature(self, **kwargs):
        if (temp := kwargs.get(ATTR_TEMPERATURE)) is not None:
            self.coordinator.target_temp = temp
            await self.coordinator.async_request_refresh()
            # After refresh, ensure switches reflect new target: if climate is in HEAT mode, ensure main/aux are on
            if self.hvac_mode == HVACMode.HEAT:
                await self.async_set_hvac_mode(HVACMode.HEAT)
            else:
                await self.async_set_hvac_mode(HVACMode.OFF)