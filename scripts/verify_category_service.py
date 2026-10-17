"""Synthetic-only service acceptance; never reads datasets or evaluates accuracy.

python -m scripts.verify_category_service --model-dir PATH --reference-json PATH --out NEW_JSON
"""
import argparse
from contextlib import contextmanager
import hashlib
import json
from pathlib import Path
import socket
import sys
import tempfile
import threading
import time
import unittest

PROBES = ["示範雞肉飯", "示範烏龍茶500ML", "示範巧克力餅", "示範冷凍青花菜",
          "示範乳清蛋白1KG", "示範理髮費", "示範95無鉛", "示範住宿費",
          "示範貓砂6L", "示範USB集線器", "  ＡＢＣ123  ", "示範長品名"*35]
MODEL_SHA256 = "16997425a9b36629469d60f506d52c2771bab1e6f3a3ea1465c2c0a316fa3e79"

def probe_fingerprint():
    return hashlib.sha256(json.dumps(PROBES,ensure_ascii=False).encode()).hexdigest()

@contextmanager
def serving(app):
    import uvicorn
    sock=socket.socket();sock.bind(("127.0.0.1",0));sock.listen(128)
    server=uvicorn.Server(uvicorn.Config(app,log_level="critical",access_log=False))
    thread=threading.Thread(target=server.run,kwargs={"sockets":[sock]},daemon=True)
    thread.start()
    try:
        deadline=time.monotonic()+20
        while not server.started:
            if not thread.is_alive() or time.monotonic()>deadline:raise RuntimeError("server_not_started")
            time.sleep(.02)
        yield "http://127.0.0.1:"+str(sock.getsockname()[1])
    finally:
        server.should_exit=True;thread.join(timeout=20);sock.close()
        if thread.is_alive():raise RuntimeError("server_did_not_stop")

