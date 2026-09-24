"""
Generate CV Set 2: 10 completely different CVs.
Different industries, formats, layouts, edge cases.
"""

import os
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm, cm
from reportlab.lib.colors import HexColor, black, white
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, PageBreak
)
from reportlab.pdfgen import canvas

OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cv_test_data")
os.makedirs(OUT_DIR, exist_ok=True)
WIDTH, HEIGHT = A4


def S():
    """Fresh styles."""
    s = getSampleStyleSheet()
    s.add(ParagraphStyle('N1', parent=s['Title'], fontSize=22, leading=26,
                         textColor=HexColor('#1a1a2e'), spaceAfter=4))
    s.add(ParagraphStyle('H1', parent=s['Heading2'], fontSize=13, leading=16,
                         textColor=HexColor('#16213e'), spaceBefore=12, spaceAfter=6))
    s.add(ParagraphStyle('H2', parent=s['Heading3'], fontSize=11, leading=14,
                         textColor=HexColor('#0f3460'), spaceBefore=6, spaceAfter=3))
    s.add(ParagraphStyle('B', parent=s['Normal'], fontSize=10, leading=13,
                         textColor=HexColor('#333333'), spaceAfter=4))
    s.add(ParagraphStyle('SM', parent=s['Normal'], fontSize=9, leading=11,
                         textColor=HexColor('#666666'), spaceAfter=2))
    s.add(ParagraphStyle('CT', parent=s['Normal'], fontSize=10, leading=13,
                         textColor=HexColor('#555555'), alignment=TA_CENTER, spaceAfter=2))
    return s


def hr(color='#16213e'):
    return HRFlowable(width="100%", thickness=1.2, color=HexColor(color),
                      spaceBefore=0, spaceAfter=6)


def sec(text, s, color='#16213e'):
    return [Paragraph(f'<b>{text}</b>', s['H1']), hr(color)]


def job(title, company, dates, bullets, s):
    e = [Paragraph(f'<b>{title}</b> | {company}', s['H2']),
         Paragraph(f'<i>{dates}</i>', s['SM'])]
    for b in bullets:
        e.append(Paragraph(f'• {b}', s['B']))
    e.append(Spacer(1, 4))
    return e


def edu(degree, inst, year, gpa=None, s=None):
    extra = f' — GPA: {gpa}' if gpa else ''
    return [Paragraph(f'<b>{degree}</b>{extra}', s['H2']),
            Paragraph(f'{inst} | {year}', s['SM']), Spacer(1, 3)]


# ============================================================
# CV 11: Registered Nurse — Healthcare (Free-form)
# ============================================================
def cv11():
    path = os.path.join(OUT_DIR, "cv11_nurse_healthcare_freeform.pdf")
    doc = SimpleDocTemplate(path, pagesize=A4, leftMargin=2*cm, rightMargin=2*cm,
                            topMargin=2*cm, bottomMargin=2*cm)
    s = S()
    st = []
    st.append(Paragraph('AMARA OKONKWO, BSN, RN', s['N1']))
    st.append(Paragraph('amara.okonkwo@email.com | +1 (713) 555-0241 | Houston, TX 77030', s['CT']))
    st.append(Paragraph('License: TX RN #874521 (Active, Exp: 12/2026) | BLS/ACLS Certified', s['CT']))
    st.append(Spacer(1, 8))

    st += sec('PROFESSIONAL SUMMARY', s)
    st.append(Paragraph(
        'Compassionate registered nurse with 6 years of experience in critical care and '
        'emergency medicine. Skilled in trauma assessment, ventilator management, and patient '
        'advocacy. Charge nurse experience managing 12-bed ICU with 98.5% patient satisfaction '
        'score. Bilingual English/Igbo. Seeking Nurse Manager position to leverage clinical '
        'expertise and leadership skills.', s['B']))

    st += sec('LICENSES & CREDENTIALS', s)
    st.append(Paragraph('<b>RN License:</b> Texas Board of Nursing #874521 — Active, Expires 12/2026', s['B']))
    st.append(Paragraph('<b>BLS:</b> American Heart Association — Expires 03/2026', s['B']))
    st.append(Paragraph('<b>ACLS:</b> American Heart Association — Expires 03/2026', s['B']))
    st.append(Paragraph('<b>CCRN:</b> AACN Certified Critical Care Nurse — Obtained 2022', s['B']))
    st.append(Paragraph('<b>TNCC:</b> Trauma Nursing Core Course — Expires 09/2025', s['B']))

    st += sec('CLINICAL EXPERIENCE', s)
    st += job('Charge Nurse — ICU', 'Houston Methodist Hospital',
              'Mar 2022 — Present', [
        'Lead 12-bed Medical ICU team of 8 RNs and 4 CNAs during 12-hour night shifts',
        'Manage ventilator protocols, arterial lines, and continuous renal replacement therapy (CRRT)',
        'Reduced catheter-associated UTI rate by 40% through evidence-based bundle implementation',
        'Precept and mentor 6 new graduate nurses through 12-week ICU orientation program',
        'Collaborate with physicians on rapid response team — average response time under 3 minutes',
        'Achieved 98.5% patient satisfaction score (Press Ganey) for Q3-Q4 2023',
    ], s)
    st += job('Staff Nurse — Emergency Department', 'Memorial Hermann Texas Medical Center',
              'Jun 2019 — Feb 2022', [
        'Provided emergency care in Level I Trauma Center averaging 85,000 annual visits',
        'Triaged 30-40 patients per shift using ESI triage system',
        'Administered medications, performed wound care, and assisted with procedures including intubation and chest tubes',
        'Served on Falls Prevention Committee — reduced ED fall rate by 25%',
    ], s)
    st += job('New Graduate Nurse — Medical-Surgical', 'St. Luke\'s Health, Houston',
              'Aug 2018 — May 2019', [
        'Managed care for 5-6 patients on 32-bed medical-surgical unit',
        'Documented patient assessments and care plans in Epic EMR system',
    ], s)

    st += sec('EDUCATION', s)
    st += edu('Bachelor of Science in Nursing (BSN)', 'University of Texas Health Science Center at Houston',
              '2014 — 2018', gpa='3.6/4.0', s=s)

    st += sec('SKILLS', s)
    st.append(Paragraph('<b>Clinical:</b> Ventilator management, Hemodynamic monitoring, CRRT, Arterial/Central lines, Blood product administration, Pain management, Wound care', s['B']))
    st.append(Paragraph('<b>Systems:</b> Epic EMR, Cerner, Meditech, Pyxis, Alaris IV pumps', s['B']))
    st.append(Paragraph('<b>Languages:</b> English (Native), Igbo (Fluent), Yoruba (Conversational)', s['B']))

    st += sec('VOLUNTEER', s)
    st.append(Paragraph('• Remote Area Medical — Annual free clinic volunteer (2020-Present)', s['B']))
    st.append(Paragraph('• Nigerian Nurses Association of Houston — Secretary (2021-2023)', s['B']))

    doc.build(st)
    print(f"  ✓ {path}")


# ============================================================
# CV 12: Freelance UX/UI Designer — Portfolio-heavy (Free-form)
# ============================================================
def cv12():
    path = os.path.join(OUT_DIR, "cv12_freelance_designer_freeform.pdf")
    doc = SimpleDocTemplate(path, pagesize=A4, leftMargin=2.5*cm, rightMargin=2.5*cm,
                            topMargin=2*cm, bottomMargin=2*cm)
    s = S()
    s.add(ParagraphStyle('Accent', parent=s['Title'], fontSize=24, leading=28,
                         textColor=HexColor('#6c5ce7'), spaceAfter=2))
    st = []

    st.append(Paragraph('LENA KOWALSKI', s['Accent']))
    st.append(Paragraph('Freelance UX/UI Designer & Design Systems Consultant', s['CT']))
    st.append(Paragraph('lena@kowalski.design | +48 501 234 567 | Warsaw, Poland (Remote-first)', s['CT']))
    st.append(Paragraph('Portfolio: kowalski.design | Dribbble: dribbble.com/lenakow | Behance: behance.net/lenakow', s['CT']))
    st.append(Spacer(1, 10))

    st += sec('ABOUT', s, '#6c5ce7')
    st.append(Paragraph(
        'Independent UX/UI designer with 8 years of experience crafting digital products for '
        'startups and enterprise clients across fintech, healthtech, and e-commerce. Specialized '
        'in design systems, accessibility (WCAG 2.1 AA), and user research. Have designed products '
        'used by 10M+ people. Available for contracts, retainers, and fractional Head of Design roles.', s['B']))

    st += sec('SELECTED PROJECTS', s, '#6c5ce7')
    # Project-based instead of employer-based
    st += job('Design System & Mobile App Redesign', 'Revolut (Contract)',
              'Sep 2023 — Mar 2024 | 7 months', [
        'Redesigned onboarding flow reducing drop-off from 35% to 12% across iOS and Android',
        'Built and documented component library with 120+ components in Figma — adopted by 40 engineers',
        'Conducted 25 user interviews and 3 rounds of usability testing',
        'Collaborated with 4 product teams across London and Krakow offices',
    ], s)
    st += job('Patient Portal UX Overhaul', 'DocPlanner (Contract)',
              'Jan 2023 — Aug 2023 | 8 months', [
        'Redesigned appointment booking flow — conversion increased 28% in A/B test',
        'Created accessibility audit framework ensuring WCAG 2.1 AA compliance',
        'Delivered design system covering web, iOS, and Android platforms',
        'Facilitated 12 design workshops with clinical stakeholders in 3 countries',
    ], s)
    st += job('E-commerce Checkout Optimization', 'Allegro (Contract)',
              'Mar 2022 — Dec 2022 | 10 months', [
        'Reduced checkout abandonment by 18% through streamlined 3-step flow',
        'Designed micro-interactions and loading states improving perceived performance',
        'Built Figma prototypes for A/B testing — 8 experiments shipped',
    ], s)
    st += job('Fintech Dashboard & Data Visualization', 'Cinkciarz.pl (Contract)',
              'Jun 2021 — Feb 2022 | 9 months', [
        'Designed forex trading dashboard displaying real-time data for 200K+ active traders',
        'Created data visualization patterns for complex financial charts',
    ], s)
    st += job('Junior/Mid UX Designer', 'Netguru (Full-time)',
              'Sep 2016 — May 2021', [
        'Worked on 15+ client projects across SaaS, fintech, and IoT domains',
        'Promoted from Junior to Mid Designer within 18 months',
        'Mentored 3 junior designers and led internal design critique sessions',
    ], s)

    st += sec('EDUCATION', s, '#6c5ce7')
    st += edu('M.A. Human-Computer Interaction', 'Warsaw University of Technology',
              '2014 — 2016', s=s)
    st += edu('B.A. Graphic Design', 'Academy of Fine Arts in Warsaw',
              '2010 — 2014', s=s)

    st += sec('TOOLS & SKILLS', s, '#6c5ce7')
    st.append(Paragraph('<b>Design:</b> Figma (Expert), Sketch, Adobe XD, Principle, ProtoPie, Framer', s['B']))
    st.append(Paragraph('<b>Research:</b> UserTesting, Maze, Hotjar, Optimal Workshop, Dovetail', s['B']))
    st.append(Paragraph('<b>Frontend:</b> HTML/CSS, Tailwind CSS, React basics (for prototyping)', s['B']))
    st.append(Paragraph('<b>Other:</b> Notion, Jira, Confluence, Miro, FigJam', s['B']))
    st.append(Paragraph('<b>Languages:</b> Polish (Native), English (C2 — Cambridge CPE), German (B1)', s['B']))

    st += sec('SPEAKING & WRITING', s, '#6c5ce7')
    st.append(Paragraph('• Speaker, Figma Config 2023 — "Scaling Design Systems for Multi-Brand Products"', s['B']))
    st.append(Paragraph('• Guest Author, Smashing Magazine — "Accessible Color Systems" (2022)', s['B']))
    st.append(Paragraph('• Workshop Lead, UX Poland Conference 2022 — "Design Tokens in Practice"', s['B']))

    doc.build(st)
    print(f"  ✓ {path}")


