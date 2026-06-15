"""Simulate jog bare mode: mock API + readchar, verify position tracking and display."""

from __future__ import annotations

import argparse
from unittest.mock import MagicMock, call, patch

from one_axis_stage.cli import _jog_bare_mode, _pos_bar


def _readchar_mock(keys: list[str]) -> MagicMock:
    rc = MagicMock()
    rc.readkey.side_effect = keys + ["q"]
    rc.key.RIGHT = "\x1b[C"
    rc.key.LEFT = "\x1b[D"
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


def _args(ids, small=20, large=40, pos_min=0, pos_max=1023, port="/dev/ttyUSB0"):
    return argparse.Namespace(
        id=ids, small=small, large=large,
        min=pos_min, max=pos_max,
        port=port, baudrate=115200,
    )


# ---------------------------------------------------------------------------
# _pos_bar unit tests


def test_pos_bar_at_min():
    bar = _pos_bar(0, 0, 1023)
    assert bar.startswith("[|")


def test_pos_bar_at_max():
    bar = _pos_bar(1023, 0, 1023)
    assert bar.endswith("|]")


def test_pos_bar_midpoint():
    bar = _pos_bar(512, 0, 1023, width=10)
    # marker should be roughly in the middle
    idx = bar.index("|")
    assert 3 <= idx <= 7


def test_pos_bar_clamped_above():
    bar_max = _pos_bar(1023, 0, 1023)
    bar_over = _pos_bar(2000, 0, 1023)
    assert bar_max == bar_over


def test_pos_bar_clamped_below():
    bar_min = _pos_bar(0, 0, 1023)
    bar_under = _pos_bar(-100, 0, 1023)
    assert bar_min == bar_under


# ---------------------------------------------------------------------------
# single-axis jog simulation


def test_single_axis_move_right(capsys):
    api = _api_mock({21: 500})
    rc = _readchar_mock(["l"])  # right/l = +step, then q

    with patch("one_axis_stage.cli._make_api", return_value=api):
        pass  # _jog_bare_mode creates its own api - patch StageAPI instead

    with patch("one_axis_stage.api.StageAPI") as mock_cls:
        mock_cls.return_value = api
        _jog_bare_mode(_args([21]), rc)

    api.set_position.assert_called_once_with(21, 520)


def test_single_axis_move_left(capsys):
    api = _api_mock({21: 500})
    rc = _readchar_mock(["h"])

    with patch("one_axis_stage.api.StageAPI") as mock_cls:
        mock_cls.return_value = api
        _jog_bare_mode(_args([21]), rc)

    api.set_position.assert_called_once_with(21, 480)


def test_single_axis_clamps_at_min(capsys):
    api = _api_mock({21: 10})
    rc = _readchar_mock(["h"])  # -20 would go to -10, clamp to 0

    with patch("one_axis_stage.api.StageAPI") as mock_cls:
        mock_cls.return_value = api
        _jog_bare_mode(_args([21]), rc)

    api.set_position.assert_called_once_with(21, 0)


def test_single_axis_clamps_at_max(capsys):
    api = _api_mock({21: 1020})
    rc = _readchar_mock(["l"])  # +20 would go to 1040, clamp to 1023

    with patch("one_axis_stage.api.StageAPI") as mock_cls:
        mock_cls.return_value = api
        _jog_bare_mode(_args([21]), rc)

    api.set_position.assert_called_once_with(21, 1023)


def test_step_halve_and_double(capsys):
    api = _api_mock({21: 500})
    # halve: step 20->10, then move right (+10), double: step 10->20, move right (+20)
    rc = _readchar_mock(["[", "l", "]", "l"])

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
# multi-axis jog simulation


def test_multi_axis_moves_all_together(capsys):
    api = _api_mock({21: 500, 22: 300})
    rc = _readchar_mock(["l"])

    with patch("one_axis_stage.api.StageAPI") as mock_cls:
        mock_cls.return_value = api
        _jog_bare_mode(_args([21, 22]), rc)

    api.set_position_multiple.assert_called_once_with([(21, 520), (22, 320)])


def test_multi_axis_clamps_independently(capsys):
    # id 21 at 1010, id 22 at 500 - +20 clamps 21 to 1023 but moves 22 to 520
    api = _api_mock({21: 1010, 22: 500})
    rc = _readchar_mock(["l"])

    with patch("one_axis_stage.api.StageAPI") as mock_cls:
        mock_cls.return_value = api
        _jog_bare_mode(_args([21, 22]), rc)

    api.set_position_multiple.assert_called_once_with([(21, 1023), (22, 520)])


def test_multi_axis_status_line_shows_all_ids(capsys):
    api = _api_mock({21: 500, 22: 300})
    rc = _readchar_mock([])  # just q immediately

    with patch("one_axis_stage.api.StageAPI") as mock_cls:
        mock_cls.return_value = api
        _jog_bare_mode(_args([21, 22]), rc)

    out = capsys.readouterr().out
    assert "id=21" in out
    assert "id=22" in out
