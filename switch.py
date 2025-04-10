# custom_components/sunway_fve/switch.py
import logging
from homeassistant.components.switch import SwitchEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from .const import DOMAIN, RW_REGISTER_MAP
from . import SunwayFveCoordinator

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass, entry, async_add_entities):
    """Set up Sunway FVE switch entities."""
    coordinator: SunwayFveCoordinator = hass.data[DOMAIN][entry.entry_id]
    entities = []

    for key, params in RW_REGISTER_MAP.items():
        if params.get("type") == "switch":
            entities.append(SunwayModbusSwitch(coordinator, key, params))
            _LOGGER.debug(f"Setting up switch: {key}")

    async_add_entities(entities)

class SunwayModbusSwitch(CoordinatorEntity, SwitchEntity):
    """Representation of a Sunway FVE Modbus switch."""

    def __init__(self, coordinator: SunwayFveCoordinator, key: str, params: dict):
        """Initialize the switch."""
        super().__init__(coordinator)
        self._key = key
        self._params = params
        self._attr_name = f"Sunway {key.replace('_', ' ').title()}" # Název
        self._attr_unique_id = f"{DOMAIN}_{coordinator.host}_{key}"
        # Propojení k zařízení
        self._attr_device_info = {
            "identifiers": {(DOMAIN, coordinator.host, coordinator.slave_id)},
            # Další info jako v sensor.py
        }

    @property
    def is_on(self) -> bool | None:
        """Return true if switch is on."""
        # Hodnota se čte z coordinatora, mapovaná zpět na True/False
        raw_value = self.coordinator.data.get(self._key)
        if raw_value is None:
            return None
        # Najdeme klíč v write_map, jehož hodnota odpovídá přečtené hodnotě
        for state, write_val in self._params.get("write_map", {}).items():
            if write_val == raw_value:
                return state # Vrací True nebo False
        _LOGGER.warning(f"Unknown state {raw_value} for switch {self.name}")
        return None # Neznámý stav

    async def async_turn_on(self, **kwargs) -> None:
        """Turn the entity on."""
        value_to_write = self._params.get("write_map", {}).get(True)
        if value_to_write is not None:
            address = self._params["address"]
            _LOGGER.debug(f"Turning ON switch {self.name} (Register: {address}, Value: {value_to_write})")
            success = await self.coordinator.async_write_register(address, value_to_write)
            if not success:
                 _LOGGER.error(f"Failed to turn ON switch {self.name}")
            # Coordinator si po úspěšném zápisu sám vyžádá refresh

    async def async_turn_off(self, **kwargs) -> None:
        """Turn the entity off."""
        value_to_write = self._params.get("write_map", {}).get(False)
        if value_to_write is not None:
            address = self._params["address"]
            _LOGGER.debug(f"Turning OFF switch {self.name} (Register: {address}, Value: {value_to_write})")
            success = await self.coordinator.async_write_register(address, value_to_write)
            if not success:
                 _LOGGER.error(f"Failed to turn OFF switch {self.name}")