import logging
from pathlib import Path
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

_CACHED_SW_VERSION = None

def _integration_version() -> str | None:
    global _CACHED_SW_VERSION
    if _CACHED_SW_VERSION is not None:
        return _CACHED_SW_VERSION
    try:
        manifest_path = Path(__file__).resolve().parent / "manifest.json"
        raw = manifest_path.read_text(encoding="utf-8")
        import json
        data = json.loads(raw)
        _CACHED_SW_VERSION = str(data.get("version")) if data.get("version") else None
    except Exception:
        _CACHED_SW_VERSION = None
    return _CACHED_SW_VERSION

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
    PRESET_AWAY = "Abwesend"
    _attr_preset_modes = [PRESET_AUTO, PRESET_BATHING, PRESET_CHLORINE, PRESET_FILTER, PRESET_AWAY, PRESET_MAINTENANCE]

    def __init__(self, coordinator):
        super().__init__(coordinator)
        self.coordinator = coordinator
        self._attr_unique_id = f"{coordinator.entry.entry_id}_climate"
        # Name aus Config übernehmen (Pool-Name aus config_flow)
        pool_name = None
        try:
            pool_name = coordinator.entry.data.get("name")
        except Exception:
            pool_name = None
        self._attr_name = pool_name or "Whirlpool"

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
            model="Advanced Controller v2",
            sw_version=_integration_version(),
        )

    @property
    def current_temperature(self):
        return self.coordinator.data.get("water_temp")

    @property
    def target_temperature(self):
        return self.coordinator.target_temp

    @property
    def hvac_mode(self):
        # hvac_mode zeigt aktives Heizen an:
        # - OFF bei Wartung
        # - OFF bei Away
        # - OFF wenn HVAC deaktiviert
        # - HEAT bei Frostlauf, manuellem Heizen, PV, Preheat, Thermostat
        if bool(getattr(self.coordinator, "maintenance_active", False)):
            return HVACMode.OFF
        if bool(getattr(self.coordinator, "away_active", False)):
            return HVACMode.OFF
        if not bool(getattr(self.coordinator, "hvac_enabled", True)):
            return HVACMode.OFF

        data = getattr(self.coordinator, "data", {}) or {}
        try:
            cur = float(self.current_temperature) if self.current_temperature is not None else None
            tgt = float(self.target_temperature) if self.target_temperature is not None else None
        except Exception:
            cur, tgt = None, None
        heat_reason = str(data.get("heat_reason") or "").lower()
        wants_heat = heat_reason not in ("", "off", "disabled")
        temp_below_target = (cur is not None and tgt is not None and cur < tgt)

        # Frostlauf: Wenn frost_timer_active, dann immer HEAT
        if data.get("frost_timer_active"):
            return HVACMode.HEAT

        # Prefer explicit demand/switch state when available.
        if bool(data.get("should_aux_on")) or bool(data.get("aux_heating_switch_on")):
            return HVACMode.HEAT
        if wants_heat and temp_below_target and bool(data.get("should_pump_on")):
            return HVACMode.HEAT
        return HVACMode.OFF

    @property
    def hvac_action(self):
        if self.hvac_mode == HVACMode.OFF:
            return HVACAction.OFF
        return HVACAction.HEATING

    @property
    def preset_mode(self):
        if bool(getattr(self.coordinator, "maintenance_active", False)):
            return self.PRESET_MAINTENANCE
        if bool(getattr(self.coordinator, "away_active", False)):
            return self.PRESET_AWAY
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
        # hvac_mode is *not* maintenance anymore:
        # - HEAT: user-triggered "heat to target" (start bathing timer with estimated duration)
        # - OFF: stop manual heating (bathing timer) and disable HVAC
        if hvac_mode == HVACMode.OFF:
            await self.coordinator.stop_manual_heat()
            await self.coordinator.set_hvac_enabled(False)
        else:
            await self.coordinator.set_hvac_enabled(True)
            await self.coordinator.start_manual_heat_to_target()
        await self.coordinator.async_request_refresh()

    async def async_set_preset_mode(self, preset_mode: str):
        mode = (preset_mode or "").strip()
        if mode == self.PRESET_MAINTENANCE:
            await self.coordinator.set_away(False)
            await self.coordinator.set_maintenance(True)
            await self.coordinator.async_request_refresh()
            return
        if mode == self.PRESET_AWAY:
            await self.coordinator.set_maintenance(False)
            await self.coordinator.set_away(True)
            await self.coordinator.async_request_refresh()
            return

        # Any other preset disables Wartung/Away first
        await self.coordinator.set_maintenance(False)
        await self.coordinator.set_away(False)

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