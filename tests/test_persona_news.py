import unittest
from datetime import datetime, timedelta, timezone
from email.utils import format_datetime
from unittest.mock import Mock, patch

import news_reader as news
import trump_persona as persona
from telegram_bot import Bot
from test_telegram_bot import FakeAPI, EventClient
from duck_cli import DuckAIError

NOW = datetime(2026, 11, 15, 8, 0, tzinfo=timezone.utc)


def feed(title='Iran news report', age=1, url='https://www.bbc.com/news/example'):
    date = format_datetime(NOW - timedelta(hours=age))
    return f'<rss><channel><item><title>{title}</title><link>{url}</link><pubDate>{date}</pubDate><description>Report about Iran negotiations</description></item></channel></rss>'.encode()


def report(**overrides):
    values = dict(publisher='BBC', group='BBC', title='گزارش درباره ایران', url='https://www.bbc.com/news/example', published=NOW, summary='گفتگو درباره مذاکرات', article='')
    values.update(overrides)
    return news.NewsItem(**values)


class NewsTests(unittest.TestCase):
    def test_filters_stale_future_and_unsafe_feed_links(self):
        self.assertEqual(len(news.parse_feed(feed(), 'BBC', 'BBC', NOW)), 1)
        for data in (feed(age=73), feed(age=-1), feed(url='https://127.0.0.1/a'), feed(url='http://www.bbc.com/a')):
            self.assertEqual(news.parse_feed(data, 'BBC', 'BBC', NOW), [])
        self.assertEqual(news.parse_feed(b'<!DOCTYPE rss><rss/>', 'BBC', 'BBC', NOW), [])

    def test_redirect_to_unapproved_host_is_never_requested(self):
        response = Mock(is_redirect=True, headers={'Location': 'https://127.0.0.1/private'})
        response.__enter__ = Mock(return_value=response)
        response.__exit__ = Mock(return_value=False)
        with patch('news_reader.requests.get', return_value=response) as get:
            with self.assertRaises(ValueError):
                news.fetch_bytes('https://www.bbc.com/news/example', 500)
            self.assertEqual(get.call_count, 1)

    def test_article_text_is_extracted_and_feed_fetch_cached(self):
        def fetch(url, limit):
            if 'rss' in url or 'feed/' in url:
                return feed()
            return b'<nav><p>Navigation text that should never be used as news content</p></nav><p>Actual article paragraph with enough text to be used as evidence.</p>'
        fetch = Mock(side_effect=fetch)
        reader = news.NewsReader(fetch=fetch, now=lambda: NOW)
        first = reader.search('اخبار ایران')
        self.assertEqual(len(first), 1)
        self.assertIn('Actual article', first[0].article)
        self.assertNotIn('Navigation', first[0].article)
        reader.search('اخبار ایران')
        self.assertEqual(sum('rss' in call.args[0] or 'feed/' in call.args[0] for call in fetch.call_args_list), 3)

    def test_unavailable_article_preserves_summary_coverage_label(self):
        def fetch(url, limit):
            if 'rss' in url or 'feed/' in url: return feed()
            raise ValueError('unavailable')
        reader = news.NewsReader(fetch=fetch, now=lambda: NOW)
        result = reader.search('ایران')
        self.assertEqual(result[0].article, '')
        self.assertIn('متن کامل خوانده نشده', news.context(result))

    def test_specific_topic_does_not_match_only_broad_keyword(self):
        reader = news.NewsReader(now=lambda: NOW)
        reader._items = Mock(return_value=[report(title='Trump speaks about trade', summary='Trade deal')])
        self.assertEqual(reader.search('حمله ترامپ به قشم'), [])

    def test_today_uses_tehran_publication_date_and_rechecks_age(self):
        reader = news.NewsReader(now=lambda: NOW)
        reader._items = Mock(return_value=[report(published=NOW-timedelta(days=1)), report(published=NOW-timedelta(days=4))])
        self.assertEqual(reader.search('امروز ایران'), [])

    def test_two_bbc_feeds_are_not_two_independent_publishers(self):
        items = [report(), report(publisher='BBC فارسی', url='https://www.bbc.com/persian/example')]
        self.assertIn('تعداد ناشران مستقل: 1', news.context(items))
        self.assertIn('زمان انتشار', news.context(items))

    def test_fabricated_action_or_source_replaced_with_attributed_headlines(self):
        for text in ('من دیشب حمله کردم.', 'منابع https://fake.invalid/news', 'I attacked Qeshm yesterday.'):
            result = news.finish_answer(text, [report()])
            self.assertIn('BBC: گزارش', result)
            self.assertNotIn('fake.invalid', result)
            self.assertNotIn('من دیشب حمله کردم', result)
            self.assertIn('https://www.bbc.com/news/example', result)


