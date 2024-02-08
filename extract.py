import json

try:
    with open("/input/cosmos.config.json", "r") as conf_file:
        config_object = json.load(conf_file)
except OSError:
    print("Couldn't read the config file.")

cert = config_object["HTTPConfig"]["TLSCert"]
key = config_object["HTTPConfig"]["TLSKey"]

with open("/output/certs/cert.pem", "w") as cert_file:
    cert_file.write(cert)

with open("/output/certs/key.pem", "w") as key_file:
    key_file.write(key)

print("Cert extracted successfully.")
