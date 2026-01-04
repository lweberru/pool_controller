from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from .const import DOMAIN
from .coordinator import PoolControllerDataCoordinator

# "button" wurde hier hinzugefügt
PLATFORMS = ["sensor", "switch", "climate", "binary_sensor", "button"]

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Setup der Integration."""
    coordinator = PoolControllerDataCoordinator(hass, entry)
    
    # Den ersten Datenabruf triggern
    await coordinator.async_config_entry_first_refresh()
    
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = coordinator

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