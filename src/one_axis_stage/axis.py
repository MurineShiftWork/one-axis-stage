"""Single-axis abstraction with position bounds enforcement."""

import logging

from one_axis_stage.api import StageAPI


class StageAxis:
    """Represents one motor axis with configurable position limits and velocity cap.

    Wraps StageAPI calls for a specific device ID and enforces min/max position
    bounds on every move command before sending it to the controller.
    """

    name: str
    id: int

    position_raw: int = -1
    position_min: int = -1
    position_max: int = -1
    velocity_max: int = 0
    operating_mode: str = "OP_POSITION"
    api: StageAPI

    def __init__(
        self,
        name: str,
        id: int,
        # position_raw: int,
        position_min: int,
        position_max: int,
        velocity_max: int,
        operating_mode: str,
        api: StageAPI,
        **kwargs,
    ) -> None:
        self.name = name
        self.id = id
        self.position_min = position_min
        self.position_max = position_max
        self.velocity_max = velocity_max
        self.operating_mode = operating_mode
        self.api = api

    def __repr__(self) -> str:
        return f"StageAxis({self.name})"

    def __str__(self) -> str:
        return f"StageAxis: {self.name}"

    def to_dict(self) -> dict:
        """Return axis configuration and current state as a plain dictionary."""
        return {
            "name": self.name,
            "id": self.id,
            "position_raw": self.position_raw,
            "position_min": self.position_min,
            "position_max": self.position_max,
            "velocity_max": self.velocity_max,
            "operating_mode": self.operating_mode,
        }

    def get_info(self) -> dict:
        """Query the device and update local state (position, velocity, operating mode).

        Returns:
            Status dict from the firmware for this device.
        """
        info = self.api.get_info(device_id=self.id)

        # update Axis attributes
        self.position_raw = info["position_raw"]
        self.velocity_max = info["velocity_max"]
        self.operating_mode = info["operating_mode"]

        return info

    def get_position(self) -> int:
        """Query and return the current raw position, updating the local cache."""
        self.position_raw = self.api.get_position(device_id=self.id)
        logging.debug(f"Get position: {self.position_raw}")
        return self.position_raw

    def set_position(self, position: int) -> None:
        """Move to an absolute raw position, clamped to [position_min, position_max].

        Args:
            position: Target raw position in device units.

        Raises:
            AssertionError: If position is outside the configured bounds.
        """
        assert position >= self.position_min and position <= self.position_max, (
            f"Invalid position: {position}"
        )

        self.api.set_position(device_id=self.id, position=position)
        self.position_raw = position
        logging.debug(f"Set position: {position}")

    def set_velocity(self, velocity: int) -> None:
        """Set the velocity limit, clamped to [0, velocity_max].

        Args:
            velocity: Target velocity in device units.

        Raises:
            AssertionError: If velocity exceeds the axis velocity_max.
        """
        assert velocity >= 0 and velocity <= self.velocity_max, (
            f"Invalid velocity: {velocity}"
        )

        self.api.set_velocity(device_id=self.id, velocity=velocity)
        logging.debug(f"Set velocity: {velocity}")

    def set_operating_mode(self, op_mode: str | int) -> None:
        """Set the operating mode for this axis.

        Args:
            op_mode: Mode name (e.g. ``"OP_POSITION"``) or integer code.
        """
        assert op_mode is not None, f"Invalid operating mode: {op_mode}"

        # api.set_operating_mode() converts a str mode name to its int code
        # internally; do not pre-convert here (StageAxis has no such helper).
        self.api.set_operating_mode(device_id=self.id, op_mode=op_mode)
        logging.debug(f"Set operating mode: {op_mode}")
