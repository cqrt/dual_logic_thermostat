"""Smart Thermostat climate platform."""
from __future__ import annotations

import asyncio
import logging
from datetime import timedelta
from typing import Any

from homeassistant.components.climate import (
    ClimateEntity,
    ClimateEntityFeature,
    HVACAction,
    HVACMode,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    ATTR_ENTITY_ID,
    ATTR_TEMPERATURE,
    CONF_NAME,
    SERVICE_TURN_OFF,
    SERVICE_TURN_ON,
    STATE_ON,
    STATE_UNAVAILABLE,
    STATE_UNKNOWN,
    UnitOfTemperature,
)
from homeassistant.components.climate import ATTR_TARGET_TEMP_HIGH, ATTR_TARGET_TEMP_LOW
from homeassistant.core import Event, HomeAssistant, State, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import (
    async_track_state_change_event,
    async_track_time_interval,
)
from homeassistant.helpers.restore_state import RestoreEntity

from .const import (
    CONF_COLD_TOLERANCE,
    CONF_COOL_SETPOINT,
    CONF_COOLER,
    CONF_HEAT_SETPOINT,
    CONF_HEATER,
    CONF_HOT_TOLERANCE,
    CONF_INITIAL_HVAC_MODE,
    CONF_KEEP_ALIVE,
    CONF_MAX_TEMP,
    CONF_MIN_TEMP,
    CONF_SENSOR,
    DEFAULT_COLD_TOLERANCE,
    DEFAULT_COOL_SETPOINT,
    DEFAULT_HEAT_SETPOINT,
    DEFAULT_HOT_TOLERANCE,
    DEFAULT_MAX_TEMP,
    DEFAULT_MIN_TEMP,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Smart Thermostat climate platform."""
    config = {**config_entry.data, **config_entry.options}

    async_add_entities(
        [
            SmartThermostat(
                name=config[CONF_NAME],
                unique_id=config_entry.entry_id,
                sensor_entity_id=config[CONF_SENSOR],
                heater_entity_id=config.get(CONF_HEATER),
                cooler_entity_id=config.get(CONF_COOLER),
                hot_tolerance=config.get(CONF_HOT_TOLERANCE, DEFAULT_HOT_TOLERANCE),
                cold_tolerance=config.get(CONF_COLD_TOLERANCE, DEFAULT_COLD_TOLERANCE),
                heat_setpoint=config.get(CONF_HEAT_SETPOINT, DEFAULT_HEAT_SETPOINT),
                cool_setpoint=config.get(CONF_COOL_SETPOINT, DEFAULT_COOL_SETPOINT),
                min_temp=config.get(CONF_MIN_TEMP, DEFAULT_MIN_TEMP),
                max_temp=config.get(CONF_MAX_TEMP, DEFAULT_MAX_TEMP),
                initial_hvac_mode=config.get(CONF_INITIAL_HVAC_MODE),
                keep_alive=config.get(CONF_KEEP_ALIVE),
            )
        ]
    )


class SmartThermostat(ClimateEntity, RestoreEntity):
    """Smart Thermostat with independent heating and cooling setpoints."""

    _attr_should_poll = False
    _enable_turn_on_off_backwards_compat = False

    def __init__(
        self,
        name: str,
        unique_id: str,
        sensor_entity_id: str,
        heater_entity_id: str | None,
        cooler_entity_id: str | None,
        hot_tolerance: float,
        cold_tolerance: float,
        heat_setpoint: float,
        cool_setpoint: float,
        min_temp: float,
        max_temp: float,
        initial_hvac_mode: str | None,
        keep_alive: timedelta | None,
    ) -> None:
        """Initialize the thermostat."""
        self._attr_name = name
        self._attr_unique_id = unique_id
        self._attr_icon = "mdi:thermostat-auto"
        self._sensor_entity_id = sensor_entity_id
        self._heater_entity_id = heater_entity_id
        self._cooler_entity_id = cooler_entity_id
        self._hot_tolerance = hot_tolerance
        self._cold_tolerance = cold_tolerance
        self._attr_min_temp = min_temp
        self._attr_max_temp = max_temp
        self._keep_alive = keep_alive
        self._cur_temp: float | None = None
        self._active = False
        self._last_hvac_mode: HVACMode | None = None
        self._temp_lock = asyncio.Lock()
        self._attr_temperature_unit = UnitOfTemperature.CELSIUS
        self._attr_target_temperature_step = 0.1

        # Dual setpoints: low = heat target, high = cool target
        self._attr_target_temperature_low = float(heat_setpoint)
        self._attr_target_temperature_high = float(cool_setpoint)

        # Build supported HVAC modes
        self._hvac_modes: list[HVACMode] = [HVACMode.OFF]
        if heater_entity_id:
            self._hvac_modes.append(HVACMode.HEAT)
        if cooler_entity_id:
            self._hvac_modes.append(HVACMode.COOL)
        if heater_entity_id and cooler_entity_id:
            self._hvac_modes.append(HVACMode.HEAT_COOL)

        # Base features — mode-specific features handled via property
        self._base_features = (
            ClimateEntityFeature.TURN_ON
            | ClimateEntityFeature.TURN_OFF
        )

        if initial_hvac_mode and initial_hvac_mode in self._hvac_modes:
            self._attr_hvac_mode = HVACMode(initial_hvac_mode)
        else:
            self._attr_hvac_mode = HVACMode.OFF

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def hvac_modes(self) -> list[HVACMode]:
        return self._hvac_modes

    @property
    def supported_features(self) -> ClimateEntityFeature:
        """Return supported features based on current HVAC mode."""
        if self._attr_hvac_mode == HVACMode.HEAT_COOL:
            return self._base_features | ClimateEntityFeature.TARGET_TEMPERATURE_RANGE
        return self._base_features | ClimateEntityFeature.TARGET_TEMPERATURE

    @property
    def target_temperature(self) -> float | None:
        """Return the single target temperature for heat or cool mode."""
        if self._attr_hvac_mode == HVACMode.HEAT:
            return self._attr_target_temperature_low
        if self._attr_hvac_mode == HVACMode.COOL:
            return self._attr_target_temperature_high
        return None

    @property
    def current_temperature(self) -> float | None:
        return self._cur_temp

    @property
    def available(self) -> bool:
        sensor_state = self.hass.states.get(self._sensor_entity_id)
        return sensor_state is not None and sensor_state.state not in (
            STATE_UNAVAILABLE,
            STATE_UNKNOWN,
        )

    @property
    def hvac_action(self) -> HVACAction:
        if self._attr_hvac_mode == HVACMode.OFF:
            return HVACAction.OFF
        if self._heater_entity_id and self._is_switch_on(self._heater_entity_id):
            return HVACAction.HEATING
        if self._cooler_entity_id and self._is_switch_on(self._cooler_entity_id):
            return HVACAction.COOLING
        return HVACAction.IDLE

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        attrs = {
            "heater_entity": self._heater_entity_id,
            "cooler_entity": self._cooler_entity_id,
            "sensor_entity": self._sensor_entity_id,
            "cold_tolerance": self._cold_tolerance,
            "hot_tolerance": self._hot_tolerance,
        }
        if self._last_hvac_mode is not None:
            attrs["last_hvac_mode"] = self._last_hvac_mode.value
        return attrs

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _is_switch_on(self, entity_id: str) -> bool:
        state = self.hass.states.get(entity_id)
        return state is not None and state.state == STATE_ON

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()

        # Restore previous state
        if (last_state := await self.async_get_last_state()) is not None:
            if last_state.state in [m.value for m in HVACMode]:
                restored_mode = HVACMode(last_state.state)
                if restored_mode in self._hvac_modes:
                    self._attr_hvac_mode = restored_mode
            attrs = last_state.attributes
            if (low := attrs.get("target_temp_low")) is not None:
                self._attr_target_temperature_low = float(low)
            if (high := attrs.get("target_temp_high")) is not None:
                self._attr_target_temperature_high = float(high)
            if (last := attrs.get("last_hvac_mode")) is not None:
                try:
                    restored = HVACMode(last)
                    if restored in self._hvac_modes and restored != HVACMode.OFF:
                        self._last_hvac_mode = restored
                except ValueError:
                    pass

        # Track sensor
        self.async_on_remove(
            async_track_state_change_event(
                self.hass, [self._sensor_entity_id], self._async_sensor_changed
            )
        )

        # Track switches for UI refresh
        switches = [e for e in [self._heater_entity_id, self._cooler_entity_id] if e]
        if switches:
            self.async_on_remove(
                async_track_state_change_event(
                    self.hass, switches, self._async_switch_changed
                )
            )

        # Keep-alive
        if self._keep_alive:
            self.async_on_remove(
                async_track_time_interval(
                    self.hass, self._async_control, self._keep_alive
                )
            )

        # Seed current temperature
        sensor_state = self.hass.states.get(self._sensor_entity_id)
        if sensor_state and sensor_state.state not in (STATE_UNAVAILABLE, STATE_UNKNOWN):
            try:
                self._cur_temp = float(sensor_state.state)
            except (ValueError, TypeError):
                pass

        await self._async_control()

    # ------------------------------------------------------------------
    # Event callbacks
    # ------------------------------------------------------------------

    @callback
    def _async_sensor_changed(self, event: Event) -> None:
        new_state: State | None = event.data.get("new_state")
        if new_state is None or new_state.state in (STATE_UNAVAILABLE, STATE_UNKNOWN):
            return
        try:
            self._cur_temp = float(new_state.state)
        except (ValueError, TypeError):
            return
        self.async_write_ha_state()
        self.hass.async_create_task(self._async_control())

    @callback
    def _async_switch_changed(self, event: Event) -> None:
        self.async_write_ha_state()

    # ------------------------------------------------------------------
    # Service calls
    # ------------------------------------------------------------------

    async def async_turn_on(self) -> None:
        # Restore the last active mode if we have one
        if self._last_hvac_mode is not None:
            await self.async_set_hvac_mode(self._last_hvac_mode)
            return
        # No history — fall back to the best available mode
        if HVACMode.HEAT_COOL in self._hvac_modes:
            await self.async_set_hvac_mode(HVACMode.HEAT_COOL)
        elif HVACMode.HEAT in self._hvac_modes:
            await self.async_set_hvac_mode(HVACMode.HEAT)
        else:
            await self.async_set_hvac_mode(HVACMode.COOL)

    async def async_turn_off(self) -> None:
        await self.async_set_hvac_mode(HVACMode.OFF)

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        if hvac_mode not in self._hvac_modes:
            _LOGGER.warning("Unsupported HVAC mode: %s", hvac_mode)
            return
        # Remember the last active mode before turning off
        if hvac_mode == HVACMode.OFF and self._attr_hvac_mode != HVACMode.OFF:
            self._last_hvac_mode = self._attr_hvac_mode
        self._attr_hvac_mode = hvac_mode
        await self._async_control()
        self.async_write_ha_state()

    async def async_set_temperature(self, **kwargs: Any) -> None:
        """Set new heat and/or cool setpoints."""
        if (low := kwargs.get(ATTR_TARGET_TEMP_LOW)) is not None:
            self._attr_target_temperature_low = float(low)
        if (high := kwargs.get(ATTR_TARGET_TEMP_HIGH)) is not None:
            self._attr_target_temperature_high = float(high)
        # Single setpoint — route to the correct setpoint based on mode
        if (temp := kwargs.get(ATTR_TEMPERATURE)) is not None:
            if self._attr_hvac_mode == HVACMode.HEAT:
                self._attr_target_temperature_low = float(temp)
            elif self._attr_hvac_mode == HVACMode.COOL:
                self._attr_target_temperature_high = float(temp)
        await self._async_control()
        self.async_write_ha_state()

    # ------------------------------------------------------------------
    # Core control logic
    # ------------------------------------------------------------------

    async def _async_control(self, *_: Any) -> None:
        """Evaluate current temperature against setpoints and toggle switches."""
        async with self._temp_lock:
            cur = self._cur_temp
            mode = self._attr_hvac_mode
            heat_sp = self._attr_target_temperature_low
            cool_sp = self._attr_target_temperature_high

            if mode == HVACMode.OFF or cur is None:
                await self._turn_off_all()
                return

            self._active = True

            if mode in (HVACMode.HEAT, HVACMode.HEAT_COOL):
                await self._control_heater(cur, heat_sp)
            else:
                await self._heater_off()

            if mode in (HVACMode.COOL, HVACMode.HEAT_COOL):
                await self._control_cooler(cur, cool_sp)
            else:
                await self._cooler_off()

    async def _control_heater(self, cur: float, setpoint: float) -> None:
        """
        Heating hysteresis:
          ON  when temp falls below  setpoint - cold_tolerance
          OFF when temp rises above  setpoint + cold_tolerance
        """
        is_on = self._heater_entity_id and self._is_switch_on(self._heater_entity_id)

        if cur <= setpoint - self._cold_tolerance:
            await self._heater_on()
        elif cur >= setpoint + self._cold_tolerance:
            await self._heater_off()
        # Between the two thresholds: keep current state (no-op)

    async def _control_cooler(self, cur: float, setpoint: float) -> None:
        """
        Cooling hysteresis:
          ON  when temp rises above  setpoint + hot_tolerance
          OFF when temp drops below  setpoint - hot_tolerance
        """
        if cur >= setpoint + self._hot_tolerance:
            await self._cooler_on()
        elif cur <= setpoint - self._hot_tolerance:
            await self._cooler_off()
        # Between the two thresholds: keep current state (no-op)

    # ------------------------------------------------------------------
    # Switch helpers
    # ------------------------------------------------------------------

    async def _turn_off_all(self) -> None:
        await self._heater_off()
        await self._cooler_off()

    async def _heater_on(self) -> None:
        if self._heater_entity_id and not self._is_switch_on(self._heater_entity_id):
            _LOGGER.debug("Turning on heater: %s", self._heater_entity_id)
            await self._call_switch(SERVICE_TURN_ON, self._heater_entity_id)

    async def _heater_off(self) -> None:
        if self._heater_entity_id and self._is_switch_on(self._heater_entity_id):
            _LOGGER.debug("Turning off heater: %s", self._heater_entity_id)
            await self._call_switch(SERVICE_TURN_OFF, self._heater_entity_id)

    async def _cooler_on(self) -> None:
        if self._cooler_entity_id and not self._is_switch_on(self._cooler_entity_id):
            _LOGGER.debug("Turning on cooler: %s", self._cooler_entity_id)
            await self._call_switch(SERVICE_TURN_ON, self._cooler_entity_id)

    async def _cooler_off(self) -> None:
        if self._cooler_entity_id and self._is_switch_on(self._cooler_entity_id):
            _LOGGER.debug("Turning off cooler: %s", self._cooler_entity_id)
            await self._call_switch(SERVICE_TURN_OFF, self._cooler_entity_id)

    async def _call_switch(self, service: str, entity_id: str) -> None:
        await self.hass.services.async_call(
            "homeassistant", service, {ATTR_ENTITY_ID: entity_id}
        )
