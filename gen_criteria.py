"""
Generate test_criteria/cv21.json … cv30.json matching the CV fixtures in gen_cv.py.
Each criteria file mirrors the structure used in cv01-cv10 ground truth.
"""

import json
import os

OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "test_criteria")
os.makedirs(OUT_DIR, exist_ok=True)


def cv21_criteria():
    return {
        "personal_info": {
            "full_name": "Sarah Elizabeth Morgan",
            "email": "sarah.morgan.md@email.com",
            "phone": "(+1) 415 555 0345",
            "city": "San Francisco",
            "country": "US",
        },
        "summary": "Triple-board-certified internist with 11 years of clinical experience in hospital medicine, clinical research, and medical education.",
        "education": [
            {"degree": "Doctor of Medicine (M.D.)", "institution": "Harvard Medical School, Boston",
             "year_start": "2007", "year_end": "2011"},
            {"degree": "Doctor of Philosophy (Ph.D.) in Cardiovascular Epidemiology",
             "institution": "Harvard T.H. Chan School of Public Health", "year_start": "2004", "year_end": "2007"},
            {"degree": "Bachelor of Arts (B.A.) in Bioethics, summa cum laude",
             "institution": "Yale University, New Haven",
             "year_start": "2000", "year_end": "2004", "gpa": "3.95/4.0"},
            {"degree": "Internal Medicine Residency", "institution": "Massachusetts General Hospital",
             "year_start": "2011", "year_end": "2014"},
        ],
        "work_experience": [
            {"title": "Attending Hospitalist — Internal Medicine",
             "company": "UCSF Medical Center, San Francisco",
             "start_date": "Jul 2018", "end_date": "Present", "is_current": True},
            {"title": "Attending Hospitalist",
             "company": "Stanford Health Care, Stanford, CA",
             "start_date": "Aug 2014", "end_date": "Jun 2018"},
            {"title": "Internal Medicine Resident (Categorical)",
             "company": "Massachusetts General Hospital, Boston",
             "start_date": "Jun 2011", "end_date": "Jun 2014"},
        ],
        "certifications": [
            "American Board of Internal Medicine — Certified 2014, Recertified 2024",
            "California Medical License #A123456 — Active through 12/2026",
            "Advanced Cardiac Life Support (ACLS) — Recertified 2024",
        ],
        "languages": [
            {"language": "English", "proficiency": "Native"},
            {"language": "Spanish", "proficiency": "Fluent — Medical Interpreter Certified"},
        ],
        "publications": [
            "Morgan SE, et al. Outcomes of Early Discharge Protocol in CHF Patients. New England Journal of Medicine, 2023.",
            "Morgan SE, Patel R. Sex Differences in Acute MI Presentation Patterns. Circulation, 2021.",
        ],
        "metadata": {"form_type": "freeform"},
    }


def cv22_criteria():
    return {
        "personal_info": {
            "full_name": "Robert Alan Patel",
            "email": "robert.patel.cpa@email.com",
            "phone": "(+1) 212 555 0398",
            "city": "Jersey City",
            "country": "US",
        },
        "summary": "Results-driven CPA with 13 years of progressive experience in corporate accounting, SOX compliance, and financial reporting.",
        "education": [
            {"degree": "Master of Business Administration (MBA) — Finance",
             "institution": "NYU Stern School of Business",
             "year_start": "2015", "year_end": "2017", "gpa": "3.8/4.0"},
            {"degree": "Bachelor of Science (B.S.) in Accounting, magna cum laude",
             "institution": "Rutgers University, New Brunswick",
             "year_start": "2008", "year_end": "2012", "gpa": "3.78/4.0"},
        ],
        "work_experience": [
            {"title": "Senior Financial Controller",
             "company": "Hudson Capital Markets, New York, NY",
             "start_date": "Aug 2020", "end_date": "Present", "is_current": True},
            {"title": "Assistant Controller — Financial Reporting",
             "company": "Greenwich Financial Holdings, Stamford, CT",
             "start_date": "Mar 2017", "end_date": "Jul 2020"},
            {"title": "Senior Accountant — Audit & Advisory",
             "company": "Deloitte & Touche LLP, New York, NY",
             "start_date": "Sep 2014", "end_date": "Feb 2017"},
            {"title": "Staff Accountant",
             "company": "PricewaterhouseCoopers LLP, New York, NY",
             "start_date": "Aug 2012", "end_date": "Aug 2014"},
        ],
        "certifications": [
            "Certified Public Accountant (CPA) — New York State #0876543 — Active since 2013",
            "Certified Fraud Examiner (CFE) — ACFE — Obtained 2019",
            "AWS Cloud Practitioner Certification — 2023",
        ],
        "languages": [
            {"language": "English", "proficiency": "Native"},
            {"language": "Hindi", "proficiency": "Fluent"},
        ],
        "metadata": {"form_type": "freeform"},
    }


