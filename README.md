# one-axis-stage

[![PyPI](https://img.shields.io/pypi/v/one-axis-stage.svg)](https://pypi.org/project/one-axis-stage)

Hardware design and Python software for modular, low-cost one-axis stages using
Dynamixel XL-320 servo motors.

Provides a serial API, high-level controller, and `stage` CLI for
scanning, configuring, and jogging stages from the command line.

**[→ Full documentation](https://murineshiftwork.github.io/one-axis-stage)**

## Installation

```bash
pip install one-axis-stage
```

For interactive jog mode:

```bash
pip install "one-axis-stage[cli]"
```

## Quick start

```python
from one_axis_stage.api import StageAPI

api = StageAPI(serial_port="/dev/ttyUSB0")
api.connect()
print(api.get_info(device_id=21))
api.set_position(device_id=21, position=400)
api.disconnect()
```

## CLI

```bash
stage scan --port /dev/ttyUSB0
stage info --port /dev/ttyUSB0 --id 21
stage move --port /dev/ttyUSB0 --id 21 --position 400
stage jog  --port /dev/ttyUSB0 --id 21
```

## Hardware

Arduino Mega 2560 + Dynamixel shield + XL-320 motors + linear slides.
Firmware source in `firmware/`.

## License

BSD 3-Clause. See [LICENSE](LICENSE).
