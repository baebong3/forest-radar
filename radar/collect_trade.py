# -*- coding: utf-8 -*-
"""
관세청 품목별 수출입실적(GW) → data/radar.db trade 테이블 (월별 · 누적 · 멱등)

  API   : https://apis.data.go.kr/1220000/Itemtrade/getItemtradeList
  인증  : 공공데이터포털 서비스키 (환경변수 DATA_GO_KR_KEY, 일반 인증키 Decoding 값 권장)
  요청  : strtYymm · endYymm (YYYYMM, 1년 이내씩 나눠 요청) · hsSgn (HS 2 · 4 · 6 · 10단위)
  응답  : item 별 year(YYYY.MM) · hsCd · statKor · expWgt(kg) · expDlr($) · impWgt(kg) · impDlr($)

동작
  - 처음 실행(해당 품목 자료 없음) : --start 연월부터 전부 채움 (기본 2016-01)
  - 이후 실행 : 최근 --recent 개월(기본 14)만 다시 받아 덮어씀 (잠정치 → 확정치 수정 반영)
  - keep 정규식이 있는 코드는 API 한글 품목명이 맞는 줄만 저장

사용법
  python radar/collect_trade.py                     # 평소 (최근 14개월 갱신 + 빈 품목 백필)
  python radar/collect_trade.py --start 2012-01     # 백필 시작 연월 변경
  python radar/collect_trade.py --xml tests/x.xml --item chestnut --q 080241   # 저장된 응답으로 파서 점검
"""
import argparse, os, re, sys, time
import urllib.parse, urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import KST, db
from items import ITEMS, BY_KEY

API = 'https://apis.data.go.kr/1220000/Itemtrade/getItemtradeList'


def months(a, b):
    """'YYYY-MM' a..b 포함 목록"""
    y, m = map(int, a.split('-'))
    y2, m2 = map(int, b.split('-'))
    out = []
    while (y, m) <= (y2, m2):
        out.append('%04d-%02d' % (y, m))
        m += 1
        if m > 12:
            y, m = y + 1, 1
    return out


def chunks(ms, n=12):
    for i in range(0, len(ms), n):
        yield ms[i:i + n]


def num(s):
    s = (s or '').replace(',', '').strip()
    try:
        return float(s)
    except ValueError:
        return None


def _txt(el, *names):
    for n in names:
        for c in el:
            if c.tag.lower() == n.lower():
                return (c.text or '').strip()
    return ''


def parse(xml_bytes):
    """응답 XML → (결과코드, 메시지, [행]) ; 총계 줄은 버림"""
    root = ET.fromstring(xml_bytes)
    code = ''.join(x.text or '' for x in root.iter() if x.tag.lower() in ('resultcode', 'returnreasoncode'))
    msg = ''.join(x.text or '' for x in root.iter() if x.tag.lower() in ('resultmsg', 'returnauthmsg', 'errmsg'))
    rows = []
    for it in root.iter():
        if it.tag.lower() != 'item':
            continue
        yr = _txt(it, 'year')
        m = re.match(r'^(\d{4})\D?(\d{2})$', yr)
        if not m:                              # '총계' 등
            continue
        rows.append({
            'ym': '%s-%s' % m.groups(),
            'hs': re.sub(r'\D', '', _txt(it, 'hsCd')),
            'stat_kor': _txt(it, 'statKor', 'statKorNm'),
            'exp_kg': num(_txt(it, 'expWgt')), 'exp_usd': num(_txt(it, 'expDlr')),
            'imp_kg': num(_txt(it, 'impWgt')), 'imp_usd': num(_txt(it, 'impDlr')),
        })
    return code.strip(), msg.strip(), rows


def fetch(key, q, ym_from, ym_to, tries=2, timeout=20):
    k = key if '%' in key else urllib.parse.quote(key, safe='')    # Encoding 키를 넣어도 이중 인코딩 안 되게
    url = '%s?serviceKey=%s&strtYymm=%s&endYymm=%s&hsSgn=%s' % (API, k, ym_from.replace('-', ''),
                                                               ym_to.replace('-', ''), q)
    last = None
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'forest-radar'})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.read()
        except Exception as ex:                 # 공공데이터포털 일시 오류 대비 재시도
            last = ex
            time.sleep(2 * (i + 1))
    raise last


