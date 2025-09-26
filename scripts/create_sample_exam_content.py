# #!/usr/bin/env python3
# """
# Script to create sample exam content for testing
# """

# import asyncio
# import sys
# import os
# from datetime import datetime, timezone

# # Add the parent directory to the path so we can import from app
# sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# from app.db import init_db
# from app.models.exam_content import ExamContent, ExamInfoSection


# async def create_sample_exam_content():
#     """Create sample exam content for testing"""

#     # Initialize database connection
#     print("🔌 Connecting to database...")
#     await init_db()
#     print("✅ Database connected")

#     # Sample exam content for SSC CGL
#     sample_content = ExamContent(
#         exam_code="ssc cgl",
#         title="SSC CGL (Combined Graduate Level)",
#         description="Staff Selection Commission Combined Graduate Level Examination is conducted for recruitment to various posts in different ministries and departments of the Government of India.",
#         linked_course_id="dummy-course-id",
#         thumbnail_url=None,
#         banner_url=None,
#         exam_info_sections=[
#             ExamInfoSection(
#                 id="1",
#                 header="Exam Pattern",
#                 content="SSC CGL consists of 4 tiers:\n\nTier 1: Computer Based Test (CBT) - 200 questions, 60 minutes\n- General Intelligence & Reasoning (25 questions)\n- General Awareness (25 questions)\n- Quantitative Aptitude (25 questions)\n- English Comprehension (25 questions)\n\nTier 2: Computer Based Test (CBT) - 100 questions, 120 minutes\n- Quantitative Abilities (50 questions)\n- English Language & Comprehension (50 questions)\n\nTier 3: Descriptive Paper (Pen & Paper mode) - 60 minutes\n- Essay/Letter/Application writing in English or Hindi\n\nTier 4: Computer Proficiency Test/Skill Test (where applicable)",
#                 order=1,
#                 is_active=True,
#             ),
#             ExamInfoSection(
#                 id="2",
#                 header="Time Duration",
#                 content="Total Duration: 4 hours 20 minutes\n\n- Tier 1: 60 minutes\n- Tier 2: 120 minutes\n- Tier 3: 60 minutes\n- Tier 4: Variable (as per post requirements)\n\nNote: There is no negative marking in Tier 3 and Tier 4.",
#                 order=2,
#                 is_active=True,
#             ),
#             ExamInfoSection(
#                 id="3",
#                 header="Syllabus",
#                 content="Tier 1 Syllabus:\n\n1. General Intelligence & Reasoning\n- Analogies, Similarities, Differences\n- Space visualization, Spatial orientation\n- Problem solving, Analysis, Judgment\n- Decision making, Visual memory\n- Discrimination, Observation\n- Relationship concepts, Arithmetical reasoning\n- Verbal and figure classification\n- Arithmetic number series\n- Non-verbal series, Coding and decoding\n- Statement conclusion, Syllogistic reasoning\n\n2. General Awareness\n- Current events, History, Culture\n- Geography, Economic scene\n- General Polity, Indian Constitution\n- Scientific Research, Sports\n\n3. Quantitative Aptitude\n- Number systems, Computation of whole numbers\n- Decimals and fractions, Relationship between numbers\n- Percentages, Ratio and Proportion\n- Square roots, Averages, Interest\n- Profit and Loss, Discount\n- Partnership Business, Mixture and Alligation\n- Time and distance, Time and work\n- Basic algebraic identities\n- Elementary surds, Graphs of linear equations\n- Triangle and its various kinds of centres\n- Congruence and similarity of triangles\n- Circle and its chords, tangents\n- Angles subtended by chords of a circle\n- Common tangents to two or more circles\n- Triangle, Quadrilaterals, Regular Polygons\n- Circle, Right Prism, Right Circular Cone\n- Right Circular Cylinder, Sphere, Hemispheres\n- Rectangular Parallelepiped, Regular Right Pyramid\n- Trigonometric ratio, Degree and Radian Measures\n- Standard Identities, Complementary angles\n- Heights and Distances, Histogram, Frequency polygon\n- Bar diagram, Pie chart\n\n4. English Comprehension\n- Vocabulary, Grammar, Sentence structure\n- Synonyms, Antonyms, One word substitution\n- Idioms and phrases, Fill in the blanks\n- Cloze passage, Comprehension passage\n- Active/Passive voice, Direct/Indirect speech\n- Sentence improvement, Spotting errors",
#                 order=3,
#                 is_active=True,
#             ),
#             ExamInfoSection(
#                 id="4",
#                 header="Eligibility Criteria",
#                 content="Educational Qualification:\n\nFor Assistant Audit Officer/Assistant Accounts Officer:\n- Essential Qualifications: Bachelor's Degree from a recognized University or Institute\n- Desirable Qualifications: Chartered Accountant or Cost & Management Accountant or Company Secretary or Masters in Commerce or Masters in Business Studies or Masters in Business Administration (Finance) or Masters in Business Economics\n\nFor Junior Statistical Officer:\n- Essential Qualifications: Bachelor's Degree in any subject from a recognized University or Institute with at least 60% Marks in Mathematics at 12th standard level\n- OR Bachelor's Degree in any subject with Statistics as one of the subjects at degree level\n\nFor all other posts:\n- Bachelor's Degree from a recognized University or equivalent\n\nAge Limit:\n- 18-32 years (as on 01-01-2024)\n- Age relaxation as per government rules for reserved categories",
#                 order=4,
#                 is_active=True,
#             ),
#             ExamInfoSection(
#                 id="5",
#                 header="Selection Process",
#                 content="The selection process consists of 4 stages:\n\n1. Tier 1 (Preliminary Examination)\n- Computer Based Test\n- Objective type questions\n- 200 questions, 60 minutes\n- Qualifying in nature\n\n2. Tier 2 (Main Examination)\n- Computer Based Test\n- Objective type questions\n- 100 questions, 120 minutes\n- Merit ranking for Tier 3\n\n3. Tier 3 (Descriptive Paper)\n- Pen and Paper mode\n- Essay/Letter/Application writing\n- 60 minutes\n- Qualifying in nature\n\n4. Tier 4 (Computer Proficiency Test/Skill Test)\n- Computer Proficiency Test (CPT)\n- Data Entry Skill Test (DEST)\n- Document Verification\n- Medical Examination (if applicable)\n\nFinal merit list is prepared based on marks obtained in Tier 2 and Tier 3.",
#                 order=5,
#                 is_active=True,
#             ),
#         ],
#         is_active=True,
#         created_at=datetime.now(timezone.utc),
#         updated_at=datetime.now(timezone.utc),
#     )

