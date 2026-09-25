# -*- coding: utf-8 -*-
"""KREI 접속 점검 2차 - 여러 주소의 응답 코드 · 본문 앞부분 기록"""
import os, json, urllib.request, urllib.error, ssl
OUT = 'probe'; os.makedirs(OUT, exist_ok=True)
UA = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36',
      'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8', 'Accept-Language': 'ko-KR,ko;q=0.9'}
URLS = [
 'https://www.krei.re.kr/',
 'https://www.krei.re.kr/krei/page/21',
 'https://krei.re.kr/krei/page/21',
 'https://www.krei.re.kr/krei/selectBbsNttList.do?key=81&bbsNo=74&searchCtgry=%EB%96%AB%EC%9D%80%EA%B0%90&searchCnd=all',
 'https://www.krei.re.kr/krei/selectBbsNttList.do?bbsNo=74&key=81',
 'https://krei.re.kr/krei/selectBbsNttView2.do?bbsNo=74&integrDeptCode=&key=81&nttNo=74028&pageIndex=9&searchCnd=all&searchCtgry=%ED%91%9C%EA%B3%A0%EB%B2%84%EC%84%AF&searchKrwd=',
 'https://krei.re.kr/attach/observ/2026/07/03/2f4606da-f57f-429f-bf5e-cb7ec23e91b6.pdf',
 'https://aglook.krei.re.kr/',
]
log = []
for i, u in enumerate(URLS):
    rec = {'url': u}
    try:
        req = urllib.request.Request(u, headers=UA)
        with urllib.request.urlopen(req, timeout=30) as r:
            b = r.read(); rec.update(status=r.status, final=r.geturl(), ctype=r.headers.get('Content-Type'), bytes=len(b))
    except urllib.error.HTTPError as e:
        b = e.read(); rec.update(status=e.code, ctype=e.headers.get('Content-Type'), bytes=len(b), server=e.headers.get('Server'))
    except Exception as ex:
        b = b''; rec['error'] = repr(ex)
    ext = 'pdf' if b[:4] == b'%PDF' else 'html'
    if b:
        open(os.path.join(OUT, 'p%02d.%s' % (i, ext)), 'wb').write(b[:3000000])
    rec['head'] = b[:300].decode('utf-8', 'ignore') if ext == 'html' else '%PDF'
    log.append(rec)
json.dump(log, open(os.path.join(OUT, 'log.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print(json.dumps(log, ensure_ascii=False, indent=1))
