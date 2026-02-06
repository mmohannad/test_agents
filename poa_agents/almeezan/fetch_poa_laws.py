#!/usr/bin/env python3
"""
Fetch all POA-related laws from Al Meezan based on law_mappings.md
Output: JSON files for each law in the 'laws/' subdirectory
"""

import os
import re
from pathlib import Path

from almeezan import AlMeezanDocument

# Law IDs from law_mappings.md
POA_LAWS = [
    {"law_id": 9176, "name": "Notarization Law", "arabic": "قانون التوثيق"},
    {"law_id": 2559, "name": "Civil Code", "arabic": "القانون المدني"},
    {"law_id": 3993, "name": "Traffic Law", "arabic": "قانون المرور"},
    {"law_id": 9564, "name": "Real Estate Registration Law", "arabic": "قانون التسجيل العقاري"},
    {"law_id": 2492, "name": "Civil & Commercial Procedures Law", "arabic": "قانون المرافعات المدنية والتجارية"},
    {"law_id": 2563, "name": "Legal Practice Law", "arabic": "قانون المحاماة"},
    {"law_id": 6656, "name": "Commercial Companies Law", "arabic": "قانون الشركات التجارية"},
    {"law_id": 2572, "name": "Commercial Code", "arabic": "قانون التجارة"},
]

def fetch_all_laws(output_dir: Path, lang: str = "ar"):
    """Fetch all POA laws and save as JSON files."""
    output_dir.mkdir(parents=True, exist_ok=True)

    results = []
    for law_info in POA_LAWS:
        law_id = law_info["law_id"]
        law_name = law_info["name"]

        print(f"\n{'='*60}")
        print(f"Fetching: {law_name} (ID: {law_id})")
        print(f"{'='*60}")

        try:
            doc = AlMeezanDocument()
            doc.extract_info(law_id=law_id, lang=lang, check_number_of_articles=False)

            # Save to JSON
            filename = output_dir / f"law_{law_id}_{lang}.json"
            doc.to_json(str(filename))

            print(f"✓ Saved: {filename}")
            print(f"  - Articles: {len(doc.articles)}")
            results.append({
                "law_id": law_id,
                "name": law_name,
                "status": "success",
                "articles": len(doc.articles),
                "file": str(filename)
            })
        except Exception as e:
            print(f"✗ Error fetching {law_name}: {e}")
            results.append({
                "law_id": law_id,
                "name": law_name,
                "status": "error",
                "error": str(e)
            })

    return results


if __name__ == "__main__":
    script_dir = Path(__file__).parent
    output_dir = script_dir / "laws"

    print("Fetching POA-related laws from Al Meezan...")
    print(f"Output directory: {output_dir}")

    results = fetch_all_laws(output_dir, lang="ar")

    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    success = [r for r in results if r["status"] == "success"]
    failed = [r for r in results if r["status"] == "error"]

    print(f"Successfully fetched: {len(success)}/{len(POA_LAWS)}")
    for r in success:
        print(f"  ✓ {r['name']}: {r['articles']} articles -> {r['file']}")

    if failed:
        print(f"\nFailed: {len(failed)}")
        for r in failed:
            print(f"  ✗ {r['name']}: {r['error']}")