#     # Check if content already exists
#     existing = await ExamContent.find_one(ExamContent.exam_code == "ssc cgl")
#     if existing:
#         print("⚠️  Sample exam content already exists for 'ssc cgl'")
#         print("🔄 Updating existing content...")
#         existing.title = sample_content.title
#         existing.description = sample_content.description
#         existing.exam_info_sections = sample_content.exam_info_sections
#         existing.updated_at = datetime.now(timezone.utc)
#         await existing.save()
#         print("✅ Sample exam content updated successfully")
#     else:
#         print("📝 Creating sample exam content...")
#         await sample_content.insert()
#         print("✅ Sample exam content created successfully")

#     # Verify the content was created
#     created_content = await ExamContent.find_one(ExamContent.exam_code == "ssc cgl")
#     if created_content:
#         print(f"\n📊 Created exam content:")
#         print(f"   Title: {created_content.title}")
#         print(f"   Exam Code: {created_content.exam_code}")
#         print(f"   Sections: {len(created_content.exam_info_sections)}")
#         print(f"   Created: {created_content.created_at}")

#         print(f"\n📋 Sections:")
#         for i, section in enumerate(created_content.exam_info_sections, 1):
#             print(f"   {i}. {section.header}")
#     else:
#         print("❌ Failed to create sample exam content")


# if __name__ == "__main__":
#     asyncio.run(create_sample_exam_content())
