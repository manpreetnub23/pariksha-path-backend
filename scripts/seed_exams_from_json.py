import sys
import json
import asyncio
from pathlib import Path

# Add parent directory to sys.path for absolute imports
sys.path.append(str(Path(__file__).parent.parent))

from app.models.course import Course
from app.models.enums import ExamCategory
from app.db import init_db


async def seed_exams_from_json():
    """Seed the database with exam data from exams.json"""
    # Initialize DB
    await init_db()

    # Path to exams.json
    json_path = (
        Path(__file__).parent.parent.parent
        / "pariksha-path2.0"
        / "public"
        / "data"
        / "exams.json"
    )

    # Load JSON
    with open(json_path, "r") as f:
        exams_data = json.load(f)

    # Flatten the data into individual exams
    exams_to_insert = []
    for category, subcategories in exams_data.items():
        # Map category to enum, with fallback to GOVT_EXAMS for unmapped
        category_enum = None
        for enum_val in ExamCategory:
            if enum_val.value.lower() in category.lower():
                category_enum = enum_val
                break
        if not category_enum:
            # Fallback to GOVT_EXAMS for unmapped categories (e.g., SSC, State Government)
            category_enum = ExamCategory.GOVT_EXAMS
            print(f"Warning: No matching category for {category}, using GOVT_EXAMS as fallback")

        # Handle nested subcategories (recursive for deeper nesting)
        def extract_exams(subcats, current_subcat=""):
            for key, value in subcats.items():
                if isinstance(value, list):
                    # This is a list of exams
                    for exam in value:
                        exams_to_insert.append({
                            "title": exam,
                            "code": exam.lower().replace(" ", "_").replace("(", "").replace(")", "").replace("&", "and"),
                            "category": category_enum,
                            "sub_category": key if current_subcat else category,  # Use key as sub_category
                            "description": f"{exam} in {category}",
                            "price": 0.0,
                            "is_free": True,
                            "thumbnail_url": "",
                            "created_by": "system_seed",
                            "is_active": True,
                        })
                elif isinstance(value, dict):
                    # Deeper nesting, recurse
                    extract_exams(value, key)

        extract_exams(subcategories)

    # Insert into DB
    for exam_data in exams_to_insert:
        # Check if already exists
        existing = await Course.find_one({"code": exam_data["code"]})
        if not existing:
            course = Course(**exam_data)
            await course.insert()
            print(f"Inserted: {course.title}")
        else:
            print(f"Skipped (exists): {exam_data['title']}")

    print(f"Total exams processed: {len(exams_to_insert)}")


if __name__ == "__main__":
    asyncio.run(seed_exams_from_json())
