# -*- coding: utf-8 -*-
"""
산림청 임산물생산조사(연 1회) → data/radar.db prod 테이블 (연도 · 품목 · 시도 · 시군구별 생산량 · 생산액)

  출처 : 산림임업통계플랫폼(kfss.forest.go.kr) 「임산물생산조사 자료실」 연도별 보고서 PDF
  방법 : PDF → pdftotext -layout → 부록 통계표의 「□ 시도」 · 「□ 시도 시군구」 블록에서
         품목 줄(밤 · 호두 · 대추 · 감 · 생표고 · 건표고)의 생산량(kg) · 생산액(원)을 읽음
  주기 : 매년 10월 전후 공표 → 새 연도 보고서가 올라오면 자동으로 추가, 처리한 연도는 다시 받지 않음

사용법
  python radar/collect_prod.py                 # 새 연도만
  python radar/collect_prod.py --since 2012    # 받을 첫 연도
  python radar/collect_prod.py --txt 보고서.txt --year 2024   # 텍스트로 파서 점검
"""
import argparse, json, os, re, subprocess, sys, tempfile, time
import urllib.request, urllib.parse, http.cookiejar
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import KST, db

B = 'https://kfss.forest.go.kr/stat'
SCHEMA = """
CREATE TABLE IF NOT EXISTS prod(
  year INTEGER NOT NULL, item TEXT NOT NULL, sub TEXT NOT NULL,
  sido TEXT NOT NULL, sigungu TEXT NOT NULL,          -- 시도 합계 줄은 sigungu = ''
  kg REAL, won REAL,
  PRIMARY KEY(year, item, sub, sido, sigungu)
);
CREATE TABLE IF NOT EXISTS prod_done(year INTEGER PRIMARY KEY, article TEXT, rows INTEGER, at TEXT);
CREATE TABLE IF NOT EXISTS prod_nat(          -- 보고서 본문 「최근 5년 생산량」 표 (전국, 톤)
  year INTEGER NOT NULL, item TEXT NOT NULL, sub TEXT NOT NULL, tonnes REAL, src INTEGER,
  PRIMARY KEY(year, item, sub)
);
"""

# 품목 줄 : 글자 사이 공백이 들어간 채로 인쇄됨 (예 '호        두   kg   8,345   47,844,803')
NUM = r'([\d,]+|-)'
ITEM_RE = [
    ('chestnut', '', re.compile(r'(?<![가-힣])밤\s+kg\s+' + NUM + r'\s+' + NUM)),
    ('walnut', '', re.compile(r'(?<![가-힣])호\s*두\s+kg\s+' + NUM + r'\s+' + NUM)),
    ('jujube', '', re.compile(r'(?<![가-힣])대\s*추\s+kg\s+' + NUM + r'\s+' + NUM)),
    ('persimmon', '', re.compile(r'(?<![가-힣])(?:떫\s*은\s*)?감\s+kg\s+' + NUM + r'\s+' + NUM)),
    ('shiitake', '생표고', re.compile(r'(?<![가-힣])생\s*표\s*고\s+kg\s+' + NUM + r'\s+' + NUM)),
    ('shiitake', '건표고', re.compile(r'(?<![가-힣])건\s*표\s*고\s+kg\s+' + NUM + r'\s+' + NUM)),
]

SIDO_MAP = [('서울', '서울'), ('부산', '부산'), ('대구', '대구'), ('인천', '인천'), ('광주', '광주'), ('대전', '대전'),
            ('울산', '울산'), ('세종', '세종'), ('경기', '경기'), ('강원', '강원'), ('충청북', '충북'), ('충북', '충북'),
            ('충청남', '충남'), ('충남', '충남'), ('전라북', '전북'), ('전북', '전북'), ('전라남', '전남'), ('전남', '전남'),
            ('경상북', '경북'), ('경북', '경북'), ('경상남', '경남'), ('경남', '경남'), ('제주', '제주')]


def sido_short(name):
    for k, v in SIDO_MAP:
        if name.startswith(k):
            return v
    return None


def num(s):
    return 0.0 if s == '-' else float(s.replace(',', ''))


def parse(text):
    """보고서 텍스트 → [(item, sub, sido, sigungu, kg, won)]"""
    out = []
    parts = re.split(r'\n\s*□\s*', '\n' + text)
    for part in parts[1:]:
        head, _, body = part.partition('\n')
        name = re.sub(r'\s+', ' ', head).strip()
        if not name or re.search(r'(시도|시군구|지역)별', name):   # '시도별 임산물 생산액' 같은 총괄표는 건너뜀
            continue
        toks = name.split(' ')
        sd = sido_short(toks[0])
        if not sd:                                         # 지방산림청 · 국립기관 등
            sd, sgg = '기관', name
        else:
            sgg = ' '.join(toks[1:])
        body = body[:20000]
        for item, sub, rx in ITEM_RE:
            m = rx.search(body)
            if not m:
                continue
            out.append((item, sub, sd, sgg, num(m.group(1)), num(m.group(2))))
    return out


