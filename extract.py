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
DEFAULT_CHECK_INTERVAL = 0  # Default check interval is when it expires

# Event to indicate interruption by signal
interrupted = False
lock = threading.Lock()
current_config_hash = None

def compute_relevant_config_hash(config_path):
    # Compute the SHA-256 hash of the relevant parts of the config file
    hasher = hashlib.sha256()
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
            relevant_data = json.dumps({
                'TLSCert': config['HTTPConfig']['TLSCert'],
                'TLSKey': config['HTTPConfig']['TLSKey']
            }, sort_keys=True).encode('utf-8')
            hasher.update(relevant_data)
    except (OSError, json.JSONDecodeError) as e:
        print(f'Error computing hash for config file: {e}')
        return None
    return hasher.hexdigest()

class ConfigChangeHandler(FileSystemEventHandler):
    # Handler for file system events. Triggers certificate renewal on config file modification.
    def on_modified(self, event):
        global current_config_hash
        # Check if the modified file is the config file
        if event.src_path == CONFIG_PATH and os.path.getsize(event.src_path) > 0:
            new_config_hash = compute_relevant_config_hash(CONFIG_PATH)
            if new_config_hash and new_config_hash != current_config_hash:
                print('Configuration file changed, renewing certificates.')
                current_config_hash = new_config_hash
                renew_certificates()
                time.sleep(1)

def get_timezone():
    # Get the timezone from the environment variable or use UTC as default.
    tz_name = os.getenv('TIMEZONE', 'UTC')
    try:
        return pytz.timezone(tz_name)
    except pytz.UnknownTimeZoneError:
        print(f'Invalid timezone specified: {tz_name}. Using UTC instead.')
        return pytz.UTC

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

def renew_certificates():
    # Renew the certificates by reading from the config file and writing to the certificate files.
    global interrupted
    cert_data, key_data = load_certificates()
    print('Updating certificates...')
    config_object = load_config()
    if config_object:
        cert = config_object['HTTPConfig']['TLSCert']
        key = config_object['HTTPConfig']['TLSKey']
        write_certificates(cert, key)
        print('Certificates updated.')
    else:
        print('Couldn\'t read the config file.')

def is_cert_expired(cert_data, tz):
    # Check if the certificate has expired and convert the expiry date to the specified timezone.
    cert = crypto.load_certificate(crypto.FILETYPE_PEM, cert_data)
    expiry_date_str = cert.get_notAfter().decode('ascii')
    expiry_date = datetime.strptime(expiry_date_str, '%Y%m%d%H%M%SZ').replace(tzinfo=timezone.utc)
    expiry_date = expiry_date.astimezone(tz)  # Convert to specified timezone
    return expiry_date < datetime.now(tz), expiry_date  # Return expiry status and expiry date

def get_check_interval():
    # Get the check interval from the environment variable or use the default.
    try:
        return int(os.getenv('CHECK_INTERVAL', DEFAULT_CHECK_INTERVAL))
    except ValueError:
        print(f'Invalid CHECK_INTERVAL value. Using default: {DEFAULT_CHECK_INTERVAL} seconds.')
        return DEFAULT_CHECK_INTERVAL

def get_watchdog_status():
    # Check if the watchdog is enabled based on the environment variable.
    return os.getenv('WATCHDOG_ENABLED', 'false').lower() in ['true', '1', 'yes']

def signal_handler(sig, frame):
    # Handle interrupt signal by setting the interrupted flag.
    global interrupted
    with lock:
        interrupted = True
    print('Received interrupt signal.')
    renew_certificates()
    interrupted = False
    time.sleep(1)

def main():
    global current_config_hash
    signal.signal(signal.SIGINT, signal_handler)  # Register SIGINT handler
    next_check_time = time.time()
    tz = get_timezone()
    renew_certificates()  # Initial renewal of certificates
    watchdog_enabled = get_watchdog_status()  # Check if watchdog is enabled
    current_config_hash = compute_relevant_config_hash(CONFIG_PATH)  # Compute initial hash
    cert_data, key_data = load_certificates()
    expired, expiry_date = is_cert_expired(cert_data, tz)
    print(f'New certificate expires on {expiry_date.isoformat()} {expiry_date.tzinfo}.')

    if watchdog_enabled:
        print('Watchdog enabled. Monitoring the configuration file for changes.')
        event_handler = ConfigChangeHandler()
        observer = Observer()
        observer.schedule(event_handler, path=os.path.dirname(CONFIG_PATH), recursive=False)
        observer.start()

    while True:
        interrupted = False
        check_interval = get_check_interval()  # Get the check interval
        current_time = time.time()
        cert_data, key_data = load_certificates()
        # Condition to renew certificates if expired or interrupted
        expired, expiry_date = is_cert_expired(cert_data, tz)
        if expired and check_interval > 0:
            old_expiry_date = expiry_date
            renew_certificates()
            expired, expiry_date = is_cert_expired(cert_data, tz)
            print(f'Certificate expired on: {old_expiry_date.isoformat()} {old_expiry_date.tzinfo}. Updating again in {check_interval} seconds.')
            next_check_time = current_time + check_interval  # Update next_check_time
        elif check_interval > 0 and current_time >= next_check_time:
            renew_certificates()
            print(f'Updating again in {check_interval} seconds.')
            next_check_time = current_time + check_interval
        # Handle the case when CHECK_INTERVAL is 0 and certificate expired or interrupted
        elif check_interval == 0 and expired:
            old_expiry_date = expiry_date
            renew_certificates()
            expired, expiry_date = is_cert_expired(cert_data, tz)
            print(f'Certificate expired on: {old_expiry_date.isoformat()} {old_expiry_date.tzinfo}. New certificate expires on {expiry_date.isoformat()} {expiry_date.tzinfo}.')

        time.sleep(1)

if __name__ == '__main__':
    main()
