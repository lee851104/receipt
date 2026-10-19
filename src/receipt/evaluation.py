"""Aggregate fictional matching results with explicit five-slot denominators."""


def summarize_matches(people, matches, opposites):
    kinds = {person["name"]: person["type"] for person in people}

    def summarize(names):
        same = opposite = similar_slots = opposite_slots = same_users = opposite_users = mutual_users = 0
        for name in names:
            lists = matches[name]
            hits = [other for other in lists["similar"] if kinds[other] == kinds[name]]
            other_hits = [other for other in lists["opposite"] if kinds[other] == opposites[kinds[name]]]
            same += len(hits)
            opposite += len(other_hits)
            similar_slots += len(lists["similar"])
            opposite_slots += len(lists["opposite"])
            same_users += bool(hits)
            opposite_users += bool(other_hits)
            mutual_users += any(name in matches[other]["similar"] for other in hits)
        count = len(names)
        covered = {kind: sum(bool(matches[name][kind]) for name in names) for kind in ("similar", "opposite")}
        return {"users": count,
                "similar_users_with_matches": covered["similar"],
                "opposite_users_with_matches": covered["opposite"],
                "similar_list_coverage": covered["similar"] / count if count else None,
                "opposite_list_coverage": covered["opposite"] / count if count else None,
                "same_type_hits": same, "similar_slots": similar_slots,
                "opposite_type_hits": opposite, "opposite_slots": opposite_slots,
                "same_type_precision_at_5": same / (count * 5) if count else None,
                "opposite_type_precision_at_5": opposite / (count * 5) if count else None,
                "same_type_user_hit_rate": same_users / count if count else None,
                "same_type_mutual_user_hit_rate": mutual_users / count if count else None,
                "opposite_type_user_hit_rate": opposite_users / count if count else None}

    return {"overall": summarize(list(kinds)),
            "by_type": {kind: summarize([name for name in kinds if kinds[name] == kind]) for kind in dict.fromkeys(kinds.values())}}