NAT_ITEMS = {'밤': ('chestnut', ''), '호두': ('walnut', ''), '대추': ('jujube', ''), '감': ('persimmon', ''),
             '표고': ('shiitake', '')}


def parse_nat(text):
    """「수실류 · 버섯 최근 5년 생산량」 표 → [(year, item, sub, 톤)]"""
    out = []
    for key in ('수실류 최근 5년', '버섯 최근 5년'):
        pos = [m.start() for m in re.finditer(key, text)]
        if not pos:
            continue
        seg = text[pos[-1]:pos[-1] + 6000]                       # 목차가 아닌 본문 쪽(마지막 등장)
        lines = seg.split('\n')
        header, rows = None, []
        for l in lines:
            toks = l.split()
            if header is None and ('밤' in toks or '표고' in toks) and not re.search(r'\d', l):
                header = []
                for t in toks:                                   # 생산량 · 생산액이 한 줄에 나란히 있으면 앞쪽(생산량)만
                    if t in ('감', '밤', '대추', '호두', '잣', '기타', '송이', '표고'):
                        if t in header:
                            break
                        header.append(t)
                continue
            m = re.match(r'^\s*(20\d\d)\s+(.*)$', l)
            if header and m:
                nums = re.findall(r'△?[\d,.]+', m.group(2))
                if len(nums) >= 3 + len(header):
                    rows.append((int(m.group(1)), nums))
                if len(rows) == 5:
                    break
        for y, nums in rows:
            vals = nums[3:3 + len(header)]
            for h, v in zip(header, vals):
                if h in NAT_ITEMS:
                    item, sub = NAT_ITEMS[h]
                    out.append((y, item, sub, float(v.replace(',', '').replace('△', '-'))))
    return out


def opener():
    cj = http.cookiejar.CookieJar()
    op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
    op.addheaders = [('User-Agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/124'), ('Accept-Language', 'ko-KR'),
                     ('X-Requested-With', 'XMLHttpRequest')]
    op.open(B + '/ptl/article/articleList.do?curMenu=9847&bbsId=ptlPdsMntProdReq', timeout=120).read()
    return op


def articles(op):
    q = urllib.parse.urlencode({'bbsId': 'ptlPdsMntProdReq', 'curMenu': '9847', 'pageIndex': 1, 'pageUnit': 50,
                                'recordCountPerPage': 50})
    rows = json.loads(op.open(B + '/ptl/article/selectArticleList.do?' + q, timeout=60).read()).get('data') or []
    by = {}
    for r in rows:
        t = r.get('title') or ''
        m = re.search(r'(20\d\d)\s*년?\s*임산물생산조사|임산물생산조사.*?(20\d\d)', t.replace(' ', ' '))
        if not m or '순임목' in t:
            continue
        y = int(m.group(1) or m.group(2))
        seq = int(r['articleSeq'])
        if y not in by or seq > by[y][0]:                 # 개정판 등 같은 연도가 여러 번이면 나중 글
            by[y] = (seq, t)
    return by


def pdf_text(op, seq):
    fl = json.loads(op.open(B + '/ptl/article/selectArticleFileList.do?' +
                            urllib.parse.urlencode({'workPath': 'Article', 'workSeq': seq}), timeout=60).read()).get('data') or []
    pdfs = [f for f in fl if (f.get('fileNm') or '').lower().endswith('.pdf')]
    if not pdfs:
        raise RuntimeError('PDF 없음 : ' + ' | '.join('%s(%s)' % (f.get('fileNm'), f.get('fileSize')) for f in fl))
    f = max(pdfs, key=lambda f: f.get('fileSize') or 0)
    b = op.open(B + '/ptl/article/articleFileDown.do?' + urllib.parse.urlencode({'fileSeq': f['fileSeq'], 'workSeq': seq}),
                timeout=600).read()
    with tempfile.TemporaryDirectory() as d:
        p = os.path.join(d, 'r.pdf')
        open(p, 'wb').write(b)
        subprocess.run(['pdftotext', '-layout', p, os.path.join(d, 'r.txt')], check=True)
        return open(os.path.join(d, 'r.txt'), encoding='utf-8', errors='ignore').read()


