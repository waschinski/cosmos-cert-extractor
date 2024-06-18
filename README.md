# cosmos-cert-extractor
This is a python script monitoring your Cosmos config file for changes in order to extract the TLS certificate from it. The use case I set this up for is in order to use the certificate in my Adguard Home instance.
> [!NOTE]
> The script is being triggered on *any* configuration change being done in Cosmos and currently does not verify whether the certificate has actually changed.

## How to use
Make sure your volume mounts are set up correctly:
* The `cosmos` volume or path must be mapped to `/input`.
* The `adguard-config` volume must be mapped to `/output`.

The `cert.pem` and `key.pem` file will be created and updated in `/output/certs` and can then be used in Adguard using these paths:
* `/opt/adguardhome/conf/certs/cert.pem`
* `/opt/adguardhome/conf/certs/key.pem`
