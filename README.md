# cosmos-cert-extractor
A lightweight Python utility that monitors your [Cosmos](https://github.com/azukaar/Cosmos-Server) configuration file for TLS certificate changes and automatically extracts them for use in other Docker containers.

> [!NOTE]
> The script is being triggered on __any__ configuration change in Cosmos. It then compares a fingerprint of every certificate in the config (the top-level `TLSValidUntil` timestamp **and** the full content of every zone / local certificate) with the last known one. Only if something changed (and on every start of the container) the script assumes the cert has been renewed and it is being extracted. This also detects per-zone certificate rotations that happen with an unchanged `TLSValidUntil` timestamp.

## How it works
1. The script uses watchdog to monitor the /input directory for changes to cosmos.config.json.
2. Upon a change, it reads the new configuration.
3. It compares a fingerprint (hash) of:
   - the top-level `TLSCert` / `TLSKey` / `TLSValidUntil`,
   - every entry of `HTTPConfig.DNSZones` (zone name + HTTPS mode + provided certificate),
   - every entry of `HTTPConfig.ZoneCerts` (the Let's Encrypt certificates issued per zone),
   - every entry of `HTTPConfig.LocalCerts` (the node's per-domain HTTP-01 certificates).
4. If the fingerprint changed (or on the first run), it extracts the certificates from the config.
5. It writes the certificates to your specified output volumes, in either separate or combined format.

## How to use

### Docker Run
```
docker run -d \
  --name cosmos-cert-extractor \
  -v /var/lib/cosmos:/input:ro \
  -v /path/to/dovecot/config:/output_dovecot \
  -v /path/to/aliasvault/certs:/output_aliasvault \
  -e CERT_FOLDER_1=/output_dovecot \
  -e CERT_FOLDER_2=/output_aliasvault \
  -e COMBINED_PEM_2=true \
  waschinski/cosmos-cert-extractor:latest
```

### Docker Compose
```
version: '3'

services:
  cert-extractor:
    image: waschinski/cosmos-cert-extractor:latest
    container_name: cosmos-cert-extractor
    restart: unless-stopped
    volumes:
      - /var/lib/cosmos:/input:ro
      - /path/to/dovecot/config:/output_dovecot
      - /path/to/aliasvault/certs:/output_aliasvault
    environment:
      - CERT_FOLDER_1=/output_dovecot
      - CERT_FOLDER_2=/output_aliasvault
      - COMBINED_PEM_2=true
      - COMBINED_PEM_FILENAME_2=smtp_combined.pem
```

### Volume Mounts
* /input (Required): Mount your Cosmos data directory (e.g., `/var/lib/cosmos`) to this path. The script will read `cosmos.config.json` from here.
* Output Paths (Required): Mount the certificate or config directory/volume of each target container to a unique path (e.g., `/output_dovecot`). These paths are then referenced by the `CERT_FOLDER_n` environment variables. Certificates are written directly to the root of that mount (no `certs/` subfolder); see the zones layout below. If you use the single, unnumbered configuration, the path must be `/output`.

### Example Usage
The extracted `cert.pem`, `key.pem`, or `combined.pem` files can be used directly by services like AdGuard Home, Omada Controller, or Dovecot. For example, in AdGuard Home, you would point to:
* `/opt/adguardhome/conf/certs/cert.pem`
* `/opt/adguardhome/conf/certs/key.pem`

## Zones (Cosmos unstable / clusters)
Since Cosmos introduced per-zone certificates (each zone covered by `HTTPConfig.DNSZones` gets a certificate of its own — either a Let's Encrypt one stored in `ZoneCerts`, an HTTP-01 one in `LocalCerts`, or an uploaded one in the zone itself for `PROVIDED` zones), the extractor mirrors that structure:

```
<CERT_FOLDER_n>/
├── cert.pem                  # legacy single certificate (top-level TLSCert/TLSKey, when present)
├── key.pem
├── <zone1>/cert.pem          # per-zone certificate
├── <zone1>/key.pem
├── <zone2>/cert.pem
└── <zone2>/key.pem
```

* **Backward compatible**: if your config has no zones (no `DNSZones`, `ZoneCerts` or `LocalCerts`), the behaviour is identical to before — only `cert.pem`/`key.pem` (or `combined.pem`) at the root.
* The legacy top-level certificate (still written by Cosmos for the node's own hostname) keeps being extracted to `cert.pem`/`key.pem` at the root.
* Every zone with a usable certificate (issued, provided, or local) is written under `<zone>/` as `cert.pem`+`key.pem` (or `combined.pem` when `COMBINED_PEM_n` is enabled).
* Zones with `SELFSIGNED` mode or `DISABLED` (HTTP-only) have nothing to extract; their directories are removed if they previously existed, so consumers never serve an outdated certificate.
* When a zone is removed from the config, its `<zone>/` directory is cleaned up automatically.

## Environment Variables
This script supports both a single configuration (for backward compatibility) and multiple configurations via numbered environment variables.

|Environment Variable|Default value|Description|
|---|---|---|
|CERT_FOLDER_n|(None)|(Required for multiple configs) The full path to the volume where certificates for instance n should be written (e.g., `/output_dovecot`).|
|COMBINED_PEM_n|`false`|If set to `true`, `1`, or `yes`, the script will write a single combined.pem file (key + cert) instead of separate files. This applies to the root certificate as well as to every `<zone>/` directory.|
|COMBINED_PEM_FILENAME_n|`combined.pem`|The filename for the combined PEM file when `COMBINED_PEM_n` is enabled.|
|COMBINED_PEM|`false`|(Fallback) The combined PEM setting for the single, unnumbered configuration.|
|COMBINED_PEM_FILENAME|`combined.pem`|(Fallback) The combined PEM filename for the single, unnumbered configuration.|