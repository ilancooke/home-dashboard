"""Documented Monoprice 10761 RS-232 command and response handling."""

from dataclasses import asdict, dataclass
import re


ZONE_ADDRESSES = {zone: f"1{zone}" for zone in range(1, 7)}
ADDRESS_ZONES = {address: zone for zone, address in ZONE_ADDRESSES.items()}

# The manual defines eleven two-character fields after the response marker.
STATUS_PATTERN = re.compile(r">(?P<payload>\d{22})(?!\d)")


class ProtocolError(ValueError):
    """Raised when a command value or amplifier response is invalid."""


@dataclass(frozen=True)
class ZoneStatus:
    zone: int
    power: bool
    mute: bool
    volume: int
    treble: int
    bass: int
    balance: int
    source: int
    pa: bool
    do_not_disturb: bool
    keypad_connected: bool

    def to_dict(self):
        return asdict(self)


def _require_integer(name, value, minimum, maximum):
    if isinstance(value, bool) or not isinstance(value, int):
        raise ProtocolError(f"{name} must be an integer")
    if not minimum <= value <= maximum:
        raise ProtocolError(f"{name} must be between {minimum} and {maximum}")
    return value


def address_for_zone(zone):
    _require_integer("zone", zone, 1, 6)
    return ZONE_ADDRESSES[zone]


def build_query(zone):
    return f"?{address_for_zone(zone)}\r".encode("ascii")


def build_control(zone, command, value, minimum, maximum):
    value = _require_integer(command, value, minimum, maximum)
    return f"<{address_for_zone(zone)}{command}{value:02d}\r".encode("ascii")


def build_power_command(zone, on):
    if not isinstance(on, bool):
        raise ProtocolError("on must be a boolean")
    return build_control(zone, "PR", int(on), 0, 1)


def build_mute_command(zone, muted):
    if not isinstance(muted, bool):
        raise ProtocolError("muted must be a boolean")
    return build_control(zone, "MU", int(muted), 0, 1)


def build_source_command(zone, source):
    return build_control(zone, "CH", source, 1, 6)


def build_volume_command(zone, volume):
    return build_control(zone, "VO", volume, 0, 38)


def build_treble_command(zone, treble):
    return build_control(zone, "TR", treble, 0, 14)


def build_bass_command(zone, bass):
    return build_control(zone, "BS", bass, 0, 14)


def build_balance_command(zone, balance):
    return build_control(zone, "BL", balance, 0, 20)


def _parse_boolean(name, raw_value):
    if raw_value not in ("00", "01"):
        raise ProtocolError(f"invalid {name} status: {raw_value}")
    return raw_value == "01"


def parse_status_response(response):
    """Extract the last valid full-zone status from echo and prompt noise."""
    if isinstance(response, bytes):
        response = response.decode("ascii", errors="ignore")
    if not isinstance(response, str):
        raise ProtocolError("status response must be bytes or text")

    matches = list(STATUS_PATTERN.finditer(response))
    if not matches:
        raise ProtocolError("no full zone status found in amplifier response")

    last_error = None
    for match in reversed(matches):
        try:
            payload = match.group("payload")
            fields = [payload[index:index + 2] for index in range(0, 22, 2)]
            address, pa, power, mute, dnd, volume, treble, bass, balance, source, keypad = fields

            if address not in ADDRESS_ZONES:
                raise ProtocolError(f"unknown zone address: {address}")

            volume_value = int(volume)
            treble_value = int(treble)
            bass_value = int(bass)
            balance_value = int(balance)
            source_value = int(source)

            _require_integer("volume", volume_value, 0, 38)
            _require_integer("treble", treble_value, 0, 14)
            _require_integer("bass", bass_value, 0, 14)
            _require_integer("balance", balance_value, 0, 20)
            _require_integer("source", source_value, 0, 6)

            return ZoneStatus(
                zone=ADDRESS_ZONES[address],
                pa=_parse_boolean("PA", pa),
                power=_parse_boolean("power", power),
                mute=_parse_boolean("mute", mute),
                do_not_disturb=_parse_boolean("do-not-disturb", dnd),
                volume=volume_value,
                treble=treble_value,
                bass=bass_value,
                balance=balance_value,
                source=source_value,
                keypad_connected=_parse_boolean("keypad", keypad),
            )
        except ProtocolError as error:
            last_error = error

    raise last_error or ProtocolError("malformed amplifier status")