# ============================================================
# CV 13: Career Changer — Teacher→Data Analyst (Free-form)
# Career gap + bootcamp education
# ============================================================
def cv13():
    path = os.path.join(OUT_DIR, "cv13_career_changer_freeform.pdf")
    doc = SimpleDocTemplate(path, pagesize=A4, leftMargin=2*cm, rightMargin=2*cm,
                            topMargin=2*cm, bottomMargin=2*cm)
    s = S()
    st = []

    st.append(Paragraph('RACHEL THOMPSON', s['N1']))
    st.append(Paragraph('rachel.thompson@email.com | +1 (503) 555-0167 | Portland, OR', s['CT']))
    st.append(Paragraph('LinkedIn: linkedin.com/in/rachelthompson-data | GitHub: github.com/rthompson-data', s['CT']))
    st.append(Spacer(1, 8))

    st += sec('PROFILE', s)
    st.append(Paragraph(
        'Former high school math teacher transitioning into data analytics after completing an '
        'intensive 6-month data science bootcamp. Strong foundation in statistics, data '
        'visualization, and SQL from 5 years of teaching AP Statistics and developing data-driven '
        'student performance tracking systems. Passionate about using data to solve real-world '
        'problems. Currently seeking entry-level Data Analyst roles.', s['B']))

    st += sec('EDUCATION & TRAINING', s)
    st += edu('Data Science Bootcamp Certificate', 'General Assembly (Full-time, 480 hours)',
              'Jan 2024 — Jun 2024', s=s)
    st.append(Paragraph('Curriculum: Python, SQL, Pandas, Tableau, Machine Learning, A/B Testing, Statistical Modeling', s['SM']))
    st.append(Spacer(1, 4))
    st += edu('M.Ed. Mathematics Education', 'Portland State University',
              '2017 — 2019', gpa='3.9/4.0', s=s)
    st += edu('B.S. Mathematics', 'University of Oregon',
              '2013 — 2017', gpa='3.5/4.0', s=s)

    st += sec('DATA PROJECTS (BOOTCAMP & PERSONAL)', s)
    st += job('Customer Churn Prediction Model', 'Bootcamp Capstone Project',
              'May 2024 — Jun 2024', [
        'Built logistic regression and random forest models predicting telecom customer churn with 87% accuracy',
        'Cleaned and analyzed dataset of 7,000+ customer records using Python (Pandas, scikit-learn)',
        'Created interactive Tableau dashboard for stakeholder presentation',
        'Presented findings to panel of 3 industry mentors — received highest cohort score',
    ], s)
    st += job('Portland Housing Market Analysis', 'Personal Project',
              'Mar 2024', [
        'Scraped 15,000+ listings from Zillow API and performed EDA with Pandas and Matplotlib',
        'Built linear regression model identifying top predictors of sale price (R² = 0.82)',
        'Published analysis as Jupyter notebook on GitHub — 45 stars',
    ], s)
    st += job('Student Performance Tracking Dashboard', 'Built during teaching career',
              '2021 — 2023', [
        'Designed Excel/Google Sheets system tracking 150+ students across 6 metrics',
        'Used pivot tables and conditional formatting to identify at-risk students 3 weeks earlier',
        'Adopted by 4 other math teachers in the department',
    ], s)

    st += sec('TEACHING EXPERIENCE', s)
    st += job('High School Mathematics Teacher', 'Lincoln High School, Portland, OR',
              'Aug 2019 — Dec 2023', [
        'Taught AP Statistics, Algebra II, and Pre-Calculus to 120+ students annually',
        'Developed data literacy curriculum incorporating real-world datasets and Python notebooks',
        'Improved AP Statistics pass rate from 62% to 84% over 3 years',
        'Led after-school "Data Club" introducing students to Python and data visualization',
    ], s)

    st += sec('CAREER GAP NOTE', s)
    st.append(Paragraph(
        '<i>Jan 2024 — Jun 2024: Full-time enrollment in General Assembly Data Science Bootcamp '
        '(listed above in Education). No employment during this period.</i>', s['SM']))

    st += sec('TECHNICAL SKILLS', s)
    st.append(Paragraph('<b>Languages:</b> Python, SQL, R (basic)', s['B']))
    st.append(Paragraph('<b>Libraries:</b> Pandas, NumPy, scikit-learn, Matplotlib, Seaborn, BeautifulSoup', s['B']))
    st.append(Paragraph('<b>Tools:</b> Tableau, Google Sheets (Advanced), Excel (Advanced), Jupyter, Git', s['B']))
    st.append(Paragraph('<b>Databases:</b> PostgreSQL, SQLite, BigQuery', s['B']))
    st.append(Paragraph('<b>Certifications:</b> Google Data Analytics Professional Certificate (2024)', s['B']))

    doc.build(st)
    print(f"  ✓ {path}")


# ============================================================
# CV 14: Electrician / Trades — with licenses (Free-form)
# ============================================================
def cv14():
    path = os.path.join(OUT_DIR, "cv14_electrician_trades_freeform.pdf")
    doc = SimpleDocTemplate(path, pagesize=A4, leftMargin=2*cm, rightMargin=2*cm,
                            topMargin=2*cm, bottomMargin=2*cm)
    s = S()
    st = []

    st.append(Paragraph('MARCUS JAMES WILSON', s['N1']))
    st.append(Paragraph('Licensed Master Electrician', s['CT']))
    st.append(Paragraph('marcus.wilson@email.com | +1 (312) 555-0289 | Chicago, IL 60614', s['CT']))
    st.append(Spacer(1, 8))

    st += sec('PROFESSIONAL SUMMARY', s)
    st.append(Paragraph(
        'Illinois Licensed Master Electrician with 14 years of experience in commercial, '
        'industrial, and residential electrical systems. Expertise in high-voltage installations, '
        'PLC programming, fire alarm systems, and renewable energy. Managed crews of up to 20 '
        'electricians on projects valued at $15M+. OSHA 30 certified with zero lost-time '
        'incidents over entire career. Currently seeking Electrical Superintendent role.', s['B']))

    st += sec('LICENSES & CERTIFICATIONS', s)
    certs = [
        ['Illinois Master Electrician License', '#ME-2018-04523', 'Active — Exp 06/2026'],
        ['OSHA 30-Hour Construction Safety', 'Card #A1234567', 'Completed 2020'],
        ['NFPA 70E Arc Flash Safety', '', 'Completed 2023'],
        ['EPA Section 608 Universal', '#6789012', 'Active'],
        ['First Aid / CPR / AED', 'American Red Cross', 'Exp 11/2025'],
        ['NABCEP PV Installation Professional', '#PV-2022-8901', 'Active'],
    ]
    data = [['Certification', 'Number/Issuer', 'Status']] + certs
    t = Table(data, colWidths=[7*cm, 5*cm, 5*cm])
    t.setStyle(TableStyle([
        ('FONTSIZE', (0,0), (-1,-1), 9),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('BACKGROUND', (0,0), (-1,0), HexColor('#e8e8e8')),
        ('GRID', (0,0), (-1,-1), 0.5, HexColor('#cccccc')),
        ('TOPPADDING', (0,0), (-1,-1), 3),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3),
    ]))
    st.append(t)
    st.append(Spacer(1, 6))

    st += sec('WORK EXPERIENCE', s)
    st += job('Electrical Foreman / Project Lead', 'PowerGrid Electric, Inc., Chicago',
              'Apr 2018 — Present', [
        'Supervise crew of 12-20 electricians on commercial projects ($2M-$15M value)',
        'Led electrical installation for 22-story mixed-use development — 800+ units, completed on schedule',
        'Install and program Allen-Bradley PLCs for industrial motor control systems',
        'Coordinate with GCs, inspectors, and engineers — pass rate: 100% on first inspection',
        'Manage material procurement and inventory ($500K+ per project)',
        'Train and mentor 8 apprentices through IBEW Local 134 program',
    ], s)
    st += job('Journeyman Electrician', 'Kelso Electric Company, Chicago',
              'Sep 2013 — Mar 2018', [
        'Performed commercial and industrial electrical installations per NEC code',
        'Installed fire alarm and emergency lighting systems in 50+ buildings',
        'Pulled wire, bent conduit, and terminated panels for 480V/277V 3-phase systems',
        'Read and interpreted blueprints, schematics, and single-line diagrams',
    ], s)
    st += job('Electrical Apprentice', 'IBEW Local 134 Apprenticeship, Chicago',
              'Jun 2010 — Aug 2013', [
        'Completed 8,000+ hours of on-the-job training and 900 classroom hours',
        'Rotated through residential, commercial, and industrial job sites',
    ], s)

    st += sec('EDUCATION', s)
    st += edu('Electrical Apprenticeship Completion Certificate', 'IBEW Local 134 / JATC Chicago',
              '2010 — 2013', s=s)
    st += edu('Associate of Applied Science — Electrical Technology', 'Washburne Trade School, Chicago',
              '2008 — 2010', s=s)

    st += sec('SKILLS', s)
    st.append(Paragraph('<b>Electrical:</b> 480V/277V 3-phase, Motor controls, VFDs, Transformers, Switchgear, Panel building, Fire alarm (NICET), Conduit bending, Cable tray', s['B']))
    st.append(Paragraph('<b>Controls:</b> Allen-Bradley PLC, Siemens, Ladder logic, HMI programming', s['B']))
    st.append(Paragraph('<b>Solar:</b> PV system design and installation, Inverters, Battery storage, Net metering', s['B']))
    st.append(Paragraph('<b>Software:</b> AutoCAD Electrical, Bluebeam, Procore, PlanGrid', s['B']))
    st.append(Paragraph('<b>Union:</b> IBEW Local 134 member since 2010', s['B']))

    doc.build(st)
    print(f"  ✓ {path}")


# ============================================================
# CV 15: Executive Chef — Hospitality (Free-form)
# ============================================================
def cv15():
    path = os.path.join(OUT_DIR, "cv15_chef_hospitality_freeform.pdf")
    doc = SimpleDocTemplate(path, pagesize=A4, leftMargin=2.5*cm, rightMargin=2.5*cm,
                            topMargin=2*cm, bottomMargin=2*cm)
    s = S()
    s.add(ParagraphStyle('ChefName', parent=s['Title'], fontSize=24, leading=28,
                         textColor=HexColor('#8B0000'), spaceAfter=2))
    st = []

    st.append(Paragraph('JEAN-PIERRE MOREAU', s['ChefName']))
    st.append(Paragraph('Executive Chef | Michelin-experienced | French & Asian Fusion', s['CT']))
    st.append(Paragraph('jp.moreau@email.com | +33 6 12 34 56 78 | Paris, France', s['CT']))
    st.append(Paragraph('Instagram: @chefjpmoreau (45K followers)', s['CT']))
    st.append(Spacer(1, 8))

    st += sec('CULINARY PHILOSOPHY', s, '#8B0000')
    st.append(Paragraph(
        'Classically trained French chef with 16 years of experience across Michelin-starred '
        'restaurants in Paris, Tokyo, and Singapore. Specialist in French-Asian fusion cuisine '
        'with emphasis on seasonal ingredients and sustainable sourcing. Led kitchens generating '
        '€3.5M+ annual revenue. Seeking Executive Chef or Culinary Director position at a '
        'fine-dining or luxury hotel group.', s['B']))

    st += sec('RESTAURANT EXPERIENCE', s, '#8B0000')
    st += job('Executive Chef', 'Le Jardin Caché (1 Michelin Star), Paris',
              'Jan 2021 — Present', [
        'Lead kitchen brigade of 18 cooks across 65-cover fine-dining restaurant',
        'Achieved Michelin star within 14 months of opening — maintained for 3 consecutive years',
        'Design seasonal tasting menus (8-course) with 95% ingredient sourcing from Île-de-France farms',
        'Manage food cost at 28% while maintaining premium quality — annual revenue €3.5M',
        'Train and develop sous chefs — 3 have gone on to lead their own kitchens',
        'Implemented zero-waste program reducing kitchen waste by 60%',
    ], s)
    st += job('Head Chef', 'Nobu Singapore (Capella Hotel)',
              'Mar 2017 — Dec 2020', [
        'Managed kitchen operations for 120-seat Japanese-Peruvian restaurant',
        'Developed signature dishes adopted across 3 Nobu APAC locations',
        'Oversaw banquet operations for events up to 500 guests',
        'Maintained food safety rating: Grade A (Singapore Food Agency) — all 4 years',
    ], s)
    st += job('Chef de Partie → Sous Chef', 'L\'Atelier de Joël Robuchon (2 Michelin Stars), Tokyo',
              'Sep 2012 — Feb 2017', [
        'Promoted from Chef de Partie to Sous Chef within 2.5 years',
        'Managed fish and sauce stations for 80-cover counter-dining concept',
        'Developed plating standards and trained 6 commis chefs',
    ], s)
    st += job('Commis Chef', 'Le Bristol Paris (3 Michelin Stars)',
              'Jun 2008 — Aug 2012', [
        'Trained under Chef Éric Frechon across all kitchen stations',
        'Assisted with pastry, garde manger, and hot appetizer sections',
    ], s)

    st += sec('EDUCATION', s, '#8B0000')
    st += edu('Diplôme de Cuisine (Grand Diplôme)', 'Le Cordon Bleu, Paris',
              '2006 — 2008', s=s)
    st += edu('Baccalauréat Professionnel — Restauration', 'Lycée Hôtelier Jean Drouant, Paris',
              '2003 — 2006', s=s)

    st += sec('CERTIFICATIONS', s, '#8B0000')
    st.append(Paragraph('• HACCP Level 4 — Advanced Food Safety Management (2023)', s['B']))
    st.append(Paragraph('• Certified Sommelier — Court of Master Sommeliers (2019)', s['B']))
    st.append(Paragraph('• ServSafe Manager Certification (2018)', s['B']))

    st += sec('LANGUAGES & COMPETITIONS', s, '#8B0000')
    st.append(Paragraph('<b>Languages:</b> French (Native), English (Fluent), Japanese (Conversational — JLPT N3)', s['B']))
    st.append(Paragraph('<b>Competitions:</b> Bocuse d\'Or France Finalist (2020), San Pellegrino Young Chef SEA Semifinalist (2016)', s['B']))

    st += sec('MEDIA & PUBLICATIONS', s, '#8B0000')
    st.append(Paragraph('• Featured in "50 Best Discovery" — World\'s 50 Best Restaurants (2023)', s['B']))
    st.append(Paragraph('• Author: "Fusion Naturelle" — recipe book, Éditions de La Martinière (2022)', s['B']))
    st.append(Paragraph('• Guest Judge — MasterChef France Season 14 (2 episodes, 2023)', s['B']))

    doc.build(st)
    print(f"  ✓ {path}")