def cv23_criteria():
    return {
        "personal_info": {
            "full_name": "Jennifer Marie Davis",
            "email": "jennifer.davis.teacher@email.com",
            "phone": "(+1) 303 555 0167",
            "city": "Denver",
            "country": "US",
        },
        "summary": "Dedicated English/Language Arts educator with 8 years of experience fostering literacy and critical thinking in diverse high school classrooms.",
        "education": [
            {"degree": "M.A. Curriculum & Instruction",
             "institution": "University of Colorado Denver",
             "year_start": "2014", "year_end": "2016"},
            {"degree": "B.A. English Literature",
             "institution": "University of Colorado Boulder",
             "year_start": "2010", "year_end": "2014", "gpa": "3.6/4.0"},
        ],
        "work_experience": [
            {"title": "10th Grade English Teacher",
             "company": "Denver South High School, Denver, CO",
             "start_date": "Aug 2020", "end_date": "Present", "is_current": True},
            {"title": "9th Grade English Teacher",
             "company": "Aurora Central High School, Aurora, CO",
             "start_date": "Aug 2017", "end_date": "May 2020"},
            {"title": "Middle School Language Arts Teacher",
             "company": "Wheeler Middle School, Denver",
             "start_date": "Aug 2016", "end_date": "May 2017"},
        ],
        "certifications": [
            "Colorado Professional Teaching License #12345678 — English (7-12), Active",
            "National Board Certified Teacher (NBCT) — Adolescent English Language Arts, 2022",
        ],
        "metadata": {"form_type": "freeform"},
    }


def cv24_criteria():
    return {
        "personal_info": {
            "full_name": "Hannah Liu",
            "email": "hannah.liu.arch@email.com",
            "phone": "(+1) 617 555 0234",
            "city": "Cambridge",
            "country": "US",
        },
        "summary": "Licensed architect with 10 years of experience designing high-performance educational, healthcare, and civic buildings.",
        "education": [
            {"degree": "M.Arch (Master of Architecture)",
             "institution": "Massachusetts Institute of Technology (MIT)",
             "year_start": "2011", "year_end": "2014"},
            {"degree": "B.A. Architecture, cum laude",
             "institution": "Wesleyan University, Middletown, CT",
             "year_start": "2007", "year_end": "2011", "gpa": "3.7/4.0"},
        ],
        "work_experience": [
            {"title": "Senior Architect / Project Lead",
             "company": "Payette Associates, Boston, MA",
             "start_date": "Sep 2020", "end_date": "Present", "is_current": True},
            {"title": "Architect",
             "company": "Perkins&Will, Boston, MA",
             "start_date": "Jun 2017", "end_date": "Aug 2020"},
            {"title": "Junior Architect",
             "company": "Sasaki Associates, Watertown, MA",
             "start_date": "Jun 2014", "end_date": "May 2017"},
        ],
        "certifications": [
            "Registered Architect (RA) — Massachusetts #ARC-98765 — Active",
            "NCIDQ-certified — Certificate #NCIDQ-45678",
            "LEED Accredited Professional — Building Design + Construction (BD+C)",
            "WELL AP — Well Building Standard, 2022",
        ],
        "languages": [
            {"language": "English", "proficiency": "Native"},
            {"language": "Mandarin Chinese", "proficiency": "Fluent — HSK 6"},
        ],
        "projects": [
            {"name": "BU College of Engineering — Lab Building",
             "year": "2024", "value": "$45M"},
            {"name": "Boston Public Library — Branch Renovation",
             "year": "2023", "value": "$8M"},
            {"name": "MIT Sloan — East Wing Addition",
             "year": "2022", "value": "$28M"},
        ],
        "metadata": {"form_type": "freeform"},
    }


