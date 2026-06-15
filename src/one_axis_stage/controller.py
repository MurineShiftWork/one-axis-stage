"""High-level multi-axis stage controller with named position support."""

import logging
import time
from pathlib import Path

import yaml

from one_axis_stage.api import StageAPI
from one_axis_stage.axis import StageAxis


class StageController:
    """Coordinates one or more StageAxis instances over a shared serial connection.

    Provides named-position storage, multi-axis simultaneous moves, and
    YAML-based configuration save/load.  The recommended entry point is
    `from_config` rather than direct construction.
    """

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
        """Current controller state as a serialisable dictionary."""
        return {
            "stage_id": self.api.stage_id,
            "connection": {
                "serial_port": self.serial_port,
                "baudrate": self.baudrate,
                "timeout": self.timeout,
            },
            "axes": {
                axis_name: axis.to_dict() for axis_name, axis in self.axes.items()
            },
            "known_positions": self.known_positions,
        }

    @config.setter
    def config(self, config: dict) -> None:
        """Apply a configuration dictionary, rebuilding axes and known positions."""
        self.serial_port = config["connection"]["serial_port"]
        self.baudrate = config["connection"]["baudrate"]
        self.timeout = config["connection"]["timeout"]

        self.axes = {}
        for axis_name, axis_config in config["axes"].items():
            self.add_axis(axis_name, **axis_config)
            time.sleep(1)

        self.known_positions = config["known_positions"]

    def connect(self) -> None:
        """Open the serial connection and query the stage ID."""
        self.api = StageAPI(
            serial_port=self.serial_port,
            baudrate=self.baudrate,
            timeout=self.timeout,
        )
        self.api.connect()
        self.api.get_stage_id()

    @staticmethod
    def from_config(config_file: str | Path | dict) -> "StageController":
        """Construct a StageController from a YAML config file or a pre-loaded dict.

        Args:
            config_file: Path to a YAML configuration file, or a dict with the same structure.

        Returns:
            A connected StageController with axes initialised.

        Raises:
            FileNotFoundError: If a path is given but the file does not exist.
            TypeError: If config_file is not a str, Path, or dict.
        """
        if isinstance(config_file, str):
            config_file = Path(config_file)

        if isinstance(config_file, Path):
            config_file = Path(config_file)
            # check file exists
            if not config_file.is_file():
                raise FileNotFoundError(f"Config file not found: {config_file}")

            config_file.open("r")
            with config_file.open("r") as file:
                # yaml full load
                stage_config = yaml.full_load(file)
        elif isinstance(config_file, dict):
            stage_config = config_file
        else:
            raise TypeError(f"Config type {config_file} is not supported")

        ctrl = StageController(**stage_config["connection"])
        ctrl.config = stage_config

        return ctrl

    def save_config(self, config_file: str | Path, overwrite: bool = True) -> bool:
        """Write the current controller configuration to a YAML file.

        Args:
            config_file: Destination path.
            overwrite: If False, raise FileExistsError when the file already exists.

        Returns:
            True if the file was written successfully.
        """
        config_file = Path(config_file)
        # check file exists
        if config_file.exists() and not overwrite:
            raise FileExistsError(f"Config file already exists: {config_file}")

        with config_file.open("w") as file:
            yaml.dump(self.config, file)

        return config_file.exists()

    def add_axis(self, axis_name: str, **axis_config) -> StageAxis:
        """Register a new axis on the controller and query its initial state.

        Args:
            axis_name: Logical name used to address the axis (e.g. ``"x"``).
            **axis_config: Keyword arguments forwarded to StageAxis (id, position_min, position_max, velocity_max, operating_mode).

        Returns:
            The newly created StageAxis instance.

        Raises:
            ValueError: If an axis with the same name already exists.
        """
        if "name" in axis_config:
            axis_name = axis_config.pop("name")

        if axis_name in self.axes:
            raise ValueError(f"Axis already exists: {axis_name}")

        self.axes[axis_name] = StageAxis(api=self.api, name=axis_name, **axis_config)
        info = self.axes[axis_name].get_info()
        logging.debug(f"Controller: Added new axis {axis_name} ({info})")

        return self.axes[axis_name]

    def ping_axes(self) -> None:
        """Refresh device info for all registered axes."""
        for axis in self.axes.values():
            axis.get_info()

    def move_to_position(self, position: dict) -> None:
        """Move one or more axes to target raw positions in a single command.

        Args:
            position: Mapping of axis name to target position. Value may be an
                integer raw position or a dict with a ``"position_raw"`` key.

        Example:
            ``ctrl.move_to_position({"x": 300, "y": 500})``
        """
        logging.debug(f"Controller: Move to position: {position}")

        # lookup axis by name and move to position
        position_by_axis_id = []
        for axis_name in position:
            axis_id = self.axes[axis_name].id
            axis_target = position[axis_name]
            logging.debug(f"Controller: Move to axis: {axis_id} -> {axis_target}")
            if "position_raw" in axis_target:
                axis_target_position = axis_target["position_raw"]
                logging.debug(f"removing key position_raw from target {axis_target}")
            else:
                axis_target_position = axis_target

            position_by_axis_id.append((axis_id, axis_target_position))

        return self.api.set_position_multiple(position_tuples=position_by_axis_id)

    def move_to_known_position(self, position_name: str) -> None:
        """Move to a previously saved named position.

        Args:
            position_name: Key used when the position was saved with `save_as_known_position`.

        Raises:
            ValueError: If the position name is not found in `known_positions`.
        """
        position = self.known_positions.get(position_name)

        if position is None:
            raise ValueError(f"Unknown position: {position_name}")

        return self.move_to_position(position)

    def save_as_known_position(self, position_name: str) -> None:
        """Query all axes and store their current positions under a named key.

        Args:
            position_name: Label for the saved position.
        """
        new_position = {}
        for axis_name in self.axes:
            self.axes[axis_name].get_info()
            axis_dict = self.axes[axis_name].__dict__()
            new_position[axis_name] = {"position_raw": axis_dict["position_raw"]}

        self.known_positions[position_name] = new_position
        logging.debug(f"Controller: Save as known position: {new_position}")

    def remove_known_position(self, position_name: str) -> None:
        """Delete a named position from the known positions registry."""
        self.known_positions.pop(position_name)
