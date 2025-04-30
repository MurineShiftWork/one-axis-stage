__author__ = "Lars B. Rollik"

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("subject_weight_db")
except PackageNotFoundError:
    __version__ = "0.0.1"


OP_MODE_LOOKUP_TO_STR = {
    0: "OP_POSITION",
    1: "OP_EXTENDED_POSITION",
    2: "OP_CURRENT_BASED_POSITION",
    3: "OP_VELOCITY",
    4: "OP_PWM",
    5: "OP_CURRENT",
}
OP_MODE_LOOKUP = {v: k for k, v in OP_MODE_LOOKUP_TO_STR.items()}
BAUDRATE_LOOKUP = {0: 9600, 1: 57600, 2: 115200, 3: 1000000}
