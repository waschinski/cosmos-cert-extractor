# cosmos-cert-extractor
This is a python script monitoring your [Cosmos](https://github.com/azukaar/Cosmos-Server) config file for changes in order to extract the TLS certificate from it. My personal use case is to re-use the certificate in my Adguard Home instance.
> [!NOTE]
> When Watchdog is enabled, the script is being triggered on __any__ configuration change being done in Cosmos and currently does not verify whether the certificate has actually changed.

## How to use
Make sure your volume mounts are set up correctly:
* The `cosmos` volume or path must be mapped to `/input`.
* The `adguard-config` volume must be mapped to `/output`.

The `cert.pem` and `key.pem` file will be created and updated in `/output/certs` and can then be used in Adguard using these paths:
* `/opt/adguardhome/conf/certs/cert.pem`
* `/opt/adguardhome/conf/certs/key.pem`
* ## Default Environment Values
* `CHECK_INTERVAL = 0` -> Timer in seconds disabled, put value other than 0 to enable.
* `WATCHDOG_ENABLED = true` -> Watchdog enabled, put false or 0 to disable.
