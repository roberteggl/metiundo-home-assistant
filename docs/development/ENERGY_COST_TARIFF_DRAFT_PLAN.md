# Energy Cost and Tariff Draft Plan

**Status:** Implemented. Tariffs are date-based and may change only on the first day of a month.

## Context

The integration already imports Metiundo cumulative grid energy readings as Home Assistant external statistics:

- `metiundo:<entry>_grid_import_energy`
- `metiundo:<entry>_grid_export_energy`

Home Assistant does not allow a fixed price entity or `number_energy_price` to be attached to an external energy statistic. For external energy statistics, the Energy Dashboard expects a separate external monetary cost statistic and uses it as `stat_cost`.

## Goal

Create a cost statistic for grid import so the Energy Dashboard can show the actual electricity cost based on:

- Working charge (Arbeitspreis), the variable price per kWh
- Standing charge (Grundpreis), the fixed monthly charge
- Tariffs that change on a defined effective date

The MVP scope is import costs. Export compensation can be added separately later.

## Proposed Home Assistant Statistic

Create an external statistic with an identifier similar to:

```text
metiundo:<entry_id>_grid_import_cost
```

The metadata should follow Home Assistant's external cost statistic pattern:

- `source`: `metiundo`
- `mean_type`: `StatisticMeanType.NONE`
- `has_sum`: `True`
- `unit_class`: `None`
- `unit_of_measurement`: `None`

Each hourly statistic should contain:

- `state`: cost incurred during that hour
- `sum`: cumulative cost for the statistic

The Energy Dashboard can then be configured with the Metiundo import energy statistic and this cost statistic under grid cost tracking.

## Tariff Configuration

Store an ordered tariff schedule in config-entry options. Each entry contains:

```text
effective_from
working_charge
standing_charge
```

`effective_from` should initially be interpreted as midnight in Home Assistant's configured local timezone. Reading timestamps must be converted consistently before selecting the applicable tariff.

The options flow adds or replaces one tariff entry per saved month. Existing cost statistics are
retained when a tariff is changed; historical recalculation is not performed automatically.

## Cost Calculation

For each pair of cumulative readings:

```text
energy_delta_kwh = latest_meter_value - previous_meter_value
working_charge_cost = energy_delta_kwh * applicable_working_charge
```

The result is aggregated into the same hourly buckets as the existing energy statistics.
For a new import range, the first returned reading is the zero baseline; the meter's lifetime
value is not used as the initial statistic sum.

The cost statistic must continue its cumulative `sum` across normal 48-hour refreshes. The implementation should use the previously stored cost statistic as the starting cumulative value instead of rebuilding the sum from only the current lookback window.

Meter resets, missing readings, negative deltas, and unavailable registers should be handled consistently with the existing energy statistic aggregation.

## Standing Charge Policy

The standing charge cannot be represented as a price-per-kWh value. It must be added as a monetary charge to the external cost statistic.

The MVP adds the monthly standing charge once to the first available hourly bucket of each calendar
month. This preserves the exact monthly total without inventing readings. A tariff change during
a month does not recalculate an already imported fixed charge.

## Tariff Changes and Historical Data

Changing the tariff from a new month is supported:

- Readings in each month use the tariff effective for that month.
- Readings before the first configured tariff are omitted from cost calculation.
- New refreshes use the new tariff automatically.

Tariff entries should be added before importing the corresponding historical range. Changing a
tariff that has already been used for imported history can change historical costs, but existing
statistics are not silently rewritten during a normal refresh.

Historical imports explicitly rebuild the requested range from a zero baseline. This preserves
correct cumulative sums when overlapping historical imports replace existing hourly statistics.

## Expected Code Areas

Likely implementation areas:

- `custom_components/metiundo/const.py`: tariff option keys and statistic suffixes
- `custom_components/metiundo/config_flow_handler/schemas/options.py`: tariff input validation
- `custom_components/metiundo/config_flow_handler/options_flow.py`: adding or updating tariff entries
- `custom_components/metiundo/coordinator/statistics.py`: tariff-aware cost aggregation and external cost import
- `custom_components/metiundo/coordinator/base.py`: passing tariff configuration and preserving cost-statistic continuity
- `custom_components/metiundo/translations/en.json`: options labels and descriptions
- `README.md` and user documentation: Energy Dashboard setup and tariff behavior

No new API endpoint is required because the calculation can use the existing cumulative readings.

## Phased Implementation

### Phase 1: Working Charge

- Add one configurable tariff.
- Generate the external import cost statistic.
- Calculate hourly cost from energy deltas.
- Keep cumulative cost sums stable across refreshes.
- Document Energy Dashboard setup.

### Implemented: Historical Tariff Schedules

- Store an ordered tariff history.
- Select the correct tariff for each reading interval.
- Import historical cost statistics across tariff boundaries.

### Implemented: Standing Charge

- Add the monthly charge to the first available hourly bucket.
- Keep the policy explicit in user documentation.

## Deferred Decisions

- Should old tariff edits trigger an explicit historical recalculation?
- Should the standing charge ever be prorated for a mid-month contract change?
- Should tariff effective dates support exact local date-times?
- Should export compensation be included in the first implementation?
- Should changing an old tariff offer an explicit recalculation action?

## Acceptance Criteria

- The generated cost statistic is selectable as grid cost tracking in the Energy Dashboard.
- Hourly cost equals measured import energy multiplied by the tariff active during each interval.
- Each month uses the tariff configured for that month.
- Normal coordinator refreshes do not reset or double-count cumulative cost sums.
- Historical imports crossing a tariff boundary produce correct hourly costs.
- Standing charge behavior is explicit, deterministic, and documented.
