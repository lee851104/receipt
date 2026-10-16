"""Offline BERT fine-tuning on train only; validation loss selects the checkpoint."""
import argparse
from collections import Counter
from contextlib import redirect_stdout,redirect_stderr
import gc
import io
import json
import math
from pathlib import Path
import random
import time

from bert_model import Classifier,save_bundle,verified_manifest
import numpy as np
import torch
from transformers import AutoTokenizer,BertForSequenceClassification
from common import environment,peak_rss_bytes
from embedding_features import local_manifest
from fixed_split_data import load_dataset,score
from fixed_split_train import verify_roundtrip,verify_predictions
from prepare_data import CATEGORIES,write_json,write_jsonl


class EarlyStopping:
    def __init__(self,patience=2,min_delta=1e-4):
        self.patience,self.min_delta=patience,min_delta
        self.best_loss=float('inf');self.best_epoch=0;self.stale=0
    def update(self,loss,epoch):
        if not math.isfinite(loss):raise ValueError('nonfinite_validation_loss')
        significant=loss<self.best_loss-self.min_delta
        self.stale=0 if significant else self.stale+1
        if loss<self.best_loss:
            self.best_loss,self.best_epoch=loss,epoch
            return True
        return False
    @property
    def should_stop(self):return self.stale>=self.patience


def batch_tokens(tokenizer,rows,device,max_length):
    tokens=tokenizer([r['name'] for r in rows],padding=True,truncation=True,max_length=max_length,return_tensors='pt').to(device)
    tokens['labels']=torch.tensor([r['category'] for r in rows],device=device)
    return tokens


def train_epoch(model,tokenizer,rows,optimizer,device,batch_size,max_length,generator):
    model.train();total=0.0
    order=torch.randperm(len(rows),generator=generator).tolist()
    for start in range(0,len(order),batch_size):
        batch=[rows[i] for i in order[start:start+batch_size]]
        optimizer.zero_grad(set_to_none=True)
        loss=model(**batch_tokens(tokenizer,batch,device,max_length)).loss
        if not torch.isfinite(loss):raise ValueError('nonfinite_training_loss')
        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(),1.0,error_if_nonfinite=True)
        optimizer.step()
        total+=float(loss.detach().cpu())*len(batch)
    return total/len(rows)


def validation_loss(model,tokenizer,rows,device,batch_size,max_length):
    model.eval();total=0.0
    with torch.inference_mode():
        for start in range(0,len(rows),batch_size):
            batch=rows[start:start+batch_size]
            loss=model(**batch_tokens(tokenizer,batch,device,max_length)).loss
            total+=float(loss.cpu())*len(batch)
    value=total/len(rows)
    if not math.isfinite(value):raise ValueError('nonfinite_validation_loss')
    return value


