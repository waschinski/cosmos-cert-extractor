# cosmos-cert-extractor
This is a python script monitoring your [Cosmos](https://github.com/azukaar/Cosmos-Server) config file for changes in order to extract the TLS certificate from it. My personal use case is to re-use the certificate in my Adguard Home instance.
> [!NOTE]
> The script is being triggered on __any__ configuration change being done in Cosmos but verifies whether `TLSValidUntil` in the config file has changed or not. Only if it has changed (and on every start of the container) the script assumes the cert has been renewed and it is being extracted.

## How to use
Make sure your volume mounts are set up correctly:
* The `cosmos` volume or path must be mapped to `/input`.
* The `adguard-config` volume or path must be mapped to `/output`.

The `cert.pem` and `key.pem` file will be created and updated in `/output/certs` and can then be used in Adguard using these paths:
* `/opt/adguardhome/conf/certs/cert.pem`
* `/opt/adguardhome/conf/certs/key.pem`

## Environment Variables

|Envvar|Default value|Description|
|---|---|---|
|CERT_SUBFOLDER|`/certs`|The subfolder in `/output` where the certifcate files are being written to| 
