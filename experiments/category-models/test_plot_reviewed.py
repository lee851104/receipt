import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from plot_reviewed_comparison import render

@unittest.skipUnless(importlib.util.find_spec('matplotlib'), 'run in the separate plotting environment')
class PlotTests(unittest.TestCase):
    def test_aggregate_report_renders_all_png_and_pdf(self):
        score=dict(confusion_matrix=[[1 if i==j else 0 for j in range(10)] for i in range(10)],support=10,accuracy=1.0,macro_f1=1.0)
        subsets=('all','train_unseen','previously_unseen')
        report=dict(categories=[f'Category {i}' for i in range(10)],overlap_counts={s:10 for s in subsets},models={k:{s:score for s in subsets} for k in ('tfidf','embedding','bert')})
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp); path=root/'report.json'; path.write_text(json.dumps(report),encoding='utf-8')
            files=render(path,root,Path('C:/Windows/Fonts/msjh.ttc'))
            self.assertEqual(len(files),6)
            for name in files:
                blob=(root/name).read_bytes()
                self.assertTrue(blob.startswith(b'\x89PNG') if name.endswith('.png') else blob.startswith(b'%PDF'))
                self.assertGreater(len(blob),1000)

if __name__=='__main__':unittest.main()
