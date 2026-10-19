"""本機預標 100 筆真實品名；只寫私人資料夾，原盲標檔和舊預測不覆寫。"""
import argparse
import copy
import hashlib
import json
from pathlib import Path

from src.ml.attributes import AttributeDescriber, MODEL_VERSION
from scripts.attribute_review import evaluate, read_groups, read_jsonl, validate_groups


def private_directory(folder):
    folder = Path(folder).resolve()
    parts = tuple(part.lower() for part in folder.parts)
    if not any(parts[i:i+2] == ('data', 'private') for i in range(len(parts)-1)):
        raise ValueError('private_directory_required')
    return folder


def version_tag(model_version):
    return hashlib.sha256(model_version.encode()).hexdigest()[:12]


def prediction_path(folder, model_version):
    return Path(folder)/f'predictions-{version_tag(model_version)}.jsonl'


def predict(folder, describe, model_version):
    folder = private_directory(folder)
    groups = read_groups(folder)
    rows = validate_groups(groups)
    output = prediction_path(folder, model_version)
    if output.exists():
        raise FileExistsError('predictions_already_exist')
    answers = describe([row['name'] for row in rows])
    if not isinstance(answers, list) or len(answers) != len(rows):
        raise ValueError('prediction_count_mismatch')
    predictions = [{'id': row['id'], 'name': row['name'], 'source': 'real', 'attributes': answer,
                    'model_version': model_version, 'review_status': 'unreviewed_model_prediction'}
                   for row, answer in zip(rows, answers)]
    result = evaluate(groups, predictions, model_version)
    with output.open('x', encoding='utf-8') as stream:
        stream.write(''.join(json.dumps(row, ensure_ascii=False)+'\n' for row in predictions))
    return {key: value for key, value in result.items() if key != 'metrics'}


def prepare_assisted(folder, groups, predictions, model_version):
    folder = private_directory(folder)
    result = evaluate(groups, predictions, model_version)
    if result['predicted_items'] != 100:
        raise ValueError('predictions_not_complete')
    destination = folder/f'assisted-{version_tag(model_version)}'
    destination.mkdir()  # Existing human edits are never replaced.
    by_id = {row['id']: row for row in predictions}
    lines = ['# 100 筆本機預標審核表', '', '此檔含真實品名，只留本機，不貼到聊天或公開網站。', '',
             '這份是本機 Qwen 的預標，尚未人工確認，也不是盲標。分成四份各 25 筆供檢查。', '',
             '每列列出所有 true、所有未知布林與三個其他欄位；未列入「成立」或「未知」的布林皆是 false。',
             'sugar=null 表示未指定甜度；fun=null 表示非娛樂；species=null 表示未寫物種。',
             '請在同目錄 reviewer-1 到 reviewer-4.jsonl 修正 attributes，確認該列後才把 review_status 改為 human_confirmed；保留 ID、品名與 model_assisted 來源。',
             '若整份核對無誤，可在聊天只回報「這 100 筆預標已確認」；需修改時只提 ID、欄位與新值，不要貼真實品名。', '',
             '欄位說明：food 人類食品飲品、meal 熟食正餐、drink 飲品、fresh 未烹調生鮮、daily 日用文具、tech 電子產品、sport 運動場館課程。',
             '屬性說明：clearance 即期食品、quick 飯糰三明治微波正餐、cooking 下廚生鮮、kitchen 調味料油米、sport_supply 乳清能量補給、sport_gear 運動裝備、car_care 車輛保養、bulk 大包裝、home 家居香氛、stationery 文具、pet_food 寵物食品、pet_supply 寵物用品、alcohol 飲用酒。',
             'sugar：0 無糖、0.3 微糖、0.5 半糖、0.7 少糖、1 全糖；species：cat 貓、dog 狗。', '',
             f'模型版本：`{model_version}`', '', '| 組 | ID | 品名 | 成立的布林 | 未知的布林 | sugar | fun | species |',
             '|---:|---|---|---|---|---|---|---|']
    def cell(value):
        # Escape Markdown/HTML because product text is untrusted data.
        import html
        text = html.escape(str(value)).replace('|','&#124;').replace('\r',' ').replace('\n',' ')
        for char in '\\`*_{}[]()#!':
            text = text.replace(char, f'&#{ord(char)};')
        return text
    for index, group in enumerate(groups, 1):
        drafts = []
        for source in group:
            row = copy.deepcopy(source)
            row.update(attributes=copy.deepcopy(by_id[row['id']]['attributes']), review_status='pending_human_review',
                       review_method='model_assisted', model_version=model_version)
            row.pop('confirmation', None); row.pop('human_confirmed', None)
            drafts.append(row)
            values = row['attributes']
            positive = ', '.join(k for k,v in values.items() if v is True) or '無'
            unknown = ', '.join(k for k,v in values.items() if v is None and k not in ('sugar','fun','species')) or '無'
            cells = [index, row['id'], row['name'], positive, unknown, *(json.dumps(values[k],ensure_ascii=False) for k in ('sugar','fun','species'))]
            lines.append('| '+' | '.join(cell(value) for value in cells)+' |')
        (destination/f'reviewer-{index}.jsonl').write_text(''.join(json.dumps(row,ensure_ascii=False)+'\n' for row in drafts),encoding='utf-8')
    (destination/'review-preview.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    return destination


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--review-dir', type=Path, required=True)
    parser.add_argument('--server-url', default='http://127.0.0.1:8080')
    parser.add_argument('--assisted', action='store_true')
    args = parser.parse_args(argv)
    try:
        client = AttributeDescriber(server_url=args.server_url)
        summary = predict(args.review_dir, client.describe_items, client.model_version)
        if args.assisted:
            prepare_assisted(args.review_dir, read_groups(args.review_dir),
                             read_jsonl(prediction_path(args.review_dir, client.model_version)), client.model_version)
        print(json.dumps(summary, ensure_ascii=False))
        return 0
    except (OSError, ValueError, KeyError, TypeError):
        print(json.dumps({'status':'prediction_or_private_output_failed'}))
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
