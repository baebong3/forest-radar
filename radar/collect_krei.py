# -*- coding: utf-8 -*-
"""
농경연(KREI) 임업관측 월보 → data/radar.db krei 테이블

  목록 : https://www.krei.re.kr/krei/page/21?cmd=list&ctgry=코드  (품목별 월보, 매월 4일 발표)
  원문 : /attach/observ/YYYY/MM/DD/*.pdf
  추출 : 월보 PDF의 소제목(갈색 13pt 줄 = 핵심 판단 문장)과 그 아래 첫 문장(근거 수치)
         → 절(생산 · 수출입 · 가격)별로 저장. '단신' 절은 제외

사용법
  python radar/collect_krei.py            # 새로 나온 호만 받음 (품목별 최근 3개 호까지)
  python radar/collect_krei.py --pdf 파일.pdf --item chestnut --ym 2026-09   # 저장된 PDF로 추출 점검
"""
import argparse, collections, io, json, os, re, sys, time, urllib.request
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import KST, db

BASE = 'https://www.krei.re.kr'
LIST = BASE + '/krei/page/21?cmd=list&ctgry={c}'
VIEW = BASE + '/krei/page/21?cmd=view&ctgry={c}&yr={y}&mm={m}'
CTGRY = {'chestnut': '0101', 'shiitake': '0102', 'jujube': '0103', 'persimmon': '0104', 'walnut': '0107'}
UA = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36',
      'Accept-Language': 'ko-KR,ko;q=0.9'}

SCHEMA = """
CREATE TABLE IF NOT EXISTS krei(
  item TEXT NOT NULL, ym TEXT NOT NULL, title TEXT, pdf TEXT, view TEXT,
  heads TEXT,               -- JSON [{sec, head, detail}]
  fetched_at TEXT,
  PRIMARY KEY(item, ym)
);
"""


def get(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=40) as r:
        return r.read()


def list_issues(c):
    t = get(LIST.format(c=c)).decode('utf-8', 'ignore')
    out = []
    for yr, mm, pdf in re.findall(r'href="\?cmd=view&(?:amp;)?ctgry=\d+&(?:amp;)?yr=(\d{4})&(?:amp;)?mm=(\d{2})".*?'
                                  r'href="(/attach/observ/[^"]+\.pdf)"', t, re.S):
        out.append({'ym': '%s-%s' % (yr, mm), 'pdf': BASE + pdf, 'view': VIEW.format(c=c, y=yr, m=mm)})
    return out


def _white(col):
    try:
        return all(float(v) > .95 for v in (col or [0]))
    except TypeError:
        return False


def _clean(s):
    s = s.replace('', '').replace('', '').replace('∙', '').replace('⸱', '·')
    s = s.replace('—', '-').replace('–', '-')
    s = re.sub(r'\s+', ' ', s).strip()
    return s


def _join(chars):
    chars = sorted(chars, key=lambda c: c['x0'])
    out, last = '', None
    for c in chars:
        if last is not None and c['x0'] - last > c['size'] * 0.25:
            out += ' '
        out += c['text']
        last = c['x1']
    return out


def kind(head):
    if re.search(r'가격|시세|보합|약세|강세', head):
        return '가격'
    if re.search(r'수출|수입', head):
        return '수출입'
    return '생산·출하'


def extract(pdf_bytes):
    """월보 PDF → [{sec, head, detail}]"""
    import pdfplumber
    res = []
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        sec = ''
        for p in pdf.pages[1:]:
            big = [c for c in p.chars if c['size'] >= 28]
            if big:
                sec = _clean(_join([c for c in big if abs(c['top'] - big[0]['top']) < 4]))
                sec = re.sub(r'^\d+\s*❘\s*', '', sec)
            if not re.search(r'동향|전망', sec):          # 단신 · 특집 분석 등은 제외
                continue
            rows = collections.defaultdict(list)
            for c in p.chars:
                if 12.5 <= c['size'] < 20 and not _white(c.get('non_stroking_color')) and c['text'].strip():
                    rows[round(c['top'] / 4)].append(c)
            heads = []
            for k in sorted(rows):
                cs = rows[k]
                heads.append({'top': min(c['top'] for c in cs), 'bottom': max(c['bottom'] for c in cs),
                              'x0': min(c['x0'] for c in cs), 'text': _clean(_join(cs))})
            for i, h in enumerate(heads):
                if len(h['text']) < 6:
                    continue
                y2 = heads[i + 1]['top'] if i + 1 < len(heads) else p.height - 30
                detail = ''
                try:
                    box = p.crop((max(0, h['x0'] - 4), h['bottom'] + 1, p.width - 20, min(p.height, max(h['bottom'] + 2, y2 - 1))))
                    body = [c for c in box.chars if 10.5 <= c['size'] < 12]
                    lines = collections.defaultdict(list)
                    for c in body:
                        lines[round(c['top'] / 3)].append(c)
                    txt = ' '.join(_join(lines[k]) for k in sorted(lines))
                    txt = _clean(re.sub(r'(연도\s*)?(\d{1,2}월\s*){3,}', ' ', txt))
                    m = re.match(r'(.+?[가-힣]\.)(\s|$)', txt)
                    detail = (m.group(1) if m else txt[:160]).rstrip('.')
                except Exception:
                    pass
                res.append({'sec': kind(h['text']), 'head': h['text'], 'detail': detail})
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--keep', type=int, default=3, help='품목별 최근 몇 개 호까지 받을지')
    ap.add_argument('--pdf'), ap.add_argument('--item'), ap.add_argument('--ym')
    a = ap.parse_args()
    con = db()
    con.executescript(SCHEMA)
    if a.pdf:
        hs = extract(open(a.pdf, 'rb').read())
        print(json.dumps(hs, ensure_ascii=False, indent=1))
        return
    now = datetime.now(KST).strftime('%Y-%m-%d %H:%M')
    for item, c in CTGRY.items():
        try:
            iss = list_issues(c)[:a.keep]
        except Exception as ex:
            print('[%s] 목록 실패 : %s' % (item, ex))
            continue
        new = 0
        for it in iss:
            if con.execute('SELECT 1 FROM krei WHERE item=? AND ym=? AND heads IS NOT NULL AND heads!="[]"',
                           (item, it['ym'])).fetchone():
                continue
            try:
                hs = extract(get(it['pdf']))
            except Exception as ex:
                print('[%s] %s 추출 실패 : %s' % (item, it['ym'], ex))
                hs = []
            con.execute('INSERT OR REPLACE INTO krei(item,ym,title,pdf,view,heads,fetched_at) VALUES(?,?,?,?,?,?,?)',
                        (item, it['ym'], '임업관측 %s년 %d월호' % (it['ym'][:4], int(it['ym'][5:])), it['pdf'], it['view'],
                         json.dumps(hs, ensure_ascii=False), now))
            new += 1
            time.sleep(0.5)
        con.commit()
        print('[%s] 목록 %d개 호 · 새로 추출 %d개' % (item, len(iss), new))
    con.execute('INSERT OR REPLACE INTO meta(k,v) VALUES(?,?)', ('krei_run', now))
    con.commit()


if __name__ == '__main__':
    main()
