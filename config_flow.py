# custom_components/sunway_fve/config_flow.py
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_PORT, CONF_SCAN_INTERVAL, CONF_SLAVE
from .const import DOMAIN, DEFAULT_PORT, DEFAULT_SCAN_INTERVAL, DEFAULT_SLAVE_ID

class SunwayFveConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Sunway FVE Modbus."""

    VERSION = 1 # Verze schématu konfigurace

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        errors = {}
        if user_input is not None:
            # TODO: Přidat validaci připojení k Modbus zařízení
            # Můžete se pokusit přečíst např. Sériové číslo (registr 10000)
            # Pokud se nepodaří, zobrazit chybu pomocí errors["base"] = "cannot_connect"
            # Pokud se podaří:
            # Použijte unique_id, aby nešlo přidat stejné zařízení dvakrát
            await self.async_set_unique_id(f"{user_input[CONF_HOST]}-{user_input[CONF_SLAVE]}")
            self._abort_if_unique_id_configured()

            return self.async_create_entry(title=f"Sunway FVE ({user_input[CONF_HOST]})", data=user_input)

        # Schéma formuláře pro uživatele
        data_schema = vol.Schema({
            vol.Required(CONF_HOST): str,
            vol.Required(CONF_PORT, default=DEFAULT_PORT): int,
            vol.Required(CONF_SLAVE, default=DEFAULT_SLAVE_ID): int,
            vol.Optional(CONF_SCAN_INTERVAL, default=DEFAULT_SCAN_INTERVAL): int,
            # Můžete přidat volbu Modbus TCP / RTU over TCP / Serial
        })

        return self.async_show_form(
            step_id="user", data_schema=data_schema, errors=errors
        )

    # TODO: Přidat podporu pro async_step_modbus, pokud chcete využít standardní Modbus config flow