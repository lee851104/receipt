"""Run downloaded GGUFs locally, sequentially, at idle priority. No external API calls."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import socket
import subprocess
import time
import urllib.request
import uuid
from lab_core import decode_sparse, attach, BOOLEAN_FIELDS

ROOT = Path(__file__).resolve().parent


def begin_output(root, size):
    root = root.resolve()
    folder = (root / size).resolve()
    if folder.parent != root:
        raise ValueError('Output must be a direct child of results')
    if folder.exists():
        archive = (root / 'archive' / (time.strftime('%Y%m%d-%H%M%S') + '-' + size + '-' + uuid.uuid4().hex[:8])).resolve()
        if not archive.is_relative_to(root):
            raise ValueError('Archive outside experiment')
        archive.parent.mkdir(parents=True, exist_ok=True)
        folder.rename(archive)
    folder.mkdir(parents=True)
    return folder


def request(port, route, data=None, timeout=900):
    raw = None if data is None else json.dumps(data, ensure_ascii=False).encode('utf-8')
    req = urllib.request.Request(f'http://127.0.0.1:{port}/{route}', data=raw,
                                 headers={'Content-Type': 'application/json'})
    # Explicitly ignore system proxies for private local inference.
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    with opener.open(req, timeout=timeout) as response:
        return json.load(response)


def wire_schema(ids):
    labels = {'type': 'array', 'items': {'enum': BOOLEAN_FIELDS}, 'maxItems': len(BOOLEAN_FIELDS)}
    item = {'type': 'object', 'properties': {
        'id': {'enum': ids},
        'yes': labels, 'unknown': labels,
        'sugar': {'enum': [None, 0, 0.2, 0.3, 0.5, 0.7, 1]},
        'fun': {'enum': [None, 'movie', 'singing', 'show', 'game']},
        'species': {'enum': [None, 'cat', 'dog']}},
        'required': ['id', 'yes', 'unknown', 'sugar', 'fun', 'species'], 'additionalProperties': False}
    return {'type': 'object', 'properties': {'items': {'type': 'array', 'items': item,
            'minItems': len(ids), 'maxItems': len(ids)}}, 'required': ['items'], 'additionalProperties': False}


def run(size, dataset, batch_size, limit, model_path=None, output_root=None):
    folder = begin_output(output_root or ROOT / 'results', size)
    exe = next((ROOT / 'runtime' / 'llama-b11557').rglob('llama-server.exe'))
    model = model_path or ROOT / 'models' / f'qwen2.5-{size}-instruct-q4_k_m.gguf'
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 0)); port = sock.getsockname()[1]
    prompt = (ROOT / 'prompt-named-v2.txt').read_text(encoding='utf-8')
    items = dataset['items'][:limit] if limit else dataset['items']
    predictions, failures, timings = [], [], []
    command = [str(exe), '-m', str(model), '--host', '127.0.0.1', '--port', str(port),
               '-t', '2', '-tb', '2', '-ngl', '0', '-c', '4096', '-np', '1', '--no-warmup']
    flags = subprocess.CREATE_NO_WINDOW | subprocess.IDLE_PRIORITY_CLASS if os.name == 'nt' else 0
    start = time.perf_counter()
    with (folder / 'server.log').open('w', encoding='utf-8') as log:
        child = subprocess.Popen(command, cwd=ROOT, stdout=log, stderr=log, creationflags=flags)
        try:
            for _ in range(120):
                if child.poll() is not None:
                    raise RuntimeError('Local server exited; inspect server.log')
                try:
                    request(port, 'health', timeout=2); break
                except Exception:
                    time.sleep(1)
            else:
                raise TimeoutError('Model load timeout')
            print(size, 'loaded', round(time.perf_counter()-start, 2), 'seconds', flush=True)
            for offset in range(0, len(items), batch_size):
                batch = items[offset:offset + batch_size]
                ids = [x['id'] for x in batch]
                inputs = [{k: x[k] for k in ['id', 'name', 'merchant', 'quantity']} for x in batch]
                payload = {'model': 'local', 'messages': [
                    {'role': 'system', 'content': prompt},
                    {'role': 'user', 'content': json.dumps(inputs, ensure_ascii=False)}],
                    'temperature': 0, 'seed': 42, 'max_tokens': 1000,
                    'response_format': {'type': 'json_schema', 'json_schema': {'name': 'items', 'strict': True, 'schema': wire_schema(ids)}}}
                tick = time.perf_counter()
                try:
                    response = request(port, 'v1/chat/completions', payload)
                    (folder / f'batch-{offset:03}.json').write_text(json.dumps(response, ensure_ascii=False, indent=2), encoding='utf-8')
                    choice = response['choices'][0]
                    if choice['finish_reason'] != 'stop':
                        raise ValueError('Truncated model output: ' + str(choice['finish_reason']))
                    decoded = json.loads(choice['message']['content'])
                    normalized = [decode_sparse(x) for x in decoded['items']]
                    if len(normalized) != len(ids) or {x['id'] for x in normalized} != set(ids):
                        raise ValueError('Output IDs differ from input')
                    predictions.extend(normalized)
                    timings.append({'offset': offset, 'seconds': round(time.perf_counter()-tick, 3), 'usage': response.get('usage'), 'timings': response.get('timings')})
                    print(size, f'{min(offset+batch_size,len(items))}/{len(items)}', round(time.perf_counter()-tick, 1), 'seconds', flush=True)
                except Exception as error:
                    failures.append({'ids': ids, 'error': str(error), 'seconds': round(time.perf_counter()-tick, 3)})
                    print(size, 'batch failed', offset, type(error).__name__, str(error)[:100], flush=True)
                checkpoint = {'schema_version': dataset['schema_version'], 'source_sha256': dataset['source_sha256'],
                              'model': size, 'prompt_sha256': hashlib.sha256(prompt.encode()).hexdigest(),
                              'batch_size': batch_size, 'requested_items': len(items), 'requested_ids': [x['id'] for x in items], 'predictions': predictions,
                              'failures': failures, 'timings': timings, 'elapsed_seconds': round(time.perf_counter()-start, 3)}
                (folder / 'predictions.json').write_text(json.dumps(checkpoint, ensure_ascii=False, indent=2), encoding='utf-8')
            if not failures and len(items) == len(dataset['items']):
                (folder / 'annotated-rows.json').write_text(json.dumps(attach(dataset, predictions), ensure_ascii=False, indent=2), encoding='utf-8')
        finally:
            child.terminate()
            try:
                child.wait(timeout=15)
            except subprocess.TimeoutExpired:
                child.kill(); child.wait()
    return not failures


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--models', nargs='+', choices=['0.5b', '1.5b', '3b'], default=['0.5b', '1.5b', '3b'])
    parser.add_argument('--batch-size', type=int, default=3)
    parser.add_argument('--limit', type=int, default=0)
    args = parser.parse_args()
    if args.batch_size < 1 or args.limit < 0:
        parser.error('invalid batch size / limit')
    dataset = json.loads((ROOT / 'private' / 'prepared.json').read_text(encoding='utf-8'))
    success = True
    for size in args.models:
        success = run(size, dataset, args.batch_size, args.limit) and success
    raise SystemExit(0 if success else 1)


if __name__ == '__main__':
    main()
