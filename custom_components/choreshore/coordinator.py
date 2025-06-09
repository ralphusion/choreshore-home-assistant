
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
        """Fetch data from ChoreShore API."""
        try:
            # Fetch multiple data sources concurrently
            tasks = await asyncio.gather(
                self._fetch_chore_instances(),
                self._fetch_analytics(),
                self._fetch_household_members(),
                return_exceptions=True
            )

            chore_instances, analytics, members = tasks

            # Handle any exceptions
            for result in tasks:
                if isinstance(result, Exception):
                    _LOGGER.error("Error fetching data: %s", result)
                    raise UpdateFailed(f"Error fetching data: {result}")

            return {
                "chore_instances": chore_instances or [],
                "analytics": analytics or {},
                "members": members or [],
                "last_updated": datetime.now(),
            }

        except Exception as err:
            _LOGGER.error("Error updating ChoreShore data: %s", err)
            raise UpdateFailed(f"Error updating data: {err}") from err

    async def _fetch_chore_instances(self) -> List[Dict[str, Any]]:
        """Fetch chore instances from the API."""
        url = f"{API_BASE_URL}/rest/v1/chore_instances"
        params = {
            "chores.household_id": f"eq.{self.household_id}",
            "select": """
                *,
                chores!inner (
                    name,
                    category,
                    priority,
                    description,
                    location,
                    estimated_duration,
                    instructions,
                    frequency_type,
                    frequency_config,
                    household_id
                ),
                assigned_user:profiles!assigned_to (
                    first_name,
                    last_name
                ),
                completed_user:profiles!completed_by (
                    first_name,
                    last_name
                )
            """,
        }

        async with self.session.get(
            url, headers=API_HEADERS, params=params, timeout=DEFAULT_TIMEOUT
        ) as response:
            if response.status == 200:
                return await response.json()
            else:
                _LOGGER.error("Error fetching chore instances: %s", response.status)
                return []

    async def _fetch_analytics(self) -> Dict[str, Any]:
        """Fetch analytics data."""
        # Calculate basic analytics from chore instances
        url = f"{API_BASE_URL}/rest/v1/chore_instances"
        params = {
            "chores.household_id": f"eq.{self.household_id}",
            "select": "status,due_date,completed_at",
        }

        async with self.session.get(
            url, headers=API_HEADERS, params=params, timeout=DEFAULT_TIMEOUT
        ) as response:
            if response.status == 200:
                instances = await response.json()
                return self._calculate_analytics(instances)
            else:
                _LOGGER.error("Error fetching analytics: %s", response.status)
                return {}

    async def _fetch_household_members(self) -> List[Dict[str, Any]]:
        """Fetch household members."""
        url = f"{API_BASE_URL}/rest/v1/profiles"
        params = {
            "household_id": f"eq.{self.household_id}",
            "select": "id,first_name,last_name,role,avatar_url",
        }

        async with self.session.get(
            url, headers=API_HEADERS, params=params, timeout=DEFAULT_TIMEOUT
        ) as response:
            if response.status == 200:
                return await response.json()
            else:
                _LOGGER.error("Error fetching household members: %s", response.status)
                return []

    def _calculate_analytics(self, instances: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate analytics from chore instances."""
        total_tasks = len(instances)
        completed_tasks = sum(1 for task in instances if task["status"] == "completed")
        overdue_tasks = sum(
            1 for task in instances 
            if task["status"] == "pending" and task["due_date"] < datetime.now().date().isoformat()
        )
        
        completion_rate = (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0
        
        return {
            "total_tasks": total_tasks,
            "completed_tasks": completed_tasks,
            "overdue_tasks": overdue_tasks,
            "pending_tasks": total_tasks - completed_tasks,
            "completion_rate": round(completion_rate, 1),
        }

    async def complete_task(self, task_id: str) -> bool:
        """Complete a task via the API."""
        try:
            url = f"{API_BASE_URL}/rest/v1/rpc/complete_shared_chore_instances"
            data = {
                "p_instance_id": task_id,
                "p_completed_by": self.user_id,
            }

            async with self.session.post(
                url, headers=API_HEADERS, json=data, timeout=DEFAULT_TIMEOUT
            ) as response:
                if response.status == 200:
                    await self.async_request_refresh()
                    return True
                else:
                    _LOGGER.error("Error completing task: %s", response.status)
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

            async with self.session.post(
                url, headers=API_HEADERS, json=data, timeout=DEFAULT_TIMEOUT
            ) as response:
                if response.status == 200:
                    await self.async_request_refresh()
                    return True
                else:
                    _LOGGER.error("Error skipping task: %s", response.status)
                    return False

        except Exception as err:
            _LOGGER.error("Error skipping task %s: %s", task_id, err)
            return False
