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
SERVICE_START_MAINTENANCE = "start_maintenance"
SERVICE_STOP_MAINTENANCE = "stop_maintenance"

START_PAUSE_SCHEMA = vol.Schema({
    vol.Required("target"): dict,
    vol.Optional("duration_minutes", default=60): cv.positive_int,
})
START_BATHING_SCHEMA = vol.Schema({
    vol.Required("target"): dict,
    vol.Optional("duration_minutes", default=60): cv.positive_int,
})
START_FILTER_SCHEMA = vol.Schema({
    vol.Required("target"): dict,
    vol.Optional("duration_minutes", default=30): cv.positive_int,
})
START_CHLORINE_SCHEMA = vol.Schema({
    vol.Required("target"): dict,
    vol.Optional("duration_minutes", default=5): cv.positive_int,
})
STOP_SCHEMA = vol.Schema({
    vol.Required("target"): dict,
})


def _iter_coordinators(hass: HomeAssistant):
    data = hass.data.get(DOMAIN, {})
    for key, value in data.items():
        if key == _SERVICES_REGISTERED_KEY:
            continue
        if isinstance(value, PoolControllerDataCoordinator):
            yield value


def _resolve_coordinator(hass: HomeAssistant, call) -> PoolControllerDataCoordinator | None:



    # Neues Target-Schema: entity_id aus call.data["target"]
    entity_id = None
    if "target" in call.data and isinstance(call.data["target"], dict):
        entity_id = call.data["target"].get("entity_id")
    elif "entity_id" in call.data:
        entity_id = call.data["entity_id"]
    if entity_id:
        ent_reg = er.async_get(hass)
        ent = ent_reg.async_get(entity_id)
        if ent and ent.config_entry_id:
            return hass.data.get(DOMAIN, {}).get(ent.config_entry_id)
    # Fallback: nur wenn genau eine Instanz existiert
    coords = list(_iter_coordinators(hass))
    if len(coords) == 1:
        return coords[0]
    return None


