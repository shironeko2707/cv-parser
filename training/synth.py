"""
Synthetic CV profiles for SLM fine-tuning.

A profile holds, for every value, both what is *printed* in the document
(random date formats, label language, casing...) and the canonical *gold*
value the model must output (ISO dates, "male"/"female", verbatim text).
Renderers in render.py print `disp`; build_dataset.py trains on `gold`.
"""
from __future__ import annotations

import random
import unicodedata
from dataclasses import dataclass, field

from faker import Faker

from training import vocab as V

MON_EN = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
MONTH_EN = ["January", "February", "March", "April", "May", "June", "July", "August", "September",
            "October", "November", "December"]

# Section headings / field labels per label language
HEADINGS = {
    "vi": {
        "personal": ["THÔNG TIN CÁ NHÂN", "Thông tin cá nhân", "THÔNG TIN LIÊN HỆ"],
        "summary": ["MỤC TIÊU NGHỀ NGHIỆP", "Mục tiêu nghề nghiệp", "GIỚI THIỆU BẢN THÂN"],
        "experience": ["KINH NGHIỆM LÀM VIỆC", "Kinh nghiệm làm việc", "QUÁ TRÌNH CÔNG TÁC", "KINH NGHIỆM"],
        "education": ["HỌC VẤN", "Học vấn", "TRÌNH ĐỘ HỌC VẤN", "QUÁ TRÌNH ĐÀO TẠO"],
        "languages": ["NGOẠI NGỮ", "Ngoại ngữ", "TRÌNH ĐỘ NGOẠI NGỮ"],
        "certificates": ["CHỨNG CHỈ", "Chứng chỉ", "BẰNG CẤP - CHỨNG CHỈ"],
        "awards": ["GIẢI THƯỞNG", "Giải thưởng", "THÀNH TÍCH", "KHEN THƯỞNG"],
        "courses": ["KHÓA HỌC", "Các khóa đào tạo", "ĐÀO TẠO NGẮN HẠN"],
        "family": ["THÔNG TIN GIA ĐÌNH", "Quan hệ gia đình", "THÂN NHÂN"],
        "skills": ["KỸ NĂNG", "Kỹ năng", "KỸ NĂNG CHUYÊN MÔN"],
        "projects": ["DỰ ÁN", "Dự án tiêu biểu"],
        "interests": ["SỞ THÍCH", "Sở thích"],
        "references": ["NGƯỜI THAM CHIẾU", "Người tham chiếu"],
    },
    "en": {
        "personal": ["PERSONAL INFORMATION", "Personal Details", "CONTACT"],
        "summary": ["SUMMARY", "Professional Summary", "PROFILE", "CAREER OBJECTIVE", "About Me"],
        "experience": ["WORK EXPERIENCE", "Professional Experience", "EXPERIENCE", "EMPLOYMENT HISTORY",
                       "Career History"],
        "education": ["EDUCATION", "Education", "ACADEMIC BACKGROUND", "EDUCATION & QUALIFICATIONS"],
        "languages": ["LANGUAGES", "Languages", "LANGUAGE SKILLS"],
        "certificates": ["CERTIFICATIONS", "Certificates", "LICENSES & CERTIFICATIONS"],
        "awards": ["AWARDS", "Honors & Awards", "ACHIEVEMENTS"],
        "courses": ["TRAINING", "Courses", "PROFESSIONAL DEVELOPMENT"],
        "family": ["FAMILY INFORMATION", "Family Members", "EMERGENCY CONTACT"],
        "skills": ["SKILLS", "Technical Skills", "KEY SKILLS", "CORE COMPETENCIES"],
        "projects": ["PROJECTS", "Selected Projects"],
        "interests": ["INTERESTS", "Hobbies"],
        "references": ["REFERENCES", "Referees"],
    },
}
# Unusual headings the lexicon does not know (teach robustness to unmarked sections)
ODD_HEADINGS = {
    "experience": ["WHERE I'VE WORKED", "PROFESSIONAL JOURNEY", "HÀNH TRÌNH SỰ NGHIỆP"],
    "education": ["WHERE I STUDIED", "NỀN TẢNG HỌC THUẬT"],
}
LABELS = {
    "vi": {"full_name": "Họ và tên", "gender": "Giới tính", "date_of_birth": "Ngày sinh",
           "place_of_birth": "Nơi sinh", "nationality": "Quốc tịch", "marital_status": "Tình trạng hôn nhân",
           "email": "Email", "phone": "Điện thoại", "address": "Địa chỉ", "city": "Tỉnh/Thành phố",
           "country": "Quốc gia", "id_number": "Số CCCD", "id_issue_date": "Ngày cấp",
           "id_issue_place": "Nơi cấp", "linkedin": "LinkedIn", "website": "Website",
           "current_title": "Vị trí ứng tuyển"},
    "en": {"full_name": "Full name", "gender": "Gender", "date_of_birth": "Date of birth",
           "place_of_birth": "Place of birth", "nationality": "Nationality", "marital_status": "Marital status",
           "email": "Email", "phone": "Phone", "address": "Address", "city": "City", "country": "Country",
           "id_number": "ID number", "id_issue_date": "Issue date", "id_issue_place": "Place of issue",
           "linkedin": "LinkedIn", "website": "Website", "current_title": "Title"},
}
FIELD_LABELS = {
    "vi": {"company": "Công ty", "job_title": "Vị trí", "time": "Thời gian", "description": "Mô tả công việc",
           "institution": "Trường", "major": "Chuyên ngành", "degree": "Bằng cấp", "grade": "Xếp loại",
           "from": "Từ", "to": "Đến", "language": "Ngoại ngữ", "proficiency": "Trình độ",
           "name": "Tên", "issuer": "Đơn vị cấp", "date": "Năm", "relationship": "Quan hệ",
           "yob": "Năm sinh", "occupation": "Nghề nghiệp", "location": "Địa điểm"},
    "en": {"company": "Company", "job_title": "Position", "time": "Period", "description": "Responsibilities",
           "institution": "School", "major": "Major", "degree": "Degree", "grade": "GPA",
           "from": "From", "to": "To", "language": "Language", "proficiency": "Level",
           "name": "Name", "issuer": "Issued by", "date": "Year", "relationship": "Relationship",
           "yob": "Year of birth", "occupation": "Occupation", "location": "Location"},
}


