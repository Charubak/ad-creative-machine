from ad_machine.schemas.brief import CreativeBrief, ExtraPlatform


def recommend_extra_platforms(brief: CreativeBrief) -> list[ExtraPlatform]:
    return [p for p in brief.recommended_extra_platforms if p.recommend]


def format_recommendation_summary(brief: CreativeBrief) -> str:
    recs = recommend_extra_platforms(brief)
    if not recs:
        return "No extra platform recommendations for this project."

    lines = []
    for r in recs:
        lines.append(
            f"{r.platform.upper()} ({r.suggested_budget_split_pct}% budget split): {r.rationale}"
        )
    return "\n".join(lines)
