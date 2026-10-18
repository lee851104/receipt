"""Generate synthetic-only reference probabilities using the original experiment loader."""
import argparse
import contextlib
import io
import json
from pathlib import Path
import sys
from scripts.verify_category_service import PROBES, MODEL_SHA256, probe_fingerprint

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model-dir",type=Path,required=True)
    parser.add_argument("--source-code",type=Path,required=True)
    parser.add_argument("--out",type=Path,required=True)
    args=parser.parse_args()
    def guard(event,values):
        if event=="open" and isinstance(values[0],(str,bytes)):
            value=values[0].decode() if isinstance(values[0],bytes) else values[0]
            normalized=value.replace("\\","/").lower()
            if normalized.endswith(".jsonl") or "/data/private/" in normalized or "/rawdata/" in normalized:
                raise RuntimeError("private_data_forbidden")
    sys.addaudithook(guard)
    try:
        if args.out.exists():raise FileExistsError("output_exists")
        sys.path.insert(0,str(args.source_code.resolve()))
        with contextlib.redirect_stdout(io.StringIO()),contextlib.redirect_stderr(io.StringIO()):
            from bert_model import Classifier
            from common import fingerprint
            assert fingerprint(args.model_dir/"model.safetensors")==MODEL_SHA256
            rows=Classifier.load(args.model_dir).predict(PROBES)
        args.out.parent.mkdir(parents=True,exist_ok=True)
        with args.out.open("x",encoding="utf-8") as f:
            json.dump(dict(model_sha256=MODEL_SHA256,probe_sha256=probe_fingerprint(),
                           categories=[r["category"] for r in rows],probabilities=[r["probabilities"] for r in rows]),f)
        print(json.dumps({"synthetic_reference_count":len(rows),"original_test":"not_opened"}))
    except Exception:parser.exit(1,"Reference failed; no private details printed.\n")
if __name__=="__main__":main()
