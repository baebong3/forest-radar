# -*- coding: utf-8 -*-
"""로고 후보 수집 (1회성) - 홈페이지 HTML에서 logo가 들어간 이미지 주소를 찾아 probe/logos/ 에 저장"""
import os, re, json, urllib.request, urllib.parse
OUT = 'probe/logos'; os.makedirs(OUT, exist_ok=True)
UA = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36'}
SITES = {'sp': 'https://www.southernpost.co.kr/', 'kofpi': 'https://www.kofpi.or.kr/index.do', 'kofpi2': 'https://www.kofpi.or.kr/'}
log = {}
def get(u):
    with urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=30) as r:
        return r.read(), r.geturl()
for k, u in SITES.items():
    try:
        b, final = get(u)
    except Exception as ex:
        log[k] = repr(ex); continue
    t = b.decode('utf-8', 'ignore')
    open('%s/%s.html' % (OUT, k), 'w', encoding='utf-8').write(t)
    cands = re.findall(r'(?:src|href|content)=["\']([^"\']+\.(?:png|svg|jpg|jpeg|gif|webp)[^"\']*)["\']', t, re.I)
    cands += re.findall(r'url\(["\']?([^"\')]+\.(?:png|svg|jpg|jpeg|webp))', t, re.I)
    pick = [c for c in cands if re.search(r'logo|ci|symbol|brand|og', c, re.I)][:12]
    log[k] = {'final': final, 'cands': pick}
    for i, c in enumerate(pick):
        cu = urllib.parse.urljoin(final, c)
        try:
            ib, _ = get(cu)
            ext = re.search(r'\.(png|svg|jpg|jpeg|gif|webp)', cu, re.I).group(1).lower()
            open('%s/%s_%02d.%s' % (OUT, k, i, ext), 'wb').write(ib)
        except Exception as ex:
            pass
json.dump(log, open(OUT + '/log.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print(json.dumps(log, ensure_ascii=False, indent=1))
