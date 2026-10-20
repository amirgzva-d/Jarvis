"""No external networking in deterministic live service tests."""
import unittest
from unittest.mock import patch
import live_info

class LiveInfoTest(unittest.TestCase):
    def setUp(self):live_info.CACHE.clear()
    def test_weather_location_and_observed_values(self):
        with patch('live_info._json',side_effect=[{'results':[{'latitude':35.7,'longitude':51.4,'name':'تهران','country':'ایران'}]}, {'current':{'temperature_2m':22.5,'relative_humidity_2m':40,'wind_speed_10m':7,'time':'2026-10-20T09:15'}}]):
            r=live_info.live_query('weather','تهران')
            self.assertIn('22.5',r['answer']);self.assertEqual(r['provider'],'Open-Meteo')
        with patch('live_info._json',side_effect=AssertionError('cache miss')):
            self.assertTrue(live_info.live_query('weather','تهران')['cached'])
    def test_news_parse_and_links(self):
        rss=b'<rss><channel><item><title>Test &amp; data</title><link>https://news.google.com/articles/123</link><pubDate>Today</pubDate></item></channel></rss>'
        with patch('live_info._get',return_value=rss):
            r=live_info.news('AI');self.assertEqual(len(r['items']),1);self.assertEqual(r['items'][0]['title'],'Test & data')
    def test_reject_news_untrusted_redirect(self):
        rss=b'<rss><channel><item><title>Spy</title><link>http://127.0.0.1/a</link></item></channel></rss>'
        with patch('live_info._get',return_value=rss):
            with self.assertRaises(live_info.LiveUnavailable):live_info.news('any')
    def test_fx_price_attribution(self):
        with patch('live_info._json',return_value={'result':'success','rates':{'EUR':.92},'time_last_update_utc':'Monday'}):
            r=live_info.exchange('USD','EUR',100)
            self.assertIn('92.0000',r['answer']);self.assertIn('بازار آزاد',r['answer'])
    def test_input_guards(self):
        for invalid in ('','x'*120):
            with self.assertRaises(ValueError):live_info.weather(invalid)
        with self.assertRaises(ValueError):live_info.exchange('USD','EUR',-1)
        with self.assertRaises(ValueError):live_info.live_query('shell','x')

if __name__=='__main__':unittest.main()
