import unittest
from unittest.mock import Mock
from agent_search import WebSearch, requested_web_query, render_results
from trump_agent import TrumpAgent


class WebToolTests(unittest.TestCase):
    def test_explicit_search(self):
        self.assertEqual(requested_web_query('جستجو کن Python 3.14'), 'Python 3.14')
        self.assertIsNone(requested_web_query('سلام'))

    def test_disabled_search(self):
        self.assertEqual(WebSearch('').search('example'), [])

    def test_bounded_two_step_search(self):
        news = Mock()
        news.search.return_value = []
        web = Mock()
        web.enabled = True
        web.search.side_effect = [
            [{'title': 'Result', 'snippet': 'Evidence', 'url': 'https://example.org/1'}],
            [{'title': 'Followup', 'snippet': 'More', 'url': 'https://example.org/2'}]
        ]
        result = TrumpAgent(news, web).prepare('search for detailed information about Python versions')
        self.assertIn('web_search', result.tool_names)
        self.assertIn('web_search_followup', result.tool_names)
        self.assertIn('https://example.org/2', result.context)
        self.assertEqual(web.search.call_count, 2)

    def test_render_empty(self):
        self.assertEqual(render_results([]), '')


if __name__ == '__main__':
    unittest.main()
