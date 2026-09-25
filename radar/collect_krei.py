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
CREATE TABLE IF NOT EXISTS krei_ts(
  item TEXT NOT NULL, tkey TEXT NOT NULL, title TEXT, unit TEXT, sub TEXT NOT NULL,
  ym TEXT NOT NULL, value REAL, src TEXT,      -- src = 값을 가져온 월보(YYYY-MM), 최신 월보 값이 우선
  PRIMARY KEY(item, tkey, sub, ym)
);
CREATE TABLE IF NOT EXISTS krei_done(item TEXT NOT NULL, ym TEXT NOT NULL, n INTEGER, PRIMARY KEY(item, ym));
"""


def get(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=40) as r:
        return r.read()


def list_issues(c, page=1):
    t = get(LIST.format(c=c) + '&pageIndex=%d' % page).decode('utf-8', 'ignore')
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


# ── 월별 표 추출 (가격 · 수출입 · 출하 등 「1월 … 12월」 머리행이 있는 표) ─────────
MON = re.compile(r'^(\d{1,2})월$')
NUMV = re.compile(r'^-?[\d,]+(\.\d+)?$')
YEAR = re.compile(r'^(?:(20\d\d)년?|[’\'‘](\d\d))$')


def _lines(words, tol=3):
    rows = collections.defaultdict(list)
    for w in words:
        rows[round(w['top'] / tol)].append(w)
    out = []
    for k in sorted(rows):
        out.append(sorted(rows[k], key=lambda w: w['x0']))
    return out


def extract_tables(pdf_bytes):
    """월보 PDF → [{title, unit, sub, year, month, value}] (평년 행 제외)"""
    import pdfplumber
    recs = []
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        for p in pdf.pages[1:]:
            words = p.extract_words(extra_attrs=['size'], x_tolerance=1.5)
            lines = _lines(words)
            for li, line in enumerate(lines):
                mons = [w for w in line if MON.match(w['text'])]
                if len(mons) < 4:
                    continue
                # 같은 줄에 표가 둘(좌우)이면 월 순서가 다시 시작하는 곳에서 나눔
                segs, cur = [], []
                for w in mons:
                    m = int(MON.match(w['text']).group(1))
                    if cur and m <= int(MON.match(cur[-1]['text']).group(1)):
                        segs.append(cur); cur = []
                    cur.append(w)
                segs.append(cur)
                htop = line[0]['top']
                for si, seg in enumerate(segs):
                    if len(seg) < 3:
                        continue
                    cols = [(int(MON.match(w['text']).group(1)), (w['x0'] + w['x1']) / 2) for w in seg]
                    gap = (cols[-1][1] - cols[0][1]) / max(1, len(cols) - 1)
                    left = segs[si - 1][-1]['x1'] + gap * 0.4 if si > 0 else 0
                    right = seg[-1]['x1'] + gap * 0.4 if si + 1 < len(segs) else p.width
                    xs0 = seg[0]['x0'] - gap * 0.55
                    tot = [w for w in line if w['text'] == '합계' and xs0 < w['x0'] < right]
                    tot_x = (tot[0]['x0'] + tot[0]['x1']) / 2 if tot else None
                    # 제목 · 단위 : 머리행 위 60pt 안
                    title, unit = '', ''
                    for up in reversed(lines[max(0, li - 6):li]):
                        ws = [w for w in up if left - 30 <= w['x0'] <= right and htop - up[0]['top'] < 70]
                        if not ws:
                            continue
                        t = ' '.join(w['text'] for w in ws)
                        if '단위' in t and not unit:
                            unit = re.sub(r'^.*단위\s*:\s*', '', t).strip()
                            continue
                        if not title and 10 <= ws[0]['size'] <= 12.6 and not MON.match(ws[0]['text']) and t not in ('구분',):
                            title = t
                    if not title:
                        continue
                    # 본문 행
                    rows, ylabels = [], []
                    last_top = htop
                    for dl in lines[li + 1:li + 40]:
                        ws = [w for w in dl if left - 5 <= w['x0'] < right]
                        if not ws:
                            continue
                        t0 = ws[0]['text']
                        if t0.startswith('주') or t0.startswith('자료') or t0.startswith('\uf06c') or dl[0]['top'] - last_top > 48:
                            break
                        if len([w for w in ws if MON.match(w['text'])]) >= 3:
                            break
                        last_top = dl[0]['top']
                        cut = cols[0][1] - gap * 0.5
                        lab = [w for w in ws if (w['x0'] + w['x1']) / 2 < cut]
                        vals = [w for w in ws if (w['x0'] + w['x1']) / 2 >= cut and NUMV.match(w['text'])]
                        yl = None
                        subt = []
                        for w in lab:
                            m = YEAR.match(w['text'])
                            if m:
                                yl = int(m.group(1)) if m.group(1) else 2000 + int(m.group(2))
                            elif w['text'] == '평년':
                                yl = 'avg'
                            else:
                                subt.append(w['text'])
                        if yl is not None:
                            ylabels.append((dl[0]['top'], yl))
                        if not vals:
                            continue
                        rows.append({'top': dl[0]['top'], 'y': yl, 'sub': re.sub(r'\s+', '', ''.join(subt)), 'vals': vals})
                    for r in rows:
                        y = r['y']
                        if y is None and ylabels:
                            y = min(ylabels, key=lambda t: abs(t[0] - r['top']))[1]
                        if y in (None, 'avg'):
                            continue
                        for w in r['vals']:
                            cx = (w['x0'] + w['x1']) / 2
                            if tot_x is not None and abs(cx - tot_x) < gap * 0.5:
                                continue
                            mm, d = min(((m, abs(cx - x)) for m, x in cols), key=lambda t: t[1])
                            if d > gap * 0.6:
                                continue
                            try:
                                v = float(w['text'].replace(',', ''))
                            except ValueError:
                                continue
                            recs.append({'title': _clean(title), 'unit': unit, 'sub': r['sub'], 'year': y, 'month': mm, 'value': v})
    return recs


def tkey(title):
    """표 제목 정규화 - 호마다 조금씩 다른 표현(월별 · 동향 · 현황 · 추이 · 공백)을 같은 표로 묶음"""
    t = re.sub(r'\s+', '', title)
    t = re.sub(r'^[^가-힣A-Za-z0-9(]+', '', t)
    for w in ('월별', '동향', '현황', '추이', '실적', '의'):
        t = t.replace(w, '')
    return t


def store_ts(con, item, src_ym, recs):
    n = 0
    for r in recs:
        ym = '%04d-%02d' % (r['year'], r['month'])
        if ym > src_ym:                                     # 발행월보다 뒤 달은 전망 · 오기로 보고 버림
            continue
        k = tkey(r['title'])
        old = con.execute('SELECT src FROM krei_ts WHERE item=? AND tkey=? AND sub=? AND ym=?', (item, k, r['sub'], ym)).fetchone()
        if old and old[0] > src_ym:
            continue
        con.execute('INSERT OR REPLACE INTO krei_ts(item,tkey,title,unit,sub,ym,value,src) VALUES(?,?,?,?,?,?,?,?)',
                    (item, k, r['title'], r['unit'], r['sub'], ym, r['value'], src_ym))
        n += 1
    return n


def all_issues(c, since_year, max_pages=20):
    out = []
    for pg in range(1, max_pages + 1):
        try:
            iss = list_issues(c, pg)
        except Exception as ex:
            print('  목록 %d쪽 실패 : %s' % (pg, ex))
            break
        if not iss:
            break
        out += iss
        if min(i['ym'] for i in iss) < '%d-01' % since_year:
            break
        time.sleep(0.3)
    seen, uniq = set(), []
    for i in out:
        if i['ym'] not in seen:
            seen.add(i['ym']); uniq.append(i)
    return uniq


def pick_for_tables(iss, since_year):
    """연도별 마지막 호 + 최근 2년의 모든 호 (한 호에 올해 · 전년 월별 값이 함께 실림)"""
    if not iss:
        return []
    latest_y = max(int(i['ym'][:4]) for i in iss)
    by_y = collections.defaultdict(list)
    for i in iss:
        by_y[int(i['ym'][:4])].append(i)
    pick = []
    for y, lst in by_y.items():
        if y < since_year:
            continue
        if y >= latest_y - 1:
            pick += lst
        else:
            pick.append(max(lst, key=lambda i: i['ym']))
    return sorted(pick, key=lambda i: i['ym'])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--keep', type=int, default=3, help='소제목을 보관할 최근 호 수')
    ap.add_argument('--since', type=int, default=2015, help='월별 표를 모을 시작 연도')
    ap.add_argument('--pdf'), ap.add_argument('--item'), ap.add_argument('--ym')
    a = ap.parse_args()
    con = db()
    con.executescript(SCHEMA)
    if a.pdf:
        b = open(a.pdf, 'rb').read()
        print(json.dumps({'heads': extract(b), 'tables': extract_tables(b)}, ensure_ascii=False, indent=1)[:6000])
        return
    now = datetime.now(KST).strftime('%Y-%m-%d %H:%M')
    for item, c in CTGRY.items():
        have = con.execute('SELECT COUNT(*) FROM krei_done WHERE item=?', (item,)).fetchone()[0]
        iss = all_issues(c, a.since) if have == 0 else list_issues(c)
        if not iss:
            print('[%s] 목록 없음' % item)
            continue
        # 1) 최근 호 소제목
        new_h = 0
        for it in iss[:a.keep]:
            if con.execute('SELECT 1 FROM krei WHERE item=? AND ym=? AND heads IS NOT NULL AND heads!="[]"',
                           (item, it['ym'])).fetchone():
                continue
            try:
                it['_pdf'] = get(it['pdf'])
                hs = extract(it['_pdf'])
            except Exception as ex:
                print('[%s] %s 소제목 추출 실패 : %s' % (item, it['ym'], ex))
                hs = []
            con.execute('INSERT OR REPLACE INTO krei(item,ym,title,pdf,view,heads,fetched_at) VALUES(?,?,?,?,?,?,?)',
                        (item, it['ym'], '임업관측 %s년 %d월호' % (it['ym'][:4], int(it['ym'][5:])), it['pdf'], it['view'],
                         json.dumps(hs, ensure_ascii=False), now))
            new_h += 1
        # 2) 월별 표 (처리 안 한 호만)
        new_t = cells = 0
        for it in pick_for_tables(iss, a.since):
            if con.execute('SELECT 1 FROM krei_done WHERE item=? AND ym=?', (item, it['ym'])).fetchone():
                continue
            try:
                b = it.get('_pdf') or get(it['pdf'])
                recs = extract_tables(b)
            except Exception as ex:                  # 일시 오류 : 완료 기록을 남기지 않아 다음 실행 때 다시 받음
                print('[%s] %s 표 추출 실패(다음 실행 때 재시도) : %s' % (item, it['ym'], ex))
                continue
            cells += store_ts(con, item, it['ym'], recs)
            con.execute('INSERT OR REPLACE INTO krei_done(item,ym,n) VALUES(?,?,?)', (item, it['ym'], len(recs)))
            new_t += 1
            con.commit()
            time.sleep(0.4)
        con.commit()
        print('[%s] 목록 %d개 호 · 소제목 새로 %d개 · 표 새로 %d개 호(%d칸)' % (item, len(iss), new_h, new_t, cells))
    con.execute('INSERT OR REPLACE INTO meta(k,v) VALUES(?,?)', ('krei_run', now))
    con.commit()


if __name__ == '__main__':
    main()