def run(model_dir, reference_path):
    import httpx2
    from src.api.app import create_app
    from src.api.settings import Settings
    from src.ml.category import digest
    from tests.model_contract import check_classify
    from tests.api_support import invoice_csv, MAY, SECRET
    import torch
    import transformers

    model_dir=Path(model_dir).resolve()
    assert digest(model_dir/"model.safetensors")==MODEL_SHA256
    reference=json.loads(Path(reference_path).read_text(encoding="utf-8"))
    assert reference["probe_sha256"]==probe_fingerprint()
    assert reference["model_sha256"]==MODEL_SHA256
    result={"model_sha256":MODEL_SHA256,"synthetic_probes":len(PROBES),
            "torch":torch.__version__,"transformers":transformers.__version__,"cuda_build":torch.version.cuda}
    assert torch.version.cuda is None
    with tempfile.TemporaryDirectory(prefix="role2-service-") as tmp:
        settings=Settings(jwt_secret=SECRET,category_model="bert",category_model_dir=str(model_dir),
                          attributes_model="fake",database_url="sqlite:///"+(Path(tmp)/"app.db").as_posix())
        started=time.perf_counter();app=create_app(settings)
        result["startup_seconds"]=time.perf_counter()-started
        assert app.state.backends.category=="bert"
        classify=app.state.backends.classify
        check_classify(unittest.TestCase(),classify,PROBES)
        rows=classify(PROBES)
        assert len(rows)==len(reference["probabilities"])
        differences=[abs(a-b) for row,expected in zip(rows,reference["probabilities"]) for a,b in zip(row["probs"],expected)]
        assert max(differences)<1e-6
        assert [r["category"] for r in rows]==reference["categories"]
        result["source_probability_max_difference"]=max(differences)
        from concurrent.futures import ThreadPoolExecutor
        with ThreadPoolExecutor(max_workers=2) as pool:
            assert all(r==rows for r in pool.map(classify,[PROBES]*2))
        classify(PROBES[:2])
        started=time.perf_counter();classify([PROBES[i%10] for i in range(1000)])
        result["cpu_1000_seconds"]=time.perf_counter()-started
        started=time.perf_counter();classify(PROBES[:1])
        result["warm_single_seconds"]=time.perf_counter()-started
        result["contract_and_concurrency"]=True
        with serving(app) as url,httpx2.Client(base_url=url,trust_env=False,timeout=20) as client:
            assert client.get("/api/health").json()["models"]["category"]=="bert"
            assert client.post("/api/auth/register",json={"username":"role2verify","password":"test-password-123"}).status_code==201
            response=client.post("/api/auth/login",data={"username":"role2verify","password":"test-password-123"})
            headers={"Authorization":"Bearer "+response.json()["access_token"]}
            answer=client.post("/api/items/classify",json={"name":PROBES[0]},headers=headers)
            assert answer.status_code==200 and len(answer.json()["probs"])==10
            assert answer.json()["category"]["id"]==rows[0]["category"]
            response=client.post("/api/invoices",files={"file":("fictional.csv",invoice_csv(MAY),"text/csv")},headers=headers)
            assert response.status_code==202
            job_id=response.json()["job_id"]
            deadline=time.monotonic()+30
            while True:
                job=client.get(f"/api/jobs/{job_id}",headers=headers).json()
                if job["status"] in ("done","failed"):break
                if time.monotonic()>deadline:raise RuntimeError("job_timeout")
                time.sleep(.05)
            assert job["status"]=="done"
            profile=client.get("/api/me/profile",headers=headers)
            assert profile.status_code==200 and profile.json()["months"]
            result["http"]={"health":"bert","classify":200,"upload":202,"job":"done","profile":200}
        app.state.worker.queue.join();app.state.engine.dispose()
        # Independent new database, same production backend, deliberately absent model.
        missing=Settings(jwt_secret=SECRET,category_model="bert",category_model_dir=str(Path(tmp)/"absent"),
                         attributes_model="fake",database_url="sqlite:///"+(Path(tmp)/"missing.db").as_posix())
        bad=create_app(missing)
        with serving(bad) as url,httpx2.Client(base_url=url,trust_env=False,timeout=20) as client:
            assert client.get("/api/health").json()["models"]["category"]=="unavailable"
            client.post("/api/auth/register",json={"username":"absent","password":"test-password-123"})
            token=client.post("/api/auth/login",data={"username":"absent","password":"test-password-123"}).json()["access_token"]
            headers={"Authorization":"Bearer "+token}
            assert client.post("/api/items/classify",json={"name":PROBES[0]},headers=headers).status_code==503
            reply=client.post("/api/invoices",files={"file":("fictional.csv",invoice_csv(MAY),"text/csv")},headers=headers)
            assert reply.status_code==202
            deadline=time.monotonic()+10
            while True:
                job=client.get("/api/jobs/"+str(reply.json()["job_id"]),headers=headers).json()
                if job["status"] in ("done","failed"):break
                if time.monotonic()>deadline:raise RuntimeError("job_timeout")
                time.sleep(.05)
            assert job["status"]=="failed"
            result["missing_model"]={"health":"unavailable","classify":503,"job":"failed"}
        bad.state.worker.queue.join();bad.state.engine.dispose()
    return result

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model-dir",type=Path,required=True)
    parser.add_argument("--reference-json",type=Path,required=True)
    parser.add_argument("--out",type=Path,required=True)
    args=parser.parse_args()
    attempts={"private_data_open_attempts":0,"external_connect_attempts":0}
    def guard(event,values):
        if event=="open" and isinstance(values[0],(str,bytes)):
            value=values[0].decode() if isinstance(values[0],bytes) else values[0]
            normalized=value.replace("\\","/").lower()
            if normalized.endswith(".jsonl") or "/rawdata/" in normalized or "/data/private/" in normalized:
                attempts["private_data_open_attempts"]+=1
                raise RuntimeError("private_data_access_forbidden")
        if event=="socket.connect" and isinstance(values[1],tuple) and values[1][0] not in ("127.0.0.1","::1"):
            attempts["external_connect_attempts"]+=1
            raise RuntimeError("external_network_forbidden")
    sys.addaudithook(guard)
    try:
        if args.out.exists():raise FileExistsError("output_exists")
        result=run(args.model_dir,args.reference_json)
        assert not any(attempts.values())
        result.update(attempts)
        args.out.parent.mkdir(parents=True,exist_ok=True)
        with args.out.open("x",encoding="utf-8") as stream:json.dump(result,stream,indent=2)
        print(json.dumps(result))
    except Exception as error:
        # Frame location only, no potentially private exception text.
        import traceback
        print(json.dumps({"status":"failed","error_type":type(error).__name__,**attempts,
                          "frames":[{"file":Path(f.filename).name,"line":f.lineno} for f in traceback.extract_tb(error.__traceback__)]}))
        raise SystemExit(1)
if __name__=="__main__":main()
