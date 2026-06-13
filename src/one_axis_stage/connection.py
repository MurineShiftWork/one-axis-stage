"""Low-level serial connection to the stage controller firmware."""

import logging
import struct
from typing import Any

from serial import Serial


class StageSerialConnection:
    """Manages an RS-232/USB serial link to a stage controller.

    Handles framing (start/stop bytes), struct encoding, and raw I/O.
    Not intended to be used directly - use StageAPI instead.
    """

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
        """Return connection parameters as a dictionary."""
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
        """True if the serial port is currently open."""
        if self.connection is not None:
            return self.connection.is_open
        else:
            return False

    def connect(self) -> "StageSerialConnection":
        """Open the serial port and flush any stale data in the buffer."""
        if not self.connected:
            self.connection = Serial(
                port=self.serial_port,
                baudrate=self.baudrate,
                timeout=self.timeout,
            )
            # is open?
            if self.connection.is_open:
                logging.info(
                    f"Connected to {self.serial_port} at {self.baudrate} baud."
                )
            else:
                logging.error(f"Failed to open serial port {self.serial_port}.")

        # clear buffer
        self.connection.read(self.connection.in_waiting)

        return self

    def disconnect(self) -> None:
        """Close the serial port."""
        if self.connection is not None:
            self.connection.close()
            self.connection = None
            logging.info(f"Disconnected from {self.serial_port}.")

    def _encode(self, data: Any, order: str) -> bytes:
        """Pack data as a framed byte struct flanked by start/stop bytes (`<`/`>`)."""
        # check that data is list
        if not isinstance(data, list):
            data = [data]

        # encode str to bytes
        data_encoded = [
            item.encode() if isinstance(item, str) else item for item in data
        ]

        # pack the data
        data_packed = struct.pack(order, *data_encoded)

        # flank the packed data with start/stop bytes </>
        message = b"<" + data_packed + b">"

        logging.debug(f"Encoded message: '{str(message)}'")
        return message

    def _clear_buffer(self):
        """Discard any unread bytes waiting in the receive buffer."""
        self.connection.read(self.connection.in_waiting)
        return not self.connection.in_waiting

    def send(self, command: str, data: Any = None, order: str = None) -> None:
        """Encode and transmit a command packet over the serial link."""
        assert isinstance(command, str)
        assert isinstance(data, list | int | str | type(None))
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
            self._clear_buffer()
            self.connection.write(data_to_send)
            self.connection.flush()
            logging.debug(f"Sent data: {data_to_send}")

    def read_bytes(
        self, n_bytes: int = None, unpack_order: str = None
    ) -> tuple[Any, ...]:
        """Read and unpack a fixed number of bytes from the serial port.

        Args:
            n_bytes: Number of bytes to read.
            unpack_order: `struct` format string used to unpack the raw bytes.

        Returns:
            Tuple of unpacked values.

        Raises:
            ValueError: If fewer than `n_bytes` bytes are received.
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
        """Read one newline-terminated line from the serial port and return it as a string."""
        line = self.connection.readline().decode("utf-8").strip()
        logging.debug(f"Received line: {line}")
        return line