# ============================================================
# CV 16: Lawyer — with bar admissions (Free-form)
# ============================================================
def cv16():
    path = os.path.join(OUT_DIR, "cv16_lawyer_legal_freeform.pdf")
    doc = SimpleDocTemplate(path, pagesize=A4, leftMargin=2*cm, rightMargin=2*cm,
                            topMargin=2*cm, bottomMargin=2*cm)
    s = S()
    st = []

    st.append(Paragraph('PRIYA SHARMA, J.D.', s['N1']))
    st.append(Paragraph('Corporate & M&A Attorney', s['CT']))
    st.append(Paragraph('priya.sharma@email.com | +1 (646) 555-0312 | New York, NY', s['CT']))
    st.append(Paragraph('LinkedIn: linkedin.com/in/priyasharma-esq', s['CT']))
    st.append(Spacer(1, 8))

    st += sec('BAR ADMISSIONS', s)
    st.append(Paragraph('• New York State Bar — Admitted November 2015', s['B']))
    st.append(Paragraph('• District of Columbia Bar — Admitted March 2016', s['B']))
    st.append(Paragraph('• U.S. District Court, Southern District of New York — Admitted 2017', s['B']))

    st += sec('PROFESSIONAL SUMMARY', s)
    st.append(Paragraph(
        'Corporate attorney with 9 years of experience in M&A transactions, private equity, '
        'and securities law. Have advised on 40+ transactions totaling $12B+ in aggregate deal '
        'value. Currently Senior Associate at a top-tier international law firm. Strong background '
        'in cross-border transactions with India, Southeast Asia, and Middle East deal experience. '
        'Dual-qualified in New York and D.C.', s['B']))

    st += sec('LEGAL EXPERIENCE', s)
    st += job('Senior Associate — Corporate / M&A', 'Davis Polk & Wardwell LLP, New York',
              'Jan 2020 — Present', [
        'Lead associate on M&A transactions ranging from $50M to $3.2B in technology and healthcare sectors',
        'Advised PE firm on $2.1B leveraged buyout of SaaS company — managed due diligence workstream',
        'Draft and negotiate SPAs, merger agreements, stockholder agreements, and ancillary documents',
        'Supervise team of 3-5 junior associates and coordinate with local counsel in 6 jurisdictions',
        'Advise public company boards on fiduciary duties, proxy contests, and activist defense',
        'Selected for firm-wide Diversity Leadership Council (2022-Present)',
    ], s)
    st += job('Associate — Corporate / M&A', 'Skadden, Arps, Slate, Meagher & Flom LLP, New York',
              'Sep 2015 — Dec 2019', [
        'Worked on 25+ M&A and private equity transactions across technology, retail, and energy sectors',
        'Drafted SEC filings including S-1 registration statements and 8-K current reports',
        'Assisted with $800M SPAC merger — one of the first SPAC deals in the fintech space',
        'Conducted antitrust analysis and HSR filing preparation',
    ], s)
    st += job('Summer Associate', 'Skadden, Arps, Slate, Meagher & Flom LLP, New York',
              'Jun 2014 — Aug 2014', [
        'Researched Delaware corporate law issues and drafted memos on fiduciary duty standards',
    ], s)

    st += sec('EDUCATION', s)
    st += edu('Juris Doctor (J.D.)', 'Columbia Law School',
              '2012 — 2015', s=s)
    st.append(Paragraph('Law Review Editor | Harlan Fiske Stone Scholar (Top 15%)', s['SM']))
    st.append(Spacer(1, 4))
    st += edu('B.A. Economics (Summa Cum Laude)', 'University of Michigan, Ann Arbor',
              '2008 — 2012', gpa='3.93/4.0', s=s)

    st += sec('PUBLICATIONS & SPEAKING', s)
    st.append(Paragraph('• "Cross-Border M&A in the Age of Data Privacy Regulation" — Columbia Business Law Review, 2023', s['B']))
    st.append(Paragraph('• Panelist, ABA M&A Conference — "AI Due Diligence in Tech Transactions" (2024)', s['B']))
    st.append(Paragraph('• CLE Instructor — "SPAC Transactions: Structures and Pitfalls" (PLI, 2021)', s['B']))

    st += sec('LANGUAGES', s)
    st.append(Paragraph('English (Native), Hindi (Fluent), Punjabi (Conversational)', s['B']))

    st += sec('PRO BONO', s)
    st.append(Paragraph('• Legal Aid Society — Represented 5 tenants in housing court (2020-2023)', s['B']))
    st.append(Paragraph('• International Refugee Assistance Project — 3 asylum cases (2017-2019)', s['B']))

    doc.build(st)
    print(f"  ✓ {path}")


# ============================================================
# CV 17: Middle East Format — with visa status (Free-form)
# ============================================================
def cv17():
    path = os.path.join(OUT_DIR, "cv17_civil_engineer_middleeast_freeform.pdf")
    doc = SimpleDocTemplate(path, pagesize=A4, leftMargin=2*cm, rightMargin=2*cm,
                            topMargin=2*cm, bottomMargin=2*cm)
    s = S()
    st = []

    st.append(Paragraph('AHMED HASSAN AL-RASHIDI', s['N1']))
    st.append(Paragraph('Senior Civil Engineer — Infrastructure & Roads', s['CT']))
    st.append(Spacer(1, 4))

    # Middle East style: personal info in table
    info = [
        ['Full Name:', 'Ahmed Hassan Al-Rashidi', 'Nationality:', 'Jordanian'],
        ['Date of Birth:', '12/04/1987', 'Gender:', 'Male'],
        ['Marital Status:', 'Married', 'Dependents:', '3'],
        ['Passport No:', 'J12345678', 'Visa Status:', 'UAE Golden Visa (10-year)'],
        ['Mobile:', '+971 50 123 4567', 'Email:', 'ahmed.rashidi@email.com'],
        ['Address:', 'Al Reem Island, Abu Dhabi, UAE', 'Driving License:', 'UAE & Jordan (Valid)'],
    ]
    t = Table(info, colWidths=[3.5*cm, 5*cm, 3.5*cm, 5*cm])
    t.setStyle(TableStyle([
        ('FONTSIZE', (0,0), (-1,-1), 9),
        ('FONTNAME', (0,0), (0,-1), 'Helvetica-Bold'),
        ('FONTNAME', (2,0), (2,-1), 'Helvetica-Bold'),
        ('GRID', (0,0), (-1,-1), 0.5, HexColor('#cccccc')),
        ('TOPPADDING', (0,0), (-1,-1), 3),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3),
        ('LEFTPADDING', (0,0), (-1,-1), 4),
    ]))
    st.append(t)
    st.append(Spacer(1, 8))

    st += sec('CAREER OBJECTIVE', s)
    st.append(Paragraph(
        'Senior civil engineer with 12+ years of experience in highway design, infrastructure '
        'development, and project management across the GCC region. Managed projects worth '
        'AED 500M+ for government and semi-government clients. Seeking Project Director or '
        'Engineering Manager position with a leading consultancy or contractor.', s['B']))

    st += sec('PROFESSIONAL EXPERIENCE', s)
    st += job('Senior Civil Engineer', 'Parsons International, Abu Dhabi, UAE',
              'Mar 2019 — Present', [
        'Lead design team of 8 engineers on AED 350M highway interchange project for DoT Abu Dhabi',
        'Design geometric alignments, pavement structures, and drainage systems per Abu Dhabi UPC standards',
        'Coordinate with traffic, structural, and utility teams on integrated design packages',
        'Review contractor RFIs and shop drawings — average turnaround 3 working days',
        'Manage project schedule using Primavera P6 — currently tracking 2 weeks ahead of baseline',
    ], s)
    st += job('Civil Engineer', 'Dar Al-Handasah (Shair & Partners), Riyadh, KSA',
              'Jun 2015 — Feb 2019', [
        'Designed road networks and site grading for NEOM early works packages',
        'Prepared tender documents and BOQs for infrastructure projects valued at SAR 200M+',
        'Conducted site inspections and supervised earthwork operations',
    ], s)
    st += job('Junior Civil Engineer', 'Arab Engineering Consultants, Amman, Jordan',
              'Sep 2012 — May 2015', [
        'Assisted with highway design and municipal infrastructure projects',
        'Performed hydrological analysis and storm water drainage design',
        'Prepared AutoCAD drawings and quantity takeoffs',
    ], s)

    st += sec('EDUCATION', s)
    st += edu('M.Sc. Transportation Engineering', 'University of Jordan, Amman',
              '2010 — 2012', gpa='3.75/4.0 (Distinction)', s=s)
    st += edu('B.Sc. Civil Engineering', 'Jordan University of Science and Technology, Irbid',
              '2005 — 2009', gpa='3.4/4.0 (Very Good)', s=s)

    st += sec('PROFESSIONAL REGISTRATIONS & CERTIFICATIONS', s)
    st.append(Paragraph('• Chartered Engineer (CEng) — Institution of Civil Engineers (ICE), UK — 2020', s['B']))
    st.append(Paragraph('• Licensed Engineer — Jordan Engineers Association (JEA) #45678 — 2012', s['B']))
    st.append(Paragraph('• PMP — Project Management Professional (PMI) #3456789 — 2021', s['B']))
    st.append(Paragraph('• NEBOSH IGC — Occupational Health & Safety — 2019', s['B']))

    st += sec('TECHNICAL SKILLS', s)
    st.append(Paragraph('<b>Design Software:</b> AutoCAD Civil 3D, MicroStation, OpenRoads Designer, HEC-RAS, EPANET', s['B']))
    st.append(Paragraph('<b>Project Mgmt:</b> Primavera P6, MS Project, Aconex, Procore', s['B']))
    st.append(Paragraph('<b>Standards:</b> Abu Dhabi UPC, AASHTO, Aramco Standards, MOMRA, BS EN', s['B']))
    st.append(Paragraph('<b>Languages:</b> Arabic (Native), English (Fluent — IELTS 7.5)', s['B']))

    doc.build(st)
    print(f"  ✓ {path}")


# ============================================================
# CV 18: Gig Worker — Multiple short stints (Free-form)
# Many entries, diverse roles
# ============================================================
def cv18():
    path = os.path.join(OUT_DIR, "cv18_gig_worker_freeform.pdf")
    doc = SimpleDocTemplate(path, pagesize=A4, leftMargin=2*cm, rightMargin=2*cm,
                            topMargin=1.5*cm, bottomMargin=1.5*cm)
    s = S()
    st = []

    st.append(Paragraph('TOMOKO HAYASHI', s['N1']))
    st.append(Paragraph('Content Creator | Translator | Virtual Assistant', s['CT']))
    st.append(Paragraph('tomoko.hayashi@email.com | +81 80-9876-5432 | Osaka, Japan', s['CT']))
    st.append(Paragraph('Upwork: upwork.com/fl/tomokoh | Fiverr: fiverr.com/tomoko_writes', s['CT']))
    st.append(Spacer(1, 6))

    st += sec('PROFILE', s)
    st.append(Paragraph(
        'Versatile freelancer with 5 years of experience across content writing, '
        'Japanese-English translation, and virtual assistance. Completed 300+ projects on '
        'Upwork (Top Rated Plus, 99% Job Success) and Fiverr (Level 2 Seller). '
        'Specializing in technology content, SaaS documentation, and localization. '
        'Seeking a full-time remote Content Strategist or Localization Manager role.', s['B']))

    st += sec('FREELANCE EXPERIENCE', s)
    st += job('Senior Content Writer', 'Upwork — Various Clients (Remote)',
              'Apr 2021 — Present', [
        'Write blog posts, whitepapers, and case studies for SaaS companies (Notion, Loom, Miro clients)',
        'Produce 15-20 articles per month averaging 1,500-3,000 words each',
        'Top Rated Plus freelancer — 99% Job Success Score, $85K+ total earnings',
    ], s)
    st += job('Japanese-English Translator', 'Fiverr & Direct Clients',
              'Jan 2020 — Present', [
        'Translate technical documentation, marketing materials, and UI strings (JA↔EN)',
        'Localized mobile apps for 3 startups — total 50,000+ words translated',
        'Level 2 Seller on Fiverr with 450+ five-star reviews',
    ], s)
    st += job('Virtual Assistant', 'Various Startups (Remote)',
              'Jun 2019 — Mar 2021', [
        'Managed calendars, email inbox, and travel arrangements for 4 startup founders',
        'Created SOPs and managed Notion workspaces for 3 early-stage companies',
        'Handled customer support tickets (Zendesk, Intercom) — avg first response: 15 min',
    ], s)
    st += job('Content Intern', 'Rakuten, Osaka',
              'Apr 2019 — May 2019 (2 months)', [
        'Wrote product descriptions for Rakuten Ichiba marketplace in English',
    ], s)

    # Short contract gigs
    st += sec('SHORT-TERM CONTRACTS', s)
    short_gigs = [
        ['Client / Company', 'Role', 'Duration', 'Output'],
        ['Mercari (Tokyo)', 'Localization QA', 'Oct — Dec 2023', '12,000 strings reviewed'],
        ['LINE Corp', 'Content Writer', 'Jul — Sep 2022', '25 help center articles'],
        ['SmartNews', 'Translation (EN→JA)', 'Mar — Apr 2022', '30,000 words'],
        ['Wantedly', 'Copywriter', 'Jan — Feb 2022', 'Landing page + 10 blog posts'],
        ['Cookpad', 'Translation (JA→EN)', 'Nov 2021', '15,000 words'],
        ['Freee K.K.', 'Technical Writer', 'Aug — Sep 2021', 'API documentation (20 pages)'],
    ]
    t = Table(short_gigs, colWidths=[4.5*cm, 3.5*cm, 3.5*cm, 5.5*cm])
    t.setStyle(TableStyle([
        ('FONTSIZE', (0,0), (-1,-1), 8),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('BACKGROUND', (0,0), (-1,0), HexColor('#e8e8e8')),
        ('GRID', (0,0), (-1,-1), 0.5, HexColor('#cccccc')),
        ('TOPPADDING', (0,0), (-1,-1), 3),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3),
    ]))
    st.append(t)
    st.append(Spacer(1, 6))

    st += sec('EDUCATION', s)
    st += edu('B.A. English Literature', 'Osaka University', '2015 — 2019', gpa='3.3/4.0', s=s)

    st += sec('SKILLS', s)
    st.append(Paragraph('<b>Writing:</b> Blog posts, Whitepapers, Case studies, UX copy, API docs, SEO content', s['B']))
    st.append(Paragraph('<b>Translation:</b> Japanese ↔ English (CAT tools: SDL Trados, memoQ, Memsource)', s['B']))
    st.append(Paragraph('<b>Tools:</b> Notion, Slack, Asana, Canva, WordPress, Google Workspace, Figma', s['B']))
    st.append(Paragraph('<b>Languages:</b> Japanese (Native), English (TOEIC 950, EIKEN Grade 1)', s['B']))

    doc.build(st)
    print(f"  ✓ {path}")


