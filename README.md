[//]: # (Links)
[Github-flavored markdown]: https://github.github.com/gfm

[manifest]: https://packaging.python.org/en/latest/guides/using-manifest-in
[packaging]: https://packaging.python.org/en/latest/tutorials/packaging-projects
[setup.cfg]: https://setuptools.pypa.io/en/latest/userguide/declarative_config.html

[bump2version]: (https://github.com/c4urself/bump2version
[pre-commit]: https://pre-commit.com

[//]: # ([black]: https://github.com/psf/black)
[ruff]: https://docs.astral.sh/ruff
[mypy]: https://mypy.readthedocs.io

[pypi]: pypi.org
[test.pypi]: test.pypi.org

[Zenodo]: https://zenodo.org

[contribution guidelines]: https://github.com/larsrollik/one-axis-stage/blob/main/CONTRIBUTING.md
[issues]: https://github.com/larsrollik/one-axis-stage/issues
[BSD 3-Clause License]: https://github.com/larsrollik/one-axis-stage/blob/main/LICENSE
[Github]: https://github.com/larsrollik/one-axis-stage/settings/secrets/actions/new
[release]: https://github.com/larsrollik/one-axis-stage/releases/new

[//]: # (Badges)

[![Contributions](https://img.shields.io/badge/Contributions-Welcome-brightgreen.svg)](https://github.com/larsrollik/one-axis-stage/blob/main/CONTRIBUTING.md)
![CI](https://img.shields.io/github/actions/workflow/status/larsrollik/one-axis-stage/pre-pr-checks.yaml?branch=main&label=build)
[![pre-commit](https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit&logoColor=white)](https://github.com/pre-commit/pre-commit)
[![Website](https://img.shields.io/website?up_message=online&url=https%3A%2F%2Fgithub.com/larsrollik/one-axis-stage)](https://github.com/larsrollik/one-axis-stage)

[//]: # ([![PyPI]&#40;https://img.shields.io/pypi/v/one-axis-stage.svg&#41;]&#40;https://pypi.org/project/one-axis-stage&#41;)
[//]: # ([![Wheel]&#40;https://img.shields.io/pypi/wheel/one-axis-stage.svg&#41;]&#40;https://pypi.org/project/one-axis-stage&#41;)

# one-axis-stage
Hardware design and software for modular, low-cost one-axis stages
---
**Version: "0.0.1"**

```-> TODO: add image```

## Hardware build

### Parts list

##### Commercially available parts

| Part name                     | Product code          | Amount (#) | Cost per part (GBP) | Total cost (GBP) |                                                                                                      |
|-------------------------------|-----------------------|------------|---------------------|------------------|------------------------------------------------------------------------------------------------------|
| Arduino Mega 2560             |                       | 1          | 20                  |                  | https://docs.arduino.cc/hardware/mega-2560                                                           |
| Dynamixel Arduino shield      |                       | 1          | 20                  |                  | https://emanual.robotis.com/docs/en/parts/interface/dynamixel_shield/                                |
| Dynamixel XL-320 motor        | XL-320                | 1+         | 20                  |                  | https://emanual.robotis.com/docs/en/dxl/x/xl320/                                                     |
| USB to TTL adapter            | LN-101 or MIKROE-3063 | 1          | 14 / 13             |                  | https://emanual.robotis.com/docs/en/parts/interface/ln-101 / https://www.mikroe.com/usb-uart-3-click |
| USB-B to other USB (computer) |                       | 1          |                     |                  |                                                                                                      |
| Linear slide 26mm range       | BSP1035SL             | 2+         | 26                  |                  | https://uk.rs-online.com/web/p/linear-slides/0749301                                                 |
|                               |                       |            |                     |                  |                                                                                                      |

##### 3D-printed parts

| Part | Count |
|------|-------|
|      |       |
|      |       |
|      |       |

### Assembly instructions

```-> TODO: add info on how to assemble the hardware```

## Software controller

### Example usage

```python
from one_axis_stage import StageController

```


## Contributing
Contributions are very welcome!
Please see the [contribution guidelines] or check out the [issues]


## License
This software is released under the **[BSD 3-Clause License]**
