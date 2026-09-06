"""Thread-safe serial controller for one Monoprice 10761 amplifier."""

import logging
import re
import threading
import time

import serial

from .protocol import (
    ProtocolError,
    address_for_zone,
    build_balance_command,
    build_bass_command,
    build_mute_command,
    build_power_command,
    build_query,
    build_source_command,
    build_treble_command,
    build_volume_command,
    parse_status_response,
)


LOG = logging.getLogger(__name__)


class AudioControllerError(RuntimeError):
    """Base class for recoverable amplifier communication errors."""


class AudioUnavailableError(AudioControllerError):
    """The serial adapter cannot currently be opened or used."""


class AudioTimeoutError(AudioControllerError):
    """The amplifier did not return a complete response in time."""

    def __init__(self, message, response=b""):
        super().__init__(message)
        self.response = response


class AudioResponseError(AudioControllerError):
    """The amplifier returned a response that could not be parsed."""


class MonopriceController:
    """Own a shared serial connection and serialize every transaction."""

    def __init__(
        self,
        port="/dev/ttyUSB0",
        baudrate=9600,
        response_timeout=1.0,
        serial_factory=None,
    ):
        self.port = port
        self.baudrate = baudrate
        self.response_timeout = response_timeout
        self._serial_factory = serial_factory or serial.Serial
        self._serial = None
        self._lock = threading.Lock()

    def _connect_locked(self):
        if self._serial is not None and getattr(self._serial, "is_open", True):
            return

        self._close_locked()
        LOG.info("Opening audio serial port %s", self.port)
        self._serial = self._serial_factory(
            port=self.port,
            baudrate=self.baudrate,
            bytesize=serial.EIGHTBITS,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
            timeout=0.1,
            write_timeout=self.response_timeout,
        )

    def _close_locked(self):
        connection = self._serial
        self._serial = None
        if connection is None:
            return
        try:
            connection.close()
        except (OSError, serial.SerialException):
            LOG.debug("Error while closing audio serial port", exc_info=True)

    def close(self):
        with self._lock:
            self._close_locked()

    def _run_transaction(self, operation):
        with self._lock:
            for attempt in range(2):
                try:
                    self._connect_locked()
                    return operation()
                except (OSError, serial.SerialException) as error:
                    LOG.warning("Audio serial transaction failed: %s", error)
                    self._close_locked()
                    if attempt == 1:
                        raise AudioUnavailableError(
                            f"audio serial port {self.port} is unavailable"
                        ) from error

    def _write_locked(self, command):
        self._serial.write(command)
        self._serial.flush()

    def _read_until_locked(self, predicate, timeout=None):
        timeout = self.response_timeout if timeout is None else timeout
        deadline = time.monotonic() + timeout
        response = bytearray()

        while time.monotonic() < deadline:
            waiting = getattr(self._serial, "in_waiting", 0)
            chunk = self._serial.read(waiting or 1)
            if chunk:
                response.extend(chunk)
                result = predicate(bytes(response))
                if result is not None:
                    return result

        raise AudioTimeoutError(
            "amplifier response timed out",
            response=bytes(response),
        )

    def _query_zone_locked(self, zone):
        self._serial.reset_input_buffer()
        self._write_locked(build_query(zone))

        def find_status(response):
            try:
                status = parse_status_response(response)
            except ProtocolError:
                return None
            return status if status.zone == zone else None

        try:
            return self._read_until_locked(find_status)
        except AudioTimeoutError as error:
            if b">" in error.response:
                raise AudioResponseError(
                    f"malformed status received for zone {zone}"
                ) from error
            raise

    def _set_and_query_locked(self, zone, command):
        self._serial.reset_input_buffer()
        self._write_locked(command)

        address = address_for_zone(zone)
        command_text = command.decode("ascii").strip("\r")
        reply_text = ">" + command_text[1:]
        reply_pattern = re.compile(re.escape(reply_text).encode("ascii") + rb"(?!\d)")

        try:
            self._read_until_locked(
                lambda response: True if reply_pattern.search(response) else None,
                timeout=min(0.25, self.response_timeout),
            )
        except AudioTimeoutError:
            # Some firmware revisions do not acknowledge setters consistently.
            # The documented zone query below verifies the resulting state.
            LOG.debug("No control acknowledgement received for %s", command_text)
        return self._query_zone_locked(zone)

    def get_zone_status(self, zone):
        address_for_zone(zone)
        status = self._run_transaction(lambda: self._query_zone_locked(zone))
        return status.to_dict()

    def get_all_zone_statuses(self):
        def query_all():
            return [self._query_zone_locked(zone).to_dict() for zone in range(1, 7)]

        return self._run_transaction(query_all)

    def _set(self, zone, command):
        status = self._run_transaction(
            lambda: self._set_and_query_locked(zone, command)
        )
        return status.to_dict()

    def set_power(self, zone, on):
        return self._set(zone, build_power_command(zone, on))

    def set_source(self, zone, source):
        return self._set(zone, build_source_command(zone, source))

    def set_volume(self, zone, volume):
        return self._set(zone, build_volume_command(zone, volume))

    def set_mute(self, zone, muted):
        return self._set(zone, build_mute_command(zone, muted))

    def set_treble(self, zone, treble):
        return self._set(zone, build_treble_command(zone, treble))

    def set_bass(self, zone, bass):
        return self._set(zone, build_bass_command(zone, bass))

    def set_balance(self, zone, balance):
        return self._set(zone, build_balance_command(zone, balance))
