"""FR-02 mandatory guardrail.

A live scan target is allowed ONLY if:
  1. it parses as an IP / CIDR range,
  2. every address in it is private — public, carrier-NAT (100.64/10, the mobile operator),
     multicast, loopback, link-local and reserved ranges are refused,
  3. it is no bigger than MAX_HOSTS addresses,
  4. it is fully inside the allowlist (default: the subnet this laptop is connected to;
     extra PRIVATE ranges via NETCHECK_ALLOWLIST or --allow),
  5. the caller passed an explicit confirmation (--confirm).
"""
from __future__ import annotations

import ipaddress
import os

MAX_HOSTS = 1024  # refuse anything bigger than a /22 even if private
_CGNAT = ipaddress.ip_network("100.64.0.0/10")


class ScopeError(Exception):
    """Refusal shown to the user. str() is English; message('ro') gives Romanian."""

    def __init__(self, en: str, ro: str):
        super().__init__(en)
        self.en, self.ro = en, ro

    def message(self, lang: str = "en") -> str:
        return self.ro if lang == "ro" else self.en


def _net(text: str):
    try:
        return ipaddress.ip_network(str(text).strip(), strict=False)
    except ValueError:
        raise ScopeError(f"'{text}' is not a valid IP address or range",
                         f"„{text}” nu este o adresă IP sau o rețea validă") from None


def is_safe_private(net) -> bool:
    for addr in (net.network_address, net.broadcast_address):
        if (not addr.is_private or addr.is_loopback or addr.is_multicast or addr.is_link_local
                or addr.is_reserved or addr.is_unspecified):
            return False
    return not (net.version == 4 and net.overlaps(_CGNAT))


def build_allowlist(connected_subnet: str | None, extra: list[str] | None = None) -> list:
    nets = [_net(connected_subnet)] if connected_subnet else []
    env_extra = [x for x in os.environ.get("NETCHECK_ALLOWLIST", "").split(",") if x.strip()]
    for item in (extra or []) + env_extra:
        n = _net(item)
        if not is_safe_private(n):
            raise ScopeError(f"allowlist entry {n} is not a private range — refused",
                             f"intrarea {n} din allowlist nu este o rețea privată — refuzat")
        nets.append(n)
    return nets


def check_target(target: str, allowlist: list, confirmed: bool) -> str:
    """Return the normalised target (e.g. '172.20.10.0/28') or raise ScopeError."""
    net = _net(target)
    if not is_safe_private(net):
        raise ScopeError(
            f"REFUSED: {net} contains public or non-local addresses. This tool only scans your own private network.",
            f"REFUZAT: {net} conține adrese publice sau din afara rețelei locale. "
            "Acest program scanează doar rețeaua ta privată.")
    if net.num_addresses > MAX_HOSTS:
        raise ScopeError(
            f"REFUSED: {net} is too large ({net.num_addresses} addresses). Scan your own subnet only.",
            f"REFUZAT: {net} este prea mare ({net.num_addresses} adrese). Scanează doar rețeaua ta.")
    if not allowlist:
        raise ScopeError("REFUSED: no allowlist (could not detect your network). Connect to your hotspot first.",
                         "REFUZAT: nu există allowlist (nu ți-am găsit rețeaua). Conectează-te întâi la hotspot.")
    if not any(net.version == a.version and net.subnet_of(a) for a in allowlist):
        allowed = ", ".join(str(a) for a in allowlist)
        raise ScopeError(
            f"REFUSED: {net} is outside the allowlist ({allowed}). "
            "You may only scan the network you are connected to and own.",
            f"REFUZAT: {net} este în afara allowlist-ului ({allowed}). "
            "Poți scana doar rețeaua la care ești conectat și care îți aparține.")
    if not confirmed:
        raise ScopeError(
            f"{net} is in scope, but a live scan needs explicit consent: add --confirm "
            "(you confirm you own every device on this network).",
            f"{net} este permisă, dar scanarea are nevoie de acordul tău explicit: adaugă --confirm "
            "(confirmi că toate dispozitivele din rețea sunt ale tale).")
    return str(net)
