#!/usr/bin/env python3
# extract_dhcp_from_netbox.py – Generates dhcp_static_hosts for Ansible from NetBox

import os
from pathlib import Path

os.environ.setdefault("PYTHONPYCACHEPREFIX", str(Path.home() / ".cache" / "pycache"))

import pynetbox
import yaml

# Verbindung zur NetBox
NETBOX_URL = "http://10.228.229.7:8000"
NETBOX_TOKEN = "tokentokentokentoken"  # ggf. austauschen
nb = pynetbox.api(NETBOX_URL, token=NETBOX_TOKEN)

hosts = []

# Alle Geräte durchgehen
for device in nb.dcim.devices.all():
    if not device.primary_ip:
        continue

    interfaces = nb.dcim.interfaces.filter(device_id=device.id)
    mac = None

    for iface in interfaces:
        if iface.mac_address:
            mac = iface.mac_address.lower()
            break  # erste MAC nehmen

    if not mac:
        continue

    ip = device.primary_ip.address.split("/")[0]
    hosts.append({
        "name": device.name,
        "mac": mac,
        "ip": ip
    })

# Als YAML für Ansible ausgeben
print(yaml.dump({"dhcp_static_hosts": hosts}, default_flow_style=False))
