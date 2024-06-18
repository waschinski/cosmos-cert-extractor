#!/usr/bin/env python3

import os
import sys
import json
import time
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

INPUT_PATH = "/input"
CERTS_PATH = "/output/certs"

class ConfigFileHandler(FileSystemEventHandler):
    def on_modified(self, event):
        if event.src_path == INPUT_PATH + "/cosmos.config.json":
            extract_cert()

def extract_cert():
    config_object = load_config()
    if config_object:
        cert = config_object["HTTPConfig"]["TLSCert"]
        key = config_object["HTTPConfig"]["TLSKey"]
        write_certificates(cert, key)
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
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()

if __name__ == "__main__":
    main()
