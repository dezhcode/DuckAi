import unittest
from duck_search import is_web_search, sources_from_event, format_sources


class DuckSearchTests(unittest.TestCase):
    def test_detects_native_search(self):
        self.assertTrue(is_web_search({'toolName': 'WebSearch', 'state': 'completed'}))
        self.assertFalse(is_web_search({'toolName': 'GenerateImage'}))

    def test_extracts_only_explicit_https_urls(self):
        event = {'toolName': 'WebSearch', 'toolResult': {
            'results': [{'url': 'https://example.org/article'},
                        {'url': 'http://unsafe.example.org'},
                        {'url': 'https://example.org/article'}]}}
        self.assertEqual(sources_from_event(event), ['https://example.org/article'])

    def test_no_invented_sources(self):
        self.assertEqual(sources_from_event({'toolName': 'WebSearch',
            'toolArguments': {'query': 'latest news'}}), [])
        self.assertEqual(format_sources([]), '')

    def test_embedded_json_results(self):
        event = {'toolName': 'WebSearch', 'output': '[{"link":"https://example.com/a"}]'}
        self.assertIn('https://example.com/a', format_sources(sources_from_event(event)))


if __name__ == '__main__':
    unittest.main()
