import json
import logging
import time
from typing import Any

from one_axis_stage import BAUDRATE_LOOKUP, OP_MODE_LOOKUP, OP_MODE_LOOKUP_TO_STR
from one_axis_stage.connection import StageSerialConnection


class StageAPI(StageSerialConnection):
    def __init__(self, serial_port: str, baudrate: int = 115200, timeout: float = 1) -> None:
        # init serial connection
        super().__init__(serial_port=serial_port, baudrate=baudrate, timeout=timeout)

    # --- GETTERS ---

    def scan_for_devices(self):
        self.send(command="s", order="c")
        time.sleep(2)

        # while returning lines, read until no more lines
        scan_result = ""
        while self.connection.in_waiting > 0:
            line = self.read_line()
            scan_result += line + "\n"
            logging.debug(f"Scan line: {line}")
            time.sleep(2)

        return scan_result

    def get_info(self, device_id: int) -> str:
        """"""
        self.send(command="i", data=device_id, order="!cH")
        info_json = self.read_line()
        # to dict
        info_dict = json.loads(info_json)

        # resolve baud_rate_int -> baud_rate, same for operating mode
        info_dict["baud_rate"] = BAUDRATE_LOOKUP.get(info_dict["baud_rate_int"])
        info_dict["operating_mode"] = self._op_mode_int_to_str(info_dict["operating_mode_int"])

        return info_dict

    def get_info_all(self, device_ids: list[Any]) -> str:
        """"""
        info_all = []
        for device_id in device_ids:
            info_all.append(self.get_info(device_id))

        # data_order = "!c" + len(device_ids) * "H"
        # self.send(command="I", data=device_ids, order=data_order)
        # info_json = self.read_line()
        # # to dict
        # info_dict = json.loads(info_json)
        # return info_dict
        return info_all

    def get_position(self, device_id: int) -> int:
        """
        Get the position of a device.
        """
        self.send(command="p", data=device_id, order="!cH")
        # read 2 bytes
        raw_data = self.read_bytes(n_bytes=2, unpack_order="!HH")
        # combine bytes to int
        position = (raw_data[0] << 8) | raw_data[1]
        logging.debug(f"Position: {position}")
        return position

    # --- SETTERS ---

    def set_position(self, device_id: int, position: int) -> None:
        """
        Set the position of a device.
        """
        self.send(
            command="m",
            data=[device_id, position],
            order="!cHH",
        )

    def set_position_multiple(self, position_tuples: list[tuple[int, int]]) -> None:
        """
        Set the position of multiple devices.
        """
        data = []
        data_order = ""
        for device_id, position in position_tuples:
            data.append(device_id)
            data.append(position)
            data_order += "HH"

        logging.debug(f"Data order: {data_order}")
        logging.debug(f"Position tuples: {data}")

        # send
        self.send(command="M", data=data, order="!c" + data_order)

    def set_baudrate(self, device_id: int, current_baudrate: int, new_baudrate: int) -> None:
        """
        Set the baudrate of a device.
        """
        # TODO: assert baudrate in baudrate list

        self.send(
            command="b",
            data=[device_id, current_baudrate, new_baudrate],
            order="!cHHH",
        )

    def set_device_id(self, current_device_id: int, new_device_id: int) -> None:
        """
        Set the device ID of a device.
        """
        # TODO: assert device id range

        self.send(
            command="d",
            data=[current_device_id, new_device_id],
            order="!cHH",
        )

    def set_velocity(self, device_id: int, velocity: int) -> None:
        """
        Set the velocity of a device.
        """
        # TODO: confirm that this is the velocity limit
        assert velocity >= 0 and velocity <= 254, f"Invalid velocity: {velocity}"

        self.send(
            command="v",
            data=[device_id, velocity],
            order="!cHH",
        )

    def _op_mode_str_to_int(self, op_mode: str) -> int:
        """
        Resolve the operating mode code from the mode string.
        """
        return OP_MODE_LOOKUP.get(op_mode)

    def _op_mode_int_to_str(self, op_mode: int) -> str:
        """
        Resolve the operating mode code from the mode string.
        """
        return OP_MODE_LOOKUP_TO_STR.get(op_mode)

    def set_operating_mode(self, device_id: int, op_mode: str | int) -> None:
        """
        Set the operating mode of a device.
        """
        # resolve mode code
        assert op_mode is not None, f"Invalid operating mode: {op_mode}"

        if isinstance(op_mode, str):
            op_mode = self._op_mode_str_to_int(op_mode=op_mode)

        self.send(
            command="o",
            data=[device_id, op_mode],
            order="!cHH",
        )

    def flash(self, device_id: int, duration_ms: int, repeats: int) -> None:
        """
        Flash the LED of a device.
        """
        assert isinstance(duration_ms, int)
        assert isinstance(repeats, int)

        self.send(
            command="f",
            data=[device_id, duration_ms, repeats],
            order="!cHHH",
        )
