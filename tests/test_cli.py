"""CLI smoke tests: parser structure and argument validation (no hardware)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from one_axis_stage.cli import _build_parser, cmd_info


def test_parser_help_does_not_raise():
    parser = _build_parser()
    assert parser is not None


def test_scan_requires_port():
    parser = _build_parser()
    with pytest.raises(SystemExit):
        parser.parse_args(["scan"])


def test_scan_parses_port():
    parser = _build_parser()
    args = parser.parse_args(["scan", "--port", "/dev/ttyUSB0"])
    assert args.port == "/dev/ttyUSB0"
    assert args.baudrate == 115200


def test_scan_accepts_baudrate():
    parser = _build_parser()
    args = parser.parse_args(["scan", "--port", "/dev/ttyUSB0", "--baudrate", "9600"])
    assert args.baudrate == 9600


def test_info_requires_port_and_id():
    parser = _build_parser()
    with pytest.raises(SystemExit):
        parser.parse_args(["info", "--port", "/dev/ttyUSB0"])
    with pytest.raises(SystemExit):
        parser.parse_args(["info", "--id", "21"])


def test_info_parses_args():
    parser = _build_parser()
    args = parser.parse_args(["info", "--port", "/dev/ttyUSB0", "--id", "21"])
    assert args.id == 21
    assert args.json is False


def test_info_json_flag():
    parser = _build_parser()
    args = parser.parse_args(["info", "--port", "/dev/ttyUSB0", "--id", "21", "--json"])
    assert args.json is True


def test_move_requires_position():
    parser = _build_parser()
    with pytest.raises(SystemExit):
        parser.parse_args(["move", "--port", "/dev/ttyUSB0", "--id", "21"])


def test_move_parses_args():
    parser = _build_parser()
    args = parser.parse_args(
        ["move", "--port", "/dev/ttyUSB0", "--id", "21", "--position", "400"]
    )
    assert args.position == 400


def test_set_id_parses_args():
    parser = _build_parser()
    args = parser.parse_args(
        ["set-id", "--port", "/dev/ttyUSB0", "--id", "21", "--new-id", "22"]
    )
    assert args.id == 21
    assert args.new_id == 22


def test_set_baudrate_parses_args():
    parser = _build_parser()
    args = parser.parse_args(
        [
            "set-baudrate",
            "--port",
            "/dev/ttyUSB0",
            "--id",
            "21",
            "--current-baud",
            "115200",
            "--new-baud",
            "57600",
        ]
    )
    assert args.current_baud == 115200
    assert args.new_baud == 57600


def test_jog_defaults():
    parser = _build_parser()
    args = parser.parse_args(["jog", "--port", "/dev/ttyUSB0", "--id", "21"])
    assert args.small == 20
    assert args.large == 40
    assert args.min == 0
    assert args.max == 65535
    assert args.config is None


def test_jog_custom_steps():
    parser = _build_parser()
    args = parser.parse_args(
        ["jog", "--port", "/dev/ttyUSB0", "--id", "21", "--small", "5", "--large", "50"]
    )
    assert args.small == 5
    assert args.large == 50


def test_jog_config_mode():
    parser = _build_parser()
    args = parser.parse_args(["jog", "--config", "stage.yaml"])
    assert args.config == "stage.yaml"


def test_unknown_subcommand_exits():
    parser = _build_parser()
    with pytest.raises(SystemExit):
        parser.parse_args(["notacommand"])


# ---------------------------------------------------------------------------
# cmd_info: connected flag


def test_cmd_info_exits_when_not_connected(capsys):
    """cmd_info must exit(1) when api.get_info returns connected=False."""
    parser = _build_parser()
    args = parser.parse_args(["info", "--port", "/dev/ttyUSB0", "--id", "20"])

    mock_api = MagicMock()
    mock_api.get_info.return_value = {
        "connected": False,
        "model_number": 65535,
        "id": 20,
    }

    with (
        patch("one_axis_stage.cli._make_api", return_value=mock_api),
        pytest.raises(SystemExit) as exc_info,
    ):
        cmd_info(args)

    assert exc_info.value.code == 1
    captured = capsys.readouterr()
    assert "No device" in captured.err


def test_cmd_info_prints_when_connected(capsys):
    """cmd_info must print fields when api.get_info returns connected=True."""
    parser = _build_parser()
    args = parser.parse_args(["info", "--port", "/dev/ttyUSB0", "--id", "21"])

    mock_api = MagicMock()
    mock_api.get_info.return_value = {
        "connected": True,
        "model_number": 1060,
        "id": 21,
        "baud_rate": "115200",
        "baud_rate_int": 3,
        "operating_mode": "position",
        "operating_mode_int": 3,
    }

    with patch("one_axis_stage.cli._make_api", return_value=mock_api):
        cmd_info(args)

    captured = capsys.readouterr()
    assert "model_number" in captured.out
    assert "1060" in captured.out
