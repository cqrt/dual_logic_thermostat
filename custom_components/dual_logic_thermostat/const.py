"""Constants for the Smart Thermostat integration."""

DOMAIN = "dual_logic_thermostat"

CONF_HEATER = "heater"
CONF_COOLER = "cooler"
CONF_SENSOR = "sensor"
CONF_HOT_TOLERANCE = "hot_tolerance"
CONF_COLD_TOLERANCE = "cold_tolerance"
CONF_HEAT_SETPOINT = "heat_setpoint"
CONF_COOL_SETPOINT = "cool_setpoint"
CONF_MIN_TEMP = "min_temp"
CONF_MAX_TEMP = "max_temp"
CONF_INITIAL_HVAC_MODE = "initial_hvac_mode"
CONF_KEEP_ALIVE = "keep_alive"

DEFAULT_HOT_TOLERANCE = 0.5
DEFAULT_COLD_TOLERANCE = 0.5
DEFAULT_MIN_TEMP = 7.0
DEFAULT_MAX_TEMP = 35.0
DEFAULT_HEAT_SETPOINT = 20.0
DEFAULT_COOL_SETPOINT = 24.0
DEFAULT_NAME = "Smart Thermostat"
