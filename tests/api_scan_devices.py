import logging

from one_axis_stage.api import StageAPI

if __name__ == "__main__":
    # logging
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)

    # Open the serial connection
    api = StageAPI(serial_port="/dev/ttyUSB0", baudrate=115200)
    api.connect()

    pos = api.get_position(device_id=21)
    api.set_position(device_id=21, position=600)
    api.set_position(device_id=21, position=100)

    info = api.get_info(device_id=21)
    info_all = api.get_info_all(
        device_ids=[
            21,
        ]
    )
    api.scan_for_devices()

    print("EXIT")

    info_all = []
    for i in range(5):
        info = api.get_info(device_id=21)
        info_all.append(info)
