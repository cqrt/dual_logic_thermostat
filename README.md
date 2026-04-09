# Dual Logic Thermostat

A Home Assistant custom thermostat integration with independent heating and cooling setpoints, tolerance-based hysteresis control, and full compatibility with Google Home and other external services.

[![HACS](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/hacs/integration)
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

### Option 1 (Manual)
1. Copy `custom_components/dual_logic_thermostat/` into your HA config directory:
```
config/custom_components/dual_logic_thermostat/
```
2. Restart Home Assistant
3. Go to **Settings → Devices & Services → Add Integration → search "Dual Logic Thermostat"**

### Option 2 (HACS Custom Repository - One-Click)
1. One-click button below to add custom repository


[![Install Dual Logic Thermostat as a custom repository](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=cqrt&repository=dual_logic_thermostat&category=integration)

2. Go to **Settings → Devices & Services → Add Integration → search "Dual Logic Thermostat"**

### Option 3 (HACS Custom Repository - Manual)
If for some reason the one-click does not work for you, you can add it manually as a custom repository:

1. Open HACS
2. Open the 3 dot menu in upper right.
3. Click **Custom Repositories**
4. Enter the repository URL
   ```
   https://github.com/cqrt/dual_logic_thermostat
   ```
5. Select **Integration** as the type
6. Click **ADD**
7. Go to **Settings → Devices & Services → Add Integration → search "Dual Logic Thermostat"**

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
| **Cold Tolerance** | ✅ | Dead band below heating setpoint (default 0.3°C) |
| **Hot Tolerance** | ✅ | Dead band above cooling setpoint (default 0.3°C) |
| **Min Temperature** | ✅ | Minimum selectable temperature (default 7°C) |
| **Max Temperature** | ✅ | Maximum selectable temperature (default 38°C) |
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

Example with `heat_setpoint=22`, `cool_setpoint=24`, `tolerance=0.3`:
- Heater fires at 21.7°C, shuts off at 22.3°C
- Cooler fires at 24.3°C, shuts off at 23.7°C
- 22.3–23.7°C is the neutral zone — nothing runs

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

## Debug logging

```yaml
logger:
  logs:
    custom_components.dual_logic_thermostat: debug
```

