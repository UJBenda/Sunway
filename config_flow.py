import logging
import voluptuous as vol
from typing import Any, Dict, Optional

import homeassistant.helpers.config_validation as cv
from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_PORT, CONF_SLAVE
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult

from .const import (
    DOMAIN, DEFAULT_PORT, DEFAULT_SLAVE_ID,
    SCAN_GROUP_REALTIME, SCAN_GROUP_DAILY_TOTALS, SCAN_GROUP_LIFETIME_TOTALS, SCAN_GROUP_INFO
)
from pymodbus.client import AsyncModbusTcpClient

_LOGGER = logging.getLogger(__name__)

DATA_SCHEMA = vol.Schema({
    vol.Required(CONF_HOST): str,
    vol.Required(CONF_PORT, default=DEFAULT_PORT): cv.port,
    vol.Required(CONF_SLAVE, default=DEFAULT_SLAVE_ID): vol.Coerce(int),
})

OPTIONS_SCHEMA = vol.Schema({
    vol.Optional(SCAN_GROUP_REALTIME, default=30): vol.All(vol.Coerce(int), vol.Range(min=5)),
    vol.Optional(SCAN_GROUP_DAILY_TOTALS, default=120): vol.All(vol.Coerce(int), vol.Range(min=30)),
    vol.Optional(SCAN_GROUP_LIFETIME_TOTALS, default=600): vol.All(vol.Coerce(int), vol.Range(min=60)),
    vol.Optional(SCAN_GROUP_INFO, default=3600): vol.All(vol.Coerce(int), vol.Range(min=300)),
})

async def test_connection(host: str, port: int, slave: int) -> bool:
    """Otestuje připojení k Modbus zařízení."""
    try:
        client = AsyncModbusTcpClient(host, port=port)
        await client.connect()
        if client.connected:
            await client.close()
            return True
    except Exception as e:
        _LOGGER.error(f"Connection test failed: {e}")
    return False

class SunwayFveConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Sunway FVE Modbus."""
    VERSION = 1

    async def async_step_user(
        self, user_input: Optional[Dict[str, Any]] = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors: Dict[str, str] = {}
        if user_input is not None:
            unique_id = f"{user_input[CONF_HOST]}:{user_input[CONF_PORT]}-{user_input[CONF_SLAVE]}"
            await self.async_set_unique_id(unique_id)
            self._abort_if_unique_id_configured()

            # Testujeme připojení
            if not await test_connection(user_input[CONF_HOST], user_input[CONF_PORT], user_input[CONF_SLAVE]):
                errors["base"] = "connection_error"  # Chybová zpráva pro zásadu
                return self.async_show_form(step_id="user", data_schema=DATA_SCHEMA, errors=errors)

            # Uložíme data z úvodního kroku; scan intervaly se nastaví v Options
            return self.async_create_entry(title=f"Sunway FVE ({user_input[CONF_HOST]})", data=user_input, options={})

        return self.async_show_form(
            step_id="user", data_schema=DATA_SCHEMA, errors=errors
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: config_entries.ConfigEntry) -> config_entries.OptionsFlow:
        """Vytvoří options flow handler."""
        return SunwayFveOptionsFlowHandler(config_entry)


class SunwayFveOptionsFlowHandler(config_entries.OptionsFlow):
    """Zpracovává options flow pro Sunway FVE - pro intervaly skupin."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Inicializace options flow."""
        self.config_entry = config_entry

    async def async_step_init(
        self, user_input: Optional[Dict[str, Any]] = None
    ) -> FlowResult:
        """Spravuje options - intervaly pro skupiny."""
        errors: Dict[str, str] = {}

        if user_input is not None:
            # Uložíme nastavené intervaly jako options
            new_options = self.config_entry.options.copy()
            new_options.update(user_input)
            return self.async_create_entry(title="", data=new_options)

        # Vytvoříme schéma s aktuálními/výchozími hodnotami intervalů
        options_schema_with_defaults = vol.Schema({
             vol.Optional(
                 group,
                 default=self.config_entry.options.get(group, default_interval)
             ): vol.All(vol.Coerce(int), vol.Range(min=5
