#!/usr/bin/env python3
"""Collect information about AVS resources from NetBox.

This script reads the NetBox address, user name, and API token from the
current user's home directory (``~/netbox.address.md``, ``~/netbox.user.md``
and ``~/netbox.token.md``) and queries the NetBox API for resources related to
"AVS".  The results are printed in a human readable format so the script can be
used directly or from within Ansible playbooks.
"""

from __future__ import annotations

import os
from pathlib import Path

os.environ.setdefault("PYTHONPYCACHEPREFIX", str(Path.home() / ".cache" / "pycache"))

import sys
from typing import Iterable, Optional

try:
    from pwd import getpwnam
except ImportError:  # pragma: no cover - Windows compatibility
    getpwnam = None  # type: ignore[assignment]

import pynetbox  # type: ignore
from pynetbox.core.query import RequestError  # type: ignore
import requests


CA_BUNDLE_FILENAMES = (
    "netbox.ca",
    "netbox.ca.pem",
    "netbox.ca.crt",
    "netbox.ca-bundle.pem",
)


CREDENTIAL_FILES = {
    "address": "netbox.address.md",
    "user": "netbox.user.md",
    "token": "netbox.token.md",
}


class CredentialError(RuntimeError):
    """Raised when credentials are missing or invalid."""


class ConfigurationError(RuntimeError):
    """Raised when SSL configuration is invalid."""


def _candidate_credential_dirs() -> list[Path]:
    """Return candidate directories that may store the credential files."""

    candidates: list[Path] = []

    def _add(path: Optional[str | Path]) -> None:
        if not path:
            return
        candidate = Path(path).expanduser()
        if candidate not in candidates:
            candidates.append(candidate)

    # Highest priority: explicit override for automation scenarios.
    _add(os.environ.get("BOXINFO_CREDENTIAL_HOME"))

    # Prefer the original sudo user when running with escalated privileges.
    sudo_user = os.environ.get("SUDO_USER")
    if sudo_user and getpwnam is not None:
        try:
            _add(getpwnam(sudo_user).pw_dir)
        except KeyError:
            pass

    # Next prefer the login/user environment variables if present.
    login_user = os.environ.get("LOGNAME") or os.environ.get("USER")
    if login_user and login_user != "root" and getpwnam is not None:
        try:
            _add(getpwnam(login_user).pw_dir)
        except KeyError:
            pass

    # Finally fall back to HOME and the effective user's home directory.
    _add(os.environ.get("HOME"))
    _add(Path.home())

    return candidates


def _read_credential(name: str) -> str:
    """Read the credential value from one of the candidate directories.

    Parameters
    ----------
    name:
        The credential key, e.g. ``"address"``.

    Returns
    -------
    str
        The value read from the credential file.
    """
    errors: list[Path] = []
    for directory in _candidate_credential_dirs():
        path = directory / CREDENTIAL_FILES[name]
        if path.exists():
            value = path.read_text(encoding="utf-8").strip()
            if not value:
                raise CredentialError(f"Credential file '{path}' is empty.")
            return value
        errors.append(path)

    tried = ", ".join(str(path) for path in errors)
    raise CredentialError(
        "Credential file not found; looked for: " + tried if tried else "Credential file not found."
    )


def _read_optional_boolean_env(name: str) -> Optional[bool]:
    """Parse a boolean environment variable when present."""

    raw = os.environ.get(name)
    if raw is None:
        return None

    value = raw.strip().lower()
    if value in {"1", "true", "yes", "on"}:
        return True
    if value in {"0", "false", "no", "off"}:
        return False
    raise ConfigurationError(
        f"Environment variable {name} must be one of '1', '0', 'true', 'false', 'yes', 'no', 'on' or 'off', not '{raw}'."
    )


