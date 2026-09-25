# -*- coding: utf-8 -*-
"""2024 임산물생산조사 보고서 PDF → 텍스트(레이아웃 유지) 덤프 (1회성)"""
import os, subprocess, urllib.request, urllib.parse, http.cookiejar
OUT = 'probe/prod4'; os.makedirs(OUT, exist_ok=True)
B = 'https://kfss.forest.go.kr/stat'
cj = http.cookiejar.CookieJar()
op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
op.addheaders = [('User-Agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/124'), ('Accept-Language', 'ko-KR')]
op.open(B + '/ptl/article/articleList.do?curMenu=9847&bbsId=ptlPdsMntProdReq', timeout=60).read()
b = op.open(B + '/ptl/article/articleFileDown.do?' + urllib.parse.urlencode({'fileSeq': '8135', 'workSeq': '2664'}), timeout=300).read()
open('/tmp/p2024.pdf', 'wb').write(b)
print('pdf bytes', len(b))
subprocess.run(['pdftotext', '-layout', '/tmp/p2024.pdf', OUT + '/p2024.txt'], check=False)
print(subprocess.run(['pdfinfo', '/tmp/p2024.pdf'], capture_output=True, text=True).stdout)