# ============================================================
# CV 19: Military Veteran Transitioning — with ranks (Org Form)
# ============================================================
def cv19():
    path = os.path.join(OUT_DIR, "cv19_military_veteran_form.pdf")
    c = canvas.Canvas(path, pagesize=A4)
    w, h = A4

    def sec_header(c, text, x, y, width):
        c.setFillColor(HexColor('#1B3A4B'))
        c.rect(x, y - 4, width, 18, fill=1, stroke=0)
        c.setFillColor(white)
        c.setFont("Helvetica-Bold", 10)
        c.drawString(x + 6, y, text)
        c.setFillColor(black)

    def field(c, label, value, x, y, lw=130, vw=350):
        c.setFont("Helvetica-Bold", 9)
        c.drawString(x, y, label)
        c.setFont("Helvetica", 10)
        c.drawString(x + lw, y, value)
        c.line(x + lw, y - 2, x + lw + vw, y - 2)

    # Header
    c.setFont("Helvetica-Bold", 15)
    c.drawCentredString(w/2, h - 35, "VETERAN CAREER TRANSITION PROFILE")
    c.setFont("Helvetica", 8)
    c.drawCentredString(w/2, h - 50, "Prepared for: Defense Talent Network | Form VET-2024-CT")
    c.line(30, h - 58, w - 30, h - 58)

    y = h - 80
    sec_header(c, "PERSONAL INFORMATION", 30, y, w - 60)
    y -= 28
    field(c, "Full Name:", "DANIEL JAMES O'BRIEN", 40, y)
    y -= 20
    field(c, "Email:", "daniel.obrien.vet@email.com", 40, y, 130, 140)
    c.setFont("Helvetica-Bold", 9); c.drawString(330, y, "Phone:")
    c.setFont("Helvetica", 10); c.drawString(380, y, "+1 (910) 555-0423")
    y -= 20
    field(c, "Location:", "Fayetteville, NC 28301", 40, y, 130, 140)
    c.setFont("Helvetica-Bold", 9); c.drawString(330, y, "Clearance:")
    c.setFont("Helvetica", 10); c.drawString(410, y, "Secret (Active)")
    y -= 20
    field(c, "LinkedIn:", "linkedin.com/in/danielobrien-vet", 40, y)

    y -= 30
    sec_header(c, "MILITARY SERVICE RECORD", 30, y, w - 60)
    y -= 25
    mil_data = [
        ['Branch:', 'United States Army', 'Service Dates:', 'Jun 2006 — Sep 2024'],
        ['Final Rank:', 'Sergeant First Class (E-7)', 'MOS:', '25B — IT Specialist'],
        ['Years of Service:', '18 years 3 months', 'Discharge:', 'Honorable'],
        ['Security Clearance:', 'Secret (Active until 2029)', 'VA Disability:', '30%'],
    ]
    c.setFont("Helvetica", 9)
    for row in mil_data:
        c.setFont("Helvetica-Bold", 9)
        c.drawString(40, y, row[0])
        c.setFont("Helvetica", 9)
        c.drawString(160, y, row[1])
        c.setFont("Helvetica-Bold", 9)
        c.drawString(330, y, row[2])
        c.setFont("Helvetica", 9)
        c.drawString(440, y, row[3])
        y -= 16

    y -= 20
    sec_header(c, "KEY ASSIGNMENTS", 30, y, w - 60)
    y -= 22
    assignments = [
        ["2020 — 2024", "Senior IT NCO, XVIII Airborne Corps, Fort Liberty, NC",
         "Managed network infrastructure for 4,000+ users; led team of 12 IT specialists; "
         "deployed and maintained tactical communication systems for 3 brigade-level exercises"],
        ["2016 — 2020", "IT Section Chief, 2nd Infantry Division, Camp Humphreys, South Korea",
         "Supervised network operations center supporting 8,000 users; maintained 99.8% uptime "
         "on classified and unclassified networks; trained 25 junior soldiers"],
        ["2012 — 2016", "Network Administrator, 82nd Airborne Division, Fort Liberty, NC",
         "Administered Windows Server, Active Directory, and Cisco switches/routers for "
         "battalion-level operations; deployed to Afghanistan (2013-2014)"],
        ["2006 — 2012", "IT Specialist, Various Units",
         "Help desk technician and network cable installer; completed initial training and "
         "first overseas assignment to Germany"],
    ]
    for dates, title, desc in assignments:
        c.setFont("Helvetica-Bold", 9)
        c.drawString(40, y, dates)
        c.setFont("Helvetica-Bold", 9)
        c.drawString(120, y, title)
        y -= 14
        # Wrap description
        c.setFont("Helvetica", 8)
        words = desc.split()
        line = ""
        for word in words:
            test = line + " " + word if line else word
            if c.stringWidth(test, "Helvetica", 8) > w - 100:
                c.drawString(50, y, line)
                y -= 11
                line = word
            else:
                line = test
        if line:
            c.drawString(50, y, line)
            y -= 16

    y -= 10
    sec_header(c, "EDUCATION & MILITARY TRAINING", 30, y, w - 60)
    y -= 22
    c.setFont("Helvetica", 9)
    ed_items = [
        "B.S. Information Technology — American Military University (AMU) — 2018 — GPA: 3.6/4.0",
        "A.A.S. Computer Information Systems — Central Texas College — 2014",
        "Advanced Leaders Course (ALC) — Fort Gordon, GA — 2016",
        "CompTIA Security+ CE — #CS-0012345 — Active through 2027",
        "CompTIA Network+ — #N-0067890 — Active through 2026",
        "Cisco CCNA — #CSCO14567890 — Obtained 2019",
        "ITIL v4 Foundation — 2020",
        "Army Warrior Leader Course (WLC) — 2012",
    ]
    for item in ed_items:
        c.drawString(40, y, item)
        y -= 14

    y -= 10
    sec_header(c, "TECHNICAL SKILLS (Civilian Equivalent)", 30, y, w - 60)
    y -= 22
    c.setFont("Helvetica", 9)
    c.drawString(40, y, "Networking: Cisco IOS, TCP/IP, VPN, VLAN, DNS, DHCP, firewall administration")
    y -= 14
    c.drawString(40, y, "Systems: Windows Server 2016/2019, Active Directory, Group Policy, SCCM, VMware")
    y -= 14
    c.drawString(40, y, "Security: SIEM (Splunk), vulnerability scanning (Nessus), IDS/IPS, PKI, DISA STIGs")
    y -= 14
    c.drawString(40, y, "Cloud: AWS (Solutions Architect Associate in progress), Azure fundamentals")
    y -= 14
    c.drawString(40, y, "Tools: ServiceNow, Jira, Remedy, SolarWinds, Wireshark")

    y -= 25
    sec_header(c, "AWARDS & DECORATIONS", 30, y, w - 60)
    y -= 22
    c.setFont("Helvetica", 9)
    awards = [
        "Meritorious Service Medal (2x)", "Army Commendation Medal (4x)",
        "Army Achievement Medal (6x)", "Afghanistan Campaign Medal",
        "Korean Defense Service Medal", "NCO of the Year — XVIII Airborne Corps (2022)",
    ]
    c.drawString(40, y, " | ".join(awards[:3]))
    y -= 14
    c.drawString(40, y, " | ".join(awards[3:]))

    y -= 25
    c.setFont("Helvetica-Bold", 9)
    c.drawString(40, y, "TARGET CIVILIAN ROLES:")
    c.setFont("Helvetica", 9)
    c.drawString(190, y, "IT Manager, Network Engineer, Cybersecurity Analyst, Systems Administrator")

    c.save()
    print(f"  ✓ {path}")


# ============================================================
# CV 20: Nonprofit / Social Work — with volunteer heavy (Org Form)
# ============================================================
def cv20():
    path = os.path.join(OUT_DIR, "cv20_nonprofit_social_worker_form.pdf")
    doc = SimpleDocTemplate(path, pagesize=A4, leftMargin=1.5*cm, rightMargin=1.5*cm,
                            topMargin=1.5*cm, bottomMargin=1.5*cm)
    s = S()
    s.add(ParagraphStyle('OrgHead', parent=s['Heading2'], fontSize=11,
                         textColor=HexColor('#2E7D32'), spaceBefore=8, spaceAfter=6))
    st = []

    st.append(Paragraph('<b>GLOBAL HOPE FOUNDATION</b>',
        ParagraphStyle('Org', parent=s['Normal'], fontSize=12, alignment=TA_CENTER,
                       textColor=HexColor('#2E7D32'))))
    st.append(Paragraph('<b>STAFF APPLICATION FORM</b>',
        ParagraphStyle('OrgTitle', parent=s['Title'], fontSize=14, alignment=TA_CENTER,
                       textColor=HexColor('#1B5E20'), spaceAfter=4)))
    st.append(Paragraph('Form: GHF-HR-2024-APP | Location: Nairobi Regional Office',
        ParagraphStyle('OrgRef', parent=s['Normal'], fontSize=8, alignment=TA_CENTER,
                       textColor=HexColor('#666'), spaceAfter=10)))

    # Personal info table
    st.append(Paragraph('<b>SECTION A: PERSONAL DETAILS</b>', s['OrgHead']))
    data_a = [
        ['Full Name:', 'FATIMA ABDI HASSAN', 'Preferred Name:', 'Fatima Hassan'],
        ['Date of Birth:', '23/07/1990', 'Gender:', 'Female'],
        ['Nationality:', 'Kenyan', 'Country of Origin:', 'Kenya / Somalia (dual heritage)'],
        ['Phone:', '+254 712 345 678', 'Email:', 'fatima.hassan@email.com'],
        ['Current Address:', 'Westlands, Nairobi, Kenya', '', ''],
        ['Passport No:', 'A12345678', 'Work Permit:', 'N/A (Kenyan national)'],
    ]
    ta = Table(data_a, colWidths=[3.5*cm, 5*cm, 3.5*cm, 5*cm])
    ta.setStyle(TableStyle([
        ('FONTSIZE', (0,0), (-1,-1), 9),
        ('FONTNAME', (0,0), (0,-1), 'Helvetica-Bold'),
        ('FONTNAME', (2,0), (2,-1), 'Helvetica-Bold'),
        ('GRID', (0,0), (-1,-1), 0.5, HexColor('#999')),
        ('TOPPADDING', (0,0), (-1,-1), 3),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3),
        ('SPAN', (1,4), (3,4)),
    ]))
    st.append(ta)
    st.append(Spacer(1, 8))

    # Position
    st.append(Paragraph('<b>SECTION B: POSITION APPLIED FOR</b>', s['OrgHead']))
    data_b = [
        ['Position:', 'Program Manager — Education & Youth Empowerment'],
        ['Duty Station:', 'Nairobi with travel to Dadaab, Kakuma, and Turkana (up to 40%)'],
        ['Contract Type:', 'Fixed-term (24 months, renewable)'],
        ['Expected Salary:', 'KES 350,000 — 450,000 per month'],
        ['Available From:', '01/03/2025'],
        ['Reference:', 'GHF-2024-PM-EDU-003'],
    ]
    tb = Table(data_b, colWidths=[4*cm, 13*cm])
    tb.setStyle(TableStyle([
        ('FONTSIZE', (0,0), (-1,-1), 9),
        ('FONTNAME', (0,0), (0,-1), 'Helvetica-Bold'),
        ('GRID', (0,0), (-1,-1), 0.5, HexColor('#999')),
        ('TOPPADDING', (0,0), (-1,-1), 3),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3),
    ]))
    st.append(tb)
    st.append(Spacer(1, 8))

    # Education
    st.append(Paragraph('<b>SECTION C: EDUCATION</b>', s['OrgHead']))
    data_c = [
        ['Degree', 'Field', 'Institution', 'Year', 'Grade'],
        ['M.A.', 'Development Studies', 'University of Nairobi', '2014-2016', 'First Class Honours'],
        ['B.A.', 'Social Work', 'Kenyatta University', '2009-2013', 'Upper Second'],
        ['Diploma', 'Project Management', 'Kenya Institute of Management', '2017', 'Distinction'],
    ]
    tc = Table(data_c, colWidths=[1.5*cm, 3.5*cm, 5*cm, 2.5*cm, 4.5*cm])
    tc.setStyle(TableStyle([
        ('FONTSIZE', (0,0), (-1,-1), 8),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('BACKGROUND', (0,0), (-1,0), HexColor('#e8e8e8')),
        ('GRID', (0,0), (-1,-1), 0.5, HexColor('#999')),
        ('ALIGN', (3,0), (3,-1), 'CENTER'),
        ('TOPPADDING', (0,0), (-1,-1), 3),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3),
    ]))
    st.append(tc)
    st.append(Spacer(1, 8))

    # Work experience
    st.append(Paragraph('<b>SECTION D: PROFESSIONAL EXPERIENCE</b>', s['OrgHead']))
    data_d = [
        ['Period', 'Position', 'Organization', 'Location'],
        ['Jul 2021 — Present', 'Senior Program Officer', 'UNICEF Kenya', 'Nairobi'],
        ['Mar 2018 — Jun 2021', 'Program Coordinator', 'Save the Children International', 'Dadaab, Kenya'],
        ['Jan 2016 — Feb 2018', 'Field Officer', 'International Rescue Committee (IRC)', 'Kakuma, Kenya'],
        ['Jun 2013 — Dec 2015', 'Community Mobilizer', 'Kenya Red Cross Society', 'Garissa, Kenya'],
    ]
    td = Table(data_d, colWidths=[3.5*cm, 4.5*cm, 5.5*cm, 3.5*cm])
    td.setStyle(TableStyle([
        ('FONTSIZE', (0,0), (-1,-1), 8),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('BACKGROUND', (0,0), (-1,0), HexColor('#e8e8e8')),
        ('GRID', (0,0), (-1,-1), 0.5, HexColor('#999')),
        ('TOPPADDING', (0,0), (-1,-1), 3),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3),
    ]))
    st.append(td)
    st.append(Spacer(1, 4))

    st.append(Paragraph('<b>Current Role Key Responsibilities:</b>', s['H2']))
    for b in [
        'Manage $2.5M education portfolio covering 45 primary schools in Turkana and Marsabit counties',
        'Lead team of 8 national staff and coordinate with 3 implementing partners',
        'Design monitoring and evaluation frameworks — developed 15 indicators aligned with SDG 4',
        'Write donor reports for USAID, DFID, and UNICEF HQ (quarterly and annual)',
        'Facilitate community engagement sessions with 500+ parents and local leaders per quarter',
        'Coordinate emergency education response during drought — reached 12,000 children in 2023',
    ]:
        st.append(Paragraph(f'• {b}', s['B']))
    st.append(Spacer(1, 6))

    # Skills & Languages
    st.append(Paragraph('<b>SECTION E: SKILLS & LANGUAGES</b>', s['OrgHead']))
    data_e = [
        ['Language', 'Speaking', 'Reading', 'Writing'],
        ['Somali', 'Native', 'Good', 'Good'],
        ['Swahili', 'Fluent', 'Fluent', 'Fluent'],
        ['English', 'Fluent', 'Fluent', 'Fluent'],
        ['Arabic', 'Intermediate', 'Intermediate', 'Basic'],
    ]
    te = Table(data_e, colWidths=[3*cm, 4*cm, 4*cm, 4*cm])
    te.setStyle(TableStyle([
        ('FONTSIZE', (0,0), (-1,-1), 9),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('BACKGROUND', (0,0), (-1,0), HexColor('#e8e8e8')),
        ('GRID', (0,0), (-1,-1), 0.5, HexColor('#999')),
        ('ALIGN', (1,0), (-1,-1), 'CENTER'),
        ('TOPPADDING', (0,0), (-1,-1), 3),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3),
    ]))
    st.append(te)
    st.append(Spacer(1, 4))
    st.append(Paragraph('<b>Technical:</b> MS Office, SPSS, KoboToolbox, ODK, Power BI, DHIS2', s['B']))
    st.append(Paragraph('<b>Certifications:</b> PRINCE2 Foundation (2020), Sphere Standards Training (2019), CHS Alliance Certified (2021)', s['B']))

    # References
    st.append(Spacer(1, 6))
    st.append(Paragraph('<b>SECTION F: REFERENCES</b>', s['OrgHead']))
    data_f = [
        ['Name', 'Title', 'Organization', 'Email', 'Phone'],
        ['Dr. James Odhiambo', 'Chief of Education', 'UNICEF Kenya', 'j.odhiambo@unicef.org', '+254 700 111 222'],
        ['Sarah Johnson', 'Country Director', 'Save the Children', 's.johnson@savechildren.org', '+254 700 333 444'],
    ]
    tf = Table(data_f, colWidths=[3.5*cm, 3*cm, 4*cm, 4.5*cm, 3*cm])
    tf.setStyle(TableStyle([
        ('FONTSIZE', (0,0), (-1,-1), 8),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('BACKGROUND', (0,0), (-1,0), HexColor('#e8e8e8')),
        ('GRID', (0,0), (-1,-1), 0.5, HexColor('#999')),
        ('TOPPADDING', (0,0), (-1,-1), 3),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3),
    ]))
    st.append(tf)

    # Declaration
    st.append(Spacer(1, 12))
    st.append(Paragraph(
        '<i>I confirm the above is accurate. I consent to reference checks.</i>',
        ParagraphStyle('Decl', parent=s['Normal'], fontSize=8, textColor=HexColor('#666'))))
    st.append(Spacer(1, 8))
    st.append(Paragraph('Signature: ________________    Date: 18/01/2025', s['B']))

    doc.build(st)
    print(f"  ✓ {path}")


