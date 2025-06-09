
"""ChoreShore Home Assistant Integration."""
import asyncio
import logging
from datetime import timedelta
from typing import Any, Dict

import aiohttp
import voluptuous as vol
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_URL, CONF_API_KEY, Platform
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
import homeassistant.helpers.config_validation as cv

from .const import (
    DOMAIN,
    CONF_HOUSEHOLD_ID,
    CONF_USER_ID,
    CONF_UPDATE_INTERVAL,
    DEFAULT_UPDATE_INTERVAL,
    SERVICE_COMPLETE_TASK,
    SERVICE_SKIP_TASK,
    SERVICE_REFRESH_DATA,
)
from .coordinator import ChoreShoreDateUpdateCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [
    Platform.SENSOR,
    Platform.BINARY_SENSOR,
    Platform.SWITCH,
]

CONFIG_SCHEMA = vol.Schema({
    DOMAIN: vol.Schema({
        vol.Required(CONF_URL): cv.url,
        vol.Required(CONF_API_KEY): cv.string,
        vol.Required(CONF_HOUSEHOLD_ID): cv.string,
        vol.Required(CONF_USER_ID): cv.string,
        vol.Optional(CONF_UPDATE_INTERVAL, default=DEFAULT_UPDATE_INTERVAL): cv.positive_int,
    })
}, extra=vol.ALLOW_EXTRA)

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up ChoreShore from a config entry."""
    coordinator = ChoreShoreDateUpdateCoordinator(hass, entry)
    
    try:
        await coordinator.async_config_entry_first_refresh()
    except Exception as err:
        raise ConfigEntryNotReady(f"Unable to connect to ChoreShore: {err}") from err

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Register services
    async def complete_task_service(call: ServiceCall) -> None:
        """Service to complete a task."""
        task_id = call.data.get("task_id")
        await coordinator.complete_task(task_id)

    async def skip_task_service(call: ServiceCall) -> None:
        """Service to skip a task."""
        task_id = call.data.get("task_id")
        reason = call.data.get("reason")
        await coordinator.skip_task(task_id, reason)

    async def refresh_data_service(call: ServiceCall) -> None:
        """Service to refresh ChoreShore data."""
        await coordinator.async_request_refresh()

    hass.services.async_register(
        DOMAIN, SERVICE_COMPLETE_TASK, complete_task_service,
        schema=vol.Schema({
            vol.Required("task_id"): cv.string,
        })
    )

    hass.services.async_register(
        DOMAIN, SERVICE_SKIP_TASK, skip_task_service,
        schema=vol.Schema({
            vol.Required("task_id"): cv.string,
            vol.Optional("reason"): cv.string,
        })
    )

    hass.services.async_register(
        DOMAIN, SERVICE_REFRESH_DATA, refresh_data_service
    )

    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok
