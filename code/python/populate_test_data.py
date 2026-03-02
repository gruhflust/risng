import os
from pathlib import Path

os.environ.setdefault("PYTHONPYCACHEPREFIX", str(Path.home() / ".cache" / "pycache"))

import pynetbox # type: ignore

# NetBox Connection Details (Change this if needed)
NETBOX_URL = "http://10.228.229.7:8000"
NETBOX_TOKEN = "ec30f0c7a1c9656c18fe884290bf9c901ff5a29e"

# Initialize NetBox API
nb = pynetbox.api(NETBOX_URL, token=NETBOX_TOKEN)

# Device name and management IP
DEVICE_NAME = "pnt-baremetal1"
MANAGEMENT_IP = "10.228.229.21/24"
INTERFACES = ["slot6-1", "slot6-2", "slot7-1", "slot7-2"]
VLANS = [2000, 2001, 2002, 2003]

def create_devices(device_name):
    existing_device = list(nb.dcim.devices.filter(name = device_name))
    if existing_device:
        print(f"DEVICE {device_name} already exists.")
        return existing_device[0]
    
    device = nb.dcim.devices.create({
        "name": device_name,
        "device_type": 6,
        "role": 11,
        "site": 1,
        "status": "active"
    })

    return device

def create_vlan(vlan_id):
    """Create a VLAN in NetBox if it doesn't already exist"""
    existing_vlan = list(nb.ipam.vlans.filter(vid=vlan_id))
    if existing_vlan:
        print(f"VLAN {vlan_id} already exists.")
        return existing_vlan[0]

    vlan = nb.ipam.vlans.create({
        "vid": vlan_id,
        "name": f"Test-VLAN-{vlan_id}",
        "status": "active"
    })
    print(f"Created VLAN {vlan_id}")
    return vlan

def create_prefix(vlan, subnet="24"):
    """Create a prefix for the VLAN"""
    prefix = f"10.{vlan.vid // 100}.{vlan.vid % 100}.0/{subnet}"
    nb.ipam.prefixes.create({
        "prefix": prefix,
        "vlan": vlan.id,
        "status": "active",
        "description": f"Prefix for VLAN {vlan.vid}"
    })
    print(f"Created Prefix {prefix}")
    return prefix

def create_gateway(vlan):
    """Create a gateway IP for the VLAN"""
    gateway_ip = f"10.{vlan.vid // 100}.{vlan.vid % 100}.1/24"
    ip = nb.ipam.ip_addresses.create({
        "address": gateway_ip,
        "status": "active",
        "description": "Default Gateway",
        "vlan": vlan.id
    })
    print(f"Created Gateway {gateway_ip}")
    return ip

def assign_vlan_to_interface(device, internetinterface, vlan):
    """Assign a VLAN to an interface, creating the interface if needed"""
    interface = nb.dcim.interfaces.get(device_id=device.id, name=internetinterface)
    if not interface:
        interface = nb.dcim.interfaces.create({
            "device": device.id,
            "name": internetinterface,
            "type": "1000base-t",
            "mode": "tagged"
        })
        print(f"Created interface {internetinterface}")

    if vlan.id not in [v.id for v in interface.tagged_vlans]:
        interface.tagged_vlans.append(vlan.id)
        interface.save()
        print(f"Assigned VLAN {vlan.vid} to {internetinterface}")
    else:
        print(f"VLAN {vlan.vid} already assigned to {internetinterface}")

def main():
    """Populate NetBox with test data"""

    # Get or create device
    devices = ["pnt-baremetal1", "pnt-baremetal2", "pnt-baremetal3", "pnt-baremetal4"]
    for i in devices:
        device = create_devices(i)
        # Assign Management IP (vmk0)
        mgmt_interface = nb.dcim.interfaces.get(device_id=device.id, name="vmk0")
        if not mgmt_interface:
            mgmt_interface = nb.dcim.interfaces.create({
                "device": device.id,
                "name": "vmk0",
                "type": "virtual",
                "mode": "access"
            })
            print(f"Created vmk0 on device {device.name}")
        else:
            print(f"Interface vmk0 already exists on {device.name}")
        ip_addr = f"10.228.229.{20 + devices.index(i) + 1}/24"
        existing_ip = nb.ipam.ip_addresses.filter(address=ip_addr)

        if not existing_ip:
            nb.ipam.ip_addresses.create({
                "address": ip_addr,
                "status": "active",
                "assigned_object_type": "dcim.interface",
                "assigned_object_id": mgmt_interface.id
            })
            print(f"Assigned Management IP {ip_addr} to vmk0 on device {device.name}")
        else:
            print(f"Management IP {ip_addr} already exists in NetBox.")

        # Create VLANs, Prefixes, and Gateways only once
        vlan_objects = {}
        for vlan_id in VLANS:
            vlan = create_vlan(vlan_id)
            create_prefix(vlan)
            create_gateway(vlan)
            vlan_objects[vlan_id] = vlan

        # Assign each VLAN to all four slot interfaces
        for internetinterface in INTERFACES:
            for vlan in vlan_objects.values():
                assign_vlan_to_interface(device, internetinterface, vlan)

    

    print("NetBox setup complete.")

if __name__ == "__main__":
    main()
