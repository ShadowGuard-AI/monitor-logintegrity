import hashlib
import os
import argparse
import logging
import time
import sys

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def calculate_checksum(filepath):
    """
    Calculates the SHA-256 checksum of a file.

    Args:
        filepath (str): The path to the file.

    Returns:
        str: The SHA-256 checksum of the file, or None if an error occurred.
    """
    try:
        with open(filepath, 'rb') as f:
            file_content = f.read()
            sha256_hash = hashlib.sha256(file_content).hexdigest()
            return sha256_hash
    except FileNotFoundError:
        logging.error(f"File not found: {filepath}")
        return None
    except PermissionError:
        logging.error(f"Permission denied: {filepath}")
        return None
    except Exception as e:
        logging.error(f"Error calculating checksum for {filepath}: {e}")
        return None

def monitor_file(filepath, initial_checksum=None, interval=60):
    """
    Monitors a file for changes in its checksum.

    Args:
        filepath (str): The path to the file to monitor.
        initial_checksum (str, optional): The initial checksum of the file. If None, it's calculated. Defaults to None.
        interval (int, optional): The interval in seconds to check for changes. Defaults to 60.
    """
    if initial_checksum is None:
        initial_checksum = calculate_checksum(filepath)
        if initial_checksum is None:
            logging.error(f"Failed to get initial checksum for {filepath}. Monitoring aborted.")
            return

        logging.info(f"Initial checksum for {filepath}: {initial_checksum}")

    while True:
        try:
            current_checksum = calculate_checksum(filepath)
            if current_checksum is None:
                logging.error(f"Failed to calculate current checksum for {filepath}. Skipping this check.")
                time.sleep(interval)
                continue

            if current_checksum != initial_checksum:
                logging.warning(f"Checksum for {filepath} has changed!")
                logging.warning(f"Old checksum: {initial_checksum}")
                logging.warning(f"New checksum: {current_checksum}")
                # Implement alerting mechanism here (e.g., send email, trigger webhook)

                #Update initial_checksum for next iteration to avoid spamming alerts
                initial_checksum = current_checksum
            else:
                logging.info(f"Checksum for {filepath} is unchanged.")

            time.sleep(interval)

        except KeyboardInterrupt:
            logging.info("Monitoring stopped by user.")
            break
        except Exception as e:
            logging.error(f"An unexpected error occurred: {e}")
            break

def setup_argparse():
    """
    Sets up the command-line argument parser.

    Returns:
        argparse.ArgumentParser: The argument parser.
    """
    parser = argparse.ArgumentParser(description="Monitors system logs for integrity by tracking checksums.")
    parser.add_argument("filepath", help="Path to the log file to monitor.")
    parser.add_argument("-i", "--interval", type=int, default=60, help="Interval in seconds to check for changes (default: 60).")
    parser.add_argument("-c", "--checksum", type=str, default=None, help="Initial checksum to compare against. If not provided, it will be calculated.")
    return parser

def main():
    """
    Main function to parse arguments and start the monitoring process.
    """
    parser = setup_argparse()
    args = parser.parse_args()

    # Input validation
    if not os.path.isfile(args.filepath):
        logging.error(f"Error: File '{args.filepath}' does not exist.")
        sys.exit(1)

    if args.interval <= 0:
        logging.error("Error: Interval must be a positive integer.")
        sys.exit(1)

    monitor_file(args.filepath, args.checksum, args.interval)


if __name__ == "__main__":
    main()

# Usage Examples:

# 1. Monitor a file and calculate the initial checksum:
# python monitor_logintegrity.py /var/log/syslog

# 2. Monitor a file with a specific interval:
# python monitor_logintegrity.py /var/log/auth.log -i 300

# 3. Monitor a file with a known initial checksum:
# python monitor_logintegrity.py /var/log/my_app.log -c "e5b7d4f2c8a9b6e1d0b5c4a3f8e2d1c0a9b8f7e6d5c4b3a2f1e0d9c8b7a6f5e4"