# ============================================================
# CV 21: Physician / Surgeon — Publications-heavy (Free-form)
# ============================================================
def cv21():
    path = os.path.join(OUT_DIR, "cv21_physician_medical_freeform.pdf")
    doc = SimpleDocTemplate(path, pagesize=A4, leftMargin=2*cm, rightMargin=2*cm,
                            topMargin=2*cm, bottomMargin=2*cm)
    s = S()
    st = []
    st.append(Paragraph('DR. SARAH ELIZABETH MORGAN, MD, PHD', s['N1']))
    st.append(Paragraph('Board-Certified Internal Medicine | Hospitalist', s['CT']))
    st.append(Paragraph('sarah.morgan.md@email.com | +1 (415) 555-0345 | San Francisco, CA 94143', s['CT']))
    st.append(Paragraph('NPI: 1234567890 | DEA: BM4567890 | LinkedIn: linkedin.com/in/drsemorgan', s['CT']))
    st.append(Spacer(1, 8))

    st += sec('PROFESSIONAL SUMMARY', s)
    st.append(Paragraph(
        'Triple-board-certified internist with 11 years of clinical experience in hospital '
        'medicine, clinical research, and medical education. Principal investigator on 8 '
        'NIH-funded clinical trials in cardiovascular outcomes. Published 32 peer-reviewed '
        'manuscripts (h-index 18). Seeking combined clinical-research role at academic medical '
        'center.', s['B']))

    st += sec('CLINICAL EXPERIENCE', s)
    st += job('Attending Hospitalist — Internal Medicine', 'UCSF Medical Center, San Francisco',
              'Jul 2018 — Present', [
        'Manage panel of 12-16 inpatients daily with average length of stay 4.2 days',
        'Reduced 30-day readmission rate for CHF patients by 22% through structured discharge protocol',
        'Chair, UCSF Hospital Medicine Quality Committee (2021-Present)',
        'Preceptor for 6 internal medicine residents per academic year',
    ], s)
    st += job('Attending Hospitalist', 'Stanford Health Care, Stanford, CA',
              'Aug 2014 — Jun 2018', [
        'Cared for complex multi-system patients in tertiary academic medical center',
        'Served on rapid response team — average activation to arrival: 90 seconds',
        'Led clinical documentation improvement initiative — increased case-mix index by 8%',
    ], s)
    st += job('Internal Medicine Resident (Categorical)', 'Massachusetts General Hospital, Boston',
              'Jun 2011 — Jun 2014', [
        'Chief Resident (2013-2014) — selected from 48 residents',
        'Completed 4,800+ hours of direct patient care across general medicine, ICU, and ED rotations',
    ], s)

    st += sec('EDUCATION & TRAINING', s)
    st += edu('Doctor of Medicine (M.D.)', 'Harvard Medical School, Boston',
              '2007 — 2011', s=s)
    st += edu('Doctor of Philosophy (Ph.D.) in Cardiovascular Epidemiology', 'Harvard T.H. Chan School of Public Health',
              '2004 — 2007', s=s)
    st += edu('Bachelor of Arts (B.A.) in Bioethics, summa cum laude', 'Yale University, New Haven',
              '2000 — 2004', gpa='3.95/4.0', s=s)
    st += edu('Internal Medicine Residency', 'Massachusetts General Hospital',
              '2011 — 2014', s=s)

    st += sec('BOARD CERTIFICATIONS & LICENSURE', s)
    st.append(Paragraph('• American Board of Internal Medicine — Certified 2014, Recertified 2024', s['B']))
    st.append(Paragraph('• California Medical License #A123456 — Active through 12/2026', s['B']))
    st.append(Paragraph('• DEA Registration BM4567890 — Active through 08/2026', s['B']))
    st.append(Paragraph('• Advanced Cardiac Life Support (ACLS) — Recertified 2024', s['B']))

    st += sec('SELECTED PUBLICATIONS (32 total, h-index 18)', s)
    pubs = [
        'Morgan SE, et al. "Outcomes of Early Discharge Protocol in CHF Patients." New England Journal of Medicine, 2023; 389(14):1284-1293.',
        'Chen J, Morgan SE. "Machine Learning Prediction Models in Cardiovascular Risk." JAMA Cardiology, 2022; 7(8):823-832.',
        'Morgan SE, Patel R. "Sex Differences in Acute MI Presentation Patterns." Circulation, 2021; 144(12):967-980.',
        'Morgan SE. "Bridging Hospital-to-Home: A Multi-Site RCT." Annals of Internal Medicine, 2020; 173(5):401-409.',
        'Williams K, Morgan SE. "Burnout Among Hospitalists During COVID-19." JAMA Internal Medicine, 2020; 180(9):1156-1158.',
    ]
    for p in pubs:
        st.append(Paragraph(f'• {p}', s['SM']))
        st.append(Spacer(1, 2))

    st += sec('RESEARCH FUNDING', s)
    st.append(Paragraph('• NIH/NHLBI R01 — Principal Investigator, $2.4M, 2022-2027', s['B']))
    st.append(Paragraph('• PCORI — Co-Investigator, $1.1M, 2020-2024', s['B']))
    st.append(Paragraph('• American Heart Association — Established Investigator Award, $400K, 2019-2023', s['B']))

    st += sec('PROFESSIONAL MEMBERSHIPS', s)
    st.append(Paragraph('• American College of Physicians (FACP) — Fellow since 2019', s['B']))
    st.append(Paragraph('• Society of Hospital Medicine (SFHM) — Fellow since 2020', s['B']))
    st.append(Paragraph('• American Heart Association — Member since 2005', s['B']))

    st.append(Spacer(1, 4))
    st.append(Paragraph('<b>Languages:</b> English (Native), Spanish (Fluent — Medical Interpreter Certified), French (Conversational)', s['B']))

    doc.build(st)
    print(f"  ✓ {path}")


# ============================================================
# CV 22: CPA / Accountant — Numbers-heavy financial CV (Free-form)
# ============================================================
def cv22():
    path = os.path.join(OUT_DIR, "cv22_cpa_accountant_freeform.pdf")
    doc = SimpleDocTemplate(path, pagesize=A4, leftMargin=2*cm, rightMargin=2*cm,
                            topMargin=2*cm, bottomMargin=2*cm)
    s = S()
    s.add(ParagraphStyle('FinHead', parent=s['Title'], fontSize=22, leading=26,
                         textColor=HexColor('#0a4d3c'), spaceAfter=4))
    st = []
    st.append(Paragraph('ROBERT ALAN PATEL, CPA, MBA', s['FinHead']))
    st.append(Paragraph('Senior Financial Controller | SOX & Audit Expert', s['CT']))
    st.append(Paragraph('robert.patel.cpa@email.com | +1 (212) 555-0398 | Jersey City, NJ 07302', s['CT']))
    st.append(Paragraph('LinkedIn: linkedin.com/in/robertpatel-cpa | CPA License: NY #0876543 (Active)', s['CT']))
    st.append(Spacer(1, 8))

    st += sec('EXECUTIVE SUMMARY', s, '#0a4d3c')
    st.append(Paragraph(
        'Results-driven CPA with 13 years of progressive experience in corporate accounting, '
        'SOX compliance, and financial reporting for Fortune 500 and mid-cap companies. '
        'Managed $80M+ annual budgets and led teams of up to 12. Reduced audit finding '
        'resolution time by 65% at current employer. Seeking Director of Financial Reporting '
        'or VP Controller role at growth-oriented public or pre-IPO company.', s['B']))

    st += sec('PROFESSIONAL EXPERIENCE', s, '#0a4d3c')
    st += job('Senior Financial Controller', 'Hudson Capital Markets, New York, NY',
              'Aug 2020 — Present', [
        'Oversee accounting operations for $3.2B AUM asset management firm across 4 product lines',
        'Manage team of 9 accountants and 3 financial analysts; $4.8M annual departmental budget',
        'Led SOX 404(b) compliance program — passed external audit with zero material weaknesses',
        'Reduced month-end close cycle from 12 business days to 6 days through automation',
        'Implemented NetSuite ERP migration — completed on time, 8% under budget ($1.2M savings)',
        'Coordinate with Big 4 external auditors; manage relationships with SEC and PCAOB reviewers',
    ], s)
    st += job('Assistant Controller — Financial Reporting', 'Greenwich Financial Holdings, Stamford, CT',
              'Mar 2017 — Jul 2020', [
        'Owned SEC filings including 10-K, 10-Q, 8-K, S-1, and proxy statements',
        'Led IPO readiness project — company successfully listed on NYSE in 2019',
        'Managed technical accounting research on ASC 606, ASC 842, and ASC 805 transactions',
        'Reduced external audit fees by 30% through improved documentation and controls',
    ], s)
    st += job('Senior Accountant — Audit & Advisory', 'Deloitte & Touche LLP, New York, NY',
              'Sep 2014 — Feb 2017', [
        'Audited SEC-registered clients in financial services and technology ($500M-$8B revenue)',
        'Led financial statement audits for 4 clients simultaneously — annual revenue $4.5B aggregate',
        'Mentored 6 junior auditors; received Deloitte "Excellence in Client Service" award (2016)',
    ], s)
    st += job('Staff Accountant', 'PricewaterhouseCoopers LLP, New York, NY',
              'Aug 2012 — Aug 2014', [
        'Performed audit testing on banking and asset management clients',
        'Passed all 4 CPA exam sections on first attempt (2013)',
    ], s)

    st += sec('EDUCATION', s, '#0a4d3c')
    st += edu('Master of Business Administration (MBA) — Finance', 'NYU Stern School of Business',
              '2015 — 2017', gpa='3.8/4.0 (Dean\'s List)', s=s)
    st += edu('Bachelor of Science (B.S.) in Accounting, magna cum laude', 'Rutgers University, New Brunswick',
              '2008 — 2012', gpa='3.78/4.0', s=s)

    st += sec('LICENSES & CERTIFICATIONS', s, '#0a4d3c')
    st.append(Paragraph('• Certified Public Accountant (CPA) — New York State #0876543 — Active since 2013', s['B']))
    st.append(Paragraph('• Chartered Financial Analyst (CFA) Level II Candidate — Passed Level I (2024)', s['B']))
    st.append(Paragraph('• Certified Fraud Examiner (CFE) — ACFE — Obtained 2019', s['B']))
    st.append(Paragraph('• AWS Cloud Practitioner Certification — 2023', s['B']))

    st += sec('TECHNICAL SKILLS', s, '#0a4d3c')
    st.append(Paragraph('<b>ERP:</b> NetSuite, Oracle ERP Cloud, SAP S/4HANA, Microsoft Dynamics GP', s['B']))
    st.append(Paragraph('<b>Reporting:</b> Workiva, XBRL filing, Hyperion, BlackLine, FloQast', s['B']))
    st.append(Paragraph('<b>Data:</b> SQL (PostgreSQL), Power BI, Tableau, Advanced Excel (VBA, Power Query)', s['B']))
    st.append(Paragraph('<b>Languages:</b> English (Native), Hindi (Fluent), Gujarati (Conversational)', s['B']))

    doc.build(st)
    print(f"  ✓ {path}")


