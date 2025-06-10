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
            _LOGGER.debug("Starting data fetch for household: %s", self.household_id)
            
            # Fetch multiple data sources concurrently
            tasks = await asyncio.gather(
                self._fetch_chore_instances(),
                self._fetch_household_members(),
                return_exceptions=True
            )

            chore_instances, members = tasks

            # Handle any exceptions
            for i, result in enumerate(tasks):
                if isinstance(result, Exception):
                    _LOGGER.error("Error fetching data source %d: %s", i, result)
                    raise UpdateFailed(f"Error fetching data: {result}")

            _LOGGER.debug("Fetched %d chore instances and %d members", 
                         len(chore_instances or []), len(members or []))

            # Calculate analytics from the fetched data
            analytics = self._calculate_analytics(chore_instances or [])
            _LOGGER.debug("Calculated analytics: %s", analytics)

            return {
                "chore_instances": chore_instances or [],
                "analytics": analytics,
                "members": members or [],
                "last_updated": datetime.now(),
            }

        except Exception as err:
            _LOGGER.error("Error updating ChoreShore data: %s", err)
            raise UpdateFailed(f"Error updating data: {err}") from err

    async def _fetch_chore_instances(self) -> List[Dict[str, Any]]:
        """Fetch chore instances from the API."""
        url = f"{API_BASE_URL}/rest/v1/chore_instances"
        
        # Use proper PostgREST syntax for filtering and joining
        params = {
            "select": "*, chores!inner(name, category, priority, description, location, estimated_duration, instructions, frequency_type, frequency_config, household_id), assigned_user:profiles!assigned_to(first_name, last_name), completed_user:profiles!completed_by(first_name, last_name)",
            "chores.household_id": f"eq.{self.household_id}",
            "order": "due_date.asc"
        }

        _LOGGER.debug("Fetching chore instances with URL: %s and params: %s", url, params)

        try:
            async with self.session.get(
                url, headers=API_HEADERS, params=params, timeout=DEFAULT_TIMEOUT
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    _LOGGER.debug("Successfully fetched %d chore instances", len(data))
                    return data
                else:
                    error_text = await response.text()
                    _LOGGER.error("Error fetching chore instances: %s - %s", response.status, error_text)
                    return []
        except Exception as err:
            _LOGGER.error("Exception fetching chore instances: %s", err)
            return []

    async def _fetch_household_members(self) -> List[Dict[str, Any]]:
        """Fetch household members."""
        url = f"{API_BASE_URL}/rest/v1/profiles"
        params = {
            "household_id": f"eq.{self.household_id}",
            "select": "id,first_name,last_name,role,avatar_url",
        }

        _LOGGER.debug("Fetching household members with params: %s", params)

        try:
            async with self.session.get(
                url, headers=API_HEADERS, params=params, timeout=DEFAULT_TIMEOUT
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    _LOGGER.debug("Successfully fetched %d household members", len(data))
                    return data
                else:
                    error_text = await response.text()
                    _LOGGER.error("Error fetching household members: %s - %s", response.status, error_text)
                    return []
        except Exception as err:
            _LOGGER.error("Exception fetching household members: %s", err)
            return []

    def _calculate_analytics(self, instances: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate analytics from chore instances."""
        if not instances:
            _LOGGER.debug("No instances to calculate analytics from")
            return {
                "total_tasks": 0,
                "completed_tasks": 0,
                "overdue_tasks": 0,
                "pending_tasks": 0,
                "completion_rate": 0,
            }

        total_tasks = len(instances)
        completed_tasks = 0
        overdue_tasks = 0
        pending_tasks = 0
        
        today = datetime.now().date()
        _LOGGER.debug("Calculating analytics for %d instances, today is %s", total_tasks, today)

        for task in instances:
            status = task.get("status", "")
            due_date_str = task.get("due_date", "")
            
            _LOGGER.debug("Processing task: status=%s, due_date=%s", status, due_date_str)
            
            if status == "completed":
                completed_tasks += 1
            elif status == "pending":
                pending_tasks += 1
                # Check if task is overdue
                if due_date_str:
                    try:
                        # Parse the due_date string to a date object
                        if isinstance(due_date_str, str):
                            due_date = datetime.fromisoformat(due_date_str.replace('Z', '+00:00')).date()
                        else:
                            due_date = due_date_str
                        
                        if due_date < today:
                            overdue_tasks += 1
                            _LOGGER.debug("Task is overdue: due=%s, today=%s", due_date, today)
                    except (ValueError, AttributeError) as e:
                        _LOGGER.warning("Could not parse due_date '%s': %s", due_date_str, e)
        
        completion_rate = round((completed_tasks / total_tasks * 100) if total_tasks > 0 else 0, 1)
        
        analytics = {
            "total_tasks": total_tasks,
            "completed_tasks": completed_tasks,
            "overdue_tasks": overdue_tasks,
            "pending_tasks": pending_tasks,
            "completion_rate": completion_rate,
        }
        
        _LOGGER.debug("Calculated analytics: %s", analytics)
        return analytics

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
