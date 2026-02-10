#!/usr/bin/env python3

import os
import sys
import json
import time
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

INPUT_PATH = "/input"
CERTS_FOLDER = os.getenv('CERT_SUBFOLDER', '/certs')
CERTS_PATH = "/output" + CERTS_FOLDER
COMBINED_PEM = os.getenv('COMBINED_PEM', 'false').lower() in ('1', 'true', 'yes')
COMBINED_PEM_FILENAME = os.getenv('COMBINED_PEM_FILENAME', 'combined.pem')

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
    if COMBINED_PEM:
        with open(CERTS_PATH + "/" + COMBINED_PEM_FILENAME, "w") as combined_file:
            combined_file.write(key)
            combined_file.write("\n")
            combined_file.write(cert)
    else:
        with open(CERTS_PATH + "/cert.pem", "w") as cert_file:
            cert_file.write(cert)
        with open(CERTS_PATH + "/key.pem", "w") as key_file:
            key_file.write(key)

    print("Cert extracted successfully.")

def main():
    if not os.path.isdir(INPUT_PATH):
        print("Config folder not found.")
        sys.exit()
    if not os.path.isdir(CERTS_PATH):
        print("Certs output folder not found.")
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
