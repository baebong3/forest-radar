# -*- coding: utf-8 -*-
"""KREI 임업관측정보 게시판 구조 점검 (Actions에서 1회성 실행 → probe/ 에 원본 저장)"""
import os, re, urllib.parse, urllib.request, html, json, sys
BASE = 'https://www.krei.re.kr'
LIST = BASE + '/krei/selectBbsNttList.do?key=81&bbsNo=74&searchCtgry={c}&searchCnd=all&pageIndex=1'
OUT = 'probe'
os.makedirs(OUT, exist_ok=True)
UA = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36',
      'Accept-Language': 'ko-KR,ko;q=0.9'}
log = []

def get(url, binary=False):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=30) as r:
        b = r.read()
        return b, r.headers.get('Content-Type', ''), r.geturl()

for cat in ['', '밤', '떫은감', '표고버섯', '호두', '대추', '잣']:
    url = LIST.format(c=urllib.parse.quote(cat))
    try:
        b, ct, final = get(url)
    except Exception as ex:
        log.append({'cat': cat, 'error': str(ex)}); continue
    name = 'list_%s.html' % (cat or 'all')
    open(os.path.join(OUT, name), 'wb').write(b)
    t = b.decode('utf-8', 'ignore')
    links = re.findall(r'href="([^"]*selectBbsNttView[^"]*)"', t)
    log.append({'cat': cat, 'status': 'ok', 'bytes': len(b), 'final': final, 'posts': len(links), 'first': links[:3]})
    if cat in ('밤', '표고버섯', '떫은감') and links:
        purl = urllib.parse.urljoin(url, html.unescape(links[0]))
        try:
            pb, _, _ = get(purl)
            open(os.path.join(OUT, 'post_%s.html' % cat), 'wb').write(pb)
            pt = pb.decode('utf-8', 'ignore')
            files = re.findall(r'href="([^"]*(?:\.pdf|fileDown|download|FileDown)[^"]*)"', pt, re.I)
            log[-1]['post'] = purl; log[-1]['files'] = files[:6]
            for f in files[:1]:
                furl = urllib.parse.urljoin(purl, html.unescape(f))
                fb, fct, _ = get(furl)
                open(os.path.join(OUT, 'file_%s.pdf' % cat), 'wb').write(fb)
                log[-1]['file'] = {'url': furl, 'ctype': fct, 'bytes': len(fb)}
        except Exception as ex:
            log[-1]['post_error'] = str(ex)
json.dump(log, open(os.path.join(OUT, 'log.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print(json.dumps(log, ensure_ascii=False, indent=1))
