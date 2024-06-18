# cosmos-cert-extractor
This is a python script periodically running (every 30 minutes[configurable]) to extract the TLS certificate from the Cosmos config file. The use case I set this up for is in order to use the certificate in my Adguard Home instance.
## How to use
Make sure your volume mounts are set up correctly:
* The `cosmos` volume or path must be mapped to `/input`.
* The `adguard-config` volume must be mapped to `/output`.

The `cert.pem` and `key.pem` file will be created and updated in `/output/certs` and can then be used in Adguard using these paths:
* `/opt/adguardhome/conf/certs/cert.pem`
* `/opt/adguardhome/conf/certs/key.pem`
