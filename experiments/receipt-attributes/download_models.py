"""Download pinned public assets only. Never reads private data; all writes stay in this lab."""
import hashlib
import json
from pathlib import Path
import urllib.request
import zipfile

ROOT = Path(__file__).resolve().parent
MODELS = [
    ('0.5b', 'Qwen/Qwen2.5-0.5B-Instruct-GGUF', '9217f5db79a29953eb74d5343926648285ec7e67', '74a4da8c9fdbcd15bd1f6d01d621410d31c6fc00986f5eb687824e7b93d7a9db'),
    ('1.5b', 'Qwen/Qwen2.5-1.5B-Instruct-GGUF', '91cad51170dc346986eccefdc2dd33a9da36ead9', '6a1a2eb6d15622bf3c96857206351ba97e1af16c30d7a74ee38970e434e9407e'),
    ('3b', 'Qwen/Qwen2.5-3B-Instruct-GGUF', '7dabda4d13d513e3e842b20f0d435c732f172cbe', '626b4a6678b86442240e33df819e00132d3ba7dddfe1cdc4fbb18e0a9615c62d'),
]


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def download(url, path, expected):
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and digest(path) == expected:
        print('verified existing', path.name, flush=True)
        return
    partial = path.with_suffix(path.suffix + '.part')
    print('downloading', path.name, flush=True)
    with urllib.request.urlopen(url, timeout=120) as response, partial.open('wb') as output:
        total, next_log = 0, 256 * 1024 * 1024
        while block := response.read(4 * 1024 * 1024):
            output.write(block)
            total += len(block)
            if total >= next_log:
                print(path.name, round(total / 1e6), 'MB', flush=True)
                next_log += 256 * 1024 * 1024
    if digest(partial) != expected:
        raise ValueError('SHA256 mismatch: ' + path.name)
    partial.replace(path)
    print('verified', path.name, path.stat().st_size, flush=True)


def main():
    runtime_name = 'llama-b11557-bin-win-cpu-x64.zip'
    runtime_url = 'https://github.com/ggml-org/llama.cpp/releases/download/b11557/' + runtime_name
    runtime_sha = 'bcfca9c8198899d4268e4e6b586113905280dec372a82c7106ebe78bc0eacb5b'
    archive = ROOT / 'runtime' / runtime_name
    download(runtime_url, archive, runtime_sha)
    target = ROOT / 'runtime' / 'llama-b11557'
    target.mkdir(exist_ok=True)
    with zipfile.ZipFile(archive) as package:
        for member in package.infolist():
            if not (target / member.filename).resolve().is_relative_to(target.resolve()):
                raise ValueError('Unsafe archive path')
        package.extractall(target)
    manifest = {'runtime': {'url': runtime_url, 'sha256': runtime_sha}, 'models': []}
    for size, repo, revision, sha in MODELS:
        name = f'qwen2.5-{size}-instruct-q4_k_m.gguf'
        url = f'https://huggingface.co/{repo}/resolve/{revision}/{name}'
        download(url, ROOT / 'models' / name, sha)
        manifest['models'].append({'id': size, 'repo': repo, 'revision': revision,
                                   'file': name, 'sha256': sha, 'url': url})
        (ROOT / 'runtime' / 'download-manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')


if __name__ == '__main__':
    main()
