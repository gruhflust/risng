import json
import os
import re
import subprocess
from pathlib import Path

os.environ.setdefault("PYTHONPYCACHEPREFIX", str(Path.home() / ".cache" / "pycache"))

import pynetbox # type: ignore

# NetBox Connection Details
NETBOX_URL = "http://10.228.229.7:8000"
NETBOX_TOKEN = "8149a96ee2a55bd3fc7ac04e9a6eb20268f7034a"

WORK_DIR = Path.home() / ".risng"
WORK_DIR.mkdir(parents=True, exist_ok=True)

VLAN_DATA_PATH = WORK_DIR / "vlan_data.json"
DETECTED_INTERFACES_PATH = WORK_DIR / "detected_interfaces.json"

# Initialize NetBox API
nb = pynetbox.api(NETBOX_URL, token=NETBOX_TOKEN)

""" def get_physical_interfaces():
    Retrieve the first four physical network interfaces dynamically, excluding VLAN interfaces.
    try:
        result = subprocess.run(["ip", "link", "show"], capture_output=True, text=True)
        interfaces = set()  # Use a set to prevent duplicates

        for line in result.stdout.split("\n"):
            match = re.match(r"\d+: ([^:]+):", line)  # Extract interface name
            if match:
                iface_name = match.group(1).strip()

                # Exclude virtual interfaces (loopback, VLANs, tunnels, management, etc.)
                if iface_name.startswith(("lo", "vmk", "vir", "docker", "br", "vnet", "tap", "veth")):
                    continue
                if "." in iface_name or "@" in iface_name:  # Exclude VLAN sub-interfaces
                    continue

                interfaces.add(iface_name)

        sorted_interfaces = sorted(interfaces)[:4]  # Ensure only first 4 unique interfaces
        print("Gathered Interfaces: " + str(sorted_interfaces))
        return sorted_interfaces

    except Exception as e:
        print(f"Error retrieving interfaces: {e}")
        return [] """

def get_vlans_for_slots(device_name):
    """Fetch VLANs from NetBox and store NetBox interface names."""
    device = nb.dcim.devices.get(name=device_name)
    if not device:
        raise ValueError(f"Device {device_name} not found in NetBox")

    networks = []
    interfaces = nb.dcim.interfaces.filter(device_id=device.id)

    for iface in interfaces:
        if "slot" in iface.name.lower():  # Only use slot interfaces
            vlans = iface.tagged_vlans or []
            for vlan in vlans:
                first_ip, gateway_ip = get_vlan_ips(vlan)
                if first_ip and gateway_ip:
                    networks.append({
                        "netbox_interface": iface.name,  # e.g., slot6-1
                        "linux_interface": None,  # This will be set later
                        "vlan_id": vlan.vid,
                        "vlan_name": vlan.name,
                        "test_ip": first_ip,
                        "gateway": gateway_ip
                    })

    return networks

def get_vlan_ips(vlan):
    """Extract the first available IP and the gateway from VLAN prefix"""
    prefix_list = list(nb.ipam.prefixes.filter(vlan_id=vlan.id))

    if not prefix_list:
        return None, None  # No prefix means no testing possible

    # Get the first prefix assigned to this VLAN
    prefix = prefix_list[0]

    # Retrieve first available IP from NetBox
    first_ip = None
    try:
        first_ip = nb.ipam.prefixes.get(prefix.id).available_ips.list()[0].address
    except IndexError:
        print(f"Warning: No available IPs found in prefix {prefix.prefix}")

    # Identify gateway from NetBox description
    gateway_ip = None
    ip_addresses = nb.ipam.ip_addresses.filter(vlan_id=vlan.id)
    for ip in ip_addresses:
        if ip.description and "default gateway" in ip.description.lower():
            gateway_ip = ip.address.split('/')[0]  # Extract only IP

    return first_ip, gateway_ip

def run_ansible_playbook(host, username, networks):
    """Run Ansible, retrieve detected Linux interfaces, and map them to NetBox interfaces."""
    inventory = f"{host},"

    # Save VLAN data before running Ansible
    with VLAN_DATA_PATH.open("w", encoding="utf-8") as f:
        json.dump({"vlans": networks}, f)

    # Run Ansible Playbook
    ansible_cmd = [
        "ansible-playbook",
        "-i", inventory,
        "-u", username,
        "--ask-become-pass",
        "-e",
        f"vlan_data_path={VLAN_DATA_PATH}",
        "-e",
        f"detected_interfaces_dest={DETECTED_INTERFACES_PATH}",
        "test_vlan.yml",
    ]
    subprocess.run(ansible_cmd, capture_output=True, text=True)

    # Read detected interfaces from Ansible output
    try:
        with DETECTED_INTERFACES_PATH.open("r", encoding="utf-8") as f:
            detected_interfaces = json.load(f)
    except FileNotFoundError:
        print("Error: Detected interfaces file not found!")
        return None

    # Map NetBox interfaces (slotX-X) to detected Linux interfaces (ensX)
    for i, network in enumerate(networks):
        if i < len(detected_interfaces):
            network["linux_interface"] = detected_interfaces[i]

    return networks

def main():
    """Main script to detect interfaces, get VLANs, and run Ansible."""
    device_name = "pnt-baremetal1"
    remote_host = "10.228.229.21"
    username = "risng"

    print("Fetching expected VLANs from NetBox...")
    networks = get_vlans_for_slots(device_name)

    print("Running Ansible Playbook with dynamic interfaces and VLANs...")
    run_ansible_playbook(remote_host, username, networks)

if __name__ == "__main__":
    main()