def store(con, year, rows):
    con.execute('DELETE FROM prod WHERE year=?', (year,))
    for item, sub, sd, sgg, kg, won in rows:
        con.execute('INSERT OR REPLACE INTO prod(year,item,sub,sido,sigungu,kg,won) VALUES(?,?,?,?,?,?,?)',
                    (year, item, sub, sd, sgg, kg, won))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--since', type=int, default=2012)
    ap.add_argument('--txt'), ap.add_argument('--year', type=int)
    ap.add_argument('--retry', action='store_true', help='못 읽었던 해도 다시 시도')
    a = ap.parse_args()
    con = db()
    con.executescript(SCHEMA)
    if a.txt:
        t = open(a.txt, encoding='utf-8').read()
        rows = parse(t)
        store(con, a.year, rows)
        for yy, item, sub, tn in parse_nat(t):
            con.execute('INSERT OR REPLACE INTO prod_nat(year,item,sub,tonnes,src) VALUES(?,?,?,?,?)', (yy, item, sub, tn, a.year))
        con.commit()
        print('행 %d' % len(rows))
        return
    op = arts = None
    for i in range(3):                                  # 산림임업통계플랫폼이 가끔 응답이 늦음 → 재시도
        try:
            op = opener()
            arts = articles(op)
            break
        except Exception as ex:
            err = ex
            time.sleep(20 * (i + 1))
    try:
        if arts is None:
            raise err
    except Exception as ex:
        print('목록 실패 : %s' % ex)
        con.execute('INSERT OR REPLACE INTO meta(k,v) VALUES(?,?)', ('prod_err', '목록 실패 : %s' % str(ex)[:300]))
        con.commit()
        return
    done = {r[0] for r in con.execute('SELECT year FROM prod_done WHERE rows > 0')}
    if not con.execute('SELECT COUNT(*) FROM prod_nat').fetchone()[0]:
        done = set()                                        # 5년 표를 새로 읽도록 한 번 다시 받음
    tried = {r[0] for r in con.execute("SELECT year FROM prod_done WHERE rows = 0")}
    for y in sorted(arts):
        if y < a.since or y in done or (y in tried and not a.retry):   # 글꼴 문제로 못 읽는 옛 보고서는 다시 받지 않음
            continue
        seq, title = arts[y]
        try:
            t = pdf_text(op, seq)
            rows = parse(t) if t else []
            for yy, item, sub, tn in (parse_nat(t) if t else []):
                old = con.execute('SELECT src FROM prod_nat WHERE year=? AND item=? AND sub=?', (yy, item, sub)).fetchone()
                if not old or old[0] <= y:                   # 나중 보고서(수정치)가 우선
                    con.execute('INSERT OR REPLACE INTO prod_nat(year,item,sub,tonnes,src) VALUES(?,?,?,?,?)', (yy, item, sub, tn, y))
        except Exception as ex:
            print('[%d] 실패 : %s' % (y, ex))
            con.execute('INSERT OR REPLACE INTO prod_done(year,article,rows,at) VALUES(?,?,?,?)',
                        (y, ('실패 : %s' % ex)[:500], 0, datetime.now(KST).strftime('%Y-%m-%d %H:%M')))
            con.commit()
            continue
        if not rows and t:                                  # 서식이 달라 못 읽은 해 : 점검용 발췌를 남김
            os.makedirs(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data', 'prod_debug'), exist_ok=True)
            ls = t.split('\n')
            hit = [i for i, l in enumerate(ls) if re.search(r'(?<![가-힣])밤(?![가-힣])', l)][:8]
            sample = '\n'.join(ls[:80]) + '\n=====\n' + '\n-----\n'.join('\n'.join(ls[max(0, i - 12):i + 25]) for i in hit)
            bl = [i for i, l in enumerate(ls) if '부여' in l][:4]
            sample += '\n=====부여\n' + '\n-----\n'.join('\n'.join(ls[max(0, i - 5):i + 60]) for i in bl)
            open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data', 'prod_debug', '%d.txt' % y),
                 'w', encoding='utf-8').write('LINES %d\n' % len(ls) + sample)
        store(con, y, rows)
        con.execute('INSERT OR REPLACE INTO prod_done(year,article,rows,at) VALUES(?,?,?,?)',
                    (y, title, len(rows), datetime.now(KST).strftime('%Y-%m-%d %H:%M')))
        con.commit()
        print('[%d] %s · %d행' % (y, title, len(rows)))
        time.sleep(1)
    con.execute('INSERT OR REPLACE INTO meta(k,v) VALUES(?,?)', ('prod_run', datetime.now(KST).strftime('%Y-%m-%d %H:%M')))
    con.commit()


if __name__ == '__main__':
    main()
