#!/usr/bin/env python3

import os
import sys
import json
import time
import hashlib
import shutil
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

INPUT_PATH = os.getenv("INPUT_PATH", "/input")
CONFIG_FILE = os.path.join(INPUT_PATH, "cosmos.config.json")


class Config:
    """Parsed certificate-relevant state of the Cosmos config."""

    def __init__(self, raw):
        self.http = raw.get("HTTPConfig") or {}
        self.zones = self.http.get("DNSZones") or []
        self.zone_certs = self.http.get("ZoneCerts") or {}
        self.local_certs = self.http.get("LocalCerts") or {}

    @property
    def legacy(self):
        """The single top-level certificate (pre-zones behaviour)."""
        cert = self.http.get("TLSCert")
        key = self.http.get("TLSKey")
        if cert and key:
            return {"cert": cert, "key": key}
        return None

    def zone_entries(self):
        """Yield (zone_name, mode, cert or None) for every explicit zone."""
        for zone in self.zones:
            name = zone.get("Zone") or zone.get("zone")
            if not name:
                continue
            mode = zone.get("HTTPSCertificateMode") or ""
            cert = None
            if mode == "PROVIDED":
                if zone.get("TLSCert") and zone.get("TLSKey"):
                    cert = {"cert": zone["TLSCert"], "key": zone["TLSKey"]}
            elif mode == "LETSENCRYPT":
                zc = self.zone_certs.get(name)
                if zc and zc.get("TLSCert") and zc.get("TLSKey"):
                    cert = {"cert": zc["TLSCert"], "key": zc["TLSKey"]}
            # SELFSIGNED: nothing to extract (self-signed is served by the server)
            # DISABLED: HTTP only, nothing to extract.

            yield (name, mode, cert)

    def local_entries(self):
        """Yield per-domain HTTP-01 certificates the node got by itself."""
        for name, zc in self.local_certs.items():
            if zc and zc.get("TLSCert") and zc.get("TLSKey"):
                yield (name, {"cert": zc["TLSCert"], "key": zc["TLSKey"]})

    def fingerprint(self):
        """Hash over everything relevant, so any cert rotation (including
        per-zone ones) triggers a rewrite."""
        h = hashlib.sha256()
        if self.legacy:
            h.update(self.legacy["cert"].encode("utf-8", "ignore"))
            h.update(self.legacy["key"].encode("utf-8", "ignore"))
        h.update(str(self.http.get("TLSValidUntil")).encode("utf-8", "ignore"))
        for name, mode, cert in sorted(self.zone_entries()):
            h.update((name + "|" + mode).encode("utf-8", "ignore"))
            if cert:
                h.update(cert["cert"].encode("utf-8", "ignore"))
                h.update(cert["key"].encode("utf-8", "ignore"))
        for name in sorted(self.local_certs.keys()):
            h.update(("local:" + name).encode("utf-8", "ignore"))
            zc = self.local_certs[name]
            for field in ("TLSCert", "TLSKey"):
                val = zc.get(field) or ""
                h.update(val.encode("utf-8", "ignore"))
        for name in sorted(self.zone_certs.keys()):
            h.update(("zonecert:" + name).encode("utf-8", "ignore"))
            zc = self.zone_certs[name]
            for field in ("TLSCert", "TLSKey", "Hosts", "ValidUntil"):
                val = zc.get(field)
                if isinstance(val, list):
                    val = json.dumps(val, sort_keys=True)
                h.update(str(val).encode("utf-8", "ignore"))
        return h.hexdigest()


def load_config():
    try:
        with open(CONFIG_FILE, "r") as conf_file:
            raw = json.load(conf_file)
            return Config(raw)
    except (OSError, json.JSONDecodeError) as exc:
        print(f"Could not read {CONFIG_FILE}: {exc}")
        return None


def get_cert_configurations():
    configs = []
    idx = 1
    while True:
        folder = os.getenv(f"CERT_FOLDER_{idx}")
        if folder is None:
            break
        config = {
            "certs_path": folder,
            "combined_pem": os.getenv(f"COMBINED_PEM_{idx}", "false").lower() in ("1", "true", "yes"),
            "filename": os.getenv(f"COMBINED_PEM_FILENAME_{idx}", "combined.pem"),
        }
        configs.append(config)
        idx += 1
    if not configs:
        configs.append({
            "certs_path": "/output",
            "combined_pem": os.getenv("COMBINED_PEM", "false").lower() in ("1", "true", "yes"),
            "filename": os.getenv("COMBINED_PEM_FILENAME", "combined.pem"),
        })
    return configs


