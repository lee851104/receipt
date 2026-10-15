"""Evaluate 300 fictional users with recorded Qwen attributes, without a database or GPU.

Run from the repository root: python -m scripts.evaluate_matching
"""
import json
from pathlib import Path
from src.receipt.evaluation import summarize_matches
from src.receipt.personas import PERIOD, build_personas
from src.receipt.similarity import compare
from src.receipt.traits import build_vector, load_context, similarity_model

ROOT = Path(__file__).resolve().parents[1]


def main():
    context = load_context(ROOT)
    people = build_personas(context["calendar"], total=300)
    records = [json.loads(line) for line in (ROOT / "datasets/synthetic/attribute-cache.jsonl").read_text(encoding="utf-8").splitlines()]
    if any(record["source"] != "synthetic" for record in records):
        raise ValueError("Only synthetic cache allowed")
    cache = {record["name"]: record["attributes"] for record in records}
    vectors = {}
    for person in people:
        rows = [{**row, "attributes": cache[row["name"]]} for row in person["rows"]]
        vectors[person["name"]] = build_vector(rows, list(PERIOD), context)
        if vectors[person["name"]] != build_vector(rows, list(PERIOD), context):
            raise AssertionError("Non-reproducible vector")
    model = similarity_model(context["traits"])
    threshold = context["traits"]["match"]
    matches = {}
    for person in people:
        name = person["name"]
        candidates = []
        for index, other in enumerate(people):
            if other["name"] == name:
                continue
            result = compare(vectors[name], vectors[other["name"]], model)
            if result["comparable"]:
                candidates.append((index, other["name"], result["score"]))
        similar = sorted((c for c in candidates if c[2] >= threshold["min_score"]), key=lambda c: (-c[2], c[0]))[:5]
        opposite = sorted((c for c in candidates if c[2] <= -threshold["opposite_score"]), key=lambda c: (c[2], c[0]))[:5]
        matches[name] = {"similar": [c[1] for c in similar], "opposite": [c[1] for c in opposite]}
    opposites = json.loads((ROOT / "configs/persona-opposites.json").read_text(encoding="utf-8"))["pairs"]
    summary = summarize_matches(people, matches, opposites)
    summary.update(source="synthetic", population=300, unique_items=len(cache), model_versions=sorted({r["model_version"] for r in records}),
                   scope="core formula with known synthetic categories and Qwen cache; API/DB ingestion not verified",
                   comparable_profiles=sum(v is not None for v in vectors.values()))
    destination = ROOT / "docs/results"
    destination.mkdir(exist_ok=True, parents=True)
    (destination / "matching.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    lines = ["# 300 位假用戶配對驗證", "", "2026-10-15；純合成資料、既定類別 + 本機 Qwen 屬性快取，再用現有核心計算向量與配對。", "",
             "這次驗證涵蓋核心公式與向量重算；資料庫匯入、分類模型與 API 端到端尚待角色 1 的管線完成。", "",
             "相反類型在執行前固定於 `configs/persona-opposites.json`：省錢／咖啡、忙碌／家庭、手搖／健身、旅人／貓奴。這是待驗證的假設，不保證一定互補。", "",
             "相近採原始分數 ≥ 0.3、互補 ≤ −0.1，各取前 5；同分依生成順序（對應全新 seed 的 id），不篩距離。P@5 分母固定是每人 5 格，名單不足仍算未命中；用戶命中率是至少命中一人。互相命中要求同類型兩人都把彼此列在相近前 5。", "",
             "| 類型 | 人數 | 同類 P@5 | 同類用戶命中 | 同類互相命中 | 相反 P@5 | 相反用戶命中 |", "|---|---:|---:|---:|---:|---:|---:|"]
    for label, stat in [("整體", summary["overall"]), *summary["by_type"].items()]:
        keys=("same_type_precision_at_5", "same_type_user_hit_rate", "same_type_mutual_user_hit_rate", "opposite_type_precision_at_5", "opposite_type_user_hit_rate")
        lines.append(f"| {label} | {stat['users']} | " + " | ".join(f"{stat[k]:.2%}" for k in keys) + " |")
    lines += ["", "原始分子、分母與模型版本見 `matching.json`。假資料仍帶有設計好的類型偏好，因此不能推論真人配對品質。", "", "重現：`python -m scripts.evaluate_matching`（不需要 GPU）。"]
    (destination / "matching.md").write_text("\n".join(lines)+"\n", encoding="utf-8")
    print(json.dumps(summary["overall"]))


if __name__ == "__main__":
    main()
