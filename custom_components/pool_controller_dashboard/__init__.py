from __future__ import annotations

import logging
from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)

DOMAIN = "pool_controller_dashboard"


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Setup via configuration.yaml (unused, dashboard is panel_custom only)."""
    _LOGGER.debug("%s loaded via configuration.yaml", DOMAIN)
    return True


async def async_setup_entry(hass: HomeAssistant, entry):
    """No config entries required for panel_custom dashboard."""
    _LOGGER.debug("%s does not use config entries", DOMAIN)
    return True
