"""
Exports Google RSA copy pack as a CSV ready for Google Ads Editor import.
"""
import csv
import io
from ad_machine.schemas.copy_pack import CopyPack


def build_rsa_csv(
    copy_pack: CopyPack,
    campaign_name: str = "Ad Machine Campaign",
    ad_group_name: str = "Ad Machine Ad Group",
    final_url: str = "",
    path1: str = "",
    path2: str = "",
) -> str:
    buf = io.StringIO()
    writer = csv.writer(buf)

    writer.writerow([
        "Campaign", "Ad Group", "Ad type", "Status",
        "Headline 1", "Headline 2", "Headline 3", "Headline 4", "Headline 5",
        "Headline 6", "Headline 7", "Headline 8", "Headline 9", "Headline 10",
        "Headline 11", "Headline 12", "Headline 13", "Headline 14", "Headline 15",
        "Description 1", "Description 2", "Description 3", "Description 4",
        "Path 1", "Path 2", "Final URL",
    ])

    rsa_variations = copy_pack.variations.get("google_rsa", [])
    if not rsa_variations:
        return buf.getvalue()

    for rsa in rsa_variations:
        payload = rsa.payload
        headlines = [h["text"] for h in payload.get("headlines", [])]
        descriptions = [d["text"] for d in payload.get("descriptions", [])]
        _path1 = payload.get("path1", path1)
        _path2 = payload.get("path2", path2)

        padded_headlines = (headlines + [""] * 15)[:15]
        padded_descs = (descriptions + [""] * 4)[:4]

        row = [
            campaign_name, ad_group_name, "Responsive search ad", "Enabled",
            *padded_headlines,
            *padded_descs,
            _path1, _path2, final_url,
        ]
        writer.writerow(row)

    return buf.getvalue()
