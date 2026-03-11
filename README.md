# Dual Logic Thermostat — Home Assistant Custom Integration

A flexible thermostat with independent **heating** and **cooling** setpoints and tolerance-based hysteresis control.

---

## Installation

### Step 1 — Copy the integration
Copy `custom_components/dual_logic_thermostat/` into your HA config directory:
```
config/custom_components/dual_logic_thermostat/
```

### Step 2 — Restart Home Assistant

### Step 3 — Add the integration
**Settings → Devices & Services → Add Integration → search "Dual Logic Thermostat"**

---

## Configuration

| Field | Required | Description |
|-------|----------|-------------|
| **Name** | ✅ | Friendly name for the thermostat |
| **Temperature Sensor** | ✅ | Sensor entity reporting current temperature |
| **Heating Switch** | ⚠️ | Switch entity for heater (one of heater/cooler required) |
| **Cooling Switch** | ⚠️ | Switch entity for cooler (one of heater/cooler required) |
| **Heating Setpoint** | ✅ | Target temperature for heating (°C) |
| **Cooling Setpoint** | ✅ | Target temperature for cooling (°C) |
| **Cold Tolerance** | ✅ | Dead band around heating setpoint (default 0.5°C) |
| **Hot Tolerance** | ✅ | Dead band around cooling setpoint (default 0.5°C) |
| **Min/Max Temperature** | ✅ | Bounds for the UI slider |
| **Initial HVAC Mode** | ✅ | Mode on HA startup |

---

## How the hysteresis works

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
- Heater fires at 19.5°C, off at 20.5°C
- Cooler fires at 24.5°C, off at 23.5°C
- 20.5–24.5°C is the neutral zone — nothing runs

---

## Debug logging

```yaml
logger:
  logs:
    custom_components.dual_logic_thermostat: debug
```
