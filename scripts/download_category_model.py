"""Download the pinned private BERT bundle. Credentials are never CLI arguments."""
import argparse
import json
from pathlib import Path
from src.ml.category_remote import download_space_model

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo",required=True)
    parser.add_argument("--revision",required=True)
    parser.add_argument("--sha256",required=True)
    parser.add_argument("--destination",required=True,type=Path)
    args=parser.parse_args()
    try:
        status=download_space_model(repo_id=args.repo,revision=args.revision,
                                    destination=args.destination,expected_sha256=args.sha256)
        print(json.dumps({"status":status,"model_sha256":args.sha256}))
    except Exception:
        parser.exit(1,"Protected model download failed; check local authentication and pinned source.\n")
if __name__=="__main__": main()
