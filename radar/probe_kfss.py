# 산림임업통계플랫폼 게시판 목록 점검 (임가경제조사 자료실 찾기) - 결과를 data/probe_kfss.txt 로 남김
import re, json, urllib.parse, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from collect_prod import opener, B
op = opener()
out = []
for path in ['/ptl/main/main.do', '/ptl/article/articleList.do?curMenu=9847&bbsId=ptlPdsMntProdReq']:
    try:
        h = op.open(B + path, timeout=60).read().decode('utf-8', 'ignore')
        for m in re.finditer(r'<a[^>]+href="([^"]*(?:bbsId|curMenu)[^"]*)"[^>]*>\s*([^<]{2,40})<', h):
            out.append('%s | %s' % (m.group(2).strip(), m.group(1)))
        out.append('== %s len %d' % (path, len(h)))
        for m in re.finditer(r'.{0,120}임가.{0,120}', h):
            out.append('CTX ' + re.sub(r'\s+', ' ', m.group(0)))
    except Exception as ex:
        out.append('ERR %s %s' % (path, ex))
for bid in ['ptlPdsMntEcoReq', 'ptlPdsMntFhEcoReq', 'ptlPdsMntFrstHsEcoReq', 'ptlPdsMntEconReq', 'ptlPdsMntFhReq', 'ptlPdsMntMgmtReq']:
    try:
        q = urllib.parse.urlencode({'bbsId': bid, 'pageIndex': 1, 'pageUnit': 20, 'recordCountPerPage': 20})
        d = json.loads(op.open(B + '/ptl/article/selectArticleList.do?' + q, timeout=60).read()).get('data') or []
        out.append('BBS %s : %s' % (bid, ' / '.join((r.get('title') or '') for r in d[:8])))
    except Exception as ex:
        out.append('BBS %s ERR %s' % (bid, ex))
open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data', 'probe_kfss.txt'), 'w').write('\n'.join(sorted(set(out))))