# ============================================================
# CV 23: K-12 Teacher — Single page sparse (Free-form)
# ============================================================
def cv23():
    path = os.path.join(OUT_DIR, "cv23_teacher_sparse_freeform.pdf")
    doc = SimpleDocTemplate(path, pagesize=A4, leftMargin=2.5*cm, rightMargin=2.5*cm,
                            topMargin=2.5*cm, bottomMargin=2.5*cm)
    s = S()
    s.add(ParagraphStyle('TeachName', parent=s['Title'], fontSize=22, leading=26,
                         textColor=HexColor('#2c3e50'), spaceAfter=4))
    st = []
    st.append(Paragraph('JENNIFER MARIE DAVIS', s['TeachName']))
    st.append(Paragraph('Secondary School English Teacher', s['CT']))
    st.append(Paragraph('jennifer.davis.teacher@email.com | +1 (303) 555-0167 | Denver, CO 80206', s['CT']))
    st.append(Spacer(1, 10))

    st += sec('OBJECTIVE', s)
    st.append(Paragraph(
        'Dedicated English/Language Arts educator with 8 years of experience fostering '
        'literacy and critical thinking in diverse high school classrooms. Passionate about '
        'project-based learning and inclusive pedagogy.', s['B']))

    st += sec('TEACHING EXPERIENCE', s)
    st += job('10th Grade English Teacher', 'Denver South High School, Denver, CO',
              'Aug 2020 — Present', [
        'Teach 4 sections of English 10 (120 students total) aligned to Colorado Academic Standards',
        'Designed project-based curriculum adopted across 3 grade levels',
        'Department Curriculum Committee chair (2022-Present)',
    ], s)
    st += job('9th Grade English Teacher', 'Aurora Central High School, Aurora, CO',
              'Aug 2017 — May 2020', [
        'Taught English 9 to 9th graders across 5 sections annually',
        'Developed writing intervention program reducing failure rate by 35%',
    ], s)
    st += job('Middle School Language Arts Teacher', 'Wheeler Middle School, Denver',
              'Aug 2016 — May 2017', [
        'Taught 6th-8th grade ELA with emphasis on writing workshop model',
    ], s)

    st += sec('EDUCATION', s)
    st += edu('M.A. Curriculum & Instruction', 'University of Colorado Denver',
              '2014 — 2016', s=s)
    st += edu('B.A. English Literature', 'University of Colorado Boulder',
              '2010 — 2014', gpa='3.6/4.0', s=s)

    st += sec('CERTIFICATION', s)
    st.append(Paragraph('• Colorado Professional Teaching License #12345678 — English (7-12), Active', s['B']))
    st.append(Paragraph('• National Board Certified Teacher (NBCT) — Adolescent English Language Arts, 2022', s['B']))

    st += sec('PROFESSIONAL DEVELOPMENT', s)
    st.append(Paragraph('• Teaching Tolerance "Inclusive Classroom" Certificate (2023)', s['B']))
    st.append(Paragraph('• Colorado Writing Project Summer Institute Fellow (2021)', s['B']))

    st += sec('PROFESSIONAL MEMBERSHIPS', s)
    st.append(Paragraph('• National Council of Teachers of English (NCTE) — Member since 2016', s['B']))
    st.append(Paragraph('• Colorado Education Association — Building Representative, 2020-2023', s['B']))

    doc.build(st)
    print(f"  ✓ {path}")


# ============================================================
# CV 24: Architect — multi-page with portfolio section (Free-form)
# ============================================================
def cv24():
    path = os.path.join(OUT_DIR, "cv24_architect_portfolio_freeform.pdf")
    doc = SimpleDocTemplate(path, pagesize=A4, leftMargin=2*cm, rightMargin=2*cm,
                            topMargin=2*cm, bottomMargin=2*cm)
    s = S()
    s.add(ParagraphStyle('ArchName', parent=s['Title'], fontSize=22, leading=26,
                         textColor=HexColor('#1a1a1a'), spaceAfter=4))
    st = []
    st.append(Paragraph('HANNAH LIU, RA, LEED AP BD+C', s['ArchName']))
    st.append(Paragraph('Senior Architect | Sustainable Design Specialist', s['CT']))
    st.append(Paragraph('hannah.liu.arch@email.com | +1 (617) 555-0234 | Cambridge, MA 02139', s['CT']))
    st.append(Paragraph('Portfolio: liuarchitecture.studio | LinkedIn: linkedin.com/in/hannahliu-arch', s['CT']))
    st.append(Paragraph('RA License: MA #ARC-98765 (Active) | LEED AP BD+C #LEED-123456', s['CT']))
    st.append(Spacer(1, 8))

    st += sec('PROFESSIONAL PROFILE', s, '#1a1a1a')
    st.append(Paragraph(
        'Licensed architect with 10 years of experience designing high-performance '
        'educational, healthcare, and civic buildings. Expertise in sustainable design '
        '(LEED Platinum on 6 projects), building information modeling (BIM), and '
        'community-engaged design processes. Portfolio includes 22 built projects totaling '
        '$340M construction value. Seeking Senior Associate / Project Architect role with '
        'mission-driven firm.', s['B']))

    st += sec('PROFESSIONAL EXPERIENCE', s, '#1a1a1a')
    st += job('Senior Architect / Project Lead', 'Payette Associates, Boston, MA',
              'Sep 2020 — Present', [
        'Lead architect on $45M academic building for Boston University — targeting LEED Platinum',
        'Manage project teams of 8-12 consultants and engineers across design phases SD-DD-CD-CA',
        'Direct client interface; oversee construction administration including 60+ RFIs per project',
        'Mentor 4 emerging professionals on path to licensure',
        'Project featured in Architect Magazine (Nov 2023 issue)',
    ], s)
    st += job('Architect', 'Perkins&Will, Boston, MA',
              'Jun 2017 — Aug 2020', [
        'Project architect for $85M hospital expansion — completed on budget and 2 weeks ahead of schedule',
        'Co-led integrated design process with structural, MEP, and sustainability consultants',
        'Achieved LEED Gold certification on completed project',
    ], s)
    st += job('Junior Architect', 'Sasaki Associates, Watertown, MA',
              'Jun 2014 — May 2017', [
        'Worked on master planning and campus design for 3 universities',
        'Developed massing models and participated in 25+ community engagement workshops',
    ], s)

    st += sec('EDUCATION', s, '#1a1a1a')
    st += edu('M.Arch (Master of Architecture)', 'Massachusetts Institute of Technology (MIT)',
              '2011 — 2014', s=s)
    st += edu('B.A. Architecture, cum laude', 'Wesleyan University, Middletown, CT',
              '2007 — 2011', gpa='3.7/4.0', s=s)

    st += sec('LICENSE & CERTIFICATIONS', s, '#1a1a1a')
    st.append(Paragraph('• Registered Architect (RA) — Massachusetts #ARC-98765 — Active', s['B']))
    st.append(Paragraph('• NCIDQ-certified — Certificate #NCIDQ-45678', s['B']))
    st.append(Paragraph('• LEED Accredited Professional — Building Design + Construction (BD+C)', s['B']))
    st.append(Paragraph('• WELL AP — Well Building Standard, 2022', s['B']))
    st.append(Paragraph('• OSHA 10-Hour Construction Safety', s['B']))

    st += sec('SELECTED BUILT PROJECTS', s, '#1a1a1a')
    projs = [
        ['2024', 'BU College of Engineering — Lab Building', '$45M', 'LEED Platinum (targeted)'],
        ['2023', 'Boston Public Library — Branch Renovation', '$8M', 'LEED Gold'],
        ['2022', 'MIT Sloan — East Wing Addition', '$28M', 'WELL Gold'],
        ['2020', 'Cambridge Health Alliance — Outpatient Clinic', '$85M', 'LEED Gold'],
        ['2019', 'UMass Boston — Substation Renovation', '$6M', 'LEED Silver'],
        ['2018', 'Worcester Polytechnic Institute — Innovation Center', '$32M', 'LEED Platinum'],
    ]
    t = Table([['Year', 'Project', 'Value', 'Rating']] + projs, colWidths=[1.5*cm, 9*cm, 2.5*cm, 4*cm])
    t.setStyle(TableStyle([
        ('FONTSIZE', (0,0), (-1,-1), 9),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('GRID', (0,0), (-1,-1), 0.5, HexColor('#cccccc')),
        ('TOPPADDING', (0,0), (-1,-1), 3),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
    ]))
    st.append(t)
    st.append(Spacer(1, 6))

    st += sec('TEACHING & SERVICE', s, '#1a1a1a')
    st.append(Paragraph('• Adjunct Faculty — Boston Architectural College, Studio II (2019-2022)', s['B']))
    st.append(Paragraph('• AIA Massachusetts — Emerging Professionals Committee Vice-Chair, 2021-2023', s['B']))
    st.append(Paragraph('• Volunteer — ACE Mentor Program Boston, Mentor since 2018', s['B']))

    st += sec('SKILLS & SOFTWARE', s, '#1a1a1a')
    st.append(Paragraph('<b>Design:</b> Revit (Expert), Rhino + Grasshopper, AutoCAD, SketchUp Pro, V-Ray', s['B']))
    st.append(Paragraph('<b>Documentation:</b> Bluebeam Revu, Adobe Creative Suite (PS, ID, AI)', s['B']))
    st.append(Paragraph('<b>Analysis:</b> EnergyPlus, IES VE, Sefaira, Ladybug/Honeybee', s['B']))
    st.append(Paragraph('<b>Languages:</b> English (Native), Mandarin Chinese (Fluent — HSK 6), Cantonese (Conversational)', s['B']))

    doc.build(st)
    print(f"  ✓ {path}")


# ============================================================
# CV 25: Two-column layout CV (Free-form)
# ============================================================
def cv25():
    path = os.path.join(OUT_DIR, "cv25_twocolumn_designer_freeform.pdf")
    # Use canvas with explicit 2-column layout
    c = canvas.Canvas(path, pagesize=A4)
    w, h = A4
    margin = 25
    col_gap = 15
    col_w = (w - 2*margin - col_gap) / 2

    def draw_col_header(c, x, y, text, width, color='#34495e'):
        c.setFillColor(HexColor(color))
        c.setFont("Helvetica-Bold", 11)
        c.drawString(x, y, text.upper())
        c.setStrokeColor(HexColor(color))
        c.setLineWidth(0.8)
        c.line(x, y - 3, x + width, y - 3)
        c.setFillColor(black)
        return y - 14

    def draw_para(c, x, y, text, font="Helvetica", size=9, width=None, leading=11):
        c.setFont(font, size)
        if width is None:
            width = col_w
        words = text.split()
        line = ""
        for word in words:
            test = (line + " " + word) if line else word
            if c.stringWidth(test, font, size) > width:
                c.drawString(x, y, line)
                y -= leading
                line = word
            else:
                line = test
        if line:
            c.drawString(x, y, line)
            y -= leading
        return y - 2

    def draw_bullets(c, x, y, bullets, font="Helvetica", size=9, width=None, leading=11):
        if width is None:
            width = col_w
        for b in bullets:
            words = b.split()
            line = "• " + (words[0] if words else "")
            y = y - leading
            for word in words[1:]:
                test = line + " " + word
                if c.stringWidth(test, font, size) > width:
                    c.drawString(x, y, line)
                    y -= leading
                    line = "  " + word
                else:
                    line = test
            if line.strip():
                c.drawString(x, y, line)
            y -= 3
        return y

    # Left column - name and contact
    x_left = margin
    x_right = margin + col_w + col_gap
    y = h - 40

    c.setFont("Helvetica-Bold", 18)
    c.drawString(x_left, y, "MARINA PETROVA")
    y -= 22
    c.setFont("Helvetica", 10)
    c.drawString(x_left, y, "Senior Product Designer | Design Lead")
    y -= 14
    c.setFont("Helvetica", 9)
    c.drawString(x_left, y, "marina.petrova@email.com")
    y -= 11
    c.drawString(x_left, y, "+7 (905) 123-45-67")
    y -= 11
    c.drawString(x_left, y, "Moscow, Russia (Open to relocation)")
    y -= 11
    c.drawString(x_left, y, "linkedin.com/in/marinapetrova")
    y -= 11
    c.drawString(x_left, y, "petrova.design")
    y -= 16

    # Right column - top header
    y_r = h - 40
    c.setFont("Helvetica-Bold", 18)
    c.drawString(x_right, y_r, "EDUCATION")

    # Left column - SUMMARY
    y = draw_col_header(c, x_left, y, "Summary", col_w)
    y = draw_para(c, x_left, y,
        "Senior product designer with 9 years experience leading 0-to-1 product development "
        "for B2B SaaS and consumer apps. Track record of shipping products used by 5M+ "
        "people. Mentor, design system expert, and accessibility advocate.",
        size=9)

    # Left column - SKILLS
    y = draw_col_header(c, x_left, y - 4, "Skills & Tools", col_w)
    y = draw_bullets(c, x_left, y, [
        "Figma, FigJam, Sketch, Principle, Framer",
        "Design Systems, Design Tokens (W3C), Storybook",
        "WCAG 2.1 AA accessibility, Inclusive design",
        "User research: Figma Maze, UserTesting, Dovetail",
        "Front-end basics: React, Vue, HTML/CSS/Tailwind",
    ], size=9)
    y -= 6

    # Left column - LANGUAGES
    y = draw_col_header(c, x_left, y, "Languages", col_w)
    y = draw_bullets(c, x_left, y, [
        "Russian (Native)",
        "English (Fluent — IELTS 8.0)",
        "German (B2 — Goethe-Zertifikat)",
        "French (A2)",
    ], size=9)
    y -= 6

    # Left column - INTERESTS
    y = draw_col_header(c, x_left, y, "Interests", col_w)
    y = draw_bullets(c, x_left, y, [
        "Generative AI for design workflows",
        "Sustainable UX / carbon-aware computing",
        "Open-source contribution (Figma plugins)",
    ], size=9)

    # Right column header (already done above)
    # Right column - top section: EDUCATION
    y_r = draw_col_header(c, x_right, y_r, "Education", col_w)
    y_r = draw_para(c, x_right, y_r, "M.A. Interaction Design", font="Helvetica-Bold", size=10)
    y_r = draw_para(c, x_right, y_r, "Royal College of Art, London, UK", size=9)
    y_r = draw_para(c, x_right, y_r, "2014 — 2016", font="Helvetica-Oblique", size=9)
    y_r -= 6
    y_r = draw_para(c, x_right, y_r, "B.A. Visual Communication", font="Helvetica-Bold", size=10)
    y_r = draw_para(c, x_right, y_r, "Moscow State Stroganov Academy, Russia", size=9)
    y_r = draw_para(c, x_right, y_r, "2010 — 2014", font="Helvetica-Oblique", size=9)
    y_r -= 10

    # Right column - top section: AWARDS
    y_r = draw_col_header(c, x_right, y_r, "Awards", col_w)
    y_r = draw_bullets(c, x_right, y_r, [
        "Red Dot Design Award 2023 — Product Design category",
        "Awwwards Site of the Day (Mar 2022)",
        "CSS Design Awards — Special Kudos (Jul 2021)",
    ], size=9)
    y_r -= 6

    # Right column - EXPERIENCE - header
    y_r = draw_col_header(c, x_right, y_r, "Professional Experience", col_w)

    # Job 1
    y_r = draw_para(c, x_right, y_r, "Senior Product Designer / Lead",
                    font="Helvetica-Bold", size=10)
    y_r = draw_para(c, x_right, y_r, "Avito (Tech Holding)", size=9)
    y_r = draw_para(c, x_right, y_r, "Jan 2022 — Present",
                    font="Helvetica-Oblique", size=9)
    y_r = draw_bullets(c, x_right, y_r, [
        "Lead 4-person design team for buyer-facing marketplace product",
        "Shipped redesign increasing listing creation by 23% in 6 weeks",
        "Established design system adopted across 12 product squads",
    ], size=9)
    y_r -= 6

    # Job 2
    y_r = draw_para(c, x_right, y_r, "Product Designer",
                    font="Helvetica-Bold", size=10)
    y_r = draw_para(c, x_right, y_r, "Yandex", size=9)
    y_r = draw_para(c, x_right, y_r, "Mar 2018 — Dec 2021",
                    font="Helvetica-Oblique", size=9)
    y_r = draw_bullets(c, x_right, y_r, [
        "Designed Yandex.Mail mobile app used by 25M+ users",
        "Led onboarding redesign — activation rate +12%",
    ], size=9)
    y_r -= 6

    # Job 3
    y_r = draw_para(c, x_right, y_r, "UX/UI Designer",
                    font="Helvetica-Bold", size=10)
    y_r = draw_para(c, x_right, y_r, "Studio Mobile, Moscow",
                    size=9)
    y_r = draw_para(c, x_right, y_r, "Sep 2016 — Feb 2018",
                    font="Helvetica-Oblique", size=9)
    y_r = draw_bullets(c, x_right, y_r, [
        "Worked on 8 client projects across banking and travel",
    ], size=9)

    c.save()
    print(f"  ✓ {path}")