def store(con, item_key, src, rows):
    """keep 정규식으로 거른 뒤 저장 · 저장 건수 반환"""
    keep = re.compile(src['keep']) if src.get('keep') else None
    now = datetime.now(KST).strftime('%Y-%m-%d %H:%M')
    n = 0
    for r in rows:
        if keep and not keep.search(r['stat_kor'] or ''):
            continue
        hs = r['hs'] or src['q']
        con.execute('INSERT OR REPLACE INTO trade(item,hs,ym,stat_kor,form,exp_kg,exp_usd,imp_kg,imp_usd,fetched_at) '
                    'VALUES(?,?,?,?,?,?,?,?,?,?)',
                    (item_key, hs, r['ym'], r['stat_kor'], src.get('form', ''), r['exp_kg'] or 0, r['exp_usd'] or 0,
                     r['imp_kg'] or 0, r['imp_usd'] or 0, now))
        n += 1
    return n


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--start', default='2016-01', help='자료가 없는 품목의 백필 시작 연월')
    ap.add_argument('--recent', type=int, default=14, help='매번 다시 받는 최근 개월 수')
    ap.add_argument('--xml', help='저장된 응답 XML로 파서 · 저장만 점검')
    ap.add_argument('--item'), ap.add_argument('--q')
    a = ap.parse_args()
    con = db()

    if a.xml:
        code, msg, rows = parse(open(a.xml, 'rb').read())
        src = next(s for s in BY_KEY[a.item]['hs'] if s['q'] == a.q)
        print('결과코드 %s %s · 행 %d · 저장 %d' % (code, msg, len(rows), store(con, a.item, src, rows)))
        con.commit()
        return

    key = os.environ.get('DATA_GO_KR_KEY', '').strip()
    if not key:
        print('DATA_GO_KR_KEY 없음 → 수출입 수집 건너뜀 (저장소 Settings > Secrets에 등록 필요)')
        return

    now = datetime.now(KST)
    end = '%04d-%02d' % (now.year, now.month)
    first_err = None
    # 접속 점검 : 공공데이터포털이 응답하지 않으면(해외 서버 차단 · 장애) 오래 붙잡지 말고 바로 끝냄
    try:
        code, msg, rows = parse(fetch(key, '080241', '%04d-01' % (now.year - 1), '%04d-03' % (now.year - 1), tries=3, timeout=40))
        print('접속 점검 : 결과코드 %s %s · 행 %d' % (code, msg, len(rows)))
    except Exception as ex:
        body = ''
        if hasattr(ex, 'read'):
            try:
                body = ex.read()[:300].decode('utf-8', 'ignore')
            except Exception:
                pass
        em = re.findall(r'<(?:errMsg|returnAuthMsg)>([^<]+)<', body)
        ex = '%s %s' % (ex, ' · '.join(em) if em else re.sub(r'\s+', ' ', body)[:120])
        if 'NOT_REGISTERED' in body:
            ex += ' (이 인증키로 「관세청_품목별 수출입실적(GW)」 활용신청이 안 됐거나 승인 반영 대기 중)'
        print('접속 점검 실패 → 수출입 수집 중단 : %s' % ex)
        con.execute('INSERT OR REPLACE INTO meta(k,v) VALUES(?,?)', ('trade_err', '공공데이터포털 접속 실패 : %s' % str(ex)[:200]))
        con.commit()
        return
    fails = 0
    for it in ITEMS:
        for src in it['hs']:
            # 코드마다 따로 판단 : 새로 추가한 코드는 처음부터 채우고, 이미 있는 코드는 최근 몇 달만 다시 받음
            have = con.execute('SELECT COUNT(*) FROM trade WHERE item=? AND hs LIKE ?', (it['key'], src['q'] + '%')).fetchone()[0]
            ms = months(a.start, end) if have == 0 else months(a.start, end)[-a.recent:]
            ms = [m for m in ms if src.get('since', '0000') <= m <= src.get('until', '9999')]
            if not ms:
                continue
            got = kept = 0
            names = set()
            for ch in chunks(ms):
                try:
                    raw = fetch(key, src['q'], ch[0], ch[-1])
                    code, msg, rows = parse(raw)
                except Exception as ex:
                    first_err = first_err or '%s %s : %s' % (it['label'], src['q'], ex)
                    print('  실패 %s %s %s~%s : %s' % (it['label'], src['q'], ch[0], ch[-1], ex))
                    fails += 1
                    if fails >= 5:
                        break
                    continue
                fails = 0
                if code not in ('', '00', '0', '000') and not rows:
                    print('  API 응답 %s %s : %s %s' % (it['label'], src['q'], code, msg))
                    print('  응답 앞부분 :', raw[:300].decode('utf-8', 'ignore'))
                    first_err = first_err or '%s %s' % (code, msg)
                    break
                got += len(rows)
                names |= {r['stat_kor'] for r in rows}
                kept += store(con, it['key'], src, rows)
                time.sleep(0.2)
            con.commit()
            print('[%s] %-10s 응답 %4d행 · 저장 %4d행 · 품목명 %s' % (it['label'], src['q'], got, kept,
                                                               ' / '.join(sorted(n for n in names if n))[:120]))
    con.execute('INSERT OR REPLACE INTO meta(k,v) VALUES(?,?)', ('trade_run', now.strftime('%Y-%m-%d %H:%M')))
    if first_err:
        con.execute('INSERT OR REPLACE INTO meta(k,v) VALUES(?,?)', ('trade_err', first_err[:300]))
    else:
        con.execute('DELETE FROM meta WHERE k=?', ('trade_err',))
    con.commit()
    print('누적 %d행' % con.execute('SELECT COUNT(*) FROM trade').fetchone()[0])


if __name__ == '__main__':
    main()
