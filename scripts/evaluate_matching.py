"""Evaluate 300 fictional users with reviewed, recorded Qwen attributes, without a database or GPU.

Run from the repository root: python -m scripts.evaluate_matching
"""
import json
from pathlib import Path
from src.receipt.evaluation import summarize_matches
from src.receipt.personas import PERIOD, build_personas
from src.api import matching
from src.receipt.places import areas_of, load_regions
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
        rows = person["rows"]
        vectors[person["name"]] = build_vector(rows, list(PERIOD), context, attributes=cache)
        if vectors[person["name"]] != build_vector(rows, list(PERIOD), context, attributes=cache):
            raise AssertionError("Non-reproducible vector")
    model = similarity_model(context["traits"])
    threshold = context["traits"]["match"]
    regions = load_regions(ROOT)
    candidates = [{"user_id": index, "display_name": person["name"], "vector": vectors[person["name"]],
                   "areas": areas_of(person["rows"], context)} for index, person in enumerate(people, start=1)]
    matches = {}
    for mine in candidates:
        others = [other for other in candidates if other["user_id"] != mine["user_id"]]
        scored = matching.entries(mine["vector"], mine["areas"], others, model, regions)
        matches[mine["display_name"]] = {
            kind: [person["display_name"] for person in matching.pick(scored, kind, None, threshold)["people"]]
            for kind in ("similar", "opposite")}
    opposites = json.loads((ROOT / "configs/persona-opposites.json").read_text(encoding="utf-8"))["pairs"]
    summary = summarize_matches(people, matches, opposites)
    summary.update(source="synthetic", population=len(people), unique_items=len(cache), model_versions=sorted({r["model_version"] for r in records}),
                   cache_review={"reviewed_items": len(records), "corrected_items": sum(bool(r.get("corrections")) for r in records),
                                 "corrected_fields": sum(len(r.get("corrections", {})) for r in records),
                                 "human_confirmed_items": sum(r.get("human_confirmed", False) for r in records),
                                 "statuses": sorted({r["review_status"] for r in records})},
                   cache_revisions=sorted({r.get("cache_revision", "original") for r in records}),
                   baseline={"commit": "5c30459", "population": 300, "overall": {
                       "similar_users_with_matches": 300, "opposite_users_with_matches": 175,
                       "same_type_precision_at_5": 1.0, "same_type_mutual_user_hit_rate": 0.91,
                       "opposite_type_precision_at_5": 0.114,
                       "opposite_type_user_hit_rate": 38 / 300, "opposite_slots": 707}},
                   calculation_note="2026-10-19 相對 main 5c30459，只調整擴充名單中的 6 位連假旅人（06–11）：加入探索不同店家、自炊、甜飲與不同外食預算；原 40 人與其餘 254 人的消費紀錄不變。清單差異來自人物向量改變，107 筆屬性快取、類別規則、相反類型對照、配對門檻與 entries／pick 排序都不變。這批合成習慣是為補齊示範清單而設計，不能當成獨立的配對品質測試。",
                   scope="reviewed synthetic cache and recorded categories; shared API entries/pick; seed pipeline covered by synthetic integration tests; not live model accuracy",
                   comparable_profiles=sum(v is not None for v in vectors.values()))
    destination = ROOT / "docs/results"
    destination.mkdir(exist_ok=True, parents=True)
    (destination / "matching.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    lines = ["# 300 位假用戶配對驗證", "", "2026-10-19；純合成資料、既定類別 + 經助理逐筆修正的本機 Qwen 屬性快取，再用現有核心計算向量與配對。", "",
             f"屬性共 {len(records)} 筆，修正新版模型 {summary['cache_review']['corrected_items']} 筆／{summary['cache_review']['corrected_fields']} 欄；真人確認 {summary['cache_review']['human_confirmed_items']} 筆。這是修正後快取的配對測試，不代表原始 Qwen 準確率。逐筆對照見 [synthetic-cache-review.md](synthetic-cache-review.md)。", "",
             "這次驗證涵蓋核心公式與向量重算；seed 的解析、既定合成分類答案重播、快取、背景工作與 profile 重算另由合成資料整合測試驗證，並測試 demo 配對隔離；不代表真實分類模型或 Qwen 即時推論的準確率。", "",
             summary["calculation_note"], "",
             "相反類型在執行前固定於 `configs/persona-opposites.json`：省錢／咖啡、忙碌／家庭、手搖／健身、旅人／貓奴。這是待驗證的假設，不保證一定互補。", "",
             "門檻與名額直接交給後端 entries／pick，使用 configs/traits.json 的 match 設定：整數百分比 ≥ +30% 為相近、≤ −10% 為互補，各取前 5；同分依顯示名稱字元碼、再依 user_id 排序，本次不篩距離。P@5 分母固定是每人 5 格，名單不足仍算未命中；用戶命中率是至少命中一人。互相命中要求同類型兩人都把彼此列在相近前 5。", "",
             "| 類型 | 人數 | 同類 P@5 | 同類用戶命中 | 同類互相命中 | 相反 P@5 | 相反用戶命中 |", "|---|---:|---:|---:|---:|---:|---:|"]
    for label, stat in [("整體", summary["overall"]), *summary["by_type"].items()]:
        keys=("same_type_precision_at_5", "same_type_user_hit_rate", "same_type_mutual_user_hit_rate", "opposite_type_precision_at_5", "opposite_type_user_hit_rate")
        lines.append(f"| {label} | {stat['users']} | " + " | ".join(f"{stat[k]:.2%}" for k in keys) + " |")
    overall = summary["overall"]
    baseline = summary["baseline"]["overall"]
    lines += ["", "與 5c30459 比較（300 人、相同門檻；空清單數另由逐人登入 API 重現）：", "",
              "| 指標 | 修正前 | 本次 |", "|---|---:|---:|"]
    for title, key, rate in (
            ("相近清單有人", "similar_users_with_matches", False),
            ("互補清單有人", "opposite_users_with_matches", False),
            ("同類 P@5", "same_type_precision_at_5", True),
            ("同類互相命中", "same_type_mutual_user_hit_rate", True),
            ("預設相反類型 P@5", "opposite_type_precision_at_5", True),
            ("預設相反類型用戶命中", "opposite_type_user_hit_rate", True),
            ("互補清單總名額", "opposite_slots", False)):
        before, after = baseline[key], overall[key]
        lines.append(f"| {title} | {before:.2%} | {after:.2%} |" if rate else f"| {title} | {before} | {after} |")
    lines += ["", "「清單有人」只檢查是否有符合正式門檻的對象；「相反類型命中」還要求對象屬於事先指定的類型，兩者不同。新增旅人可能排在其他類型前面，因此清單涵蓋率提升不代表預設相反類型命中率提升。", "",
              "| 類型 | 人數 | 相近清單有人 | 互補清單有人 |", "|---|---:|---:|---:|"]
    for label, stat in [("整體", overall), *summary["by_type"].items()]:
        lines.append(f"| {label} | {stat['users']} | {stat['similar_users_with_matches']} | {stat['opposite_users_with_matches']} |")
    lines += ["", "原始分子、分母與模型版本見 `matching.json`。假資料仍帶有設計好的類型偏好，因此不能推論真人配對品質。", "", "重現：`python -m scripts.evaluate_matching`（不需要 GPU）。"]
    (destination / "matching.md").write_text("\n".join(lines)+"\n", encoding="utf-8")
    print(json.dumps(summary["overall"]))


if __name__ == "__main__":
    main()