# ============================================================
# CV 26: Vietnamese CV with Vietnamese sections (Form-style)
# ============================================================
def cv26():
    path = os.path.join(OUT_DIR, "cv26_vietnamese_koreanengineer_form.pdf")
    doc = SimpleDocTemplate(path, pagesize=A4, leftMargin=2*cm, rightMargin=2*cm,
                            topMargin=2*cm, bottomMargin=2*cm)
    s = S()
    s.add(ParagraphStyle('VNName', parent=s['Title'], fontSize=22, leading=26,
                         textColor=HexColor('#da251d'), spaceAfter=2))
    st = []

    st.append(Paragraph('TRẦN MINH QUÂN', s['VNName']))
    st.append(Paragraph('<b>Kỹ sư phần mềm / Software Engineer</b>', s['CT']))
    st.append(Paragraph('Email: tranquan.dev@email.com | ĐT: (+84) 909 876 543', s['CT']))
    st.append(Paragraph('Địa chỉ: Quận 7, TP. Hồ Chí Minh | LinkedIn: linkedin.com/in/tranminhquan', s['CT']))
    st.append(Spacer(1, 10))

    st += sec('MỤC TIÊU NGHỀ NGHIỆP', s, '#da251d')
    st.append(Paragraph(
        'Kỹ sư phần mềm với 6 năm kinh nghiệm phát triển backend Java/Spring Boot và '
        'hệ thống microservices. Mong muốn ứng tuyển vị trí Senior Backend Engineer tại '
        'công ty công nghệ có sản phẩm phục vụ hàng triệu người dùng.', s['B']))

    st += sec('KINH NGHIỆM LÀM VIỆC', s, '#da251d')
    st += job('Senior Backend Engineer', 'Tiki Corporation',
              'Tháng 6/2021 — Hiện tại', [
        'Thiết kế và phát triển hệ thống đơn hàng xử lý 50,000+ đơn/ngày với độ trễ P99 < 200ms',
        'Dẫn dắt nhóm 4 kỹ sư trong dự án migration từ monolith sang microservices',
        'Tối ưu database PostgreSQL — giảm 35% chi phí query và cải thiện hiệu năng 2x',
        'Triển khai CI/CD pipeline với Jenkins, Docker, Kubernetes — giảm deploy time từ 45 phút xuống 8 phút',
    ], s)
    st += job('Backend Engineer', 'VNG Corporation (ZaloPay)',
              'Tháng 3/2019 — Tháng 5/2021', [
        'Phát triển payment gateway xử lý 8 triệu giao dịch/tháng với uptime 99.95%',
        'Tích hợp với 25 ngân hàng và ví điện tử đối tác',
        'Xây dựng fraud detection system sử dụng rule engine và ML model',
    ], s)
    st += job('Java Developer', 'FPT Software',
              'Tháng 8/2017 — Tháng 2/2019', [
        'Tham gia 4 dự án outsourcing cho khách hàng Nhật Bản và Mỹ',
        'Phát triển REST API sử dụng Spring Boot và Hibernate',
    ], s)

    st += sec('HỌC VẤN', s, '#da251d')
    st += edu('Kỹ sư Khoa học Máy tính (tốt nghiệp loại Giỏi)',
              'Trường Đại học Bách Khoa TP.HCM (HCMUT)',
              '2013 — 2017', gpa='3.6/4.0', s=s)

    st += sec('CHỨNG CHỈ', s, '#da251d')
    st.append(Paragraph('• Oracle Certified Professional Java SE 11 Developer — 2020', s['B']))
    st.append(Paragraph('• AWS Solutions Architect Associate — 2022', s['B']))
    st.append(Paragraph('• Certified Kubernetes Administrator (CKA) — 2023', s['B']))

    st += sec('KỸ NĂNG KỸ THUẬT', s, '#da251d')
    st.append(Paragraph('<b>Ngôn ngữ:</b> Java, Kotlin, Python, SQL', s['B']))
    st.append(Paragraph('<b>Frameworks:</b> Spring Boot, Spring Cloud, Hibernate, Micronaut, Quarkus', s['B']))
    st.append(Paragraph('<b>Database:</b> PostgreSQL, MySQL, MongoDB, Redis, Cassandra', s['B']))
    st.append(Paragraph('<b>DevOps:</b> Docker, Kubernetes, Jenkins, GitLab CI, ArgoCD, Terraform', s['B']))
    st.append(Paragraph('<b>Khác:</b> Kafka, RabbitMQ, Elasticsearch, Prometheus, Grafana', s['B']))

    st += sec('NGOẠI NGỮ', s, '#da251d')
    st.append(Paragraph('Tiếng Việt (Bản ngữ) | Tiếng Anh (TOEFL iBT 95) | Tiếng Nhật (JLPT N3)', s['B']))

    st += sec('DỰ ÁN NỔI BẬT', s, '#da251d')
    st.append(Paragraph('<b>E-Commerce Order Service</b> — Spring Boot, Kafka, PostgreSQL, Redis', s['B']))
    st.append(Paragraph('Hệ thống xử lý đơn hàng phục vụ 50K đơn/ngày với eventual consistency qua Kafka', s['SM']))
    st.append(Spacer(1, 4))
    st.append(Paragraph('<b>Real-time Fraud Detection</b> — Flink, Kafka, ML (Python)', s['B']))
    st.append(Paragraph('Pipeline phát hiện giao dịch gian lận với độ chính xác 94%, giảm tỷ lệ chargeback 40%', s['SM']))

    doc.build(st)
    print(f"  ✓ {path}")


# ============================================================
# CV 27: German Engineer — with ISO dates (Free-form)
# ============================================================
def cv27():
    path = os.path.join(OUT_DIR, "cv27_engineer_german_freeform.pdf")
    doc = SimpleDocTemplate(path, pagesize=A4, leftMargin=2*cm, rightMargin=2*cm,
                            topMargin=2*cm, bottomMargin=2*cm)
    s = S()
    s.add(ParagraphStyle('DeName', parent=s['Title'], fontSize=22, leading=26,
                         textColor=HexColor('#1e3a8a'), spaceAfter=4))
    st = []
    st.append(Paragraph('DR. KLAUS WEBER', s['DeName']))
    st.append(Paragraph('Senior Mechanical Engineering Manager', s['CT']))
    st.append(Paragraph('klaus.weber.eng@email.com | +49 89 1234 5678 | München, Deutschland', s['CT']))
    st.append(Spacer(1, 8))

    st += sec('PROFIL', s, '#1e3a8a')
    st.append(Paragraph(
        'Diplom-Ingenieur mit 17 Jahren Erfahrung in der Automobil- und '
        'Luftfahrtbranche. Spezialisiert auf Antriebsstrang-Entwicklung, FEM-Simulation '
        'und Lieferantenmanagement. Six Sigma Black Belt. Führungserfahrung mit Teams bis '
        'zu 35 Mitarbeitern. Spricht fließend Englisch und Deutsch.', s['B']))

    st += sec('BERUFSERFAHRUNG', s, '#1e3a8a')
    st += job('Engineering Manager — Powertrain', 'BMW Group, München',
              '01.03.2019 — heute', [
        'Leitung eines Teams von 35 Ingenieuren in der Entwicklung von E-Antrieben',
        'Verantwortlich für jährliches Budget von 28 Mio. EUR',
        'Lieferung von 4 Antriebsstrang-Plattformen termingerecht — alle Meilensteine erreicht',
        'Einführung von Six Sigma DMAIC — Reduktion der Garantiekosten um 18%',
    ], s)
    st += job('Senior Mechanical Engineer', 'Airbus Operations GmbH, Hamburg',
              '15.06.2014 — 28.02.2019', [
        'Strukturelle FEM-Analyse von Flugzeugkomponenten (ANSYS, Abaqus)',
        'Zertifizierungsdokumentation nach EASA CS-25 erstellt',
        'Erfindungsmeldung — 2 Patente im Bereich Verbundwerkstoffe angemeldet',
    ], s)
    st += job('Mechanical Engineer', 'Robert Bosch GmbH, Stuttgart',
              '01.09.2010 — 31.05.2014', [
        'Entwicklung von Einspritzsystemen für Dieselmotoren',
        'Lieferantenmanagement — 8 internationale Lieferanten verantwortet',
    ], s)

    st += sec('AUSBILDUNG', s, '#1e3a8a')
    st += edu('Dr.-Ing. Maschinenbau (Promotion)', 'Technische Universität München (TUM)',
              '2007 — 2010', s=s)
    st.append(Paragraph('Note: magna cum laude | Stipendium: Bayerische Forschungsstiftung', s['SM']))
    st.append(Spacer(1, 4))
    st += edu('Dipl.-Ing. Maschinenbau (Diplom)', 'RWTH Aachen',
              '2002 — 2007', gpa='1,7 (sehr gut)', s=s)

    st += sec('ZERTIFIKATE', s, '#1e3a8a')
    st.append(Paragraph('• Six Sigma Black Belt (ASQ) — 2019', s['B']))
    st.append(Paragraph('• PMP — Project Management Professional (PMI) — 2017', s['B']))
    st.append(Paragraph('• EASA Part 66 B1.1 Aircraft Maintenance License — 2014', s['B']))
    st.append(Paragraph('• CATIA V5 Expert Certification — 2011', s['B']))

    st += sec('TECHNISCHE FÄHIGKEITEN', s, '#1e3a8a')
    st.append(Paragraph('<b>CAD/CAE:</b> CATIA V5, Siemens NX, SolidWorks, ANSYS Workbench, Abaqus', s['B']))
    st.append(Paragraph('<b>Methoden:</b> FEM/FEA, CFD, Six Sigma DMAIC, FMEA, APQP', s['B']))
    st.append(Paragraph('<b>Normen:</b> ISO 9001, IATF 16949, AS9100, EASA CS-25', s['B']))
    st.append(Paragraph('<b>Sprachen:</b> Deutsch (Muttersprache), Englisch (C2 — Cambridge CPE), Französisch (B1)', s['B']))

    st += sec('PATENTE', s, '#1e3a8a')
    st.append(Paragraph('• EP1234567B1 — "Verstärkungsstruktur für Flugzeugkomponenten" (2020)', s['B']))
    st.append(Paragraph('• DE102015008341A1 — "Einspritzventil mit optimiertem Strömungsverhalten" (2017)', s['B']))

    doc.build(st)
    print(f"  ✓ {path}")


