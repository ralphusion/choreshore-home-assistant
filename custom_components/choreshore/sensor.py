
"""ChoreShore sensor platform."""
import logging
from datetime import datetime
from typing import Any, Dict, Optional, List

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

from .const import DOMAIN, TASK_STATUS_PENDING
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
    
    # Non-redundant chore sensors (one per unique chore)
    if coordinator.data and "chore_instances" in coordinator.data:
        unique_chores = {}
        
        # Group all instances by chore_id to identify unique chores
        for task in coordinator.data["chore_instances"]:
            chore_data = task.get("chores", {})
            chore_id = chore_data.get("id")
            if chore_id and chore_id not in unique_chores:
                unique_chores[chore_id] = chore_data
        
        # Create one sensor per unique chore
        for chore_id, chore_data in unique_chores.items():
            entities.append(ChoreShoreUniqueChoreStatusSensor(coordinator, chore_id, chore_data))
    
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

class ChoreShoreUniqueChoreStatusSensor(ChoreShoreBaseSensor):
    """Non-redundant chore status sensor (one per unique chore, aggregating all instances)."""

    def __init__(self, coordinator: ChoreShoreDateUpdateCoordinator, chore_id: str, chore_data: Dict[str, Any]) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._chore_id = chore_id
        self._chore_data = chore_data
        self._chore_name = chore_data.get("name", "Unknown Chore")

    @property
    def name(self) -> str:
        """Return the name of the sensor."""
        return f"ChoreShore {self._chore_name}"

    @property
    def unique_id(self) -> str:
        """Return the unique ID of the sensor."""
        return f"{DOMAIN}_chore_{self._chore_id}"

    @property
    def icon(self) -> str:
        """Return the icon of the sensor."""
        # Get all current instances to determine status
        instances = self._get_all_instances()
        pending_count = len([i for i in instances if i.get("status") == "pending"])
        completed_count = len([i for i in instances if i.get("status") == "completed"])
        
        if pending_count > 0:
            # Check if any are overdue
            today = datetime.now().date()
            overdue = any(
                datetime.strptime(i["due_date"], "%Y-%m-%d").date() < today 
                for i in instances 
                if i.get("status") == "pending"
            )
            return "mdi:alert-circle" if overdue else "mdi:clock-outline"
        elif completed_count > 0:
            return "mdi:check-circle"
        else:
            return "mdi:clipboard-list"

    @property
    def state_class(self) -> str:
        """Return the state class."""
        return SensorStateClass.MEASUREMENT

    @property
    def native_value(self) -> Optional[int]:
        """Return the total number of instances for this chore."""
        instances = self._get_all_instances()
        count = len(instances)
        _LOGGER.debug("Chore %s has %d total instances", self._chore_name, count)
        return count

    @property
    def available(self) -> bool:
        """Return if the sensor is available."""
        return len(self._get_all_instances()) > 0

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Return comprehensive state attributes for this chore."""
        instances = self._get_all_instances()
        if not instances:
            return {
                "chore_name": self._chore_name,
                "chore_id": self._chore_id,
                "total_instances": 0,
                "pending_instances": 0,
                "completed_instances": 0,
                "overdue_instances": 0,
            }

        # Categorize instances
        pending_instances = [i for i in instances if i.get("status") == "pending"]
        completed_instances = [i for i in instances if i.get("status") == "completed"]
        skipped_instances = [i for i in instances if i.get("status") == "skipped"]
        
        # Analyze dates
        today = datetime.now().date()
        overdue_instances = []
        upcoming_instances = []
        
        for instance in pending_instances:
            try:
                due_date = datetime.strptime(instance["due_date"], "%Y-%m-%d").date()
                if due_date < today:
                    overdue_instances.append(instance)
                else:
                    upcoming_instances.append(instance)
            except (ValueError, KeyError):
                pass
        
        # Get unique assigned members
        assigned_members = set()
        for instance in instances:
            assigned_user = instance.get("assigned_user", {})
            if assigned_user:
                member_name = f"{assigned_user.get('first_name', '')} {assigned_user.get('last_name', '')}".strip()
                if member_name:
                    assigned_members.add(member_name)
        
        # Find date ranges
        all_dates = []
        for instance in instances:
            try:
                due_date = datetime.strptime(instance["due_date"], "%Y-%m-%d").date()
                all_dates.append(due_date)
            except (ValueError, KeyError):
                pass
        
        earliest_date = min(all_dates) if all_dates else None
        latest_date = max(all_dates) if all_dates else None
        
        # Find next due and most overdue
        next_due_date = None
        most_overdue_date = None
        
        if upcoming_instances:
            upcoming_dates = []
            for instance in upcoming_instances:
                try:
                    due_date = datetime.strptime(instance["due_date"], "%Y-%m-%d").date()
                    upcoming_dates.append(due_date)
                except (ValueError, KeyError):
                    pass
            next_due_date = min(upcoming_dates) if upcoming_dates else None
        
        if overdue_instances:
            overdue_dates = []
            for instance in overdue_instances:
                try:
                    due_date = datetime.strptime(instance["due_date"], "%Y-%m-%d").date()
                    overdue_dates.append(due_date)
                except (ValueError, KeyError):
                    pass
            most_overdue_date = min(overdue_dates) if overdue_dates else None

        return {
            "chore_name": self._chore_name,
            "chore_id": self._chore_id,
            "total_instances": len(instances),
            "pending_instances": len(pending_instances),
            "completed_instances": len(completed_instances),
            "skipped_instances": len(skipped_instances),
            "overdue_instances": len(overdue_instances),
            "upcoming_instances": len(upcoming_instances),
            "assigned_members": list(assigned_members),
            "date_range": {
                "earliest": earliest_date.isoformat() if earliest_date else None,
                "latest": latest_date.isoformat() if latest_date else None,
            },
            "next_due_date": next_due_date.isoformat() if next_due_date else None,
            "most_overdue_date": most_overdue_date.isoformat() if most_overdue_date else None,
            "category": self._chore_data.get("category"),
            "priority": self._chore_data.get("priority"),
            "location": self._chore_data.get("location"),
            "description": self._chore_data.get("description"),
            "estimated_duration": self._chore_data.get("estimated_duration"),
            "frequency_type": self._chore_data.get("frequency_type"),
        }

    def _get_all_instances(self) -> List[Dict[str, Any]]:
        """Get all instances for this chore from coordinator data."""
        if not self.coordinator.data or "chore_instances" not in self.coordinator.data:
            return []
        
        instances = []
        for task in self.coordinator.data["chore_instances"]:
            chore_data = task.get("chores", {})
            if chore_data.get("id") == self._chore_id:
                instances.append(task)
        
        return instances
