import threading
import time
import unittest

import serial

from modules.audio.controller import MonopriceController


class FakeSerial:
    def __init__(self, **_kwargs):
        self.is_open = True
        self._response = bytearray()
        self._guard = threading.Lock()
        self.concurrent_writes = False
        self.writes = []
        self.power = {zone: False for zone in range(1, 7)}
        self.send_control_reply = True

    @property
    def in_waiting(self):
        return len(self._response)

    def reset_input_buffer(self):
        self._response.clear()

    def write(self, command):
        if not self._guard.acquire(blocking=False):
            self.concurrent_writes = True
            return
        try:
            time.sleep(0.002)
            self.writes.append(command)
            text = command.decode("ascii").rstrip("\r")
            address = text[1:3]
            zone = int(address[1])
            if text.startswith("<"):
                code = text[3:5]
                value = text[5:7]
                if code == "PR":
                    self.power[zone] = value == "01"
                if self.send_control_reply:
                    self._response.extend(command + b"\n#>" + text[1:].encode("ascii") + b"\r\r\n#")
            else:
                power = "01" if self.power[zone] else "00"
                payload = address + "00" + power + "00" + "00" + "15" + "07" + "07" + "10" + "01" + "01"
                self._response.extend(command + b"\n#>" + payload.encode("ascii") + b"\r\r\n#")
            return len(command)
        finally:
            self._guard.release()

    def flush(self):
        pass

    def read(self, size):
        data = bytes(self._response[:size])
        del self._response[:size]
        return data

    def close(self):
        self.is_open = False


class AudioControllerTests(unittest.TestCase):
    def test_queries_without_real_hardware(self):
        fake = FakeSerial()
        controller = MonopriceController(serial_factory=lambda **kwargs: fake)

        status = controller.get_zone_status(1)

        self.assertEqual(status["zone"], 1)
        self.assertEqual(status["volume"], 15)
        self.assertEqual(fake.writes, [b"?11\r"])

    def test_setter_waits_for_reply_and_returns_fresh_status(self):
        fake = FakeSerial()
        controller = MonopriceController(serial_factory=lambda **kwargs: fake)

        status = controller.set_power(1, True)

        self.assertTrue(status["power"])
        self.assertEqual(fake.writes, [b"<11PR01\r", b"?11\r"])

    def test_setter_verifies_state_when_acknowledgement_is_missing(self):
        fake = FakeSerial()
        fake.send_control_reply = False
        controller = MonopriceController(
            serial_factory=lambda **kwargs: fake,
            response_timeout=0.01,
        )

        status = controller.set_power(1, True)

        self.assertTrue(status["power"])
        self.assertEqual(fake.writes, [b"<11PR01\r", b"?11\r"])

    def test_retries_connection_after_serial_failure(self):
        fake = FakeSerial()
        attempts = []

        def factory(**_kwargs):
            attempts.append(True)
            if len(attempts) == 1:
                raise serial.SerialException("adapter missing")
            return fake

        controller = MonopriceController(serial_factory=factory)

        self.assertEqual(controller.get_zone_status(1)["zone"], 1)
        self.assertEqual(len(attempts), 2)

    def test_concurrent_requests_share_one_transaction_lock(self):
        fake = FakeSerial()
        controller = MonopriceController(serial_factory=lambda **kwargs: fake)
        threads = [
            threading.Thread(target=controller.get_zone_status, args=(zone,))
            for zone in range(1, 7)
        ]

        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        self.assertFalse(fake.concurrent_writes)
        self.assertEqual(len(fake.writes), 6)


if __name__ == "__main__":
    unittest.main()