class PersonaFlowTests(unittest.TestCase):
    def setUp(self):
        self.api = FakeAPI()
        self.client = EventClient()
        self.reader = Mock()
        self.reader.search.return_value = [report()]
        self.bot = Bot(self.api, lambda: self.client, news_reader=self.reader)
        self.message = {'chat': {'id': 12}, 'from': {'id': 34}, 'message_id': 56}

    def send(self, text, **fields):
        self.bot.handle_update({'message': dict(self.message, text=text, **fields)})

    def test_first_intro_only_once_and_persona_not_saved_in_history(self):
        self.send('سلام')
        self.assertIn(persona.INTRO, self.api.sent[-1][1])
        history = self.client.text_stream.call_args.kwargs['history']
        self.assertIn('شبیه‌سازی', history[0]['content'][0]['text'])
        self.assertIn('زمان فعلی تهران', history[0]['content'][0]['text'])
        self.send('حالت چطوره؟')
        self.assertNotIn(persona.INTRO, self.api.sent[-1][1])
        session = self.bot.session(self.message)
        self.assertEqual(len(session['history']), 4)
        self.assertEqual(session['history'][0]['content'][0]['text'], 'سلام')
        self.reader.search.assert_not_called()

    def test_identity_question_is_honest_and_does_not_need_provider(self):
        self.send('تو خود ترامپ هستی؟')
        self.assertEqual(self.api.sent[-1][1], persona.IDENTITY)
        self.client.text_stream.assert_not_called()
        self.reader.search.assert_not_called()

    def test_news_context_sources_and_followup_are_wired_to_response(self):
        self.client.text_stream.return_value = [('message', 'طبق گزارش [1] مذاکرات ادامه دارد.')]
        self.send('اخبار ایران چیست؟')
        history = self.client.text_stream.call_args.kwargs['history']
        self.assertIn('گزارش درباره ایران', history[0]['content'][0]['text'])
        self.assertEqual(self.client.text_stream.call_args.args[0], 'اخبار ایران چیست؟')
        self.assertIn('منابع بررسی‌شده', self.api.sent[-1][1])
        self.assertIn('https://www.bbc.com/news/example', self.api.sent[-1][1])
        self.send('جزئیات بیشتر بگو')
        self.assertIn('اخبار ایران', self.reader.search.call_args.args[0])
        self.send('/clear')
        self.assertIsNone(self.bot.session(self.message)['news_topic'])

    def test_no_sources_fails_closed_without_calling_model(self):
        self.reader.search.return_value = []
        self.send('دیشب قشم را زدی؟')
        self.client.text_stream.assert_not_called()
        self.assertIn('تأیید نکردم', self.api.sent[-1][1])
        self.assertFalse(self.bot.ai_gate._value == 0)

    def test_news_is_fetched_once_during_bounded_model_retry(self):
        first = EventClient()
        first.text_stream.side_effect = DuckAIError('challenge', status=418, stage='chat', provider_code='ERR_CHALLENGE')
        self.bot.client_factory = Mock(side_effect=[first, self.client])
        self.send('اخبار ایران')
        self.reader.search.assert_called_once()
        self.assertEqual(self.bot.client_factory.call_count, 2)
        self.assertIn('منابع بررسی‌شده', self.api.sent[-1][1])

    def test_image_request_keeps_original_prompt_without_news_fetch(self):
        self.send('تصویر ترامپ در قشم را طراحی کن')
        self.assertEqual(self.client.image_requests[0][0], 'تصویر ترامپ در قشم را طراحی کن')
        self.reader.search.assert_not_called()
        self.assertEqual(len(self.api.photos), 1)
        self.assertIn(persona.INTRO, self.api.sent[0][1])

    def test_photo_vision_still_receives_image_and_persona(self):
        self.send('رنگ این عکس چیست؟', photo=[{'file_id':'example'}])
        options = self.client.text_stream.call_args.kwargs
        self.assertTrue(options['images'])
        self.assertIn('شبیه‌سازی', options['history'][0]['content'][0]['text'])

    def test_unsourced_personal_military_claim_is_not_sent(self):
        self.client.text_stream.return_value = [('message', 'من دستور حمله دادم.')]
        self.send('چه کردی؟')
        self.assertNotIn('من دستور حمله دادم', self.api.sent[-1][1])
        self.assertIn('شبیه‌سازی', self.api.sent[-1][1])


if __name__ == '__main__':
    unittest.main()
