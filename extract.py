#!/usr/bin/env python3

import json
import os
import signal
import threading
import time
from datetime import datetime, timezone
from OpenSSL import crypto
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import pytz
import hashlib

# Paths to configuration and certificate files
CONFIG_PATH = '/input/cosmos.config.json'
CERT_PATH = '/output/certs/cert.pem'
KEY_PATH = '/output/certs/key.pem'  
# Event to indicate interruption by signal
interrupted = False
lock = threading.Lock()
curr_valid_until = None

class ConfigFileHandler(FileSystemEventHandler):
    def on_modified(self, event):
        if event.src_path == INPUT_PATH and os.path.getsize(event.src_path) > 0:
            check_certificate()

def check_certificate():
    global curr_valid_until
    config_object = load_config()
    if config_object:
        cert = config_object["HTTPConfig"]["TLSCert"]
        key = config_object["HTTPConfig"]["TLSKey"]
        valid_until = config_object["HTTPConfig"]["TLSValidUntil"]
        if valid_until != curr_valid_until:
            write_certificates(cert, key)
            curr_valid_until = valid_until
            print(f'New certificate expires on {convert_to_timezone(curr_valid_until, tz)} {expiry_date.tzinfo}.')
    else:
        print("Cosmos config file not found.")
        sys.exit()

def get_local_timezone():
    # Get the system's local timezone from environment variable or tzlocal
    tz_name = os.getenv('TZ', get_localzone() )
    if tz_name:
        try:
            os.system(f'ln -fs /usr/share/zoneinfo/{tz_name} /etc/localtime && \
    dpkg-reconfigure -f noninteractive tzdata && \
    echo {tz_name} > /etc/timezone')
            with open('/etc/timezone', 'w') as f:
                f.write(tz_name + '\n')
                return pytz.timezone(tz_name)
        except pytz.UnknownTimeZoneError:
            print(f'Invalid timezone specified: {tz_name}. Using UTC instead.')
            return pytz.UTC
    else:
        return get_localzone()

def load_config():
    # Load the configuration from the specified config file.
    try:
        with open(CONFIG_PATH, 'r') as conf_file:
            return json.load(conf_file)
    except OSError as e:
        print(f'Error reading config file: {e}')
        return None

def load_certificates():
    # Load the current certificates from the specified files.
    try:
        with open(CERT_PATH, 'r') as cert_file:
            cert_data = cert_file.read()
        with open(KEY_PATH, 'r') as key_file:
            key_data = key_file.read()
        return cert_data, key_data
    except OSError as e:
        print(f'Error reading certificates: {e}')
        return None, None

def write_certificates(cert, key):
    # Write the new certificates to the specified files.
    try:
        with open(CERT_PATH, 'w') as cert_file:
            cert_file.write(cert)
        with open(KEY_PATH, 'w') as key_file:
            key_file.write(key)
        print('Certificates written successfully.')
    except OSError as e:
        print(f'Error writing certificates: {e}')

def convert_to_timezone(utc_timestamp, timezone_str):
    # Convert UTC timestamp to the specified timezone
    utc_dt = datetime.fromisoformat(utc_timestamp[:-1] + '+00:00')
    target_tz = pytz.timezone(timezone_str)
    local_dt = utc_dt.astimezone(target_tz)
    return local_dt
    
def signal_handler(sig, frame):
    # Handle interrupt signal by setting the interrupted flag.
    global interrupted
    with lock:
        interrupted = True
    print('Received interrupt signal.')
    check_certificate()
    interrupted = False
    time.sleep(1)

def main():
    global tz
    signal.signal(signal.SIGINT, signal_handler)  # Register SIGINT handler
    tz = get_local_timezone()
    check_certificate()  # Initial renewal of certificates
    print('Watchdog enabled. Monitoring the configuration file for changes.')
    event_handler = ConfigChangeHandler()
    observer = Observer()
    observer.schedule(event_handler, path=os.path.dirname(CONFIG_PATH), recursive=False)
    observer.start()

if __name__ == '__main__':
    main()