CONFIGS = get_cert_configurations()
curr_fingerprint = None


def _ensure_dir(path):
    if not os.path.isdir(path):
        try:
            os.makedirs(path, exist_ok=True)
            print(f"Created {path}")
        except OSError as exc:
            print(f"Could not create {path}: {exc}")
            raise


def _write_pair_to(config, folder, cert, key):
    _ensure_dir(folder)
    if config["combined_pem"]:
        with open(os.path.join(folder, config["filename"]), "w")as f:
            f.write(key)
            f.write("\n")
            f.write(cert)
    else:
        with open(os.path.join(folder, "cert.pem"), "w")as f:
            f.write(cert)
        with open(os.path.join(folder, "key.pem"), "w")as f:
            f.write(key)


def write_certificates(config_obj):
    """Write every certificate the config contains to all output configs."""
    legacy = config_obj.legacy
    zone_entries = list(config_obj.zone_entries())
    local_entries = list(config_obj.local_entries())

    # Merge zone certs and local certs by zone name;the explicit zone's own
    # cert wins over a local cert of the same name. In practice there is no
    # overlap: a zone with its own cert excludes its hosts from the node's
    # local ones.

    certs_by_zone = {}
    for name, mode, cert in zone_entries:
        if cert:
            certs_by_zone[name] = cert
    for name, cert in local_entries:
        if name not in certs_by_zone and cert:
            certs_by_zone[name] = cert

    for config in CONFIGS:
        base = config["certs_path"]
        _ensure_dir(base)
        wrote_any = False

        if legacy:
            _write_pair_to(config, base, legacy["cert"], legacy["key"])
            wrote_any = True

        # per-zone certificates: <zone>/cert.pem (or combined.pem) directly
        # under the output base.
        for name, cert in sorted(certs_by_zone.items()):
            target = os.path.join(base, name)
            _write_pair_to(config, target, cert["cert"], cert["key"])
            wrote_any = True

        # Remove stale per-zone directories whose zone no longer has a cert
        # (or was removed from the config entirely), so consumers never serve
        # an outdated certificate after a zone is deleted or becomes HTTP-only.
        # Only directories that actually contain cert artifacts are removed, so
        # unrelated folders in the output base are never touched.
        present = set(certs_by_zone.keys())
        for entry in os.listdir(base):
            if entry in present:
                continue
            stale = os.path.join(base, entry)
            if not os.path.isdir(stale):
                continue
            if any(os.path.exists(os.path.join(stale, f)) for f in ("cert.pem", "key.pem", config["filename"])):
                shutil.rmtree(stale, ignore_errors=True)
                print(f"Removed stale zone certificate directory {stale}.")

        if wrote_any:
            print(f"Cert successfully extracted to {base}.")
        else:
            print(f"No certificates found in config. Nothing written to {base}.")


def check_certificate():
    global curr_fingerprint
    config_obj = load_config()
    if config_obj is None:
        sys.exit(1)
    fp = config_obj.fingerprint()
    if fp != curr_fingerprint:
        write_certificates(config_obj)
        curr_fingerprint = fp


class ConfigFileHandler(FileSystemEventHandler):
    def on_modified(self, event):
        if event.src_path == CONFIG_FILE and os.path.getsize(event.src_path) > 0:
            check_certificate()


def main():
    if not os.path.isdir(INPUT_PATH):
        print("Config folder not found.")
        sys.exit(1)
    for config in CONFIGS:
        try:
            _ensure_dir(config["certs_path"])
        except OSError:
            print(f"Certs output folder {config['certs_path']} not found. Check your mounts and configuration.")
            sys.exit(1)

    # initial extraction (also covers container starts with an already-populated config)
    check_certificate()

    observer = Observer()
    event_handler = ConfigFileHandler()
    observer.schedule(event_handler, INPUT_PATH, recursive=False)
    observer.start()
    print("Starting to watch for certificate updates.")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()


if __name__ == "__main__":
    main()