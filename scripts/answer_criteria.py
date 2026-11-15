"""確認済み根拠から定型回答。自由文の診断・推測・適用計算はしない。"""
import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
FIELDS = ('issuer', 'facility', 'stage', 'edition', 'topic', 'scope')
NOTICE = '収録版の原典記載の照会です。実木の安全性・伐採・個別契約への適用は判定していません。'


def load_database(root=ROOT):
    raw = (root / 'references/evidence.json').read_bytes()
    manifest = json.loads((root / 'manifest.json').read_text(encoding='utf-8'))
    digest = hashlib.sha256(raw).hexdigest()
    if digest != manifest['files'].get('references/evidence.json'):
        raise ValueError('根拠データのハッシュが不一致です。回答を停止します。')
    db = json.loads(raw)
    if db.get('schema_version') != 1:
        raise ValueError('未対応の根拠形式です。')
    for key, c in db['claims'].items():
        if not c.get('text') or c.get('status') not in ('checked', 'conflict') or not c.get('source_ids'):
            raise ValueError('未確認または出典のない根拠: ' + key)
        for sid in c['source_ids']:
            s = db['sources'][sid]
            if not (s.get('url', '').startswith('https://') and s.get('title') and s.get('pdf_page') and s.get('section') and s.get('sha256')):
                raise ValueError('出典情報の欠落: ' + sid)
    seen = set()
    for route in db['routes']:
        selector = route['selector']
        signature = tuple(selector[k] for k in FIELDS)
        if set(selector) != set(FIELDS) or signature in seen or not route['claim_ids']:
            raise ValueError('曖昧または空の照会条件です。')
        seen.add(signature)
        for cid in route['claim_ids']:
            if cid not in db['claims']:
                raise ValueError('不明な根拠ID: ' + cid)
    return db, digest


def answer(request, db, digest):
    if not isinstance(request, dict):
        raise ValueError('照会はJSONオブジェクトで指定してください。')
    if set(request) - set(FIELDS) - {'purpose'}:
        raise ValueError('未対応の入力項目です。自由文・測定値を解釈しません。')
    if any(not isinstance(v, str) for v in request.values()):
        raise ValueError('照会条件は文字列で指定してください。')
    result = {'schema_version': 1, 'evidence_sha256': digest, 'request': request,
              'status': '', 'claims': [], 'sources': {}, 'notice': NOTICE}
    missing = [k for k in (*FIELDS, 'purpose') if not request.get(k)]
    if missing:
        result.update(status='needs_context', missing_fields=missing)
        return result
    if request['purpose'] != '原典記載の照会':
        result.update(status='unsupported_purpose')
        return result
    routes = [r for r in db['routes'] if all(request[k] == r['selector'][k] for k in FIELDS)]
    if not routes:
        result.update(status='not_recorded')
        return result
    for cid in routes[0]['claim_ids']:
        claim = db['claims'][cid]
        result['claims'].append({'id': cid, **claim})
        for sid in claim['source_ids']:
            result['sources'][sid] = db['sources'][sid]
    result['status'] = 'source_conflict' if any(c['status'] == 'conflict' for c in result['claims']) else 'reference_only'
    return result


def render(result):
    messages = {'needs_context': '条件が不足しているため、基準を回答しません。',
                'unsupported_purpose': '実木の診断や措置の決定には対応していません。',
                'not_recorded': '指定条件に一致する確認済みの根拠は未収録です。近隣地域・別工程の基準で補いません。',
                'source_conflict': '原典内に不一致があるため、結論を確定しません。',
                'reference_only': '原典に記載された内容は次のとおりです。'}
    lines = [messages[result['status']]]
    if result.get('missing_fields'):
        lines.append('不足項目: ' + '、'.join(result['missing_fields']))
    if result['claims']:
        q = result['request']
        lines.append('照会条件: ' + '／'.join(q[k] for k in FIELDS))
    for c in result['claims']:
        lines.append(f"\n[{c['id']}] {c['text']}")
        for sid in c['source_ids']:
            s = result['sources'][sid]
            lines.append(f"出典: [{s['title']}・紙面{s['printed_page']}頁／PDF{s['pdf_page']}頁・{s['section']}]({s['url']})")
    lines.append('\n' + result['notice'])
    return '\n'.join(lines)


def packet(request, db, digest):
    result = answer(request, db, digest)
    result['answer_markdown'] = render(result)
    return result


def verify(request, proposed, db, digest):
    # Exact canonical equality also catches plausible invented prose, swapped citations,
    # dropped conflict companions, and an answer for a different request.
    if proposed != packet(request, db, digest):
        raise ValueError('回答が指定条件の定型回答と一致しません。根拠・条件・本文の改変を検出しました。')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--list', action='store_true', help='照会できる条件を表示')
    parser.add_argument('--request', type=Path, help='質問から確認した条件のJSON')
    parser.add_argument('--verify', type=Path, help='この照会に対する回答JSONを検査')
    parser.add_argument('--markdown', action='store_true')
    args = parser.parse_args()
    db, digest = load_database()
    if args.list:
        output = {'purpose': '原典記載の照会', 'selectors': [r['selector'] for r in db['routes']]}
    else:
        if not args.request:
            parser.error('--request または --list が必要です。')
        request = json.loads(args.request.read_text(encoding='utf-8-sig'))
        output = packet(request, db, digest)
        if args.verify:
            verify(request, json.loads(args.verify.read_text(encoding='utf-8-sig')), db, digest)
            output = {'valid': True}
        elif args.markdown:
            print(output['answer_markdown'])
            return
    print(json.dumps(output, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    try:
        main()
    except (ValueError, KeyError, OSError) as exc:
        print('回答停止: ' + str(exc), file=sys.stderr)
        sys.exit(2)
