
"""Data update coordinator for ChoreShore."""
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import aiohttp
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_URL, CONF_API_KEY, CONF_NAME
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    DOMAIN,
    CONF_HOUSEHOLD_ID,
    CONF_USER_ID,
    CONF_UPDATE_INTERVAL,
    DEFAULT_UPDATE_INTERVAL,
    DEFAULT_TIMEOUT,
    API_BASE_URL,
    API_HEADERS,
)

_LOGGER = logging.getLogger(__name__)

class ChoreShoreDateUpdateCoordinator(DataUpdateCoordinator):
    """ChoreShore data update coordinator."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize the coordinator."""
        self.entry = entry
        self.household_id = entry.data[CONF_HOUSEHOLD_ID]
        self.user_id = entry.data[CONF_USER_ID]
        self.session = async_get_clientsession(hass)
        
        # Get user profile information for device naming
        self._user_name = None
        
        update_interval = timedelta(
            seconds=entry.options.get(CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL)
        )

        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_{self.user_id}",
            update_interval=update_interval,
        )

    @property
    def device_name(self) -> str:
        """Get the device name from config entry or generate one."""
        # First check if user provided a custom device name
        custom_name = self.entry.data.get(CONF_NAME)
        if custom_name:
            return custom_name
        
        # Fall back to auto-generated name
        return f"ChoreShore - {self.user_name}"

    @property
    def user_name(self) -> str:
        """Get the user's display name."""
        if self._user_name is None:
            # Try to get user name from coordinator data
            if self.data and "members" in self.data:
                for member in self.data["members"]:
                    if member.get("id") == self.user_id:
                        first_name = member.get("first_name", "")
                        last_name = member.get("last_name", "")
                        self._user_name = f"{first_name} {last_name}".strip() or "User"
                        break
            
            if self._user_name is None:
                self._user_name = f"User {self.user_id[:8]}"
        
        return self._user_name

    # ... keep existing code (_async_update_data, _filter_user_data, _calculate_user_analytics, complete_task, skip_task methods)