def run(dataset_dir,pretrained,output_dir,seed=42,device='cuda',epochs=10,batch_size=16,lr=2e-5,benchmark_count=1000,progress=None,warm_start=False,development_only=False):
    if (type(seed) is not int or not 0<=seed<2**32 or type(epochs) is not int or epochs<1
            or type(batch_size) is not int or batch_size<1 or not math.isfinite(lr) or lr<=0
            or device not in ('cpu','cuda') or type(benchmark_count) is not int or benchmark_count<1):
        raise ValueError('invalid_training_settings')
    dataset_dir,pretrained,output_dir=map(lambda p:Path(p).resolve(),(dataset_dir,pretrained,output_dir))
    if output_dir.exists():raise FileExistsError('output_exists')
    if output_dir.is_relative_to(dataset_dir) or output_dir.is_relative_to(pretrained):raise ValueError('unsafe_output')
    from bert_continuation import load as load_continuation
    if development_only and warm_start:raise ValueError('development_recipe_requires_public_encoder')
    if development_only:
        from bert_release_data import load as load_development
        dataset_loader=load_development
    else:
        dataset_loader=load_continuation if warm_start else load_dataset
    parts,manifest,identity=dataset_loader(dataset_dir)
    training,validation=parts['train'],parts['validation']
    if not training or len({r['category'] for r in training})<2 or not validation:raise ValueError('insufficient_train_or_validation')
    if development_only:
        config=json.loads((pretrained/'config.json').read_text(encoding='utf-8'))
        if ((pretrained/'classifier-manifest.json').exists() or
                any('SequenceClassification' in a for a in config.get('architectures',[]))):
            raise ValueError('finetuned_initialization_forbidden')
    pretrained_checker=verified_manifest if warm_start else local_manifest
    pretrained_manifest=pretrained_checker(pretrained)
    if warm_start:
        from common import fingerprint
        if (pretrained_manifest['dataset_sha256']!=manifest['parent_dataset_sha256'] or
                fingerprint(pretrained/'classifier-manifest.json')!=manifest['parent_classifier_manifest_sha256']):
            raise ValueError('warm_start_parent_mismatch')
    if device=='cuda' and not torch.cuda.is_available():raise ValueError('cuda_unavailable')
    random.seed(seed);np.random.seed(seed);torch.manual_seed(seed)
    torch.set_num_threads(1)
    torch.use_deterministic_algorithms(True)
    if device=='cuda':
        torch.cuda.manual_seed_all(seed)
        torch.backends.cudnn.benchmark=False
        torch.backends.cuda.matmul.allow_tf32=False
        torch.backends.cudnn.allow_tf32=False
        torch.cuda.reset_peak_memory_stats()
    max_length=pretrained_manifest['max_length'] if warm_start else 32
    settings=dict(seed=seed,device=device,epochs=epochs,batch_size=batch_size,lr=lr,weight_decay=.01,
                  max_length=max_length,patience=2,min_delta=1e-4,gradient_clip=1.0,dtype='float32',threads=1,
                  selection='minimum_validation_cross_entropy; min_delta_controls_patience_only',tuned=False,
                  data_policy='development_only' if development_only else 'fixed_split',
                  initialization='verified_classifier_warm_start' if warm_start else 'public_pretrained_encoder')
    started=time.perf_counter()
    tokenizer=AutoTokenizer.from_pretrained(pretrained,local_files_only=True,trust_remote_code=False)
    model=BertForSequenceClassification.from_pretrained(pretrained,num_labels=10,
        id2label={i:n for i,n in enumerate(CATEGORIES)},label2id={n:i for i,n in enumerate(CATEGORIES)},
        local_files_only=True,trust_remote_code=False,use_safetensors=True,attn_implementation='eager').to(device)
    load_seconds=time.perf_counter()-started
    optimizer=torch.optim.AdamW(model.parameters(),lr=lr,weight_decay=.01)
    generator=torch.Generator().manual_seed(seed)
    stop=EarlyStopping();history=[]
    names=[r['name'] for r in validation]
    probe=[r['name'] for r in training[:10]]
    output_dir.mkdir(parents=True,exist_ok=False)
    metadata=dict(categories=list(CATEGORIES),max_length=max_length,dataset_sha256=identity,seed=seed,pretrained=pretrained_manifest)
    started=time.perf_counter()
    if warm_start:
        initial_loss=validation_loss(model,tokenizer,validation,device,batch_size,max_length)
        stop.update(initial_loss,0)
        history.append(dict(epoch=0,training_loss=None,validation_loss=initial_loss,seconds=0.0))
        cpu_model=Classifier(model,tokenizer,max_length,device='cpu')
        saved_validation=cpu_model.predict(names);saved_probe=cpu_model.predict(probe)
        save_bundle(model,tokenizer,output_dir/'model',dict(**metadata,best_epoch=0))
        del cpu_model
        model.to(device)
        if progress:progress(dict(seed=seed,**history[-1],best_epoch=0))
    for epoch in range(1,epochs+1):
        fit_start=time.perf_counter()
        loss=train_epoch(model,tokenizer,training,optimizer,device,batch_size,max_length,generator)
        val_loss=validation_loss(model,tokenizer,validation,device,batch_size,max_length)
        row=dict(epoch=epoch,training_loss=loss,validation_loss=val_loss,seconds=time.perf_counter()-fit_start)
        history.append(row)
        if stop.update(val_loss,epoch):
            cpu_model=Classifier(model,tokenizer,max_length,device='cpu')
            saved_validation=cpu_model.predict(names)
            saved_probe=cpu_model.predict(probe)
            save_bundle(model,tokenizer,output_dir/'model',dict(**metadata,best_epoch=epoch))
            del cpu_model
            model.to(device)
        if progress:progress(dict(seed=seed,**row,best_epoch=stop.best_epoch))
        if stop.should_stop:break
    training_seconds=time.perf_counter()-started
    if dataset_loader(dataset_dir)[2]!=identity or pretrained_checker(pretrained)!=pretrained_manifest:
        raise ValueError('source_changed_during_training')
    gpu_peak=torch.cuda.max_memory_allocated() if device=='cuda' else 0
    del model,optimizer,tokenizer
    gc.collect()
    if device=='cuda':torch.cuda.empty_cache()
    started=time.perf_counter()
    predictor=Classifier.load(output_dir/'model',device='cpu')
    reload_seconds=time.perf_counter()-started
    predictions=predictor.predict(names)
    verify_predictions(predictions,len(validation))
    verify_roundtrip(saved_validation,predictions,len(validation))
    verify_roundtrip(saved_probe,predictor.predict(probe),len(probe))
    benchmark=[training[i%len(training)]['name'] for i in range(benchmark_count)]
    predictor.predict(benchmark[:10])
    started=time.perf_counter();predictor.predict(benchmark)
    inference_seconds=time.perf_counter()-started
    sources=dict(Counter(r['source'] for r in training))
    report=dict(experiment='C',model='bert',seed=seed,best_epoch=stop.best_epoch,best_validation_loss=stop.best_loss,
        settings=settings,history=history,pretrained=pretrained_manifest,
        dataset=dict(manifest_sha256=identity,files_sha256=manifest['files_sha256'],source_sha256=manifest['source_sha256'],summary=manifest['summary']),
        training_sources=sources,test_evaluation='not_run',reload_verified=True,reload_probe_items=len(probe),
        test_access='not_opened' if development_only else 'loaded_for_integrity_checks_only',
        validation=dict(model=score([r['category'] for r in validation],[r['category'] for r in predictions])),
        cost=dict(initial_load_seconds=load_seconds,training_seconds=training_seconds,reload_seconds=reload_seconds,
                  inference_seconds=inference_seconds,benchmark_count=benchmark_count,
                  model_bytes=sum(p.stat().st_size for p in (output_dir/'model').iterdir() if p.is_file()),
                  pretrained_download_bytes=sum((pretrained/n).stat().st_size for n in pretrained_manifest['files']),
                  peak_process_rss_bytes=peak_rss_bytes(),peak_gpu_allocated_bytes=gpu_peak),
        environment=dict(**environment(),training_device=device,torch=torch.__version__,cuda=torch.version.cuda,
                         gpu=torch.cuda.get_device_name() if device=='cuda' else None),
        limitations=['Development data previously evaluated or reviewed with model suggestions; not independent blind evidence.',
                     'Synthetic replay is confined to train; see summary for actual validation support.',
                     'Labels and semantic variant groups require broader human review.',
                     'Fewer than five real items per class excludes class F1 and macro F1.',
                     'CPU benchmark cycles training names; RSS includes earlier training in this process.'])
    if dataset_loader(dataset_dir)[2]!=identity:raise ValueError('dataset_changed_during_training')
    write_jsonl(output_dir/'validation-predictions.jsonl',[
        dict(id=r['id'],name=r['name'],actual=r['category'],predicted=p['category'],probabilities=p['probabilities']) for r,p in zip(validation,predictions)])
    write_json(output_dir/'report.json',report)
    return report


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dataset',required=True,type=Path)
    parser.add_argument('--pretrained',required=True,type=Path)
    parser.add_argument('--out',required=True,type=Path)
    parser.add_argument('--seed',type=int,default=42)
    parser.add_argument('--device',choices=('cpu','cuda'),default='cuda')
    parser.add_argument('--warm-start',action='store_true')
    parser.add_argument('--development-only',action='store_true')
    parser.add_argument('--lr',type=float,default=2e-5)
    args=parser.parse_args()
    stream=__import__('sys').stdout
    try:
        with redirect_stdout(io.StringIO()),redirect_stderr(io.StringIO()):
            report=run(args.dataset,args.pretrained,args.out,seed=args.seed,device=args.device,lr=args.lr,warm_start=args.warm_start,development_only=args.development_only,
                       progress=lambda row:print(json.dumps(row),file=stream,flush=True))
        print(json.dumps(dict(status='complete',seed=report['seed'],best_epoch=report['best_epoch'],validation=report['validation'],cost=report['cost'])))
    except Exception:
        parser.exit(1,'BERT training failed; check local inputs, model integrity, device and a new output directory.\n')

if __name__=='__main__':main()
