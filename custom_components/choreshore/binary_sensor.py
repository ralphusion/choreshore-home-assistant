
"""ChoreShore binary sensor platform."""
import logging
from datetime import datetime
from typing import Any, Dict, Optional

from homeassistant.components.binary_sensor import (
    BinarySensorEntity,
    BinarySensorDeviceClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, TASK_STATUS_PENDING, TASK_STATUS_OVERDUE
from .coordinator import ChoreShoreDateUpdateCoordinator

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up ChoreShore binary sensor platform."""
    coordinator = hass.data[DOMAIN][config_entry.entry_id]
    
    entities = []
    
    # Create binary sensors for tasks
    if coordinator.data and "chore_instances" in coordinator.data:
        for task in coordinator.data["chore_instances"]:
            if task.get("status") in [TASK_STATUS_PENDING]:
                entities.append(ChoreShoreTaskBinarySensor(coordinator, task))
    
    # Add household-level binary sensors
    entities.extend([
        ChoreShoreOverdueTasksBinarySensor(coordinator),
        ChoreShorePendingTasksBinarySensor(coordinator),
    ])
    
    async_add_entities(entities)

class ChoreShoreBaseBinarySensor(CoordinatorEntity, BinarySensorEntity):
    """Base ChoreShore binary sensor."""

    def __init__(self, coordinator: ChoreShoreDateUpdateCoordinator) -> None:
        """Initialize the binary sensor."""
        super().__init__(coordinator)
        self._attr_device_info = {
            "identifiers": {(DOMAIN, coordinator.household_id)},
            "name": "ChoreShore Household",
            "manufacturer": "ChoreShore",
            "model": "Household Management",
        }

class ChoreShoreTaskBinarySensor(ChoreShoreBaseBinarySensor):
    """Binary sensor for individual tasks."""

    def __init__(self, coordinator: ChoreShoreDateUpdateCoordinator, task: Dict[str, Any]) -> None:
        """Initialize the task binary sensor."""
        super().__init__(coordinator)
        self._task = task
        self._task_id = task["id"]
        self._chore_name = task.get("chores", {}).get("name", "Unknown Task")

    @property
    def name(self) -> str:
        """Return the name of the binary sensor."""
        return f"ChoreShore {self._chore_name}"

    @property
    def unique_id(self) -> str:
        """Return the unique ID of the binary sensor."""
        return f"{DOMAIN}_task_{self._task_id}"

    @property
    def icon(self) -> str:
        """Return the icon based on task status."""
        if self.is_on:
            due_date = self._task.get("due_date", "")
            if due_date < datetime.now().date().isoformat():
                return "mdi:alert-circle"
            return "mdi:clock-alert"
        return "mdi:check-circle"

    @property
    def is_on(self) -> bool:
        """Return true if the task is pending or overdue."""
        current_task = self._get_current_task()
        if not current_task:
            return False
        return current_task.get("status") == TASK_STATUS_PENDING

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Return additional state attributes."""
        current_task = self._get_current_task()
        if not current_task:
            return {}

        chore = current_task.get("chores", {})
        assigned_user = current_task.get("assigned_user", {})
        
        due_date = current_task.get("due_date", "")
        is_overdue = due_date < datetime.now().date().isoformat()
        
        return {
            "task_id": current_task["id"],
            "chore_name": chore.get("name"),
            "description": chore.get("description"),
            "category": chore.get("category"),
            "priority": chore.get("priority"),
            "location": chore.get("location"),
            "estimated_duration": chore.get("estimated_duration"),
            "due_date": due_date,
            "due_time": current_task.get("due_time"),
            "assigned_to": f"{assigned_user.get('first_name', '')} {assigned_user.get('last_name', '')}".strip(),
            "status": current_task.get("status"),
            "is_overdue": is_overdue,
        }

    def _get_current_task(self) -> Optional[Dict[str, Any]]:
        """Get the current task data from coordinator."""
        if not self.coordinator.data or "chore_instances" not in self.coordinator.data:
            return None
        
        for task in self.coordinator.data["chore_instances"]:
            if task["id"] == self._task_id:
                return task
        return None

class ChoreShoreOverdueTasksBinarySensor(ChoreShoreBaseBinarySensor):
    """Binary sensor for overdue tasks."""

    _attr_name = "ChoreShore Has Overdue Tasks"
    _attr_unique_id = f"{DOMAIN}_has_overdue_tasks"
    _attr_icon = "mdi:alert-circle"
    _attr_device_class = BinarySensorDeviceClass.PROBLEM

    @property
    def is_on(self) -> bool:
        """Return true if there are overdue tasks."""
        if self.coordinator.data and "analytics" in self.coordinator.data:
            return self.coordinator.data["analytics"].get("overdue_tasks", 0) > 0
        return False

class ChoreShorePendingTasksBinarySensor(ChoreShoreBaseBinarySensor):
    """Binary sensor for pending tasks."""

    _attr_name = "ChoreShore Has Pending Tasks"
    _attr_unique_id = f"{DOMAIN}_has_pending_tasks"
    _attr_icon = "mdi:clock-outline"

    @property
    def is_on(self) -> bool:
        """Return true if there are pending tasks."""
        if self.coordinator.data and "analytics" in self.coordinator.data:
            return self.coordinator.data["analytics"].get("pending_tasks", 0) > 0
        return False
