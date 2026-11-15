from pathlib import Path
import json,html,re,hashlib
p=Path(__file__).resolve().parents[1];refs=p/'references';data=json.loads((refs/'criteria.json').read_text(encoding='utf-8'));forms=json.loads((refs/'forms.json').read_text(encoding='utf-8'));cov=json.loads((refs/'coverage.json').read_text(encoding='utf-8'))
def inline(s):
 s=html.escape(s)
 s=s.replace('../forms.json','references/forms.json')
 s=re.sub(r'\[([^\]]+)\]\((https?://[^)]+|references/forms.json)\)',r'<a href="\2">\1</a>',s)
 s=re.sub(r'(?<!["\(])(https?://[^\s<>]+)',lambda m:m[0] if m.start()>0 and s[m.start()-1]=='"' else m[0],s)
 return s.replace('&lt;br&gt;','<br>')
def md(s):
 lines=s.splitlines();out=[];table=False
 for l in lines:
  if l.startswith('|'):
   if re.match(r'^\|[-: |]+\|$',l):continue
   if not table:out.append('<div class="table"><table>');table=True
   out.append('<tr>'+''.join('<td>'+inline(c.strip())+'</td>' for c in l.strip('|').split('|'))+'</tr>');continue
  if table:out.append('</table></div>');table=False
  if l.startswith('#'):out.append('<h3>'+inline(l.lstrip('# '))+'</h3>')
  elif re.match(r'^https?://',l.strip()):out.append('<p><a href="'+html.escape(l.strip(),quote=True)+'">原典</a></p>')
  elif l.strip():out.append('<p>'+inline(l)+'</p>')
 if table:out.append('</table></div>')
 return '\n'.join(out)
idx='# 地域と管理者の索引\n\nv0.1.2。4都道府県・14市・国指針の19カード。市には管理手順・帳票のみの資料も含む。\n\n|所在|管理者|対象・内容|出典位置|\n|---|---|---|---|\n'
for d in data:idx+='|'+d['prefecture']+'|['+d['issuer']+'](cards/'+d['id']+'.md)|'+d['scope']+'／'+d['available']+'|'+d['locator']+'|\n'
idx+='\n[47都道府県の収録状況](coverage.json)・[74帳票の所在](forms.json)・[基準台帳](criteria.json)\n\n帳票台帳は東京国道事務所・国総研1059号・吹田市・福岡市のカード外22票も含む。出典欄はPDF頁・紙面頁・シート・節のうち存在するものを読む。県名の依頼は市カードだけで終わらず収録台帳も参照する。\n';(refs/'index.md').write_text(idx,encoding='utf-8')
articles=''
for d in data:
 content=(p/d['file']).read_text(encoding='utf-8')
 articles+='<article data-kind="card" data-id="'+d['id']+'"><p class="match"></p>'+md(content)+'</article>'
for i,c in enumerate(cov):articles+='<article data-kind="coverage" data-id="'+str(i)+'"><h3>'+c['prefecture']+'の収録資料</h3><p>'+c['status']+'：'+c['status_definition']+'</p><p>'+c['gap']+'</p><p>'+c['scope']+'</p><p>県内カード：'+', '.join(c['card_ids'])+'</p></article>'
for f in forms:
 articles+='<article data-kind="form" data-id="'+f['id']+'"><p class="match"></p><h3>'+html.escape(f['issuer']+'｜'+f['name'])+'</h3><p>'+html.escape(f['stage_label']+'｜'+f['scope']+'｜'+f['status'])+'</p>'
 for s in f['sources']:
  label=' / '.join(k+': '+str(v) for k,v in s.items() if k!='url' and v is not None);articles+='<p><a href="'+html.escape(s['url'],quote=True)+'">原典</a> '+html.escape(label)+'</p>'
 articles+='</article>'
