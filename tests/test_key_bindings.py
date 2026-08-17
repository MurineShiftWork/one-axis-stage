"""Unit tests for jog key-binding parsing + dispatch (no hardware, no live readchar)."""

from __future__ import annotations

import types

import pytest

from one_axis_stage.cli import _jog_apply_key, _parse_key_bindings


def _rc():
    """A minimal readchar stand-in exposing the arrow-key codes the parser reads."""
    key = types.SimpleNamespace(
        UP="\x1b[A", DOWN="\x1b[B", LEFT="\x1b[D", RIGHT="\x1b[C"
    )
    return types.SimpleNamespace(key=key)


# --- default (backward compatible) ----------------------------------------------------------------
def test_default_is_ws_da_arrows_for_three_axes():
    # Historical directions preserved: w/d/Up are +, s/a/Down are - (so axis 1 is ("d", "a")).
    rc = _rc()
    assert _parse_key_bindings(None, 3, rc) == {
        0: ("w", "s"),
        1: ("d", "a"),
        2: (rc.key.UP, rc.key.DOWN),
    }


def test_default_clamps_to_available_axes():
    rc = _rc()
    assert set(_parse_key_bindings(None, 2, rc)) == {0, 1}
    assert set(_parse_key_bindings(None, 1, rc)) == {0}


def test_default_beyond_three_axes_only_binds_first_three():
    rc = _rc()
    # The historical default leaves a 4th/5th axis unreachable (that is the bug --keys fixes).
    assert set(_parse_key_bindings(None, 5, rc)) == {0, 1, 2}


# --- custom --keys --------------------------------------------------------------------------------
def test_shorthand_pairs():
    rc = _rc()
    assert _parse_key_bindings("ws,ad,uj,kl", 4, rc) == {
        0: ("w", "s"),
        1: ("a", "d"),
        2: ("u", "j"),
        3: ("k", "l"),
    }


def test_arrow_names_resolve_to_codes():
    rc = _rc()
    assert _parse_key_bindings("up/down,left/right", 2, rc) == {
        0: (rc.key.UP, rc.key.DOWN),
        1: (rc.key.LEFT, rc.key.RIGHT),
    }


def test_space_separator_and_case_insensitive():
    rc = _rc()
    assert _parse_key_bindings("W S,A D", 2, rc) == {0: ("w", "s"), 1: ("a", "d")}


def test_bindings_beyond_num_axes_are_ignored():
    rc = _rc()
    assert set(_parse_key_bindings("ws,ad,uj", 2, rc)) == {0, 1}


def test_malformed_pair_raises():
    rc = _rc()
    with pytest.raises(ValueError, match="key pair"):
        _parse_key_bindings("wsa", 1, rc)  # three chars, no separator


# --- dispatch -------------------------------------------------------------------------------------
def test_apply_key_moves_bound_axis():
    moves: list[tuple[int, int]] = []
    bindings = {0: ("w", "s"), 1: ("k", "j")}
    assert _jog_apply_key("w", bindings, lambda i, d: moves.append((i, d))) is True  # +
    assert _jog_apply_key("j", bindings, lambda i, d: moves.append((i, d))) is True  # -
    assert moves == [(0, +1), (1, -1)]


def test_apply_key_false_for_unbound_key():
    assert _jog_apply_key("x", {0: ("w", "s")}, lambda i, d: None) is False


def test_custom_keys_reach_fourth_axis():
    # The core of issue #11: a 4th axis is reachable once keys are bound to it.
    rc = _rc()
    bindings = _parse_key_bindings("ws,ad,up/down,uj", 4, rc)
    moves: list[tuple[int, int]] = []
    assert _jog_apply_key("u", bindings, lambda i, d: moves.append((i, d))) is True
    assert _jog_apply_key("j", bindings, lambda i, d: moves.append((i, d))) is True
    assert moves == [(3, +1), (3, -1)]
