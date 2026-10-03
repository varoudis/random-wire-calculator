"""Numerical regression checks; run with python -m unittest -v."""

import argparse
import math
import unittest

from random_wire import (
    BANDS, CORE, blocked_ranges, finite_nonnegative, finite_positive,
    halfwaves, merge_intervals, resonance_ranges, unflagged_ranges,
)


class CalculationTests(unittest.TestCase):
    def test_all_multiples_and_display_clipping(self):
        for band in BANDS.values():
            for maximum in (5, 25, 65, 135, 250, 1000):
                with self.subTest(band=band.name, maximum=maximum):
                    expected = [
                        (n, n * 468 / band.high_mhz, min(maximum, n * 468 / band.low_mhz))
                        for n in range(1, 100)
                        if n * 468 / band.high_mhz <= maximum
                    ]
                    self.assertEqual(halfwaves(band, maximum), expected)

    def test_original_missing_multiples_are_present(self):
        expected_counts = {"40": 2, "30": 2, "20": 4, "17": 5, "15": 6, "12": 7, "10": 8}
        for name, count in expected_counts.items():
            self.assertEqual(len(halfwaves(BANDS[name], 135)), count)
        bands = [BANDS[name] for name in CORE]
        blocked = blocked_ranges(bands, 135)
        self.assertTrue(any(low <= 98 <= high for low, high in blocked))
        self.assertFalse(any(low < 98 < high for low, high in unflagged_ranges(blocked, 135)))

    def test_quarter_wave_guide_uses_lowest_selected_frequency(self):
        bands = [BANDS[name] for name in CORE]
        self.assertAlmostEqual(blocked_ranges(bands, 135)[0][1], 468 / 7 / 2)
        self.assertAlmostEqual(blocked_ranges(bands + [BANDS["80"]], 135)[0][1], 468 / 3.5 / 2)
        self.assertEqual(blocked_ranges(bands, 5), [(0, 5)])

    def test_overlapping_intervals_and_gap_complements(self):
        self.assertEqual(merge_intervals([(3, 5), (1, 3), (2, 4), (8, 9)]), [(1, 5), (8, 9)])
        self.assertEqual(unflagged_ranges([(0, 5), (10, 15)], 20), [(5, 10), (15, 20)])
        for maximum in (5, 135, 250):
            blocked = blocked_ranges(list(BANDS.values()), maximum)
            gaps = unflagged_ranges(blocked, maximum)
            total = sum(high - low for low, high in blocked + gaps)
            self.assertAlmostEqual(total, maximum)
            self.assertTrue(all(0 <= low <= high <= maximum for low, high in blocked + gaps))

    def test_padding_includes_intervals_just_outside_display(self):
        # First 20 m half-wave begins just above 32 ft, but 1 ft padding reaches in.
        spans = resonance_ranges(BANDS["20"], 32, 1)
        self.assertEqual(len(spans), 1)
        self.assertAlmostEqual(spans[0][0], 468 / 14.35 - 1)
        self.assertEqual(spans[0][1], 32)
        self.assertEqual(resonance_ranges(BANDS["20"], 32), [])

    def test_invalid_lengths_rejected(self):
        for value in ("nan", "inf", "-inf", "-1"):
            for converter in (finite_positive, finite_nonnegative):
                with self.assertRaises(argparse.ArgumentTypeError):
                    converter(value)
        with self.assertRaises(argparse.ArgumentTypeError):
            finite_positive("0")
        self.assertEqual(finite_nonnegative("0"), 0)
        self.assertTrue(math.isfinite(finite_positive("135")))


if __name__ == "__main__":
    unittest.main()
