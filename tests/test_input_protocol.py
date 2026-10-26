import unittest

from agent_theme.input import InputObserver


class InputProtocolTests(unittest.TestCase):
    def test_commands_at_every_split(self):
        for data, expected in ((b'/clear\r', (True, True)),
                               (b'hello\r', (True, False)),
                               (b'\x1b[200~/clear\n\x1b[201~', (False, False)),
                               (b'\x1b[200~/clear\x1b[201~\r', (True, False))):
            for cut in range(len(data) + 1):
                observer = InputObserver()
                first = observer.feed(data[:cut])
                last = observer.feed(data[cut:])
                self.assertEqual(tuple(a or b for a, b in zip(first, last)), expected)

    def test_last_submission_determines_reset(self):
        observer = InputObserver()
        self.assertEqual(observer.feed(b'/clear\rhello\r'), (True, False))
        self.assertEqual(observer.feed(b'hello\r/clear\r'), (True, True))
        self.assertEqual(observer.feed(b'/clear\r\r'), (True, True))

    def test_utf8_split_and_backspace(self):
        observer = InputObserver()
        for byte in '界😀'.encode():
            observer.feed(bytes((byte,)))
        self.assertEqual(observer.typed, '界😀')
        observer.feed(b'\x7f')
        self.assertEqual(observer.typed, '界')
        self.assertFalse(observer.exact)
        observer.feed(b'\x15/clearr\x7f')
        self.assertEqual(observer.feed(b'\r'), (True, True))

    def test_unicode_whitespace_cannot_normalize_a_reset_command(self):
        for command in ('\u00a0/clear\r', '/clear\u2003\r'):
            self.assertEqual(InputObserver().feed(command.encode()), (True, False))
        self.assertEqual(InputObserver().feed(b' /clear \r'), (True, True))

    def test_navigation_cannot_create_command_candidate(self):
        for escape in (b'\x1b[A', b'\x1bOD', b'\x1b[3~', b'\x01', b'\t'):
            observer = InputObserver()
            for byte in escape + b'/clear\r':
                result = observer.feed(bytes((byte,)))
            self.assertEqual(result, (True, False))
            self.assertEqual(observer.feed(b'\x15/clear\r'), (True, True))

    def test_control_strings_do_not_become_text(self):
        for control in (b'\x1b]52;secret\x07', b'\x1bPsecret\x1b\\'):
            observer = InputObserver()
            for byte in control:
                observer.feed(bytes((byte,)))
            self.assertEqual(observer.typed, '')
            # Terminal reports must not mask a command typed afterwards.
            self.assertEqual(observer.feed(b'/clear\r'), (True, True))

    def test_terminal_reports_do_not_arm_a_bare_enter(self):
        reports = (
            b'\x1bP>|tmux 3.8\x1b\\',           # XTVERSION
            b'\x1b[?1;2;4c',                    # primary device attributes
            b'\x1b[>0;10;1c',                   # secondary device attributes
            b'\x1b[?2026;2$y',                  # DECRPM
            b'\x1b[?0u',                        # kitty keyboard flags
            b'\x1b]11;rgb:0000/0000/0000\x07',  # background colour
            b'\x1b[I', b'\x1b[O',               # focus in/out
            b'\x1b[4;600;800t',                 # window size report
        )
        for report in reports:
            with self.subTest(report=report):
                observer = InputObserver()
                observer.feed(report)
                self.assertTrue(observer.exact)
                self.assertEqual(observer.feed(b'\r'), (False, False))

    def test_navigation_still_arms_a_bare_enter(self):
        # Cursor-position reports are byte-identical to a modified F3 key, so
        # both remain conservative.
        for sequence in (b'\x1b[A', b'\x1bOD', b'\x1b[3~', b'\x1b[1;2R'):
            with self.subTest(sequence=sequence):
                observer = InputObserver()
                observer.feed(sequence)
                self.assertFalse(observer.exact)
                self.assertEqual(observer.feed(b'\r'), (True, False))

    def test_dcs_bel_does_not_terminate_control_string(self):
        observer = InputObserver()
        self.assertEqual(observer.feed(b'\x1bP\x07/clear\r'), (False, False))
        self.assertEqual(observer.typed, '')
        observer.feed(b'\x1b\\')
        self.assertEqual(observer.feed(b'/clear\r'), (True, True))

    def test_decoder_tail_survives_controls_in_same_chunk(self):
        observer = InputObserver()
        observer.feed(b'hello\r\xe7')
        observer.feed(b'\x95\x8c')
        self.assertEqual(observer.typed, '界')
        self.assertTrue(observer.exact)

    def test_bounded_input_never_recognizes_truncated_suffix(self):
        observer = InputObserver()
        observer.feed(b'x' * 100000 + b'/clear')
        self.assertLessEqual(len(observer.typed), 64)
        observer.feed(b'\x7f' * 100)
        self.assertEqual(observer.feed(b'/clear\r'), (True, False))

    def test_incomplete_utf8_cannot_confirm_command(self):
        observer = InputObserver()
        self.assertEqual(observer.feed(b'/clear\xe7\r'), (True, False))

    def test_unterminated_controls_are_bounded(self):
        observer = InputObserver()
        observer.feed(b'\x1b[' + b'1' * 100000)
        self.assertLessEqual(len(observer._csi), 8)
        observer.feed(b'~')
        self.assertEqual(observer.feed(b'/clear\r'), (True, False))


if __name__ == '__main__':
    unittest.main()
