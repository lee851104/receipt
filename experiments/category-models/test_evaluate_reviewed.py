import unittest
from evaluate_reviewed import select_confirmed, align_saved, overlap_slices, summarize

def item(i, name, category=0, status='human_confirmed'):
    return dict(id=i, name=name, category=category, review_status=status, source='real')

def draft(i, name, a=0, c=1):
    p=[0.0]*10; p[c]=1.0
    return dict(id=i,name=name,tfidf_category=a,suggested_category=c,bert_probabilities=p)

class EvaluationTests(unittest.TestCase):
    def test_pending_and_unknown_do_not_become_gold(self):
        rows, counts=select_confirmed([item('a','虛構茶',1), item('b','虛構未知',None,'model_pending'),item('c','虛構其他',10)])
        self.assertEqual(len(rows),1)
        self.assertEqual(counts['excluded_unconfirmed_or_unknown'],2)

    def test_conflicting_gold_rejected(self):
        with self.assertRaises(ValueError):
            select_confirmed([item('a','虛構茶',0),item('b','虛構茶',1)])

    def test_saved_predictions_align_by_id_and_name_not_row_order(self):
        rows,_=select_confirmed([item('b','虛構糕',2),item('a','虛構茶',1)])
        a,c=align_saved(rows,[draft('b','虛構糕',3,4),draft('a','虛構茶',0,1)])
        self.assertEqual(a,[0,3]); self.assertEqual(c,[1,4])
        with self.assertRaises(ValueError):
            align_saved(rows,[draft('b','虛構糕'),draft('a','名稱被改')])

    def test_reviewed_name_must_be_identical_model_input(self):
        rows,_=select_confirmed([item('a','Fictional A B')])
        with self.assertRaises(ValueError):
            align_saved(rows,[draft('a','fictional ab')])

    def test_overlap_distinguishes_training_from_previous_holdout(self):
        rows=[item('a','虛構Ａ茶'),item('b','虛構糕'),item('c','虛構新物')]
        slices=overlap_slices(rows,dict(train=[item('old','虛構A茶')],validation=[item('v','虛構糕')],test=[]))
        self.assertEqual(slices['train_seen'],[0])
        self.assertEqual(slices['train_unseen'],[1,2])
        self.assertEqual(slices['previously_unseen'],[2])

    def test_explicit_existing_group_survives_gold_preparation(self):
        supplied=item('new-id','虛構新寫法')
        supplied['group']='existing-group-id'
        rows,_=select_confirmed([supplied])
        old=item('old-id','虛構舊寫法');old['group']='existing-group-id'
        slices=overlap_slices(rows,dict(train=[old],validation=[],test=[]))
        self.assertEqual(slices['train_seen'],[0])
        self.assertEqual(slices['previously_unseen'],[])

    def test_alias_group_shares_overlap_with_a_known_name(self):
        a=item('a','虛構舊名稱'); a['group']='alias-link'
        b=item('b','虛構新名稱'); b['group']='alias-link'
        rows,_=select_confirmed([a,b])
        slices=overlap_slices(rows,dict(train=[item('old','虛構舊名稱')],validation=[],test=[]))
        self.assertEqual(slices['train_seen'],[0,1])

    def test_matrix_rows_are_truth_columns_are_predictions(self):
        result=summarize([0,0,1],[0,1,1])
        self.assertEqual(result['confusion_matrix'][0][:2],[1,1])
        self.assertEqual(result['confusion_matrix'][1][:2],[0,1])
        self.assertAlmostEqual(result['accuracy'],2/3)
        self.assertIsNone(result['macro_f1_support_ge5'])
        self.assertEqual(result['low_support_categories'],[0,1])

    def test_empty_subset_is_explicitly_not_scored(self):
        result=summarize([],[])
        self.assertEqual(result['support'],0)
        self.assertIsNone(result['accuracy'])
        self.assertEqual(sum(map(sum,result['confusion_matrix'])),0)

if __name__=='__main__':unittest.main()
