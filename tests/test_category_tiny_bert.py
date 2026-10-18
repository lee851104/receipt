"""Optional real ML smoke test: tiny random model and invented tokenizer, no network."""
import json
import shutil
from pathlib import Path
import tempfile
import unittest
from unittest import mock
from concurrent.futures import ThreadPoolExecutor
try:
    import torch
    from transformers import BertConfig, BertForSequenceClassification, BertTokenizerFast
    from safetensors.torch import load_file, save_file
    HAS_ML = True
except ImportError:
    HAS_ML = False
from src.ml import category
from tests.model_contract import check_classify

@unittest.skipUnless(HAS_ML, "optional CPU ML dependencies are not installed")
class TinyBertTests(unittest.TestCase):
    def test_real_load_concurrency_truncation_and_missing_head(self):
        old_threads=torch.get_num_threads()
        self.addCleanup(torch.set_num_threads,old_threads)
        with tempfile.TemporaryDirectory() as folder, mock.patch("socket.socket.connect",side_effect=AssertionError("network forbidden")):
            path=Path(folder)
            (path/"vocab.txt").write_text("[PAD]\n[UNK]\n[CLS]\n[SEP]\n[MASK]\n示\n範\n品\n",encoding="utf-8")
            tokenizer=BertTokenizerFast(vocab_file=str(path/"vocab.txt"))
            tokenizer.save_pretrained(path)
            with torch.random.fork_rng(devices=[]):
                torch.manual_seed(42)
                model=BertForSequenceClassification(BertConfig(vocab_size=8,hidden_size=16,
                    num_hidden_layers=1,num_attention_heads=2,intermediate_size=32,max_position_embeddings=32,
                    num_labels=10,id2label=dict(enumerate(category.CATEGORIES)),
                    label2id={n:i for i,n in enumerate(category.CATEGORIES)}))
            model.save_pretrained(path,safe_serialization=True)
            def manifest(root=path):
                files={p.name:category.digest(p) for p in root.iterdir() if p.name!="classifier-manifest.json"}
                (root/"classifier-manifest.json").write_text(json.dumps(dict(format_version="bert-category-1",
                    categories=list(category.CATEGORIES),max_length=32,files=files)),encoding="utf-8")
            manifest()
            classify=category.load(path,batch_size=2)
            check_classify(self,classify,["示範品","示範"*100])
            expected=classify(["示範品","示範"*100])
            with ThreadPoolExecutor(max_workers=4) as pool:
                self.assertTrue(all(rows==expected for rows in pool.map(classify,[["示範品","示範"*100]]*8)))
            weights=load_file(path/"model.safetensors")
            weights.pop("classifier.bias")
            with tempfile.TemporaryDirectory() as broken_folder:
                broken=Path(broken_folder)
                for source in path.iterdir(): shutil.copyfile(source,broken/source.name)
                save_file(weights,broken/"model.safetensors",metadata={"format":"pt"})
                manifest(broken)
                with self.assertRaisesRegex(RuntimeError,"category_model_unavailable"):
                    category.load(broken)
