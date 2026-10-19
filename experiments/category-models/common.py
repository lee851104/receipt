"""Shared folds, scoring and reproducibility helpers for category experiments."""
from collections import Counter, defaultdict
import ctypes
import hashlib
import json
import os
import platform

import numpy as np
from sklearn.metrics import (accuracy_score, confusion_matrix,
                             precision_recall_fscore_support)
from sklearn.model_selection import StratifiedKFold

from prepare_data import group_key


def make_folds(items, n_splits=3, seed=42):
    if n_splits < 2:
        raise ValueError("At least two folds are required")
    groups, labels = defaultdict(list), {}
    for index, item in enumerate(items):
        key = group_key(item.get("group", item["name"]))
        groups[key].append(index)
        if key in labels and labels[key] != item["category"]:
            raise ValueError("Conflicting labels in a variant group")
        labels[key] = item["category"]
    counts = Counter(labels.values())
    eligible = {label for label, count in counts.items() if count >= n_splits}
    if len(eligible) < 2:
        return []
    keys = sorted(key for key in groups if labels[key] in eligible)
    splitter = StratifiedKFold(n_splits=n_splits, shuffle=True, random_state=seed)
    folds = []
    for _, validation in splitter.split(keys, [labels[key] for key in keys]):
        held = {index for j in validation for index in groups[keys[j]]}
        folds.append(dict(train=[i for i in range(len(items)) if i not in held],
                          validation=sorted(held)))
    return folds


def metrics(truth, predicted):
    if not truth:
        return None
    precision, recall, f1, support = precision_recall_fscore_support(
        truth, predicted, labels=list(range(10)), zero_division=0)
    evaluated = [i for i in range(10) if support[i]]
    return dict(
        support=len(truth), accuracy=float(accuracy_score(truth, predicted)),
        evaluated_categories=evaluated,
        macro_f1=float(np.mean(f1[evaluated])),
        ten_class_macro_f1=float(np.mean(f1)) if len(evaluated) == 10 else None,
        per_class={str(i): dict(support=int(support[i]),
                               precision=float(precision[i]) if support[i] else None,
                               recall=float(recall[i]) if support[i] else None,
                               f1=float(f1[i]) if support[i] else None)
                   for i in range(10)},
        confusion_matrix=confusion_matrix(truth, predicted, labels=list(range(10))).tolist())


def fingerprint(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def data_digest(items):
    return hashlib.sha256(json.dumps(items, ensure_ascii=False, sort_keys=True)
                          .encode("utf-8")).hexdigest()


def environment():
    import joblib
    import scipy
    import sklearn
    import threadpoolctl
    return dict(python=platform.python_version(), os=platform.platform(),
                cpu=platform.processor() or os.environ.get("PROCESSOR_IDENTIFIER"),
                logical_cpus=os.cpu_count(), numpy=np.__version__,
                scipy=scipy.__version__, sklearn=sklearn.__version__,
                joblib=joblib.__version__, threadpoolctl=threadpoolctl.__version__,
                compute_device="CPU", compute_threads=1)


def peak_rss_bytes():
    """OS process high-water mark, including native allocations, or unavailable."""
    if os.name == "nt":
        from ctypes import wintypes

        class Counters(ctypes.Structure):
            _fields_ = [("cb", wintypes.DWORD), ("PageFaultCount", wintypes.DWORD)] + [
                (name, ctypes.c_size_t) for name in (
                    "PeakWorkingSetSize", "WorkingSetSize", "QuotaPeakPagedPoolUsage",
                    "QuotaPagedPoolUsage", "QuotaPeakNonPagedPoolUsage",
                    "QuotaNonPagedPoolUsage", "PagefileUsage", "PeakPagefileUsage")]

        get_process = ctypes.windll.kernel32.GetCurrentProcess
        get_process.restype = wintypes.HANDLE
        info = Counters()
        info.cb = ctypes.sizeof(info)
        get_info = ctypes.windll.psapi.GetProcessMemoryInfo
        get_info.argtypes = [wintypes.HANDLE, ctypes.POINTER(Counters), wintypes.DWORD]
        if get_info(get_process(), ctypes.byref(info), info.cb):
            return int(info.PeakWorkingSetSize)
        return None
    try:
        import resource
        peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        return int(peak if platform.system() == "Darwin" else peak * 1024)
    except (ImportError, OSError):
        return None
