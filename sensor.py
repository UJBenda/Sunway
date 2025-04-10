# custom_components/sunway_fve/sensor.py
import logging
from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.core import callback
from .const import DOMAIN, SENSOR_DESCRIPTIONS # Import definic
from . import SunwayFveCoordinator # Import coordinatora

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass, entry, async_add_entities):
    """Set up Sunway FVE sensor entities."""
    coordinator: SunwayFveCoordinator = hass.data[DOMAIN][entry.entry_id]

    entities = []
    for description in SENSOR_DESCRIPTIONS:
        # Vytvoříme senzory pro všechny definované entity (RO i RW)
        entities.append(SunwayModbusSensor(coordinator, description))
        _LOGGER.debug(f"Setting up sensor: {description.name} ({description.key})")

    async_add_entities(entities)

class SunwayModbusSensor(CoordinatorEntity, SensorEntity):
    """Representation of a Sunway FVE Modbus sensor."""

    def __init__(self, coordinator: SunwayFveCoordinator, description):
        """Initialize the sensor."""
        super().__init__(coordinator)
        self.entity_description = description # Použijeme dataclass jako entity_description
        self._attr_name = f"Sunway {description.name}" # Název v HA
        # Unikátní ID = doména + identifikátor zařízení (např. host) + klíč senzoru
        self._attr_unique_id = f"{DOMAIN}_{coordinator.host}_{description.key}"
        # Device Info - propojí všechny entity k jednomu zařízení
        # Můžete sem přidat Sériové číslo (SN) a Verzi firmwaru, pokud je čtete
        self._attr_device_info = {
            "identifiers": {(DOMAIN, coordinator.host, coordinator.slave_id)},
            "name": f"Sunway FVE ({coordinator.host})",
            "manufacturer": "Sunway",
            # "model": "Váš Model", # Zjistěte model, pokud je dostupný
            # "sw_version": coordinator.data.get("firmware_version"), # Příklad
            # "serial_number": coordinator.data.get("inverter_sn"), # Příklad
        }
        self._attr_native_value = self._get_coordinator_value() # Počáteční hodnota

    def _get_coordinator_value(self):
        """Helper to get value from coordinator data."""
        return self.coordinator.data.get(self.entity_description.key)

    @property
    def native_value(self):
        """Return the state of the sensor."""
        # Hodnota se bere přímo z coordinator.data
        val = self._get_coordinator_value()
        # Zde můžete přidat specifické parsování, pokud je potřeba
        # Např. pro statusy, bitové masky atd.
        # if self.entity_description.key == "running_status":
        #     return self._map_status(val)
        return val

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self._attr_native_value = self._get_coordinator_value()
        self.async_write_ha_state()
        _LOGGER.debug(f"Updating sensor {self.name}: {self.native_value}")

    # --- Volitelné vlastnosti pro lepší integraci ---
    @property
    def native_unit_of_measurement(self):
        return self.entity_description.unit

    @property
    def device_class(self):
        return self.entity_description.device_class

    @property
    def state_class(self):
         return self.entity_description.state_class

    # Příklad funkce pro mapování statusu (pokud by byla potřeba)
    # def _map_status(self, value):
    #     status_map = {0: "Wait", 1: "Check", 2: "On Grid", 3: "Fault", 4: "Flash", 5: "Off Grid"}
    #     return status_map.get(value, f"Unknown ({value})")