def _ensure_services_registered(hass: HomeAssistant):
    hass.data.setdefault(DOMAIN, {})
    if hass.data[DOMAIN].get(_SERVICES_REGISTERED_KEY):
        return

    def _warn_no_target(service_name: str, call):
        coords = list(_iter_coordinators(hass))
        _LOGGER.warning(
            "pool_controller.%s: no target instance resolved (provide target.entity_id). instances=%s payload_keys=%s",
            service_name,
            len(coords),
            sorted(list((call.data or {}).keys())) if call else [],
        )

    async def handle_start_pause(call):
        coordinator = _resolve_coordinator(hass, call)
        if not coordinator:
            _warn_no_target("start_pause", call)
            return
        duration = call.data.get("duration_minutes", 60)
        await coordinator.activate_pause(minutes=duration)
        await coordinator.async_request_refresh()

    async def handle_stop_pause(call):
        coordinator = _resolve_coordinator(hass, call)
        if not coordinator:
            _warn_no_target("stop_pause", call)
            return
        await coordinator.deactivate_pause()
        await coordinator.async_request_refresh()

    async def handle_start_bathing(call):
        coordinator = _resolve_coordinator(hass, call)
        if not coordinator:
            _warn_no_target("start_bathing", call)
            return
        duration = call.data.get("duration_minutes", 60)
        await coordinator.activate_manual_timer(timer_type="bathing", minutes=duration)
        await coordinator.async_request_refresh()

    async def handle_stop_bathing(call):
        coordinator = _resolve_coordinator(hass, call)
        if not coordinator:
            _warn_no_target("stop_bathing", call)
            return
        await coordinator.deactivate_manual_timer(only_type="bathing")
        await coordinator.async_request_refresh()

    async def handle_start_filter(call):
        coordinator = _resolve_coordinator(hass, call)
        if not coordinator:
            _warn_no_target("start_filter", call)
            return
        duration = call.data.get("duration_minutes", 30)
        await coordinator.activate_manual_timer(timer_type="filter", minutes=duration)
        await coordinator.async_request_refresh()

    async def handle_stop_filter(call):
        coordinator = _resolve_coordinator(hass, call)
        if not coordinator:
            _warn_no_target("stop_filter", call)
            return
        await coordinator.stop_filter()
        await coordinator.async_request_refresh()

    async def handle_start_chlorine(call):
        coordinator = _resolve_coordinator(hass, call)
        if not coordinator:
            _warn_no_target("start_chlorine", call)
            return
        duration = call.data.get("duration_minutes", 5)
        await coordinator.activate_manual_timer(timer_type="chlorine", minutes=duration)
        await coordinator.async_request_refresh()

    async def handle_stop_chlorine(call):
        coordinator = _resolve_coordinator(hass, call)
        if not coordinator:
            _warn_no_target("stop_chlorine", call)
            return
        await coordinator.deactivate_manual_timer(only_type="chlorine")
        await coordinator.async_request_refresh()

    async def handle_start_maintenance(call):
        coordinator = _resolve_coordinator(hass, call)
        if not coordinator:
            _warn_no_target("start_maintenance", call)
            return
        await coordinator.set_maintenance(True)
        await coordinator.async_request_refresh()

    async def handle_stop_maintenance(call):
        coordinator = _resolve_coordinator(hass, call)
        if not coordinator:
            _warn_no_target("stop_maintenance", call)
            return
        await coordinator.set_maintenance(False)
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

    hass.services.async_register(
        DOMAIN,
        SERVICE_START_MAINTENANCE,
        handle_start_maintenance,
        schema=STOP_SCHEMA,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_STOP_MAINTENANCE,
        handle_stop_maintenance,
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
    # Ensure entity registry entries for this config entry have a translation_key
    # and an original name when missing. This helps new installs get sensible
    # friendly names immediately (prevents "Whirlpool None").
    try:
        await _ensure_registry_translation_keys(hass, entry)
    except Exception:
        _LOGGER.debug("Could not ensure registry translation keys for %s", entry.entry_id)
    
    # Listener für Optionen-Updates (Zahnrad-Änderungen)
    entry.async_on_unload(entry.add_update_listener(update_listener))
    
    return True

async def update_listener(hass: HomeAssistant, entry: ConfigEntry):
    """Wird aufgerufen, wenn Optionen im Zahnrad geändert wurden."""
    await hass.config_entries.async_reload(entry.entry_id)


async def _ensure_registry_translation_keys(hass: HomeAssistant, entry: ConfigEntry):
    """Best-effort: setze `translation_key` und `original_name` in entity registry, wenn fehlen.

    This fixes cases where older installs or import paths created entities without
    a translation_key/original_name, resulting in UI names like "Whirlpool None".
    """
    try:
        ent_reg = er.async_get(hass)
        # Prefer helper that lists entries for this config entry if available.
        try:
            entries = er.async_entries_for_config_entry(ent_reg, entry.entry_id)
        except Exception:
            # Fallback: iterate all entries and filter by config_entry_id
            entries = [e for e in ent_reg.entities.values() if getattr(e, "config_entry_id", None) == entry.entry_id]

        changed_any = False
        for e in entries:
            # Only touch our platform's entries
            if getattr(e, "platform", None) != DOMAIN:
                continue

            # Derive sensible suffix from unique_id. The unique_id format is
            # "{entry_id}_{suffix}", but the suffix itself may contain underscores
            # (e.g. "bath_60"), so prefer extracting the part after the entry_id.
            suffix = None
            if getattr(e, "unique_id", None):
                try:
                    uid = str(e.unique_id)
                    eid = getattr(entry, "entry_id", None)
                    if eid and uid.startswith(f"{eid}_"):
                        suffix = uid[len(eid) + 1 :]
                    else:
                        # fallback: if there are multiple parts, use everything after the first token
                        parts = uid.split("_")
                        if len(parts) > 1:
                            suffix = "_".join(parts[1:])
                        else:
                            suffix = parts[-1]
                except Exception:
                    suffix = None

            # If translation_key missing, set it to suffix (many translation keys match suffix)
            if not getattr(e, "translation_key", None) and suffix:
                try:
                    ent_reg.async_update_entity(e.entity_id, translation_key=suffix)
                    changed_any = True
                    _LOGGER.debug("Set translation_key=%s for %s", suffix, e.entity_id)
                except Exception:
                    _LOGGER.debug("Failed to set translation_key for %s", e.entity_id)

            # If original_name missing, set a human-friendly fallback based on suffix
            if getattr(e, "original_name", None) is None:
                suggestion = None
                if suffix:
                    suggestion = suffix.replace("_", " ").replace("  ", " ").strip().title()
                if not suggestion:
                    suggestion = e.entity_id.split(".", 1)[-1].replace("_", " ").title()
                try:
                    ent_reg.async_update_entity(e.entity_id, name=suggestion)
                    changed_any = True
                    _LOGGER.debug("Set original_name='%s' for %s", suggestion, e.entity_id)
                except Exception:
                    _LOGGER.debug("Failed to set original_name for %s", e.entity_id)

                    # If the registry produced a placeholder object_id like 'none' (entity_id contains '_none'),
                    # attempt to rename the entity_id to a sensible one based on the suffix.
                    try:
                        obj = str(e.entity_id).split('.', 1)[1]
                        if obj.startswith('whirlpool_none') or obj == 'none' or '_none' in obj:
                            # build candidate object_id: prefer suffix, else fallback to sanitized suggestion
                            cand_base = suffix or suggestion or obj
                            # simple slugify: keep a-z0-9 and underscore
                            import re
                            cand = re.sub(r'[^a-z0-9_]', '', str(cand_base).lower().replace(' ', '_'))
                            if not cand:
                                cand = f"{e.unique_id.split('_')[-1]}"
                            new_eid = f"{e.entity_id.split('.')[0]}.{cand}"
                            # only attempt if different
                            if new_eid != e.entity_id:
                                try:
                                    ent_reg.async_update_entity(e.entity_id, new_entity_id=new_eid)
                                    _LOGGER.info("Renamed %s -> %s to avoid placeholder 'none' object id", e.entity_id, new_eid)
                                    changed_any = True
                                except Exception as ex:
                                    _LOGGER.debug("Could not rename %s -> %s: %s", e.entity_id, new_eid, ex)
                    except Exception:
                        # best-effort: ignore
                        pass

        if changed_any:
            _LOGGER.info("Updated entity registry names/translation_keys for config entry %s", entry.entry_id)
    except Exception:
        _LOGGER.exception("Error while ensuring registry translation keys for %s", entry.entry_id)

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Entladen der Integration."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)