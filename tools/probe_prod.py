# -*- coding: utf-8 -*-
"""임산물생산조사 자료 위치 점검 (1회성) → probe/prod/"""
import os, re, json, html, urllib.request, urllib.parse
OUT = 'probe/prod'; os.makedirs(OUT, exist_ok=True)
UA = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36',
      'Accept-Language': 'ko-KR,ko;q=0.9'}
URLS = {
 'kfss_list': 'https://kfss.forest.go.kr/stat/ptl/article/articleList.do?curMenu=9847&bbsId=ptlPdsMntProdReq',
 'kosis_h004': 'https://stat.kosis.kr/statHtml_host/statHtml.do?orgId=136&tblId=DT_136034_H004&dbUser=NSI_IN_136',
 'forest_cms': 'https://www.forest.go.kr/kfsweb/kfi/kfs/cms/cmsView.do?mn=NKFS_04_05_02&cmsId=FC_000076',
 'index1302': 'https://www.index.go.kr/unity/potal/main/EachDtlPageDetail.do?idx_cd=1302',
}
log = {}
def get(u, data=None):
    req = urllib.request.Request(u, data=data, headers=UA)
    with urllib.request.urlopen(req, timeout=40) as r:
        return r.read(), r.geturl(), r.headers.get('Content-Type', '')
for k, u in URLS.items():
    try:
        b, final, ct = get(u)
        t = b.decode('utf-8', 'ignore')
        open('%s/%s.html' % (OUT, k), 'w', encoding='utf-8').write(t)
        links = re.findall(r'(?:href|onclick)=["\']([^"\']*(?:download|Down|down|file|atch|\.xlsx|\.xls|\.pdf|\.hwp|articleView|fn_)[^"\']*)["\']', t)
        log[k] = {'final': final, 'bytes': len(b), 'links': links[:60]}
    except Exception as ex:
        log[k] = repr(ex)
json.dump(log, open(OUT + '/log.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print(json.dumps(log, ensure_ascii=False, indent=1)[:5000])
