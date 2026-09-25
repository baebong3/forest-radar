# -*- coding: utf-8 -*-
"""로고 원본 받기 (1회성)"""
import os, urllib.request
OUT = 'probe/logos'; os.makedirs(OUT, exist_ok=True)
UA = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36'}
URLS = {'sp_header': 'https://cdn.imweb.me/thumbnail/20240725/1b132fa97dba8.png',
        'sp_small': 'https://cdn.imweb.me/thumbnail/20240725/47bb9799054eb.png',
        'sp_org': 'https://cdn.imweb.me/upload/S202407257fd1d0a9d4a2d/cef9e25e6fc9e.png',
        'kofpi_new': 'https://www.kofpi.or.kr/resources/img/common/new_logo.png'}
for k, u in URLS.items():
    try:
        with urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=30) as r:
            open('%s/%s.png' % (OUT, k), 'wb').write(r.read())
        print('ok', k)
    except Exception as ex:
        print('fail', k, ex)
