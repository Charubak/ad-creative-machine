"""
Thin slop-check layer. When running standalone it uses a regex-based scorer.
When the ai-content-machine packages are on sys.path it delegates to the
real humanizer for rewrites.
"""
import re

SLOP_WORDS = [
    "delve", "tapestry", "vibrant", "pivotal", "leverage", "synergy", "robust",
    "seamless", "groundbreaking", "transformative", "stakeholders", "cultivate",
    "showcase", "foster", "innovative", "cutting-edge", "unlock", "empower",
    "revolutionize", "game-changer", "paradigm", "ecosystem", "journey",
    "holistic", "actionable", "deep dive", "circle back", "move the needle",
]

EM_DASH_PATTERN = re.compile(r"\s?—\s?")


def score_slop(text: str) -> float:
    words = text.lower().split()
    if not words:
        return 10.0
    hits = sum(1 for w in SLOP_WORDS if w in text.lower())
    em_dash_hits = len(EM_DASH_PATTERN.findall(text))
    total_hits = hits + em_dash_hits
    # Score: 10 = clean, 1 = sloppy. Penalise 1 point per 20 words of slop density.
    density = total_hits / (len(words) / 20)
    return max(1.0, min(10.0, 10.0 - density))


def rewrite_for_voice(text: str) -> str:
    try:
        from agents.humanizer import check_and_rewrite  # ai-content-machine package
        import anthropic, os
        c = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
        result = check_and_rewrite(text, "", c, auto_rewrite=True)
        return result.get("rewritten", text)
    except ImportError:
        return _regex_clean(text)


def _regex_clean(text: str) -> str:
    cleaned = EM_DASH_PATTERN.sub(", ", text)
    for word in SLOP_WORDS:
        replacements = {
            "delve": "look", "leverage": "use", "unlock": "access",
            "robust": "strong", "seamless": "smooth", "innovative": "",
            "cutting-edge": "new", "revolutionize": "change",
        }
        if word in replacements and replacements[word]:
            cleaned = re.sub(rf"\b{word}\b", replacements[word], cleaned, flags=re.IGNORECASE)
    return cleaned
