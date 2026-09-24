"""
Multilingual CV section-heading lexicon.

Used by the text extractor to mark headings ("## EDUCATION") and by the
LLM chunker to split long CVs on section boundaries. Headings are matched
after normalize_label() (no diacritics, no punctuation, lowercase), so each
alias only needs to be listed once without accents.
"""
import re

from text_utils import normalize_label

# canonical section -> aliases (EN, VI, FR, DE, ES, plus common variants)
SECTION_ALIASES: dict[str, list[str]] = {
    "personal": [
        "personal information", "personal info", "personal details", "personal data",
        "personal profile", "contact", "contacts", "contact information", "contact details",
        "about me", "details",
        "thong tin ca nhan", "thong tin lien he", "lien he", "ho so ca nhan", "ban than",
        "so yeu ly lich", "thong tin chung",
        "informations personnelles", "coordonnees", "personliche daten", "kontakt",
        "datos personales", "informacion personal", "contacto",
    ],
    "summary": [
        "summary", "professional summary", "profile", "professional profile", "career summary",
        "objective", "career objective", "career objectives", "objectives", "about",
        "executive summary", "overview", "introduction", "summary of qualifications",
        "muc tieu", "muc tieu nghe nghiep", "gioi thieu", "gioi thieu ban than", "tom tat",
        "dinh huong nghe nghiep", "muc tieu cong viec",
        "profil", "objectif", "profil professionnel", "zusammenfassung",
        "perfil", "perfil profesional", "resumen", "objetivo",
    ],
    "experience": [
        "experience", "work experience", "professional experience", "employment",
        "employment history", "work history", "career history", "relevant experience",
        "professional background", "experiences", "working experience", "work experiences",
        "career", "positions held", "internships", "internship", "military service",
        "assignments", "key assignments", "military experience", "service record",
        "military service record", "employment record",
        "kinh nghiem", "kinh nghiem lam viec", "qua trinh lam viec", "qua trinh cong tac",
        "lich su lam viec", "kinh nghiem chuyen mon", "qua trinh cong tac lam viec",
        "experience professionnelle", "experiences professionnelles", "berufserfahrung",
        "berufliche erfahrung", "experiencia", "experiencia laboral", "experiencia profesional",
    ],
    "education": [
        "education", "educational background", "academic background", "academic history",
        "education and training", "education training", "qualifications",
        "academic qualifications", "educational qualifications", "studies", "academics",
        "hoc van", "trinh do hoc van", "qua trinh hoc tap", "dao tao", "trinh do dao tao",
        "qua trinh dao tao", "bang cap", "trinh do chuyen mon",
        "formation", "formations", "etudes", "ausbildung", "bildung", "bildungsweg",
        "educacion", "formacion", "formacion academica",
    ],
    "skills": [
        "skills", "technical skills", "key skills", "core skills", "competencies",
        "core competencies", "skills and abilities", "skills tools", "tools", "expertise",
        "areas of expertise", "it skills", "computer skills", "soft skills", "hard skills",
        "technologies", "tech stack",
        "ky nang", "ky nang chuyen mon", "ky nang mem", "ky nang tin hoc", "tin hoc",
        "nang luc", "ky nang ky thuat",
        "competences", "kenntnisse", "fahigkeiten", "habilidades", "competencias",
    ],
    "languages": [
        "languages", "language", "language skills", "foreign languages", "language proficiency",
        "ngoai ngu", "ngon ngu", "trinh do ngoai ngu", "kha nang ngoai ngu",
        "langues", "sprachen", "sprachkenntnisse", "idiomas",
    ],
    "certificates": [
        "certificates", "certifications", "certification", "licenses", "licences",
        "licenses and certifications", "certifications and licenses", "credentials",
        "professional certifications", "accreditations",
        "chung chi", "chung nhan", "bang cap chung chi", "chung chi chung nhan",
        "certificats", "zertifikate", "zertifizierungen", "certificados", "certificaciones",
    ],
    "awards": [
        "awards", "honors", "honours", "awards and honors", "awards and achievements",
        "achievements", "accomplishments", "recognition", "honors and awards", "scholarships",
        "giai thuong", "khen thuong", "thanh tich", "thanh tuu", "danh hieu", "hoc bong",
        "prix", "distinctions", "auszeichnungen", "premios", "logros",
    ],
    "courses": [
        "courses", "training", "trainings", "professional development", "short courses",
        "additional training", "training courses", "workshops", "continuing education",
        "khoa hoc", "khoa dao tao", "dao tao ngan han", "boi duong", "cac khoa hoc",
        "cours", "weiterbildung", "fortbildung", "cursos",
    ],
    "projects": [
        "projects", "project", "key projects", "selected projects", "notable projects",
        "personal projects", "academic projects", "project experience", "portfolio",
        "du an", "cac du an", "du an tieu bieu", "du an da tham gia",
        "projets", "projekte", "proyectos",
    ],
    "activities": [
        "activities", "extracurricular activities", "volunteer", "volunteering",
        "volunteer experience", "community service", "leadership", "memberships",
        "professional memberships", "affiliations", "organizations",
        "hoat dong", "hoat dong ngoai khoa", "tinh nguyen", "hoat dong xa hoi",
        "benevolat", "ehrenamt", "voluntariado",
    ],
    "publications": [
        "publications", "research", "papers", "research experience", "presentations",
        "cong trinh nghien cuu", "bai bao", "nghien cuu khoa hoc",
    ],
    "references": [
        "references", "referees", "reference", "nguoi tham chieu", "tham chieu",
        "nguoi gioi thieu", "references available upon request", "referenzen", "referencias",
    ],
    "family": [
        "family", "family members", "family information", "dependents", "family background",
        "emergency contact", "emergency contacts",
        "gia dinh", "thong tin gia dinh", "than nhan", "nguoi than", "quan he gia dinh",
        "lien he khan cap",
    ],
    "interests": [
        "interests", "hobbies", "hobbies and interests", "personal interests",
        "so thich", "so thich ca nhan", "centres d interet", "loisirs", "hobbys", "intereses",
    ],
    "additional": [
        "additional information", "other information", "others", "miscellaneous",
        "thong tin khac", "thong tin bo sung", "khac",
    ],
    "disciplinary": [
        "discipline", "disciplinary", "ky luat",
    ],
}

