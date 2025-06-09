
"""ChoreShore switch platform."""
import logging
from typing import Any, Dict, Optional

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, TASK_STATUS_PENDING, TASK_STATUS_COMPLETED
from .coordinator import ChoreShoreDateUpdateCoordinator

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up ChoreShore switch platform."""
    coordinator = hass.data[DOMAIN][config_entry.entry_id]
    
    entities = []
    
    # Create switches for pending tasks
    if coordinator.data and "chore_instances" in coordinator.data:
        for task in coordinator.data["chore_instances"]:
            if task.get("status") == TASK_STATUS_PENDING:
                entities.append(ChoreShoreTaskSwitch(coordinator, task))
    
    async_add_entities(entities)

class ChoreShoreTaskSwitch(CoordinatorEntity, SwitchEntity):
    """Switch entity for ChoreShore tasks."""

    def __init__(self, coordinator: ChoreShoreDateUpdateCoordinator, task: Dict[str, Any]) -> None:
        """Initialize the switch."""
        super().__init__(coordinator)
        self._task = task
        self._task_id = task["id"]
        self._chore_name = task.get("chores", {}).get("name", "Unknown Task")
        
        self._attr_device_info = {
            "identifiers": {(DOMAIN, coordinator.household_id)},
            "name": "ChoreShore Household",
            "manufacturer": "ChoreShore",
            "model": "Household Management",
        }

    @property
    def name(self) -> str:
        """Return the name of the switch."""
        return f"ChoreShore {self._chore_name} Complete"

    @property
    def unique_id(self) -> str:
        """Return the unique ID of the switch."""
        return f"{DOMAIN}_task_switch_{self._task_id}"

    @property
    def icon(self) -> str:
        """Return the icon of the switch."""
        return "mdi:check-circle" if self.is_on else "mdi:circle-outline"

    @property
    def is_on(self) -> bool:
        """Return true if the task is completed."""
        current_task = self._get_current_task()
        if not current_task:
            return False
        return current_task.get("status") == TASK_STATUS_COMPLETED

    @property
    def available(self) -> bool:
        """Return if the switch is available."""
        current_task = self._get_current_task()
        if not current_task:
            return False
        # Only allow switching if task is pending or completed
        return current_task.get("status") in [TASK_STATUS_PENDING, TASK_STATUS_COMPLETED]

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Return additional state attributes."""
        current_task = self._get_current_task()
        if not current_task:
            return {}

        chore = current_task.get("chores", {})
        assigned_user = current_task.get("assigned_user", {})
        
        return {
            "task_id": current_task["id"],
            "chore_name": chore.get("name"),
            "description": chore.get("description"),
            "category": chore.get("category"),
            "priority": chore.get("priority"),
            "location": chore.get("location"),
            "due_date": current_task.get("due_date"),
            "due_time": current_task.get("due_time"),
            "assigned_to": f"{assigned_user.get('first_name', '')} {assigned_user.get('last_name', '')}".strip(),
            "status": current_task.get("status"),
        }

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the switch on (complete the task)."""
        success = await self.coordinator.complete_task(self._task_id)
        if success:
            await self.coordinator.async_request_refresh()
        else:
            _LOGGER.error("Failed to complete task %s", self._task_id)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the switch off (not supported for task completion)."""
        _LOGGER.warning("Cannot uncomplete a task via switch")

    def _get_current_task(self) -> Optional[Dict[str, Any]]:
        """Get the current task data from coordinator."""
        if not self.coordinator.data or "chore_instances" not in self.coordinator.data:
            return None
        
        for task in self.coordinator.data["chore_instances"]:
            if task["id"] == self._task_id:
                return task
        return None
