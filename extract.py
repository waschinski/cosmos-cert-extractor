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
        print("Couldn't read the config file.")
        return None

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
        config_object = load_config()
        if not config_object:
            print("Couldn't read the config file.Checking Later")
            time.sleep(check_interval)
            continue
        
        cert = config_object["HTTPConfig"]["TLSCert"]
        key = config_object["HTTPConfig"]["TLSKey"]

        if not run_once or is_cert_expired(cert):
            write_certificates(cert, key)
            print("Cert extracted successfully.")
            run_once = True
        else:
            print("Certificate is still valid.")
        
        time.sleep(check_interval)

if __name__ == "__main__":
    main()

