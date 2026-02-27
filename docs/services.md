# Actions

[← Back to README](../README.md)

All actions support optional `duration_minutes` parameter for custom durations.

If you have multiple pool_controller instances, use the new **target** schema:
- `target.entity_id` (climate entity of the pool)
- or `target.device_id` (device created by the integration)

## Pause Management

```yaml
# Start pause (default 60 minutes)
action: pool_controller.start_pause
data:
  target:
    entity_id: climate.my_pool  # recommended for multi-instance setups
  duration_minutes: 45  # optional

# Stop active pause
action: pool_controller.stop_pause
data:
  target:
    entity_id: climate.my_pool
```

**Use Case**: Pause pool when guests are sleeping or during maintenance

## Bathing Sessions

```yaml
# Start bathing session (default 60 minutes)
action: pool_controller.start_bathing
data:
  target:
    entity_id: climate.my_pool
  duration_minutes: 120  # optional - great for extended family gatherings!

# End bathing session
action: pool_controller.stop_bathing
data:
  target:
    entity_id: climate.my_pool
```

**Use Case**: Scheduled bath times via calendar or time automation

## Filter Cycles

```yaml
# Start filter cycle (default 30 minutes)
action: pool_controller.start_filter
data:
  target:
    entity_id: climate.my_pool
  duration_minutes: 60  # optional

# Stop filter cycle
action: pool_controller.stop_filter
data:
  target:
    entity_id: climate.my_pool
```

## Chlorine (Quick Chlorination)

```yaml
# Start quick chlorine (default 5 minutes)
action: pool_controller.start_chlorine
data:
  target:
    entity_id: climate.my_pool
  duration_minutes: 5  # optional

# Stop chlorine
action: pool_controller.stop_chlorine
data:
  target:
    entity_id: climate.my_pool
```

**Use Case**: Manual filter triggers or extended filtration on high-use days

## Maintenance mode

```yaml
# Enable maintenance (hard lockout)
action: pool_controller.start_maintenance
data:
  target:
    entity_id: climate.my_pool

# Disable maintenance
action: pool_controller.stop_maintenance
data:
  target:
    entity_id: climate.my_pool
```

## Away mode

```yaml
# Enable away mode (reduces activity, sets Away temperature)
action: pool_controller.start_away
data:
  target:
    entity_id: climate.my_pool

# Disable away mode
action: pool_controller.stop_away
data:
  target:
    entity_id: climate.my_pool
```

## Power-saving mode

```yaml
# Enable power-saving mode (PV-prioritized operation)
action: pool_controller.start_power_saving
data:
  target:
    entity_id: climate.my_pool

# Disable power-saving mode
action: pool_controller.stop_power_saving
data:
  target:
    entity_id: climate.my_pool
```

**Behavior**:
- Keeps frost protection and required safety behavior active.
- Prioritizes operation when PV power is sufficient.
- Automatic filter cycles can be deferred and are forced at the configured deadline hour.
- Availability is sensor-dependent; mode is hidden/disabled when required signals are missing.

## Alternative: target by device_id

```yaml
action: pool_controller.start_bathing
data:
  target:
    device_id: 1234567890abcdef
  duration_minutes: 90
```
```