def ascii_slug(s: str) -> str:
    s = s.replace("đ", "d").replace("Đ", "D")
    s = unicodedata.normalize("NFKD", s)
    return "".join(c for c in s if c.isascii() and (c.isalnum() or c == " ")).lower()


@dataclass
class Entry:
    disp: dict = field(default_factory=dict)  # printed strings (incl. "dates", "bullets")
    gold: dict = field(default_factory=dict)  # canonical target values


@dataclass
class Profile:
    lang: str                      # label language: vi | en | bi
    content_lang: str              # vi | en
    locale: str
    personal_disp: dict = field(default_factory=dict)
    personal_gold: dict = field(default_factory=dict)
    sections: dict = field(default_factory=dict)  # canonical section -> list[Entry]
    extras: dict = field(default_factory=dict)    # summary/skills/projects/... (not in gold)
    heading: dict = field(default_factory=dict)   # section -> chosen heading text
    style: dict = field(default_factory=dict)     # renderer knobs chosen per document

    def gold(self) -> dict:
        out: dict = {}
        if self.personal_gold:
            out["personal"] = dict(self.personal_gold)
        for sec, entries in self.sections.items():
            golds = [e.gold for e in entries if e.gold]
            if golds:
                out[sec] = golds
        return out

    def label(self, key: str) -> str:
        if self.lang == "bi":
            return f"{LABELS['vi'][key]} / {LABELS['en'][key]}"
        return LABELS[self.lang][key]

    def flabel(self, key: str) -> str:
        if self.lang == "bi":
            return f"{FIELD_LABELS['vi'][key]} / {FIELD_LABELS['en'][key]}"
        return FIELD_LABELS[self.lang][key]


