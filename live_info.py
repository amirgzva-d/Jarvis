"""Live, attributed, server-side information for Jarvis.

Only fixed trusted HTTPS endpoints are contacted. No user-supplied URL fetches.
Answers are marked with providers and update time; external errors do not become facts.
"""
from __future__ import annotations
import json
import re
import threading
import time
from datetime import datetime, timezone
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from xml.etree import ElementTree

CACHE: dict[tuple[str, str], tuple[float, dict]] = {}
_LOCK = threading.Lock()
MAX_QUERY = 110

class LiveUnavailable(Exception):
    pass

def _get(url: str, max_bytes: int = 400_000) -> bytes:
    req = Request(url, headers={'User-Agent': 'JarvisPersonalAssistant/1.1 (local research application)', 'Accept': 'application/json, application/rss+xml'})
    try:
        with urlopen(req, timeout=9) as response:
            data = response.read(max_bytes + 1)
        if len(data) > max_bytes:
            raise LiveUnavailable('پاسخ سرویس بیرونی بیش از حد بزرگ است.')
        return data
    except (OSError, TimeoutError, ValueError) as exc:
        raise LiveUnavailable('سرویس اطلاعات زنده اکنون در دسترس نیست.') from exc

def _json(url: str) -> dict:
    try:
        data = json.loads(_get(url))
        if not isinstance(data, dict): raise ValueError('Expected object')
        return data
    except (ValueError, UnicodeError) as exc:
        raise LiveUnavailable('داده معتبر از سرویس دریافت نشد.') from exc

def _query(text: str) -> str:
    if not isinstance(text, str) or not 1 <= len(text.strip()) <= MAX_QUERY:
        raise ValueError('موضوع جستجو باید بین ۱ تا ۱۱۰ نویسه باشد.')
    return re.sub(r'[\x00-\x1f<>]+', ' ', text).strip()

def _stamp() -> str:
    return datetime.now(timezone.utc).isoformat(timespec='seconds')

def weather(city: str) -> dict:
    city = _query(city)
    geo = _json('https://geocoding-api.open-meteo.com/v1/search?' + urlencode({'name': city, 'count': 1, 'language': 'fa'}))
    locations = geo.get('results') or []
    if not locations:
        raise LiveUnavailable('شهری با این نام در سرویس هواشناسی پیدا نشد.')
    location = locations[0]
    forecast = _json('https://api.open-meteo.com/v1/forecast?' + urlencode({
        'latitude': location['latitude'], 'longitude': location['longitude'],
        'current': 'temperature_2m,relative_humidity_2m,wind_speed_10m,weather_code',
        'timezone': 'auto'}))
    current = forecast.get('current') or {}
    temp, humidity, wind = current.get('temperature_2m'), current.get('relative_humidity_2m'), current.get('wind_speed_10m')
    if not all(isinstance(v,(int,float)) for v in (temp,humidity,wind)):
        raise LiveUnavailable('داده کامل هواشناسی دریافت نشد.')
    name = f'{location.get("name",city)}، {location.get("country", "")}'.strip('، ')
    return {'kind':'weather', 'title':'آب‌وهوای '+name, 'answer':f'دمای فعلی {name} {temp:g} درجه سانتی‌گراد، رطوبت {humidity:g}٪ و سرعت باد {wind:g} کیلومتر بر ساعت است.',
            'updated_at':str(current.get('time') or _stamp()), 'provider':'Open-Meteo', 'source':'https://open-meteo.com/',
            'details': {'temperature_c':temp,'humidity_pct':humidity,'wind_kmh':wind,'weather_code':current.get('weather_code')}, 'sources':[]}

def news(topic: str) -> dict:
    topic = _query(topic)
    url = 'https://news.google.com/rss/search?' + urlencode({'q':topic,'hl':'fa','gl':'IR','ceid':'IR:fa'})
    try:
        tree=ElementTree.fromstring(_get(url))
    except ElementTree.ParseError as exc:
        raise LiveUnavailable('دریافت فید اخبار موفق نبود.') from exc
    items=[]
    for item in tree.findall('./channel/item')[:6]:
        title=(item.findtext('title') or '').strip()[:180]
        link=(item.findtext('link') or '').strip()
        if title and link.startswith('https://news.google.com/'):
            items.append({'title':title,'url':link,'published':(item.findtext('pubDate') or '')[:90]})
    if not items:
        raise LiveUnavailable('خبر قابل استنادی برای این موضوع پیدا نشد.')
    return {'kind':'news','title':'آخرین اخبار: '+topic,
            'answer':'این‌ها جدیدترین عنوان‌های دریافتی از فید اخبار هستند؛ محتوای مقاله‌ها بررسی مستقل نشده است.',
            'updated_at':_stamp(),'provider':'Google News RSS','source':url,'items':items,'sources':[]}

def exchange(base: str, quote: str, amount: float = 1) -> dict:
    base,quote=base.upper().strip(),quote.upper().strip()
    if not re.fullmatch(r'[A-Z]{3}',base) or not re.fullmatch(r'[A-Z]{3}',quote):
        raise ValueError('کد ارز باید سه حرف انگلیسی باشد؛ مانند USD یا EUR.')
    if not 0 < amount <= 10**9:
        raise ValueError('مقدار ارز باید بزرگ‌تر از صفر و محدود باشد.')
    data=_json('https://open.er-api.com/v6/latest/'+base)
    if data.get('result')!='success' or not isinstance(data.get('rates',{}).get(quote), (int,float)):
        raise LiveUnavailable('نرخ تبدیل برای این جفت‌ارز پیدا نشد.')
    rate=data['rates'][quote]
    date=data.get('time_last_update_utc') or _stamp()
    return {'kind':'exchange','title':f'{base} → {quote}',
            'answer':f'{amount:g} {base} بر اساس نرخ مرجع برابر با {amount*rate:,.4f} {quote} است. این نرخ بازار آزاد یا نرخ معامله تضمین‌شده نیست.',
            'updated_at':str(date),'provider':'ExchangeRate-API Open Access','source':'https://www.exchangerate-api.com/docs/free',
            'details':{'base':base,'quote':quote,'amount':amount,'rate':rate},'sources':[]}

def live_query(kind: str, query: str, *, base='USD',quote='EUR',amount=1) -> dict:
    if kind not in {'weather','news','exchange'}:
        raise ValueError('نوع داده زنده شناخته‌شده نیست.')
    key=(kind, _query(query) if kind!='exchange' else f'{base.upper()}:{quote.upper()}:{amount}')
    now=time.monotonic()
    with _LOCK:
        cached=CACHE.get(key)
        if cached and cached[0]>now:
            return dict(cached[1], cached=True)
    result={'weather':lambda:weather(query),'news':lambda:news(query),'exchange':lambda:exchange(base,quote,float(amount))}[kind]()
    with _LOCK:
        CACHE[key]=(now+(180 if kind!='exchange' else 1800), result)
    return dict(result,cached=False)