_ALIAS_TO_SECTION: dict[str, str] = {}
for _sec, _aliases in SECTION_ALIASES.items():
    for _a in _aliases:
        _ALIAS_TO_SECTION[normalize_label(_a)] = _sec

# "1.", "II.", "A)" style numbering in front of headings
_NUMBERING_RE = re.compile(r"^\s*(?:[0-9]{1,2}|[ivxIVX]{1,4}|[a-hA-H])\s*[.)/-]\s+")
# bilingual headings: "HỌC VẤN / EDUCATION", "Kinh nghiệm | Experience"
_BILINGUAL_SPLIT_RE = re.compile(r"\s*[/|–—]\s*|\s+-\s+|\s*\(\s*|\s*\)\s*")


def match_section(text: str, loose: bool = False) -> str | None:
    """Return the canonical section key if `text` is a section heading, else None.

    loose=True also accepts headings that start or end with a known alias
    ("Education & Military Training", "Key Assignments"); callers use it only
    for lines that are styled like headings (bold / caps / larger font).
    """
    if not text:
        return None
    raw = text.strip().rstrip(":：").strip()
    if len(raw) > 70 or len(raw.split()) > 9:
        return None
    raw = _NUMBERING_RE.sub("", raw)
    parts = [raw] + [p for p in _BILINGUAL_SPLIT_RE.split(raw) if p]
    for part in parts:
        key = normalize_label(part)
        if key in _ALIAS_TO_SECTION:
            return _ALIAS_TO_SECTION[key]
        # "Skills & Tools", "Education and Training", "Awards & Decorations"
        first = normalize_label(re.split(r"\s*&\s*|\s+(?:and|và|va|et|und|y)\s+", part, flags=re.I)[0])
        if first != key and first in _ALIAS_TO_SECTION:
            return _ALIAS_TO_SECTION[first]
    if loose:
        words = normalize_label(raw).split()
        for n in (3, 2, 1):
            if len(words) > n:
                for cand in (" ".join(words[:n]), " ".join(words[-n:])):
                    if cand in _ALIAS_TO_SECTION:
                        return _ALIAS_TO_SECTION[cand]
    return None


# Document-title lines that are not a candidate's name or a section
DOCUMENT_TITLES = {
    normalize_label(t) for t in [
        "curriculum vitae", "resume", "résumé", "cv", "so yeu ly lich", "ly lich",
        "don ung tuyen", "phieu thong tin ung vien", "application form",
        "candidate information form", "employment application", "lebenslauf",
    ]
}


def is_document_title(text: str) -> bool:
    return normalize_label(text) in DOCUMENT_TITLES
