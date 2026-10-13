"""Pinned data-only GGUF download for the follow-up benchmark."""
import json
from download_models import ROOT, download

ASSET = {
    'id': 'qwen3-4b',
    'repo': 'bartowski/Qwen_Qwen3-4B-Instruct-2507-GGUF',
    'revision': 'ae44f08e1392f39c0e474af10c3ff8355c8b6688',
    'file': 'Qwen_Qwen3-4B-Instruct-2507-Q4_K_M.gguf',
    'sha256': '2fde00ce69dd4899c70d020845e2638353015bba0fdf161b3eb965f2bca4464e',
    'base_model': 'Qwen/Qwen3-4B-Instruct-2507',
    'quantizer': 'bartowski',
}

if __name__ == '__main__':
    url = f"https://huggingface.co/{ASSET['repo']}/resolve/{ASSET['revision']}/{ASSET['file']}"
    download(url, ROOT / 'models' / ASSET['file'], ASSET['sha256'])
    (ROOT / 'runtime/extra-manifest.json').write_text(json.dumps(ASSET, indent=2), encoding='utf-8')
