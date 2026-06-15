"""Command-line interface for one-axis-stage: scan, info, move, configure, jog."""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any


def _make_api(port: str, baudrate: int = 115200):
    from one_axis_stage.api import StageAPI

    api = StageAPI(serial_port=port, baudrate=baudrate)
    api.connect()
    return api


# ---------------------------------------------------------------------------
# scan


def cmd_scan(args: argparse.Namespace) -> None:
    """Broadcast a device scan and print discovered IDs."""
    api = _make_api(args.port, args.baudrate)
    try:
        result = api.scan_for_devices()
        if result.strip():
            print(result.strip())
        else:
            print("No devices found.")
    finally:
        api.disconnect()


# ---------------------------------------------------------------------------
# info


def cmd_info(args: argparse.Namespace) -> None:
    """Print status for a single device."""
    api = _make_api(args.port, args.baudrate)
    try:
        info = api.get_info(args.id)
        if not info.get("connected", True):
            print(f"No device responding at ID {args.id}.", file=sys.stderr)
            sys.exit(1)
        if args.json:
            print(json.dumps(info, indent=2))
        else:
            col = max(len(k) for k in info) + 2
            for k, v in info.items():
                print(f"  {k:<{col}}{v}")
    finally:
        api.disconnect()


# ---------------------------------------------------------------------------
# move


def cmd_move(args: argparse.Namespace) -> None:
    """Move a device to an absolute position."""
    api = _make_api(args.port, args.baudrate)
    try:
        api.set_position(args.id, args.position)
        pos = api.get_position(args.id)
        print(f"Position: {pos}")
    finally:
        api.disconnect()


# ---------------------------------------------------------------------------
# set-id


def cmd_set_id(args: argparse.Namespace) -> None:
    """Reassign the device ID stored on a device."""
    api = _make_api(args.port, args.baudrate)
    try:
        api.set_device_id(args.id, args.new_id)
        print(f"ID changed from {args.id} to {args.new_id}.")
        print(f"Reconnect with --id {args.new_id}")
    finally:
        api.disconnect()


# ---------------------------------------------------------------------------
# set-baudrate


def cmd_set_baudrate(args: argparse.Namespace) -> None:
    """Persist a new baud rate on a device."""
    api = _make_api(args.port, args.current_baud)
    try:
        api.set_baudrate(args.id, args.current_baud, args.new_baud)
        print(f"Baudrate changed from {args.current_baud} to {args.new_baud}.")
        print(f"Reconnect with --baudrate {args.new_baud}")
    finally:
        api.disconnect()


# ---------------------------------------------------------------------------
# jog


def cmd_jog(args: argparse.Namespace) -> None:
    """Interactive keyboard jog mode."""
    try:
        import readchar
    except ImportError:
        print(
            "readchar is required for jog mode.\n"
            "Install with: pip install 'one-axis-stage[cli]'",
            file=sys.stderr,
        )
        sys.exit(1)

    if args.config:
        _jog_config_mode(args, readchar)
    else:
        _jog_bare_mode(args, readchar)


def _pos_bar(pos: int, pos_min: int, pos_max: int, width: int = 32) -> str:
    """Return a fixed-width ASCII bar showing position within [pos_min, pos_max]."""
    span = pos_max - pos_min
    ratio = (pos - pos_min) / span if span else 0.0
    ratio = max(0.0, min(1.0, ratio))
    idx = int(ratio * (width - 1))
    return "[" + "-" * idx + "|" + "-" * (width - 1 - idx) + "]"


