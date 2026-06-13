# Usage

## Moving axes

### Single-axis absolute move

```python
ctrl.move_to_position({"x": 500})
```

### Multi-axis simultaneous move

All target positions are sent in a single serial packet so the axes start
moving at the same time:

```python
ctrl.move_to_position({"x": 300, "y": 600, "z": 250})
```

### Direct axis access

Individual axes expose `set_position` and `get_position` directly:

```python
axis = ctrl.axes["y"]
print(axis.get_position())   # raw position int
axis.set_position(450)
```

## Named positions

Save and recall named positions to repeat common locations without
hardcoding coordinates:

```python
# Save wherever the stage is right now
ctrl.save_as_known_position("loading")

# Move elsewhere, then return
ctrl.move_to_position({"x": 700, "y": 700})
ctrl.move_to_known_position("loading")

# Remove a saved position
ctrl.remove_known_position("loading")
```

Named positions survive a `save_config` / `from_config` round-trip.

## Saving and reloading configuration

```python
# Write current state (axes, known positions, connection params) to YAML
ctrl.save_config("my_stage.yaml")

# Reload in a later session
ctrl = StageController.from_config("my_stage.yaml")
```

## Incremental moves with MoveInterface

`MoveInterface` is useful for interactive fine-tuning.
It wraps a controller and exposes per-axis step methods:

```python
from one_axis_stage.interface import MoveInterface

move = MoveInterface(ctrl, small_increment=20, large_increment=40)

move.xp()    # x +20
move.xm()    # x -20
move.xpp()   # x +40
move.xmm()   # x -40

# Same pattern for every registered axis
move.yp()
move.ymm()
```

Out-of-bounds moves are caught and logged rather than raising an exception,
so these helpers are safe to call in loops or GUI callbacks.

## Device identification and scanning

Flash the LED on a device to identify it physically:

```python
ctrl.api.flash(device_id=21, duration_ms=500, repeats=3)
```

Scan the bus to discover which device IDs are online:

```python
results = ctrl.api.scan_for_devices()
print(results)
```

## Changing operating mode

```python
# By name
ctrl.api.set_operating_mode(device_id=21, op_mode="OP_VELOCITY")

# By integer code
ctrl.api.set_operating_mode(device_id=21, op_mode=3)
```

Available modes: `OP_POSITION`, `OP_EXTENDED_POSITION`,
`OP_CURRENT_BASED_POSITION`, `OP_VELOCITY`, `OP_PWM`, `OP_CURRENT`.

## Logging

The package uses the standard `logging` module.
Enable debug output to see every command sent over the serial link:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```
