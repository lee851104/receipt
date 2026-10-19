"""Plot aggregate-only reviewed evaluation metrics as standalone PNG and PDF."""
import argparse
import json
import os
from pathlib import Path


def render(report_path, output, font_path):
    output = Path(output)
    # Avoid altering the model runtime or global plotting configuration.
    os.environ.setdefault('MPLCONFIGDIR', str(output/'matplotlib-cache'))
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib import font_manager
    import numpy as np
    report = json.loads(Path(report_path).read_text(encoding='utf-8'))
    font_manager.fontManager.addfont(str(font_path))
    plt.rcParams.update({'font.family': font_manager.FontProperties(fname=str(font_path)).get_name(),
                         'axes.unicode_minus':False, 'pdf.fonttype':42, 'font.size':10})
    labels = [f'{i} {name}' for i,name in enumerate(report['categories'])]
    if len(labels) != 10:
        raise ValueError('expected_ten_categories')
    subsets = {'all':'全部已確認品名', 'train_unseen':'排除舊訓練同名／同群組',
               'previously_unseen':'排除舊訓練、驗證與測試已見品名'}
    bert_seed = next((entry.get('seed') for entry in report.get('provenance', {}).get('model_identities', []) if entry['kind']=='bert'), None)
    bert_label = f'BERT (seed {bert_seed})' if bert_seed is not None else 'BERT'
    outputs = []
    for subset, title in subsets.items():
        targets = [output/f'confusion-{subset}.{ext}' for ext in ('png','pdf')]
        if any(p.exists() for p in targets):
            raise FileExistsError('plot_already_exists')
        fig, axes = plt.subplots(1,3,figsize=(22,8.6))
        fig.patch.set_facecolor('#ffffff')
        for ax, kind, display in zip(axes, ('tfidf','embedding','bert'), ('TF-IDF + LR','Embedding + LR',bert_label)):
            result = report['models'][kind][subset]
            matrix = np.asarray(result['confusion_matrix'],dtype=int)
            if matrix.shape != (10,10) or np.any(matrix < 0) or int(matrix.sum()) != result['support']:
                raise ValueError('invalid_confusion_matrix')
            supports = matrix.sum(axis=1)
            ratios = np.divide(matrix, supports[:,None], out=np.zeros((10,10),dtype=float), where=supports[:,None] != 0)
            im = ax.imshow(ratios, cmap='Blues', vmin=0,vmax=1, interpolation='nearest')
            for i in range(10):
                for j in range(10):
                    ax.text(j,i,str(matrix[i,j]),ha='center',va='center',fontsize=10.5,
                            color='white' if ratios[i,j]>.53 else '#1b334c',fontweight='bold' if i==j else 'normal')
            acc = 'N/A' if result['accuracy'] is None else f"{100*result['accuracy']:.2f}%"
            f1 = 'N/A' if result['macro_f1'] is None else f"{100*result['macro_f1']:.2f}%"
            ax.set_title(f"{display}\nAccuracy {acc}  |  Macro-F1 {f1}",pad=16,fontsize=13,fontweight='bold')
            ax.set_xticks(range(10),labels,rotation=55,ha='right')
            ax.set_yticks(range(10),labels)
            ax.set_xlabel('模型預測 →',labelpad=12,fontsize=12)
            ax.set_ylabel('人工標準答案 →',fontsize=12)
            ax.set_xticks(np.arange(-.5,10,1),minor=True);ax.set_yticks(np.arange(-.5,10,1),minor=True)
            ax.grid(which='minor',color='white',linewidth=.8);ax.tick_params(which='minor',bottom=False,left=False)
            for spine in ax.spines.values():spine.set_visible(False)
        fig.subplots_adjust(left=.055,right=.945,bottom=.24,top=.77,wspace=.33)
        color_ax = fig.add_axes([.96,.285,.008,.43])
        colorbar = fig.colorbar(im,cax=color_ax)
        colorbar.set_ticks([0,.25,.5,.75,1],labels=['0%','25%','50%','75%','100%'])
        count = report['overlap_counts'][subset]
        fig.suptitle(f'三模型混淆矩陣｜{title}（n = {count}）',fontsize=21,fontweight='bold',y=.96,color='#173a53')
        fig.text(.5,.89,'格內數字＝品名筆數；色階＝該真實類別內的預測比例。對角線為正確分類。',ha='center',fontsize=12,color='#425a6b')
        fig.text(.055,.075,'僅納入人工確認的可辨識品項；運動／住宿等低樣本類別需審慎解讀。Macro-F1 平均本子集有樣本的類別。',fontsize=11,color='#425a6b')
        fig.text(.055,.035,'模型輔助標註後的比較，並非盲測或穩定正確率證明。未重新訓練；完整指標與資料重疊說明見 comparison.md。',fontsize=11,color='#425a6b')
        for target in targets:
            fig.savefig(target,dpi=160,facecolor='white')
            outputs.append(target.name)
        plt.close(fig)
    return outputs


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--report',type=Path,required=True)
    parser.add_argument('--out',type=Path,required=True)
    parser.add_argument('--font',type=Path,default=Path('C:/Windows/Fonts/msjh.ttc'))
    args=parser.parse_args()
    try:
        files=render(args.report,args.out,args.font)
        print(json.dumps(dict(aggregate_figures=files)))
    except Exception:
        parser.exit(1,'Aggregate plotting failed; inputs were not printed.\n')
