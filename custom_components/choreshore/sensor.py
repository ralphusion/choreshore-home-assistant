
"""ChoreShore sensor platform."""
import logging
from datetime import datetime
from typing import Any, Dict, Optional

from homeassistant.components.sensor import (
    SensorEntity,
    SensorDeviceClass,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import ChoreShoreDateUpdateCoordinator

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up ChoreShore sensor platform."""
    coordinator = hass.data[DOMAIN][config_entry.entry_id]
    
    entities = []
    
    # Analytics sensors (household-level)
    entities.extend([
        ChoreShoreTotalTasksSensor(coordinator),
        ChoreShoreCompletedTasksSensor(coordinator),
        ChoreShoreOverdueTasksSensor(coordinator),
        ChoreShorePendingTasksSensor(coordinator),
        ChoreShoreCompletionRateSensor(coordinator),
    ])
    
    # Member performance sensors (individual member stats)
    if coordinator.data and "members" in coordinator.data:
        for member in coordinator.data["members"]:
            entities.append(ChoreShoreMemberPerformanceSensor(coordinator, member))
    
    _LOGGER.info("Setting up %d ChoreShore sensor entities", len(entities))
    async_add_entities(entities)

class ChoreShoreBaseSensor(CoordinatorEntity, SensorEntity):
    """Base ChoreShore sensor."""

    def __init__(self, coordinator: ChoreShoreDateUpdateCoordinator) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._attr_device_info = {
            "identifiers": {(DOMAIN, coordinator.household_id)},
            "name": "ChoreShore Household",
            "manufacturer": "ChoreShore",
            "model": "Household Management",
        }

class ChoreShoreTotalTasksSensor(ChoreShoreBaseSensor):
    """Total tasks sensor."""

    _attr_name = "ChoreShore Total Tasks"
    _attr_unique_id = f"{DOMAIN}_total_tasks"
    _attr_icon = "mdi:format-list-checks"
    _attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def native_value(self) -> Optional[int]:
        """Return the state of the sensor."""
        if not self.coordinator.data:
            return 0
        
        analytics = self.coordinator.data.get("analytics", {})
        value = analytics.get("total_tasks", 0)
        _LOGGER.debug("Total tasks sensor returning: %s", value)
        return value

class ChoreShoreCompletedTasksSensor(ChoreShoreBaseSensor):
    """Completed tasks sensor."""

    _attr_name = "ChoreShore Completed Tasks"
    _attr_unique_id = f"{DOMAIN}_completed_tasks"
    _attr_icon = "mdi:check-circle"
    _attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def native_value(self) -> Optional[int]:
        """Return the state of the sensor."""
        if not self.coordinator.data:
            return 0
        
        analytics = self.coordinator.data.get("analytics", {})
        value = analytics.get("completed_tasks", 0)
        _LOGGER.debug("Completed tasks sensor returning: %s", value)
        return value

class ChoreShoreOverdueTasksSensor(ChoreShoreBaseSensor):
    """Overdue tasks sensor."""

    _attr_name = "ChoreShore Overdue Tasks"
    _attr_unique_id = f"{DOMAIN}_overdue_tasks"
    _attr_icon = "mdi:alert-circle"
    _attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def native_value(self) -> Optional[int]:
        """Return the state of the sensor."""
        if not self.coordinator.data:
            return 0
        
        analytics = self.coordinator.data.get("analytics", {})
        value = analytics.get("overdue_tasks", 0)
        _LOGGER.debug("Overdue tasks sensor returning: %s", value)
        return value

class ChoreShorePendingTasksSensor(ChoreShoreBaseSensor):
    """Pending tasks sensor."""

    _attr_name = "ChoreShore Pending Tasks"
    _attr_unique_id = f"{DOMAIN}_pending_tasks"
    _attr_icon = "mdi:clock-outline"
    _attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def native_value(self) -> Optional[int]:
        """Return the state of the sensor."""
        if not self.coordinator.data:
            return 0
        
        analytics = self.coordinator.data.get("analytics", {})
        value = analytics.get("pending_tasks", 0)
        _LOGGER.debug("Pending tasks sensor returning: %s", value)
        return value

class ChoreShoreCompletionRateSensor(ChoreShoreBaseSensor):
    """Completion rate sensor."""

    _attr_name = "ChoreShore Completion Rate"
    _attr_unique_id = f"{DOMAIN}_completion_rate"
    _attr_icon = "mdi:percent"
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = "%"

    @property
    def native_value(self) -> Optional[float]:
        """Return the state of the sensor."""
        if not self.coordinator.data:
            return 0
        
        analytics = self.coordinator.data.get("analytics", {})
        value = analytics.get("completion_rate", 0)
        _LOGGER.debug("Completion rate sensor returning: %s", value)
        return value

class ChoreShoreMemberPerformanceSensor(ChoreShoreBaseSensor):
    """Member performance sensor."""

    def __init__(self, coordinator: ChoreShoreDateUpdateCoordinator, member: Dict[str, Any]) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._member = member
        self._member_id = member["id"]
        self._member_name = f"{member.get('first_name', 'Unknown')} {member.get('last_name', '')}"

    @property
    def name(self) -> str:
        """Return the name of the sensor."""
        return f"ChoreShore {self._member_name} Performance"

    @property
    def unique_id(self) -> str:
        """Return the unique ID of the sensor."""
        return f"{DOMAIN}_member_{self._member_id}_performance"

    @property
    def icon(self) -> str:
        """Return the icon of the sensor."""
        return "mdi:account-check"

    @property
    def native_value(self) -> Optional[float]:
        """Return the completion rate for this member."""
        if not self.coordinator.data or "chore_instances" not in self.coordinator.data:
            return 0

        chore_instances = self.coordinator.data["chore_instances"]
        member_tasks = [
            task for task in chore_instances
            if task.get("assigned_to") == self._member_id
        ]
        
        if not member_tasks:
            return 0
        
        completed = len([t for t in member_tasks if t.get("status") == "completed"])
        completion_rate = round((completed / len(member_tasks) * 100), 1)
        
        _LOGGER.debug("Member %s completion rate: %s%%", self._member_name, completion_rate)
        return completion_rate

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Return additional state attributes."""
        if not self.coordinator.data or "chore_instances" not in self.coordinator.data:
            return {}

        chore_instances = self.coordinator.data["chore_instances"]
        member_tasks = [
            task for task in chore_instances
            if task.get("assigned_to") == self._member_id
        ]
        
        completed = len([t for t in member_tasks if t.get("status") == "completed"])
        pending = len([t for t in member_tasks if t.get("status") == "pending"])
        
        # Calculate overdue tasks for this member
        overdue = 0
        today = datetime.now().date()
        for task in member_tasks:
            if task.get("status") == "pending" and task.get("due_date"):
                try:
                    due_date_str = task.get("due_date", "")
                    if isinstance(due_date_str, str):
                        due_date = datetime.strptime(due_date_str, "%Y-%m-%d").date()
                    else:
                        due_date = due_date_str
                    
                    if due_date < today:
                        overdue += 1
                except (ValueError, AttributeError):
                    pass
        
        completion_rate = round((completed / len(member_tasks) * 100) if member_tasks else 0, 1)
        
        return {
            "member_name": self._member_name,
            "member_role": self._member.get("role"),
            "total_tasks": len(member_tasks),
            "completed_tasks": completed,
            "pending_tasks": pending,
            "overdue_tasks": overdue,
            "completion_rate": completion_rate,
        }
