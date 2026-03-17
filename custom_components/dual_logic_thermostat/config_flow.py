"""Config flow for Smart Thermostat integration."""
from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.components.climate import HVACMode
from homeassistant.const import CONF_NAME
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import selector

from .const import (
    CONF_COLD_TOLERANCE,
    CONF_COOL_SETPOINT,
    CONF_COOLER,
    CONF_HEAT_SETPOINT,
    CONF_HEATER,
    CONF_HOT_TOLERANCE,
    CONF_INITIAL_HVAC_MODE,
    CONF_MAX_TEMP,
    CONF_MIN_CYCLE_DURATION,
    CONF_MIN_TEMP,
    CONF_SENSOR,
    DEFAULT_COLD_TOLERANCE,
    DEFAULT_COOL_SETPOINT,
    DEFAULT_HEAT_SETPOINT,
    DEFAULT_HOT_TOLERANCE,
    DEFAULT_MAX_TEMP,
    DEFAULT_MIN_TEMP,
    DEFAULT_NAME,
    DOMAIN,
)


def _get_schema(defaults: dict) -> vol.Schema:
    return vol.Schema(
        {
            vol.Required(CONF_NAME, default=defaults.get(CONF_NAME, DEFAULT_NAME)): selector.TextSelector(),
            vol.Required(CONF_SENSOR, default=defaults.get(CONF_SENSOR, "")): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="sensor")
            ),
            vol.Optional(
                CONF_HEATER,
                default=defaults.get(CONF_HEATER, ""),
            ): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="switch")
            ),
            vol.Optional(
                CONF_COOLER,
                default=defaults.get(CONF_COOLER, ""),
            ): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="switch")
            ),
            vol.Optional(
                CONF_HEAT_SETPOINT,
                default=defaults.get(CONF_HEAT_SETPOINT, DEFAULT_HEAT_SETPOINT),
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(min=5, max=40, step=0.1, mode="box")
            ),
            vol.Optional(
                CONF_COOL_SETPOINT,
                default=defaults.get(CONF_COOL_SETPOINT, DEFAULT_COOL_SETPOINT),
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(min=5, max=40, step=0.1, mode="box")
            ),
            vol.Optional(
                CONF_HOT_TOLERANCE,
                default=defaults.get(CONF_HOT_TOLERANCE, DEFAULT_HOT_TOLERANCE),
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(min=0, max=5, step=0.1, mode="box")
            ),
            vol.Optional(
                CONF_COLD_TOLERANCE,
                default=defaults.get(CONF_COLD_TOLERANCE, DEFAULT_COLD_TOLERANCE),
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(min=0, max=5, step=0.1, mode="box")
            ),
            vol.Optional(
                CONF_MIN_TEMP,
                default=defaults.get(CONF_MIN_TEMP, DEFAULT_MIN_TEMP),
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(min=0, max=20, step=0.5, mode="box")
            ),
            vol.Optional(
                CONF_MAX_TEMP,
                default=defaults.get(CONF_MAX_TEMP, DEFAULT_MAX_TEMP),
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(min=20, max=50, step=0.5, mode="box")
            ),
            vol.Optional(
                CONF_INITIAL_HVAC_MODE,
                default=defaults.get(CONF_INITIAL_HVAC_MODE, HVACMode.OFF),
            ): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=[
                        HVACMode.OFF,
                        HVACMode.HEAT,
                        HVACMode.COOL,
                        HVACMode.HEAT_COOL,
                    ]
                )
            ),
            vol.Optional(
                CONF_MIN_CYCLE_DURATION,
                default=defaults.get(CONF_MIN_CYCLE_DURATION, 0),
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(min=0, max=600, step=5, mode="box", unit_of_measurement="s")
            ),
        }
    )


def _validate_config(data: dict) -> dict:
    """Validate that at least one of heater or cooler is set."""
    errors = {}
    if not data.get(CONF_HEATER) and not data.get(CONF_COOLER):
        errors["base"] = "no_switch_configured"
    heat_sp = data.get(CONF_HEAT_SETPOINT, DEFAULT_HEAT_SETPOINT)
    cool_sp = data.get(CONF_COOL_SETPOINT, DEFAULT_COOL_SETPOINT)
    if heat_sp >= cool_sp:
        errors["base"] = "setpoints_overlap"
    return errors


class DualLogicThermostatConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Smart Thermostat."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.FlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            errors = _validate_config(user_input)
            if not errors:
                return self.async_create_entry(
                    title=user_input[CONF_NAME], data=user_input
                )

        return self.async_show_form(
            step_id="user",
            data_schema=_get_schema(user_input or {}),
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> DualLogicThermostatOptionsFlow:
        """Get the options flow for this handler."""
        return DualLogicThermostatOptionsFlow()


class DualLogicThermostatOptionsFlow(config_entries.OptionsFlow):
    """Handle options flow for Dual Logic Thermostat."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.FlowResult:
        """Manage the options."""
        errors: dict[str, str] = {}

        if user_input is not None:
            errors = _validate_config(user_input)
            if not errors:
                return self.async_create_entry(title="", data=user_input)

        current = {**self.config_entry.data, **self.config_entry.options}

        return self.async_show_form(
            step_id="init",
            data_schema=_get_schema(current),
            errors=errors,
        )