def _find_custom_ca_bundle() -> Optional[Path]:
    """Return the path to a custom CA bundle if present."""

    override = os.environ.get("BOXINFO_CA_BUNDLE")
    if override:
        candidate = Path(override).expanduser()
        if not candidate.exists():
            raise ConfigurationError(
                f"CA bundle specified in BOXINFO_CA_BUNDLE does not exist: {candidate}"
            )
        if not candidate.is_file():
            raise ConfigurationError(
                f"CA bundle specified in BOXINFO_CA_BUNDLE is not a file: {candidate}"
            )
        return candidate

    for directory in _candidate_credential_dirs():
        for filename in CA_BUNDLE_FILENAMES:
            candidate = directory / filename
            if candidate.is_file():
                return candidate

    return None


def _configure_http_session(session: object) -> None:
    """Configure SSL verification behaviour for the NetBox HTTP session."""

    verify_override = _read_optional_boolean_env("BOXINFO_VERIFY_SSL")
    if verify_override is False:
        if hasattr(session, "verify"):
            session.verify = False  # type: ignore[attr-defined]
        return

    ca_bundle = _find_custom_ca_bundle()
    if ca_bundle is not None and hasattr(session, "verify"):
        session.verify = str(ca_bundle)  # type: ignore[attr-defined]
    elif verify_override is True and hasattr(session, "verify"):
        session.verify = True  # type: ignore[attr-defined]


def _normalise_url(address: str) -> str:
    """Ensure the NetBox address has a proper scheme and no trailing slash."""

    cleaned = address.strip()
    if not cleaned.startswith("http://") and not cleaned.startswith("https://"):
        cleaned = f"https://{cleaned}"
    return cleaned.rstrip("/")


def _related_name(obj: object, attribute: str) -> str:
    """Return the ``name`` attribute of a related object when available."""

    related = getattr(obj, attribute, None)
    if related is None:
        return "n/a"
    return getattr(related, "name", str(related))


def _primary_ip(obj: object) -> str:
    """Return the primary IP address of a device or VM if present."""

    primary = getattr(obj, "primary_ip", None)
    if primary is None:
        primary = getattr(obj, "primary_ip4", None)
    if primary is None:
        return "n/a"
    address = getattr(primary, "address", None)
    return address if address else str(primary)


def _summarise_vm(vm: object) -> str:
    """Create a single-line summary for a virtual machine."""

    status = getattr(vm, "status", "unknown")
    cluster = _related_name(vm, "cluster")
    tenant = _related_name(vm, "tenant")
    primary_ip = _primary_ip(vm)
    role = _related_name(vm, "role")
    return (
        f"{getattr(vm, 'name', 'n/a')} | status: {status} | "
        f"cluster: {cluster} | tenant: {tenant} | role: {role} | IP: {primary_ip}"
    )


def _summarise_device(device: object) -> str:
    """Create a single-line summary for a physical device."""

    status = getattr(device, "status", "unknown")
    site = _related_name(device, "site")
    rack = _related_name(device, "rack")
    role = _related_name(device, "device_role") or _related_name(device, "role")
    platform = _related_name(device, "platform")
    primary_ip = _primary_ip(device)
    return (
        f"{getattr(device, 'name', 'n/a')} | status: {status} | site: {site} | "
        f"rack: {rack} | role: {role} | platform: {platform} | IP: {primary_ip}"
    )


def _filter_avs(items: Iterable[object]) -> list[object]:
    """Return items whose name or slug mentions 'avs' (case insensitive)."""

    result = []
    for item in items:
        name = getattr(item, "name", "")
        slug = getattr(item, "slug", "")
        if isinstance(name, str) and "avs" in name.lower():
            result.append(item)
        elif isinstance(slug, str) and slug.lower() == "avs":
            result.append(item)
    return result


