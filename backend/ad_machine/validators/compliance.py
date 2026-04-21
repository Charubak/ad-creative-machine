import re
from ad_machine.schemas.copy_pack import CopyVariation, ComplianceFlag

BLOCK_PATTERNS = [
    (r"\bguaranteed returns?\b", "Forbidden: guaranteed returns claim"),
    (r"\brisk-free yield\b", "Forbidden: risk-free yield claim"),
    (r"\bguaranteed APR\b", "Forbidden: guaranteed APR claim"),
    (r"\bpassive income guaranteed\b", "Forbidden: passive income guarantee"),
    (r"\bno risk\b", "Forbidden: no risk claim"),
    (r"\b100% safe\b", "Forbidden: 100% safe claim"),
    (r"\bzero risk\b", "Forbidden: zero risk claim"),
    (r"\bnot financial advice\b.*\bbut\b", "Disclaimer followed by advice is not a valid disclaimer"),
]

WARN_PATTERNS = [
    (r"\bguaranteed\b", "Word 'guaranteed' often triggers ad platform review"),
    (r"\bearn\b.*\b(daily|weekly|monthly)\b", "Earnings + frequency may trigger compliance review"),
    (r"\b(double|triple|10x|100x)\b.*\b(your|returns?|gains?)\b", "Amplification claims trigger review"),
    (r"\bget rich\b", "Get rich language flagged"),
    (r"\bfinancial advice\b", "Financial advice language should be reviewed"),
    (r"\bhigh (returns?|yields?|apy)\b", "High returns claims may trigger review"),
]


def lint(variation: CopyVariation, project_constraints: list[str]) -> list[ComplianceFlag]:
    flags = []
    text_to_check = _extract_all_text(variation.payload)

    for pattern, rule in BLOCK_PATTERNS:
        for match in re.finditer(pattern, text_to_check, re.IGNORECASE):
            flags.append(ComplianceFlag(
                severity="block",
                rule=rule,
                matched_text=match.group(0),
                suggestion="Remove or rephrase to avoid guarantee language",
            ))

    for pattern, rule in WARN_PATTERNS:
        for match in re.finditer(pattern, text_to_check, re.IGNORECASE):
            flags.append(ComplianceFlag(
                severity="warn",
                rule=rule,
                matched_text=match.group(0),
            ))

    for constraint in project_constraints:
        quoted = re.findall(r'"([^"]+)"', constraint)
        for q in quoted:
            if q.lower() in text_to_check.lower():
                flags.append(ComplianceFlag(
                    severity="warn",
                    rule=f"Project-specific constraint: {constraint}",
                    matched_text=q,
                ))

    return flags


def lint_all(variations: list[CopyVariation], project_constraints: list[str]) -> list[ComplianceFlag]:
    return [f for v in variations for f in lint(v, project_constraints)]


def _extract_all_text(payload: dict) -> str:
    parts = []
    for key, val in payload.items():
        if isinstance(val, str):
            parts.append(val)
        elif isinstance(val, list):
            for item in val:
                if isinstance(item, str):
                    parts.append(item)
                elif isinstance(item, dict):
                    parts.append(_extract_all_text(item))
        elif isinstance(val, dict):
            parts.append(_extract_all_text(val))
    return " ".join(parts)
