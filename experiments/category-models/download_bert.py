"""Download pinned public BERT weights only, without opening any item data."""
import argparse
import hashlib
import json
from pathlib import Path
import urllib.request
from download_embedding import verified

REPO='google-bert/bert-base-chinese'
REVISION='8f23c25b06e129b6c986331a13d8d025a92cf0ea'
FILES=('config.json','model.safetensors','tokenizer.json','tokenizer_config.json','vocab.txt','README.md')

def download(directory):
    directory=Path(directory)
    with urllib.request.urlopen(f'https://huggingface.co/api/models/{REPO}/revision/{REVISION}?blobs=true',timeout=60) as r:
        metadata=json.load(r)
    if metadata['sha']!=REVISION:raise ValueError('revision_mismatch')
    available={r['rfilename']:r for r in metadata['siblings']}
    directory.mkdir(parents=True,exist_ok=True)
    hashes={}
    for name in FILES:
        target=directory/name
        if target.exists() and not verified(target,available[name]):
            raise ValueError('existing_model_file_mismatch')
        if not target.exists():
            temporary=directory/(name+'.part')
            with urllib.request.urlopen(f'https://huggingface.co/{REPO}/resolve/{REVISION}/{name}',timeout=120) as response,temporary.open('wb') as stream:
                for chunk in iter(lambda:response.read(1024*1024),b''):stream.write(chunk)
            if not verified(temporary,available[name]):raise ValueError('upstream_hash_mismatch')
            temporary.replace(target)
        hashes[name]=hashlib.sha256(target.read_bytes()).hexdigest()
        print(f'Verified {name}: {target.stat().st_size} bytes',flush=True)
    manifest=dict(repo=REPO,revision=REVISION,files=hashes)
    (directory/'encoder-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
    return manifest

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out',type=Path,required=True)
    download(parser.parse_args().out)