def cv25_criteria():
    return {
        "personal_info": {
            "full_name": "Marina Petrova",
            "email": "marina.petrova@email.com",
            "phone": "(+7) 905 123 45 67",
            "city": "Moscow",
            "country": "Russia",
        },
        "summary": "Senior product designer with 9 years experience leading 0-to-1 product development for B2B SaaS and consumer apps.",
        "education": [
            {"degree": "M.A. Interaction Design",
             "institution": "Royal College of Art, London, UK",
             "year_start": "2014", "year_end": "2016"},
            {"degree": "B.A. Visual Communication",
             "institution": "Moscow State Stroganov Academy, Russia",
             "year_start": "2010", "year_end": "2014"},
        ],
        "work_experience": [
            {"title": "Senior Product Designer / Lead",
             "company": "Avito (Tech Holding)",
             "start_date": "Jan 2022", "end_date": "Present", "is_current": True},
            {"title": "Product Designer",
             "company": "Yandex",
             "start_date": "Mar 2018", "end_date": "Dec 2021"},
            {"title": "UX/UI Designer",
             "company": "Studio Mobile, Moscow",
             "start_date": "Sep 2016", "end_date": "Feb 2018"},
        ],
        "awards": [
            "Red Dot Design Award 2023 — Product Design category",
            "Awwwards Site of the Day (Mar 2022)",
        ],
        "languages": [
            {"language": "Russian", "proficiency": "Native"},
            {"language": "English", "proficiency": "Fluent — IELTS 8.0"},
            {"language": "German", "proficiency": "B2 — Goethe-Zertifikat"},
        ],
        "metadata": {"form_type": "freeform"},
    }


def cv26_criteria():
    return {
        "personal_info": {
            "full_name": "Trần Minh Quân",
            "email": "tranquan.dev@email.com",
            "phone": "(+84) 909 876 543",
            "city": "TP. Hồ Chí Minh",
            "country": "Vietnam",
        },
        "summary": "Kỹ sư phần mềm với 6 năm kinh nghiệm phát triển backend Java/Spring Boot và hệ thống microservices.",
        "education": [
            {"degree": "Kỹ sư Khoa học Máy tính (tốt nghiệp loại Giỏi)",
             "institution": "Trường Đại học Bách Khoa TP.HCM (HCMUT)",
             "year_start": "2013", "year_end": "2017", "gpa": "3.6/4.0"},
        ],
        "work_experience": [
            {"title": "Senior Backend Engineer",
             "company": "Tiki Corporation",
             "start_date": "Tháng 6/2021", "end_date": "Present", "is_current": True},
            {"title": "Backend Engineer",
             "company": "VNG Corporation (ZaloPay)",
             "start_date": "Tháng 3/2019", "end_date": "Tháng 5/2021"},
            {"title": "Java Developer",
             "company": "FPT Software",
             "start_date": "Tháng 8/2017", "end_date": "Tháng 2/2019"},
        ],
        "certifications": [
            "Oracle Certified Professional Java SE 11 Developer — 2020",
            "AWS Solutions Architect Associate — 2022",
            "Certified Kubernetes Administrator (CKA) — 2023",
        ],
        "languages": [
            {"language": "Tiếng Việt", "proficiency": "Bản ngữ"},
            {"language": "English", "proficiency": "TOEFL iBT 95"},
            {"language": "Japanese", "proficiency": "JLPT N3"},
        ],
        "metadata": {"form_type": "structured_form"},
    }


