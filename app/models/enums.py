from enum import Enum


class ExamCategory(str, Enum):
    """Common exam/course categories"""

    MEDICAL = "medical"  # NEET
    ENGINEERING = "engineering"  # JEE Main, JEE Advanced
    TEACHING = "teaching"  # HTET, CTET, DSSSB, KVS
    GOVT_EXAMS = "govt_exams"  # SSC CGL, CHSL, MTS, CPO, GD
    BANKING = "banking"  # IBPS PO, Clerk, SBI PO, RBI Assistant, NABARD
    DEFENCE = "defence"  # NDA, CDS, Airforce X/Y, Navy, Agniveer
    STATE_EXAMS = "state_exams"  # HSSC, HCS, Patwari, Police, Teachers


class UserRole(str, Enum):
    """User roles"""

    STUDENT = "student"
    ADMIN = "admin"


class MaterialType(str, Enum):
    """Study material types"""

    PDF = "pdf"
    DOC = "doc"
    DOCX = "docx"
    PPTX = "pptx"
    VIDEO = "video"
    AUDIO = "audio"
    LINK = "link"
    PYQ = "pyq"  # Previous Year Questions


class MaterialAccessType(str, Enum):
    """Material access control"""

    FREE = "free"  # Available to all users
    PREMIUM = "premium"  # Requires payment/subscription
    ENROLLED = "enrolled"  # Available to enrolled students only
    COURSE_ONLY = "course_only"  # Available only to enrolled students


class MaterialCategory(str, Enum):
    """Study material categories"""

    NOTES = "notes"
    PYQ = "previous_year_questions"
    REFERENCE = "reference"
    WORKSHEET = "worksheet"
    SOLUTION = "solution"
    FORMULA_SHEET = "formula_sheet"
    SYLLABUS = "syllabus"
