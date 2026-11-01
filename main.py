import hashlib
import os
import argparse
import logging
import re
import time
import sys
from datetime import datetime, timezone

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

CHUNK_SIZE = 65536
CHECKSUM_RE = re.compile(r'^[0-9a-f]{64}$')

def hash_bytes_range(filepath, limit=None):
    """Hash a file, or its first limit bytes, in fixed size chunks."""
    hasher = hashlib.sha256()
    remaining = limit
    with open(filepath, 'rb') as f:
        while True:
            if remaining is not None:
                if remaining <= 0:
                    break
                chunk = f.read(min(CHUNK_SIZE, remaining))
            else:
                chunk = f.read(CHUNK_SIZE)
            if not chunk:
                break
            hasher.update(chunk)
            if remaining is not None:
                remaining -= len(chunk)
    return hasher.hexdigest()

def calculate_checksum(filepath):
    """Calculates the SHA-256 checksum of a file in fixed size chunks, or None on error."""
    try:
        return hash_bytes_range(filepath)
    except FileNotFoundError:
        logging.error(f"File not found: {filepath}")
        return None
    except PermissionError:
        logging.error(f"Permission denied: {filepath}")
        return None
    except Exception as e:
        logging.error(f"Error calculating checksum for {filepath}: {e}")
        return None

def snapshot(filepath, prefix_limit=None):
    """Returns (size, full_hash, prefix_hash) or None if the file cannot be read."""
    try:
        size = os.path.getsize(filepath)
        # A snapshot is three separate reads: a size, a full hash,
        # and later a prefix hash. A file being written while I read
        # it can give me a size from one moment and hashes from
        # others, and the growth test below then compares a prefix
        # of the new file against a hash of a version that may never
        # have existed whole. Busy logs are exactly where this bites.
        full_hash = hash_bytes_range(filepath)
        prefix_hash = hash_bytes_range(filepath, limit=prefix_limit) if prefix_limit is not None else None
        return size, full_hash, prefix_hash
    except OSError as e:
        logging.error(f"Error reading {filepath}: {e}")
        return None

def append_history(state_file, checksum, size):
    if not state_file:
        return
    stamp = datetime.now(timezone.utc).isoformat()
    with open(state_file, 'a', encoding='utf-8') as f:
        # Every poll appends a line, changed or not, so the history
        # file grows by one line per interval forever. Pointing the
        # state option at the monitored file itself is the pathological
        # case: my own append becomes the file's next change, and
        # each cycle records growth I caused.
        f.write(f"{stamp} {checksum} size={size}\n")

def normalise_checksum(value):
    """Normalise a supplied checksum to lowercase hex. Returns None if the format is invalid."""
    if value is None:
        return None
    candidate = value.strip().lower()
    if not CHECKSUM_RE.match(candidate):
        return None
    return candidate

def monitor_file(filepath, initial_checksum=None, interval=60, state_file=None):
    """
    Monitors a file for integrity changes.

    Pure appends are logged as growth. Shrinkage, or a change to the
    previously seen prefix, is an integrity alert. A file that becomes
    missing or unreadable after a successful baseline is an integrity
    alert in its own right. Every observed checksum is logged, and is
    also appended with its time to the state file when one is named
    with --state. Without --state, the history is kept in the log
    lines only.
    """
    snap = snapshot(filepath)
    if snap is None:
        logging.error(f"Failed to get initial checksum for {filepath}. Monitoring aborted.")
        return False
    prev_size, prev_hash, _ = snap
    if initial_checksum is not None:
        if initial_checksum != prev_hash:
            # A mismatch against a supplied checksum is announced here
            # and then monitoring carries on from the file as it now is.
            # The run does not stop, and the state history absorbs the
            # new checksum as the next baseline, so the warning at
            # startup is the only moment the supplied value is enforced.
            logging.warning(f"Checksum for {filepath} has changed!")
            logging.warning(f"Old checksum: {initial_checksum}")
            logging.warning(f"New checksum: {prev_hash}")
        else:
            logging.info(f"Initial checksum for {filepath}: {prev_hash}")
    else:
        logging.info(f"Initial checksum for {filepath}: {prev_hash}")
    try:
        append_history(state_file, prev_hash, prev_size)
    except OSError as e:
        logging.error(f"Error writing to state file {state_file}: {e}")
        return False

    while True:
        try:
            time.sleep(interval)
            snap = snapshot(filepath, prefix_limit=prev_size)
            if snap is None:
                logging.warning(f"Integrity alert: monitored file is missing or unreadable: {filepath}")
                # A missing file alerts on every cycle until it returns, with
                # no count and no backing off, and my previous state is kept
                # throughout, so a file that comes back different is judged
                # against what it was before it vanished, which is the one
                # part of an outage that stays honest.
                continue
            cur_size, cur_hash, prefix_hash = snap
            try:
                append_history(state_file, cur_hash, cur_size)
            except OSError as e:
                logging.error(f"Error writing to state file {state_file}: {e}")
            if cur_size < prev_size:
                logging.warning(f"Integrity alert: {filepath} shrank from {prev_size} to {cur_size} bytes.")
                logging.warning(f"Old checksum: {prev_hash}")
                logging.warning(f"New checksum: {cur_hash}")
            elif cur_size > prev_size:
                if prefix_hash != prev_hash:
                    logging.warning(f"Integrity alert: earlier content of {filepath} changed while the file grew.")
                    logging.warning(f"Old checksum: {prev_hash}")
                    logging.warning(f"New checksum: {cur_hash}")
                else:
                    logging.info(f"File grew by append: {filepath} size {prev_size} to {cur_size} bytes. New checksum: {cur_hash}")
            else:
                if cur_hash != prev_hash:
                    logging.warning(f"Integrity alert: checksum for {filepath} has changed!")
                    logging.warning(f"Old checksum: {prev_hash}")
                    logging.warning(f"New checksum: {cur_hash}")
                else:
                    logging.info(f"Checksum for {filepath} is unchanged: {cur_hash}")
            prev_size, prev_hash = cur_size, cur_hash
        except KeyboardInterrupt:
            logging.info("Monitoring stopped by user.")
            break
        except Exception as e:
            logging.error(f"An unexpected error occurred: {e}")
            break
    return True

def setup_argparse():
    parser = argparse.ArgumentParser(description="Monitors system logs for integrity by tracking checksums.")
    parser.add_argument("filepath", help="Path to the log file to monitor.")
    parser.add_argument("-i", "--interval", type=int, default=60, help="Interval in seconds to check for changes (default: 60).")
    parser.add_argument("-c", "--checksum", type=str, default=None, help="Initial checksum to compare against. If not provided, it will be calculated.")
    parser.add_argument("-s", "--state", type=str, default=None, help="Optional state or history file. Every observed checksum is appended to it with its time. If not provided, the checksum history is kept in the log lines only.")
    return parser

def main():
    parser = setup_argparse()
    args = parser.parse_args()
    if not os.path.isfile(args.filepath):
        logging.error(f"Error: File '{args.filepath}' does not exist.")
        sys.exit(1)
    if args.interval <= 0:
        logging.error("Error: Interval must be a positive integer.")
        sys.exit(1)
    checksum = None
    if args.checksum is not None:
        checksum = normalise_checksum(args.checksum)
        if checksum is None:
            logging.error("Error: Supplied checksum is not a valid SHA256 hex digest.")
            sys.exit(1)
    if not monitor_file(args.filepath, checksum, args.interval, args.state):
        sys.exit(1)

if __name__ == "__main__":
    main()
