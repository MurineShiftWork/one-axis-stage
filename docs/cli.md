# CLI reference

Installing `one-axis-stage` registers the `stage` command.

For interactive jog mode also install the `cli` extra:

```bash
pip install "one-axis-stage[cli]"
```

---

## stage scan

Broadcast a scan and print discovered device IDs.

```
stage scan --port PORT [--baudrate BAUD]
```

| Flag | Default | Description |
|---|---|---|
| `--port` | required | Serial port (e.g. `/dev/ttyUSB0`, `COM3`). |
| `--baudrate` | `115200` | Connection baud rate. |

**Example:**

```bash
stage scan --port /dev/ttyUSB0
```

---

## stage info

Print status (baud rate, operating mode, position) for a single device.

```
stage info --port PORT --id ID [--baudrate BAUD] [--json]
```

| Flag | Default | Description |
|---|---|---|
| `--port` | required | Serial port. |
| `--id` | required | Device ID (integer). |
| `--baudrate` | `115200` | Connection baud rate. |
| `--json` | off | Emit raw JSON instead of formatted table. |

**Example:**

```bash
stage info --port /dev/ttyUSB0 --id 21
stage info --port /dev/ttyUSB0 --id 21 --json
```

!!! note
    If no device responds at the given ID, the command prints an error to stderr
    and exits with code 1.  Use `stage scan` first to confirm which IDs are
    present on the bus.

---

## stage move

Move a device to an absolute raw position, then print the confirmed position.

```
stage move --port PORT --id ID --position POS [--baudrate BAUD]
```

| Flag | Default | Description |
|---|---|---|
| `--port` | required | Serial port. |
| `--id` | required | Device ID. |
| `--position` | required | Target position (raw units, integer). |
| `--baudrate` | `115200` | Connection baud rate. |

!!! note
    No soft limits are enforced here. Confirm the valid range with
    `stage info` before moving to an untested position.

**Example:**

```bash
stage move --port /dev/ttyUSB0 --id 21 --position 400
```

---

## stage set-id

Reassign the device ID stored on a device.

```
stage set-id --port PORT --id CURRENT_ID --new-id NEW_ID [--baudrate BAUD]
```

!!! warning
    After this command the device responds only on the new ID.
    Reconnect with `--id NEW_ID`.

---

## stage set-baudrate

Change the baud rate persisted on a device.

```
stage set-baudrate --port PORT --id ID --current-baud CUR --new-baud NEW
```

Valid baud rates: `9600`, `57600`, `115200`, `1000000`.

!!! warning
    After this command the device responds only on the new baud rate.
    Reconnect with `--baudrate NEW`.

---

## stage jog

Interactive keyboard jog mode. Requires `pip install "one-axis-stage[cli]"`.

```
stage jog --port PORT --id ID [--baudrate BAUD]
          [--small STEP] [--large STEP] [--min MIN] [--max MAX]

stage jog --config CONFIG_YAML [--small STEP] [--large STEP]
```

Two launch modes:

**Bare mode** (`--port` + `--id`): quick single-device jog with optional soft limits.

**Config mode** (`--config`): load a `StageController` YAML for named multi-axis jog.

### Keyboard map - bare mode

| Key | Action |
|---|---|
| Right arrow / `l` | Step forward |
| Left arrow / `h` | Step backward |
| Up arrow / `k` | Big step forward |
| Down arrow / `j` | Big step backward |
| `[` | Halve step size |
| `]` | Double step size |
| `p` | Refresh position |
| `q` / Ctrl-C | Quit |

The status line updates after every move:

```
pos=   599  step=20   0 [--------|-----------------------] 65535
```

### Keyboard map - config mode (multi-axis)

Keys are generated per axis name. With axes `x` and `y`:

| Key | Action |
|---|---|
| `xp` | x step forward |
| `xm` | x step backward |
| `xP` | x big step forward |
| `xM` | x big step backward |
| `[` | Halve step size |
| `]` | Double step size |
| `q` / Ctrl-C | Quit |

Per-axis bars are shown after each move:

```
x=   599  0 [-----|--------------------------] 65535   |   y=   300  0 [---|----------------------------] 65535   step=20
```

### Flags

| Flag | Default | Description |
|---|---|---|
| `--port` | required (bare) | Serial port. |
| `--id` | required (bare) | Device ID. |
| `--baudrate` | `115200` | Connection baud rate. |
| `--config` | — | Path to StageController YAML (multi-axis mode). |
| `--small` | `20` | Small step size (raw units). |
| `--large` | `40` | Large step size (raw units). |
| `--min` | `0` | Soft lower position limit (bare mode). |
| `--max` | `65535` | Soft upper position limit (bare mode). |
