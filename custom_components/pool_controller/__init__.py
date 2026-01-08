import logging

from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
import voluptuous as vol
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import entity_registry as er

from .const import DOMAIN
from .coordinator import PoolControllerDataCoordinator

_LOGGER = logging.getLogger(__name__)

_SERVICES_REGISTERED_KEY = "__services_registered"

# "button" wurde hier hinzugefügt (timer ist keine Entity-Plattform)
PLATFORMS = ["sensor", "switch", "climate", "binary_sensor", "button"]

SERVICE_START_PAUSE = "start_pause"
SERVICE_STOP_PAUSE = "stop_pause"
SERVICE_START_BATHING = "start_bathing"
SERVICE_STOP_BATHING = "stop_bathing"
SERVICE_START_FILTER = "start_filter"
SERVICE_STOP_FILTER = "stop_filter"
SERVICE_START_CHLORINE = "start_chlorine"
SERVICE_STOP_CHLORINE = "stop_chlorine"

TARGET_SCHEMA = {
    vol.Optional("climate_entity"): cv.entity_id,
    vol.Optional("controller_entity"): cv.entity_id,
    vol.Optional("config_entry_id"): cv.string,
}

START_PAUSE_SCHEMA = vol.Schema({
    **TARGET_SCHEMA,
    vol.Optional("duration_minutes", default=60): cv.positive_int,
})

START_BATHING_SCHEMA = vol.Schema({
    **TARGET_SCHEMA,
    vol.Optional("duration_minutes", default=60): cv.positive_int,
})

START_FILTER_SCHEMA = vol.Schema({
    **TARGET_SCHEMA,
    vol.Optional("duration_minutes", default=30): cv.positive_int,
})

START_CHLORINE_SCHEMA = vol.Schema({
    **TARGET_SCHEMA,
    vol.Optional("duration_minutes", default=5): cv.positive_int,
})

STOP_SCHEMA = vol.Schema({
    **TARGET_SCHEMA,
})


def _iter_coordinators(hass: HomeAssistant):
    data = hass.data.get(DOMAIN, {})
    for key, value in data.items():
        if key == _SERVICES_REGISTERED_KEY:
            continue
        if isinstance(value, PoolControllerDataCoordinator):
            yield value


def _get_coordinator_by_entry_id(hass: HomeAssistant, config_entry_id: str | None):
    if not config_entry_id:
        return None
    return hass.data.get(DOMAIN, {}).get(config_entry_id)


def _get_coordinator_by_climate_entity(hass: HomeAssistant, climate_entity: str | None):
    if not climate_entity:
        return None
    ent_reg = er.async_get(hass)
    ent = ent_reg.async_get(climate_entity)
    if not ent or not ent.config_entry_id:
        return None
    return _get_coordinator_by_entry_id(hass, ent.config_entry_id)


def _resolve_coordinator(hass: HomeAssistant, call) -> PoolControllerDataCoordinator | None:
    # 1) Explicit config_entry_id
    coord = _get_coordinator_by_entry_id(hass, call.data.get("config_entry_id"))
    if coord:
        return coord

    # 2) Resolve via entity registry from climate_entity
    coord = _get_coordinator_by_climate_entity(hass, call.data.get("climate_entity"))
    if coord:
        return coord

    # 2b) Backward/alias: controller_entity
    coord = _get_coordinator_by_climate_entity(hass, call.data.get("controller_entity"))
    if coord:
        return coord

    # 3) Fallback only if there is exactly one instance
    coords = list(_iter_coordinators(hass))
    if len(coords) == 1:
        return coords[0]
    return None


