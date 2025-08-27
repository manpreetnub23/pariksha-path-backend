from fastapi.testclient import TestClient
import sys
import os
import asyncio
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from app.main import app
from app.models.exam_category_structure import ExamCategoryStructure
from app.db import init_db

# Sample exam category structure
exam_structure = {
    "SSC": {
        "National": [
            "SSC CGL",
            "SSC CHSL",
            "SSC MTS",
            "SSC GD Constable",
            "SSC CPO",
            "SSC JE",
            "SSC Stenographer (C & D)",
            "SSC JHT",
            "SSC Selection Post",
            "SSC Scientific Assistant (IMD)",
            "SSC Delhi Police Constable",
        ]
    },
    "Banking & Insurance": {
        "SBI": ["SBI PO", "SBI Clerk", "SBI SO"],
        "IBPS": ["IBPS PO", "IBPS Clerk", "IBPS SO", "IBPS RRB PO", "IBPS RRB Clerk"],
        "RBI": ["RBI Grade B", "RBI Assistant", "RBI Specialist"],
        "Other": [
            "NABARD Grade A & B",
            "SIDBI Grade A",
            "LIC AAO",
            "LIC ADO",
            "LIC Assistant",
            "NIACL AO",
            "NIACL Assistant",
            "GIC Assistant Manager",
        ],
    },
    "Teaching": {
        "Central": [
            "CTET Paper 1",
            "CTET Paper 2",
            "KVS PRT",
            "KVS TGT",
            "KVS PGT",
            "NVS PRT",
            "NVS TGT",
            "NVS PGT",
            "DSSSB PRT",
            "DSSSB TGT",
            "DSSSB PGT",
            "DSSSB Nursery",
            "AWES (Army Public School) PRT",
            "AWES TGT",
            "AWES PGT",
            "EMRS TGT",
            "EMRS PGT",
        ],
        "State": {
            "Haryana": ["HTET"],
            "Rajasthan": ["REET", "RTET"],
            "Uttar Pradesh": ["UPTET", "Super TET"],
            "Bihar": ["BTET"],
            "Madhya Pradesh": ["MPTET"],
            "Maharashtra": ["MHTET"],
            "Karnataka": ["KARTET"],
            "Kerala": ["KTET"],
            "Odisha": ["OTET"],
            "West Bengal": ["WBTET"],
            "Andhra Pradesh": ["AP TET"],
            "Telangana": ["TS TET"],
            "Tamil Nadu": ["TN TET"],
            "Assam": ["Assam TET"],
            "Nagaland": ["Nagaland TET"],
            "Tripura": ["Tripura TET"],
            "Arunachal Pradesh": ["Arunachal Pradesh TET"],
            "Manipur": ["Manipur TET"],
            "Meghalaya": ["Meghalaya TET"],
            "Mizoram": ["Mizoram TET"],
            "Goa": ["Goa TET"],
            "Jharkhand": ["JTET"],
            "Chhattisgarh": ["CGTET"],
            "Punjab": ["PSTET"],
            "Himachal Pradesh": ["HPTET"],
            "Jammu & Kashmir": ["JK TET"],
            "Uttarakhand": ["UTET"],
        },
    },
    "Defence": {
        "NDA & NA": ["NDA", "NA Exam"],
        "CDS": ["CDS Exam"],
        "Army": [
            "TES",
            "JAG",
            "NCC Special Entry",
            "TGC",
            "SSC Tech Entry",
            "Agniveer GD",
            "Agniveer Technical",
            "Agniveer Clerk",
            "Agniveer Tradesman",
        ],
        "Air Force": ["AFCAT", "Agniveer Vayu", "NCC Special Entry"],
        "Navy": [
            "B.Tech Entry",
            "INET",
            "SSR",
            "AA",
            "MR",
            "Agniveer SSR",
            "Agniveer MR",
        ],
        "Special Defence": [
            "CAPF (Assistant Commandant)",
            "Coast Guard (AC, Navik, Yantrik)",
        ],
        "Other": ["Territorial Army Officer", "SSC Tech", "UES", "Direct SSB"],
    },
    "State Government": {
        "PSC": {
            "Uttar Pradesh": ["UPPCS"],
            "Bihar": ["BPSC"],
            "Haryana": ["HPSC"],
            "Rajasthan": ["RPSC"],
            "Madhya Pradesh": ["MPPSC"],
            "Uttarakhand": ["UKPSC"],
            "Himachal Pradesh": ["HPPSC"],
            "Jharkhand": ["JPSC"],
            "Chhattisgarh": ["CGPSC"],
            "Tamil Nadu": ["TNPSC"],
            "Karnataka": ["KPSC"],
            "Kerala": ["Kerala PSC"],
            "Telangana": ["TSPSC"],
            "Andhra Pradesh": ["APPSC"],
            "Maharashtra": ["MPSC"],
            "West Bengal": ["WBPSC"],
            "Odisha": ["OPSC"],
            "Gujarat": ["GPSC"],
            "North East": [
                "Manipur PSC",
                "Meghalaya PSC",
                "Mizoram PSC",
                "Nagaland PSC",
                "Tripura PSC",
                "Goa PSC",
            ],
        },
        "SSC/Boards": {
            "Uttar Pradesh": ["UPSSSC"],
            "Haryana": ["HSSC"],
            "Rajasthan": ["RSMSSB"],
            "Madhya Pradesh": ["MPESB (Vyapam)"],
            "Uttarakhand": ["UKSSSC"],
            "Himachal Pradesh": ["HPSSSB"],
            "Bihar": ["BSSC"],
            "Jharkhand": ["JSSC"],
            "West Bengal": ["WBSSC"],
            "Tamil Nadu": ["TN MRB", "TN TRB"],
        },
        "Police": {
            "Uttar Pradesh": ["UP Police SI", "UP Police Constable"],
            "Haryana": ["Haryana Police SI", "Haryana Police Constable"],
            "Rajasthan": ["Rajasthan Police SI", "Rajasthan Police Constable"],
            "Madhya Pradesh": ["MP Police"],
            "Bihar": ["Bihar Police"],
            "Delhi": ["Delhi Police (via SSC)"],
        },
    },
    "Medical": {
        "National": [
            "NEET UG",
            "NEET PG",
            "INICET",
            "AIIMS Nursing",
            "JIPMER MBBS (NEET)",
            "FMGE",
        ],
        "Allied": ["NBE (DNB/DrNB)", "ICMR JRF", "State-level Counselling via NEET"],
    },
    "Engineering": {
        "National": [
            "JEE Main",
            "JEE Advanced",
            "BITSAT",
            "VITEEE",
            "SRMJEEE",
            "KIITEE",
            "AMUEEE",
            "AEEE",
        ],
        "State": {
            "Maharashtra": ["MHT CET"],
            "West Bengal": ["WBJEE"],
            "Karnataka": ["KCET"],
            "Andhra Pradesh": ["AP EAMCET / EAPCET"],
            "Telangana": ["TS EAMCET"],
            "Kerala": ["KEAM"],
            "Gujarat": ["GUJCET"],
            "Odisha": ["OJEE"],
            "Uttarakhand": ["UKSEE"],
            "Himachal Pradesh": ["HPCET"],
            "Chhattisgarh": ["CG PET"],
            "Bihar": ["BCECE"],
            "Jharkhand": ["JCECE"],
        },
    },
}


async def init_exam_categories():
    # Initialize database connection
    await init_db()

    # Create new structure document
    new_structure = ExamCategoryStructure(
        structure=exam_structure,
        version=1,
        created_by="system_init",  # Since this is a script
        is_active=True,
    )

    # Save to database
    await new_structure.insert()
    print("✅ Exam category structure initialized successfully!")
    print("\nStructure overview:")
    for category, subcategories in exam_structure.items():
        print(f"\n{category}:")
        for group, exams in subcategories.items():
            print(f"  {group}:")
            for exam in exams:
                print(f"    - {exam}")


if __name__ == "__main__":
    asyncio.run(init_exam_categories())
