# Maintenance & Recommendations

[← Back to README](../README.md)

This chapter explains the **maintenance recommendation sensors** produced by the integration and the (best-effort)
calculations behind them. The dashboard card
([pool_controller_dashboard_frontend](https://github.com/lweberru/pool_controller_dashboard_frontend)) renders these
recommendations in its **Maintenance** section.

Note: All recommendations are heuristics and depend on correct inputs (pool volume, sensor calibration). Use your own
judgement and chemical product instructions.

## Overview (recommendation sensors)

Typical recommendation sensors (entity IDs depend on your instance name):

- `sensor.<pool>_ph_plus_g` – grams of pH+ to add
- `sensor.<pool>_ph_minus_g` – grams of pH- to add
- `sensor.<pool>_chlor_spoons` – chlorine dosage in spoons (based on ORP mV)
- `sensor.<pool>_salt_add_g` – **grams of salt** to add (saltwater/mixed mode)
- `sensor.<pool>_tds_water_change_liters` – recommended water change volume in liters
- `sensor.<pool>_tds_water_change_percent` – recommended water change in percent

Related “context” sensors:

- `sensor.<pool>_sanitizer_mode` – `chlorine` | `saltwater` | `mixed`
- `sensor.<pool>_tds_val` – raw derived TDS (ppm)
- `sensor.<pool>_tds_effective` – effective TDS (ppm, salt baseline subtracted in saltwater/mixed)
- `sensor.<pool>_tds_status` – `optimal` | `good` | `high` | `critical` | `urgent`
- `binary_sensor.<pool>_tds_high` – water change needed (based on thresholds)

For the full entity list, see [docs/entities.md](entities.md).

## Inputs used for calculations

- Pool volume in liters: configured via `water_volume`.
- pH: `sensor` configured as `ph_sensor`.
- Chlorine/ORP in mV: `sensor` configured as `chlorine_sensor`.
- Conductivity in µS/cm: `sensor` configured as `tds_sensor` (conductivity).
- Salt concentration in g/L: `sensor` configured as `salt_sensor`.
- Target salt level in g/L: option `target_salt_g_l` (saltwater/mixed).

## pH recommendations

Target pH: **7.2**

Tolerance range (no dosing needed): **7.0 – 7.4**

Let $V_{m^3}$ be the pool volume in cubic meters ($V_{m^3} = V_L / 1000$).

- If $pH > 7.4$:

$$\text{pH- grams} = (pH - 7.2) \times 100 \times V_{m^3}$$

- If $pH < 7.0$:

$$\text{pH+ grams} = (7.2 - pH) \times 100 \times V_{m^3}$$

Otherwise, both recommendations are 0.

## Chlorine (ORP) recommendation

Target ORP: **700 mV**

Rule of thumb:

- Per **100 mV below 700**, add **0.25 spoons** for **1000 L**.

Let $V_L$ be the pool volume in liters.

1. Compute quarter-spoons:

$$q = \text{round}\left(\frac{700 - \text{ORP}_{mV}}{100}\right)$$

2. Convert to spoons and scale with volume:

$$\text{spoons} = \frac{q}{4} \times \left(\frac{V_L}{1000}\right)$$

If ORP is at/above 700 mV, recommendation is 0.

## Salt recommendation (saltwater / mixed)

Only relevant when `sanitizer_mode` is **saltwater** or **mixed**.

- Current salt concentration: `sensor.<pool>_salt_val` (g/L)
- Target salt concentration: `target_salt_g_l` (g/L)

Let $V_L$ be the pool volume in liters.

$$\text{missing}_{g/L} = \max(0, \text{target}_{g/L} - \text{salt}_{g/L})$$

$$\text{salt_add}_g = \text{round}(\text{missing}_{g/L} \times V_L)$$

The recommendation sensor `sensor.<pool>_salt_add_g` is 0 when OK / not applicable.

## TDS & water change recommendation

### Conductivity → TDS

TDS is derived from conductivity (µS/cm) using a standard factor:

$$\text{TDS}_{ppm} = \text{round}(\text{conductivity}_{\mu S/cm} \times 0.64)$$

### Effective TDS (saltwater/mixed)

In saltwater/mixed mode, conductivity/TDS is dominated by the intended salt level. The integration therefore computes an
**effective** TDS value by subtracting a baseline derived from the configured target salt level:

$$\text{salt_baseline}_{ppm} = \text{target_salt}_{g/L} \times 1000$$

$$\text{TDS}_{effective} = \max(0, \text{TDS}_{val} - \text{salt_baseline}_{ppm})$$

All status/alerting and water-change recommendations use **effective TDS** when available (otherwise raw `tds_val`).

### Status thresholds

Based on the maintenance TDS value:

- `< 1500` → `optimal`
- `< 2000` → `good`
- `< 2500` → `high` (sets `binary_sensor.<pool>_tds_high`)
- `< 3000` → `critical` (sets `binary_sensor.<pool>_tds_high`)
- `≥ 3000` → `urgent` (sets `binary_sensor.<pool>_tds_high`)

### Recommended water change

Target maintenance TDS: **1200 ppm**

Let $V_L$ be the pool volume in liters and $T$ the maintenance TDS value (effective when available).

If $T > 1200$:

$$\text{water_change}_L = \text{round}\left(V_L \times \frac{T - 1200}{T}\right)$$

$$\text{water_change}_\% = \text{round}\left(\frac{\text{water_change}_L}{V_L} \times 100\right)$$

Otherwise both recommendations are 0.
