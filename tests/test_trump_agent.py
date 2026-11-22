import unittest
from trump_agent import TrumpAgent, calculate


class FakeNews:
    def search(self, query):
        return []


class AgentTests(unittest.TestCase):
    def test_arithmetic(self):
        self.assertEqual(calculate('2 + 3 * 4'), 14)
        self.assertEqual(calculate('2^3'), 8)

    def test_reject_unsafe_expression(self):
        for expr in ('__import__("os")', '2**100', '1/0'):
            with self.assertRaises((ValueError, ZeroDivisionError)):
                calculate(expr)

    def test_normal_chat_has_no_tools(self):
        result = TrumpAgent(FakeNews()).prepare('سلام')
        self.assertEqual(result.tool_names, [])

    def test_calculator_tool(self):
        result = TrumpAgent(FakeNews()).prepare('حساب کن 20 * 3')
        self.assertIn('calculator', result.tool_names)
        self.assertIn('60', result.context)


if __name__ == '__main__':
    unittest.main()
