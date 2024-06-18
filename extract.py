#!/usr/bin/env python3

import json
import os
import time
from datetime import datetime
from OpenSSL import crypto

CONFIG_PATH = "/input/cosmos.config.json"
CERT_PATH = "/output/certs/cert.pem"
KEY_PATH = "/output/certs/key.pem"
DEFAULT_CHECK_INTERVAL = 3600  # Default check interval (1 hour)

def load_config():
    try:
        with open(CONFIG_PATH, "r") as conf_file:
            return json.load(conf_file)
    except OSError:
        return None

def load_certificates():
    try:
        with open(CERT_PATH, "r") as cert_file:
            cert_data = cert_file.read()
        with open(KEY_PATH, "r") as key_file:
            key_data = key_file.read()
        return cert_data, key_data
    except OSError:
        return None, None

def write_certificates(cert, key):
    with open(CERT_PATH, "w") as cert_file:
        cert_file.write(cert)
    
    with open(KEY_PATH, "w") as key_file:
        key_file.write(key)

    print("Cert extracted successfully.")

def is_cert_expired(cert_data):
    cert = crypto.load_certificate(crypto.FILETYPE_PEM, cert_data)
    expiry_date_str = cert.get_notAfter().decode('ascii')
    expiry_date = datetime.strptime(expiry_date_str, '%Y%m%d%H%M%SZ')
    return expiry_date < datetime.utcnow()

def get_check_interval():
    try:
        return int(os.getenv('CHECK_INTERVAL', DEFAULT_CHECK_INTERVAL))
    except ValueError:
        print(f"Invalid CHECK_INTERVAL value. Using default: {DEFAULT_CHECK_INTERVAL} seconds.")
        return DEFAULT_CHECK_INTERVAL

def main():
    # Ensure it runs at least once
    run_once = False
    check_interval = get_check_interval()

    while True:
        cert_data, key_data = load_certificates()
        if not cert_data or not key_data:
            print(f"Couldn't read the certificate or key file. Checking again in {check_interval} seconds")
            time.sleep(check_interval)
            continue

        if not run_once or is_cert_expired(cert_data):
            config_object = load_config()
            if config_object:
                cert = config_object["HTTPConfig"]["TLSCert"]
                key = config_object["HTTPConfig"]["TLSKey"]
                write_certificates(cert, key)
                run_once = True
            else:
                print(f"Couldn't read the config file. Checking again in {check_interval} seconds")
        else:
            print(f"Certificate is still valid. Checking again in {check_interval} seconds")
        
        time.sleep(check_interval)

if __name__ == "__main__":
    main()
