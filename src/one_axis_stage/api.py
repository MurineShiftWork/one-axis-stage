"""Command-level API for a single stage controller over serial."""

import json
import logging
import time
from typing import Any

from one_axis_stage import BAUDRATE_LOOKUP, OP_MODE_LOOKUP, OP_MODE_LOOKUP_TO_STR
from one_axis_stage.connection import StageSerialConnection


class StageAPI(StageSerialConnection):
    """Direct command interface to the stage controller firmware.

    Wraps StageSerialConnection with typed commands for device discovery,
    position control, velocity, operating mode, and LED feedback.
    Each method corresponds to one firmware command.
    """

    stage_id: int = 0

    def __init__(
        self, serial_port: str, baudrate: int = 115200, timeout: float = 1
    ) -> None:
        # init serial connection
        super().__init__(serial_port=serial_port, baudrate=baudrate, timeout=timeout)

    # --- GETTERS ---

    def get_stage_id(self) -> int:
        """Query and cache the controller's stage ID."""
        self.send(command="e", order="c")
        info_json = self.read_line()

        # to dict
        stage_id_dict = json.loads(info_json)
        stage_id = stage_id_dict["stage_id"]
        self.stage_id = stage_id
        return stage_id

    def scan_for_devices(self, timeout: float = 8.0, idle_timeout: float = 1.0) -> str:
        """Broadcast a scan and return a newline-separated list of discovered device IDs.

        Reads until there has been ``idle_timeout`` seconds of silence on the bus
        or ``timeout`` seconds total have elapsed. Increase ``timeout`` if the bus
        has many devices or runs at a slow baud rate.

        Args:
            timeout: Maximum total wait time in seconds.
            idle_timeout: Stop reading after this many seconds with no new data.
        """
        self.send(command="s", order="c")

        scan_result = ""
        deadline = time.monotonic() + timeout
        last_data = time.monotonic()

        while time.monotonic() < deadline:
            if self.connection.in_waiting > 0:
                line = self.read_line()
                scan_result += line + "\n"
                logging.debug("Scan line: %s", line)
                last_data = time.monotonic()
            elif time.monotonic() - last_data > idle_timeout:
                break
            else:
                time.sleep(0.05)

        return scan_result

    def get_info(self, device_id: int) -> dict:
        """Return a status dict for a single device, with baud rate and operating mode resolved to human-readable strings.

        Args:
            device_id: Dynamixel device ID on the serial bus.
        """
        self.send(command="i", data=device_id, order="!cH")
        info_json = self.read_line()

        # to dict
        info_dict = json.loads(info_json)

        # resolve baud_rate_int -> baud_rate, same for operating mode
        info_dict["baud_rate"] = BAUDRATE_LOOKUP.get(info_dict["baud_rate_int"])
        info_dict["operating_mode"] = self._op_mode_int_to_str(
            info_dict["operating_mode_int"]
        )

        return info_dict

    def get_info_all(self, device_ids: list[Any]) -> list[dict]:
        """Return a list of status dicts, one per device ID."""
        info_all = []
        for device_id in device_ids:
            info_all.append(self.get_info(device_id))

        return info_all

    def get_position(self, device_id: int) -> int:
        """Return the current raw position of a device."""
        self.send(command="p", data=device_id, order="!cH")
        # read 2 bytes & combine bytes to int
        position = self.read_bytes(n_bytes=2, unpack_order="!H")
        if isinstance(position, tuple):
            position = position[0]

        logging.debug(f"Position: {position}")
        return position

    # --- SETTERS ---

    def set_position(self, device_id: int, position: int) -> None:
        """Command a device to move to an absolute raw position."""
        self.send(
            command="m",
            data=[device_id, position],
            order="!cHH",
        )

    def set_position_multiple(self, position_tuples: list[tuple[int, int]]) -> None:
        """Command multiple devices to move simultaneously.

        Args:
            position_tuples: List of (device_id, position) pairs sent in a single packet.
        """
        logging.debug(f"Moving to position: {position_tuples}")

        data = []
        data_order = "!c"
        for device_id, position in position_tuples:
            data.append(device_id)
            data.append(position)
            data_order += "HH"

        logging.debug(f"Data order: {data_order}")
        logging.debug(f"Position tuples: {data}")

        # send
        self.send(command="M", data=data, order=data_order)

    def set_baudrate(
        self, device_id: int, current_baudrate: int, new_baudrate: int
    ) -> None:
        """Change the baud rate stored on a device.

        Args:
            device_id: Target device ID.
            current_baudrate: Active baud rate used for this transaction.
            new_baudrate: Baud rate to persist on the device.
        """
        assert new_baudrate in BAUDRATE_LOOKUP.values(), (
            f"Invalid baudrate {new_baudrate}; valid: {sorted(BAUDRATE_LOOKUP.values())}"
        )

        self.send(
            command="b",
            data=[device_id, current_baudrate, new_baudrate],
            order="!cHII",
        )

    def set_device_id(self, current_device_id: int, new_device_id: int) -> None:
        """Reassign the Dynamixel ID stored on a device.

        Args:
            current_device_id: Existing device ID used to address the device.
            new_device_id: Replacement ID to persist on the device.
        """
        assert 1 <= new_device_id <= 253, (
            f"Device ID {new_device_id} out of range; must be 1-253"
        )

        self.send(
            command="d",
            data=[current_device_id, new_device_id],
            order="!cHH",
        )

    def set_velocity(self, device_id: int, velocity: int) -> None:
        """Set the velocity limit for a device (0-254)."""
        # TODO: confirm that this is the velocity limit
        assert velocity >= 0 and velocity <= 254, f"Invalid velocity: {velocity}"

        self.send(
            command="v",
            data=[device_id, velocity],
            order="!cHH",
        )

    def _op_mode_str_to_int(self, op_mode: str) -> int:
        """Resolve an operating mode name to its integer code."""
        return OP_MODE_LOOKUP.get(op_mode)

    def _op_mode_int_to_str(self, op_mode: int) -> str:
        """Resolve an operating mode integer code to its name string."""
        return OP_MODE_LOOKUP_TO_STR.get(op_mode)

    def set_operating_mode(self, device_id: int, op_mode: str | int) -> None:
        """Set the operating mode of a device.

        Args:
            device_id: Target device ID.
            op_mode: Mode name (e.g. ``"OP_POSITION"``) or integer code.
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
        """Trigger the LED on a device for visual identification.

        Args:
            device_id: Target device ID.
            duration_ms: On-time of each flash in milliseconds.
            repeats: Number of times to flash.
        """
        assert isinstance(duration_ms, int)
        assert isinstance(repeats, int)

        self.send(
            command="f",
            data=[device_id, duration_ms, repeats],
            order="!cHHH",
        )