def _load_cluster(nb: pynetbox.api.Api) -> Optional[object]:  # type: ignore[name-defined]
    """Return the AVS cluster if present."""

    try:
        clusters = list(nb.virtualization.clusters.all())
    except (RequestError, requests.exceptions.RequestException) as exc:  # pragma: no cover - network failures are runtime only
        raise RuntimeError(f"Failed to query NetBox clusters: {exc}") from exc

    filtered = _filter_avs(clusters)
    return filtered[0] if filtered else None


def _load_vms(nb: pynetbox.api.Api, cluster: Optional[object]) -> list[object]:  # type: ignore[name-defined]
    """Fetch AVS-related virtual machines."""

    try:
        if cluster is not None:
            vms = list(nb.virtualization.virtual_machines.filter(cluster_id=cluster.id))  # type: ignore[attr-defined]
        else:
            vms = list(nb.virtualization.virtual_machines.all())
    except (RequestError, requests.exceptions.RequestException) as exc:  # pragma: no cover - network failures are runtime only
        raise RuntimeError(f"Failed to query NetBox virtual machines: {exc}") from exc

    return _filter_avs(vms)


def _load_devices(nb: pynetbox.api.Api) -> list[object]:  # type: ignore[name-defined]
    """Fetch AVS-related physical devices."""

    try:
        devices = list(nb.dcim.devices.all())
    except (RequestError, requests.exceptions.RequestException) as exc:  # pragma: no cover - network failures are runtime only
        raise RuntimeError(f"Failed to query NetBox devices: {exc}") from exc

    return _filter_avs(devices)


def main() -> int:
    """Entry point for the ``boxinfo`` command."""

    try:
        address = _read_credential("address")
        token = _read_credential("token")
        user = _read_credential("user")
    except CredentialError as exc:
        print(f"[boxinfo] Credential error: {exc}", file=sys.stderr)
        return 2

    url = _normalise_url(address)

    try:
        nb = pynetbox.api(url, token=token)  # type: ignore[attr-defined]
    except Exception as exc:  # pragma: no cover - network failures are runtime only
        print(f"[boxinfo] Failed to initialise NetBox client: {exc}", file=sys.stderr)
        return 3

    # Provide the username for tracing purposes in the request headers.
    if user:
        nb.http_session.headers.setdefault("X-Boxinfo-User", user)  # type: ignore[attr-defined]

    try:
        _configure_http_session(nb.http_session)
    except ConfigurationError as exc:
        print(f"[boxinfo] {exc}", file=sys.stderr)
        return 5

    try:
        cluster = _load_cluster(nb)
        vms = _load_vms(nb, cluster)
        devices = _load_devices(nb)
    except RuntimeError as exc:
        print(f"[boxinfo] {exc}", file=sys.stderr)
        return 4

    verify_setting = getattr(nb.http_session, "verify", True)
    if verify_setting is False:
        verification_status = "disabled"
    elif isinstance(verify_setting, str):
        verification_status = f"custom bundle ({verify_setting})"
    else:
        verification_status = "enabled"

    lines = [
        f"NetBox URL: {url}",
        f"Queried as: {user}",
        f"SSL verification: {verification_status}",
    ]

    if cluster is not None:
        cluster_name = getattr(cluster, "name", getattr(cluster, "slug", "avs"))
        lines.append(f"Cluster: {cluster_name} (id={getattr(cluster, 'id', 'n/a')})")
    else:
        lines.append("Cluster: n/a (no cluster with name or slug 'avs' found)")

    lines.append("")

    if vms:
        lines.append("Virtual machines related to 'AVS':")
        for vm in sorted(vms, key=lambda item: getattr(item, "name", "")):
            lines.append(f"  - {_summarise_vm(vm)}")
    else:
        lines.append("No virtual machines related to 'AVS' were found.")

    lines.append("")

    if devices:
        lines.append("Devices related to 'AVS':")
        for device in sorted(devices, key=lambda item: getattr(item, "name", "")):
            lines.append(f"  - {_summarise_device(device)}")
    else:
        lines.append("No devices related to 'AVS' were found.")

    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    sys.exit(main())
