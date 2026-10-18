"""Re-run the frozen synthetic attribute benchmark on the two pinned GPU candidates."""
import argparse,hashlib,json,os,socket,subprocess,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument("--runtime",type=Path,required=True)
parser.add_argument("--models-dir",type=Path,default=ROOT/"models")
parser.add_argument("--output",type=Path,default=ROOT/"data/role3")
args=parser.parse_args()
args.output.mkdir(parents=True,exist_ok=True)
sys.path.insert(0,str(ROOT/"experiments/receipt-attributes"))
from run_followup import synthetic
from run_models import request,wire_schema
from lab_core import decode_sparse
from bulk_rule import apply_bulk_rule
from sugar_guard import apply_sugar_guard
from metrics import score
os.chdir(ROOT)
data=synthetic(); prompt=(ROOT/"experiments/receipt-attributes/prompt-named-v2.txt").read_text(encoding="utf-8")
assets=json.loads((ROOT/"configs/attribute-models.json").read_text())["candidates"]
exe=str(args.runtime.resolve())
summary=[]
for asset in assets:
    model_path=args.models_dir/asset["file"]
    with model_path.open("rb") as stream:
        if hashlib.file_digest(stream,"sha256").hexdigest()!=asset["sha256"]:
            raise ValueError("Model SHA256 mismatch")
    free=int(subprocess.check_output(["nvidia-smi","--query-gpu=memory.free","--format=csv,noheader,nounits"],text=True).strip())
    if free < 6500: raise RuntimeError("GPU memory in use; do not interfere")
    with socket.socket() as sock: sock.bind(("127.0.0.1",8080))
    folder=args.output/asset["id"]; folder.mkdir(exist_ok=True)
    raw=[]; failed=[]; start=time.perf_counter()
    with (folder/"server.log").open("w") as log:
        child=subprocess.Popen([exe,"-m",str(args.models_dir/asset["file"]),"--host","127.0.0.1","--port","8080","-ngl","99","-c","4096","-np","1","-t","2"],stdout=log,stderr=log,creationflags=subprocess.CREATE_NO_WINDOW)
        try:
            for _ in range(90):
                if child.poll() is not None: raise RuntimeError("server exited")
                try: request(8080,"health",timeout=2); break
                except OSError: time.sleep(1)
            for offset in range(0,len(data["items"]),3):
                batch=data["items"][offset:offset+3]; ids=[x["id"] for x in batch]
                inputs=[{k:x[k] for k in ("id","name","merchant","quantity")} for x in batch]
                payload={"model":"local","messages":[{"role":"system","content":prompt},{"role":"user","content":json.dumps(inputs,ensure_ascii=False)}],"temperature":0,"seed":42,"max_tokens":1000,"chat_template_kwargs":{"enable_thinking":False},"response_format":{"type":"json_schema","json_schema":{"name":"items","strict":True,"schema":wire_schema(ids)}}}
                response=request(8080,"v1/chat/completions",payload,timeout=120)
                (folder/f"batch-{offset:03}.json").write_text(json.dumps({"inputs":inputs,"response":response},ensure_ascii=False,indent=2),encoding="utf-8")
                try:
                    choice=response["choices"][0]
                    if choice["finish_reason"]!="stop": raise ValueError("truncated")
                    values=[decode_sparse(x) for x in json.loads(choice["message"]["content"])["items"]]
                    if len(values)!=len(ids) or {x["id"] for x in values}!=set(ids): raise ValueError("IDs")
                    raw.extend(values)
                except (ValueError,KeyError,TypeError) as error: failed.append({"offset":offset,"error":str(error)})
                print(asset["id"],offset+len(batch),"/",len(data["items"]),flush=True)
        finally:
            child.terminate()
            try: child.wait(timeout=15)
            except subprocess.TimeoutExpired: child.kill(); child.wait()
    guarded=apply_sugar_guard(data["items"],apply_bulk_rule(data["items"],raw)["predictions"])["predictions"]
    metrics={"model":asset,"seconds":time.perf_counter()-start,"failures":failed,"raw":score(data["reference"],raw),"guarded":score(data["reference"],guarded),"prompt_sha256":hashlib.sha256(prompt.encode()).hexdigest(),"dataset_sha256":data["source_sha256"]}
    (folder/"evaluation.json").write_text(json.dumps(metrics,ensure_ascii=False,indent=2),encoding="utf-8")
    summary.append(metrics)
(args.output/"comparison.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding="utf-8")
