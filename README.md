# cosmos-cert-extractor
A lightweight Python utility that monitors your [Cosmos](https://github.com/azukaar/Cosmos-Server) configuration file for TLS certificate changes and automatically extracts them for use in other Docker containers.
> [!NOTE]
> The script is being triggered on __any__ configuration change in Cosmos. It then checks if the `TLSValidUntil` timestamp in the config file has been updated. Only if it has changed (and on every start of the container) the script assumes the cert has been renewed and it is being extracted.

## How it works
1. The script uses watchdog to monitor the /input directory for changes to cosmos.config.json.
2. Upon a change, it reads the new configuration.
3. It compares the new TLSValidUntil value with the last known value.
4. If the timestamp has changed (or on the first run), it extracts the TLSCert and TLSKey from the config.
5. It writes the certificate and key to your specified output volumes, in either separate or combined format.

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
  -e CERT_SUBFOLDER_1=/ \
  -e CERT_SUBFOLDER_2=/ \
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
      - CERT_SUBFOLDER_1=/
      - CERT_SUBFOLDER_2=/
      - COMBINED_PEM_2=true
      - COMBINED_PEM_FILENAME_2=smtp_combined.pem
```

### Volume Mounts
* /input (Required): Mount your Cosmos data directory (e.g., `/var/lib/cosmos`) to this path. The script will read cosmos.config.json from here.
* Output Paths (Required): Mount the certificate or config directory/volume of each target container to a unique path (e.g., `/output_dovecot`). These paths are then referenced by the `CERT_FOLDER_n` environment variables. If you use the single, unnumbered configuration, the path must be `/output`.

### Example Usage
The extracted `cert.pem`, `key.pem`, or `combined.pem` files can be used directly by services like AdGuard Home, Omada Controller, or Dovecot. For example, in AdGuard Home, you would point to:
* `/opt/adguardhome/conf/certs/cert.pem`
* `/opt/adguardhome/conf/certs/key.pem`

## Environment Variables
This script supports both a single configuration (for backward compatibility) and multiple configurations via numbered environment variables.

|Environment Variable|Default value|Description|
|---|---|---|
|CERT_FOLDER_n|(None)|(Required for multiple configs) The full path to the volume where certificates for instance n should be written (e.g., `/output_dovecot`).|
|CERT_SUBFOLDER_n|`/certs`|The subdirectory within `CERT_FOLDER_n` where the files will be created.|
|COMBINED_PEM_n|`false`|If set to `true`, `1`, or `yes`, the script will write a single combined.pem file (key + cert) instead of separate files.|
|COMBINED_PEM_FILENAME_n|`combined.pem`|The filename for the combined PEM file when `COMBINED_PEM_n` is enabled.|
|CERT_SUBFOLDER|`/certs`|(Fallback) The subdirectory for the single, unnumbered configuration.|
|COMBINED_PEM|`false`|(Fallback) The combined PEM setting for the single, unnumbered configuration.|
|COMBINED_PEM_FILENAME|`combined.pem`|(Fallback) The combined PEM filename for the single, unnumbered configuration.|
