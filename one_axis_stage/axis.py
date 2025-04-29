import logging

from one_axis_stage.api import StageAPI


class StageAxis:
    name: str
    id: int

    position_raw: int = -1
    position_min: int = -1
    position_max: int = -1
    position_max: int = -1
    velocity_max: int = 0
    operating_mode: str = "OP_POSITION"
    api: StageAPI

    def __init__(
        self,
        name: str,
        id: int,
        position_min: int,
        position_max: int,
        velocity_max: int,
        operating_mode: str,
        api: StageAPI,
    ) -> None:
        self.name = name
        self.id = id
        self.position_min = position_min
        self.position_max = position_max
        self.velocity_max = velocity_max
        self.operating_mode = operating_mode
        self.api = api

        # set device mode
        # self.set_operating_mode(device_id=self.id, op_mode=self.operating_mode)
        # self.set_velocity(device_id=self.id, velocity=self.velocity_max)

        # get attrs
        # self.

    def __repr__(self) -> str:
        return f"StageAxis({self.name})"

    def __str__(self) -> str:
        return f"StageAxis: {self.name}"

    def __dict__(self) -> dict:
        return {
            "name": self.name,
            "id": self.id,
            "position_raw": self.position_raw,
            "position_min": self.position_min,
            "position_max": self.position_max,
            "velocity_max": self.velocity_max,
            "operating_mode": self.operating_mode,
        }

    def get_info(self):
        """
        Get the information of the device.

        Returns
        -------
        dict
            Information of the device.

        """
        info = self.api.get_info(device_id=self.id)

        # update Axis attributes
        self.position_raw = info["position_raw"]
        # self.position_deg = info["position_deg"]
        self.velocity_max = info["velocity_max"]
        self.operating_mode = info["operating_mode"]

        return info

    def get_position(self):
        """
        Get the position of the device.
        """
        self.position_raw = self.api.get_position(device_id=self.id)
        logging.debug(f"Get position: {self.position_raw}")
        return self.position_raw

    def set_position(self, position: int) -> None:
        """
        Set the position of the device.
        """
        assert (
            position >= self.position_min and position <= self.position_max
        ), f"Invalid position: {position}"

        self.api.set_position(device_id=self.id, position=position)
        self.position_raw = position
        logging.debug(f"Set position: {position}")

    def set_velocity(self, velocity: int) -> None:
        """
        Set the velocity of the device.
        """
        assert velocity >= 0 and velocity <= self.velocity_max, f"Invalid velocity: {velocity}"

        self.api.set_velocity(device_id=self.id, velocity=velocity)
        logging.debug(f"Set velocity: {velocity}")

    def set_operating_mode(self, op_mode: str | int) -> None:
        """
        Set the operating mode of the device.
        """
        assert op_mode is not None, f"Invalid operating mode: {op_mode}"

        if isinstance(op_mode, str):
            mode = self._op_mode_str_to_int(op_mode=op_mode)

        self.api.set_operating_mode(device_id=self.id, op_mode=op_mode)
        logging.debug(f"Set operating mode: {op_mode}")
