"""候補・収録状況・帳票を検索。適用判断や診断計算は行わない。"""
from pathlib import Path
import argparse,json,sys,unicodedata,re
ROOT=Path(__file__).resolve().parents[1]
def norm(s):return unicodedata.normalize('NFKC',s).lower()
def aliases(s):
    result=[norm(s)]
    if s.endswith(('県','府','都','市')):result.append(norm(s[:-1]))
    if s=='東京都建設局':result+=['東京都','東京']
    if s=='国土交通省':result+=['国交省']
    return [norm(x) for x in result]
def lookup(query):
    cards=json.loads((ROOT/'references/criteria.json').read_text(encoding='utf-8'))
    coverage=json.loads((ROOT/'references/coverage.json').read_text(encoding='utf-8'))
    forms=json.loads((ROOT/'references/forms.json').read_text(encoding='utf-8'))
    tokens=norm(query).split()
    names={a for c in cards+forms+coverage for key in ['issuer','prefecture'] for a in aliases(c.get(key,'')) if a}
    regions=[t for t in tokens if t in names]
    rest=[t for t in tokens if t not in regions]
    def same_region(r):return all(t in aliases(r.get('issuer',''))+aliases(r.get('prefecture','')) for t in regions)
    def text(r):return norm(r.get('search_text','')+' '+json.dumps(r,ensure_ascii=False))
    def select(rows):
        pool=[r for r in rows if same_region(r)]
        exact=[r for r in pool if all(t in text(r) for t in rest)]
        fallback=bool(not exact and regions and pool)
        chosen=pool if fallback else exact
        return [{**r,'match':'region_fallback' if fallback else 'all_terms','unmatched_terms':[t for t in rest if t not in text(r)]} for r in chosen]
    found=select(cards);foundforms=select(forms)
    cov=[c for c in coverage if any(t in aliases(c['prefecture']) for t in regions)]
    return {'status':'results' if found or foundforms or cov else 'no_match','note':'地域のみ一致する候補は工程・条件への適用確定ではない。0件も資料の不存在を意味しない。県一覧はこの配布版の収録状況のみ。未収録の基準は推測しない。','candidates':found,'prefecture_coverage':cov,'forms':foundforms}
if __name__=='__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    a=argparse.ArgumentParser();a.add_argument('query',nargs='+');args=a.parse_args()
    print(json.dumps(lookup(' '.join(args.query)),ensure_ascii=False,indent=2))
