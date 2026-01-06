from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
import voluptuous as vol
from homeassistant.helpers import config_validation as cv
from .const import DOMAIN
from .coordinator import PoolControllerDataCoordinator

# "button" wurde hier hinzugefügt (timer ist keine Entity-Plattform)
PLATFORMS = ["sensor", "switch", "climate", "binary_sensor", "button"]

SERVICE_START_PAUSE = "start_pause"
SERVICE_STOP_PAUSE = "stop_pause"
SERVICE_START_BATHING = "start_bathing"
SERVICE_STOP_BATHING = "stop_bathing"
SERVICE_START_FILTER = "start_filter"
SERVICE_STOP_FILTER = "stop_filter"

START_PAUSE_SCHEMA = vol.Schema({
    vol.Optional("duration_minutes", default=30): cv.positive_int,
})

START_BATHING_SCHEMA = vol.Schema({
    vol.Optional("duration_minutes", default=60): cv.positive_int,
})

START_FILTER_SCHEMA = vol.Schema({
    vol.Optional("duration_minutes", default=30): cv.positive_int,
})

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Setup der Integration."""
    coordinator = PoolControllerDataCoordinator(hass, entry)
    
    # Den ersten Datenabruf triggern
    await coordinator.async_config_entry_first_refresh()
    
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = coordinator

    # Plattformen laden
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    
    # Services registrieren
    async def handle_start_pause(call):
        duration = call.data.get("duration_minutes", 30)
        await coordinator.activate_pause(minutes=duration)
        await coordinator.async_request_refresh()
    
    async def handle_stop_pause(call):
        await coordinator.activate_pause(minutes=0)
        await coordinator.async_request_refresh()
    
    async def handle_start_bathing(call):
        duration = call.data.get("duration_minutes", 60)
        await coordinator.activate_bathing(minutes=duration)
        await coordinator.async_request_refresh()
    
    async def handle_stop_bathing(call):
        await coordinator.deactivate_bathing()
        await coordinator.async_request_refresh()
    
    async def handle_start_filter(call):
        duration = call.data.get("duration_minutes", 30)
        await coordinator.activate_filter(minutes=duration)
        await coordinator.async_request_refresh()
    
    async def handle_stop_filter(call):
        await coordinator.deactivate_filter()
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
    )
    
    # Listener für Optionen-Updates (Zahnrad-Änderungen)
    entry.async_on_unload(entry.add_update_listener(update_listener))
    
    return True

async def update_listener(hass: HomeAssistant, entry: ConfigEntry):
    """Wird aufgerufen, wenn Optionen im Zahnrad geändert wurden."""
    await hass.config_entries.async_reload(entry.entry_id)

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Entladen der Integration."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)