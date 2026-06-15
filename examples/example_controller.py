import logging
import time
from pathlib import Path

import yaml

from one_axis_stage.controller import StageController

if __name__ == "__main__":
    # Set up logging
    logging.basicConfig(level=logging.DEBUG)
    # format
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    # set on handler
    for handler in logging.getLogger().handlers:
        handler.setFormatter(formatter)

    config_file = Path(__file__).resolve().parent / "example_config.yaml"
    with config_file.open() as f:
        config = yaml.safe_load(f)

    # Your controller logic goes here
    ctrl = StageController.from_config(config_file)
    # ctrl.ping_axes()

    ctrl.move_to_position({"x": 300, "y": 300, "z": 300})
    ctrl.save_as_known_position("front")

    time.sleep(1)

    ctrl.move_to_position({"x": 300, "y": 600, "z": 300})
    ctrl.save_as_known_position("back")

    time.sleep(1)

    ctrl.save_config(config_file=config_file.with_name("example_config_saved.yaml"))

    # move all axes in increments along the above position to the one below
    inc = 20
    for i in range(10):
        ctrl.move_to_position(
            {"x": 300 + i * inc, "y": 300 + i * inc, "z": 250 + i * inc}
        )
        time.sleep(2)

    ctrl.save_as_known_position("home")

    ctrl.move_to_position({"y": 250})

    time.sleep(1)

    ctrl.move_to_position({"x": 600, "y": 600, "z": 400})

    time.sleep(1)

    ctrl.move_to_known_position("home")

    # Example usage of the loaded configuration
    print("Controller configuration:")
    print(config)
