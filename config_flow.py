# custom_components/sunway_fve/config_flow.py
import logging
import voluptuous as vol
from typing import Any, Dict, Optional

import homeassistant.helpers.config_validation as cv
from homeassistant import config_entries
# Odebrán import CONF_SCAN_INTERVAL, pokud už není potřeba jinde
from homeassistant.const import CONF_HOST, CONF_PORT, CONF_SLAVE
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult

# Import názvů skupin z const.py
from .const import (
    DOMAIN, DEFAULT_PORT, DEFAULT_SLAVE_ID,
    SCAN_GROUP_REALTIME, SCAN_GROUP_DAILY_TOTALS, SCAN_GROUP_LIFETIME_TOTALS, SCAN_GROUP_INFO
)

_LOGGER = logging.getLogger(__name__)

# Schéma pro úvodní krok - BEZ globálního scan_interval
DATA_SCHEMA = vol.Schema({
    vol.Required(CONF_HOST): str,
    vol.Required(CONF_PORT, default=DEFAULT_PORT): cv.port,
    vol.Required(CONF_SLAVE, default=DEFAULT_SLAVE_ID): vol.Coerce(int),
})

# Schéma pro Options Flow - intervaly pro skupiny
# Používáme názvy skupin jako klíče
OPTIONS_SCHEMA = vol.Schema({
    vol.Optional(SCAN_GROUP_REALTIME, default=30): vol.All(vol.Coerce(int), vol.Range(min=5)), # Rychlé aktualizace, min 5s
    vol.Optional(SCAN_GROUP_DAILY_TOTALS, default=120): vol.All(vol.Coerce(int), vol.Range(min=30)), # Denní součty, min 30s
    vol.Optional(SCAN_GROUP_LIFETIME_TOTALS, default=600): vol.All(vol.Coerce(int), vol.Range(min=60)), # Celkové součty, min 60s
    vol.Optional(SCAN_GROUP_INFO, default=3600): vol.All(vol.Coerce(int), vol.Range(min=300)), # Info, min 5 minut
})

# TODO: Funkce pro test připojení (zůstává stejná jako předtím)
# def test_connection(host: str, port: int, slave: int) -> bool: ...


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

            # TODO: Test připojení (pokud je potřeba)

            # Uložíme data z úvodního kroku; scan intervaly se nastaví v Options
            return self.async_create_entry(title=f"Sunway FVE ({user_input[CONF_HOST]})", data=user_input, options={})
            # Prázdný slovník options zajistí, že se spustí Options Flow pro nastavení intervalů

        return self.async_show_form(
            step_id="user", data_schema=DATA_SCHEMA, errors=errors
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: config_entries.ConfigEntry) -> config_entries.OptionsFlow:
        """Vytvoří options flow handler."""
        return SunwayFveOptionsFlowHandler(config_entry)


class SunwayFveOptionsFlowHandler(config_entries.OptionsFlow):
    """Zpracovává options flow pro Sunway FVE - nyní pro intervaly skupin."""

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
            # Kombinujeme nové options s původními daty (host, port, slave),
            # i když pro běh Hubu je budeme číst hlavně z options.
            # Lepší je mít vše v options. Zkopírujeme data a přidáme nové options.
            new_options = self.config_entry.options.copy()
            new_options.update(user_input)
            return self.async_create_entry(title="", data=new_options) # Uložíme nové options

        # Vytvoříme schéma s aktuálními/výchozími hodnotami intervalů
        options_schema_with_defaults = vol.Schema({
             vol.Optional(
                 group,
                 default=self.config_entry.options.get(group, default_interval) # Vezme uloženou hodnotu nebo default
             ): vol.All(vol.Coerce(int), vol.Range(min=5 if group == SCAN_GROUP_REALTIME else (30 if group == SCAN_GROUP_DAILY_TOTALS else (60 if group == SCAN_GROUP_LIFETIME_TOTALS else 300)))) # Různé min pro různé skupiny
             for group, default_interval in { # Slovník skupin a jejich výchozích hodnot pro formulář
                 SCAN_GROUP_REALTIME: 30,
                 SCAN_GROUP_DAILY_TOTALS: 120,
                 SCAN_GROUP_LIFETIME_TOTALS: 600,
                 SCAN_GROUP_INFO: 3600,
             }.items()
        })

        return self.async_show_form(
            step_id="init", data_schema=options_schema_with_defaults, errors=errors
        )