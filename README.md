# Dual Logic Thermostat

A Home Assistant custom thermostat integration with independent heating and cooling setpoints, tolerance-based hysteresis control, and full compatibility with Google Home and other external services.

[![HACS](https://img.shields.io/badge/HACS-Pending-yellow.svg)](https://github.com/hacs/default)
[![GitHub Release](https://img.shields.io/github/release/cqrt/dual_logic_thermostat.svg)](https://github.com/cqrt/dual_logic_thermostat/releases)

---

## Features

- Independent heating and cooling setpoints
- Tolerance-based hysteresis dead band for each switch — prevents rapid toggling
- Supports `heat`, `cool`, `heat_cool`, and `off` HVAC modes
- Dynamic UI — single setpoint shown in `heat`/`cool` mode, dual setpoints in `heat_cool` mode
- Minimum cycle duration to protect physical HVAC equipment from rapid switching
- Restores previous HVAC mode on turn on (e.g. via Google Home)
- Full Google Home compatibility — including turn on/off commands
- State persistence across HA restarts
- Fully configurable via the HA UI — no YAML required
- Reconfigurable at any time via Settings → Devices & Services

---

## Installation

### Manual
1. Copy `custom_components/dual_logic_thermostat/` into your HA config directory:
```
config/custom_components/dual_logic_thermostat/
```
2. Restart Home Assistant
3. Go to **Settings → Devices & Services → Add Integration → search "Dual Logic Thermostat"**

### HACS
Once listed, search for **Dual Logic Thermostat** in the HACS integration store and install from there.

---

## Configuration

| Field | Required | Description |
|-------|----------|-------------|
| **Name** | ✅ | Friendly name for the thermostat entity |
| **Temperature Sensor** | ✅ | Sensor entity reporting current temperature |
| **Heating Switch** | ⚠️ | Switch entity for heater (at least one of heater/cooler required) |
| **Cooling Switch** | ⚠️ | Switch entity for cooler (at least one of heater/cooler required) |
| **Heating Setpoint** | ✅ | Target temperature for heating in °C (step 0.1) |
| **Cooling Setpoint** | ✅ | Target temperature for cooling in °C (step 0.1) |
| **Cold Tolerance** | ✅ | Dead band below heating setpoint (default 0.5°C) |
| **Hot Tolerance** | ✅ | Dead band above cooling setpoint (default 0.5°C) |
| **Min Temperature** | ✅ | Minimum selectable temperature (default 7°C) |
| **Max Temperature** | ✅ | Maximum selectable temperature (default 35°C) |
| **Initial HVAC Mode** | ✅ | HVAC mode on HA startup |
| **Minimum Cycle Duration** | ✅ | Minimum seconds a switch must stay on or off before changing state. Set to 0 to disable (default) |

---

## How the hysteresis works

Each switch has its own independent dead band, preventing rapid toggling when temperature hovers near a setpoint.

**Heating** (around `heat_setpoint` ± `cold_tolerance`):
```
Heater ON  when temp ≤ heat_setpoint - cold_tolerance
Heater OFF when temp ≥ heat_setpoint + cold_tolerance
```

**Cooling** (around `cool_setpoint` ± `hot_tolerance`):
```
Cooler ON  when temp ≥ cool_setpoint + hot_tolerance
Cooler OFF when temp ≤ cool_setpoint - hot_tolerance
```

Example with `heat_setpoint=20`, `cool_setpoint=24`, `tolerance=0.5`:
- Heater fires at 19.5°C, shuts off at 20.5°C
- Cooler fires at 24.5°C, shuts off at 23.5°C
- 20.5–24.5°C is the neutral zone — nothing runs

---

## HVAC Modes

| Mode | Behaviour |
|------|-----------|
| `off` | Both switches off |
| `heat` | Only heater operates, single setpoint shown in UI |
| `cool` | Only cooler operates, single setpoint shown in UI |
| `heat_cool` | Both can operate independently, dual setpoints shown in UI |

`heat_cool` is only available when both a heater and cooler switch are configured. Heating and cooling never run simultaneously.

---

## Minimum Cycle Duration

When set, each switch must remain in its current state for at least this many seconds before it can be toggled. The heater and cooler track their timers independently. This protects compressors and relay hardware from rapid cycling. A typical value for an AC unit is 180–300 seconds.

---

## Last Mode Restoration

When the thermostat receives a generic "turn on" command (e.g. from Google Home or an automation), it restores the last active HVAC mode rather than defaulting to a fixed mode. This persists across HA restarts.

---

## Google Home Compatibility

The integration is fully compatible with Google Home:
- Set the thermostat to `heat`, `cool`, or `heat_cool` mode
- Turn the thermostat off
- Turn the thermostat on — restores the last active mode

---

## Debug logging

```yaml
logger:
  logs:
    custom_components.dual_logic_thermostat: debug
```

