from ad_machine.schemas.copy_pack import CopyVariation

LIMITS = {
    "x": {"primary_text": 280},
    "linkedin": {"intro_hook": 150, "body": 1200},
    "meta": {"primary_text": 125, "headline": 40, "description": 30},
    "google_rsa_headline": 30,
    "google_rsa_description": 90,
    "google_rsa_path": 15,
}

CONSTRAINTS_TEXT = {
    "x": "Single tweet max 280 chars including spaces. Threads: each tweet max 280 chars. Avoid more than 2 hashtags.",
    "linkedin": "Intro hook max 150 chars (above-the-fold). Body max 1200 chars. No more than 3 hashtags.",
    "meta": "Primary text max 125 visible chars before truncation. Headline max 40 chars. Description max 30 chars.",
    "google_rsa": "Headlines exactly 30 chars max each. Descriptions exactly 90 chars max each. Path1 and Path2 exactly 15 chars max each. Generate 12-15 headlines and 4 descriptions.",
}


def constraints_text(platform: str) -> str:
    return CONSTRAINTS_TEXT.get(platform, "")


def validate_and_trim(variation: CopyVariation, platform: str) -> CopyVariation:
    payload = dict(variation.payload)

    if platform == "x":
        text = payload.get("primary_text", "")
        if len(text) > 280:
            payload["primary_text"] = text[:277] + "..."
        payload["char_count"] = len(payload.get("primary_text", ""))
        variation.char_count = payload["char_count"]

    elif platform == "linkedin":
        if len(payload.get("intro_hook", "")) > 150:
            payload["intro_hook"] = payload["intro_hook"][:147] + "..."
        if len(payload.get("body", "")) > 1200:
            payload["body"] = payload["body"][:1197] + "..."

    elif platform == "meta":
        for field, limit in [("primary_text", 125), ("headline", 40), ("description", 30)]:
            if len(payload.get(field, "")) > limit:
                payload[field] = payload[field][:limit - 3] + "..."

    elif platform == "google_rsa":
        payload["headlines"] = [
            {**h, "text": h["text"][:30]} for h in payload.get("headlines", [])
        ]
        payload["descriptions"] = [
            {**d, "text": d["text"][:90]} for d in payload.get("descriptions", [])
        ]
        payload["path1"] = payload.get("path1", "")[:15]
        payload["path2"] = payload.get("path2", "")[:15]

    variation.payload = payload
    return variation
