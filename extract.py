#!/usr/bin/env python3

import os
import sys
import json
import time
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

def get_cert_configurations():
    configs = []
    i = 1

    while True:
        folder = os.getenv(f'CERT_FOLDER_{i}')
        if folder is None:
            break

        config = {
            'certs_path': f"{folder}{os.getenv(f'CERT_SUBFOLDER_{i}', '/certs')}",
            'combined_pem': os.getenv(f'COMBINED_PEM_{i}', 'false').lower() in ('1', 'true', 'yes'),
            'filename': os.getenv(f'COMBINED_PEM_FILENAME_{i}', 'combined.pem'),
        }
        configs.append(config)
        i += 1

    if not configs:
        configs.append({
            'certs_path': f"/output{os.getenv('CERT_SUBFOLDER', '/certs')}",
            'combined_pem': os.getenv('COMBINED_PEM', 'false').lower() in ('1', 'true', 'yes'),
            'filename': os.getenv('COMBINED_PEM_FILENAME', 'combined.pem'),
        })

    return configs

INPUT_PATH = "/input"
CONFIGS = get_cert_configurations()
curr_valid_until = None

class ConfigFileHandler(FileSystemEventHandler):
    def on_modified(self, event):
        if event.src_path == INPUT_PATH + "/cosmos.config.json" and os.path.getsize(event.src_path) > 0:
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
    else:
        print("Cosmos config file not found.")
        sys.exit()

def load_config():
    try:
        with open(INPUT_PATH + "/cosmos.config.json", "r") as conf_file:
            return json.load(conf_file)
    except OSError:
        return None

def write_certificates(cert, key):
    for config in CONFIGS:
        if config['combined_pem']:
            with open(f"{config['certs_path']}/{config['filename']}", "w") as combined_file:
                combined_file.write(key)
                combined_file.write("\n")
                combined_file.write(cert)
        else:
            with open(f"{config['certs_path']}/cert.pem", "w") as cert_file:
                cert_file.write(cert)
            with open(f"{config['certs_path']}/key.pem", "w") as key_file:
                key_file.write(key)

        print(f"Cert successfully extracted to {config['certs_path']}.")

def main():
    if not os.path.isdir(INPUT_PATH):
        print("Config folder not found.")
        sys.exit()
    for config in CONFIGS:
        if not os.path.isdir(config['certs_path']):
            print(f"Certs output folder {config['certs_path']} not found. Check your mapppings and configuration.")
            sys.exit()

    observer = Observer()
    event_handler = ConfigFileHandler()
    observer.schedule(event_handler, INPUT_PATH, recursive=False)
    observer.start()
    print("Starting to watch for certificate updates.")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()

if __name__ == "__main__":
    main()
