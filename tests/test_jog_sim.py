"""Simulate jog bare mode: mock API + readchar, verify position tracking and display."""

from __future__ import annotations

import argparse
from unittest.mock import MagicMock, call, patch

from one_axis_stage.cli import _jog_bare_mode, _pos_bar


def _readchar_mock(keys: list[str]) -> MagicMock:
    rc = MagicMock()
    rc.readkey.side_effect = keys + ["q"]
    rc.key.UP = "\x1b[A"
    rc.key.DOWN = "\x1b[B"
    rc.key.CTRL_C = "\x03"
    return rc


def _api_mock(initial_positions: dict[int, int]) -> MagicMock:
    api = MagicMock()
    api.get_info.side_effect = lambda dev_id: {
        "connected": True,
        "position_raw": initial_positions[dev_id],
    }
    return api


def _args(ids, small=20, pos_min=0, pos_max=1023, port="/dev/ttyUSB0"):
    return argparse.Namespace(
        id=ids,
        small=small,
        min=pos_min,
        max=pos_max,
        port=port,
        baudrate=115200,
    )


# ---------------------------------------------------------------------------
# _pos_bar unit tests


def test_pos_bar_at_min():
    assert _pos_bar(0, 0, 1023).startswith("[|")


def test_pos_bar_at_max():
    assert _pos_bar(1023, 0, 1023).endswith("|]")


def test_pos_bar_midpoint():
    bar = _pos_bar(512, 0, 1023, width=10)
    idx = bar.index("|")
    assert 3 <= idx <= 7


def test_pos_bar_clamped_above():
    assert _pos_bar(2000, 0, 1023) == _pos_bar(1023, 0, 1023)


def test_pos_bar_clamped_below():
    assert _pos_bar(-100, 0, 1023) == _pos_bar(0, 0, 1023)


# ---------------------------------------------------------------------------
# single-axis jog simulation


def test_single_axis_move_forward_w(capsys):
    api = _api_mock({21: 500})
    rc = _readchar_mock(["w"])

    with patch("one_axis_stage.api.StageAPI") as mock_cls:
        mock_cls.return_value = api
        _jog_bare_mode(_args([21]), rc)

    api.set_position.assert_called_once_with(21, 520)


def test_single_axis_move_back_s(capsys):
    api = _api_mock({21: 500})
    rc = _readchar_mock(["s"])

    with patch("one_axis_stage.api.StageAPI") as mock_cls:
        mock_cls.return_value = api
        _jog_bare_mode(_args([21]), rc)

    api.set_position.assert_called_once_with(21, 480)


def test_single_axis_clamps_at_min(capsys):
    api = _api_mock({21: 10})
    rc = _readchar_mock(["s"])  # -20 from 10 → clamp to 0

    with patch("one_axis_stage.api.StageAPI") as mock_cls:
        mock_cls.return_value = api
        _jog_bare_mode(_args([21]), rc)

    api.set_position.assert_called_once_with(21, 0)


def test_single_axis_clamps_at_max(capsys):
    api = _api_mock({21: 1020})
    rc = _readchar_mock(["w"])  # +20 from 1020 → clamp to 1023

    with patch("one_axis_stage.api.StageAPI") as mock_cls:
        mock_cls.return_value = api
        _jog_bare_mode(_args([21]), rc)

    api.set_position.assert_called_once_with(21, 1023)


def test_step_decrease_and_increase(capsys):
    api = _api_mock({21: 500})
    # halve: step 20->10, move w (+10), double: step 10->20, move w (+20)
    rc = _readchar_mock(["-", "w", "+", "w"])

    with patch("one_axis_stage.api.StageAPI") as mock_cls:
        mock_cls.return_value = api
        _jog_bare_mode(_args([21]), rc)

    calls = api.set_position.call_args_list
    assert calls[0] == call(21, 510)  # +10 after halve
    assert calls[1] == call(21, 530)  # +20 after double (pos now 510)


def test_refresh_calls_get_info(capsys):
    api = _api_mock({21: 500})
    rc = _readchar_mock(["p"])

    with patch("one_axis_stage.api.StageAPI") as mock_cls:
        mock_cls.return_value = api
        _jog_bare_mode(_args([21]), rc)

    # get_info called once for init, once for p refresh
    assert api.get_info.call_count == 2


# ---------------------------------------------------------------------------
# multi-axis jog simulation: each key group controls its own axis


def test_second_axis_moves_on_d(capsys):
    api = _api_mock({21: 500, 22: 300})
    rc = _readchar_mock(["d"])  # A/D → ids[1] = 22

    with patch("one_axis_stage.api.StageAPI") as mock_cls:
        mock_cls.return_value = api
        _jog_bare_mode(_args([21, 22]), rc)

    # Only id 22 should move; id 21 untouched
    api.set_position.assert_called_once_with(22, 320)


def test_second_axis_moves_on_a(capsys):
    api = _api_mock({21: 500, 22: 300})
    rc = _readchar_mock(["a"])  # A/D → ids[1] = 22, direction -1

    with patch("one_axis_stage.api.StageAPI") as mock_cls:
        mock_cls.return_value = api
        _jog_bare_mode(_args([21, 22]), rc)

    api.set_position.assert_called_once_with(22, 280)


def test_third_axis_moves_on_up(capsys):
    api = _api_mock({21: 500, 22: 300, 23: 100})
    rc = _readchar_mock(["\x1b[A"])  # UP → ids[2] = 23

    with patch("one_axis_stage.api.StageAPI") as mock_cls:
        mock_cls.return_value = api
        _jog_bare_mode(_args([21, 22, 23]), rc)

    api.set_position.assert_called_once_with(23, 120)


def test_no_move_when_key_out_of_range(capsys):
    # Only 1 axis but 'd' pressed (would be ids[1] which doesn't exist)
    api = _api_mock({21: 500})
    rc = _readchar_mock(["d"])

    with patch("one_axis_stage.api.StageAPI") as mock_cls:
        mock_cls.return_value = api
        _jog_bare_mode(_args([21]), rc)

    api.set_position.assert_not_called()


def test_status_line_labels_axes(capsys):
    api = _api_mock({21: 500, 22: 300})
    rc = _readchar_mock([])  # just q

    with patch("one_axis_stage.api.StageAPI") as mock_cls:
        mock_cls.return_value = api
        _jog_bare_mode(_args([21, 22]), rc)

    out = capsys.readouterr().out
    assert "y(id=21)" in out
    assert "x(id=22)" in out
