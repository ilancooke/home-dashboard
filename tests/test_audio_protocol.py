import unittest

from modules.audio.protocol import (
    ProtocolError,
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


class AudioProtocolTests(unittest.TestCase):
    def test_parses_status_from_echo_and_prompt_noise(self):
        response = b"?11\r\n#>1100010000150707100101\r\r\n#"

        status = parse_status_response(response)

        self.assertEqual(status.zone, 1)
        self.assertTrue(status.power)
        self.assertFalse(status.mute)
        self.assertEqual(status.volume, 15)
        self.assertEqual(status.treble, 7)
        self.assertEqual(status.bass, 7)
        self.assertEqual(status.balance, 10)
        self.assertEqual(status.source, 1)
        self.assertFalse(status.pa)
        self.assertFalse(status.do_not_disturb)
        self.assertTrue(status.keypad_connected)

    def test_rejects_malformed_status(self):
        with self.assertRaises(ProtocolError):
            parse_status_response("?11\r\n#>11000100001507\r\n#")

    def test_parses_confirmed_powered_off_hardware_response(self):
        status = parse_status_response(">1100000000150707100201")

        self.assertFalse(status.power)
        self.assertFalse(status.mute)
        self.assertEqual(status.volume, 15)
        self.assertEqual(status.source, 2)

    def test_builds_only_documented_zone_commands(self):
        self.assertEqual(build_query(1), b"?11\r")
        self.assertEqual(build_query(6), b"?16\r")
        self.assertEqual(build_power_command(1, True), b"<11PR01\r")
        self.assertEqual(build_mute_command(2, False), b"<12MU00\r")
        self.assertEqual(build_source_command(3, 6), b"<13CH06\r")
        self.assertEqual(build_volume_command(4, 38), b"<14VO38\r")
        self.assertEqual(build_treble_command(5, 14), b"<15TR14\r")
        self.assertEqual(build_bass_command(6, 0), b"<16BS00\r")
        self.assertEqual(build_balance_command(1, 10), b"<11BL10\r")

    def test_rejects_out_of_range_command_values(self):
        invalid_commands = (
            lambda: build_query(7),
            lambda: build_source_command(1, 0),
            lambda: build_volume_command(1, 39),
            lambda: build_treble_command(1, -1),
            lambda: build_bass_command(1, 15),
            lambda: build_balance_command(1, 21),
        )
        for command in invalid_commands:
            with self.subTest(command=command):
                with self.assertRaises(ProtocolError):
                    command()


if __name__ == "__main__":
    unittest.main()
