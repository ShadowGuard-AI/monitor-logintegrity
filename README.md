![Banner](banner.png)

# monitor-logintegrity
Monitors system logs (e.g., syslog, auth.log) for changes that could indicate tampering. Calculates and tracks checksums of log files. Pure appends to a log file are logged as growth. Shrinkage, a change to content that was already seen, or a monitored file that becomes missing or unreadable after its baseline is an integrity alert. Uses only the Python standard library, and files are hashed in fixed size chunks. - Focused on System monitoring and alerts

This tool uses only the Python standard library. No installs are needed and there is no requirements.txt.

## Install
`git clone https://github.com/ShadowStrikeHQ/monitor-logintegrity`

## Usage
`python3 main.py FILE [-i INTERVAL] [-c CHECKSUM] [-s STATE]`

A supplied checksum is normalised to lowercase hex, and a supplied checksum that is not a valid SHA256 hex digest exits with status 1. Every observed checksum is logged with its time. With `-s` or `--state`, every observed checksum is also appended, with its time, to the state or history file the operator names. If no state file is named, the checksum history is kept in the log lines only, and no state file is created.

## Parameters
- `-h`: Show help message and exit
- `filepath`: Path to the log file to monitor.
- `-i`: Interval in seconds to check for changes (default: 60).
- `-c`: Initial checksum to compare against. If not provided, it will be calculated.
- `-s`: Optional state or history file for observed checksums, as described above.

## License
Copyright (c) ShadowStrikeHQ