js='''
function norm(s){return s.normalize('NFKC').toLowerCase()}
function aliases(s){let a=[s];if(/[県府都市]$/.test(s))a.push(s.slice(0,-1));if(s==='東京都建設局')a.push('東京都','東京');if(s==='国土交通省')a.push('国交省');return a.map(norm)}
function lookup(q){let tokens=norm(q).trim().split(/\\s+/).filter(Boolean),names=new Set([...DATA.cards,...DATA.forms,...DATA.coverage].flatMap(r=>[...aliases(r.issuer||''),...aliases(r.prefecture||'')]).filter(Boolean));let regions=tokens.filter(t=>names.has(t)),rest=tokens.filter(t=>!names.has(t));function select(rows){let pool=rows.filter(r=>regions.every(t=>[...aliases(r.issuer||''),...aliases(r.prefecture||'')].includes(t)));let exact=pool.filter(r=>rest.every(t=>norm(JSON.stringify(r)).includes(t))),fall=!exact.length&&regions.length&&pool.length;return (fall?pool:exact).map(r=>({...r,match:fall?'地域のみ一致':'検索語一致',unmatched_terms:rest.filter(t=>!norm(JSON.stringify(r)).includes(t))}))}return {cards:select(DATA.cards),forms:select(DATA.forms),coverage:DATA.coverage.filter(c=>!tokens.length||regions.some(t=>aliases(c.prefecture).includes(t)))}}
function filter(){let q=document.getElementById('query').value,result=lookup(q),mode=document.getElementById('mode').value,count=0;document.querySelectorAll('article').forEach(a=>{let kind=a.dataset.kind,rows=result[kind==='card'?'cards':kind==='form'?'forms':'coverage'];let r=rows.find(r=>kind==='coverage'?DATA.coverage[+a.dataset.id].prefecture===r.prefecture:r.id===a.dataset.id);a.hidden=!r||(mode!=='all'&&mode!==kind);if(!a.hidden)count++;let note=a.querySelector('.match');if(note&&r)note.textContent=r.match+(r.unmatched_terms.length?'：一致しない語 '+r.unmatched_terms.join('、'):'')});document.getElementById('count').textContent=count+'件。地域のみの候補は適用確定ではありません。';}
if(typeof document!=='undefined')filter();
'''
(p/'index.html').write_text('<!doctype html><html lang="ja"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>地域別樹木診断資料 v0.1.2</title><style>body{max-width:1050px;margin:30px auto;padding:0 18px;font:16px/1.8 sans-serif;color:#203b31;background:#f7f9f6}article{background:white;margin:18px 0;padding:22px;border:1px solid #cbd8d0;border-radius:10px}article[hidden]{display:none}h3{font-size:20px}input,select{font:inherit;padding:10px;max-width:95%}table{border-collapse:collapse;width:100%}td{padding:8px;border:1px solid #cad5ce;vertical-align:top}.table{overflow:auto}a{color:#17634c;overflow-wrap:anywhere}.match{color:#805a14}p{overflow-wrap:anywhere}</style><h1>地域別の樹木診断資料</h1><p>試用版 v0.1.2。行政の公式資料ではありません。管理者・施設・指定版・診断段階を照合するための調査索引です。</p><p>19カード／47都道府県の収録状況／74帳票。出典URLと位置のない基準は掲載していません。</p><label for="query">地域・管理者・内容</label><br><input id="query" placeholder="北海道 三次診断、日立市 40%、埼玉県" oninput="filter()"><select id="mode" aria-label="資料の種類" onchange="filter()"><option value="all">すべて</option><option value="card">基準カード</option><option value="coverage">収録状況</option><option value="form">帳票</option></select><p id="count"></p>'+articles+'<script>const DATA='+json.dumps({'cards':data,'forms':forms,'coverage':cov},ensure_ascii=False).replace('</','<\\/')+';'+js+'</script></html>',encoding='utf-8')

manifest={f.relative_to(p).as_posix():hashlib.sha256(f.read_bytes()).hexdigest() for f in [p/'SKILL.md',p/'INSTALL.md',p/'NOTICE.md',p/'index.html',*sorted((p/'references').rglob('*')),*sorted((p/'scripts').glob('*.py'))] if f.is_file()}
(p/'manifest.json').write_text(json.dumps({'version':'0.1.2','files':manifest},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('Built index and manifest')
