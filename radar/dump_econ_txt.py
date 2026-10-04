# -*- coding: utf-8 -*-
"""산림임업통계플랫폼 임가경제조사 · 임산물소득조사 보고서 PDF → data/econ_txt/{econ|income}_연도.txt.gz (이미 받은 해는 건너뜀)"""
import gzip, json, os, re, sys, time, urllib.parse
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from collect_prod import opener, B, pdf_text

OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data', 'econ_txt')
BBS = {'econ': ('ptlPdsMntHouseEcono', '12509', r'임가\s*경제'), 'income': ('ptlPdsMntIncome', '9851', r'소득')}


def arts(op, bid, menu, pat):
    q = urllib.parse.urlencode({'bbsId': bid, 'curMenu': menu, 'pageIndex': 1, 'pageUnit': 50, 'recordCountPerPage': 50})
    rows = json.loads(op.open(B + '/ptl/article/selectArticleList.do?' + q, timeout=60).read()).get('data') or []
    by = {}
    for r in rows:
        t = r.get('title') or ''
        m = re.search(r'(20\d\d)', t)
        if not m or not re.search(pat, t):
            continue
        y, seq = int(m.group(1)), int(r['articleSeq'])
        if y not in by or seq > by[y][0]:
            by[y] = (seq, t)
    return by


def main(since=2015):
    os.makedirs(OUT, exist_ok=True)
    op = None
    for i in range(3):
        try:
            op = opener(); break
        except Exception as ex:
            print('재시도', ex); time.sleep(20)
    for kind, (bid, menu, pat) in BBS.items():
        try:
            by = arts(op, bid, menu, pat)
        except Exception as ex:
            print(kind, '목록 실패', ex); continue
        print(kind, sorted((y, t) for y, (s, t) in by.items()))
        for y in sorted(by):
            p = os.path.join(OUT, '%s_%d.txt.gz' % (kind, y))
            if y < since or os.path.exists(p):
                continue
            for i in range(2):
                try:
                    t = pdf_text(op, by[y][0])
                    gzip.open(p, 'wt', encoding='utf-8').write(t)
                    print(kind, y, len(t)); break
                except Exception as ex:
                    print(kind, y, '실패', ex); time.sleep(10)


if __name__ == '__main__':
    main()
