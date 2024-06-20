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

# Paths to configuration and certificate files
CONFIG_PATH = '/input/cosmos.config.json'
CERT_PATH = '/output/certs/cert.pem'
KEY_PATH = '/output/certs/key.pem'
DEFAULT_CHECK_INTERVAL = 0  # Default check interval is when it expires

# Event to indicate interruption by signal
interrupted = False
lock = threading.Lock()

class ConfigChangeHandler(FileSystemEventHandler):
    # Handler for file system events. Triggers certificate renewal on config file modification.
    def on_modified(self, event):
        # Check if the modified file is the config file
        if event.src_path == CONFIG_PATH:
            print('Configuration file changed, renewing certificates.')
            renew_certificates()
            time.sleep(0.0000001)

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

def is_cert_expired(cert_data):
    # Check if the certificate has expired.
    cert = crypto.load_certificate(crypto.FILETYPE_PEM, cert_data)
    expiry_date_str = cert.get_notAfter().decode('ascii')
    expiry_date = datetime.strptime(expiry_date_str, '%Y%m%d%H%M%SZ').replace(tzinfo=timezone.utc)
    return expiry_date < datetime.now(timezone.utc), expiry_date  # Return expiry status and expiry date

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
    time.sleep(0.0000001)

def main():
    signal.signal(signal.SIGINT, signal_handler)  # Register SIGINT handler
    next_check_time = time.time()
    renew_certificates()  # Initial renewal of certificates
    watchdog_enabled = get_watchdog_status()  # Check if watchdog is enabled
    expired, expiry_date = is_cert_expired(cert_data)
    print(f'New certificate expires on {expiry_date}.')
    
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
        expired, expiry_date = is_cert_expired(cert_data)
        if expired and check_interval > 0:
            old_expiry_date = expiry_date
            renew_certificates()
            expired, expiry_date = is_cert_expired(cert_data)
            print(f'Certificate expired on: {old_expiry_date}. Updating again in {check_interval} seconds.')
            next_check_time = current_time + check_interval  # Update next_check_time
        elif check_interval > 0 and current_time >= next_check_time:
            renew_certificates()
            print(f'Updating again in {check_interval} seconds.')
            next_check_time = current_time + check_interval
        # Handle the case when CHECK_INTERVAL is 0 and certificate expired or interrupted
        elif check_interval == 0 and expired:
            old_expiry_date = expiry_date
            renew_certificates()
            expired, expiry_date = is_cert_expired(cert_data)
            print(f'Certificate expired on: {old_expiry_date}. New certificate expires on {expiry_date}.')
        
        time.sleep(0.0000001)

if __name__ == '__main__':
    main()