def _jog_bare_mode(args: argparse.Namespace, readchar) -> None:
    from one_axis_stage.api import StageAPI

    api = StageAPI(serial_port=args.port, baudrate=args.baudrate)
    api.connect()

    ids: list[int] = args.id
    step = args.small
    large = args.large
    pos_min = args.min
    pos_max = args.max

    # Use get_info (JSON, confirmed working) for initial positions; track locally after.
    positions: dict[int, int] = {
        dev_id: api.get_info(dev_id)["position_raw"] for dev_id in ids
    }

    def _clamp(p: int) -> int:
        return max(pos_min, min(pos_max, p))

    def _status() -> str:
        parts = []
        for dev_id in ids:
            bar = _pos_bar(positions[dev_id], pos_min, pos_max)
            parts.append(
                f"id={dev_id} pos={positions[dev_id]:>5}  {pos_min} {bar} {pos_max}"
            )
        sep = "   |   "
        return "\r  " + sep.join(parts) + f"   step={step}   "

    def _move(delta: int) -> None:
        targets = [(dev_id, _clamp(positions[dev_id] + delta)) for dev_id in ids]
        if len(targets) == 1:
            api.set_position(targets[0][0], targets[0][1])
        else:
            api.set_position_multiple(targets)
        for dev_id, new_pos in targets:
            positions[dev_id] = new_pos

    def _refresh() -> None:
        for dev_id in ids:
            info = api.get_info(dev_id)
            positions[dev_id] = info["position_raw"]

    id_str = " ".join(str(i) for i in ids)
    print(f"Jogging id(s) {id_str} on {args.port}")
    print("  right/l +step   left/h -step   up/k +big   down/j -big")
    print("  [ half-step   ] double-step   p refresh from hardware   q quit")
    print(_status(), end="", flush=True)

    try:
        while True:
            key = readchar.readkey()
            if key in (readchar.key.RIGHT, "l"):
                _move(step)
            elif key in (readchar.key.LEFT, "h"):
                _move(-step)
            elif key in (readchar.key.UP, "k"):
                _move(large)
            elif key in (readchar.key.DOWN, "j"):
                _move(-large)
            elif key == "[":
                step = max(1, step // 2)
            elif key == "]":
                step = step * 2
            elif key == "p":
                _refresh()
            elif key in ("q", readchar.key.CTRL_C):
                break
            else:
                continue
            print(_status(), end="", flush=True)
    except KeyboardInterrupt:
        pass
    finally:
        api.disconnect()
        print()


def _jog_config_mode(args: argparse.Namespace, readchar) -> None:
    from one_axis_stage.controller import StageController
    from one_axis_stage.interface import MoveInterface

    controller = StageController.from_config(args.config)
    small = args.small
    large = args.large

    def _make_move() -> MoveInterface:
        return MoveInterface(controller, small_increment=small, large_increment=large)

    move = _make_move()

    axis_names = list(controller.axes.keys())
    print(f"Jogging axes: {axis_names}")
    print("  <axis>p/m +/-step   <axis>P/M +/-big   [ half-step   ] double-step   q quit")
    print("  Example: 'xp' = x forward one step")

    def _status() -> str:
        parts = []
        for name in axis_names:
            ax = controller.axes[name]
            bar = _pos_bar(ax.position_raw, ax.position_min, ax.position_max)
            parts.append(f"{name}={ax.position_raw:>6}  {ax.position_min} {bar} {ax.position_max}")
        return "\r  " + "   |   ".join(parts) + f"   step={small}   "

    # Build dispatch: lowercase p/m = small, uppercase P/M = large
    dispatch: dict[str, Any] = {}
    for name in axis_names:
        dispatch[f"{name}p"] = getattr(move, f"{name}p")
        dispatch[f"{name}m"] = getattr(move, f"{name}m")
        dispatch[f"{name}P"] = getattr(move, f"{name}pp")
        dispatch[f"{name}M"] = getattr(move, f"{name}mm")

    buf = ""
    try:
        while True:
            key = readchar.readkey()
            if key in ("q", readchar.key.CTRL_C):
                break
            if key == "[":
                small = max(1, small // 2)
                move = _make_move()
                dispatch.update({
                    f"{n}{s}": getattr(move, f"{n}{s}")
                    for n in axis_names for s in ("p", "m", "pp", "mm")
                })
                print(_status(), end="", flush=True)
                continue
            if key == "]":
                small = small * 2
                move = _make_move()
                dispatch.update({
                    f"{n}{s}": getattr(move, f"{n}{s}")
                    for n in axis_names for s in ("p", "m", "pp", "mm")
                })
                print(_status(), end="", flush=True)
                continue
            buf += key
            # Try longest match first, then single char
            matched = None
            for seq in sorted(dispatch, key=len, reverse=True):
                if buf.endswith(seq):
                    matched = seq
                    break
            if matched:
                dispatch[matched]()
                buf = ""
                print(_status(), end="", flush=True)
    except KeyboardInterrupt:
        pass
    finally:
        controller.api.disconnect()
        print()


# ---------------------------------------------------------------------------
# Parser


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="stage",
        description="Control one-axis Dynamixel stages from the command line.",
    )
    sub = parser.add_subparsers(dest="command", metavar="COMMAND")
    sub.required = True

    # --- scan ---
    p_scan = sub.add_parser("scan", help="Scan bus for device IDs.")
    p_scan.add_argument(
        "--port", required=True, help="Serial port (e.g. /dev/ttyUSB0)."
    )
    p_scan.add_argument("--baudrate", type=int, default=115200)
    p_scan.set_defaults(func=cmd_scan)

    # --- info ---
    p_info = sub.add_parser("info", help="Print status for a device.")
    p_info.add_argument("--port", required=True)
    p_info.add_argument("--id", type=int, required=True, help="Device ID.")
    p_info.add_argument("--baudrate", type=int, default=115200)
    p_info.add_argument("--json", action="store_true", help="Output raw JSON.")
    p_info.set_defaults(func=cmd_info)

    # --- move ---
    p_move = sub.add_parser("move", help="Move device to an absolute position.")
    p_move.add_argument("--port", required=True)
    p_move.add_argument("--id", type=int, required=True)
    p_move.add_argument(
        "--position", type=int, required=True, help="Target position (raw units)."
    )
    p_move.add_argument("--baudrate", type=int, default=115200)
    p_move.set_defaults(func=cmd_move)

    # --- set-id ---
    p_sid = sub.add_parser("set-id", help="Reassign a device ID.")
    p_sid.add_argument("--port", required=True)
    p_sid.add_argument("--id", type=int, required=True, help="Current device ID.")
    p_sid.add_argument(
        "--new-id",
        type=int,
        required=True,
        dest="new_id",
        help="New device ID (1-253).",
    )
    p_sid.add_argument("--baudrate", type=int, default=115200)
    p_sid.set_defaults(func=cmd_set_id)

    # --- set-baudrate ---
    p_sb = sub.add_parser("set-baudrate", help="Change baud rate stored on a device.")
    p_sb.add_argument("--port", required=True)
    p_sb.add_argument("--id", type=int, required=True)
    p_sb.add_argument("--current-baud", type=int, required=True, dest="current_baud")
    p_sb.add_argument("--new-baud", type=int, required=True, dest="new_baud")
    p_sb.set_defaults(func=cmd_set_baudrate)

    # --- jog ---
    p_jog = sub.add_parser("jog", help="Interactive keyboard jog mode.")
    p_jog.add_argument("--port", help="Serial port. Required without --config.")
    p_jog.add_argument(
        "--id",
        type=int,
        nargs="+",
        help="Device ID(s). Multiple IDs move together. Required without --config.",
    )
    p_jog.add_argument("--baudrate", type=int, default=115200)
    p_jog.add_argument(
        "--config", help="Path to StageController YAML for multi-axis jog."
    )
    p_jog.add_argument(
        "--small", type=int, default=20, help="Small step size (default 20)."
    )
    p_jog.add_argument(
        "--large", type=int, default=40, help="Large step size (default 40)."
    )
    p_jog.add_argument(
        "--min", type=int, default=0, dest="min", help="Soft lower limit (default 0)."
    )
    p_jog.add_argument(
        "--max",
        type=int,
        default=1023,
        dest="max",
        help="Soft upper limit (default 1023).",
    )
    p_jog.set_defaults(func=cmd_jog)

    return parser


def main() -> None:
    parser = _build_parser()
    args = parser.parse_args()

    # Validate jog bare-mode requirements
    if args.command == "jog" and not args.config and (not args.port or args.id is None):
        parser.error("jog requires --port and --id when --config is not given.")

    args.func(args)


if __name__ == "__main__":
    main()
