import sys


def test_python_version() -> None:
    assert sys.version_info >= (3, 10), "Python version must be 3.10 or higher"


def test_import() -> None:
    import one_axis_stage

    assert one_axis_stage.__version__ is not None
