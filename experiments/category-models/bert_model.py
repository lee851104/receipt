"""Local-only ten-class BERT inference and integrity-checked safetensors bundles."""
import json
import os
from pathlib import Path
os.environ['HF_HUB_OFFLINE']='1'
os.environ['TRANSFORMERS_OFFLINE']='1'
os.environ['HF_HUB_DISABLE_TELEMETRY']='1'
os.environ['TOKENIZERS_PARALLELISM']='false'
os.environ.setdefault('CUBLAS_WORKSPACE_CONFIG',':4096:8')

import torch
from transformers import AutoTokenizer, BertForSequenceClassification
from common import fingerprint
from prepare_data import CATEGORIES, normalize, write_json


def save_bundle(model,tokenizer,directory,metadata):
    directory=Path(directory)
    directory.mkdir(parents=True,exist_ok=True)
    model.save_pretrained(directory,safe_serialization=True)
    tokenizer.save_pretrained(directory)
    files={p.name:fingerprint(p) for p in directory.iterdir() if p.is_file() and p.name!='classifier-manifest.json'}
    write_json(directory/'classifier-manifest.json',dict(**metadata,format_version='bert-category-1',files=files))


def verified_manifest(directory):
    directory=Path(directory).resolve()
    metadata=json.loads((directory/'classifier-manifest.json').read_text(encoding='utf-8'))
    if metadata.get('format_version')!='bert-category-1' or metadata.get('categories')!=list(CATEGORIES):
        raise ValueError('invalid_classifier_manifest')
    files=metadata['files']
    if not {'config.json','model.safetensors','tokenizer_config.json'}<=set(files) or not {'tokenizer.json','vocab.txt'}&set(files):
        raise ValueError('missing_classifier_files')
    actual={p.name for p in directory.iterdir() if p.is_file() and p.name!='classifier-manifest.json'}
    if actual!=set(files):raise ValueError('unverified_classifier_files')
    for name,digest in files.items():
        path=(directory/name).resolve()
        if path.parent!=directory or fingerprint(path)!=digest:raise ValueError('classifier_hash_mismatch')
    if type(metadata['max_length']) is not int or not 2<=metadata['max_length']<=512:
        raise ValueError('invalid_max_length')
    return metadata


class Classifier:
    def __init__(self,model,tokenizer,max_length=32,batch_size=16,device='cpu'):
        if batch_size<1 or device not in ('cpu','cuda'):raise ValueError('invalid_inference_settings')
        self.model=model.to(device=device,dtype=torch.float32).eval()
        self.tokenizer=tokenizer
        self.max_length,self.batch_size,self.device=max_length,batch_size,device
        if model.config.num_labels!=10:raise ValueError('expected_ten_classes')

    @classmethod
    def load(cls,directory,device='cpu',threads=1):
        metadata=verified_manifest(directory)
        torch.set_num_threads(threads)
        tokenizer=AutoTokenizer.from_pretrained(directory,local_files_only=True,trust_remote_code=False)
        model=BertForSequenceClassification.from_pretrained(directory,local_files_only=True,trust_remote_code=False,use_safetensors=True,attn_implementation='eager')
        instance=cls(model,tokenizer,metadata['max_length'],device=device)
        instance.metadata=metadata
        return instance

    def predict(self,names):
        names=[normalize(name) for name in names]
        results=[]
        with torch.inference_mode():
            for start in range(0,len(names),self.batch_size):
                tokens=self.tokenizer(names[start:start+self.batch_size],padding=True,truncation=True,max_length=self.max_length,return_tensors='pt').to(self.device)
                probabilities=self.model(**tokens).logits.softmax(-1).cpu().tolist()
                for row in probabilities:
                    category=max(range(10),key=row.__getitem__)
                    results.append(dict(category=category,category_name=CATEGORIES[category],probabilities=row))
        return results
