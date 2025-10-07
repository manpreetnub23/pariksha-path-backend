import sys
import json
import asyncio
from pathlib import Path

# Add parent directory to sys.path for absolute imports
sys.path.append(str(Path(__file__).parent.parent))

from app.models.course import Course
from app.models.enums import ExamCategory
from app.db import init_db

async def compare_exams_with_db():
    """Compare exams from JSON with those in the database"""
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

    # Flatten the data into individual exam names (same as seeding)
    json_exams = []
    for category, subcategories in exams_data.items():
        category_enum = None
        for enum_val in ExamCategory:
            if enum_val.value.lower() in category.lower():
                category_enum = enum_val
                break
        if not category_enum:
            # Use same fallback as seeding script
            category_enum = ExamCategory.GOVT_EXAMS

        # Use the same extraction logic as seeding
        def extract_exams(subcats):
            for key, value in subcats.items():
                if isinstance(value, list):
                    # This is a list of exams
                    for exam in value:
                        json_exams.append(exam)
                elif isinstance(value, dict):
                    # Deeper nesting, recurse
                    extract_exams(value)

        extract_exams(subcategories)

    # Fetch all courses from DB
    db_courses = await Course.find().to_list()
    db_exam_titles = [course.title for course in db_courses]

    # Compare
    missing_in_db = []
    extra_in_db = []
    extra_in_json = []

    for exam in json_exams:
        if exam not in db_exam_titles:
            missing_in_db.append(exam)

    for db_title in db_exam_titles:
        if db_title not in json_exams:
            extra_in_db.append(db_title)

    # Report
    print("=== Comparison Report ===")
    print(f"Total exams in JSON: {len(json_exams)}")
    print(f"Total courses in DB: {len(db_courses)}")
    print()

    if not missing_in_db:
        print("✅ All JSON exams are in DB")
    else:
        print(f"❌ Missing in DB (extra in JSON) ({len(missing_in_db)}):")
        for exam in missing_in_db:
            print(f"  - {exam}")

    if not extra_in_db:
        print("✅ No extra courses in DB")
    else:
        print(f"⚠️ Extra in DB ({len(extra_in_db)} - possibly added manually):")
        for exam in extra_in_db:
            print(f"  - {exam}")

    print(f"Debug: Missing list: {missing_in_db}")  # Added debug

if __name__ == "__main__":
    asyncio.run(compare_exams_with_db())
