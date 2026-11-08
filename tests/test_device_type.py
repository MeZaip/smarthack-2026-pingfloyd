"""guess_type: the device name beats the maker (a MacBook is not a phone, a Galaxy phone is not a TV)."""
import pytest

from netcheck.core.device import guess_type
from netcheck.core.models import Host, Port


def host(vendor=None, names=(), ports=()):
    return Host(ip="192.168.1.20", vendor=vendor, hostnames=list(names),
                ports=[Port("tcp", p, "open", s) for p, s in ports])


@pytest.mark.parametrize("vendor, names, expected", [
    ("Apple", ["Stefans-MacBook-Air.local"], "computer"),
    ("Apple", ["iMac-de-acasa"], "computer"),
    ("Apple", ["Mac-mini"], "computer"),
    ("Apple", ["Ana-iPhone"], "phone"),
    ("Apple", [], "phone"),                                  # no name: the maker decides, as before
    ("Samsung Electronics", ["Galaxy-S23"], "phone"),
    ("Samsung Electronics", ["android-3f2a9c"], "phone"),
    ("Samsung Electronics", [], "tv"),                       # unchanged without a name
    ("Google", ["Pixel-8"], "phone"),
    ("Raspberry Pi Trading", ["raspberrypi"], "iot"),
    (None, ["DESKTOP-4KQ7"], "unknown"),
])
def test_name_then_vendor(vendor, names, expected):
    assert guess_type(host(vendor, names)) == expected


def test_ports_still_win_over_the_name():
    # an "iPhone" name on a device that serves RTSP video is still a camera
    assert guess_type(host("Apple", ["iphone-cam"], [(554, "rtsp")])) == "camera"


def test_gateway_is_always_the_router():
    assert guess_type(host("Apple", ["MacBook"]), is_gateway=True) == "router"
