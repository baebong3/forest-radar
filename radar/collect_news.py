# -*- coding: utf-8 -*-
"""
품목별 뉴스 수집 → data/radar.db news 테이블 (누적 · 멱등)

  - 네이버 뉴스 검색 API (NAVER_ID · NAVER_SECRET 환경변수가 있으면 사용)
  - Google 뉴스 RSS (키 없이 동작)
  - 제목에 품목 핵심어가 있는 기사만 저장 (밤 = night 같은 오탐 차단)

사용법
  python radar/collect_news.py              # 최근 3일
  python radar/collect_news.py --days 30    # 과거 보충
"""
import argparse, html, json, os, re, sys, time
import urllib.parse, urllib.request
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import KST, db
from items import ITEMS, POLICY, relevant, classify

GOOGLE = 'https://news.google.com/rss/search?q={q}&hl=ko&gl=KR&ceid=KR:ko'
NAVER = 'https://openapi.naver.com/v1/search/news.json?query={q}&display=100&start={s}&sort=date'


def clean(s):
    s = re.sub(r'<[^>]+>', ' ', s or '')
    return re.sub(r'\s+', ' ', html.unescape(s)).strip()


def fetch(url, headers=None, timeout=15):
    req = urllib.request.Request(url, headers=dict({'User-Agent': 'Mozilla/5.0 forest-radar'}, **(headers or {})))
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def from_naver(q, since, cid, secret, limit=300):
    out, start = [], 1
    while start <= limit:
        raw = fetch(NAVER.format(q=urllib.parse.quote(q), s=start),
                    {'X-Naver-Client-Id': cid, 'X-Naver-Client-Secret': secret})
        items = json.loads(raw).get('items', [])
        old = False
        for e in items:
            try:
                d = parsedate_to_datetime(e['pubDate']).astimezone(KST)
            except Exception:
                continue
            if d < since:
                old = True
                continue
            url = e.get('originallink') or e.get('link')
            out.append({'title': clean(e.get('title')), 'url': url,
                        'media': urllib.parse.urlparse(url).netloc.replace('www.', ''),
                        'date': d.strftime('%Y-%m-%d'), 'summary': clean(e.get('description'))[:240],
                        'source': 'naver'})
        if old or len(items) < 100:
            break
        start += 100
        time.sleep(0.12)
    return out


def from_google(q, since):
    try:
        import feedparser
    except ImportError:
        return []
    f = feedparser.parse(GOOGLE.format(q=urllib.parse.quote(q)))
    out = []
    for e in f.entries:
        pp = e.get('published_parsed') or e.get('updated_parsed')
        if not pp:
            continue
        d = datetime(*pp[:6], tzinfo=timezone.utc).astimezone(KST)
        if d < since:
            continue
        title, media = clean(e.get('title')), ''
        m = re.match(r'^(.*) - ([^-]+)$', title)
        if m:
            title, media = m.group(1).strip(), m.group(2).strip()
        out.append({'title': title, 'url': e.get('link', ''), 'media': media, 'date': d.strftime('%Y-%m-%d'),
                    'summary': clean(e.get('summary'))[:240], 'source': 'google'})
    return out


def upsert(con, item, it):
    if con.execute('SELECT 1 FROM news WHERE url=? AND item=?', (it['url'], item)).fetchone():
        return 0
    if con.execute('SELECT 1 FROM news WHERE item=? AND title=?', (item, it['title'])).fetchone():
        return 0                                  # 통신사 전재 등 같은 제목은 한 번만
    con.execute('INSERT INTO news(url,item,title,media,date,summary,category,source,collected_at) '
                'VALUES(?,?,?,?,?,?,?,?,?)',
                (it['url'], item, it['title'], it.get('media', ''), it['date'], it.get('summary', ''),
                 classify(it['title'] + ' ' + (it.get('summary') or '')), it.get('source', ''),
                 datetime.now(KST).strftime('%Y-%m-%d %H:%M')))
    return 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--days', type=int, default=3)
    ap.add_argument('--seed', help='JSON [{item,title,url,date,summary}] 적재 (점검 · 수작업 보강용)')
    a = ap.parse_args()
    con = db()
    if a.seed:
        n = sum(upsert(con, x['item'], x) for x in json.load(open(a.seed, encoding='utf-8')))
        con.commit()
        print('seed 적재 %d건' % n)
        return

    since = datetime.now(KST) - timedelta(days=a.days)
    cid, secret = os.environ.get('NAVER_ID'), os.environ.get('NAVER_SECRET')
    total = 0
    for cfg in ITEMS + [POLICY]:
        got = []
        for q in cfg['news']:
            if cid and secret:
                try:
                    got += from_naver(q, since, cid, secret)
                except Exception as ex:
                    print('  네이버 실패 %s : %s' % (q, ex))
                time.sleep(0.15)
            try:
                got += from_google(q, since)
            except Exception as ex:
                print('  Google 실패 %s : %s' % (q, ex))
        ok = [g for g in got if g['url'] and g['title'] and relevant(g['title'], cfg)]
        n = sum(upsert(con, cfg['key'], g) for g in ok)
        con.commit()
        total += n
        print('[%s] 후보 %d건 · 품목 기사 %d건 · 신규 %d건' % (cfg['label'], len(got), len(ok), n))
    con.execute('INSERT OR REPLACE INTO meta(k,v) VALUES(?,?)',
                ('news_run', datetime.now(KST).strftime('%Y-%m-%d %H:%M')))
    con.commit()
    print('합계 신규 %d건 · 누적 %d건' % (total, con.execute('SELECT COUNT(*) FROM news').fetchone()[0]))


if __name__ == '__main__':
    main()
