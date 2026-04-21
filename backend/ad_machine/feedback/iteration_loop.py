"""
Builds the iteration context for round N+1 from performance labels.
"""
from ad_machine.schemas.creative_pack import CreativePairing


def build_iteration_context(
    performance_rows: list[dict],
    pairings: list[CreativePairing],
    user_notes: str = "",
) -> str:
    winners = [r for r in performance_rows if r.get("user_label") == "winner"]
    losers = [r for r in performance_rows if r.get("user_label") == "loser"]

    pairing_map = {p.pairing_id: p for p in pairings}

    winner_angles: list[str] = []
    loser_angles: list[str] = []

    for row in winners:
        pairing = pairing_map.get(row.get("pairing_id", ""))
        if pairing and row.get("platform"):
            winner_angles.append(
                f"- Pairing {pairing.pairing_id[:8]} on {pairing.platform}: "
                f"{row.get('impressions', 0)} impressions, "
                f"{row.get('ctr', 0):.2%} CTR, "
                f"${row.get('spend', 0):.2f} spend"
            )

    for row in losers:
        pairing = pairing_map.get(row.get("pairing_id", ""))
        if pairing:
            loser_angles.append(
                f"- Pairing {pairing.pairing_id[:8]} on {pairing.platform}: "
                f"low performance, labelled loser"
            )

    lines = []

    if winner_angles:
        lines.append("PERFORMANCE CONTEXT FOR ROUND 2")
        lines.append("================================")
        lines.append("WINNING pairings from round 1 (double down on these angles):")
        lines.extend(winner_angles)

    if loser_angles:
        lines.append("\nLOSING pairings from round 1 (abandon these angles):")
        lines.extend(loser_angles)

    if user_notes:
        lines.append(f"\nADDITIONAL NOTES FROM OPERATOR:\n{user_notes}")

    lines.append(
        "\nINSTRUCTION: Use the winner signals to sharpen angles. "
        "Do NOT repeat any angle execution that appeared in losing pairings. "
        "iteration_notes in the brief must summarize what changed and why."
    )

    return "\n".join(lines)