def cv27_criteria():
    return {
        "personal_info": {
            "full_name": "Klaus Weber",
            "email": "klaus.weber.eng@email.com",
            "phone": "(+49) 89 1234 5678",
            "city": "München",
            "country": "Germany",
        },
        "summary": "Diplom-Ingenieur mit 17 Jahren Erfahrung in der Automobil- und Luftfahrtbranche.",
        "education": [
            {"degree": "Dr.-Ing. Maschinenbau (Promotion)",
             "institution": "Technische Universität München (TUM)",
             "year_start": "2007", "year_end": "2010"},
            {"degree": "Dipl.-Ing. Maschinenbau (Diplom)",
             "institution": "RWTH Aachen",
             "year_start": "2002", "year_end": "2007"},
        ],
        "work_experience": [
            {"title": "Engineering Manager — Powertrain",
             "company": "BMW Group, München",
             "start_date": "01.03.2019", "end_date": "Present", "is_current": True},
            {"title": "Senior Mechanical Engineer",
             "company": "Airbus Operations GmbH, Hamburg",
             "start_date": "15.06.2014", "end_date": "28.02.2019"},
            {"title": "Mechanical Engineer",
             "company": "Robert Bosch GmbH, Stuttgart",
             "start_date": "01.09.2010", "end_date": "31.05.2014"},
        ],
        "certifications": [
            "Six Sigma Black Belt (ASQ) — 2019",
            "PMP — Project Management Professional (PMI) — 2017",
            "EASA Part 66 B1.1 Aircraft Maintenance License — 2014",
        ],
        "patents": [
            "EP1234567B1 — Verstärkungsstruktur für Flugzeugkomponenten (2020)",
            "DE102015008341A1 — Einspritzventil mit optimiertem Strömungsverhalten (2017)",
        ],
        "languages": [
            {"language": "German", "proficiency": "Muttersprache"},
            {"language": "English", "proficiency": "C2 — Cambridge CPE"},
        ],
        "metadata": {"form_type": "freeform"},
    }


def cv28_criteria():
    return {
        "personal_info": {
            "full_name": "Olivia Chen",
            "email": "olivia.chen.cs@email.com",
            "phone": "(+1) 408 555 0298",
            "city": "San Jose",
            "country": "US",
        },
        "summary": "Recent CS graduate seeking a full-time software engineering role.",
        "education": [
            {"degree": "B.S. Computer Science",
             "institution": "University of California, Berkeley",
             "year_start": "2021", "year_end": "2025", "gpa": "3.85/4.0"},
        ],
        "work_experience": [
            {"title": "Backend Engineering Intern",
             "company": "Visa Inc., San Francisco (Summer 2024)",
             "start_date": "Jun 2024", "end_date": "Aug 2024"},
            {"title": "Computer Science Tutor",
             "company": "UC Berkeley Student Learning Center",
             "start_date": "Sep 2023", "end_date": "May 2024"},
        ],
        "projects": [
            {"name": "Course Enrollment Platform",
             "description": "Full-stack web app in team of 5 using React, Flask, PostgreSQL",
             "technologies": ["React", "Flask", "PostgreSQL"]},
            {"name": "Pac-Man AI",
             "description": "Implemented search and adversarial agents",
             "technologies": ["Python"]},
        ],
        "metadata": {"form_type": "freeform"},
    }


