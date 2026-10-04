import unittest

from app.calculator.math_calc import calculate
from app.calculator.parser import CommandParser
from app.calculator.unit_converter import convert
from app.calculator.lc_calc import calculate_lc


class CalculatorTests(unittest.TestCase):
    def test_math_functions_precedence(self):
        self.assertAlmostEqual(calculate("(25*3.3)/7"), 11.785714285714286)
        self.assertEqual(calculate("-2^2"), -4)
        self.assertEqual(calculate("2^3^2"), 512)
        self.assertAlmostEqual(calculate("sqrt(9)+sin(pi/2)+cos(0)+tan(0)+log(e)"), 6)

    def test_reject_unsafe_or_expensive_input(self):
        for text in ("__import__('os')", "(1).__class__", "[1][0]", "True+1", "sqrt(x=2)",
                     "2**10000", "1e999", "0^-1", "sqrt(-1)", "1/0", "2^0.5j", "10" * 200):
            with self.subTest(text=text), self.assertRaises(ValueError):
                calculate(text)

    def test_units_all_dimensions(self):
        for text, expected in (("25 mm to inch", "0.9842519685 inch"), ("10 cm to m", "0.1 m"),
                               ("2.4 GHz to MHz", "2400 MHz"), ("1 s to ns", "1000000000 ns"),
                               ("1 uF to fF", "1000000000 fF"), ("2 nH to pH", "2000 pH")):
            self.assertEqual(convert(text), expected)
        with self.assertRaises(ValueError):
            convert("1 GHz to nH")

    def test_lc_three_directions_and_invalid(self):
        self.assertEqual(calculate_lc("6GHz 1nH"), "C = 703.62 fF")
        self.assertEqual(calculate_lc("6GHz 700fF"), "L = 1.0052 nH")
        self.assertEqual(calculate_lc("1nH 700fF"), "f = 6.0155 GHz")
        for text in ("0GHz 1nH", "-1nH 700fF", "1nH 2nH", "1cm 1nH"):
            with self.assertRaises(ValueError):
                calculate_lc(text)

    def test_command_dispatch(self):
        parser = CommandParser()
        self.assertEqual(parser.parse("/note 明天检查 VCO").kind, "note")
        self.assertEqual(parser.parse("6GHz 1nH").text, "C = 703.62 fF")
        self.assertFalse(parser.parse("/note").ok)
        self.assertFalse(parser.parse("/unknown").ok)


if __name__ == "__main__":
    unittest.main()
