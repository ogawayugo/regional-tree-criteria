"""出典の欠落と生成物の不整合を検査する。原典の内容・利用許諾は検証しない。"""
from pathlib import Path
from urllib.parse import urlsplit
import hashlib,json,sys
ROOT=Path(__file__).resolve().parents[1]
def validate(root=ROOT):
    cards=json.loads((root/'references/criteria.json').read_text(encoding='utf-8'))
    forms=json.loads((root/'references/forms.json').read_text(encoding='utf-8'))
    def url(value):
        p=urlsplit(value)
        assert p.scheme=='https' and p.hostname and not p.query and not p.username, 'Invalid source URL'
    for c in cards:
        assert c['facts'], c['id']
        body=(root/c['file']).read_text(encoding='utf-8')
        for f in c['facts']:
            s=f['source'];url(s['url'])
            assert all(s.get(k) for k in ('title','locator')),c['id']
            assert '未確認' not in s['locator'],c['id']
            assert f['summary'] in body and s['url'] in body and s['locator'] in body,c['id']
    for f in forms:
        assert f['sources'],f['id']
        for s in f['sources']:
            url(s['url'])
            assert any(s.get(k) for k in ('pdf_pages','printed_pages','sheet','section')),f['id']
    for c in json.loads((root/'references/coverage.json').read_text(encoding='utf-8')):
        assert c['card_ids']==[d['id'] for d in cards if d['prefecture']==c['prefecture']]
    manifest=json.loads((root/'manifest.json').read_text(encoding='utf-8'))
    for name,digest in manifest['files'].items():
        assert hashlib.sha256((root/name).read_bytes()).hexdigest()==digest,name
    assert not (root/'references/survey.md').exists()
    return {'cards':len(cards),'facts':sum(len(c['facts']) for c in cards),'forms':len(forms),'manifest_files':len(manifest['files'])}
if __name__=='__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    print(json.dumps(validate(),ensure_ascii=False))
