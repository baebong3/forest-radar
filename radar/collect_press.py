# -*- coding: utf-8 -*-
"""
산림청 보도자료 → data/radar.db news 테이블 (item='press')

  출처 순서 (앞에서 받으면 뒤는 건너뜀)
    1) 대한민국 정책브리핑 부처별 보도자료 RSS (산림청)
    2) 산림청 누리집 보도자료 게시판 목록
  - 실행마다 각 출처의 응답 상태를 meta.press_src 에 남겨 점검
  - 최근 60일 보도자료만 저장 · 같은 제목은 한 번만
"""
import os, re, sys, html, time
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from email.utils import parsedate_to_datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import KST, db
from items import classify

UA = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/124', 'Accept-Language': 'ko-KR'}
RSS = ['https://www.korea.kr/rss/dept_kfs.xml', 'https://www.korea.kr/rss/dept_kfs.xml?type=press']
BOARD = ['https://www.forest.go.kr/kfsweb/cop/bbs/selectBoardList.do?bbsId=BBSMSTR_1036&mn=NKFS_04_02_01']


def get(url, timeout=30):
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=timeout) as r:
        return r.read()


def clean(s):
    return re.sub(r'\s+', ' ', html.unescape(re.sub(r'<[^>]+>', ' ', s or ''))).strip()


def from_rss(url):
    root = ET.fromstring(get(url))
    out = []
    for it in root.iter('item'):
        t = clean(it.findtext('title'))
        link = (it.findtext('link') or '').strip()
        d = it.findtext('pubDate') or it.findtext('{http://purl.org/dc/elements/1.1/}date') or ''
        try:
            dt = parsedate_to_datetime(d).astimezone(KST)
        except Exception:
            m = re.search(r'(20\d\d)[-.](\d\d)[-.](\d\d)', d)
            dt = datetime(*map(int, m.groups()), tzinfo=KST) if m else None
        if t and link and dt:
            out.append({'title': t, 'url': link, 'date': dt.strftime('%Y-%m-%d'), 'summary': clean(it.findtext('description'))[:240]})
    return out


DEBUG = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data', 'press_debug.html')


def from_board(url):
    h = get(url).decode('utf-8', 'ignore')
    out = []
    try:
        open(DEBUG, 'w', encoding='utf-8').write(h[:400000])        # 서식 점검용 (목록을 못 읽을 때 원인 확인)
    except Exception:
        pass
    for tr in re.findall(r'<tr[^>]*>(.*?)</tr>', h, re.S):
        a = re.search(r'<a[^>]+href="([^"]+)"[^>]*>(.*?)</a>', tr, re.S)
        d = re.search(r'(20\d\d)[-.](\d\d)[-.](\d\d)', tr)
        if not a or not d:
            continue
        href = html.unescape(a.group(1))
        if href.startswith('/'):
            href = 'https://www.forest.go.kr' + href
        elif not href.startswith('http'):
            nt = re.search(r"nttId['\"]?\s*[,:=]\s*['\"]?(\d+)", tr)
            if not nt:
                continue
            href = 'https://www.forest.go.kr/kfsweb/cop/bbs/selectBoardArticle.do?bbsId=BBSMSTR_1036&nttId=' + nt.group(1)
        t = clean(a.group(2))
        if len(t) >= 6:
            out.append({'title': t, 'url': href, 'date': '%s-%s-%s' % d.groups(), 'summary': ''})
    return out


def main():
    con = db()
    since = (datetime.now(KST) - timedelta(days=60)).strftime('%Y-%m-%d')
    rows, notes = [], []
    for kind, urls, fn in (('정책브리핑 RSS', RSS, from_rss), ('산림청 게시판', BOARD, from_board)):
        for u in urls:
            try:
                got = fn(u)
                notes.append('%s %d건' % (kind, len(got)))
                if got:
                    rows = got
                    break
            except Exception as ex:
                notes.append('%s 실패 %s' % (kind, str(ex)[:60]))
            time.sleep(1)
        if rows:
            break
    n = 0
    now = datetime.now(KST).strftime('%Y-%m-%d %H:%M')
    for r in rows:
        if r['date'] < since:
            continue
        if con.execute('SELECT 1 FROM news WHERE item=? AND (url=? OR title=?)', ('press', r['url'], r['title'])).fetchone():
            continue
        con.execute('INSERT INTO news(url,item,title,media,date,summary,category,source,collected_at) VALUES(?,?,?,?,?,?,?,?,?)',
                    (r['url'], 'press', r['title'], '산림청', r['date'], r['summary'], classify(r['title'] + ' ' + r['summary']),
                     'kfs', now))
        n += 1
    con.execute('INSERT OR REPLACE INTO meta(k,v) VALUES(?,?)', ('press_src', ' · '.join(notes)[:300]))
    con.execute('INSERT OR REPLACE INTO meta(k,v) VALUES(?,?)', ('press_run', now))
    con.commit()
    print('산림청 보도자료 : %s · 신규 %d건' % (' · '.join(notes), n))


if __name__ == '__main__':
    main()
