import unittest
from contrast import contrast, luminance, text_color


class ContrastTests(unittest.TestCase):
    def test_extremes_symmetry_and_identical_colors(self):
        self.assertEqual(luminance("#000000"), 0)
        self.assertAlmostEqual(luminance("#ffffff"), 1)
        self.assertAlmostEqual(contrast("#000000", "#ffffff"), 21)
        self.assertAlmostEqual(contrast("#1d4ed8", "#ffffff"), contrast("#ffffff", "#1d4ed8"))
        self.assertEqual(contrast("#123456", "#123456"), 1)

    def test_rounding_does_not_pass_below_threshold(self):
        self.assertLess(contrast("#777777", "#ffffff"), 4.5)
        self.assertGreaterEqual(contrast("#767676", "#ffffff"), 4.5)

    def test_documented_fallback_pairs_and_text_choice(self):
        for background in ("#1d4ed8", "#166534", "#b91c1c"):
            self.assertGreaterEqual(contrast("#ffffff", background), 4.5)
        for background in ("#ffffff", "#000000", "#abcdef", "#777777"):
            self.assertGreaterEqual(contrast(text_color(background), background), 4.5)

    def test_invalid_and_alpha_colors_are_refused(self):
        for color in (None, "#fff", "red", "#ffffff00", "#GGGGGG", "ffffff"):
            with self.assertRaises(ValueError):
                luminance(color)


if __name__ == "__main__":
    unittest.main()
