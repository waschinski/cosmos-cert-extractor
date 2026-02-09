# cosmos-cert-extractor
This is a python script monitoring your [Cosmos](https://github.com/azukaar/Cosmos-Server) config file for changes in order to extract the TLS certificate from it. I am personally using this to re-use the certificate in my Omada Controller, Dovecot and AliasVault containers.
> [!NOTE]
> The script is being triggered on __any__ configuration change being done in Cosmos but verifies whether `TLSValidUntil` in the config file has changed or not. Only if it has changed (and on every start of the container) the script assumes the cert has been renewed and it is being extracted.

## How to use
Make sure your volume mounts are set up correctly:
* The `cosmos` volume or path must be mapped to `/input`.
* The `adguard-config` volume or path must be mapped to `/output`.

The `cert.pem`, `key.pem` and the optional `combined.pem` file will be created and updated in `/output/certs` and can then be used e.g. in Adguard using these paths:
* `/opt/adguardhome/conf/certs/cert.pem`
* `/opt/adguardhome/conf/certs/key.pem`

## Environment Variables

|Envvar|Default value|Description|
|---|---|---|
|CERT_SUBFOLDER|`/certs`|The subfolder in `/output` where the certifcate files are being written to|
|COMBINED_PEM|`false`|Setting this to `true`, `1` or `yes` will create an additional `combined.pem` file which contains both 
the private key and the certificate|
