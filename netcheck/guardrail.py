"""FR-02 mandatory guardrail.

A live scan target is allowed ONLY if:
  1. it parses as an IP / CIDR range,
  2. every address in it is private (RFC1918 etc.) — public, CGNAT (100.64/10, mobile
     operator), multicast, loopback, link-local and reserved ranges are refused,
  3. it is fully inside the allowlist (default: the subnet this laptop is connected to;
     extra private ranges via NETCHECK_ALLOWLIST or --allow),
  4. the caller passed an explicit confirmation (--confirm).
"""
from __future__ import annotations

import ipaddress
import os

MAX_HOSTS = 1024  # refuse anything bigger than a /22 even if private


class ScopeError(Exception):
    """Message is shown to the user as-is."""


def _net(text: str) -> ipaddress.IPv4Network | ipaddress.IPv6Network:
    try:
        return ipaddress.ip_network(text.strip(), strict=False)
    except ValueError:
        raise ScopeError(f"'{text}' is not a valid IP address or range") from None


def _is_safe_private(net) -> bool:
    for addr in (net.network_address, net.broadcast_address):
        if not addr.is_private or addr.is_loopback or addr.is_multicast or addr.is_link_local \
                or addr.is_reserved or addr.is_unspecified:
            return False
    # 100.64.0.0/10 is "shared address space" (carrier NAT) — never ours.
    if net.version == 4 and net.overlaps(ipaddress.ip_network("100.64.0.0/10")):
        return False
    return True


def build_allowlist(connected_subnet: str | None, extra: list[str] | None = None) -> list:
    nets = []
    if connected_subnet:
        nets.append(_net(connected_subnet))
    env_extra = [x for x in os.environ.get("NETCHECK_ALLOWLIST", "").split(",") if x.strip()]
    for item in (extra or []) + env_extra:
        n = _net(item)
        if not _is_safe_private(n):
            raise ScopeError(f"allowlist entry {n} is not a private range — refused")
        nets.append(n)
    return nets


def check_target(target: str, allowlist: list, confirmed: bool) -> str:
    """Return the normalised target or raise ScopeError."""
    net = _net(target)
    if not _is_safe_private(net):
        raise ScopeError(f"REFUSED: {net} contains public or non-local addresses. "
                         "This tool only scans your own private network.")
    if net.num_addresses > MAX_HOSTS:
        raise ScopeError(f"REFUSED: {net} is too large ({net.num_addresses} addresses). Scan your own subnet only.")
    if not allowlist:
        raise ScopeError("REFUSED: no allowlist (could not detect your network). Connect to your hotspot first.")
    if not any(net.version == a.version and net.subnet_of(a) for a in allowlist):
        allowed = ", ".join(str(a) for a in allowlist)
        raise ScopeError(f"REFUSED: {net} is outside the allowlist ({allowed}). "
                         "You may only scan the network you are connected to and own.")
    if not confirmed:
        raise ScopeError(f"{net} is in scope, but a live scan needs explicit consent: add --confirm "
                         "(you confirm you own every device on this network).")
    return str(net)
