
"""ChoreShore binary sensor platform."""
import logging
from typing import Any, Dict

from homeassistant.components.binary_sensor import (
    BinarySensorEntity,
    BinarySensorDeviceClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
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
    """Set up ChoreShore binary sensor platform."""
    coordinator = hass.data[DOMAIN][config_entry.entry_id]
    
    # Only create household-level binary sensors (no per-task redundancy)
    entities = [
        ChoreShoreOverdueTasksBinarySensor(coordinator),
        ChoreShorePendingTasksBinarySensor(coordinator),
    ]
    
    _LOGGER.info("Setting up %d ChoreShore binary sensor entities", len(entities))
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

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Return additional state attributes."""
        if not self.coordinator.data or "analytics" not in self.coordinator.data:
            return {}
        
        analytics = self.coordinator.data["analytics"]
        return {
            "overdue_count": analytics.get("overdue_tasks", 0),
            "total_tasks": analytics.get("total_tasks", 0),
        }

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

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Return additional state attributes."""
        if not self.coordinator.data or "analytics" not in self.coordinator.data:
            return {}
        
        analytics = self.coordinator.data["analytics"]
        return {
            "pending_count": analytics.get("pending_tasks", 0),
            "total_tasks": analytics.get("total_tasks", 0),
        }
