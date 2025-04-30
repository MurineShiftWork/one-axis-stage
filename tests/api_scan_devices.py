import logging

from one_axis_stage.api import StageAPI

if __name__ == "__main__":
    # logging
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)

    # Open the serial connection
    api = StageAPI(serial_port="/dev/ttyUSB0", baudrate=115200)
    api.connect()

    pos = api.get_position(device_id=11)
    api.set_position(device_id=11, position=600)
    pos = api.get_position(device_id=11)
    api.set_position(device_id=21, position=100)
    pos = api.get_position(device_id=11)

    # TODO: set position multiple
    # TODO: set baudrate
    # TODO: set new id
    # TODO: set velocity
    # TODO: set operating mode
    # TODO: flash

    info = api.get_info(device_id=21)
    info_all = api.get_info_all(device_ids=[21, 55, 67])
    info_all = api.get_info_all(device_ids=[11, 12, 13])
    api.scan_for_devices()

    api.flash(device_id=55, duration_ms=1000, repeats=5)
    api.set_baudrate(73, 1000000, 115200)

    api.set_velocity(device_id=21, velocity=0)
    # api.set_operating_mode(device_id=21, op_mode="OP_VELOCITY") # FIXME

    api.set_device_id(current_device_id=1, new_device_id=67)

    print("EXIT")

    info_all = []
    for i in range(5):
        info = api.get_info(device_id=21)
        info_all.append(info)
