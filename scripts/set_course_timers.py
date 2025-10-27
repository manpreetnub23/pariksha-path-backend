#!/usr/bin/env python3
"""
Script to update all existing courses with a 30-minute timer for mock tests.
This script sets mock_test_timer_seconds to 1800 (30 minutes * 60 seconds)
for all courses that don't already have this field set.

Usage:
    python scripts/set_course_timers.py

Requirements:
    - .env file with database credentials (same as main app)
    - The script will automatically load settings from the .env file
"""


import asyncio
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from app.config import settings

from app.models.course import Course
from app.db import init_db


async def set_course_timers():
    """
    Update all courses to set mock_test_timer_seconds to 30 minutes (1800 seconds)
    """
    print("🔄 Initializing database connection...")
    await init_db()

    # 30 minutes in seconds
    new_timer_seconds = 1800

    print(f"🔍 Finding all courses...")

    # Get all courses
    all_courses = await Course.find().to_list()
    total_courses = len(all_courses)

    print(f"📊 Found {total_courses} courses")

    if total_courses == 0:
        print("❌ No courses found in database")
        return

    updated_count = 0
    skipped_count = 0

    print(f"\n🚀 Updating courses with {new_timer_seconds // 60} minute timer...")

    for i, course in enumerate(all_courses, 1):
        print(f"  Processing {i}/{total_courses}: {course.title} ({course.code})")

        # Check current timer value
        current_timer = getattr(course, "mock_test_timer_seconds", None)

        if current_timer is None:
            print(f"    ⚠️  No timer field found (using default)")
        elif current_timer == new_timer_seconds:
            print(f"    ⏭️  Already has {current_timer // 60} minute timer, skipping")
            skipped_count += 1
            continue
        else:
            print(
                f"    📏 Current timer: {current_timer // 60} minutes ({current_timer}s)"
            )

        # Update the timer
        course.mock_test_timer_seconds = new_timer_seconds
        course.update_timestamp()
        await course.save()

        print(
            f"    ✅ Updated to {new_timer_seconds // 60} minutes ({new_timer_seconds}s)"
        )
        updated_count += 1

        # Progress indicator every 10 courses
        if i % 10 == 0:
            print(f"  📈 Progress: {i}/{total_courses} courses processed")

    print("🎉 Update completed!")
    print(f"   ✅ Updated: {updated_count} courses")
    print(f"   ⏭️  Skipped: {skipped_count} courses")
    print(f"   📊 Total: {total_courses} courses")

    # Summary of timer distribution
    print("📋 Timer distribution summary:")
    timer_counts = {}

    for course in all_courses:
        timer_value = getattr(course, "mock_test_timer_seconds", 0)
        minutes = timer_value // 60
        timer_counts[minutes] = timer_counts.get(minutes, 0) + 1

    for minutes, count in sorted(timer_counts.items()):
        print(f"   {minutes} minutes: {count} courses")


async def verify_update():
    """
    Verify that the update was successful by checking a few courses
    """
    print("🔍 Verifying update...")
    await init_db()

    # Get a sample of courses to verify
    sample_courses = await Course.find().limit(5).to_list()

    print("Sample verification:")
    for course in sample_courses:
        timer_seconds = getattr(course, "mock_test_timer_seconds", 0)
        timer_minutes = timer_seconds // 60
        print(f"   {course.title}: {timer_minutes} minutes ({timer_seconds}s)")


if __name__ == "__main__":
    print("🎯 Course Timer Update Script")
    print("=" * 50)
    print("This script will set all courses to use a 30-minute timer for mock tests.")
    print("Settings will be loaded automatically from the .env file.")
    print()

    # Check if environment variables are set
    if not hasattr(settings, 'MONGO_URI') or not settings.MONGO_URI:
        print("❌ MONGO_URI not found in settings!")
        print("Please set your MONGO_URI in the .env file.")
        sys.exit(1)

    print(f"📊 MongoDB URI: {settings.MONGO_URI[:20]}... (masked)")
    print()

    try:
        # Run the main update
        asyncio.run(set_course_timers())

        # Verify the update
        # await asyncio.sleep(1)  # Brief pause
        asyncio.run(verify_update())

        print("✅ Script completed successfully!")
        print("All courses now have a 30-minute timer for mock tests.")

    except Exception as e:
        print(f"\n❌ Error occurred: {str(e)}")
        print("Please check your database connection and try again.")
        sys.exit(1)
