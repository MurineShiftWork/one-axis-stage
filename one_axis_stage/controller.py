import time
from pathlib import Path

import yaml

from one_axis_stage.api import StageAPI
from one_axis_stage.axis import StageAxis


class StageController:
    serial_port: str
    baudrate: int
    timeout: float

    api: StageAPI
    axes: dict = {}
    known_positions: dict = {}

    def __init__(
        self,
        serial_port: str | None = None,
        baudrate: int | None = None,
        timeout: float | None = None,
        # **kwargs,
    ) -> None:
        if serial_port is not None:
            self.serial_port = str(serial_port)
        if baudrate is not None:
            self.baudrate = int(baudrate)
        if timeout is not None:
            self.timeout = float(timeout)

        # if serial port is provided, connect to the stage
        if self.serial_port is not None:
            self.connect()

    # getter/setter for config dict
    @property
    def config(self) -> dict:
        return {
            "connection": {
                "serial_port": self.serial_port,
                "baudrate": self.baudrate,
                "timeout": self.timeout,
            },
            "axes": {axis_name: axis.__dict__() for axis_name, axis in self.axes.items()},
            "known_positions": self.known_positions,
        }

    @config.setter
    def config(self, config: dict) -> None:
        self.serial_port = config["connection"]["serial_port"]
        self.baudrate = config["connection"]["baudrate"]
        self.timeout = config["connection"]["timeout"]

        self.axes = {}
        for axis_name, axis_config in config["axes"].items():
            self.add_axis(axis_name, **axis_config)
            time.sleep(1)

        # self.axes = {
        #     axis_name: StageAxis(controller=self, name=axis_name, **axis_config)
        #     for axis_name, axis_config in config["axes"].items()
        # }
        self.known_positions = config["known_positions"]

    def connect(self) -> None:
        self.api = StageAPI(
            serial_port=self.serial_port,
            baudrate=self.baudrate,
            timeout=self.timeout,
        )
        self.api.connect()

    # factory function to create a StageController instance from a configuration file
    @staticmethod
    def from_config(config_file: str | Path) -> "StageController":
        config_file = Path(config_file)
        # check file exists
        if not config_file.is_file():
            raise FileNotFoundError(f"Config file not found: {config_file}")

        config_file.open("r")
        with config_file.open("r") as file:
            # yaml full load
            stage_config = yaml.full_load(file)

        ctrl = StageController(**stage_config["connection"])
        ctrl.config = stage_config

        # ctrl.ping_axes()

        return ctrl

    def save_config(self, config_file: str | Path) -> None:
        config_file = Path(config_file)
        # check file exists
        if not config_file.is_file():
            raise FileNotFoundError(f"Config file not found: {config_file}")

        with config_file.open("w") as file:
            yaml.dump(self.config, file)

    def add_axis(self, axis_name: str, **axis_config) -> None:
        if "name" in axis_config:
            axis_name = axis_config.pop("name")

        if axis_name in self.axes:
            raise ValueError(f"Axis already exists: {axis_name}")

        self.axes[axis_name] = StageAxis(controller=self, name=axis_name, **axis_config)

        return self.axes[axis_name]

    def ping_axes(self) -> None:
        for axis in self.axes.values():
            axis.sync_attrs_from_stage()

    def move_to_position(self, position: dict) -> None:
        # lookup axis by name and move to position
        position_by_axis_id = [
            (self.axes[axis_name].id, position[axis_name]) for axis_name in position
        ]
        return self.api.set_position_multiple(position_tuples=position_by_axis_id)

    def move_to_known_position(self, position_name: str) -> None:
        position = self.known_positions.get(position_name)

        if position is None:
            raise ValueError(f"Unknown position: {position_name}")

        return self.move_to_position(position)

    def save_known_position(self, position_name: str) -> None:
        new_position = {}
        for axis_name in self.axes:
            self.axes[axis_name].dict()
            new_position[axis_name] = self.axes[axis_name].__dict__()["position_raw"]

        self.known_positions[position_name] = new_position

    def remove_known_position(self, position_name: str) -> None:
        self.known_positions.pop(position_name)
