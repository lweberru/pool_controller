# Services (Automations & Advanced)

[← Back to README](../README.md)

All services support optional `duration_minutes` parameter for custom durations.

If you have multiple pool_controller instances, you should target the correct instance using one of:
- `config_entry_id` (most explicit)
- `climate_entity` (or alias `controller_entity`) of that instance

## Pause Management

```yaml
# Start pause (default 60 minutes)
service: pool_controller.start_pause
data:
  climate_entity: climate.my_pool  # recommended for multi-instance setups
  duration_minutes: 45  # optional

# Stop active pause
service: pool_controller.stop_pause
data:
  climate_entity: climate.my_pool
```

**Use Case**: Pause pool when guests are sleeping or during maintenance

## Bathing Sessions

```yaml
# Start bathing session (default 60 minutes)
service: pool_controller.start_bathing
data:
  climate_entity: climate.my_pool
  duration_minutes: 120  # optional - great for extended family gatherings!

# End bathing session
service: pool_controller.stop_bathing
data:
  climate_entity: climate.my_pool
```

**Use Case**: Scheduled bath times via calendar or time automation

## Filter Cycles

```yaml
# Start filter cycle (default 30 minutes)
service: pool_controller.start_filter
data:
  climate_entity: climate.my_pool
  duration_minutes: 60  # optional

# Stop filter cycle
service: pool_controller.stop_filter
data:
  climate_entity: climate.my_pool
```

## Chlorine (Quick Chlorination)

```yaml
# Start quick chlorine (default 5 minutes)
service: pool_controller.start_chlorine
data:
  climate_entity: climate.my_pool
  duration_minutes: 5  # optional

# Stop chlorine
service: pool_controller.stop_chlorine
data:
  climate_entity: climate.my_pool
```

**Use Case**: Manual filter triggers or extended filtration on high-use days

## Maintenance mode

```yaml
# Enable maintenance (hard lockout)
service: pool_controller.start_maintenance
data:
  climate_entity: climate.my_pool

# Disable maintenance
service: pool_controller.stop_maintenance
data:
  climate_entity: climate.my_pool
```