class DateStyle:
    """One date format per document (like a real CV)."""

    def __init__(self, rng: random.Random, lang: str):
        vi = lang in ("vi", "bi")
        month_styles = ["mm/yyyy", "m/yyyy", "Mon yyyy", "Month yyyy", "yyyy-mm", "mm.yyyy", "yyyy"]
        if vi:
            month_styles += ["Tm/yyyy", "Tháng m/yyyy", "mm/yyyy", "mm/yyyy", "tháng m năm yyyy"]
        self.month_style = rng.choice(month_styles)
        self.sep = rng.choice([" - ", " – ", " — ", " - ", " to "] + ([" đến ", " - "] if vi else []))
        if self.month_style.startswith(("Tm", "Tháng", "tháng")):
            self.sep = rng.choice([" - ", " – ", " đến "])
        self.present = rng.choice(["nay", "Hiện tại", "Đến nay", "Present", "hiện nay"] if vi
                                  else ["Present", "Current", "Now", "present"])
        dob_styles = ["dd/mm/yyyy", "d/m/yyyy", "dd-mm-yyyy", "dd.mm.yyyy", "yyyy-mm-dd", "d Month yyyy",
                      "Month d, yyyy"]
        if vi:
            dob_styles += ["dd/mm/yyyy", "dd/mm/yyyy", "ngày d tháng m năm yyyy"]
        self.dob_style = rng.choice(dob_styles)

    def month(self, y: int, m: int) -> tuple[str, str]:
        s = self.month_style
        disp = {
            "mm/yyyy": f"{m:02d}/{y}", "m/yyyy": f"{m}/{y}", "Mon yyyy": f"{MON_EN[m - 1]} {y}",
            "Month yyyy": f"{MONTH_EN[m - 1]} {y}", "yyyy-mm": f"{y}-{m:02d}", "mm.yyyy": f"{m:02d}.{y}",
            "yyyy": f"{y}", "Tm/yyyy": f"T{m}/{y}", "Tháng m/yyyy": f"Tháng {m}/{y}",
            "tháng m năm yyyy": f"tháng {m} năm {y}",
        }[s]
        gold = f"{y}" if s == "yyyy" else f"{y}-{m:02d}"
        return disp, gold

    def range(self, start: tuple[int, int], end: tuple[int, int] | None) -> tuple[str, str, str]:
        sd, sg = self.month(*start)
        if end is None:
            return f"{sd}{self.sep}{self.present}", sg, "present"
        ed, eg = self.month(*end)
        return f"{sd}{self.sep}{ed}", sg, eg

    def day(self, y: int, m: int, d: int) -> tuple[str, str]:
        s = self.dob_style
        disp = {
            "dd/mm/yyyy": f"{d:02d}/{m:02d}/{y}", "d/m/yyyy": f"{d}/{m}/{y}",
            "dd-mm-yyyy": f"{d:02d}-{m:02d}-{y}", "dd.mm.yyyy": f"{d:02d}.{m:02d}.{y}",
            "yyyy-mm-dd": f"{y}-{m:02d}-{d:02d}", "d Month yyyy": f"{d} {MONTH_EN[m - 1]} {y}",
            "Month d, yyyy": f"{MONTH_EN[m - 1]} {d}, {y}", "ngày d tháng m năm yyyy": f"ngày {d} tháng {m} năm {y}",
        }[s]
        return disp, f"{y}-{m:02d}-{d:02d}"


def _fill(template: str, rng: random.Random) -> str:
    return template.format(
        tech=rng.choice(V.TECH), cloud=rng.choice(V.CLOUD), product=rng.choice(V.PRODUCTS),
        n=rng.choice([5, 8, 12, 20, 35, 50, 120, 300]), p=rng.choice([10, 15, 20, 25, 30, 40, 120]),
        k=rng.randint(3, 9),
    )