# ============================================================
# CV 28: Recent grad with no experience — very simple (Free-form)
# ============================================================
def cv28():
    path = os.path.join(OUT_DIR, "cv28_newgrad_simple_freeform.pdf")
    doc = SimpleDocTemplate(path, pagesize=A4, leftMargin=2*cm, rightMargin=2*cm,
                            topMargin=2*cm, bottomMargin=2*cm)
    s = S()
    s.add(ParagraphStyle('GrName', parent=s['Title'], fontSize=22, leading=26,
                         textColor=HexColor('#374151'), spaceAfter=4))
    st = []
    st.append(Paragraph('OLIVIA CHEN', s['GrName']))
    st.append(Paragraph('Bachelor of Science in Computer Science, May 2025', s['CT']))
    st.append(Paragraph('olivia.chen.cs@email.com | (408) 555-0298 | San Jose, CA', s['CT']))
    st.append(Paragraph('linkedin.com/in/oliviachen-cs | github.com/oliviachen', s['CT']))
    st.append(Spacer(1, 8))

    st += sec('OBJECTIVE', s)
    st.append(Paragraph(
        'Recent CS graduate seeking a full-time software engineering role. Strong foundation '
        'in data structures, algorithms, and web development. Excited to contribute to '
        'production code and grow as an engineer.', s['B']))

    st += sec('EDUCATION', s)
    st += edu('B.S. Computer Science', 'University of California, Berkeley',
              'Aug 2021 — May 2025', gpa='3.85/4.0 | Dean\'s List (6 semesters)', s=s)
    st.append(Paragraph('<b>Relevant Coursework:</b> CS 61B (Data Structures), CS 70 (Discrete Math), CS 161 (Algorithms), CS 162 (Operating Systems), CS 188 (AI), CS 186 (Databases), CS 169A (Software Engineering), EE 16A (Circuits)', s['SM']))

    st += sec('PROJECTS', s)
    st += job('Course Enrollment Platform', 'CS 169A Capstone, UC Berkeley',
              'Jan 2025 — May 2025', [
        'Built full-stack web app in team of 5 using React, Flask, PostgreSQL',
        'Implemented course catalog, search, and enrollment workflow with role-based access control',
        'Achieved 92% test coverage, deployed to Heroku with CI/CD via GitHub Actions',
    ], s)
    st += job('Pac-Man AI', 'CS 188 Project, UC Berkeley',
              'Oct 2024', [
        'Implemented search and adversarial agents (Minimax, Alpha-Beta, Expectimax)',
        'Built reinforcement learning agent using Q-learning — won class tournament',
    ], s)
    st += job('Personal Portfolio Site', 'Independent',
              'Aug 2024', [
        'Built responsive personal site with React + Next.js + Tailwind',
        'Deployed on Vercel with custom domain',
    ], s)

    st += sec('EXTRACURRICULAR', s)
    st.append(Paragraph('• ACM@Berkeley — Officer (2023-2024); organized AI/ML workshop series', s['B']))
    st.append(Paragraph('• Cal Hacks 9 — Participant; built accessibility-first reading app in 24h', s['B']))
    st.append(Paragraph('• Society of Women Engineers — Member since 2021', s['B']))

    st += sec('SKILLS', s)
    st.append(Paragraph('<b>Languages:</b> Python, Java, JavaScript/TypeScript, C++, SQL, HTML/CSS', s['B']))
    st.append(Paragraph('<b>Frameworks:</b> React, Next.js, Node.js, Flask, Django, Spring Boot', s['B']))
    st.append(Paragraph('<b>Tools:</b> Git, Docker, PostgreSQL, MongoDB, VS Code, IntelliJ, Postman', s['B']))

    st += sec('WORK EXPERIENCE (Part-time)', s)
    st += job('Backend Engineering Intern', 'Visa Inc., San Francisco (Summer 2024)',
              'Jun 2024 — Aug 2024', [
        'Built internal REST API in Python/Flask for fraud analytics team',
        'Wrote unit tests increasing coverage from 45% to 78%',
        'Mentored by senior engineer; received return offer for full-time',
    ], s)
    st += job('Computer Science Tutor', 'UC Berkeley Student Learning Center',
              'Sep 2023 — May 2024', [
        'Tutored 30+ students in CS 61A and CS 61B',
        'Created supplementary materials adopted by tutoring center',
    ], s)

    doc.build(st)
    print(f"  ✓ {path}")


# ============================================================
# CV 29: Mixed Vietnamese + English — bilingual content
# ============================================================
def cv29():
    path = os.path.join(OUT_DIR, "cv29_vietnamese_mixedbilingual_freeform.pdf")
    doc = SimpleDocTemplate(path, pagesize=A4, leftMargin=2*cm, rightMargin=2*cm,
                            topMargin=2*cm, bottomMargin=2*cm)
    s = S()
    s.add(ParagraphStyle('MixedName', parent=s['Title'], fontSize=22, leading=26,
                         textColor=HexColor('#0066cc'), spaceAfter=4))
    st = []
    st.append(Paragraph('NGUYỄN THỊ HỒNG VÂN / VAN NGUYEN', s['MixedName']))
    st.append(Paragraph('Marketing Manager | Brand Strategy & Digital Marketing', s['CT']))
    st.append(Paragraph('vannguyen.marketing@email.com | (+84) 988 234 567 | Đà Nẵng, Việt Nam', s['CT']))
    st.append(Paragraph('linkedin.com/in/vannguyen-mkt | Website: vannguyen.marketing', s['CT']))
    st.append(Spacer(1, 8))

    st += sec('SUMMARY / TÓM TẮT', s, '#0066cc')
    st.append(Paragraph(
        '<b>EN:</b> Marketing Manager with 8 years of experience building brands across FMCG '
        'and tech in Vietnam and SEA markets. Expertise in brand strategy, integrated '
        'marketing, and performance marketing. Managed $4M annual budget. Track record of '
        'launching 12 successful products. Fluent in Vietnamese and English.', s['B']))
    st.append(Spacer(1, 3))
    st.append(Paragraph(
        '<b>VN:</b> Quản lý Marketing với 8 năm kinh nghiệm xây dựng thương hiệu trong ngành '
        'FMCG và công nghệ tại Việt Nam và Đông Nam Á. Chuyên gia chiến lược thương hiệu, '
        'marketing tích hợp và marketing hiệu suất.', s['B']))

    st += sec('WORK EXPERIENCE / KINH NGHIỆM', s, '#0066cc')
    st += job('Senior Marketing Manager', 'Vinamilk / Vinamilk Brand Division',
              '03/2021 — Present', [
        'Lead brand strategy for 3 product lines — combined revenue $45M annually',
        'Launched new organic yogurt line — captured 12% market share within 9 months',
        'Manage $2.5M annual media budget across TV, digital, and OOH',
        'Spearheaded 360° campaign for "Vinamilk 100% Organic" — won MMA Smarties Award 2023',
        'Direct team of 6 (3 brand managers, 2 designers, 1 digital analyst)',
    ], s)
    st += job('Marketing Manager', 'Tiki Corporation (E-commerce)',
              '07/2018 — 02/2021', [
        'Managed end-to-end marketing campaigns for Tiki mobile app — DAU 8M+',
        'Owned performance marketing on Facebook & Google — $1.2M monthly spend',
        'A/B tested 50+ creatives monthly — improved CAC by 28% YoY',
        'Coordinated with PR team on launch campaigns for 4 major sales events',
    ], s)
    st += job('Brand Executive', 'Unilever Vietnam (Pond\'s, Dove)',
              '08/2016 — 06/2018', [
        'Assisted brand manager in planning and execution of skincare campaigns',
        'Managed agency relationships with 2 creative shops and 3 media agencies',
    ], s)

    st += sec('EDUCATION / HỌC VẤN', s, '#0066cc')
    st += edu('MBA Marketing — Dean\'s List', 'University of Economics HCMC (UEH)',
              '2017 — 2019', gpa='3.8/4.0', s=s)
    st += edu('B.A. International Business', 'Foreign Trade University (FTU), Hanoi',
              '2012 — 2016', gpa='3.7/4.0 | Top 5% cohort', s=s)
    st += edu('Business Management Exchange Program', 'ESSEC Business School, Singapore',
              'Spring 2015', s=s)

    st += sec('CERTIFICATIONS', s, '#0066cc')
    st.append(Paragraph('• Google Ads Certified — Search, Display, Video, Measurement (2023)', s['B']))
    st.append(Paragraph('• Meta Blueprint Certified — Facebook Media Planning Professional (2024)', s['B']))
    st.append(Paragraph('• HubSpot Inbound Marketing Certification (2022)', s['B']))

    st += sec('LANGUAGES / NGOẠI NGỮ', s, '#0066cc')
    st.append(Paragraph('• Tiếng Việt — Native (Bản ngữ)', s['B']))
    st.append(Paragraph('• English — Fluent (IELTS 7.5, TOEIC 920)', s['B']))
    st.append(Paragraph('• Mandarin Chinese — HSK 4 (Conversational Business)', s['B']))

    st += sec('AWARDS', s, '#0066cc')
    st.append(Paragraph('• MMA Smarties Vietnam — Silver, Brand Marketing 2023', s['B']))
    st.append(Paragraph('• Marketing Magazine Vietnam — "Top 30 Under 30" 2020', s['B']))

    doc.build(st)
    print(f"  ✓ {path}")


# ============================================================
# CV 30: Heavy data professional — Data Engineer (Free-form)
# ============================================================
def cv30():
    path = os.path.join(OUT_DIR, "cv30_dataengineer_freeform.pdf")
    doc = SimpleDocTemplate(path, pagesize=A4, leftMargin=2*cm, rightMargin=2*cm,
                            topMargin=2*cm, bottomMargin=2*cm)
    s = S()
    st = []
    st.append(Paragraph('LI WEI (李伟)', s['N1']))
    st.append(Paragraph('Senior Data Engineer / ML Platform Engineer', s['CT']))
    st.append(Paragraph('liwei.data@email.com | +65 9123 4567 | Singapore', s['CT']))
    st.append(Paragraph('linkedin.com/in/liwei-data | github.com/liwei-data', s['CT']))
    st.append(Spacer(1, 8))

    st += sec('PROFESSIONAL SUMMARY', s)
    st.append(Paragraph(
        'Data engineer with 8 years of experience building large-scale data platforms '
        'and ML infrastructure. Led platform teams at TikTok, Shopee, and a fintech '
        'startup. Specialized in batch/streaming pipelines, lakehouse architectures '
        '(Iceberg/Delta Lake), and ML ops (Kubeflow, MLflow). Managed petabyte-scale '
        'data lakes. Seeking Staff Data Engineer role at a high-growth tech company.', s['B']))

    st += sec('PROFESSIONAL EXPERIENCE', s)
    st += job('Senior Data Engineer — ML Platform', 'TikTok (ByteDance), Singapore',
              'Sep 2021 — Present', [
        'Architect and maintain feature store serving 200+ ML models across the SEA region',
        'Designed streaming pipelines (Kafka + Flink) ingesting 2TB/hour from 1,200+ sources',
        'Cut model training data prep time from 6 hours to 18 minutes via Iceberg + Spark 3.4',
        'Led migration of 80TB data lake from Hadoop HDFS to S3 + Iceberg tables — saved $400K/yr',
        'Mentor 4 junior data engineers; co-author internal data engineering handbook',
    ], s)
    st += job('Data Engineer', 'Shopee (Sea Group), Singapore',
              'Mar 2019 — Aug 2021', [
        'Built real-time fraud detection pipeline using Flink and AWS services',
        'Owned Airflow infrastructure for 200+ ETL jobs across 3 product lines',
        'Reduced data pipeline failures by 60% through observability improvements',
    ], s)
    st += job('Backend / Data Engineer', 'Akulaku, Jakarta, Indonesia',
              'Jun 2017 — Feb 2019', [
        'Built credit scoring data pipelines for 5M+ loan applications',
        'Migrated reporting stack from MySQL to ClickHouse — query latency improved 50x',
    ], s)
    st += job('Software Engineer Intern', 'Tencent, Shenzhen, China',
              'Jun 2016 — Aug 2016', [
        'Worked on the WeChat payment risk team — built log analysis pipeline with Spark',
    ], s)

    st += sec('EDUCATION', s)
    st += edu('M.S. Computer Science (Big Data Systems)', 'National University of Singapore (NUS)',
              '2015 — 2017', gpa='4.6/5.0 | Research: stream processing systems', s=s)
    st += edu('B.Eng. Software Engineering', 'South China University of Technology (SCUT)',
              '2011 — 2015', gpa='3.78/4.0 | Outstanding Graduate', s=s)

    st += sec('PUBLICATIONS & OPEN SOURCE', s)
    st.append(Paragraph('• Chen L, Li W. "Cost-Optimized Iceberg Tables in Multi-Cloud." VLDB 2024 (Demo Track)', s['B']))
    st.append(Paragraph('• Contributor: Apache Iceberg (5 merged PRs in 2023)', s['B']))
    st.append(Paragraph('• Author: pyspark-data-quality (open source, 850+ GitHub stars)', s['B']))

    st += sec('CERTIFICATIONS', s)
    st.append(Paragraph('• AWS Certified Solutions Architect — Professional (2023)', s['B']))
    st.append(Paragraph('• GCP Professional Data Engineer (2022)', s['B']))
    st.append(Paragraph('• Databricks Certified Data Engineer Professional (2022)', s['B']))
    st.append(Paragraph('• SnowPro Advanced — Snowflake Snowpipe Streaming (2023)', s['B']))

    st += sec('TECHNICAL SKILLS', s)
    st.append(Paragraph('<b>Streaming:</b> Apache Flink, Kafka, Pulsar, Kinesis, Spark Structured Streaming', s['B']))
    st.append(Paragraph('<b>Batch:</b> Spark, Hive, Presto/Trino, dbt, Apache Beam', s['B']))
    st.append(Paragraph('<b>Storage:</b> Iceberg, Delta Lake, Hudi, Parquet, ORC, ClickHouse, Druid', s['B']))
    st.append(Paragraph('<b>Orchestration:</b> Airflow, Dagster, Prefect, Argo Workflows', s['B']))
    st.append(Paragraph('<b>Cloud:</b> AWS (S3, EMR, Glue, Kinesis), GCP (BigQuery, Dataflow), Snowflake', s['B']))
    st.append(Paragraph('<b>Languages:</b> Python, Scala, SQL, Java, Go (basic)', s['B']))
    st.append(Paragraph('<b>Languages spoken:</b> English (Fluent), Mandarin Chinese (Native), Bahasa Indonesia (Conversational)', s['B']))

    st += sec('PROJECTS & SIDE WORK', s)
    st.append(Paragraph('<b>iceberg-compactor</b> — Open-source compaction tool for Apache Iceberg, adopted internally at 3 companies', s['B']))
    st.append(Paragraph('<b>data-platform-playbook</b> — Technical blog with 12K monthly readers covering modern data stack', s['B']))

    doc.build(st)
    print(f"  ✓ {path}")


# ============================================================
if __name__ == "__main__":
    import sys
    sets = sys.argv[1] if len(sys.argv) > 1 else "all"

    if sets in ("all", "1"):
        print("=== Set 1: Free-form ===")
        cv11()
        cv12()
        cv13()
        cv14()
        cv15()
        cv16()
        cv17()
        cv18()
        print("\n=== Set 1: Organizational Forms ===")
        cv19()
        cv20()

    if sets in ("all", "2"):
        print("\n=== Set 2: Free-form ===")
        cv21()
        cv22()
        cv23()
        cv24()
        cv25()
        cv26()
        cv27()
        cv28()
        cv29()
        cv30()

    print(f"\nDone — all in {OUT_DIR}")