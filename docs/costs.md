# Costs & Electricity Prices

This section explains how the integration calculates costs, which sensors are relevant, and what matters with dynamic electricity prices.

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
- `sensor.<pool>_power_cost_per_hour` (gross)
- `sensor.<pool>_power_cost_per_hour_net` (net, PV accounted for)

## Net vs. Gross

- **Gross cost**: grid energy × price.
- **Net cost**: gross minus PV share (if `solar_energy_entity_daily` is configured).

**Fallback:** If no daily load sensors exist, the PV share is approximated as
`solar_energy_entity_daily × current price` and subtracted from the gross daily cost. This is an approximation but provides immediate net differences.

## Why there are no “period” costs

Period sensors (total cost since an unknown start date) are not meaningful with **dynamic prices**, because the price varies over time. Therefore these sensors were removed.

## Tips for clean values

- Use **utility meters** or real **daily kWh sensors** if possible.
- If only total counters are available, the integration derives daily costs via deltas.
- Ensure all energy sensors are **monotonic** and **never reset** unexpectedly.

## Further reading

- Full entity list: [docs/entities.md](entities.md)
