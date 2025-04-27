import json
import logging
import struct
import time
from typing import Any

from serial import Serial

OP_MODE_LOOKUP_TO_STR = {
    0: "OP_POSITION",
    1: "OP_EXTENDED_POSITION",
    2: "OP_CURRENT_BASED_POSITION",
    3: "OP_VELOCITY",
    4: "OP_PWM",
    5: "OP_CURRENT",
}
# invert dict
OP_MODE_LOOKUP = {v: k for k, v in OP_MODE_LOOKUP_TO_STR.items()}


class SerialConnection:
    serial_port: str | None = None
    baudrate: int | None = None
    timeout: float = 1
    connection: Serial | None = None

    def __init__(
        self,
        serial_port: str | None = None,
        baudrate: int | None = None,
        timeout: float | None = None,
        **kwargs: Any,
    ) -> None:
        self.serial_port = serial_port
        self.baudrate = baudrate or 115200
        self.timeout = timeout or 0.1

    def dict(self) -> dict:
        class_data = {
            "serial_port": self.serial_port,
            "baudrate": self.baudrate,
            "timeout": self.timeout,
        }
        return class_data

    def __repr__(self) -> str:
        return (
            f"SerialConnection(serial_port={self.serial_port}, "
            f"baudrate={self.baudrate}, "
            f"timeout={self.timeout})"
        )

    def __str__(self) -> str:
        return (
            f"SerialConnection: {self.serial_port} @ {self.baudrate} baud, "
            f"timeout={self.timeout}"
        )

    @property
    def connected(self) -> bool:
        if self.connection is not None:
            return self.connection.is_open
        else:
            return False

    def connect(self) -> "SerialConnection":
        if not self.connected:
            self.connection = Serial(
                port=self.serial_port,
                baudrate=self.baudrate,
                timeout=self.timeout,
            )
            # is open?
            if self.connection.is_open:
                logging.info(f"Connected to {self.serial_port} at {self.baudrate} baud.")
            else:
                logging.error(f"Failed to open serial port {self.serial_port}.")

        return self

    def disconnect(self) -> None:
        if self.connection is not None:
            self.connection.close()
            self.connection = None
            logging.info(f"Disconnected from {self.serial_port}.")

    def _encode(self, data: Any, order: str) -> bytes:
        """Encode & pack as byte struct & flank by start/stop bytes."""
        # check that data is list
        if not isinstance(data, list):
            data = [data]

        # encode str to bytes
        data_encoded = [item.encode() if isinstance(item, str) else item for item in data]

        # pack the data
        data_packed = struct.pack(order, *data_encoded)

        # flank the packed data with start/stop bytes </>
        message = b"<" + data_packed + b">"

        logging.debug(f"Encoded message: '{str(message)}'")
        return message

    def send(self, command: str, data: Any = None, order: str = None) -> None:
        """"""
        assert isinstance(command, str)
        assert isinstance(data, (list, int, str, None))
        assert isinstance(order, str)

        # combine command and data
        if data is not None:
            if not isinstance(data, list):
                data = [data]
            raw_data = [command] + data
        else:
            raw_data = command

        # encode/pack
        data_to_send = self._encode(raw_data, order=order)

        # send data
        if self.connected:
            self.connection.write(data_to_send)
            self.connection.flush()
            logging.debug(f"Sent data: {data_to_send}")

    def read_bytes(self, n_bytes: int = None, unpack_order: str = None) -> tuple[Any, ...]:
        """
        Read n_bytes from the serial port and unpack them according to the
        specified unpack_order.
        The unpack_order should be a format string compatible with the
        struct module.

        Parameters
        ----------
        n_bytes : int
        unpack_order : str

        Returns
        -------
        tuple
            Unpacked data as a tuple of values.

        """
        raw_data = self.connection.read(n_bytes)

        # Check if the correct amount of data was read
        if len(raw_data) != n_bytes:
            raise ValueError(f"Did not receive {n_bytes} bytes from serial port")

        # Unpack the data as separate variables
        unpacked_bytes = struct.unpack(unpack_order, raw_data)

        logging.debug(f"Unpacked bytes: {unpacked_bytes}")
        return unpacked_bytes

    def read_line(self) -> str:
        """
        Read a line from the serial port and decode it to a string.
        """
        line = self.connection.readline().decode("utf-8").strip()
        logging.debug(f"Received line: {line}")
        return line


class StageAPI(SerialConnection):
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

    def get_info_all(self, device_ids: list[int]) -> str:
        """"""
        self.send(command="I", data=device_ids, order="!HH")
        info_json = self.read_line()
        # to dict
        info_dict = json.loads(info_json)
        return info_dict

    def get_info(self, device_id: int) -> str:
        """"""
        self.send(command="i", data=device_id, order="!cH")

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

    def _resolve_operating_mode_code(self, op_mode: str) -> int:
        """
        Resolve the operating mode code from the mode string.
        """
        return OP_MODE_LOOKUP.get(op_mode)

    def set_operating_mode(self, device_id: int, op_mode: str | int) -> None:
        """
        Set the operating mode of a device.
        """
        # resolve mode code
        assert op_mode is not None, f"Invalid operating mode: {op_mode}"

        if isinstance(op_mode, str):
            op_mode = self._resolve_operating_mode_code(op_mode=op_mode)

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


class StageAxis(StageAPI):
    name: str
    id: int

    position_raw: int
    position_min: int
    position_max: int
    velocity_max: int
    operating_mode: str
    controller: StageAPI

    def __init__(
        self,
        name: str,
        id: int,
        position_min: int,
        position_max: int,
        velocity_max: int,
        operating_mode: str,
        controller: StageAPI,
    ) -> None:
        self.name = name
        self.id = id
        self.position_min = position_min
        self.position_max = position_max
        self.velocity_max = velocity_max
        self.operating_mode = operating_mode
        self.controller = controller

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
        return self.controller.get_info(device_id=self.id)

    def get_position(self):
        """
        Get the position of the device.
        """
        self.position_raw = self.controller.get_position(device_id=self.id)
        logging.debug(f"Get position: {self.position_raw}")
        return self.position_raw

    def set_position(self, position: int) -> None:
        """
        Set the position of the device.
        """
        assert (
            position >= self.position_min and position <= self.position_max
        ), f"Invalid position: {position}"

        self.controller.set_position(device_id=self.id, position=position)
        self.position_raw = position
        logging.debug(f"Set position: {position}")

    def set_velocity(self, velocity: int) -> None:
        """
        Set the velocity of the device.
        """
        assert velocity >= 0 and velocity <= self.velocity_max, f"Invalid velocity: {velocity}"

        self.controller.set_velocity(device_id=self.id, velocity=velocity)
        logging.debug(f"Set velocity: {velocity}")

    def set_operating_mode(self, op_mode: str | int) -> None:
        """
        Set the operating mode of the device.
        """
        assert op_mode is not None, f"Invalid operating mode: {op_mode}"

        if isinstance(op_mode, str):
            mode = self._resolve_operating_mode_code(op_mode=op_mode)

        self.controller.set_operating_mode(device_id=self.id, op_mode=op_mode)
        logging.debug(f"Set operating mode: {op_mode}")


if __name__ == "__main__":
    # Open the serial connection
    api = StageAPI(serial_port="/dev/ttyUSB0", baudrate=115200)
    api.connect()
    api.scan_for_devices()
