# Getting Started

## Installation

```bash
pip install one-axis-stage
```

The package requires Python 3.10 or later and depends on [pyserial](https://pyserial.readthedocs.io/).

## Hardware connection

Connect the stage controller to a USB or RS-232 serial port on your computer.
On Linux the port is typically `/dev/ttyUSB0`; on macOS it appears as
`/dev/tty.usbserial-*`; on Windows it is a `COM` port such as `COM3`.

Set the baud rate to match the firmware setting (default: `115200`).

## First connection

The recommended entry point is `StageController`.
You can connect directly by passing a serial port and then adding axes manually:

```python
from one_axis_stage.controller import StageController

ctrl = StageController(serial_port="/dev/ttyUSB0", baudrate=115200, timeout=1)

# Register an axis: give it a logical name and the Dynamixel device ID
ctrl.add_axis("x", id=21, position_min=200, position_max=800, velocity_max=0, operating_mode="OP_POSITION")
```

## Minimal working example

```python
from one_axis_stage.controller import StageController

ctrl = StageController(serial_port="/dev/ttyUSB0", baudrate=115200, timeout=1)
ctrl.add_axis("x", id=21, position_min=200, position_max=800, velocity_max=0, operating_mode="OP_POSITION")

# Query the current position
pos = ctrl.axes["x"].get_position()
print(f"Current position: {pos}")

# Move to an absolute raw position
ctrl.move_to_position({"x": 500})

# Save the current location and return to it later
ctrl.save_as_known_position("home")
ctrl.move_to_position({"x": 700})
ctrl.move_to_known_position("home")
```

## Loading a configuration file

For multi-axis rigs it is more practical to define axes in a YAML file and
load with `from_config`:

```yaml
# stage_config.yaml
connection:
  serial_port: /dev/ttyUSB0
  baudrate: 115200
  timeout: 1

axes:
  x:
    id: 21
    position_min: 200
    position_max: 800
    velocity_max: 0
    operating_mode: OP_POSITION
  y:
    id: 55
    position_min: 200
    position_max: 800
    velocity_max: 0
    operating_mode: OP_POSITION

known_positions:
  home:
    x:
      position_raw: 400
    y:
      position_raw: 400
```

```python
from one_axis_stage.controller import StageController

ctrl = StageController.from_config("stage_config.yaml")
ctrl.move_to_known_position("home")
```
