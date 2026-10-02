# -*- coding: utf-8 -*-
"""
관세청 국가별 품목별 수출입실적(GW) → data/radar.db trade_cty (품목 · HS · 연월 · 상대국)

  API   : https://apis.data.go.kr/1220000/nitemtrade/getNitemtradeList
  인증  : DATA_GO_KR_KEY (공공데이터포털에서 「관세청_국가별 품목별 수출입실적(GW)」 활용신청이 따로 필요)
  요청  : strtYymm · endYymm (1년 이내) · hsSgn · cntyCd(상대국 코드, 비우면 전체 국가)
  동작  : 처음엔 최근 36개월, 이후엔 최근 14개월만 다시 받음 · 승인 전이면 meta.cty_err 에 남기고 끝냄
"""
import os, re, sys, time
import urllib.parse, urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import KST, db
from items import ITEMS
from collect_trade import months, chunks, num

API = 'https://apis.data.go.kr/1220000/nitemtrade/getNitemtradeList'
SCHEMA = """CREATE TABLE IF NOT EXISTS trade_cty(
  item TEXT NOT NULL, hs TEXT NOT NULL, ym TEXT NOT NULL, cty TEXT NOT NULL, cty_nm TEXT,
  exp_kg REAL, exp_usd REAL, imp_kg REAL, imp_usd REAL, PRIMARY KEY(item, hs, ym, cty));"""
# 전체 국가 조회가 막혀 있을 때 쓰는 주요 상대국 (임산물 교역 상위)
MAIN = ['CN', 'US', 'JP', 'VN', 'TW', 'HK', 'TH', 'AU', 'CL', 'TR', 'IT', 'FR', 'ES', 'UZ', 'KP', 'MY', 'ID', 'CA', 'NZ', 'DE']


def txt(el, *names):
    for c in el:
        if c.tag.lower() in [n.lower() for n in names]:
            return (c.text or '').strip()
    return ''


def fetch(key, hs, a, b, cty=''):
    k = key if '%' in key else urllib.parse.quote(key, safe='')
    url = '%s?serviceKey=%s&strtYymm=%s&endYymm=%s&hsSgn=%s%s' % (API, k, a.replace('-', ''), b.replace('-', ''), hs,
                                                                   ('&cntyCd=' + cty) if cty else '')
    last = None
    for i in range(3):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent': 'forest-radar'}), timeout=40) as r:
                return r.read()
        except Exception as ex:
            last = ex
            time.sleep(3 * (i + 1))
    raise last


def parse(b):
    root = ET.fromstring(b)
    code = ''.join(x.text or '' for x in root.iter() if x.tag.lower() in ('resultcode', 'returnreasoncode')).strip()
    msg = ''.join(x.text or '' for x in root.iter() if x.tag.lower() in ('resultmsg', 'returnauthmsg', 'errmsg')).strip()
    rows = []
    for it in root.iter():
        if it.tag.lower() != 'item':
            continue
        m = re.match(r'^(\d{4})\D?(\d{2})$', txt(it, 'year'))
        cty = txt(it, 'statCd', 'cntyCd')
        if not m or not cty or cty in ('-', '총계'):
            continue
        rows.append({'ym': '%s-%s' % m.groups(), 'cty': cty, 'nm': txt(it, 'statCdCntnKor1', 'statCdCntnKor', 'cntyNm'),
                     'hs': re.sub(r'\D', '', txt(it, 'hsCd')), 'kor': txt(it, 'statKor', 'statKorNm'),
                     'ek': num(txt(it, 'expWgt')), 'eu': num(txt(it, 'expDlr')), 'ik': num(txt(it, 'impWgt')), 'iu': num(txt(it, 'impDlr'))})
    return code, msg, rows


def main():
    con = db()
    con.executescript(SCHEMA)
    key = os.environ.get('DATA_GO_KR_KEY', '').strip()
    if not key:
        print('DATA_GO_KR_KEY 없음 → 건너뜀')
        return
    now = datetime.now(KST)
    end = '%04d-%02d' % (now.year, now.month)
    # 접속 · 승인 점검 (밤 껍데기 있는 것 · 전년 1~3월)
    probe = '%04d-01' % (now.year - 1), '%04d-03' % (now.year - 1)
    mode = 'all'
    try:
        raw = fetch(key, '080241', *probe)
        code, msg, rows = parse(raw)
        print('점검(전체 국가) : 코드 %s %s · 행 %d' % (code, msg, len(rows)))
        print('  응답 앞부분 :', raw[:500].decode('utf-8', 'ignore'))
        if not rows:
            raw = fetch(key, '080241', *probe, cty='JP')
            code, msg, rows = parse(raw)
            print('점검(일본) : 코드 %s %s · 행 %d' % (code, msg, len(rows)))
            print('  응답 앞부분 :', raw[:500].decode('utf-8', 'ignore'))
            mode = 'main'
        if not rows:
            raise RuntimeError('%s %s' % (code, msg))
    except Exception as ex:
        body = ex.read()[:300].decode('utf-8', 'ignore') if hasattr(ex, 'read') else ''
        note = ' (「관세청_국가별 품목별 수출입실적(GW)」 활용신청 필요)' if 'NOT_REGISTERED' in body + str(ex) else ''
        print('국가별 수출입 수집 중단 : %s %s%s' % (ex, body[:200], note))
        con.execute('INSERT OR REPLACE INTO meta(k,v) VALUES(?,?)', ('cty_err', ('%s %s%s' % (ex, body, note))[:300]))
        con.commit()
        return
    con.execute("DELETE FROM meta WHERE k='cty_err'")
    for it in ITEMS:
        for src in it['hs']:
            have = con.execute('SELECT COUNT(*) FROM trade_cty WHERE item=? AND hs LIKE ?', (it['key'], src['q'] + '%')).fetchone()[0]
            ms = months('%04d-%02d' % (now.year - 3, now.month), end)
            ms = ms if have == 0 else ms[-14:]
            ms = [m for m in ms if src.get('since', '0000') <= m <= src.get('until', '9999')]
            keep = re.compile(src['keep']) if src.get('keep') else None
            n = 0
            for ch in chunks(ms):
                for cty in (MAIN if mode == 'main' else ['']):
                    try:
                        code, msg, rows = parse(fetch(key, src['q'], ch[0], ch[-1], cty))
                    except Exception as ex:
                        print('  실패 %s %s %s : %s' % (it['label'], src['q'], cty, ex))
                        continue
                    for r in rows:
                        if keep and not keep.search(r['kor'] or ''):
                            continue
                        con.execute('INSERT OR REPLACE INTO trade_cty VALUES(?,?,?,?,?,?,?,?,?)',
                                    (it['key'], r['hs'] or src['q'], r['ym'], r['cty'], r['nm'], r['ek'] or 0, r['eu'] or 0,
                                     r['ik'] or 0, r['iu'] or 0))
                        n += 1
                    time.sleep(0.15)
            con.commit()
            print('[%s] %s 저장 %d행' % (it['label'], src['q'], n))
    con.execute('INSERT OR REPLACE INTO meta(k,v) VALUES(?,?)', ('cty_run', now.strftime('%Y-%m-%d %H:%M')))
    con.commit()


if __name__ == '__main__':
    main()
