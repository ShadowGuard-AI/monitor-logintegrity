# monitor-logintegrity
Monitors system logs (e.g., syslog, auth.log) for changes that could indicate tampering. Calculates and tracks checksums of log files. Alerts if the checksum changes unexpectedly. Uses `hashlib` and `os` modules. - Focused on System monitoring and alerts

## Install
`git clone https://github.com/ShadowStrikeHQ/monitor-logintegrity`

## Usage
`./monitor-logintegrity [params]`

## Parameters
- `-h`: Show help message and exit
- `-i`: No description provided
- `-c`: Initial checksum to compare against. If not provided, it will be calculated.

## License
Copyright (c) ShadowStrikeHQ
