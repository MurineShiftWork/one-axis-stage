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


def _jog_bare_mode(args: argparse.Namespace, readchar) -> None:
    from one_axis_stage.api import StageAPI

    api = StageAPI(serial_port=args.port, baudrate=args.baudrate)
    api.connect()

    pos = api.get_position(args.id)
    small = args.small
    large = args.large
    pos_min = args.min
    pos_max = args.max

    print(f"Jogging device {args.id} on {args.port}")
    print(f"Position: {pos}  |  range: {pos_min}-{pos_max}  |  steps: {small}/{large}")
    print(
        "Keys: right/l=+small  left/h=-small  up/k=+large  down/j=-large  p=print  q=quit"
    )

    try:
        while True:
            key = readchar.readkey()
            delta = None
            if key in (readchar.key.RIGHT, "l"):
                delta = small
            elif key in (readchar.key.LEFT, "h"):
                delta = -small
            elif key in (readchar.key.UP, "k"):
                delta = large
            elif key in (readchar.key.DOWN, "j"):
                delta = -large
            elif key == "p":
                pos = api.get_position(args.id)
                print(f"Position: {pos}")
                continue
            elif key in ("q", readchar.key.CTRL_C):
                break

            if delta is not None:
                new_pos = max(pos_min, min(pos_max, pos + delta))
                api.set_position(args.id, new_pos)
                pos = api.get_position(args.id)
                print(f"\rPosition: {pos}  ", end="", flush=True)
    except KeyboardInterrupt:
        pass
    finally:
        api.disconnect()
        print()


def _jog_config_mode(args: argparse.Namespace, readchar) -> None:
    from one_axis_stage.controller import StageController
    from one_axis_stage.interface import MoveInterface

    controller = StageController.from_config(args.config)
    move = MoveInterface(
        controller,
        small_increment=args.small,
        large_increment=args.large,
    )

    axis_names = list(controller.axes.keys())
    print(f"Jogging axes: {axis_names}")
    print("Keys per axis: <axis>p/m = small +/-   <axis>P/M = large +/-   q = quit")
    print("Example: 'xp' moves x forward one small step")

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
                # Print current positions
                positions = {n: controller.axes[n].position_raw for n in axis_names}
                print(f"\r{positions}  ", end="", flush=True)
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
    p_jog.add_argument("--id", type=int, help="Device ID. Required without --config.")
    p_jog.add_argument("--baudrate", type=int, default=115200)
    p_jog.add_argument(
        "--config", help="Path to StageController YAML for multi-axis jog."
    )
    p_jog.add_argument(
        "--small", type=int, default=20, help="Small step size (default 20)."
    )
    p_jog.add_argument(
        "--large", type=int, default=200, help="Large step size (default 200)."
    )
    p_jog.add_argument(
        "--min", type=int, default=0, dest="min", help="Soft lower limit (default 0)."
    )
    p_jog.add_argument(
        "--max",
        type=int,
        default=65535,
        dest="max",
        help="Soft upper limit (default 65535).",
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