class ProfileGenerator:
    def __init__(self, seed: int | None = None):
        self.rng = random.Random(seed)
        self.fakers = {loc: Faker(loc) for loc in ("en_US", "en_GB", "en_AU", "en_IN")}
        self.reseed(seed or 0)

    def reseed(self, seed: int):
        """Deterministic per-sample seeding (Faker instances are slow to create)."""
        self.rng.seed(seed)
        for i, f in enumerate(self.fakers.values()):
            f.seed_instance(seed * 7 + i)

    # -- personal ------------------------------------------------------------
    def _vn_person(self, p: Profile, gender: str):
        r = self.rng
        family = r.choice(V.VN_FAMILY)
        middle = r.choice(V.VN_MIDDLE_M if gender == "male" else V.VN_MIDDLE_F)
        given = r.choice(V.VN_GIVEN_M if gender == "male" else V.VN_GIVEN_F)
        parts = [family, middle, given]
        if r.random() < 0.15:
            parts.insert(2, r.choice(V.VN_MIDDLE_M if gender == "male" else V.VN_MIDDLE_F))
        name = " ".join(dict.fromkeys(parts))
        city = r.choice(list(V.VN_CITIES))
        district = r.choice(V.VN_CITIES[city])
        num = r.randint(1, 250)
        street = r.choice(V.VN_STREETS)
        addr_forms = [
            f"Số {num} {street}, {district}, {city}",
            f"{num} {street}, {r.choice(V.VN_WARDS)}, {district}, {city}",
            f"Số {num}, ngõ {r.randint(2, 200)} {street}, {district}, {city}",
            f"{district}, {city}",
        ]
        prefix = r.choice(["09", "03", "07", "08", "09", "09"])
        digits = prefix + "".join(str(r.randint(0, 9)) for _ in range(8))
        phone = r.choice([
            f"{digits[:4]} {digits[4:7]} {digits[7:]}", f"{digits[:4]}.{digits[4:7]}.{digits[7:]}",
            digits, f"+84 {digits[1:4]} {digits[4:7]} {digits[7:]}", f"(+84) {digits[1:4]}-{digits[4:7]}-{digits[7:]}",
            f"{digits[:3]} {digits[3:6]} {digits[6:]}",
        ])
        slug = ascii_slug(name).split()
        local = r.choice([
            f"{slug[-1]}.{slug[0]}", f"{slug[0]}{slug[-1]}{r.randint(80, 99)}", "".join(slug),
            f"{slug[-1]}{''.join(w[0] for w in slug[:-1])}{r.randint(1, 99)}", f"{slug[-1]}.{''.join(slug[:-1])}",
        ])
        email = f"{local}@{r.choice(['gmail.com', 'gmail.com', 'yahoo.com', 'outlook.com', 'hotmail.com', 'fpt.edu.vn'])}"
        return {
            "name": name, "address": r.choice(addr_forms), "city": city, "phone": phone, "email": email,
            "country": r.choice(["Việt Nam", "Vietnam"]), "nationality": r.choice(["Việt Nam", "Vietnamese"]),
            "place_of_birth": r.choice(V.VN_PROVINCES_BIRTH), "slug": "".join(slug),
        }

    def _en_person(self, gender: str):
        r = self.rng
        loc = r.choice(list(self.fakers))
        f = self.fakers[loc]
        first = f.first_name_male() if gender == "male" else f.first_name_female()
        last = f.last_name()
        name = f"{first} {r.choice(['A.', 'J.', 'M.', ''])} {last}".replace("  ", " ") if r.random() < 0.2 \
            else f"{first} {last}"
        city = f.city()
        addr = f.street_address() + ", " + city
        phone = f.phone_number()
        slug = ascii_slug(f"{first} {last}").split()
        email = f"{slug[0]}.{slug[-1]}@{r.choice(['gmail.com', 'outlook.com', 'yahoo.com', 'email.com'])}"
        country = {"en_US": "United States", "en_GB": "United Kingdom", "en_AU": "Australia", "en_IN": "India"}[loc]
        return {
            "name": name, "address": addr, "city": city, "phone": phone, "email": email, "country": country,
            "nationality": {"en_US": "American", "en_GB": "British", "en_AU": "Australian", "en_IN": "Indian"}[loc],
            "place_of_birth": f.city(), "slug": "".join(slug), "locale": loc,
        }

    def _personal(self, p: Profile, form_like: bool):
        r = self.rng
        gender = r.choice(["male", "female"])
        person = self._vn_person(p, gender) if p.content_lang == "vi" else self._en_person(gender)
        ds: DateStyle = p.style["dates"]
        disp, gold = {}, {}

        def put(key, d, g=None):
            disp[key] = d
            gold[key] = d if g is None else g

        name = person["name"]
        if r.random() < 0.35:
            name = name.upper()
        put("full_name", name)
        put("email", person["email"])
        put("phone", person["phone"])
        heavy = form_like or (p.content_lang == "vi" and r.random() < 0.6)
        if heavy or r.random() < 0.3:
            y, m, d = r.randint(1975, 2003), r.randint(1, 12), r.randint(1, 28)
            put("date_of_birth", *ds.day(y, m, d))
        if heavy and r.random() < 0.85 or r.random() < 0.1:
            vi = p.lang in ("vi", "bi")
            put("gender", ("Nam" if gender == "male" else "Nữ") if vi else gender.capitalize(), gender)
        if heavy and r.random() < 0.7:
            put("address", person["address"])
        elif r.random() < 0.5:
            put("city", person["city"])
        if heavy and r.random() < 0.5:
            put("place_of_birth", person["place_of_birth"])
        if heavy and r.random() < 0.5:
            put("nationality", person["nationality"])
        if heavy and r.random() < 0.4:
            vi = p.lang in ("vi", "bi")
            put("marital_status", r.choice(["Độc thân", "Đã kết hôn"] if vi else ["Single", "Married"]))
        if (form_like and r.random() < 0.7) or (heavy and r.random() < 0.15):
            idn = "".join(str(r.randint(0, 9)) for _ in range(r.choice([12, 12, 9])))
            put("id_number", "0" + idn[1:] if len(idn) == 12 else idn)
            if r.random() < 0.8:
                y, m, d = r.randint(2015, 2024), r.randint(1, 12), r.randint(1, 28)
                put("id_issue_date", *ds.day(y, m, d))
            if r.random() < 0.8:
                put("id_issue_place", r.choice(["Cục Cảnh sát QLHC về TTXH", "Công an TP. Hà Nội",
                                                "Công an TP. Hồ Chí Minh", "Bộ Công an"]))
        if r.random() < 0.3 and "address" not in disp and "city" not in disp:
            put("country", person["country"])
        if r.random() < 0.35:
            put("linkedin", r.choice(["linkedin.com/in/", "https://www.linkedin.com/in/", "www.linkedin.com/in/"])
                + person["slug"] + r.choice(["", str(r.randint(1, 99))]))
        if r.random() < 0.2:
            put("website", r.choice(["github.com/", "https://github.com/", ""]) + person["slug"]
                + ("" if r.random() < 0.7 else ".dev"))
        p.personal_disp, p.personal_gold = disp, gold
        return person

    # -- sections ------------------------------------------------------------
    def _career(self, p: Profile, domain: dict) -> tuple[list[Entry], int]:
        r = self.rng
        ds: DateStyle = p.style["dates"]
        n = r.choices([0, 1, 2, 3, 4, 5], weights=[4, 16, 28, 28, 16, 8])[0]
        year, month = 2026, r.randint(1, 9)
        entries = []
        vi = p.content_lang == "vi"
        companies = V.VN_COMPANIES if vi else None
        for i in range(n):
            ongoing = i == 0 and r.random() < 0.6
            end = None if ongoing else (year, month)
            dur = r.randint(8, 48)
            sy, sm = divmod((year * 12 + month - 1) - dur, 12)
            start = (sy, sm + 1)
            dates_disp, sg, eg = ds.range(start, end)
            title_pool = domain["titles_vi"] + domain["titles_en"] if vi else domain["titles_en"]
            title = r.choice(title_pool)
            company = r.choice(companies) if vi else self.fakers[r.choice(list(self.fakers))].company()
            bullets_pool = (domain["bullets_vi"] if vi and r.random() < 0.7 else domain["bullets_en"])
            k = r.choices([0, 1, 2, 3, 4, 5], weights=[8, 10, 25, 30, 17, 10])[0]
            bullets = [_fill(b, r) for b in r.sample(bullets_pool, min(k, len(bullets_pool)))]
            gold = {"job_title": title, "company": company, "start_date": sg, "end_date": eg}
            disp = {"job_title": title, "company": company, "dates": dates_disp, "bullets": bullets,
                    "start": ds.month(*start)[0], "end": ds.present if end is None else ds.month(*end)[0]}
            if r.random() < 0.3:
                loc = r.choice(list(V.VN_CITIES)) if vi else self.fakers["en_US"].city()
                gold["location"] = disp["location"] = loc
            if bullets:
                gold["description"] = "\n".join(bullets)
            entries.append(Entry(disp, gold))
            # next (older) job ends a bit before this one starts
            gap = r.randint(0, 4)
            year, month = divmod((start[0] * 12 + start[1] - 1) - gap, 12)
            month += 1
        return entries, year

    def _education(self, p: Profile, domain: dict, before_year: int) -> list[Entry]:
        r = self.rng
        ds: DateStyle = p.style["dates"]
        vi = p.content_lang == "vi"
        n = r.choices([0, 1, 2, 3], weights=[5, 60, 28, 7])[0]
        entries = []
        end_year = min(before_year, 2026) if before_year < 2026 else r.randint(2018, 2026)
        levels = ["bachelor", "master", "phd"][:n] if n else []
        levels = list(reversed(levels)) if r.random() < 0.7 else levels  # newest first usually
        for lvl in levels:
            span = {"bachelor": 4, "master": 2, "phd": 4, "college": 3}[lvl]
            if lvl == "bachelor" and vi and r.random() < 0.15:
                lvl, span = "college", 3
            school = r.choice(V.VN_COLLEGES if lvl == "college" else V.VN_UNIVERSITIES) if vi \
                else r.choice(V.EN_UNIVERSITIES)
            degree = r.choice((V.VN_DEGREES if vi and r.random() < 0.8 else V.EN_DEGREES)[lvl])
            major = r.choice(domain["majors_vi"] if vi and r.random() < 0.7 else domain["majors_en"])
            ey = end_year - (0 if lvl != "bachelor" else r.randint(0, 1))
            sy = ey - span
            if ds.month_style == "yyyy" or r.random() < 0.6:
                sd, sg, ed, eg = str(sy), str(sy), str(ey), str(ey)
            else:
                sd, sg = ds.month(sy, 9)
                ed, eg = ds.month(ey, r.choice([6, 7, 8]))
            gold = {"institution": school, "degree": degree, "major": major}
            disp = {"institution": school, "degree": degree, "major": major}
            if r.random() < 0.8:
                gold["start_date"], disp["start"] = sg, sd
            gold["end_date"], disp["end"] = eg, ed
            if r.random() < 0.1:
                del gold["degree"], disp["degree"]
            if r.random() < 0.45:
                grade = r.choice(V.VN_GRADES if vi and r.random() < 0.6 else V.EN_GRADES)
                gold["grade"] = disp["grade"] = grade
            entries.append(Entry(disp, gold))
            end_year = sy - r.randint(0, 2)
        return entries

    def _simple_list(self, p: Profile, domain: dict, sec: str) -> list[Entry]:
        r = self.rng
        vi = p.content_lang == "vi"
        out = []
        if sec == "languages":
            pool = V.LANGUAGES["vi" if p.lang in ("vi", "bi") else "en"]
            n = r.choices([0, 1, 2, 3], weights=[20, 45, 28, 7])[0]
            for lang, levels in r.sample(pool, n):
                gold = {"language": lang}
                disp = {"language": lang}
                if r.random() < 0.85:
                    gold["proficiency"] = disp["proficiency"] = r.choice(levels)
                out.append(Entry(disp, gold))
        elif sec in ("certificates", "courses"):
            pool = domain["certs"] if sec == "certificates" else domain["courses"]
            n = r.choices([0, 1, 2, 3], weights=[45, 30, 18, 7])[0]
            for name, issuer in r.sample(pool, min(n, len(pool))):
                gold = {"name": name}
                disp = {"name": name}
                key = "issuer" if sec == "certificates" else "provider"
                if r.random() < 0.5:
                    gold[key] = disp[key] = issuer
                if r.random() < 0.6:
                    y = r.randint(2015, 2025)
                    if sec == "certificates":
                        gold["date"], disp["date"] = str(y), str(y)
                    else:
                        gold["end_date"], disp["date"] = str(y), str(y)
                out.append(Entry(disp, gold))
        elif sec == "awards":
            pool = V.AWARDS_VI if vi else V.AWARDS_EN
            n = r.choices([0, 1, 2], weights=[65, 25, 10])[0]
            for name, issuer in r.sample(pool, n):
                gold = {"name": name}
                disp = {"name": name}
                if issuer:
                    gold["issuer"] = disp["issuer"] = issuer
                if r.random() < 0.7:
                    y = str(r.randint(2012, 2025))
                    gold["date"] = disp["date"] = y
                out.append(Entry(disp, gold))
        elif sec == "family":
            n = r.randint(1, 4)
            for _ in range(n):
                g = r.choice(["male", "female"])
                person = self._vn_person(p, g)
                rel = r.choice(V.FAMILY_REL_VI)
                gold = {"full_name": person["name"], "relationship": rel}
                disp = dict(gold)
                if r.random() < 0.8:
                    y = str(r.randint(1950, 2015))
                    gold["date_of_birth"] = disp["yob"] = y
                if r.random() < 0.7:
                    gold["occupation"] = disp["occupation"] = r.choice(V.OCCUPATIONS_VI)
                if r.random() < 0.2:
                    gold["phone"] = disp["phone"] = person["phone"]
                out.append(Entry(disp, gold))
        return out

    def generate(self, form_like: bool | None = None) -> Profile:
        r = self.rng
        content_lang = "vi" if r.random() < 0.65 else "en"
        lang = ("vi" if r.random() < 0.7 else "bi") if content_lang == "vi" else ("en" if r.random() < 0.9 else "bi")
        if form_like is None:
            form_like = content_lang == "vi" and r.random() < 0.35
        p = Profile(lang=lang, content_lang=content_lang, locale="vi_VN" if content_lang == "vi" else "en")
        p.style["dates"] = DateStyle(r, lang)
        p.style["form_like"] = form_like
        domain_name = r.choice(list(V.DOMAINS))
        domain = V.DOMAINS[domain_name]
        self._personal(p, form_like)
        if r.random() < 0.6:
            titles = domain["titles_vi"] + domain["titles_en"] if content_lang == "vi" else domain["titles_en"]
            t = r.choice(titles)
            p.personal_disp["current_title"] = p.personal_gold["current_title"] = t

        exp, oldest_year = self._career(p, domain)
        p.sections["experience"] = exp
        p.sections["education"] = self._education(p, domain, oldest_year)
        for sec in ("languages", "certificates", "awards", "courses"):
            p.sections[sec] = self._simple_list(p, domain, sec)
        if form_like and r.random() < 0.7 or content_lang == "vi" and r.random() < 0.08:
            p.sections["family"] = self._simple_list(p, domain, "family")

        # distractor content that must NOT end up in the output
        if r.random() < 0.7:
            p.extras["summary"] = r.choice([
                "Có hơn {k} năm kinh nghiệm trong lĩnh vực chuyên môn, mong muốn phát triển lâu dài.",
                "Mong muốn làm việc trong môi trường chuyên nghiệp, năng động để phát triển bản thân.",
                "Results-driven professional with {k}+ years of experience delivering measurable impact.",
                "Detail-oriented and motivated, seeking a challenging role in a growing company.",
            ]).format(k=r.randint(2, 12))
        if r.random() < 0.8:
            p.extras["skills"] = r.sample(V.SKILLS, r.randint(3, 8))
        if r.random() < 0.25:
            p.extras["projects"] = [f"{r.choice(V.PRODUCTS).capitalize()} — {r.choice(V.TECH)}"
                                    for _ in range(r.randint(1, 3))]
        if r.random() < 0.3:
            p.extras["interests"] = r.sample(V.HOBBIES, r.randint(2, 4))
        if r.random() < 0.15:
            ref = self._en_person("male")["name"] if content_lang == "en" else self._vn_person(p, "male")["name"]
            p.extras["references"] = [f"{ref} — {r.choice(['Manager', 'Trưởng phòng', 'Director'])}"]

        for sec in list(HEADINGS["en"]):
            if lang == "bi":
                h = f"{r.choice(HEADINGS['vi'][sec])} / {r.choice(HEADINGS['en'][sec])}"
            else:
                h = r.choice(HEADINGS[lang][sec])
                if sec in ODD_HEADINGS and r.random() < 0.05:
                    h = r.choice(ODD_HEADINGS[sec])
            p.heading[sec] = h.upper() if r.random() < 0.3 else h
        return p
