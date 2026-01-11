import logging
from homeassistant.components.climate import ClimateEntity, ClimateEntityFeature, HVACMode, HVACAction
from homeassistant.const import UnitOfTemperature, ATTR_TEMPERATURE
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from .const import (
    DOMAIN,
    MANUFACTURER,
    CONF_MIN_TEMP,
    CONF_MAX_TEMP,
    CONF_TARGET_TEMP_STEP,
    DEFAULT_MIN_TEMP,
    DEFAULT_MAX_TEMP,
    DEFAULT_TARGET_TEMP_STEP,
)

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass, entry, async_add_entities):
    coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([WhirlpoolClimate(coordinator)])

class WhirlpoolClimate(CoordinatorEntity, ClimateEntity):
    _attr_has_entity_name = True
    _attr_translation_key = "pool_climate" # Ermöglicht Übersetzung via de.json
    _attr_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_hvac_modes = [HVACMode.OFF, HVACMode.HEAT]
    _attr_supported_features = ClimateEntityFeature.TARGET_TEMPERATURE | ClimateEntityFeature.PRESET_MODE
    # Defaults; will be overridden from entry config/options in __init__.
    _attr_min_temp = DEFAULT_MIN_TEMP
    _attr_max_temp = DEFAULT_MAX_TEMP
    _attr_target_temperature_step = DEFAULT_TARGET_TEMP_STEP

    PRESET_AUTO = "Auto"
    PRESET_BATHING = "Baden"
    PRESET_CHLORINE = "Chloren"
    PRESET_FILTER = "Filtern"
    PRESET_MAINTENANCE = "Wartung"
    _attr_preset_modes = [PRESET_AUTO, PRESET_BATHING, PRESET_CHLORINE, PRESET_FILTER, PRESET_MAINTENANCE]

    def __init__(self, coordinator):
        super().__init__(coordinator)
        self.coordinator = coordinator
        self._attr_unique_id = f"{coordinator.entry.entry_id}_climate"
        self._attr_name = None # Name kommt vom Device

        merged = {**(coordinator.entry.data or {}), **(coordinator.entry.options or {})}
        try:
            self._attr_min_temp = float(merged.get(CONF_MIN_TEMP, DEFAULT_MIN_TEMP))
        except Exception:
            self._attr_min_temp = DEFAULT_MIN_TEMP
        try:
            self._attr_max_temp = float(merged.get(CONF_MAX_TEMP, DEFAULT_MAX_TEMP))
        except Exception:
            self._attr_max_temp = DEFAULT_MAX_TEMP
        try:
            self._attr_target_temperature_step = float(merged.get(CONF_TARGET_TEMP_STEP, DEFAULT_TARGET_TEMP_STEP))
        except Exception:
            self._attr_target_temperature_step = DEFAULT_TARGET_TEMP_STEP

        # Ensure the coordinator uses the same target temp bounds.
        try:
            if coordinator.target_temp is not None:
                coordinator.target_temp = max(self._attr_min_temp, min(self._attr_max_temp, float(coordinator.target_temp)))
        except Exception:
            pass

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={(DOMAIN, self.coordinator.entry.entry_id)},
            name=self.coordinator.entry.data.get("name", "Whirlpool"),
            manufacturer=MANUFACTURER,
            model="Advanced Controller v1",
            sw_version="1.6.20",
        )

    @property
    def current_temperature(self):
        return self.coordinator.data.get("water_temp")

    @property
    def target_temperature(self):
        return self.coordinator.target_temp

    @property
    def hvac_mode(self):
        # hvac_mode is used here as a coarse "enabled/disabled" switch.
        # In Wartung (maintenance) everything is suppressed.
        return HVACMode.OFF if bool(getattr(self.coordinator, "maintenance_active", False)) else HVACMode.HEAT

    @property
    def hvac_action(self):
        if self.hvac_mode == HVACMode.OFF: return HVACAction.OFF
        if self.current_temperature and self.current_temperature < self.target_temperature:
            return HVACAction.HEATING
        return HVACAction.IDLE

    @property
    def preset_mode(self):
        if bool(getattr(self.coordinator, "maintenance_active", False)):
            return self.PRESET_MAINTENANCE
        if self.coordinator.data.get("manual_timer_active"):
            t = (self.coordinator.manual_timer_type or "").lower()
            if t == "bathing":
                return self.PRESET_BATHING
            if t == "chlorine":
                return self.PRESET_CHLORINE
            if t == "filter":
                return self.PRESET_FILTER
        return self.PRESET_AUTO

    async def async_set_hvac_mode(self, hvac_mode):
        # Do not directly toggle switches here; the coordinator is authoritative.
        # OFF is mapped to Wartung (hard lockout), HEAT disables Wartung.
        if hvac_mode == HVACMode.OFF:
            await self.coordinator.set_maintenance(True)
        else:
            await self.coordinator.set_maintenance(False)
        await self.coordinator.async_request_refresh()

    async def async_set_preset_mode(self, preset_mode: str):
        mode = (preset_mode or "").strip()
        if mode == self.PRESET_MAINTENANCE:
            await self.coordinator.set_maintenance(True)
            await self.coordinator.async_request_refresh()
            return

        # Any non-maintenance preset disables Wartung first
        await self.coordinator.set_maintenance(False)

        if mode == self.PRESET_AUTO:
            # Back to automation: stop manual timer + pause
            await self.coordinator.deactivate_manual_timer()
            await self.coordinator.deactivate_pause()
        elif mode == self.PRESET_BATHING:
            await self.coordinator.activate_manual_timer(timer_type="bathing", minutes=60)
        elif mode == self.PRESET_CHLORINE:
            await self.coordinator.activate_manual_timer(timer_type="chlorine", minutes=5)
        elif mode == self.PRESET_FILTER:
            await self.coordinator.activate_manual_timer(timer_type="filter", minutes=30)
        else:
            _LOGGER.debug("Unknown preset_mode '%s'", mode)
        await self.coordinator.async_request_refresh()

    async def async_set_temperature(self, **kwargs):
        if (temp := kwargs.get(ATTR_TEMPERATURE)) is not None:
            await self.coordinator.set_target_temperature(temp)
            await self.coordinator.async_request_refresh()
            # Switch control is handled by the coordinator.