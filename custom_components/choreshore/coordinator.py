"""Data update coordinator for ChoreShore."""
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import aiohttp
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_URL, CONF_API_KEY
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
        
        update_interval = timedelta(
            seconds=entry.options.get(CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL)
        )

        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=update_interval,
        )

    async def _async_update_data(self) -> Dict[str, Any]:
        """Fetch data from ChoreShore API via dedicated edge function."""
        try:
            _LOGGER.info("Fetching data via edge function for household: %s", self.household_id)
            
            # Call the dedicated edge function
            url = f"{API_BASE_URL}/functions/v1/ha-analytics"
            data = {"household_id": self.household_id}
            
            async with self.session.post(
                url, 
                headers=API_HEADERS, 
                json=data, 
                timeout=DEFAULT_TIMEOUT
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    _LOGGER.error("Edge function error: %s - %s", response.status, error_text)
                    raise UpdateFailed(f"Edge function error: {response.status}")
                
                result = await response.json()
                
                if "error" in result:
                    _LOGGER.error("Edge function returned error: %s", result["error"])
                    raise UpdateFailed(f"Edge function error: {result['error']}")
                
                # Log the results
                analytics = result.get("analytics", {})
                instances = result.get("chore_instances", [])
                members = result.get("members", [])
                
                _LOGGER.info("Successfully fetched data: %d instances, %d members", 
                           len(instances), len(members))
                _LOGGER.info("Analytics: %s", analytics)
                
                # Log a few sample instances for debugging
                if instances:
                    _LOGGER.info("Sample instance: %s", instances[0])
                
                return result

        except Exception as err:
            _LOGGER.error("Error updating ChoreShore data: %s", err, exc_info=True)
            raise UpdateFailed(f"Error updating data: {err}") from err

    async def complete_task(self, task_id: str) -> bool:
        """Complete a task via the API."""
        try:
            url = f"{API_BASE_URL}/rest/v1/rpc/complete_shared_chore_instances"
            data = {
                "p_instance_id": task_id,
                "p_completed_by": self.user_id,
            }

            _LOGGER.debug("Completing task %s for user %s", task_id, self.user_id)

            async with self.session.post(
                url, headers=API_HEADERS, json=data, timeout=DEFAULT_TIMEOUT
            ) as response:
                if response.status == 200:
                    _LOGGER.info("Successfully completed task %s", task_id)
                    await self.async_request_refresh()
                    return True
                else:
                    error_text = await response.text()
                    _LOGGER.error("Error completing task %s: %s - %s", task_id, response.status, error_text)
                    return False

        except Exception as err:
            _LOGGER.error("Error completing task %s: %s", task_id, err)
            return False

    async def skip_task(self, task_id: str, reason: Optional[str] = None) -> bool:
        """Skip a task via the API."""
        try:
            url = f"{API_BASE_URL}/rest/v1/rpc/skip_shared_chore_instances"
            data = {
                "p_instance_id": task_id,
                "p_skipped_by": self.user_id,
                "p_skip_reason": reason,
            }

            _LOGGER.debug("Skipping task %s for user %s with reason: %s", task_id, self.user_id, reason)

            async with self.session.post(
                url, headers=API_HEADERS, json=data, timeout=DEFAULT_TIMEOUT
            ) as response:
                if response.status == 200:
                    _LOGGER.info("Successfully skipped task %s", task_id)
                    await self.async_request_refresh()
                    return True
                else:
                    error_text = await response.text()
                    _LOGGER.error("Error skipping task %s: %s - %s", task_id, response.status, error_text)
                    return False

        except Exception as err:
            _LOGGER.error("Error skipping task %s: %s", task_id, err)
            return False
