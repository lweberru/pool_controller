# Costs & Electricity Prices

This section explains how the integration calculates costs, which sensors are relevant, and what matters with dynamic electricity prices.

The goal of this part of the integration is to make the pool’s (sometimes significant) electricity costs visible and to quantify the impact of a PV system and PV‑aligned pool operation. The credit system contributes to cost reduction by merging and shifting runs, while scheduled bathing with preheat still ensures the desired target temperature is reached on time.

## Cost Tip: Use Power-Saving Mode for Lowest Running Cost

If your priority is **minimum operating cost**, prefer the **power-saving mode** (`Stromsparen`) for daily operation.

Why it is usually the cheapest mode:
- It prioritizes runtime when PV is available.
- It defers automatic filter runs while PV is insufficient.
- Deferred filter runs are only forced at/after the configured deadline hour (`power_saving_filter_deadline_hour`), reducing expensive grid-powered runtime during high-price windows.

Practical recommendation:
- Use **Auto mode** when comfort and strict timing are more important.
- Use **Power-saving mode** when cost minimization and PV self-consumption are more important.

Important trade-offs in power-saving mode:
- Automatic runs can be stretched or shifted, so total active runtime can increase (longer pump noise windows).
- In some installations, pump-first heat-up can be less efficient than earlier/stronger auxiliary-heater usage.

Quick estimation workflow (recommended):
- Measure 3-7 comparable days in **Auto** and in **Power-saving**.
- Record for each mode: daily pool energy (`kWh`), daily runtime (`minutes`), and approximate PV share of pool consumption (`0..1`).
- Compute approximate net daily cost per mode with:

```text
cost_net ≈ E × (p_grid - PV_share × (p_grid - p_feed))
```

Where:
- `E` = daily pool energy (`kWh/day`)
- `p_grid` = average grid price (`€/kWh`)
- `p_feed` = feed-in tariff (`€/kWh`)

Then compare:

```text
savings_day ≈ cost_net_auto - cost_net_ps
runtime_increase_% ≈ (runtime_ps - runtime_auto) / runtime_auto × 100
```

Rule of thumb:
- Keep Power-saving as default if `savings_day` is positive and runtime increase/noise is acceptable.
- Switch to Auto during periods where comfort timing or faster heat-up is more important.

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

`pv_surplus_sensor` is interpreted as current PV production power (W).
If `pv_house_load_sensor` is also set, the integration computes available PV surplus internally as
`production - (house_load - pool_load)`.

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
