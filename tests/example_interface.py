import logging
import os
import time

import yaml

from one_axis_stage.controller import StageController
from one_axis_stage.interface import MoveInterface

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

    # Get the path of the current script
    script_path = os.path.dirname(os.path.abspath(__file__))

    # Load the configuration file
    config_file = os.path.join(script_path, "example_config.yaml")
    config_file = "/home/murinemanager/.murineshiftwork/calibration.stage.setup2.yaml"
    with open(config_file) as f:
        config = yaml.safe_load(f)

    # Your controller logic goes here
    ctrl = StageController.from_config(config_file)

    ctrl.move_to_known_position("back")
    ctrl.move_to_known_position("center")

    ctrl.axes["y"].set_position(500)
    time.sleep(1)
    ctrl.save_as_known_position("front")

    ctrl.move_to_known_position("back")

    ctrl.move_to_known_position("front")

    ctrl.axes["y"].set_position(800)

    move = MoveInterface(ctrl, small_increment=20, large_increment=40)

    print(ctrl)

    move.move_axis_by_increment("x", -1)

    for _ in range(5):
        time.sleep(0.5)
        move.move_axis_by_increment("y", -1)

    move.move_axis_by_increment("y", 1)

    # ctrl.small_in

    ctrl.move_to_position({"x": 300, "y": 300, "z": 300})
    ctrl.save_known_position("front")

    time.sleep(1)

    ctrl.move_to_position({"x": 300, "y": 600, "z": 300})
    ctrl.save_known_position("back")

    time.sleep(1)

    ctrl.save_config(config_file=config_file)  # +"_saved.yaml")

    # move all axes in increments along the above position to the one below
    inc = 20
    for i in range(10):
        ctrl.move_to_position(
            {"x": 300 + i * inc, "y": 300 + i * inc, "z": 250 + i * inc}
        )
        time.sleep(2)

    ctrl.save_known_position("home")

    ctrl.move_to_position({"y": 250})

    time.sleep(1)

    ctrl.move_to_position({"x": 600, "y": 600, "z": 400})

    time.sleep(1)

    ctrl.move_to_known_position("home")

    # Example usage of the loaded configuration
    print("Controller configuration:")
    print(config)
