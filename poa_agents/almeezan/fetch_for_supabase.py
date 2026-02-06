#!/usr/bin/env python3
"""
Fetch POA-related laws from Al Meezan and format for Supabase import.
Output matches the articles table schema with hierarchy_path, text_arabic, text_english, etc.
"""

import json
import re
import warnings
from datetime import date
from pathlib import Path

from almeezan import AlMeezanDocument

warnings.filterwarnings('ignore')

# Law mappings with metadata
POA_LAWS = [
    {
        "law_id": 9176,
        "name_en": "Notarization Law",
        "name_ar": "قانون التوثيق",
        "chapter_en": "Notarization",
        "chapter_ar": "التوثيق",
        "services": ["All POA Services"]
    },
    {
        "law_id": 2559,
        "name_en": "Civil Code",
        "name_ar": "القانون المدني",
        "chapter_en": "Civil Code",
        "chapter_ar": "القانون المدني",
        "services": ["General POA", "Special POA"]
    },
    {
        "law_id": 3993,
        "name_en": "Traffic Law",
        "name_ar": "قانون المرور",
        "chapter_en": "Traffic",
        "chapter_ar": "المرور",
        "services": ["Vehicle POA"]
    },
    {
        "law_id": 9564,
        "name_en": "Real Estate Registration Law",
        "name_ar": "قانون التسجيل العقاري",
        "chapter_en": "Real Estate Registration",
        "chapter_ar": "التسجيل العقاري",
        "services": ["Real Estate POA"]
    },
    {
        "law_id": 2492,
        "name_en": "Civil & Commercial Procedures Law",
        "name_ar": "قانون المرافعات المدنية والتجارية",
        "chapter_en": "Civil & Commercial Procedures",
        "chapter_ar": "المرافعات المدنية والتجارية",
        "services": ["Litigation POA"]
    },
    {
        "law_id": 2563,
        "name_en": "Legal Practice Law",
        "name_ar": "قانون المحاماة",
        "chapter_en": "Legal Practice",
        "chapter_ar": "المحاماة",
        "services": ["Litigation POA", "General POA", "Special POA"]
    },
    {
        "law_id": 6656,
        "name_en": "Commercial Companies Law",
        "name_ar": "قانون الشركات التجارية",
        "chapter_en": "Commercial Companies",
        "chapter_ar": "الشركات التجارية",
        "services": ["Company POA"]
    },
    {
        "law_id": 2572,
        "name_en": "Commercial Code",
        "name_ar": "قانون التجارة",
        "chapter_en": "Commercial Code",
        "chapter_ar": "التجارة",
        "services": ["Commercial Agency", "General POA", "Special POA"]
    },
]


def extract_article_number(article_key: str) -> int:
    """Extract article number from key like '1 المادة' or 'المادة 1'."""
    numbers = re.findall(r'\d+', article_key)
    if numbers:
        return int(numbers[0])
    return 0


def transform_to_supabase_format(doc: AlMeezanDocument, law_info: dict) -> list[dict]:
    """Transform AlMeezanDocument to list of Supabase-compatible article records."""
    today = date.today().isoformat()
    records = []

    for idx, (article_key, article_data) in enumerate(doc.articles.items()):
        article_num = extract_article_number(article_key)

        # Build hierarchy_path matching Supabase schema
        hierarchy_path = {
            "level": 1,
            "chapter": {
                "ar": law_info["chapter_ar"],
                "en": law_info["chapter_en"]
            },
            "section": {
                "ar": law_info["name_ar"],
                "en": law_info["name_en"]
            }
        }

        # Build citation for granular references
        citation = {
            "law_id": doc.law_id,
            "law_number": doc.law_number,
            "law_year": doc.law_year,
            "law_name_ar": law_info["name_ar"],
            "law_name_en": law_info["name_en"],
            "article_url": article_data.get("url", ""),
            "formatted_ar": f"المادة {article_num} من {law_info['name_ar']} رقم {doc.law_number} لسنة {doc.law_year}",
            "formatted_en": f"Article {article_num} of {law_info['name_en']} No. {doc.law_number} of {doc.law_year}"
        }

        record = {
            "idx": idx,
            "article_number": article_num,
            "hierarchy_path": json.dumps(hierarchy_path, ensure_ascii=False),
            "citation": json.dumps(citation, ensure_ascii=False),
            "text_arabic": article_data.get("content", ""),
            "text_english": "",  # Would need translation
            "effective_date": today,
            "is_active": doc.law_status == "قيد التطبيق",
            "updated": today,
            "added": today
        }
        records.append(record)

    return records


def fetch_single_law(law_info: dict, lang: str = "ar") -> list[dict]:
    """Fetch a single law and return Supabase-formatted records."""
    law_id = law_info["law_id"]
    print(f"\nFetching: {law_info['name_en']} (ID: {law_id})")

    doc = AlMeezanDocument()
    doc.extract_info(law_id=law_id, lang=lang, check_number_of_articles=False)

    records = transform_to_supabase_format(doc, law_info)
    print(f"  → {len(records)} articles extracted")

    return records


def fetch_all_laws(output_dir: Path, lang: str = "ar"):
    """Fetch all POA laws and save in Supabase-compatible format."""
    output_dir.mkdir(parents=True, exist_ok=True)

    all_records = []

    for law_info in POA_LAWS:
        try:
            records = fetch_single_law(law_info, lang)
            all_records.extend(records)

            # Also save individual law file
            law_file = output_dir / f"law_{law_info['law_id']}_supabase.json"
            with open(law_file, "w", encoding="utf-8") as f:
                json.dump(records, f, ensure_ascii=False, indent=2)
            print(f"  → Saved: {law_file}")

        except Exception as e:
            print(f"  ✗ Error: {e}")

    # Save combined file
    combined_file = output_dir / "all_poa_articles.json"
    with open(combined_file, "w", encoding="utf-8") as f:
        json.dump(all_records, f, ensure_ascii=False, indent=2)

    print(f"\n{'='*60}")
    print(f"TOTAL: {len(all_records)} articles saved to {combined_file}")

    return all_records


if __name__ == "__main__":
    script_dir = Path(__file__).parent
    output_dir = script_dir / "supabase_import"

    print("Fetching POA laws for Supabase import...")
    records = fetch_all_laws(output_dir)