def _ensure_services_registered(hass: HomeAssistant):
    hass.data.setdefault(DOMAIN, {})
    if hass.data[DOMAIN].get(_SERVICES_REGISTERED_KEY):
        return

    def _warn_no_target(service_name: str):
        coords = list(_iter_coordinators(hass))
        _LOGGER.warning(
            "pool_controller.%s: no target instance resolved (provide climate_entity/controller_entity or config_entry_id). instances=%s payload_keys=%s",
            service_name,
            len(coords),
            sorted(list((call.data or {}).keys())),
        )

    async def handle_start_pause(call):
        coordinator = _resolve_coordinator(hass, call)
        if not coordinator:
            _warn_no_target("start_pause")
            return
        duration = call.data.get("duration_minutes", 60)
        await coordinator.activate_pause(minutes=duration)
        await coordinator.async_request_refresh()

    async def handle_stop_pause(call):
        coordinator = _resolve_coordinator(hass, call)
        if not coordinator:
            _warn_no_target("stop_pause")
            return
        await coordinator.deactivate_pause()
        await coordinator.async_request_refresh()

    async def handle_start_bathing(call):
        coordinator = _resolve_coordinator(hass, call)
        if not coordinator:
            _warn_no_target("start_bathing")
            return
        duration = call.data.get("duration_minutes", 60)
        await coordinator.activate_manual_timer(timer_type="bathing", minutes=duration)
        await coordinator.async_request_refresh()

    async def handle_stop_bathing(call):
        coordinator = _resolve_coordinator(hass, call)
        if not coordinator:
            _warn_no_target("stop_bathing")
            return
        await coordinator.deactivate_manual_timer(only_type="bathing")
        await coordinator.async_request_refresh()

    async def handle_start_filter(call):
        coordinator = _resolve_coordinator(hass, call)
        if not coordinator:
            _warn_no_target("start_filter")
            return
        duration = call.data.get("duration_minutes", 30)
        await coordinator.activate_manual_timer(timer_type="filter", minutes=duration)
        await coordinator.async_request_refresh()

    async def handle_stop_filter(call):
        coordinator = _resolve_coordinator(hass, call)
        if not coordinator:
            _warn_no_target("stop_filter")
            return
        await coordinator.stop_filter()
        await coordinator.async_request_refresh()

    async def handle_start_chlorine(call):
        coordinator = _resolve_coordinator(hass, call)
        if not coordinator:
            _warn_no_target("start_chlorine")
            return
        duration = call.data.get("duration_minutes", 5)
        await coordinator.activate_manual_timer(timer_type="chlorine", minutes=duration)
        await coordinator.async_request_refresh()

    async def handle_stop_chlorine(call):
        coordinator = _resolve_coordinator(hass, call)
        if not coordinator:
            _warn_no_target("stop_chlorine")
            return
        await coordinator.deactivate_manual_timer(only_type="chlorine")
        await coordinator.async_request_refresh()

    hass.services.async_register(
        DOMAIN,
        SERVICE_START_PAUSE,
        handle_start_pause,
        schema=START_PAUSE_SCHEMA,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_STOP_PAUSE,
        handle_stop_pause,
        schema=STOP_SCHEMA,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_START_BATHING,
        handle_start_bathing,
        schema=START_BATHING_SCHEMA,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_STOP_BATHING,
        handle_stop_bathing,
        schema=STOP_SCHEMA,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_START_FILTER,
        handle_start_filter,
        schema=START_FILTER_SCHEMA,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_STOP_FILTER,
        handle_stop_filter,
        schema=STOP_SCHEMA,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_START_CHLORINE,
        handle_start_chlorine,
        schema=START_CHLORINE_SCHEMA,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_STOP_CHLORINE,
        handle_stop_chlorine,
        schema=STOP_SCHEMA,
    )

    hass.data[DOMAIN][_SERVICES_REGISTERED_KEY] = True

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Setup der Integration."""
    coordinator = PoolControllerDataCoordinator(hass, entry)
    
    # Den ersten Datenabruf triggern
    await coordinator.async_config_entry_first_refresh()
    
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = coordinator

    # Services werden global (einmalig) registriert und routen dann auf die richtige Instanz.
    _ensure_services_registered(hass)

    # Plattformen laden
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    
    # Listener für Optionen-Updates (Zahnrad-Änderungen)
    entry.async_on_unload(entry.add_update_listener(update_listener))
    
    return True

async def update_listener(hass: HomeAssistant, entry: ConfigEntry):
    """Wird aufgerufen, wenn Optionen im Zahnrad geändert wurden."""
    await hass.config_entries.async_reload(entry.entry_id)

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Entladen der Integration."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)