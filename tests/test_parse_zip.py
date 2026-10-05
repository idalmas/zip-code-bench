"""Answer-parsing cases, taken from reply shapes seen in real runs (see results/runs/)."""

import unittest

from run_eval import parse_zip

ADDR = "20830 Clay Landing Lane, Katy, TX"


class ParseZip(unittest.TestCase):
    def test_bare_zip(self):
        self.assertEqual(parse_zip("77449", ADDR), "77449")

    def test_leading_zero(self):
        self.assertEqual(parse_zip("07077", "41 Main Street, Sewaren, NJ"), "07077")

    def test_zip_plus_four(self):
        self.assertEqual(parse_zip("77449-1234", ADDR), "77449")

    def test_hedged_then_answer(self):
        text = "I don't have reliable information about this address. My best guess would be:\n\n77449"
        self.assertEqual(parse_zip(text, ADDR), "77449")

    def test_several_zips_final_answer_last(self):
        text = "Rosenberg, TX has ZIP codes 77471 and 77469. Downtown Rosenberg is in 77471.\n\n77471"
        self.assertEqual(parse_zip(text, "100 1st Street, Rosenberg, TX"), "77471")

    def test_correction_takes_last(self):
        self.assertEqual(parse_zip("Not 77450, it's 77449.", ADDR), "77449")

    def test_house_number_after_answer_is_ignored(self):
        text = "**77449**\n\nI'm not certain, but a 20830 address in Katy most likely falls in 77449's area, near 20830"
        self.assertEqual(parse_zip(text, ADDR), "77449")

    def test_house_number_only_is_not_an_answer(self):
        self.assertIsNone(parse_zip("45795", "45795 South Loon Lake, Loon Lake, WA"))

    def test_refusal(self):
        self.assertIsNone(parse_zip("I don't know the ZIP code for that address.", ADDR))

    def test_empty_reply(self):
        self.assertIsNone(parse_zip("", ADDR))

    def test_longer_digit_runs_are_not_zips(self):
        self.assertIsNone(parse_zip("Call 7135551234 for details", ADDR))


if __name__ == "__main__":
    unittest.main()