def cv29_criteria():
    return {
        "personal_info": {
            "full_name": "Nguyễn Thị Hồng Vân",
            "email": "vannguyen.marketing@email.com",
            "phone": "(+84) 988 234 567",
            "city": "Đà Nẵng",
            "country": "Vietnam",
        },
        "summary": "Marketing Manager with 8 years of experience building brands across FMCG and tech in Vietnam and SEA markets.",
        "education": [
            {"degree": "MBA Marketing — Dean's List",
             "institution": "University of Economics HCMC (UEH)",
             "year_start": "2017", "year_end": "2019", "gpa": "3.8/4.0"},
            {"degree": "B.A. International Business",
             "institution": "Foreign Trade University (FTU), Hanoi",
             "year_start": "2012", "year_end": "2016", "gpa": "3.7/4.0"},
        ],
        "work_experience": [
            {"title": "Senior Marketing Manager",
             "company": "Vinamilk / Vinamilk Brand Division",
             "start_date": "Mar 2021", "end_date": "Present", "is_current": True},
            {"title": "Marketing Manager",
             "company": "Tiki Corporation (E-commerce)",
             "start_date": "Jul 2018", "end_date": "Feb 2021"},
            {"title": "Brand Executive",
             "company": "Unilever Vietnam (Pond's, Dove)",
             "start_date": "Aug 2016", "end_date": "Jun 2018"},
        ],
        "certifications": [
            "Google Ads Certified — Search, Display, Video, Measurement (2023)",
            "Meta Blueprint Certified — Facebook Media Planning Professional (2024)",
            "HubSpot Inbound Marketing Certification (2022)",
        ],
        "awards": [
            "MMA Smarties Vietnam — Silver, Brand Marketing 2023",
            "Marketing Magazine Vietnam — Top 30 Under 30 2020",
        ],
        "languages": [
            {"language": "Vietnamese", "proficiency": "Native"},
            {"language": "English", "proficiency": "IELTS 7.5"},
            {"language": "Mandarin Chinese", "proficiency": "HSK 4"},
        ],
        "metadata": {"form_type": "freeform"},
    }


def cv30_criteria():
    return {
        "personal_info": {
            "full_name": "Li Wei",
            "email": "liwei.data@email.com",
            "phone": "(+65) 9123 4567",
            "city": "Singapore",
            "country": "Singapore",
        },
        "summary": "Data engineer with 8 years of experience building large-scale data platforms and ML infrastructure.",
        "education": [
            {"degree": "M.S. Computer Science (Big Data Systems)",
             "institution": "National University of Singapore (NUS)",
             "year_start": "2015", "year_end": "2017", "gpa": "4.6/5.0"},
            {"degree": "B.Eng. Software Engineering",
             "institution": "South China University of Technology (SCUT)",
             "year_start": "2011", "year_end": "2015", "gpa": "3.78/4.0"},
        ],
        "work_experience": [
            {"title": "Senior Data Engineer — ML Platform",
             "company": "TikTok (ByteDance), Singapore",
             "start_date": "Sep 2021", "end_date": "Present", "is_current": True},
            {"title": "Data Engineer",
             "company": "Shopee (Sea Group), Singapore",
             "start_date": "Mar 2019", "end_date": "Aug 2021"},
            {"title": "Backend / Data Engineer",
             "company": "Akulaku, Jakarta, Indonesia",
             "start_date": "Jun 2017", "end_date": "Feb 2019"},
            {"title": "Software Engineer Intern",
             "company": "Tencent, Shenzhen, China",
             "start_date": "Jun 2016", "end_date": "Aug 2016"},
        ],
        "certifications": [
            "AWS Certified Solutions Architect — Professional (2023)",
            "GCP Professional Data Engineer (2022)",
            "Databricks Certified Data Engineer Professional (2022)",
            "SnowPro Advanced — Snowflake Snowpipe Streaming (2023)",
        ],
        "languages": [
            {"language": "English", "proficiency": "Fluent"},
            {"language": "Mandarin Chinese", "proficiency": "Native"},
        ],
        "metadata": {"form_type": "freeform"},
    }


def main():
    crits = {
        "cv21": cv21_criteria,
        "cv22": cv22_criteria,
        "cv23": cv23_criteria,
        "cv24": cv24_criteria,
        "cv25": cv25_criteria,
        "cv26": cv26_criteria,
        "cv27": cv27_criteria,
        "cv28": cv28_criteria,
        "cv29": cv29_criteria,
        "cv30": cv30_criteria,
    }
    for cv_id, fn in crits.items():
        path = os.path.join(OUT_DIR, f"{cv_id}.json")
        with open(path, "w") as f:
            json.dump(fn(), f, indent=2, ensure_ascii=False)
        print(f"  ✓ {path}")


if __name__ == "__main__":
    main()
