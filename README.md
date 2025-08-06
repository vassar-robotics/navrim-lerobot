# Robot Position Reader (Minimal)

A minimal script to read and display joint positions from SO101 robot in real-time.

## Requirements

- Python 3.x
- pyserial: `pip install pyserial`
- scservo_sdk (included in the `scservo_sdk/` directory)

## Scripts

### read_leader_positions.py
Continuously reads and displays joint positions from the robot at 30 Hz.

```bash
# Auto-detect robot port and display positions
python read_leader_positions.py

# Specify port manually
python read_leader_positions.py --port=/dev/ttyUSB0

# Custom motor IDs and frequency
python read_leader_positions.py --motor_ids=1,2,3,4 --hz=60
```

Output format:
```
Motor  | Pos  |   %
--------------------
1      | 2048 |  50%
2      | 1024 |  25%
3      | 3072 |  75%
...
```

### set_middle_position_standalone.py
Sets the middle position calibration for Feetech servo motors.

```bash
# Auto-detect robot and set middle position
python set_middle_position_standalone.py

# Specify port manually
python set_middle_position_standalone.py --port=/dev/ttyUSB0
```

## Features

- Auto-detects robot port
- Displays real-time joint positions
- Minimal dependencies (only pyserial)
- Clean, compact terminal output
- ~120 lines of code
