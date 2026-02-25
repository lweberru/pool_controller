# Costs & Electricity Prices

This section explains how the integration calculates costs, which sensors are relevant, and what matters with dynamic electricity prices.

The goal of this part of the integration is to make the pool’s (sometimes significant) electricity costs visible and to quantify the impact of a PV system and PV‑aligned pool operation. The credit system contributes to cost reduction by merging and shifting runs, while scheduled bathing with preheat still ensures the desired target temperature is reached on time.

## Basics

Costs are based on **energy (kWh)** × **electricity price (€/kWh)**. The price can be **fixed** or **dynamic**:

- **Fixed price**: value from the configuration.
- **Dynamic price**: an entity in the configuration (e.g., hourly changing price).

The integration calculates costs **time‑weighted per day** and derives monthly and yearly values. This is required so dynamic prices are applied correctly.

## Which energy sensors are used

For cost calculation, the integration prefers daily kWh sensors (if configured). If no daily sensors are available, it derives a **daily delta** from **total counters**.

**Configuration (config flow):**
- `pool_energy_entity_base` (total kWh counter)
- `pool_energy_entity_aux` (total kWh counter)
- `pool_energy_entity_base_daily` (optional, daily kWh)
- `pool_energy_entity_aux_daily` (optional, daily kWh)
- `solar_energy_entity_daily` (optional, daily solar kWh for net calculation)
- `pv_surplus_sensor` (PV power input in W)
- `pv_house_load_sensor` (optional house load in W; enables internal surplus calculation without templates)

## Sensors and meaning

**Daily / Monthly / Yearly (relevant):**
- `sensor.<pool>_energy_cost_daily`
- `sensor.<pool>_energy_cost_monthly`
- `sensor.<pool>_energy_cost_yearly`
- `sensor.<pool>_energy_cost_net_daily`
- `sensor.<pool>_energy_cost_net_monthly`
- `sensor.<pool>_energy_cost_net_yearly`

**Feed‑in loss (lost export revenue):**
- `sensor.<pool>_energy_feed_in_loss_daily`
- `sensor.<pool>_energy_feed_in_loss_monthly`
- `sensor.<pool>_energy_feed_in_loss_yearly`

**Instant values (for reference):**
- `sensor.<pool>_power_cost_per_hour` (gross, no PV credit)
- `sensor.<pool>_power_cost_per_hour_net` (net, PV deducted)

## Net vs. Gross

- **Gross cost**: grid energy × price (no PV credit applied).
- **Net cost**: gross minus PV share (if `solar_energy_entity_daily` is configured).

If `pv_house_load_sensor` is set, `pv_surplus_sensor` is interpreted as PV production power and the integration computes
available PV surplus internally as `production - (house_load - pool_load)`.

**Fallbacks:**
- If `solar_energy_entity_daily` is not configured, net daily cost uses a time-weighted PV credit derived from instantaneous overlap between
	pool power and PV surplus (`pv_surplus_sensor`).
- If only total load sensors exist (no daily load sensors), the integration still derives a daily delta from total counters.

This keeps `net` and `gross` separated in typical PV operation even without a dedicated daily pool-solar kWh sensor.

## Why there are no “period” costs

Period sensors (total cost since an unknown start date) are not meaningful with **dynamic prices**, because the price varies over time. Therefore these sensors were removed.

## Tips for clean values

- Use **utility meters** or real **daily kWh sensors** if possible.
- If only total counters are available, the integration derives daily costs via deltas.
- Ensure all energy sensors are **monotonic** and **never reset** unexpectedly.

## Further reading

- Full entity list: [docs/entities.md](entities.md)
